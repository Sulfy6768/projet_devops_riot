"""
Meta statistics and Lolalytics routes.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from prometheus_client import Counter

from .lolalytics_scraper import get_champion_stats
from .recommender import get_meta_tierlist

router = APIRouter(tags=["meta"])

# Prometheus metrics
CHAMPION_LOOKUPS = Counter(
    "champion_lookups_total", "Champion lookups by name", ["champion", "role"]
)


@router.get("/meta/tierlist")
async def meta_tierlist(role: Optional[str] = None):
    """
    Get the current meta tierlist.

    - role: Filter by role (top, jng, mid, bot, sup)
    """
    tierlist = get_meta_tierlist(role=role)

    if not tierlist:
        raise HTTPException(status_code=503, detail="Dataset not available")

    return {"role_filter": role, "tierlist": tierlist}


@router.get("/meta/champion/{champion}")
async def meta_champion_stats(champion: str, role: str = "mid"):
    """
    Get stats for a champion from Lolalytics.
    """
    stats = get_champion_stats(champion, role)

    if not stats or stats.get("games", 0) == 0:
        raise HTTPException(status_code=404, detail=f"Champion '{champion}' not found in meta")

    # Track metric
    CHAMPION_LOOKUPS.labels(champion=champion, role=role).inc()

    return {"champion": champion, "role": role, "stats": stats}


@router.get("/lolalytics/{champion}/{role}")
async def lolalytics_champion_stats(champion: str, role: str):
    """
    Get champion stats from Lolalytics.

    - champion: Champion name (e.g., "Yone", "LeeSin")
    - role: Role (top, jng, mid, bot, sup)

    Returns:
        - counters: Champions we're strong against (WR >= 52%)
        - weak_against: Champions we're weak against (WR <= 48%)
        - winrate: Global winrate
        - games: Number of games analyzed
    """
    try:
        stats = get_champion_stats(champion, role)

        if not stats or stats.get("games", 0) == 0:
            raise HTTPException(status_code=404, detail=f"No data for {champion} {role}")

        # Track metric
        CHAMPION_LOOKUPS.labels(champion=champion, role=role).inc()

        return {"champion": champion, "role": role, "stats": stats}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
