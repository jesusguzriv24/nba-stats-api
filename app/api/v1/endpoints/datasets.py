# app/api/v1/routes/datasets.py
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.game import Game, GameType
from app.models.player_game_stats import PlayerGameStats
from app.models.team_game_stats import TeamGameStats
from app.schemas.datasets import PlayerGameDatasetRow, TeamGameDatasetRow

from app.core.dependencies import get_current_user
from app.models.user import User

from app.core.rate_limit import limiter, get_dynamic_rate_limit

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /api/v1/datasets/player-game-stats
# ---------------------------------------------------------------------------
@router.get("/player-game-stats", response_model=List[PlayerGameDatasetRow])
@limiter.limit(get_dynamic_rate_limit)
async def get_player_game_dataset(
    request: Request,
    season: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    game_type: Optional[GameType] = Query(
        None,
        description="Game type filter: RS (Regular Season), PI (Play-In), PO (Playoffs)",
    ),
    team_id: Optional[int] = Query(None),
    player_id: Optional[int] = Query(None),
    limit: int = Query(10_000, ge=1, le=100_000),
    skip: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Flat dataset of player game stats, joined with game + team context.

    Designed for ML/analytics consumption from pandas.
    """

    # Base join: PlayerGameStats + Game
    stmt = (
        select(
            PlayerGameStats.game_id,
            Game.date.label("game_date"),
            Game.season,
            Game.game_type,  
            PlayerGameStats.team_id,
            PlayerGameStats.player_id,
            PlayerGameStats.is_starter,
            PlayerGameStats.minutes,
            PlayerGameStats.pts,
            PlayerGameStats.trb,
            PlayerGameStats.ast,
            PlayerGameStats.stl,
            PlayerGameStats.blk,
            PlayerGameStats.tov,
            PlayerGameStats.pf,
            PlayerGameStats.fg,
            PlayerGameStats.fga,
            PlayerGameStats.fg_pct,
            PlayerGameStats.fg3,
            PlayerGameStats.fg3a,
            PlayerGameStats.fg3_pct,
            PlayerGameStats.ft,
            PlayerGameStats.fta,
            PlayerGameStats.ft_pct,
            PlayerGameStats.ts_pct,
            PlayerGameStats.efg_pct,
            PlayerGameStats.usg_pct,
            PlayerGameStats.off_rating,
            PlayerGameStats.def_rating,
            PlayerGameStats.plus_minus,
            PlayerGameStats.game_score,
            # We infer opponent and home/away using Game
            Game.home_team_id,
            Game.visitor_team_id,
        )
        .join(Game, Game.id == PlayerGameStats.game_id)
    )

    # Filters
    if season is not None:
        stmt = stmt.where(Game.season == season)

    if game_type is not None:
        stmt = stmt.where(Game.game_type == game_type)

    if from_date:
        try:
            d = datetime.fromisoformat(from_date).date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid from_date format, expected YYYY-MM-DD",
            )
        stmt = stmt.where(Game.date >= d)

    if to_date:
        try:
            d = datetime.fromisoformat(to_date).date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid to_date format, expected YYYY-MM-DD",
            )
        stmt = stmt.where(Game.date <= d)

    if team_id is not None:
        stmt = stmt.where(PlayerGameStats.team_id == team_id)

    if player_id is not None:
        stmt = stmt.where(PlayerGameStats.player_id == player_id)

    stmt = (
        stmt.order_by(Game.date.desc(), PlayerGameStats.game_id.desc())
        .offset(skip)
        .limit(limit)
    )

    res = await db.execute(stmt)
    rows = res.all()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No player game stats found for given filters",
        )

    out: List[PlayerGameDatasetRow] = []

    for r in rows:
        # Determine opponent_id and home/away from game context
        if r.team_id == r.home_team_id:
            opponent_id = r.visitor_team_id
            is_home_game = True
        else:
            opponent_id = r.home_team_id
            is_home_game = False

        out.append(
            PlayerGameDatasetRow(
                game_id=r.game_id,
                game_date=r.game_date,
                season=r.season,
                game_type=r.game_type, 
                team_id=r.team_id,
                opponent_id=opponent_id,
                is_home_game=is_home_game,
                player_id=r.player_id,
                minutes=r.minutes or 0.0,
                pts=r.pts,
                trb=r.trb,
                ast=r.ast,
                stl=r.stl,
                blk=r.blk,
                tov=r.tov,
                pf=r.pf,
                fg=r.fg,
                fga=r.fga,
                fg_pct=r.fg_pct,
                fg3=r.fg3,
                fg3a=r.fg3a,
                fg3_pct=r.fg3_pct,
                ft=r.ft,
                fta=r.fta,
                ft_pct=r.ft_pct,
                ts_pct=r.ts_pct,
                efg_pct=r.efg_pct,
                usg_pct=r.usg_pct,
                off_rating=r.off_rating,
                def_rating=r.def_rating,
                plus_minus=r.plus_minus,
                game_score=r.game_score,
            )
        )

    return out


# ---------------------------------------------------------------------------
# GET /api/v1/datasets/team-game-stats
# ---------------------------------------------------------------------------
@router.get("/team-game-stats", response_model=List[TeamGameDatasetRow])
@limiter.limit(get_dynamic_rate_limit)
async def get_team_game_dataset(
    request: Request,
    season: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    game_type: Optional[GameType] = Query(
        None,
        description="Game type filter: RS (Regular Season), PI (Play-In), PO (Playoffs)",
    ),
    team_id: Optional[int] = Query(None),
    limit: int = Query(10_000, ge=1, le=100_000),
    skip: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Flat dataset of team game stats (Four Factors, efficiency, scoreboard).

    Designed for ML/analytics consumption from pandas.
    """

    stmt = (
        select(
            TeamGameStats.game_id,
            Game.date.label("game_date"),
            Game.season,
            Game.game_type,  
            TeamGameStats.team_id,
            TeamGameStats.opponent_id,
            TeamGameStats.is_home_game,
            # Scoreboard context
            Game.home_team_id,
            Game.visitor_team_id,
            Game.home_score,
            Game.visitor_score,
            # Advanced team stats
            TeamGameStats.pace,
            TeamGameStats.offensive_rating,
            TeamGameStats.defensive_rating,
            TeamGameStats.effective_fg_pct,
            TeamGameStats.true_shooting_pct,
            TeamGameStats.ft_per_fga,
            TeamGameStats.turnover_pct,
            TeamGameStats.assist_pct,
            TeamGameStats.off_rebound_pct,
            TeamGameStats.def_rebound_pct,
            TeamGameStats.total_rebound_pct,
        )
        .join(Game, Game.id == TeamGameStats.game_id)
    )

    # Filters
    if season is not None:
        stmt = stmt.where(Game.season == season)

    if game_type is not None:
        stmt = stmt.where(Game.game_type == game_type)

    if from_date:
        try:
            d = datetime.fromisoformat(from_date).date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid from_date format, expected YYYY-MM-DD",
            )
        stmt = stmt.where(Game.date >= d)

    if to_date:
        try:
            d = datetime.fromisoformat(to_date).date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid to_date format, expected YYYY-MM-DD",
            )
        stmt = stmt.where(Game.date <= d)

    if team_id is not None:
        stmt = stmt.where(TeamGameStats.team_id == team_id)

    stmt = (
        stmt.order_by(Game.date.desc(), TeamGameStats.game_id.desc())
        .offset(skip)
        .limit(limit)
    )

    res = await db.execute(stmt)
    rows = res.all()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No team game stats found for given filters",
        )

    out: List[TeamGameDatasetRow] = []

    for r in rows:
        # Derive team_score / opponent_score from Game + is_home_game
        if r.team_id == r.home_team_id:
            team_score = r.home_score
            opponent_score = r.visitor_score
        else:
            team_score = r.visitor_score
            opponent_score = r.home_score

        out.append(
            TeamGameDatasetRow(
                game_id=r.game_id,
                game_date=r.game_date,
                season=r.season,
                game_type=r.game_type, 
                team_id=r.team_id,
                opponent_id=r.opponent_id,
                is_home_game=r.is_home_game,
                team_score=team_score,
                opponent_score=opponent_score,
                pace=r.pace,
                offensive_rating=r.offensive_rating,
                defensive_rating=r.defensive_rating,
                effective_fg_pct=r.effective_fg_pct,
                true_shooting_pct=r.true_shooting_pct,
                ft_per_fga=r.ft_per_fga,
                turnover_pct=r.turnover_pct,
                assist_pct=r.assist_pct,
                off_rebound_pct=r.off_rebound_pct,
                def_rebound_pct=r.def_rebound_pct,
                total_rebound_pct=r.total_rebound_pct,
            )
        )

    return out
