import os
import csv
import asyncio
import ssl
from urllib.parse import urlparse
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, update
from sqlalchemy.pool import NullPool

# Import the Player model
# Note: We need to ensure the app directory is in the python path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.models.player import Player
from app.models.team import Team
from app.models.player_game_stats import PlayerGameStats
from app.models.game import Game
from app.models.team_game_stats import TeamGameStats

# Load environment variables
load_dotenv()

async def update_player_images():
    # 1. Database Configuration
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not found in .env")
        return

    # Clean URL for asyncpg
    if "?sslmode=" in database_url:
        database_url = database_url.split("?sslmode=")[0]
    
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://")

    # SSL configuration for Aiven
    parsed = urlparse(database_url)
    host = parsed.hostname or ""
    use_ssl = host not in ("db", "localhost", "127.0.0.1")
    
    connect_args = {}
    if use_ssl:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context

    # Create engine
    engine = create_async_engine(
        database_url,
        connect_args=connect_args,
        poolclass=NullPool
    )

    async_session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # 2. Read CSV Data
    csv_file_path = os.path.join(os.path.dirname(__file__), "data", "players-image.csv")
    if not os.path.exists(csv_file_path):
        print(f"Error: CSV file not found at {csv_file_path}")
        return

    player_images = []
    with open(csv_file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            player_images.append({
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "image_url": row["image_url"]
            })

    print(f"Total players in CSV: {len(player_images)}")

    # 3. Update Database
    async with async_session_maker() as session:
        updated_count = 0
        not_found_count = 0
        
        for p_data in player_images:
            # Search for the player by first_name and last_name
            stmt = select(Player).where(
                Player.first_name == p_data["first_name"],
                Player.last_name == p_data["last_name"]
            )
            result = await session.execute(stmt)
            player = result.scalars().first()

            if player:
                # Update image_url
                player.image_url = p_data["image_url"]
                updated_count += 1
                if updated_count % 50 == 0:
                    print(f"Progress: {updated_count} players updated...")
            else:
                not_found_count += 1
                # print(f"Warning: Player {p_data['first_name']} {p_data['last_name']} not found in database.")

        await session.commit()
        print("-" * 30)
        print(f"Migration finished!")
        print(f"Players updated: {updated_count}")
        print(f"Players not found in DB: {not_found_count}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(update_player_images())
