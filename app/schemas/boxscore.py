# app/schemas/boxscore.py
from typing import List
from pydantic import BaseModel

from app.schemas.game import GameResponse
from app.schemas.team_game_stats import TeamGameStatsResponse
from app.schemas.player_game_stats import PlayerGameStatsResponse

class GameBoxscoreResponse(BaseModel):
    game: GameResponse
    team_stats: List[TeamGameStatsResponse]
    player_stats: List[PlayerGameStatsResponse]
