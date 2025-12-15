from typing import List, Optional
from datetime import date
from enum import Enum as PythonEnum
from pydantic import BaseModel, ConfigDict
from app.schemas.team import TeamResponse

class GameType(PythonEnum):
    RS = "RS"
    PI = "PI"
    PO = "PO"

# ------------------------------------------------------------------
# SHARED BASE SCHEMA
# ------------------------------------------------------------------
class GameBase(BaseModel):
    """
    Shared properties for Game schemas.
    """
    date: date
    season: int
    game_type: GameType = GameType.RS  # Default to Regular Season
    status: str = "Scheduled"  # Nuevo campo: "Scheduled", "Final", "Live"
    
    # Scores
    # Optional/Default 0 because scheduled games have no score yet
    home_score: Optional[int] = 0
    visitor_score: Optional[int] = 0
    
    # Period scores as lists of integers (e.g., [25, 30, 24, 28])
    home_period_scores: Optional[List[int]] = None
    visitor_period_scores: Optional[List[int]] = None


# ------------------------------------------------------------------
# CREATION SCHEMA (INPUT)
# ------------------------------------------------------------------
class GameCreate(GameBase):
    """
    Schema for creating a new game.
    We exclude 'id' because it's auto-generated (autoincrement=True).
    We only need the team FKs.
    """
    home_team_id: int
    visitor_team_id: int


# ------------------------------------------------------------------
# RESPONSE SCHEMA (OUTPUT)
# ------------------------------------------------------------------
class GameResponse(GameBase):
    """
    Schema for returning game data.
    Includes the DB-generated integer ID and nested Team objects.
    """
    id: int  # Changed to int to match your Integer PK
    
    # Nested team objects (instead of just IDs)
    home_team: Optional[TeamResponse] = None
    visitor_team: Optional[TeamResponse] = None

    model_config = ConfigDict(from_attributes=True)
