from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Player(Base):
    """
    SQLAlchemy model representing an NBA player.
    """
    __tablename__ = "players"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ------------------------------------------------------------------
    # PERSONAL INFORMATION
    # ------------------------------------------------------------------
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    country = Column(String, nullable=True)     # e.g., "USA"
    college = Column(String, nullable=True)     # e.g., "Davidson"
    image_url = Column(String, nullable=True)   # e.g. "https://..."

    # ------------------------------------------------------------------
    # PHYSICAL ATTRIBUTES & GAME INFO
    # ------------------------------------------------------------------
    position = Column(String, nullable=True)    # e.g., "G", "F"
    height = Column(String, nullable=True)      # e.g., "6-2"
    weight = Column(Integer, nullable=True)      # e.g., "185"
    jersey_number = Column(Integer, nullable=True) # e.g., "30" 

    # ------------------------------------------------------------------
    # DRAFT INFORMATION
    # ------------------------------------------------------------------
    draft_year = Column(Integer, nullable=True)
    draft_round = Column(Integer, nullable=True)
    draft_number = Column(Integer, nullable=True)

    # ------------------------------------------------------------------
    # RELATIONSHIPS
    # ------------------------------------------------------------------
    # Foreign key linking to the 'teams' table
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    # Relationship to Team
    team = relationship("Team", back_populates="players")

    # Relationship to PlayerGameStats
    game_stats = relationship("PlayerGameStats", back_populates="player")
