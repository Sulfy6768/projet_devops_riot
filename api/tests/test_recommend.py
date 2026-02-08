"""
Tests for recommendations endpoint.
"""

from unittest.mock import patch


class TestRecommendations:
    """Tests for /recommend/{riot_id} endpoint."""

    def test_recommend_user_not_found(self, client):
        """Recommendations for nonexistent user should fail."""
        response = client.get("/recommend/NotExists%23EUW")
        assert response.status_code == 404

    def test_recommend_success(self, client, sample_user):
        """Recommendations for registered user should work."""
        client.post("/auth/register", json=sample_user)

        with patch("api.main.get_recommendations") as mock_recs:
            mock_recs.return_value = [
                {"champion": "Jinx", "role": "bot", "score": 85.0},
                {"champion": "Caitlyn", "role": "bot", "score": 80.0},
            ]

            riot_id_encoded = sample_user["riot_id"].replace("#", "%23")
            response = client.get(f"/recommend/{riot_id_encoded}")

            assert response.status_code == 200
            data = response.json()
            assert "recommendations" in data
            assert data["riot_id"] == sample_user["riot_id"]

    def test_recommend_with_role_filter(self, client, sample_user):
        """Recommendations with role filter should work."""
        client.post("/auth/register", json=sample_user)

        with patch("api.main.get_recommendations") as mock_recs:
            mock_recs.return_value = [
                {"champion": "Thresh", "role": "sup", "score": 75.0},
            ]

            riot_id_encoded = sample_user["riot_id"].replace("#", "%23")
            response = client.get(f"/recommend/{riot_id_encoded}?role=sup")

            assert response.status_code == 200
            data = response.json()
            assert data["role_filter"] == "sup"

    def test_recommend_with_mode(self, client, sample_user):
        """Recommendations with different modes should work."""
        client.post("/auth/register", json=sample_user)

        with patch("api.main.get_recommendations") as mock_recs:
            mock_recs.return_value = []

            riot_id_encoded = sample_user["riot_id"].replace("#", "%23")

            for mode in ["balanced", "counter", "blind", "comfort"]:
                response = client.get(f"/recommend/{riot_id_encoded}?mode={mode}")
                assert response.status_code == 200
                assert response.json()["mode"] == mode

    def test_recommend_with_enemy_champions(self, client, sample_user):
        """Recommendations with enemy champions should work."""
        client.post("/auth/register", json=sample_user)

        with patch("api.main.get_recommendations") as mock_recs:
            mock_recs.return_value = []

            riot_id_encoded = sample_user["riot_id"].replace("#", "%23")
            response = client.get(
                f"/recommend/{riot_id_encoded}?enemy_champions=Yone,Thresh&mode=counter"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["enemy_champions"] == ["Yone", "Thresh"]
