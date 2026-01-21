import asyncio
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, List

import pandas as pd
from sqlalchemy import select, func

from app.core.database import AsyncSessionLocal
from app.models.game import Game
from app.models.team import Team   
from app.models.player_game_stats import PlayerGameStats
from app.models.player import Player
from app.models.team_game_stats import TeamGameStats  

# Base URL for Basketball Reference schedule pages
BASE_URL = "https://www.basketball-reference.com/leagues/NBA_{year}_games-{month}.html"

# Seasons and months configuration (Basketball Reference "season year")
NBA_SEASONS = {
    # 2025–26 season -> NBA_2026_...
    2026: ["October", "November", "December", "January", "February", "March", "April"],
    # 2024–25 season -> NBA_2025_...
    2025: ["October", "November", "December", "January", "February", "March", "April", "May", "June"],
}

# Mapping full team names to abbreviations
NBA_TEAMS = {
    "Atlanta Hawks": "ATL",
    "Boston Celtics": "BOS",
    "Brooklyn Nets": "BRK",
    "Charlotte Hornets": "CHO",
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL",
    "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW",
    "Houston Rockets": "HOU",
    "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC",
    "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA",
    "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHO",
    "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}

# Output directory only for testing CSV
OUTPUT_DIR = Path("scripts/data/raw/schedule")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------
# 1. Helpers for database and dates
# --------------------------------------------------------------------
async def get_last_final_game_date() -> Optional[date]:
    """
    Get the most recent Game.date where status = 'Final'.
    Returns None if there is no game with status 'Final'.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(func.max(Game.date)).where(Game.status == "Final")
        result = await session.execute(stmt)  # [web:43][web:51]
        max_date: Optional[date] = result.scalar_one_or_none()
        return max_date


def get_today_date() -> date:
    """
    Get current server date as a date object.
    """
    return date.today()  # [web:26][web:28]


async def get_scraping_date_range() -> Tuple[date, date]:
    """
    Decide the date range for scraping:
    - start_date: day after the last 'Final' game in DB
    - end_date: current server date
    If there is no 'Final' game in DB, start_date = end_date.
    """
    today = get_today_date()
    last_final_date = await get_last_final_game_date()

    if last_final_date is None:
        # No games in DB yet -> start and end are today
        start_date = today
    else:
        # Start from the next day after the last final game
        start_date = last_final_date + timedelta(days=1)

    return start_date, today


def month_name_from_date(d: date) -> str:
    """
    Convert a date to month name in English, matching Basketball Reference URLs.
    Example: 2025-10-15 -> 'October'.
    """
    return d.strftime("%B")  # [web:38]

def get_season_year_for_date(d: date) -> int:
    """
    Map a calendar date to Basketball Reference 'season year'
    (the year that appears in NBA_{year}_games-*.html).

    Example:
      - 2025-10-21 (regular season start 2025–26) -> 2026
      - 2025-12-10 (still 2025–26) -> 2026
      - 2026-03-15 (still 2025–26) -> 2026
    """
    # Simple rule: if month >= October (10), the season finishes next calendar year
    if d.month >= 10:
        return d.year + 1
    return d.year

def get_year_month_pairs_in_range(start_date: date, end_date: date) -> List[Tuple[int, str]]:
    """
    Given a date range, return the list of (season_year, month_name)
    needed to cover that range, where season_year is the year used in
    Basketball Reference URLs (NBA_{season_year}_games-month.html).
    """
    pairs: List[Tuple[int, str]] = []

    current = date(start_date.year, start_date.month, 1)
    end_marker = date(end_date.year, end_date.month, 1)

    while current <= end_marker:
        season_year = get_season_year_for_date(current)
        month_name = month_name_from_date(current)
        pairs.append((season_year, month_name))

        # Move to first day of next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return pairs

# --------------------------------------------------------------------
# 2. Scraping logic (per month and full range)
# --------------------------------------------------------------------
def scrape_nba_schedule_month(year: int, month: str) -> Optional[pd.DataFrame]:
    """
    Download and process the schedule table for a specific year and month
    from Basketball Reference, returning a DataFrame with:

    Date, Start (ET), VT, VT_PTS, HT, HT_PTS

    - Finished games keep their real scores.
    - Games not played yet (no scores) keep NaN or get 0.
    """
    url = BASE_URL.format(year=year, month=month.lower().replace(" ", "-"))
    print(f"[INFO] Requesting URL: {url}")

    try:
        # Read HTML table with id='schedule'
        tables = pd.read_html(url, attrs={"id": "schedule"})

        if not tables:
            print(f"[WARN] No 'schedule' table found for {year} - {month}")
            return None

        df = tables[0]

        # Keep only necessary columns
        columns_to_keep = ["Date", "Start (ET)", "Visitor/Neutral", "PTS", "Home/Neutral", "PTS.1"]
        # Ensure columns exist before filtering
        existing_cols = [c for c in columns_to_keep if c in df.columns]
        df = df[existing_cols].copy()

        # Rename columns
        df.rename(
            columns={
                "Date": "Date",
                "Start (ET)": "Time",
                "Visitor/Neutral": "VT",
                "PTS": "VT_PTS",
                "Home/Neutral": "HT",
                "PTS.1": "HT_PTS",
            },
            inplace=True,
        )

        # Replace team names with abbreviations
        df["VT"] = df["VT"].replace(NBA_TEAMS)
        df["HT"] = df["HT"].replace(NBA_TEAMS)

        # Drop rows with missing crucial info (Date, Teams)
        df = df.dropna(subset=["Date", "VT", "HT"])

        # Convert Date to string YYYY-MM-DD
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

        print(f"[OK] Extracted {len(df)} total games for {year} - {month}")
        return df

    except Exception as exc:
        print(f"[ERROR] Failed to process {year} - {month}: {exc}")
        return None

    except Exception as exc:
        print(f"[ERROR] Failed to process {year} - {month}: {exc}")
        return None


async def fetch_schedule_dataframe() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Main function to:
    - Read last 'Final' game date from DB
    - Determine date range until current server date
    - Scrape all necessary months from Basketball Reference
    - Return two DataFrames:
        1. historical_df: Games with scores (before today)
        2. daily_df: Games for today (scheduled)
    """
    print("=" * 60)
    print(" NBA SCHEDULE SCRAPER (DUAL MODE: HISTORICAL + DAILY)")
    print("=" * 60)

    start_date, end_date = await get_scraping_date_range()
    print(f"[INFO] Start date from DB (next after last Final): {start_date}")
    print(f"[INFO] End date (server today):                  {end_date}")

    year_month_pairs = get_year_month_pairs_in_range(start_date, end_date)
    
    all_frames: List[pd.DataFrame] = []
    for year, month_name in year_month_pairs:
        if year not in NBA_SEASONS or month_name not in NBA_SEASONS[year]:
            continue

        df_month = scrape_nba_schedule_month(year, month_name)
        if df_month is not None and not df_month.empty:
            all_frames.append(df_month)

    if not all_frames:
        print("\n[FAIL] No data extracted.")
        return pd.DataFrame(), pd.DataFrame()

    combined_df = pd.concat(all_frames, ignore_index=True)
    combined_df["Date"] = pd.to_datetime(combined_df["Date"])

    # Filter by range
    mask = (combined_df["Date"] >= pd.to_datetime(start_date)) & (
        combined_df["Date"] <= pd.to_datetime(end_date)
    )
    combined_df = combined_df.loc[mask].copy()

    # Split: Historical (with scores) vs Daily (today)
    today_str = end_date.strftime("%Y-%m-%d")
    
    # Historical: Date < today AND scores not NaN
    historical_mask = (combined_df["Date"] < pd.to_datetime(today_str)) & (
        combined_df["VT_PTS"].notna()
    )
    historical_df = combined_df.loc[historical_mask].copy()
    
    # Daily: Date == today
    daily_mask = (combined_df["Date"] == pd.to_datetime(today_str))
    daily_df = combined_df.loc[daily_mask].copy()

    # Clean historical: cast scores to int
    if not historical_df.empty:
        historical_df["VT_PTS"] = historical_df["VT_PTS"].astype(int)
        historical_df["HT_PTS"] = historical_df["HT_PTS"].astype(int)
        historical_df["Date"] = historical_df["Date"].dt.strftime("%Y-%m-%d")
        historical_df.sort_values(by="Date", ascending=False, inplace=True)

    # Clean daily: keep Date, Time, VT, HT
    if not daily_df.empty:
        daily_df["Date"] = daily_df["Date"].dt.strftime("%Y-%m-%d")
        daily_df = daily_df[["Date", "Time", "VT", "HT"]]

    print("\n" + "-" * 60)
    print(f" SCRAPER SUMMARY")
    print("-" * 60)
    print(f" > Historical games: {len(historical_df)}")
    print(f" > Daily games (today): {len(daily_df)}")
    print("-" * 60)

    return historical_df, daily_df


# --------------------------------------------------------------------
# 3. Test helper: generate CSV from the DataFrame
# --------------------------------------------------------------------
async def generate_test_schedule_csv() -> Path:
    """
    For testing purposes:
    - Build the schedule DataFrames
    - Save the historical one as a CSV file
    """
    df_hist, df_daily = await fetch_schedule_dataframe()

    if df_hist.empty:
        print("[WARN] Historical schedule DataFrame is empty. CSV will not be created.")
        return OUTPUT_DIR / "nba_schedule_test.csv"

    output_file = OUTPUT_DIR / "nba_schedule_test.csv"
    df.to_csv(output_file, index=False)

    print("\n" + "=" * 60)
    print(" TEST SCHEDULE CSV GENERATED")
    print("=" * 60)
    print(f" > File:        {output_file}")
    print(f" > Rows:        {len(df)}")
    print(f" > First date:  {df['Date'].min()}")
    print(f" > Last date:   {df['Date'].max()}")
    print("=" * 60)

    return output_file


if __name__ == "__main__":
    # Run only the CSV generation in test mode
    asyncio.run(generate_test_schedule_csv())
