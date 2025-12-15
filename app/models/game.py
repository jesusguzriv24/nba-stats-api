from sqlalchemy import Column, String, Integer, Date, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum as SQLAlchemyEnum
from enum import Enum as PythonEnum
from app.core.database import Base

class GameType(PythonEnum):
    RS = "RS"
    PI = "PI"
    PO = "PO"

class Game(Base):
    """
    SQLAlchemy model representing an NBA Game.
    """
    __tablename__ = "games"

    # ------------------------------------------------------------------
    # IDENTIFICATION
    # ------------------------------------------------------------------
    id = Column(Integer, autoincrement=True, primary_key=True) 

    # ------------------------------------------------------------------
    # GAME METADATA
    # ------------------------------------------------------------------
    date = Column(Date, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)  # e.g., 2024 for the 2024-25 season
    game_type = Column(SQLAlchemyEnum(GameType), default=GameType.RS, nullable=False)
    status = Column(String, default="Scheduled") # "Scheduled", "Final"

    # ------------------------------------------------------------------
    # TEAMS (Foreign Keys)
    # ------------------------------------------------------------------
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    visitor_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)

    # ------------------------------------------------------------------
    # SCORES (Final & Periods)
    # ------------------------------------------------------------------
    # Final score is kept in its own column for fast, frequent queries
    home_score = Column(Integer, nullable=False)
    visitor_score = Column(Integer, nullable=False)

    # Detailed period scores stored in a flexible JSON array
    # Expected structure: [25, 30, 22, 28, 10] (Q1, Q2, Q3, Q4, OT1...)
    # Using JSONB is recommended for efficient querying within the array if needed
    home_period_scores = Column(JSONB, nullable=True) 
    visitor_period_scores = Column(JSONB, nullable=True)

    # ------------------------------------------------------------------
    # RELATIONSHIPS
    # ------------------------------------------------------------------
    # We explicitly define `foreign_keys` because there are two separate relationships
    # pointing to the same 'teams' table. This resolves ambiguity for SQLAlchemy.
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_games")
    visitor_team = relationship("Team", foreign_keys=[visitor_team_id], back_populates="visitor_games")

    # ------------------------------------------------------------------
    # ADVANCED STATS RELATIONSHIP
    # ------------------------------------------------------------------
    # Allows accessing the advanced stats rows directly from the game object
    # e.g., game.team_stats (returns a list of 2 objects: home stats and visitor stats)
    team_stats = relationship("TeamGameStats", back_populates="game", cascade="all, delete-orphan")
    player_stats = relationship("PlayerGameStats", back_populates="game", cascade="all, delete-orphan")