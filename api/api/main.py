"""
Riot Stats API - Backend FastAPI
Main application entry point.
"""

import hashlib
import json
import os
import time
from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .champions import CHAMPION_ID_TO_NAME
from .draft import router as draft_router
from .lolalytics_scraper import get_champion_stats
from .models import UserLogin, UserRegister, UserResponse
from .recommender import get_meta_tierlist, get_recommendations
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


async def update_user_masteries(riot_id: str, puuid: str):
    """Update masteries for a user (used by add_player endpoint)."""
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
    riot_id = unquote(riot_id)  # Decode %20 -> space, %23 -> #
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
    riot_id = unquote(riot_id)  # Decode %20 -> space, %23 -> #
    masteries_data = load_json(MASTERIES_FILE)

    if riot_id not in masteries_data:
        raise HTTPException(status_code=404, detail="Masteries not found")

    return masteries_data[riot_id]


@app.get("/masteries/{riot_id}/top")
async def get_top_masteries(riot_id: str, limit: int = 10):
    """Get a user's top masteries."""
    riot_id = unquote(riot_id)  # Decode %20 -> space, %23 -> #
    masteries_data = load_json(MASTERIES_FILE)

    if riot_id not in masteries_data:
        raise HTTPException(status_code=404, detail="Masteries not found")

    masteries = masteries_data[riot_id].get("masteries", [])
    sorted_masteries = sorted(masteries, key=lambda x: x["champion_points"], reverse=True)

    return {"masteries": sorted_masteries[:limit]}


@app.post("/masteries/{riot_id}/refresh")
async def refresh_masteries(riot_id: str):
    """Force refresh of user's masteries."""
    riot_id = unquote(riot_id)  # Decode %20 -> space, %23 -> #
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


# ============================================
# Recommandations basées sur Méta + Masteries + Counters
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
    Recommande des champions basés sur la méta, les masteries ET le contexte du draft

    - riot_id: Riot ID du joueur (ex: "Player#EUW")
    - role: Rôle spécifique (top, jng, mid, bot, sup) ou tous si non spécifié
    - top_n: Nombre de recommandations par rôle
    - min_pickrate: Pickrate minimum en % pour être recommandé (défaut: 1%)
    - mode: Mode de recommandation
        - "balanced": Équilibre méta + masteries + counters
        - "counter": Priorité aux counter-picks (quand enemy_champions fourni)
        - "blind": Priorité aux picks safe (peu de counters)
        - "comfort": Priorité aux masteries du joueur
    - enemy_champions: Champions ennemis séparés par virgule (ex: "Yone,Jinx,Thresh")
    - ally_champions: Champions alliés séparés par virgule
    - banned_champions: Champions bannis séparés par virgule
    """
    riot_id = unquote(riot_id)

    # Parser les listes de champions
    enemy_list = [c.strip() for c in enemy_champions.split(",")] if enemy_champions else None
    ally_list = [c.strip() for c in ally_champions.split(",")] if ally_champions else None
    banned_list = [c.strip() for c in banned_champions.split(",")] if banned_champions else None

    # Charger les masteries du joueur
    masteries_data = load_json(MASTERIES_FILE)

    if riot_id not in masteries_data:
        raise HTTPException(
            status_code=404, detail="Masteries non trouvées. Connectez-vous d'abord."
        )

    player_masteries = masteries_data[riot_id].get("masteries", [])

    if not player_masteries:
        raise HTTPException(status_code=400, detail="Aucune mastery trouvée pour ce joueur")

    # Obtenir les recommandations
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

    # Grouper par rôle
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


@app.post("/players/add/{game_name}/{tag_line}")
async def add_player(game_name: str, tag_line: str):
    """
    Ajoute un joueur à la base de données (sans mot de passe, juste pour les masteries)
    Utile pour tracker les masteries des joueurs de l'équipe
    """
    riot_id = f"{game_name}#{tag_line}"

    # Vérifier si déjà dans la base
    masteries_data = load_json(MASTERIES_FILE)
    if riot_id in masteries_data:
        # Rafraîchir les masteries
        puuid = masteries_data[riot_id].get("puuid")
        if puuid:
            await update_user_masteries(riot_id, puuid)
            return {"message": "Masteries rafraîchies", "riot_id": riot_id}
        return {"message": "Joueur déjà enregistré", "riot_id": riot_id}

    # Récupérer le PUUID
    puuid = get_puuid_from_riot_id(game_name, tag_line)
    if not puuid:
        raise HTTPException(status_code=404, detail="Joueur non trouvé sur le serveur Riot")

    # Sauvegarder les masteries
    raw_masteries = fetch_masteries_from_riot(puuid)

    masteries_data[riot_id] = {
        "puuid": puuid,
        "masteries": transform_masteries(raw_masteries),
        "updated_at": int(time.time()),
    }
    save_json(MASTERIES_FILE, masteries_data)

    return {
        "message": "Joueur ajouté avec succès",
        "riot_id": riot_id,
        "puuid": puuid,
        "masteries_count": len(masteries_data[riot_id]["masteries"]),
    }


@app.get("/players")
async def list_players():
    """Liste tous les joueurs enregistrés"""
    masteries_data = load_json(MASTERIES_FILE)

    players = []
    for riot_id, data in masteries_data.items():
        players.append(
            {
                "riot_id": riot_id,
                "masteries_count": len(data.get("masteries", [])),
                "updated_at": data.get("updated_at"),
            }
        )

    return {"players": players, "total": len(players)}


@app.get("/meta/tierlist")
async def meta_tierlist(role: Optional[str] = None):
    """
    Retourne la tierlist de la méta actuelle

    - role: Filtrer par rôle (top, jng, mid, bot, sup)
    """
    tierlist = get_meta_tierlist(role=role)

    if not tierlist:
        raise HTTPException(status_code=503, detail="Dataset non disponible")

    return {"role_filter": role, "tierlist": tierlist}


@app.get("/meta/champion/{champion}")
async def meta_champion_stats(champion: str, role: str = "mid"):
    """
    Retourne les stats d'un champion depuis Lolalytics
    """
    from api.lolalytics_scraper import get_champion_stats

    stats = get_champion_stats(champion, role)

    if not stats or stats.get("games", 0) == 0:
        raise HTTPException(
            status_code=404, detail=f"Champion '{champion}' non trouvé dans la méta"
        )

    return {"champion": champion, "role": role, "stats": stats}


# ============================================
# Lolalytics Stats - Matchups et Counters
# ============================================


@app.get("/lolalytics/{champion}/{role}")
async def lolalytics_champion_stats(champion: str, role: str):
    """
    Récupère les stats d'un champion depuis Lolalytics

    - champion: Nom du champion (ex: "Yone", "LeeSin")
    - role: Rôle (top, jng, mid, bot, sup)

    Returns:
        - counters: Champions contre lesquels on est fort (WR >= 52%)
        - weak_against: Champions contre lesquels on est faible (WR <= 48%)
        - winrate: Winrate global du champion
        - games: Nombre de games analysées
    """
    try:
        stats = get_champion_stats(champion, role)

        if not stats or stats.get("games", 0) == 0:
            raise HTTPException(status_code=404, detail=f"Pas de données pour {champion} {role}")

        return {"champion": champion, "role": role, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
