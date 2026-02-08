"""
Tests for players endpoints.
"""


class TestAddPlayer:
    """Tests for /players/add/{game_name}/{tag_line} endpoint."""

    def test_add_player_success(self, client):
        """Adding a new player should succeed."""
        response = client.post("/players/add/NewPlayer/EUW")

        assert response.status_code == 200
        data = response.json()
        assert "riot_id" in data
        assert data["riot_id"] == "NewPlayer#EUW"

    def test_add_player_already_exists(self, client):
        """Adding the same player twice should refresh masteries."""
        # First add
        client.post("/players/add/TestPlayer/EUW")

        # Second add should still succeed (refresh)
        response = client.post("/players/add/TestPlayer/EUW")
        assert response.status_code == 200

    def test_add_player_not_found(self, client, mock_riot_api):
        """Adding nonexistent player should fail."""
        mock_riot_api["puuid"].return_value = None
        mock_riot_api["puuid_players"].return_value = None

        response = client.post("/players/add/FakePlayer/FAKE")
        assert response.status_code == 404


class TestListPlayers:
    """Tests for /players endpoint."""

    def test_list_players_empty(self, client):
        """Listing players when none exist should return empty list."""
        response = client.get("/players")

        assert response.status_code == 200
        data = response.json()
        assert "players" in data
        assert "total" in data
        assert data["total"] == 0

    def test_list_players_with_data(self, client):
        """Listing players after adding should return them."""
        # Add some players
        client.post("/players/add/Player1/EUW")
        client.post("/players/add/Player2/EUW")

        response = client.get("/players")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["players"]) == 2

    def test_list_players_format(self, client):
        """Player list should have correct format."""
        client.post("/players/add/TestPlayer/EUW")

        response = client.get("/players")
        data = response.json()

        player = data["players"][0]
        assert "riot_id" in player
        assert "masteries_count" in player
        assert "updated_at" in player
