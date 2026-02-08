"""
Tests for users endpoints.
"""


class TestGetUser:
    """Tests for /users/{riot_id} endpoint."""

    def test_get_user_not_found(self, client):
        """Getting nonexistent user should fail."""
        response = client.get("/users/NotExists%23EUW")
        assert response.status_code == 404

    def test_get_user_success(self, client, sample_user):
        """Getting registered user should succeed."""
        client.post("/auth/register", json=sample_user)

        riot_id_encoded = sample_user["riot_id"].replace("#", "%23")
        response = client.get(f"/users/{riot_id_encoded}")

        assert response.status_code == 200
        data = response.json()
        assert data["riot_id"] == sample_user["riot_id"]
        assert "puuid" in data
        assert "region" in data

    def test_get_user_url_encoded(self, client, sample_user):
        """User endpoint should handle URL encoding correctly."""
        client.post("/auth/register", json=sample_user)

        # Test with space in name
        user_with_space = {"riot_id": "Test Player#EUW", "password": "pass123"}
        client.post("/auth/register", json=user_with_space)

        response = client.get("/users/Test%20Player%23EUW")
        assert response.status_code == 200
        assert response.json()["riot_id"] == "Test Player#EUW"
