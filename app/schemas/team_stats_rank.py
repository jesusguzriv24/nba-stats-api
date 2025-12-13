# app/schemas/team_stats_rank.py
from pydantic import BaseModel

class TeamStatsRank(BaseModel):
    team_id: int
    pace: float | None
    offensive_rating: float | None
    defensive_rating: float | None
    effective_fg_pct: float | None
    true_shooting_pct: float | None
    ft_per_fga: float | None
    turnover_pct: float | None
    assist_pct: float | None
    off_rebound_pct: float | None
    def_rebound_pct: float | None
    total_rebound_pct: float | None
