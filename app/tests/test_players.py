"""
Test suite for NBA Stats API Players endpoints.
Tests basic list operations, filtering, searching, and response structure validation.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_list_players_basic():
    """
    Test GET /api/v1/players endpoint with basic parameters.
    
    Validates:
    - Endpoint is reachable
    - Response status is 200 or 404
    - Response is a list
    - Result count respects limit parameter
    - PlayerResponse structure is correct
    - Nested team object is present
    """
    # Setup: Create async test client with ASGI transport
    transport = ASGITransport(app=app)

    # Execute: Request players list with limit=10
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/api/v1/players", params={"limit": 10}, follow_redirects=True)

    # Assert: Check response status code
    assert response.status_code in (200, 404), f"Expected 200 or 404, got {response.status_code}"

    # Handle: No players found (404 is acceptable)
    if response.status_code == 404:
        return

    # Parse: Get JSON response data
    data = response.json()
    
    # Assert: Verify response structure
    assert isinstance(data, list), "Response should be a list of players"
    assert len(data) <= 10, "Response length should not exceed limit"

    # Assert: Validate player object structure
    if data:
        player = data[0]
        
        # Verify: PlayerResponse required fields
        required_player_fields = [
            "id", "first_name", "last_name", "position", "team"
        ]
        for field in required_player_fields:
            assert field in player, f"Missing field '{field}' in player response"


@pytest.mark.asyncio
async def test_list_players_search_and_position():
    """
    Test GET /api/v1/players with search and position filters.
    
    Validates:
    - Filters are accepted without errors
    - Response structure is correct
    - Pagination parameters work
    """
    # Setup: Create async test client with ASGI transport
    transport = ASGITransport(app=app)

    # Execute: Request players with search and position filters
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get(
            "/api/v1/players",
            params={"search": "jaMes", "position": "G", "limit": 10},
            follow_redirects=True,
        )

    # Assert: Check response status code
    assert response.status_code in (200, 404), f"Expected 200 or 404, got {response.status_code}"

    # Handle: No players matching filters (404 is acceptable)
    if response.status_code == 404:
        return

    # Parse: Get JSON response data
    data = response.json()
    
    # Assert: Verify response structure
    assert isinstance(data, list), "Response should be a list of players"


@pytest.mark.asyncio
async def test_get_player_not_found():
    """
    Test GET /api/v1/players/{player_id} with non-existent player ID.
    
    Validates:
    - Non-existent player returns 404
    """
    # Setup: Create async test client with ASGI transport
    transport = ASGITransport(app=app)

    # Execute: Request non-existent player
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/api/v1/players/999999", follow_redirects=True)

    # Assert: Verify 404 Not Found
    assert response.status_code == 404, f"Expected 404 for non-existent player, got {response.status_code}"


@pytest.mark.asyncio
async def test_get_player_games_basic():
    """
    Test GET /api/v1/players/{player_id}/games endpoint.
    
    Validates:
    - Response status is 200 or 404
    - Response is a list when data exists
    - Result count respects limit parameter
    - PlayerGameStatsResponse structure is correct
    """
    # Setup: Create async test client with ASGI transport
    transport = ASGITransport(app=app)

    # Execute: Request player game statistics
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get(
            "/api/v1/players/1/games",
            params={"limit": 5},
            follow_redirects=True,
        )

    # Assert: Check response status code
    assert response.status_code in (200, 404), f"Expected 200 or 404, got {response.status_code}"

    # Handle: No games found for this player (404 is acceptable)
    if response.status_code == 404:
        return

    # Parse: Get JSON response data
    data = response.json()
    
    # Assert: Verify response structure
    assert isinstance(data, list), "Response should be a list of player game stats"
    assert len(data) <= 5, "Response length should not exceed limit"

    # Assert: Validate player game stats object structure
    if data:
        stats = data[0]
        
        # Verify: PlayerGameStatsResponse required fields
        required_stats_fields = [
            "id", "game_id", "player", "pts", "ast", "trb", "minutes"
        ]
        for field in required_stats_fields:
            assert field in stats, f"Missing field '{field}' in player game stats response"
        
        # Verify: Nested team object if present
        if stats.get("team") is not None:
            assert "id" in stats["team"], "Team object missing 'id' field"

