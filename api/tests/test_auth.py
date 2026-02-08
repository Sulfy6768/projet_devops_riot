"""
Tests for authentication endpoints.
"""


class TestRegister:
    """Tests for /auth/register endpoint."""

    def test_register_success(self, client, sample_user):
        """Registration with valid data should succeed."""
        response = client.post("/auth/register", json=sample_user)

        assert response.status_code == 200
        data = response.json()
        assert data["riot_id"] == sample_user["riot_id"]
        assert "puuid" in data
        assert data["region"] == "euw1"

    def test_register_duplicate_user(self, client, sample_user):
        """Registering the same user twice should fail."""
        # First registration
        client.post("/auth/register", json=sample_user)

        # Second registration should fail
        response = client.post("/auth/register", json=sample_user)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_invalid_riot_id_format(self, client):
        """Registration without # in riot_id should fail."""
        response = client.post(
            "/auth/register", json={"riot_id": "InvalidFormat", "password": "pass123"}
        )

        assert response.status_code == 400
        assert "Invalid format" in response.json()["detail"]

    def test_register_missing_fields(self, client):
        """Registration without required fields should fail."""
        response = client.post("/auth/register", json={"riot_id": "Test#EUW"})
        assert response.status_code == 422  # Validation error

        response = client.post("/auth/register", json={"password": "pass123"})
        assert response.status_code == 422


class TestLogin:
    """Tests for /auth/login endpoint."""

    def test_login_success(self, client, sample_user):
        """Login with correct credentials should succeed."""
        # First register
        client.post("/auth/register", json=sample_user)

        # Then login
        response = client.post("/auth/login", json=sample_user)
        assert response.status_code == 200

        data = response.json()
        assert data["riot_id"] == sample_user["riot_id"]

    def test_login_wrong_password(self, client, sample_user):
        """Login with wrong password should fail."""
        client.post("/auth/register", json=sample_user)

        response = client.post(
            "/auth/login", json={"riot_id": sample_user["riot_id"], "password": "wrongpass"}
        )

        assert response.status_code == 401
        assert "Incorrect password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Login with nonexistent user should fail."""
        response = client.post(
            "/auth/login", json={"riot_id": "NotExists#EUW", "password": "pass123"}
        )

        assert response.status_code == 401
        assert "User not found" in response.json()["detail"]
