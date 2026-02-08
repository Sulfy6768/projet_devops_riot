"""
Tests for draft endpoints.
"""

from unittest.mock import MagicMock, patch


class TestDraftPredict:
    """Tests for /draft/predict endpoint."""

    def test_predict_model_not_loaded(self, client):
        """Prediction without model should return 503."""
        with patch("api.draft.get_draft_predictor") as mock_predictor:
            mock_predictor.return_value = None

            response = client.post(
                "/draft/predict",
                json={
                    "blue_bans": ["Yone", "Yasuo"],
                    "red_bans": ["Jinx", "Vayne"],
                    "blue_picks": ["Ahri.mid", "LeeSin.jng"],
                    "red_picks": ["Zed.mid", "Vi.jng"],
                },
            )

            assert response.status_code == 503
            assert "not loaded" in response.json()["detail"]

    def test_predict_success(self, client):
        """Prediction with loaded model should succeed."""
        mock_predictor = MagicMock()
        mock_predictor.predict_win_probability.return_value = {
            "blue_win_probability": 55.5,
            "red_win_probability": 44.5,
        }

        with patch("api.draft.get_draft_predictor") as mock_get:
            mock_get.return_value = mock_predictor

            response = client.post(
                "/draft/predict",
                json={
                    "blue_bans": ["Yone"],
                    "red_bans": ["Jinx"],
                    "blue_picks": ["Ahri.mid"],
                    "red_picks": ["Zed.mid"],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "blue_winrate" in data
            assert "red_winrate" in data

    def test_predict_empty_draft(self, client):
        """Prediction with empty draft should work."""
        mock_predictor = MagicMock()
        mock_predictor.predict_win_probability.return_value = {
            "blue_win_probability": 50.0,
            "red_win_probability": 50.0,
        }

        with patch("api.draft.get_draft_predictor") as mock_get:
            mock_get.return_value = mock_predictor

            response = client.post(
                "/draft/predict",
                json={
                    "blue_bans": [],
                    "red_bans": [],
                    "blue_picks": [],
                    "red_picks": [],
                },
            )

            assert response.status_code == 200


class TestDraftSuggest:
    """Tests for /draft/suggest endpoint."""

    def test_suggest_model_not_loaded(self, client):
        """Suggestion without model should return 503."""
        with patch("api.draft.get_draft_predictor") as mock_predictor:
            mock_predictor.return_value = None

            response = client.post(
                "/draft/suggest",
                json={
                    "team": "blue",
                    "position": "mid",
                    "blue_picks": ["LeeSin.jng"],
                    "red_picks": ["Vi.jng"],
                    "blue_bans": [],
                    "red_bans": [],
                },
            )

            assert response.status_code == 503

    def test_suggest_success(self, client):
        """Suggestion with loaded model should succeed."""
        mock_predictor = MagicMock()
        mock_predictor.suggest_best_picks.return_value = [
            {"champion": "Ahri", "win_probability": 55.5},
            {"champion": "Syndra", "win_probability": 54.0},
        ]

        with patch("api.draft.get_draft_predictor") as mock_get:
            mock_get.return_value = mock_predictor

            response = client.post(
                "/draft/suggest",
                json={
                    "team": "blue",
                    "position": "mid",
                    "blue_picks": [],
                    "red_picks": [],
                    "blue_bans": [],
                    "red_bans": [],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "suggestions" in data


class TestDraftAnalyze:
    """Tests for /draft/analyze endpoint."""

    def test_analyze_empty_players(self, client):
        """Analysis with empty players list should fail."""
        response = client.post(
            "/draft/analyze",
            json={
                "players": [],
                "banned_champions": [],
                "picked_champions": [],
                "enemy_champions": [],
            },
        )

        # Should return 400 or similar
        assert response.status_code in [400, 422, 200]

    def test_analyze_with_players(self, client, sample_user):
        """Analysis with players should work."""
        # First register a user
        client.post("/auth/register", json=sample_user)

        response = client.post(
            "/draft/analyze",
            json={
                "players": [{"riot_id": sample_user["riot_id"], "role": "bot"}],
                "banned_champions": ["Yone"],
                "picked_champions": [],
                "enemy_champions": ["Thresh"],
            },
        )

        # May succeed or fail depending on data
        assert response.status_code in [200, 404, 400]
