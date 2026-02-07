"""
Match history routes.
"""

from fastapi import APIRouter, HTTPException

from .riot_api import (
    RIOT_API_KEY,
    format_match_for_frontend,
    get_match_details,
    get_match_ids,
    get_puuid_from_riot_id,
)

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/{game_name}/{tag_line}")
async def get_player_matches(game_name: str, tag_line: str, count: int = 20):
    """
    Get recent ranked matches for a player.

    - game_name: Player name (e.g., "KKC Sulfy")
    - tag_line: Player tag (e.g., "SuS")
    - count: Number of matches (max 20)
    """
    if not RIOT_API_KEY:
        raise HTTPException(status_code=503, detail="Riot API not configured")

    count = min(count, 20)

    puuid = get_puuid_from_riot_id(game_name, tag_line)
    if not puuid:
        raise HTTPException(status_code=404, detail=f"Player '{game_name}#{tag_line}' not found")

    match_ids = get_match_ids(puuid, count)
    if not match_ids:
        raise HTTPException(status_code=404, detail="No ranked matches found")

    matches = []
    for match_id in match_ids:
        match_data = get_match_details(match_id)
        if match_data:
            formatted = format_match_for_frontend(match_data, puuid)
            matches.append(formatted)

    return {
        "player": f"{game_name}#{tag_line}",
        "puuid": puuid,
        "matches": matches,
        "total": len(matches),
    }
