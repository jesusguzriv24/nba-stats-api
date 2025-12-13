from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.team import TeamResponse


# ------------------------------------------------------------------
# SHARED BASE SCHEMA
# ------------------------------------------------------------------
class PlayerBase(BaseModel):
    """
    Shared properties for Player schemas.
    """
    first_name: str
    last_name: str
    position: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[int] = None
    jersey_number: Optional[int] = None
    college: Optional[str] = None
    country: Optional[str] = None
    draft_year: Optional[int] = None
    draft_round: Optional[int] = None
    draft_number: Optional[int] = None


# ------------------------------------------------------------------
# CREATION SCHEMA (INPUT)
# ------------------------------------------------------------------
class PlayerCreate(PlayerBase):
    """
    Schema for creating a new player.
    We use 'team_id' to link the player to an existing team.
    """
    team_id: Optional[int] = None


# ------------------------------------------------------------------
# RESPONSE SCHEMA (OUTPUT)
# ------------------------------------------------------------------
class PlayerResponse(PlayerBase):
    """
    Schema for returning player data.
    Includes the nested Team object to match your JSON example.
    """
    id: int
    team: Optional[TeamResponse] = None

    model_config = ConfigDict(from_attributes=True)
