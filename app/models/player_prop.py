from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class PlayerProp(Base):
    """
    SQLAlchemy model representing a player betting line (prop).
    Linked to a specific player, teams, and optionally a daily game.
    """
    __tablename__ = "player_props"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ------------------------------------------------------------------
    # IDENTIFICATION & RELATIONSHIPS (Foreign Keys)
    # ------------------------------------------------------------------
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    player_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    opp_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    daily_game_id = Column(Integer, ForeignKey("daily_games.id", ondelete="CASCADE"), nullable=True)

    # ------------------------------------------------------------------
    # PROP DATA
    # ------------------------------------------------------------------
    prop_type = Column(String(50), nullable=False, index=True) # e.g., "Points", "Rebounds"
    line = Column(Float, nullable=False)                       # e.g., 24.5
    
    over_odds = Column(Integer, nullable=True)                 # e.g., -110
    under_odds = Column(Integer, nullable=True)                # e.g., +105

    # ------------------------------------------------------------------
    # METADATA
    # ------------------------------------------------------------------
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ------------------------------------------------------------------
    # RELATIONSHIPS
    # ------------------------------------------------------------------
    player = relationship("Player")
    player_team = relationship("Team", foreign_keys=[player_team_id])
    opp_team = relationship("Team", foreign_keys=[opp_team_id])
    daily_game = relationship("DailyGame")

    def __repr__(self):
        return f"<PlayerProp id={self.id} player_id={self.player_id} type={self.prop_type} line={self.line}>"
