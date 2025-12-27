from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.team import Team
from app.models.game import Game, GameType
from app.schemas.team import TeamResponse
from app.schemas.game import GameResponse

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=List[TeamResponse])
async def list_teams(
    request: Request,
    conference: Optional[str] = Query(None),
    division: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Team)
    if conference:
        stmt = stmt.where(Team.conference.ilike(conference))
    if division:
        stmt = stmt.where(Team.division.ilike(division))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Team.full_name.ilike(pattern),
                Team.city.ilike(pattern),
                Team.name.ilike(pattern),
                Team.abbreviation.ilike(pattern),
            )
        )
    stmt = stmt.offset(skip).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    request: Request,
    team_id: int, 
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):

    res = await db.execute(select(Team).where(Team.id == team_id))
    team = res.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.get("/{team_id}/games", response_model=List[GameResponse])
async def get_team_games(
    request: Request,
    team_id: int,
    season: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    game_type: Optional[GameType] = Query(
        None,
        description="Game type filter: RS (Regular Season), PI (Play-In), PO (Playoffs)",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Game).where(
        (Game.home_team_id == team_id) | (Game.visitor_team_id == team_id)
    )

    if season is not None:
        stmt = stmt.where(Game.season == season)

    if game_type is not None:
        stmt = stmt.where(Game.game_type == game_type)

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
            detail="No games found for this team with the given filters",
        )

    return games
