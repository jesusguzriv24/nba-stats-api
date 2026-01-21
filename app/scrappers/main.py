import asyncio
import pandas as pd
from app.scrappers.schedule import fetch_schedule_dataframe
from app.scrappers.game_player_stats import process_games_from_schedule_df
import sys
from app.scrappers.insert_tables import populate_games_and_stats  


async def main():
    # 1) Get schedule: historical (with scores) and daily (today's scheduled)
    historical_df, daily_df = await fetch_schedule_dataframe()

    # 2) Process daily games (today)
    from app.scrappers.insert_tables import populate_daily_games, populate_player_props
    await populate_daily_games(daily_df)

    # 3) Process player props (Casino lines)
    from app.scrappers.player_props import scrape_nba_props
    props_df = scrape_nba_props()
    if not props_df.empty:
        await populate_player_props(props_df)

    # 4) Process historical games (yesterday and before)
    if not historical_df.empty:
        # Generate a DataFrame with full boxscore stats
        boxscores_df = process_games_from_schedule_df(historical_df)

        # Insert historical data into the database
        if not boxscores_df.empty:
            await populate_games_and_stats(boxscores_df)
    else:
        print("[INFO] No new historical games to process.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
