"""
Tests for masteries endpoints.
"""


class TestGetMasteries:
    """Tests for /masteries/{riot_id} endpoint."""

    def test_get_masteries_not_found(self, client):
        """Getting masteries for nonexistent user should fail."""
        response = client.get("/masteries/NotExists%23EUW")
        assert response.status_code == 404

    def test_get_masteries_success(self, client, sample_user, mock_data_files):
        """Getting masteries for registered user should succeed."""
        # Register user first
        client.post("/auth/register", json=sample_user)

        # Get masteries
        riot_id_encoded = sample_user["riot_id"].replace("#", "%23")
        response = client.get(f"/masteries/{riot_id_encoded}")

        assert response.status_code == 200
        data = response.json()
        assert "masteries" in data
        assert "puuid" in data


class TestGetTopMasteries:
    """Tests for /masteries/{riot_id}/top endpoint."""

    def test_get_top_masteries_not_found(self, client):
        """Getting top masteries for nonexistent user should fail."""
        response = client.get("/masteries/NotExists%23EUW/top")
        assert response.status_code == 404

    def test_get_top_masteries_success(self, client, sample_user):
        """Getting top masteries should return limited results."""
        client.post("/auth/register", json=sample_user)

        riot_id_encoded = sample_user["riot_id"].replace("#", "%23")
        response = client.get(f"/masteries/{riot_id_encoded}/top?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert "masteries" in data
        assert len(data["masteries"]) <= 5

    def test_get_top_masteries_default_limit(self, client, sample_user):
        """Default limit should be 10."""
        client.post("/auth/register", json=sample_user)

        riot_id_encoded = sample_user["riot_id"].replace("#", "%23")
        response = client.get(f"/masteries/{riot_id_encoded}/top")

        assert response.status_code == 200
        data = response.json()
        assert len(data["masteries"]) <= 10


class TestRefreshMasteries:
    """Tests for /masteries/{riot_id}/refresh endpoint."""

    def test_refresh_masteries_not_found(self, client):
        """Refreshing masteries for nonexistent user should fail."""
        response = client.post("/masteries/NotExists%23EUW/refresh")
        assert response.status_code == 404

    def test_refresh_masteries_success(self, client, sample_user):
        """Refreshing masteries for registered user should succeed."""
        client.post("/auth/register", json=sample_user)

        riot_id_encoded = sample_user["riot_id"].replace("#", "%23")
        response = client.post(f"/masteries/{riot_id_encoded}/refresh")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Masteries updated"


class TestLookupMasteries:
    """Tests for /masteries/lookup/{game_name}/{tag_line} endpoint."""

    def test_lookup_masteries_success(self, client):
        """Looking up masteries by Riot ID should work."""
        response = client.get("/masteries/lookup/TestPlayer/EUW?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "riot_id" in data
        assert "puuid" in data
        assert "masteries" in data
        assert data["riot_id"] == "TestPlayer#EUW"

    def test_lookup_masteries_with_limit(self, client):
        """Limit parameter should work."""
        response = client.get("/masteries/lookup/TestPlayer/EUW?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["masteries"]) <= 2

    def test_lookup_masteries_player_not_found(self, client, mock_riot_api):
        """Looking up nonexistent player should fail."""
        mock_riot_api["puuid"].return_value = None

        response = client.get("/masteries/lookup/FakePlayer/FAKE")
        assert response.status_code == 404
