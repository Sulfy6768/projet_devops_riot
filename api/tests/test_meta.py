"""
Tests for meta endpoints.
"""

from unittest.mock import patch


class TestMetaTierlist:
    """Tests for /meta/tierlist endpoint."""

    def test_meta_tierlist_success(self, client):
        """Tierlist endpoint should return data."""
        with patch("api.meta.get_meta_tierlist") as mock_tierlist:
            mock_tierlist.return_value = [
                {"champion": "Yone", "role": "mid", "winrate": 52.5, "pickrate": 10.0},
                {"champion": "Jinx", "role": "bot", "winrate": 51.0, "pickrate": 8.0},
            ]

            response = client.get("/meta/tierlist")

            assert response.status_code == 200
            data = response.json()
            assert "tierlist" in data

    def test_meta_tierlist_with_role_filter(self, client):
        """Tierlist should accept role filter."""
        with patch("api.meta.get_meta_tierlist") as mock_tierlist:
            mock_tierlist.return_value = [
                {"champion": "Jinx", "role": "bot", "winrate": 51.0, "pickrate": 8.0},
            ]

            response = client.get("/meta/tierlist?role=bot")

            assert response.status_code == 200
            data = response.json()
            assert data["role_filter"] == "bot"

    def test_meta_tierlist_empty(self, client):
        """Empty tierlist should return 503."""
        with patch("api.meta.get_meta_tierlist") as mock_tierlist:
            mock_tierlist.return_value = []

            response = client.get("/meta/tierlist")
            assert response.status_code == 503


class TestMetaChampion:
    """Tests for /meta/champion/{champion} endpoint."""

    def test_meta_champion_success(self, client):
        """Getting champion stats should work."""
        with patch("api.meta.get_champion_stats") as mock_stats:
            mock_stats.return_value = {
                "winrate": 52.5,
                "pickrate": 8.0,
                "games": 10000,
                "counters": ["Zed", "Talon"],
            }

            response = client.get("/meta/champion/Yone?role=mid")

            assert response.status_code == 200
            data = response.json()
            assert data["champion"] == "Yone"
            assert data["role"] == "mid"
            assert "stats" in data

    def test_meta_champion_not_found(self, client):
        """Nonexistent champion should return 404."""
        with patch("api.meta.get_champion_stats") as mock_stats:
            mock_stats.return_value = {"games": 0}

            response = client.get("/meta/champion/FakeChampion?role=mid")
            assert response.status_code == 404


class TestLolalytics:
    """Tests for /lolalytics/{champion}/{role} endpoint."""

    def test_lolalytics_success(self, client):
        """Lolalytics endpoint should return stats."""
        with patch("api.meta.get_champion_stats") as mock_stats:
            mock_stats.return_value = {
                "winrate": 52.5,
                "pickrate": 8.0,
                "games": 10000,
                "counters": [{"champion": "Zed", "winrate": 45.0}],
                "weak_against": [{"champion": "Malzahar", "winrate": 55.0}],
            }

            response = client.get("/lolalytics/Yone/mid")

            assert response.status_code == 200
            data = response.json()
            assert data["champion"] == "Yone"
            assert data["role"] == "mid"
            assert "stats" in data

    def test_lolalytics_not_found(self, client):
        """Nonexistent champion/role combo should return 404."""
        with patch("api.meta.get_champion_stats") as mock_stats:
            mock_stats.return_value = {"games": 0}

            response = client.get("/lolalytics/FakeChamp/top")
            assert response.status_code == 404
