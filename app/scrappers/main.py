import asyncio
import pandas as pd
from app.scrappers.schedule import fetch_schedule_dataframe
from app.scrappers.game_player_stats import process_games_from_schedule_df
import sys
from app.scrappers.insert_tables import populate_games_and_stats 


async def main():
    # 1) Get schedule between last Final date and today
    schedule_df = await fetch_schedule_dataframe()

    # 2) Generate a DataFrame with full boxscore stats (not CSV)
    boxscores_df = process_games_from_schedule_df(schedule_df)

    # 3) Insert data into the database
    await populate_games_and_stats(boxscores_df)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
