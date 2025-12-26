from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.player import Player
from app.models.player_game_stats import PlayerGameStats
from app.models.game import Game, GameType
from app.schemas.player import PlayerResponse
from app.schemas.player_game_stats import PlayerGameStatsResponse

from app.core.dependencies import get_current_user
from app.models.user import User

from app.core.rate_limit import limiter, get_rate_limit_for_user

router = APIRouter()


@router.get("/", response_model=List[PlayerResponse])
@limiter.limit(get_rate_limit_for_user)
async def list_players(
    request: Request,
    team_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Player)
    if team_id is not None:
        stmt = stmt.where(Player.team_id == team_id)
    if position:
        stmt = stmt.where(Player.position.ilike(position))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            (Player.first_name + " " + Player.last_name).ilike(pattern)
        )
    stmt = stmt.offset(skip).limit(limit)
    stmt = stmt.options(selectinload(Player.team))
    res = await db.execute(stmt)
    players = res.scalars().all()
    if not players:
        raise HTTPException(status_code=404, detail="No players found with the given filters")
    return players


@router.get("/{player_id}", response_model=PlayerResponse)
@limiter.limit(get_rate_limit_for_user)
async def get_player(
    request: Request,
    player_id: int, 
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):

    res = await db.execute(
        select(Player)
        .options(selectinload(Player.team))
        .where(Player.id == player_id)
    )
    player = res.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/{player_id}/games", response_model=List[PlayerGameStatsResponse])
@limiter.limit(get_rate_limit_for_user)
async def get_player_games(
    request: Request,
    player_id: int,
    season: Optional[int] = Query(None),
    game_type: Optional[GameType] = Query(
        None,
        description="Game type filter: RS (Regular Season), PI (Play-In), PO (Playoffs)",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    stmt = select(PlayerGameStats).where(PlayerGameStats.player_id == player_id)

    if season is not None or game_type is not None:
        stmt = stmt.join(Game, Game.id == PlayerGameStats.game_id)

        if season is not None:
            stmt = stmt.where(Game.season == season)

        if game_type is not None:
            stmt = stmt.where(Game.game_type == game_type)

    stmt = (
        stmt.order_by(PlayerGameStats.game_id.desc())
        .offset(skip)
        .limit(limit)
        .options(
            selectinload(PlayerGameStats.player).selectinload(Player.team),
            selectinload(PlayerGameStats.team),
        )
    )

    res = await db.execute(stmt)
    stats = res.scalars().all()

    if not stats:
        raise HTTPException(
            status_code=404,
            detail="No player stats found for this player with the given filters",
        )

    return stats
