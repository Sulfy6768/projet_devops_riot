"""
Pytest fixtures for API tests.
"""

import json
import os
import tempfile
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Set environment variables before importing app
os.environ["RIOT_API_KEY"] = "FAKE_API_KEY"
os.environ["RIOT_REGION"] = "euw1"


@pytest.fixture
def temp_data_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test data files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create empty JSON files
        users_file = os.path.join(tmpdir, "users.json")
        masteries_file = os.path.join(tmpdir, "masteries.json")

        with open(users_file, "w") as f:
            json.dump({}, f)
        with open(masteries_file, "w") as f:
            json.dump({}, f)

        yield tmpdir


# Storage for mock data
_mock_users: dict = {}
_mock_masteries: dict = {}


def mock_load_json(filepath: str) -> dict:
    """Mock load_json that uses in-memory storage."""
    if "users" in filepath:
        return _mock_users.copy()
    elif "masteries" in filepath:
        return _mock_masteries.copy()
    return {}


def mock_save_json(filepath: str, data: dict):
    """Mock save_json that uses in-memory storage."""
    global _mock_users, _mock_masteries
    if "users" in filepath:
        _mock_users.clear()
        _mock_users.update(data)
    elif "masteries" in filepath:
        _mock_masteries.clear()
        _mock_masteries.update(data)


@pytest.fixture(autouse=True)
def reset_mock_data():
    """Reset mock data before each test."""
    global _mock_users, _mock_masteries
    _mock_users = {}
    _mock_masteries = {}
    yield
    _mock_users = {}
    _mock_masteries = {}


@pytest.fixture
def mock_data_files():
    """Mock the load/save functions to use in-memory storage."""
    with (
        patch("api.main.load_json", side_effect=mock_load_json),
        patch("api.main.save_json", side_effect=mock_save_json),
        patch("api.players.load_json", side_effect=mock_load_json),
        patch("api.players.save_json", side_effect=mock_save_json),
    ):
        yield


@pytest.fixture
def mock_riot_api():
    """Mock Riot API calls."""
    # Need to patch where the functions are used, not where defined
    with (
        patch("api.main.get_puuid_from_riot_id") as mock_puuid1,
        patch("api.main.fetch_masteries_from_riot") as mock_masteries1,
        patch("api.players.get_puuid_from_riot_id") as mock_puuid2,
        patch("api.players.fetch_masteries_from_riot") as mock_masteries2,
        patch("api.riot_api.get_puuid_from_riot_id") as mock_puuid3,
        patch("api.riot_api.fetch_masteries_from_riot") as mock_masteries3,
    ):
        # Default return values for all mocks
        for m in [mock_puuid1, mock_puuid2, mock_puuid3]:
            m.return_value = "fake-puuid-12345"
        for m in [mock_masteries1, mock_masteries2, mock_masteries3]:
            m.return_value = [
                {
                    "championId": 21,
                    "championLevel": 7,
                    "championPoints": 500000,
                    "lastPlayTime": 1700000000000,
                },
                {
                    "championId": 67,
                    "championLevel": 7,
                    "championPoints": 400000,
                    "lastPlayTime": 1700000000000,
                },
                {
                    "championId": 222,
                    "championLevel": 6,
                    "championPoints": 100000,
                    "lastPlayTime": 1700000000000,
                },
            ]
        yield {
            "puuid": mock_puuid1,
            "masteries": mock_masteries1,
            "puuid_players": mock_puuid2,
            "masteries_players": mock_masteries2,
        }


@pytest.fixture
def client(mock_data_files, mock_riot_api) -> TestClient:
    """Create a test client with mocked dependencies."""
    # Need to reimport after patching
    from api.main import app

    return TestClient(app)


@pytest.fixture
def sample_user():
    """Sample user data for tests."""
    return {"riot_id": "TestPlayer#EUW", "password": "testpass123"}


@pytest.fixture
def sample_masteries():
    """Sample masteries data."""
    return {
        "puuid": "fake-puuid-12345",
        "masteries": [
            {
                "champion_id": 21,
                "champion_name": "MissFortune",
                "champion_level": 7,
                "champion_points": 500000,
                "last_play_time": 1700000000000,
            },
            {
                "champion_id": 67,
                "champion_name": "Vayne",
                "champion_level": 7,
                "champion_points": 400000,
                "last_play_time": 1700000000000,
            },
        ],
        "updated_at": 1700000000,
    }


@pytest.fixture
def registered_user(client, sample_user, mock_data_files):
    """Register a user and return the response."""
    response = client.post("/auth/register", json=sample_user)
    return response.json()
