"""
Riot API client functions.
"""

import os
from typing import Optional

import requests

RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")
RIOT_REGION = os.getenv("RIOT_REGION", "euw1")

# Region to routing mapping
ROUTING_MAP = {
    "euw1": "europe",
    "eun1": "europe",
    "tr1": "europe",
    "ru": "europe",
    "na1": "americas",
    "br1": "americas",
    "la1": "americas",
    "la2": "americas",
    "kr": "asia",
    "jp1": "asia",
    "oc1": "sea",
    "ph2": "sea",
    "sg2": "sea",
    "th2": "sea",
    "tw2": "sea",
    "vn2": "sea",
}


def get_routing(region: str) -> str:
    """Get regional routing for Riot API endpoints."""
    return ROUTING_MAP.get(region, "europe")


def get_puuid_from_riot_id(game_name: str, tag_line: str) -> Optional[str]:
    """Get PUUID from a Riot ID (GameName#TagLine)."""
    if not RIOT_API_KEY:
        return None

    routing = get_routing(RIOT_REGION)
    url = f"https://{routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("puuid")
    except Exception as e:
        print(f"Error getting PUUID: {e}")
    return None


def get_summoner_id_from_puuid(puuid: str) -> Optional[str]:
    """Get Summoner ID from a PUUID."""
    if not RIOT_API_KEY:
        return None

    url = f"https://{RIOT_REGION}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("id")
    except Exception as e:
        print(f"Error getting Summoner ID: {e}")
    return None


def fetch_masteries_from_riot(puuid: str) -> list:
    """Fetch champion masteries from Riot API."""
    if not RIOT_API_KEY:
        return []

    url = f"https://{RIOT_REGION}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching masteries: {e}")
    return []
