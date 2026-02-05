"""
Pydantic models for API request/response validation.
"""

from typing import Optional

from pydantic import BaseModel


class UserRegister(BaseModel):
    """User registration request."""

    riot_id: str  # Format: GameName#TagLine
    password: str


class UserLogin(BaseModel):
    """User login request."""

    riot_id: str
    password: str


class UserResponse(BaseModel):
    """User response model."""

    riot_id: str
    puuid: Optional[str] = None
    region: str = "euw1"


class MasteryData(BaseModel):
    """Champion mastery data."""

    champion_id: int
    champion_name: str
    champion_level: int
    champion_points: int
    last_play_time: Optional[int] = None


class DraftPredictionRequest(BaseModel):
    """Request for draft winrate prediction."""

    blue_bans: list[str] = []
    red_bans: list[str] = []
    blue_picks: list[str] = []  # Format: ["Champion.position", ...]
    red_picks: list[str] = []  # Format: ["Champion.position", ...]


class DraftAnalyzeRequest(BaseModel):
    """Request for draft analysis with player masteries."""

    players: list[dict]  # [{"riot_id": "Name#TAG", "role": "top|jng|mid|bot|sup"}, ...]
    banned_champions: list[str] = []
    picked_champions: list[str] = []
    enemy_champions: list[str] = []
