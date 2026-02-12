import asyncio
import os
from sqlalchemy import text
from app.core.database import engine

async def apply_indexes():
    """
    Manually apply missing indexes to an existing database.
    This is necessary since SQLAlchemy's create_all() doesn't add indexes to existing tables.
    """
    print("Connecting to database to apply indexes...")
    
    indexes = [
        # Games table
        "CREATE INDEX IF NOT EXISTS idx_games_game_type ON games (game_type)",
        "CREATE INDEX IF NOT EXISTS idx_games_status ON games (status)",
        
        # Team Game Stats table
        "CREATE INDEX IF NOT EXISTS idx_team_game_stats_opponent_id ON team_game_stats (opponent_id)",
        "CREATE INDEX IF NOT EXISTS idx_team_game_stats_is_home_game ON team_game_stats (is_home_game)",
        
        # API Keys table
        "CREATE INDEX IF NOT EXISTS idx_api_keys_last_chars ON api_keys (last_chars)",
    ]
    
    async with engine.begin() as conn:
        for index_sql in indexes:
            try:
                print(f"Executing: {index_sql}")
                await conn.execute(text(index_sql))
            except Exception as e:
                print(f"Error applying index: {e}")
                
    print("Index application complete.")

if __name__ == "__main__":
    asyncio.run(apply_indexes())
