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


# ============================================
# Match History Functions
# ============================================


def get_match_ids(puuid: str, count: int = 20) -> list:
    """Get recent ranked match IDs for a player."""
    if not RIOT_API_KEY:
        return []

    routing = get_routing(RIOT_REGION)
    url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {
        "queue": 420,  # Ranked Solo/Duo
        "type": "ranked",
        "start": 0,
        "count": count,
    }
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        print(f"Error getting match IDs: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error getting match IDs: {e}")
    return []


def get_match_details(match_id: str) -> Optional[dict]:
    """Get details for a specific match."""
    if not RIOT_API_KEY:
        return None

    routing = get_routing(RIOT_REGION)
    url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error getting match details: {e}")
    return None


def format_match_for_frontend(match_data: dict, searched_puuid: str) -> dict:
    """Format match data for frontend consumption."""
    info = match_data.get("info", {})
    participants = info.get("participants", [])

    team_100 = []
    team_200 = []
    player_win = False
    team_100_win = False
    player_data_searched = None

    for p in participants:
        player_data = {
            "championId": p.get("championId"),
            "championName": p.get("championName"),
            "teamPosition": p.get("teamPosition", ""),
            "summonerName": p.get("summonerName", ""),
            "riotIdGameName": p.get("riotIdGameName", ""),
            "riotIdTagline": p.get("riotIdTagline", ""),
            "kills": p.get("kills", 0),
            "deaths": p.get("deaths", 0),
            "assists": p.get("assists", 0),
            "cs": p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0),
            "visionScore": p.get("visionScore", 0),
            "goldEarned": p.get("goldEarned", 0),
            "totalDamageDealt": p.get("totalDamageDealtToChampions", 0),
            "totalDamageTaken": p.get("totalDamageTaken", 0),
            "win": p.get("win", False),
        }

        if p.get("teamId") == 100:
            team_100.append(player_data)
            if p.get("win"):
                team_100_win = True
        else:
            team_200.append(player_data)

        if p.get("puuid") == searched_puuid:
            player_win = p.get("win", False)
            player_data_searched = player_data

    return {
        "match_id": match_data.get("metadata", {}).get("matchId"),
        "game_duration": info.get("gameDuration", 0),
        "game_mode": info.get("gameMode", ""),
        "game_version": info.get("gameVersion", ""),
        "queue_id": info.get("queueId", 0),
        "game_creation": info.get("gameCreation", 0),
        "team_100_win": team_100_win,
        "team_100_champions": team_100,
        "team_200_champions": team_200,
        "playerWin": player_win,
        "playerData": player_data_searched,
    }
