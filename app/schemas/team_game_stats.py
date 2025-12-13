from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.team import TeamResponse


# ------------------------------------------------------------------
# SHARED BASE SCHEMA
# ------------------------------------------------------------------
class TeamGameStatsBase(BaseModel):
    """
    Shared properties for Team Game Stats (Four Factors, Advanced).
    """
    is_home_game: bool
    
    # Advanced Stats (Optional because they might be calculated later)
    pace: Optional[float] = None
    offensive_rating: Optional[float] = None
    defensive_rating: Optional[float] = None
    
    effective_fg_pct: Optional[float] = None
    true_shooting_pct: Optional[float] = None
    ft_per_fga: Optional[float] = None
    
    turnover_pct: Optional[float] = None
    assist_pct: Optional[float] = None
    
    off_rebound_pct: Optional[float] = None
    def_rebound_pct: Optional[float] = None
    total_rebound_pct: Optional[float] = None


# ------------------------------------------------------------------
# CREATION SCHEMA (INPUT)
# ------------------------------------------------------------------
class TeamGameStatsCreate(TeamGameStatsBase):
    """
    Schema for creating new stats entries.
    Requires linking to existing Game and Teams.
    """
    game_id: int
    team_id: int
    opponent_id: int


# ------------------------------------------------------------------
# RESPONSE SCHEMA (OUTPUT)
# ------------------------------------------------------------------
class TeamGameStatsResponse(TeamGameStatsBase):
    """
    Schema for returning advanced stats.
    Includes nested Team objects for easier consumption.
    """
    id: int
    game_id: int  # We keep the ID for reference
    
    # Nested objects allow the client to see team details immediately
    team: Optional[TeamResponse] = None
    opponent: Optional[TeamResponse] = None

    model_config = ConfigDict(from_attributes=True)
