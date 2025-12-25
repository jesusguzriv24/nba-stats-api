# app/api/v1/router.py
from fastapi import APIRouter

from app.api.v1.endpoints import teams, players, games, stats, datasets, webhooks, users

api_v1_router = APIRouter()
api_v1_router.include_router(teams.router, prefix="/teams", tags=["teams"])
api_v1_router.include_router(players.router, prefix="/players", tags=["players"])
api_v1_router.include_router(games.router, prefix="/games", tags=["games"])
api_v1_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_v1_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_v1_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"]) 