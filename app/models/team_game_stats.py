from sqlalchemy import Column, Integer, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class TeamGameStats(Base):
    """
    Advanced statistics for a specific team in a specific game.
    One game creates 2 rows in this table (one for home team, one for visitor).
    """
    __tablename__ = "team_game_stats"

    # PK
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ------------------------------------------------------------------
    # RELATIONSHIPS (Context)
    # ------------------------------------------------------------------
    # CORRECCIÓN: Usamos Integer para coincidir con Game.id
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True) 
    
    # CORRECCIÓN: Usamos Integer para coincidir con Team.id
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True) 
    
    # Metadata context
    is_home_game = Column(Boolean, nullable=False) # True if this row is for the home team
    opponent_id = Column(Integer, ForeignKey("teams.id"), nullable=False) # Who did they play against?

    # ------------------------------------------------------------------
    # FOUR FACTORS (Dean Oliver) & ADVANCED STATS
    # ------------------------------------------------------------------
    pace = Column(Float, nullable=True)             # Possessions per 48 min
    offensive_rating = Column(Float, nullable=True) # Points scored per 100 poss
    defensive_rating = Column(Float, nullable=True) # Points allowed per 100 poss
    
    # Shooting
    effective_fg_pct = Column(Float, nullable=True) # eFG%
    true_shooting_pct = Column(Float, nullable=True) # TS%
    ft_per_fga = Column(Float, nullable=True)       # FT Rate (FT/FGA)

    # Ball Control
    turnover_pct = Column(Float, nullable=True)     # TOV%
    assist_pct = Column(Float, nullable=True)       # AST%

    # Rebounding
    off_rebound_pct = Column(Float, nullable=True)   # ORB%
    def_rebound_pct = Column(Float, nullable=True)   # DRB%
    total_rebound_pct = Column(Float, nullable=True) # TRB%

    # ------------------------------------------------------------------
    # RELATIONSHIPS (SQLAlchemy)
    # ------------------------------------------------------------------
    # back_populates allows access from the Game object (game.team_stats)
    game = relationship("Game", back_populates="team_stats")
    
    team = relationship("Team", foreign_keys=[team_id])
    opponent = relationship("Team", foreign_keys=[opponent_id])
