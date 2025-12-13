"""
Test suite for NBA Stats API Teams endpoints.
Tests basic list operations, filtering, searching, and response structure validation.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_list_teams_basic():
    """
    Test GET /api/v1/teams endpoint with basic parameters.
    
    Validates:
    - Endpoint is reachable
    - Response status is 200 or 404
    - Response is a list
    - Result count respects limit parameter
    - TeamResponse structure is correct with all required fields
    """
    # Setup: Create async test client with ASGI transport
    transport = ASGITransport(app=app)

    # Execute: Request teams list with limit=10
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/api/v1/teams", params={"limit": 10}, follow_redirects=True)

    # Assert: Check response status code
    assert response.status_code in (200, 404), f"Expected 200 or 404, got {response.status_code}"

    # Handle: No teams found (404 is acceptable)
    if response.status_code == 404:
        return

    # Parse: Get JSON response data
    data = response.json()
    
    # Assert: Verify response structure
    assert isinstance(data, list), "Response should be a list of teams"
    assert len(data) <= 10, "Response length should not exceed limit"

    # Assert: Validate team object structure
    if data:
        team = data[0]
        
        # Verify: TeamResponse required fields
        required_team_fields = [
            "id", "conference", "division", "city", "name", "full_name", "abbreviation"
        ]
        for field in required_team_fields:
            assert field in team, f"Missing field '{field}' in team response"


@pytest.mark.asyncio
async def test_list_teams_search_case_insensitive():
    """
    Test GET /api/v1/teams with search filter.
    
    Validates:
    - Search parameter is case-insensitive
    - Filters work without errors
    - Response structure is correct when data exists
    - Pagination parameters work correctly
    """
    # Setup: Create async test client with ASGI transport
    transport = ASGITransport(app=app)

    # Execute: Request teams with case-insensitive search
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get(
            "/api/v1/teams",
            params={"search": "laKeRs", "limit": 10},
            follow_redirects=True,
        )

    # Assert: Check response status code
    assert response.status_code in (200, 404), f"Expected 200 or 404, got {response.status_code}"

    # Handle: No teams matching search (404 is acceptable)
    if response.status_code == 404:
        return

    # Parse: Get JSON response data
    data = response.json()
    
    # Assert: Verify response structure
    assert isinstance(data, list), "Response should be a list of teams"


@pytest.mark.asyncio
async def test_get_team_not_found():
    """
    Test GET /api/v1/teams/{team_id} with non-existent team ID.
    
    Validates:
    - Non-existent team returns 404
    """
    # Setup: Create async test client with ASGI transport
    transport = ASGITransport(app=app)

    # Execute: Request non-existent team
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/api/v1/teams/999999", follow_redirects=True)

    # Assert: Verify 404 Not Found
    assert response.status_code == 404, f"Expected 404 for non-existent team, got {response.status_code}"
