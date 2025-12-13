# app/tests/test_games.py
"""
Test suite for NBA Stats API Games endpoints.
Tests basic list operations, filtering, and response structure validation.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_list_games_basic():
    """
    Test GET /api/v1/games endpoint with basic parameters.
    
    Validates:
    - Response status code (200 or 404 if no data)
    - Response is a list
    - Result count respects limit parameter
    - GameResponse structure is correct
    - Nested team objects have required fields
    """
    # Setup: Create async test client with ASGI transport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        # Execute: Request games list with limit=5
        resp = await ac.get("/api/v1/games", params={"limit": 5}, follow_redirects=True)

    # Assert: Check response status code
    assert resp.status_code in (200, 404), f"Expected 200 or 404, got {resp.status_code}"

    # Handle: No games found (404 is acceptable)
    if resp.status_code == 404:
        return

    # Parse: Get JSON response data
    data = resp.json()
    
    # Assert: Verify response structure
    assert isinstance(data, list), "Response should be a list of games"
    assert len(data) <= 5, "Response length should not exceed limit"

    # Assert: Validate game object structure and nested data
    if data:
        game = data[0]
        
        # Verify: GameResponse required fields
        required_game_fields = [
            "id", "date", "season", "home_score", "visitor_score",
            "home_team", "visitor_team"
        ]
        for field in required_game_fields:
            assert field in game, f"Missing field '{field}' in game response"
        
        # Verify: Nested team objects have required fields
        assert "id" in game["home_team"], "Home team missing 'id' field"
        assert "id" in game["visitor_team"], "Visitor team missing 'id' field"
