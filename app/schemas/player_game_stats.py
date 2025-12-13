from typing import Optional, Union
from pydantic import BaseModel, ConfigDict
from app.schemas.player import PlayerResponse
from app.schemas.team import TeamResponse


# ------------------------------------------------------------------
# SHARED BASE SCHEMA
# ------------------------------------------------------------------
class PlayerGameStatsBase(BaseModel):
    """
    Shared properties for Player Game Stats.
    Includes Minutes, Traditional Stats, and Advanced Stats.
    """
    is_starter: bool = False
    minutes: Optional[Union[str, float]] = None  # "34:12" or 34.2

    # --- Traditional Stats ---
    fg: int = 0
    fga: int = 0
    fg_pct: Optional[float] = None
    
    fg3: int = 0
    fg3a: int = 0
    fg3_pct: Optional[float] = None
    
    ft: int = 0
    fta: int = 0
    ft_pct: Optional[float] = None
    
    orb: int = 0
    drb: int = 0
    trb: int = 0
    
    ast: int = 0
    stl: int = 0
    blk: int = 0
    tov: int = 0
    pf: int = 0
    pts: int = 0
    
    plus_minus: Optional[int] = None
    game_score: Optional[float] = None

    # --- Advanced Stats ---
    ts_pct: Optional[float] = None
    efg_pct: Optional[float] = None
    fg3a_rate: Optional[float] = None
    ft_rate: Optional[float] = None
    
    orb_pct: Optional[float] = None
    drb_pct: Optional[float] = None
    trb_pct: Optional[float] = None
    
    ast_pct: Optional[float] = None
    stl_pct: Optional[float] = None
    blk_pct: Optional[float] = None
    tov_pct: Optional[float] = None
    
    usg_pct: Optional[float] = None
    off_rating: Optional[float] = None
    def_rating: Optional[float] = None
    bpm: Optional[float] = None


# ------------------------------------------------------------------
# CREATION SCHEMA (INPUT)
# ------------------------------------------------------------------
class PlayerGameStatsCreate(PlayerGameStatsBase):
    """
    Schema for creating a new stat line.
    Requires linking IDs.
    """
    game_id: int
    player_id: int
    team_id: int


# ------------------------------------------------------------------
# RESPONSE SCHEMA (OUTPUT)
# ------------------------------------------------------------------
class PlayerGameStatsResponse(PlayerGameStatsBase):
    """
    Schema for returning player stats.
    Includes nested Player and Team objects for rich UI display.
    """
    id: int
    game_id: int
    
    # Nested objects
    player: Optional[PlayerResponse] = None
    team: Optional[TeamResponse] = None

    model_config = ConfigDict(from_attributes=True)
