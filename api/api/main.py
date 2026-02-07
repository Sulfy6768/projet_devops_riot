"""
Riot Stats API - Backend FastAPI
Main application entry point.
"""

import hashlib
import time
from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .draft import router as draft_router
from .matches import router as matches_router
from .meta import router as meta_router
from .models import UserLogin, UserRegister, UserResponse
from .players import router as players_router
from .recommender import get_recommendations
from .riot_api import fetch_masteries_from_riot, get_puuid_from_riot_id
from .utils import (
    MASTERIES_FILE,
    RIOT_REGION,
    USERS_FILE,
    load_json,
    save_json,
    transform_masteries,
)

# ============================================
# Application
# ============================================

app = FastAPI(title="Riot Stats API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Include routers
app.include_router(draft_router)
app.include_router(matches_router)
app.include_router(players_router)
app.include_router(meta_router)


# ============================================
# Utility Functions
# ============================================


def hash_password(password: str) -> str:
    """Hash a password with SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


async def update_user_masteries(riot_id: str, puuid: str):
    """Update masteries for a user."""
    raw_masteries = fetch_masteries_from_riot(puuid)
    masteries_data = load_json(MASTERIES_FILE)
    masteries_data[riot_id] = {
        "puuid": puuid,
        "masteries": transform_masteries(raw_masteries),
        "updated_at": int(time.time()),
    }
    save_json(MASTERIES_FILE, masteries_data)


# ============================================
# Health Check
# ============================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "riot-api"}


# ============================================
# Authentication Routes
# ============================================


@app.post("/auth/register", response_model=UserResponse)
async def register(user: UserRegister):
    """Register a new user."""
    users = load_json(USERS_FILE)

    if user.riot_id in users:
        raise HTTPException(status_code=400, detail="User already exists")

    if "#" not in user.riot_id:
        raise HTTPException(status_code=400, detail="Invalid format. Use: GameName#TagLine")

    game_name, tag_line = user.riot_id.rsplit("#", 1)
    puuid = get_puuid_from_riot_id(game_name, tag_line)

    users[user.riot_id] = {
        "password_hash": hash_password(user.password),
        "puuid": puuid,
        "region": RIOT_REGION,
        "created_at": int(time.time()),
    }
    save_json(USERS_FILE, users)

    if puuid:
        await update_user_masteries(user.riot_id, puuid)

    return UserResponse(riot_id=user.riot_id, puuid=puuid, region=RIOT_REGION)


@app.post("/auth/login", response_model=UserResponse)
async def login(user: UserLogin):
    """Login a user and refresh their masteries."""
    users = load_json(USERS_FILE)

    if user.riot_id not in users:
        raise HTTPException(status_code=401, detail="User not found")

    stored_user = users[user.riot_id]
    if stored_user["password_hash"] != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Incorrect password")

    puuid = stored_user.get("puuid")
    if puuid:
        await update_user_masteries(user.riot_id, puuid)

    return UserResponse(
        riot_id=user.riot_id,
        puuid=puuid,
        region=stored_user.get("region", RIOT_REGION),
    )


# ============================================
# User Routes
# ============================================


@app.get("/users/{riot_id}")
async def get_user(riot_id: str):
    """Get user info."""
    riot_id = unquote(riot_id)
    users = load_json(USERS_FILE)

    if riot_id not in users:
        raise HTTPException(status_code=404, detail="User not found")

    user = users[riot_id]
    return UserResponse(
        riot_id=riot_id,
        puuid=user.get("puuid"),
        region=user.get("region", RIOT_REGION),
    )


# ============================================
# Mastery Routes
# ============================================


@app.get("/masteries/{riot_id}")
async def get_masteries(riot_id: str):
    """Get a user's masteries."""
    riot_id = unquote(riot_id)
    masteries_data = load_json(MASTERIES_FILE)

    if riot_id not in masteries_data:
        raise HTTPException(status_code=404, detail="Masteries not found")

    return masteries_data[riot_id]


@app.get("/masteries/{riot_id}/top")
async def get_top_masteries(riot_id: str, limit: int = 10):
    """Get a user's top masteries."""
    riot_id = unquote(riot_id)
    masteries_data = load_json(MASTERIES_FILE)

    if riot_id not in masteries_data:
        raise HTTPException(status_code=404, detail="Masteries not found")

    masteries = masteries_data[riot_id].get("masteries", [])
    sorted_masteries = sorted(masteries, key=lambda x: x["champion_points"], reverse=True)

    return {"masteries": sorted_masteries[:limit]}


@app.post("/masteries/{riot_id}/refresh")
async def refresh_masteries(riot_id: str):
    """Force refresh of user's masteries."""
    riot_id = unquote(riot_id)
    users = load_json(USERS_FILE)

    if riot_id not in users:
        raise HTTPException(status_code=404, detail="User not found")

    puuid = users[riot_id].get("puuid")
    if not puuid:
        raise HTTPException(status_code=400, detail="PUUID not available")

    await update_user_masteries(riot_id, puuid)

    return {"message": "Masteries updated"}


@app.get("/masteries/lookup/{game_name}/{tag_line}")
async def lookup_masteries(game_name: str, tag_line: str, limit: int = 50):
    """Lookup masteries for any player by Riot ID (no account required)."""
    puuid = get_puuid_from_riot_id(game_name, tag_line)
    if not puuid:
        raise HTTPException(status_code=404, detail="Player not found")

    raw_masteries = fetch_masteries_from_riot(puuid)
    if not raw_masteries:
        raise HTTPException(status_code=404, detail="Masteries not available")

    return {
        "riot_id": f"{game_name}#{tag_line}",
        "puuid": puuid,
        "masteries": transform_masteries(raw_masteries, limit),
    }


# ============================================
# Recommendations
# ============================================


@app.get("/recommend/{riot_id}")
async def recommend_champions(
    riot_id: str,
    role: Optional[str] = None,
    top_n: int = 5,
    min_pickrate: float = 1.0,
    mode: str = "balanced",
    enemy_champions: Optional[str] = None,
    ally_champions: Optional[str] = None,
    banned_champions: Optional[str] = None,
):
    """
    Recommend champions based on meta, masteries, and draft context.

    - riot_id: Player's Riot ID (e.g., "Player#EUW")
    - role: Specific role (top, jng, mid, bot, sup) or all if not specified
    - top_n: Number of recommendations per role
    - min_pickrate: Minimum pickrate % to be recommended (default: 1%)
    - mode: Recommendation mode
        - "balanced": Balance meta + masteries + counters
        - "counter": Prioritize counter-picks (when enemy_champions provided)
        - "blind": Prioritize safe picks (few counters)
        - "comfort": Prioritize player's masteries
    - enemy_champions: Enemy champions comma-separated (e.g., "Yone,Jinx,Thresh")
    - ally_champions: Ally champions comma-separated
    - banned_champions: Banned champions comma-separated
    """
    riot_id = unquote(riot_id)

    enemy_list = [c.strip() for c in enemy_champions.split(",")] if enemy_champions else None
    ally_list = [c.strip() for c in ally_champions.split(",")] if ally_champions else None
    banned_list = [c.strip() for c in banned_champions.split(",")] if banned_champions else None

    masteries_data = load_json(MASTERIES_FILE)

    if riot_id not in masteries_data:
        raise HTTPException(status_code=404, detail="Masteries not found. Please login first.")

    player_masteries = masteries_data[riot_id].get("masteries", [])

    if not player_masteries:
        raise HTTPException(status_code=400, detail="No masteries found for this player")

    recommendations = get_recommendations(
        masteries=player_masteries,
        role=role,
        top_n=top_n,
        min_pickrate=min_pickrate,
        enemy_champions=enemy_list,
        ally_champions=ally_list,
        banned_champions=banned_list,
        mode=mode,
    )

    by_role = {}
    for rec in recommendations:
        r = rec["role"]
        if r not in by_role:
            by_role[r] = []
        by_role[r].append(rec)

    return {
        "riot_id": riot_id,
        "role_filter": role,
        "mode": mode,
        "enemy_champions": enemy_list,
        "recommendations": by_role,
        "total_masteries": len(player_masteries),
    }
