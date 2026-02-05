"""
Riot Stats API - Backend FastAPI
Main application entry point.
"""

import hashlib
import json
import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .champions import CHAMPION_ID_TO_NAME
from .draft import router as draft_router
from .models import UserLogin, UserRegister, UserResponse
from .riot_api import fetch_masteries_from_riot, get_puuid_from_riot_id

# ============================================
# Configuration
# ============================================

RIOT_REGION = os.getenv("RIOT_REGION", "euw1")
DATA_DIR = "/app/data"
USERS_FILE = f"{DATA_DIR}/users.json"
MASTERIES_FILE = f"{DATA_DIR}/masteries.json"

os.makedirs(DATA_DIR, exist_ok=True)

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
app.include_router(draft_router)


# ============================================
# Utility Functions
# ============================================


def load_json(filepath: str) -> dict:
    """Load a JSON file, return {} if doesn't exist."""
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return {}


def save_json(filepath: str, data: dict):
    """Save data to a JSON file."""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def hash_password(password: str) -> str:
    """Hash a password with SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def transform_masteries(raw_masteries: list, limit: Optional[int] = None) -> list:
    """Transform raw Riot API masteries to our format."""
    masteries = []
    data = raw_masteries[:limit] if limit else raw_masteries
    for m in data:
        champion_id = m.get("championId")
        masteries.append(
            {
                "champion_id": champion_id,
                "champion_name": CHAMPION_ID_TO_NAME.get(champion_id, f"Champion_{champion_id}"),
                "champion_level": m.get("championLevel", 0),
                "champion_points": m.get("championPoints", 0),
                "last_play_time": m.get("lastPlayTime"),
            }
        )
    return masteries


async def refresh_user_data(riot_id: str, update_stored_puuid: bool = True) -> str:
    """
    Refresh a user's PUUID and masteries from Riot API.
    Returns the fresh PUUID.
    """
    if "#" not in riot_id:
        raise HTTPException(status_code=400, detail="Invalid format. Use: GameName#TagLine")

    game_name, tag_line = riot_id.rsplit("#", 1)
    puuid = get_puuid_from_riot_id(game_name, tag_line)

    if not puuid:
        raise HTTPException(status_code=404, detail="Player not found on Riot API")

    # Update stored PUUID if requested
    if update_stored_puuid:
        users = load_json(USERS_FILE)
        if riot_id in users and users[riot_id].get("puuid") != puuid:
            users[riot_id]["puuid"] = puuid
            save_json(USERS_FILE, users)

    # Update masteries
    raw_masteries = fetch_masteries_from_riot(puuid)
    masteries_data = load_json(MASTERIES_FILE)
    masteries_data[riot_id] = {
        "puuid": puuid,
        "masteries": transform_masteries(raw_masteries),
        "updated_at": int(time.time()),
    }
    save_json(MASTERIES_FILE, masteries_data)

    return puuid


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
        await refresh_user_data(user.riot_id, update_stored_puuid=False)

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

    try:
        puuid = await refresh_user_data(user.riot_id)
    except HTTPException:
        # Fallback to stored PUUID if Riot API fails
        puuid = stored_user.get("puuid")

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
    masteries_data = load_json(MASTERIES_FILE)

    if riot_id not in masteries_data:
        raise HTTPException(status_code=404, detail="Masteries not found")

    return masteries_data[riot_id]


@app.get("/masteries/{riot_id}/top")
async def get_top_masteries(riot_id: str, limit: int = 10):
    """Get a user's top masteries."""
    masteries_data = load_json(MASTERIES_FILE)

    if riot_id not in masteries_data:
        raise HTTPException(status_code=404, detail="Masteries not found")

    masteries = masteries_data[riot_id].get("masteries", [])
    sorted_masteries = sorted(masteries, key=lambda x: x["champion_points"], reverse=True)

    return {"masteries": sorted_masteries[:limit]}


@app.post("/masteries/{riot_id}/refresh")
async def refresh_masteries(riot_id: str):
    """Force refresh of user's masteries."""
    users = load_json(USERS_FILE)

    if riot_id not in users:
        raise HTTPException(status_code=404, detail="User not found")

    await refresh_user_data(riot_id)

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
