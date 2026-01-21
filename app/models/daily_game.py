from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class DailyGame(Base):
    """
    Temporary table ('Hot Data') for daily games.
    Populated via scraping and cleared daily.
    """
    __tablename__ = "daily_games"

    # ------------------------------------------------------------------
    # IDENTIFICATION
    # ------------------------------------------------------------------
    id = Column(Integer, autoincrement=True, primary_key=True)

    # ------------------------------------------------------------------
    # DATE & TIME
    # ------------------------------------------------------------------
    # Includes both date and time (e.g., 2026-01-25 18:00:00)
    # This allows for easy countdown calculations on the frontend.
    date = Column(DateTime, nullable=False, index=True)

    # ------------------------------------------------------------------
    # TEAMS (Foreign Keys)
    # ------------------------------------------------------------------
    # References to the 'teams' table for Home and Visitor
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    visitor_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)

    # ------------------------------------------------------------------
    # RELATIONSHIPS
    # ------------------------------------------------------------------
    # Allows accessing the full Team object (e.g., game.home_team.name)
    home_team = relationship("Team", foreign_keys=[home_team_id])
    visitor_team = relationship("Team", foreign_keys=[visitor_team_id])

    def __repr__(self):
        return f"<DailyGame id={self.id} date={self.date}>"
