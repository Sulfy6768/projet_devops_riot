"""
Player management routes.
"""

import time

from fastapi import APIRouter, HTTPException

from .riot_api import fetch_masteries_from_riot, get_puuid_from_riot_id
from .utils import MASTERIES_FILE, load_json, save_json, transform_masteries

router = APIRouter(prefix="/players", tags=["players"])


@router.post("/add/{game_name}/{tag_line}")
async def add_player(game_name: str, tag_line: str):
    """
    Add a player to the database (no password, just for masteries).
    Useful for tracking team players' masteries.
    """
    riot_id = f"{game_name}#{tag_line}"

    masteries_data = load_json(MASTERIES_FILE)
    if riot_id in masteries_data:
        puuid = masteries_data[riot_id].get("puuid")
        if puuid:
            raw_masteries = fetch_masteries_from_riot(puuid)
            masteries_data[riot_id] = {
                "puuid": puuid,
                "masteries": transform_masteries(raw_masteries),
                "updated_at": int(time.time()),
            }
            save_json(MASTERIES_FILE, masteries_data)
            return {"message": "Masteries refreshed", "riot_id": riot_id}
        return {"message": "Player already registered", "riot_id": riot_id}

    puuid = get_puuid_from_riot_id(game_name, tag_line)
    if not puuid:
        raise HTTPException(status_code=404, detail="Player not found on Riot server")

    raw_masteries = fetch_masteries_from_riot(puuid)

    masteries_data[riot_id] = {
        "puuid": puuid,
        "masteries": transform_masteries(raw_masteries),
        "updated_at": int(time.time()),
    }
    save_json(MASTERIES_FILE, masteries_data)

    return {
        "message": "Player added successfully",
        "riot_id": riot_id,
        "puuid": puuid,
        "masteries_count": len(masteries_data[riot_id]["masteries"]),
    }


@router.get("")
async def list_players():
    """List all registered players."""
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
