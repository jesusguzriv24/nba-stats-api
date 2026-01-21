from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


# ------------------------------------------------------------------
# SHARED BASE SCHEMA
# ------------------------------------------------------------------
class PlayerPropBase(BaseModel):
    """
    Shared properties for PlayerProp schemas.
    """
    player_id: int
    player_team_id: int
    opp_team_id: int
    daily_game_id: Optional[int] = None
    prop_type: str
    line: float
    over_odds: Optional[int] = None
    under_odds: Optional[int] = None


# ------------------------------------------------------------------
# CREATION SCHEMA (INPUT)
# ------------------------------------------------------------------
class PlayerPropCreate(PlayerPropBase):
    """
    Schema for creating a new player prop record.
    """
    pass


# ------------------------------------------------------------------
# RESPONSE SCHEMA (OUTPUT)
# ------------------------------------------------------------------
class PlayerPropResponse(PlayerPropBase):
    """
    Schema for returning player prop data.
    Includes the DB-generated ID and updated_at timestamp.
    """
    id: int
    updated_at: datetime

    # Configuration to allow Pydantic to read data from SQLAlchemy models
    model_config = ConfigDict(from_attributes=True)
