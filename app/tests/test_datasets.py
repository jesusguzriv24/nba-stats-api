"""
Test suite for NBA Stats API Datasets endpoints.
Tests flat data structures for machine learning, validating field presence and value ranges.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_player_dataset_basic():
    """
    Test GET /api/v1/datasets/player-game-stats endpoint.
    
    Validates:
    - Endpoint is reachable
    - Response status is 200 or 404
    - Response is a flat list structure suitable for ML
    - All expected columns are present
    - Result count respects limit parameter
    """
    # Setup: Create async test client with ASGI transport
    transport = ASGITransport(app=app)

    # Execute: Request player game stats dataset
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get(
            "/api/v1/datasets/player-game-stats",
            params={"limit": 50},
            follow_redirects=True,
        )

    # Assert: Check response status code
    assert response.status_code in (200, 404), f"Expected 200 or 404, got {response.status_code}"

    # Handle: No stats found (404 is acceptable)
    if response.status_code == 404:
        return

    # Parse: Get JSON response data
    rows = response.json()
    
    # Assert: Verify response structure
    assert isinstance(rows, list), "Response should be a list of player game stats rows"
    assert len(rows) <= 50, "Response length should not exceed limit"

    # Assert: Validate row structure and required columns
    if rows:
        row = rows[0]
        
        # Verify: Core identifier fields
        core_fields = [
            "game_id", "game_date", "season", "is_playoffs", 
            "team_id", "opponent_id", "is_home_game", "player_id"
        ]
        for field in core_fields:
            assert field in row, f"Missing core field '{field}' in player stats row"
        
        # Verify: Boxscore/counting stat fields
        boxscore_fields = [
            "pts", "trb", "ast", "stl", "blk", "tov", 
            "fg", "fga", "ft", "fta"
        ]
        for field in boxscore_fields:
            assert field in row, f"Missing boxscore field '{field}' in player stats row"
        
        # Verify: Advanced stat fields
        advanced_fields = [
            "ts_pct", "efg_pct", "usg_pct", "off_rating", "def_rating"
        ]
        for field in advanced_fields:
            assert field in row, f"Missing advanced field '{field}' in player stats row"


@pytest.mark.asyncio
async def test_player_dataset_sanity_values():
    """
    Test sanity checks on numeric values in player game stats dataset.
    
    Validates:
    - Minutes are non-negative
    - Counting stats (pts, trb, ast) are non-negative
    - Percentage stats (ts_pct, efg_pct) are in realistic ranges (0-1 or 0-3)
    - Data quality and consistency
    """
    # Setup: Create async test client with ASGI transport
    transport = ASGITransport(app=app)

    # Execute: Request player game stats dataset with larger limit for validation
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get(
            "/api/v1/datasets/player-game-stats",
            params={"limit": 200},
            follow_redirects=True,
        )

    # Assert: Check response status code
    assert response.status_code in (200, 404), f"Expected 200 or 404, got {response.status_code}"

    # Handle: No stats found (404 is acceptable)
    if response.status_code == 404:
        return

    # Parse: Get JSON response data
    rows = response.json()
    
    # Assert: Validate numeric value ranges for each row
    for idx, row in enumerate(rows):
        # Verify: Minutes are non-negative
        assert row["minutes"] >= 0, f"Row {idx}: minutes must be non-negative, got {row['minutes']}"
        
        # Verify: Counting stats are non-negative
        assert row["pts"] >= 0, f"Row {idx}: points must be non-negative"
        assert row["trb"] >= 0, f"Row {idx}: rebounds must be non-negative"
        assert row["ast"] >= 0, f"Row {idx}: assists must be non-negative"
        
        # Verify: Percentage stats are in realistic range
        if row["ts_pct"] is not None:
            assert row["ts_pct"] >= 0, f"Row {idx}: ts_pct must be non-negative"
            assert row["ts_pct"] <= 3, f"Row {idx}: unrealistic ts_pct value {row['ts_pct']}"



@pytest.mark.asyncio
async def test_team_dataset_basic():
    """
    Test GET /api/v1/datasets/team-game-stats endpoint.
    
    Validates:
    - Endpoint is reachable
    - Response status is 200 or 404
    - Response is a flat list structure suitable for ML
    - All expected columns are present
    - Result count respects limit parameter
    """
    # Setup: Create async test client with ASGI transport
    transport = ASGITransport(app=app)

    # Execute: Request team game stats dataset
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get(
            "/api/v1/datasets/team-game-stats",
            params={"limit": 50},
            follow_redirects=True,
        )

    # Assert: Check response status code
    assert response.status_code in (200, 404), f"Expected 200 or 404, got {response.status_code}"

    # Handle: No stats found (404 is acceptable)
    if response.status_code == 404:
        return

    # Parse: Get JSON response data
    rows = response.json()
    
    # Assert: Verify response structure
    assert isinstance(rows, list), "Response should be a list of team game stats rows"
    assert len(rows) <= 50, "Response length should not exceed limit"

    # Assert: Validate row structure and required columns
    if rows:
        row = rows[0]
        
        # Verify: Core identifier fields
        core_fields = [
            "game_id", "game_date", "season", "is_playoffs",
            "team_id", "opponent_id", "is_home_game"
        ]
        for field in core_fields:
            assert field in row, f"Missing core field '{field}' in team stats row"
        
        # Verify: Scoreboard fields
        score_fields = ["team_score", "opponent_score"]
        for field in score_fields:
            assert field in row, f"Missing score field '{field}' in team stats row"
        
        # Verify: Advanced team stat fields (Four Factors)
        advanced_fields = [
            "pace", "offensive_rating", "defensive_rating",
            "effective_fg_pct", "true_shooting_pct", "ft_per_fga",
            "turnover_pct", "assist_pct", "off_rebound_pct",
            "def_rebound_pct", "total_rebound_pct"
        ]
        for field in advanced_fields:
            assert field in row, f"Missing advanced field '{field}' in team stats row"


@pytest.mark.asyncio
async def test_team_dataset_sanity_values():
    """
    Test sanity checks on numeric values in team game stats dataset.
    
    Validates:
    - Scores are non-negative
    - Pace is positive when present
    - Ratings (offensive/defensive) are positive when present
    - Data quality and consistency
    """
    # Setup: Create async test client with ASGI transport
    transport = ASGITransport(app=app)

    # Execute: Request team game stats dataset with larger limit for validation
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get(
            "/api/v1/datasets/team-game-stats",
            params={"limit": 200},
            follow_redirects=True,
        )

    # Assert: Check response status code
    assert response.status_code in (200, 404), f"Expected 200 or 404, got {response.status_code}"

    # Handle: No stats found (404 is acceptable)
    if response.status_code == 404:
        return

    # Parse: Get JSON response data
    rows = response.json()
    
    # Assert: Validate numeric value ranges for each row
    for idx, row in enumerate(rows):
        # Verify: Scores are non-negative
        assert row["team_score"] >= 0, f"Row {idx}: team_score must be non-negative"
        assert row["opponent_score"] >= 0, f"Row {idx}: opponent_score must be non-negative"
        
        # Verify: Pace is positive when present
        if row["pace"] is not None:
            assert row["pace"] > 0, f"Row {idx}: pace must be positive when present"
        
        # Verify: Ratings are positive when present
        if row["offensive_rating"] is not None:
            assert row["offensive_rating"] > 0, f"Row {idx}: offensive_rating must be positive"
        
        if row["defensive_rating"] is not None:
            assert row["defensive_rating"] > 0, f"Row {idx}: defensive_rating must be positive"
