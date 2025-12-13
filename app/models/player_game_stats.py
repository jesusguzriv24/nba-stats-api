from sqlalchemy import Column, Integer, Float, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class PlayerGameStats(Base):
    """
    Detailed box score and advanced stats for a specific player in a specific game.
    """
    __tablename__ = "player_game_stats"

    # PK
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ------------------------------------------------------------------
    # CONTEXT & RELATIONSHIPS
    # ------------------------------------------------------------------
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True) # Team the player played for in this game
    
    # Metadata
    is_starter = Column(Boolean, default=False) # True if started the game
    minutes = Column(Float, nullable=True)     # Stored as string "34:12" (min:sec) or float if you prefer decimal minutes

    # ------------------------------------------------------------------
    # TRADITIONAL STATS (Counting Stats)
    # ------------------------------------------------------------------
    fg = Column(Integer, default=0)         # Field Goals Made
    fga = Column(Integer, default=0)        # Field Goals Attempted
    fg_pct = Column(Float, nullable=True)   # FG%
    
    fg3 = Column(Integer, default=0)        # 3-Point FG Made (Renamed from '3p' because variables can't start with numbers)
    fg3a = Column(Integer, default=0)       # 3-Point FG Attempted
    fg3_pct = Column(Float, nullable=True)  # 3P%
    
    ft = Column(Integer, default=0)         # Free Throws Made
    fta = Column(Integer, default=0)        # Free Throws Attempted
    ft_pct = Column(Float, nullable=True)   # FT%
    
    orb = Column(Integer, default=0)        # Offensive Rebounds
    drb = Column(Integer, default=0)        # Defensive Rebounds
    trb = Column(Integer, default=0)        # Total Rebounds
    
    ast = Column(Integer, default=0)        # Assists
    stl = Column(Integer, default=0)        # Steals
    blk = Column(Integer, default=0)        # Blocks
    tov = Column(Integer, default=0)        # Turnovers
    pf = Column(Integer, default=0)         # Personal Fouls
    pts = Column(Integer, default=0)        # Points
    
    plus_minus = Column(Integer, nullable=True) # +/-
    game_score = Column(Float, nullable=True)   # GmSc

    # ------------------------------------------------------------------
    # ADVANCED STATS (Efficiency & Rates)
    # ------------------------------------------------------------------
    ts_pct = Column(Float, nullable=True)   # True Shooting %
    efg_pct = Column(Float, nullable=True)  # Effective FG %
    
    fg3a_rate = Column(Float, nullable=True) # 3PAr (3P Attempt Rate)
    ft_rate = Column(Float, nullable=True)   # FTr (Free Throw Rate)
    
    orb_pct = Column(Float, nullable=True)   # ORB%
    drb_pct = Column(Float, nullable=True)   # DRB%
    trb_pct = Column(Float, nullable=True)   # TRB%
    
    ast_pct = Column(Float, nullable=True)   # AST%
    stl_pct = Column(Float, nullable=True)   # STL%
    blk_pct = Column(Float, nullable=True)   # BLK%
    tov_pct = Column(Float, nullable=True)   # TOV%
    
    usg_pct = Column(Float, nullable=True)   # Usage %
    
    off_rating = Column(Float, nullable=True) # ORtg
    def_rating = Column(Float, nullable=True) # DRtg
    
    bpm = Column(Float, nullable=True)        # Box Plus/Minus

    # ------------------------------------------------------------------
    # RELATIONSHIPS (SQLAlchemy)
    # ------------------------------------------------------------------
    game = relationship("Game", back_populates="player_stats")
    player = relationship("Player", back_populates="game_stats")
    team = relationship("Team", foreign_keys=[team_id])
