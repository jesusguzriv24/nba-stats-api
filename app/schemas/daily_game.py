from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.team import TeamResponse


# ------------------------------------------------------------------
# SHARED BASE SCHEMA
# ------------------------------------------------------------------
class DailyGameBase(BaseModel):
    """
    Shared properties for DailyGame schemas.
    """
    date: datetime
    home_team_id: int
    visitor_team_id: int


# ------------------------------------------------------------------
# CREATION SCHEMA (INPUT)
# ------------------------------------------------------------------
class DailyGameCreate(DailyGameBase):
    """
    Schema for creating a new daily game record.
    """
    pass


# ------------------------------------------------------------------
# UPDATE SCHEMA (INPUT)
# ------------------------------------------------------------------
class DailyGameUpdate(BaseModel):
    """
    Schema for updating an existing daily game record.
    All fields are optional.
    """
    date: Optional[datetime] = None
    home_team_id: Optional[int] = None
    visitor_team_id: Optional[int] = None


# ------------------------------------------------------------------
# RESPONSE SCHEMA (OUTPUT)
# ------------------------------------------------------------------
class DailyGameResponse(DailyGameBase):
    """
    Schema for returning daily game data.
    Includes the database ID and nested team information.
    """
    id: int
    home_team: TeamResponse
    visitor_team: TeamResponse

    # Configuration to allow Pydantic to read data from SQLAlchemy models
    model_config = ConfigDict(from_attributes=True)
