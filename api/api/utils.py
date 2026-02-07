"""
Shared utility functions and constants.
"""

import json
import os
from typing import Optional

from .champions import CHAMPION_ID_TO_NAME

# ============================================
# Configuration
# ============================================

RIOT_REGION = os.getenv("RIOT_REGION", "euw1")
DATA_DIR = os.getenv("DATA_DIR", "/app/data")
USERS_FILE = f"{DATA_DIR}/users.json"
MASTERIES_FILE = f"{DATA_DIR}/masteries.json"


# ============================================
# JSON Utilities
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


# ============================================
# Data Transformation
# ============================================


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
