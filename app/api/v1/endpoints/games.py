from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.game import Game, GameType
from app.models.team_game_stats import TeamGameStats
from app.models.player_game_stats import PlayerGameStats
from app.models.player import Player
from app.schemas.game import GameResponse
from app.schemas.team_game_stats import TeamGameStatsResponse
from app.schemas.player_game_stats import PlayerGameStatsResponse
from app.schemas.boxscore import GameBoxscoreResponse

from app.core.dependencies import get_current_user
from app.models.user import User

from app.core.rate_limit import limiter, get_dynamic_rate_limit

router = APIRouter()


@router.get("/", response_model=List[GameResponse])
@limiter.limit(get_dynamic_rate_limit)
async def list_games(
    request: Request,
    season: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    home_team_id: Optional[int] = Query(None),
    visitor_team_id: Optional[int] = Query(None),
    game_type: Optional[GameType] = Query(
        None,
        description="Game type filter: RS (Regular Season), PI (Play-In), PO (Playoffs)",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Game)

    if season is not None:
        stmt = stmt.where(Game.season == season)

    if game_type is not None:
        stmt = stmt.where(Game.game_type == game_type)

    if home_team_id is not None:
        stmt = stmt.where(Game.home_team_id == home_team_id)

    if visitor_team_id is not None:
        stmt = stmt.where(Game.visitor_team_id == visitor_team_id)

    if from_date:
        try:
            d = datetime.fromisoformat(from_date).date()
            stmt = stmt.where(Game.date >= d)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid from_date format, expected YYYY-MM-DD",
            )

    if to_date:
        try:
            d = datetime.fromisoformat(to_date).date()
            stmt = stmt.where(Game.date <= d)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid to_date format, expected YYYY-MM-DD",
            )

    stmt = (
        stmt.order_by(Game.date.desc())
        .offset(skip)
        .limit(limit)
        .options(
            selectinload(Game.home_team),
            selectinload(Game.visitor_team),
        )
    )

    res = await db.execute(stmt)
    games = res.scalars().all()

    if not games:
        raise HTTPException(
            status_code=404,
            detail="No games found with the given filters",
        )

    return games


@router.get("/{game_id}", response_model=GameResponse)
@limiter.limit(get_dynamic_rate_limit)
async def get_game(
    request: Request,
    game_id: int, 
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):

    res = await db.execute(
        select(Game)
        .options(selectinload(Game.home_team), selectinload(Game.visitor_team))
        .where(Game.id == game_id)
    )
    game = res.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.get("/{game_id}/team-stats", response_model=List[TeamGameStatsResponse])
@limiter.limit(get_dynamic_rate_limit)
async def get_game_team_stats(
    request: Request,
    game_id: int, 
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):

    res = await db.execute(
        select(TeamGameStats)
        .options(selectinload(TeamGameStats.team), selectinload(TeamGameStats.opponent))
        .where(TeamGameStats.game_id == game_id)
    )
    stats = res.scalars().all()
    if not stats:
        raise HTTPException(status_code=404, detail="Team stats not found for this game")
    return stats


@router.get("/{game_id}/player-stats", response_model=List[PlayerGameStatsResponse])
@limiter.limit(get_dynamic_rate_limit)
async def get_game_player_stats(
    request: Request,
    game_id: int, 
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):

    res = await db.execute(
        select(PlayerGameStats)
        .options(
            selectinload(PlayerGameStats.player).selectinload(Player.team),
            selectinload(PlayerGameStats.team)
        )
        .where(PlayerGameStats.game_id == game_id)
    )
    stats = res.scalars().all()
    if not stats:
        raise HTTPException(status_code=404, detail="Player stats not found for this game")
    return stats


@router.get("/{game_id}/boxscore", response_model=GameBoxscoreResponse)
@limiter.limit(get_dynamic_rate_limit)
async def get_game_boxscore(
    request: Request,
    game_id: int, 
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):

    # Game
    res_game = await db.execute(
        select(Game)
        .options(selectinload(Game.home_team), selectinload(Game.visitor_team))
        .where(Game.id == game_id)
    )
    game = res_game.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Team stats (two rows: home and visitor)
    res_team_stats = await db.execute(
        select(TeamGameStats)
        .options(selectinload(TeamGameStats.team), selectinload(TeamGameStats.opponent))
        .where(TeamGameStats.game_id == game_id)
    )
    team_stats = res_team_stats.scalars().all()

    # Player stats (one row per player)
    res_player_stats = await db.execute(
        select(PlayerGameStats)
        .options(
            selectinload(PlayerGameStats.player).selectinload(Player.team),
            selectinload(PlayerGameStats.team)
        )
        .where(PlayerGameStats.game_id == game_id)
    )
    player_stats = res_player_stats.scalars().all()

    if not team_stats and not player_stats:
        raise HTTPException(status_code=404, detail="No boxscore stats found for this game")

    return GameBoxscoreResponse(
        game=game,
        team_stats=team_stats,
        player_stats=player_stats,
    )
