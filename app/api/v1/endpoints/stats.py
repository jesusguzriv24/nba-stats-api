# app/api/v1/routes/stats.py
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.team_game_stats import TeamGameStats
from app.models.game import Game, GameType
from app.schemas.team_stats_rank import TeamStatsRank

router = APIRouter()


@router.get("/teams", response_model=List[TeamStatsRank])
async def team_rankings(
    season: int = Query(...),
    game_type: Optional[GameType] = Query(
        None,
        description="Game type filter: RS (Regular Season), PI (Play-In), PO (Playoffs)",
    ),
    sort_by: str = Query("offensive_rating"),
    limit: int = Query(30, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    sort_map = {
        "offensive_rating": func.avg(TeamGameStats.offensive_rating),
        "defensive_rating": func.avg(TeamGameStats.defensive_rating),
        "pace": func.avg(TeamGameStats.pace),
    }
    sort_column = sort_map.get(sort_by, sort_map["offensive_rating"])

    stmt = (
        select(
            TeamGameStats.team_id.label("team_id"),
            func.avg(TeamGameStats.pace).label("pace"),
            func.avg(TeamGameStats.offensive_rating).label("offensive_rating"),
            func.avg(TeamGameStats.defensive_rating).label("defensive_rating"),
            func.avg(TeamGameStats.effective_fg_pct).label("effective_fg_pct"),
            func.avg(TeamGameStats.true_shooting_pct).label("true_shooting_pct"),
            func.avg(TeamGameStats.ft_per_fga).label("ft_per_fga"),
            func.avg(TeamGameStats.turnover_pct).label("turnover_pct"),
            func.avg(TeamGameStats.assist_pct).label("assist_pct"),
            func.avg(TeamGameStats.off_rebound_pct).label("off_rebound_pct"),
            func.avg(TeamGameStats.def_rebound_pct).label("def_rebound_pct"),
            func.avg(TeamGameStats.total_rebound_pct).label("total_rebound_pct"),
        )
        .join(Game, Game.id == TeamGameStats.game_id)
        .where(Game.season == season)
    )

    if game_type is not None:
        stmt = stmt.where(Game.game_type == game_type)

    stmt = (
        stmt.group_by(TeamGameStats.team_id)
        .order_by(sort_column.desc())
        .limit(limit)
    )

    res = await db.execute(stmt)
    rows = res.all()

    return [TeamStatsRank(**row._mapping) for row in rows]