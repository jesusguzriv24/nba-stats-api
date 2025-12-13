from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base

class Team(Base):
    """
    SQLAlchemy model representing an NBA team.
    """
    __tablename__ = "teams"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ------------------------------------------------------------------
    # LEAGUE CLASSIFICATION
    # ------------------------------------------------------------------
    conference = Column(String, nullable=False)   # e.g., "East", "West"
    division = Column(String, nullable=False)     # e.g., "Atlantic", "Pacific"

    # ------------------------------------------------------------------
    # LOCATION DETAILS
    # ------------------------------------------------------------------
    city = Column(String, nullable=False)         # e.g., "Boston"

    # ------------------------------------------------------------------
    # IDENTITY
    # ------------------------------------------------------------------
    name = Column(String, nullable=False)         # e.g., "Celtics"
    
    # Stores the complete official name (City + Name)
    full_name = Column(String, nullable=False)    # e.g., "Boston Celtics"
    
    # Indexed for faster lookup by standard tricode abbreviation
    abbreviation = Column(String, nullable=False, index=True) # e.g., "BOS"

    # ------------------------------------------------------------------
    # RELATIONSHIPS
    # ------------------------------------------------------------------
    # 1. Relation to Players
    players = relationship("Player", back_populates="team")

    # 2. Relation to Home Games
    home_games = relationship("Game", back_populates="home_team", foreign_keys="[Game.home_team_id]")

    # 3. Relation to Visitor Games
    visitor_games = relationship("Game", back_populates="visitor_team", foreign_keys="[Game.visitor_team_id]")
