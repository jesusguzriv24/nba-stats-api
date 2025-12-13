# app/schemas/datasets.py
from datetime import date
from pydantic import BaseModel
from typing import Optional


class PlayerGameDatasetRow(BaseModel):
    game_id: int
    game_date: date
    season: int
    is_playoffs: bool

    team_id: int
    opponent_id: int
    is_home_game: bool

    player_id: int

    # Boxscore core
    minutes: float
    pts: int
    trb: int
    ast: int
    stl: int
    blk: int
    tov: int
    pf: int
    fg: int
    fga: int
    fg_pct: Optional[float]
    fg3: int
    fg3a: int
    fg3_pct: Optional[float]
    ft: int
    fta: int
    ft_pct: Optional[float]

    # Advanced
    ts_pct: Optional[float]
    efg_pct: Optional[float]
    usg_pct: Optional[float]
    off_rating: Optional[float]
    def_rating: Optional[float]

    plus_minus: Optional[int]
    game_score: Optional[float]


class TeamGameDatasetRow(BaseModel):
    game_id: int
    game_date: date
    season: int
    is_playoffs: bool

    team_id: int
    opponent_id: int
    is_home_game: bool

    # Score context
    team_score: int
    opponent_score: int

    # Advanced team stats
    pace: Optional[float]
    offensive_rating: Optional[float]
    defensive_rating: Optional[float]
    effective_fg_pct: Optional[float]
    true_shooting_pct: Optional[float]
    ft_per_fga: Optional[float]
    turnover_pct: Optional[float]
    assist_pct: Optional[float]
    off_rebound_pct: Optional[float]
    def_rebound_pct: Optional[float]
    total_rebound_pct: Optional[float]
