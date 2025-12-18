import sys
import os
import json
import pandas as pd
import asyncio
from datetime import datetime
from sqlalchemy import select

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import AsyncSessionLocal
from app.models.team import Team
from app.models.player import Player
from app.models.game import Game, GameType
from app.models.team_game_stats import TeamGameStats
from app.models.player_game_stats import PlayerGameStats


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEAMS_JSON_PATH = "app/scrappers/utils/teams.json"
PLAYERS_JSON_PATH = "app/scrappers/utils/players.json"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def parse_date(date_str):
    """
    Parse a date string into a Python date object.
    Accepts formats like 2025-12-08 or 2025/12/08.
    """
    try:
        return datetime.strptime(str(date_str).replace("-", "/"), "%Y/%m/%d").date()
    except (ValueError, TypeError):
        return None


def clean_float(val):
    """
    Safely convert a value to float. Returns 0 for invalid/empty values.
    """
    try:
        if pd.isna(val) or val == "" or str(val).strip() == "":
            return 0.0
        return float(val)
    except Exception:
        return 0.0


def clean_int(val):
    """
    Safely convert a value to int. Returns 0 for invalid/empty values.
    """
    try:
        if pd.isna(val) or val == "" or str(val).strip() == "":
            return 0
        return int(float(val))
    except Exception:
        return 0


def clean_minutes(val):
    """
    Convert minutes played from 'MM:SS' or float/text to decimal minutes.
    Returns 0.0 for empty or invalid values.
    """
    if pd.isna(val) or val == "":
        return 0.0
    try:
        if isinstance(val, str) and ":" in val:
            m, s = val.split(":")
            return int(m) + int(s) / 60.0
        return float(val)
    except Exception:
        return 0.0


def extract_periods(row, prefix):
    """
    Build a list of period scores for a team: Q1, Q2, Q3, Q4, OT1, OT2, ...
    """
    scores = []
    # Regular quarters
    for i in range(1, 5):
        scores.append(clean_int(row.get(f"{prefix}_Q{i}")))
    # Overtime periods
    ot = 1
    while True:
        col = f"{prefix}_OT{ot}"
        if col not in row or pd.isna(row[col]) or row[col] == 0:
            break
        scores.append(clean_int(row[col]))
        ot += 1
    return scores


def load_maps():
    """
    Load team and player mappings from JSON.
    Returns:
        team_map: maps team abbreviation/full_name -> team_id
        player_map: maps (first, last) and 'first last' -> player_id
    """
    with open(TEAMS_JSON_PATH, "r") as f:
        t_data = json.load(f)
    team_map = {}
    for t in t_data["teams"]:
        team_map[t["abbreviation"]] = t["id"]
        team_map[t["full_name"]] = t["id"]

    with open(PLAYERS_JSON_PATH, "r") as f:
        p_data = json.load(f)

    player_map = {}
    for p in p_data["players"]:
        first = str(p["first_name"]).strip().lower()
        last = str(p["last_name"]).strip().lower()
        key_tuple = (first, last)
        full_key = f"{first} {last}"
        player_map[key_tuple] = p["id"]
        player_map[full_key] = p["id"]

    return team_map, player_map


def get_player_id(name_str, player_map):
    """
    Resolve a player name from the DataFrame into a player_id using the player_map.
    Returns None if the name is missing or not found.
    """
    if not name_str or str(name_str).strip().upper() in ["NO INFO", "N/A", "0", "0.0"]:
        return None

    clean_name = str(name_str).strip()
    lower_full = clean_name.lower()

    # Direct full-name match ("first last")
    if lower_full in player_map:
        return player_map[lower_full]

    # Split into first/last and try tuple key
    parts = lower_full.split(" ", 1)
    if len(parts) == 2:
        key = (parts[0], parts[1])
        if key in player_map:
            return player_map[key]

    return None


# ---------------------------------------------------------------------------
# Team-level aggregation and advanced metrics
# ---------------------------------------------------------------------------
def aggregate_team_boxscore(row, team_prefix):
    """
    Aggregate team box score from all players (starters + bench) for a given team.
    Returns a dict with: pts, fga, fta, orb, drb, trb, ast, tov
    """
    total_pts = total_fga = total_fta = 0
    total_orb = total_drb = total_trb = 0
    total_ast = total_tov = 0

    # Starters
    for i in range(1, 6):
        prefix = f"{team_prefix}_ST_P{i}"
        total_pts += clean_int(row.get(f"{prefix}_PTS"))
        total_fga += clean_int(row.get(f"{prefix}_FGA"))
        total_fta += clean_int(row.get(f"{prefix}_FTA"))
        total_orb += clean_int(row.get(f"{prefix}_ORB"))
        total_drb += clean_int(row.get(f"{prefix}_DRB"))
        total_trb += clean_int(row.get(f"{prefix}_TRB"))
        total_ast += clean_int(row.get(f"{prefix}_AST"))
        total_tov += clean_int(row.get(f"{prefix}_TOV"))

    # Bench (your data goes up to RS_P10)
    for i in range(1, 11):
        prefix = f"{team_prefix}_RS_P{i}"
        total_pts += clean_int(row.get(f"{prefix}_PTS"))
        total_fga += clean_int(row.get(f"{prefix}_FGA"))
        total_fta += clean_int(row.get(f"{prefix}_FTA"))
        total_orb += clean_int(row.get(f"{prefix}_ORB"))
        total_drb += clean_int(row.get(f"{prefix}_DRB"))
        total_trb += clean_int(row.get(f"{prefix}_TRB"))
        total_ast += clean_int(row.get(f"{prefix}_AST"))
        total_tov += clean_int(row.get(f"{prefix}_TOV"))

    return {
        "pts": total_pts,
        "fga": total_fga,
        "fta": total_fta,
        "orb": total_orb,
        "drb": total_drb,
        "trb": total_trb,
        "ast": total_ast,
        "tov": total_tov,
    }


def calculate_team_advanced_from_box(team_stats, opp_stats, pace):
    """
    Calculate team advanced metrics from aggregated box score and pace.
    Returns: offensive_rating_calc, true_shooting_pct, assist_pct, def_rebound_pct, total_rebound_pct
    """
    pts = team_stats["pts"]
    fga = team_stats["fga"]
    fta = team_stats["fta"]
    ast = team_stats["ast"]
    drb = team_stats["drb"]
    trb = team_stats["trb"]
    orb = team_stats["orb"]
    opp_orb = opp_stats["orb"]
    opp_trb = opp_stats["trb"]

    # True Shooting Percentage
    ts_att = 2 * (fga + 0.44 * fta)
    ts_pct = pts / ts_att if ts_att > 0 else 0

    # Assist Percentage
    ast_pct = (ast * 2 / pts) if pts > 0 else 0

    # Defensive Rebound Percentage
    drb_chance = drb + opp_orb
    drb_pct = drb / drb_chance if drb_chance > 0 else 0

    # Total Rebound Percentage
    trb_chance = trb + opp_trb
    trb_pct = trb / trb_chance if trb_chance > 0 else 0

    # Offensive Rating
    ortg_calc = (pts / pace) * 100.0 if pace is not None and pace > 0 else 0

    return {
        "offensive_rating_calc": round(ortg_calc, 1) if ortg_calc is not None else 0,
        "true_shooting_pct": round(ts_pct, 3),
        "assist_pct": round(ast_pct, 3),
        "def_rebound_pct": round(drb_pct, 3) * 100,
        "total_rebound_pct": round(trb_pct, 3) * 100,
    }


# ---------------------------------------------------------------------------
# MAIN SCRIPT
# ---------------------------------------------------------------------------
async def populate_games_and_stats(df: pd.DataFrame):
    """
    Populate games, team_game_stats, and player_game_stats tables from a DataFrame.
    """
    print("\n" + "=" * 80)
    print(" POPULATING GAMES, TEAM_GAME_STATS & PLAYER_GAME_STATS ")
    print("=" * 80 + "\n")

    team_map, player_map = load_maps()

    print(f">> Processing {len(df)} rows from DataFrame...")

    # Normalize team abbreviations so they match teams.json
    abbr_map = {
        "BRK": "BKN",
        "CHO": "CHA",
        "PHO": "PHX",
    }
    df["VT"] = df["VT"].replace(abbr_map)
    df["HT"] = df["HT"].replace(abbr_map)

    async with AsyncSessionLocal() as session:
        try:
            for idx, row in df.iterrows():
                # A. GAME METADATA
                date_obj = parse_date(row.get("Date"))
                if not date_obj:
                    print(f"Skipping row {idx}: Invalid date.")
                    continue

                vt_abbr = row.get("VT")
                ht_abbr = row.get("HT")

                vt_id = team_map.get(vt_abbr)
                ht_id = team_map.get(ht_abbr)
                if not vt_id or not ht_id:
                    print(f"Skipping row {idx}: Team not found.")
                    continue

                # Avoid duplicates
                stmt = select(Game).where(
                    (Game.date == date_obj)
                    & (Game.home_team_id == ht_id)
                    & (Game.visitor_team_id == vt_id)
                )
                res = await session.execute(stmt)
                if res.scalar_one_or_none():
                    print(f"Skipping row {idx}: Game already exists.")
                    continue

                season = date_obj.year + 1 if date_obj.month >= 8 else date_obj.year

                raw_game_type = str(row.get("Game_Type") or "").strip().upper()
                if raw_game_type == "RS":
                    game_type_enum = GameType.RS
                elif raw_game_type == "PI":
                    game_type_enum = GameType.PI
                elif raw_game_type == "PO":
                    game_type_enum = GameType.PO
                else:
                    print(f"Skipping row {idx}: Invalid Game_Type: {raw_game_type}")
                    continue

                game = Game(
                    date=date_obj,
                    season=season,
                    game_type=game_type_enum,
                    status="Final",
                    home_team_id=ht_id,
                    visitor_team_id=vt_id,
                    home_score=clean_int(row.get("HT_Total")),
                    visitor_score=clean_int(row.get("VT_Total")),
                    home_period_scores=extract_periods(row, "HT"),
                    visitor_period_scores=extract_periods(row, "VT"),
                )
                session.add(game)
                await session.flush()

                # B. TEAM STATS (TeamGameStats)
                ht_box = aggregate_team_boxscore(row, "HT")
                vt_box = aggregate_team_boxscore(row, "VT")

                ht_pace = clean_float(row.get("HT_Pace"))
                vt_pace = clean_float(row.get("VT_Pace"))

                ht_calc = calculate_team_advanced_from_box(ht_box, vt_box, ht_pace)
                vt_calc = calculate_team_advanced_from_box(vt_box, ht_box, vt_pace)

                def create_team_stats(prefix, is_home, team_id, opp_id, calc, opp_calc):
                    """
                    Build a TeamGameStats instance for one side (home or visitor).
                    """
                    ortg_csv = clean_float(row.get(f"{prefix}_ORtg"))
                    offensive_raw = ortg_csv if ortg_csv is not None else calc["offensive_rating_calc"]
                    offensive_rating = round(offensive_raw, 1) if offensive_raw is not None else None

                    defensive_raw = opp_calc["offensive_rating_calc"]
                    defensive_rating = round(defensive_raw, 1) if defensive_raw is not None else None

                    return TeamGameStats(
                        game_id=game.id,
                        team_id=team_id,
                        opponent_id=opp_id,
                        is_home_game=is_home,
                        pace=clean_float(row.get(f"{prefix}_Pace")),
                        offensive_rating=offensive_rating,
                        defensive_rating=defensive_rating,
                        effective_fg_pct=clean_float(row.get(f"{prefix}_eFG%")),
                        true_shooting_pct=calc["true_shooting_pct"],
                        ft_per_fga=clean_float(row.get(f"{prefix}_FT/FGA")),
                        turnover_pct=clean_float(row.get(f"{prefix}_TOV%")),
                        assist_pct=calc["assist_pct"],
                        off_rebound_pct=clean_float(row.get(f"{prefix}_ORB%")),
                        def_rebound_pct=calc["def_rebound_pct"],
                        total_rebound_pct=calc["total_rebound_pct"],
                    )

                session.add(create_team_stats("HT", True, ht_id, vt_id, ht_calc, vt_calc))
                session.add(create_team_stats("VT", False, vt_id, ht_id, vt_calc, ht_calc))

                # C. PLAYER STATS (PlayerGameStats)
                player_prefixes = []
                for i in range(1, 6):
                    player_prefixes.append((f"VT_ST_P{i}", vt_id, True))
                    player_prefixes.append((f"HT_ST_P{i}", ht_id, True))
                for i in range(1, 11):
                    player_prefixes.append((f"VT_RS_P{i}", vt_id, False))
                    player_prefixes.append((f"HT_RS_P{i}", ht_id, False))

                for prefix, p_team_id, is_starter in player_prefixes:
                    name_col = f"{prefix}_Name"
                    p_name = row.get(name_col)
                    if not p_name or str(p_name).strip().upper() in ["NO INFO", ""]:
                        continue

                    p_id = get_player_id(p_name, player_map)
                    if not p_id:
                        continue

                    def g(col: str):
                        return row.get(f"{prefix}_{col}")

                    p_stats = PlayerGameStats(
                        game_id=game.id,
                        player_id=p_id,
                        team_id=p_team_id,
                        is_starter=is_starter,
                        minutes=clean_minutes(g("MP")),
                        fg=clean_int(g("FG")),
                        fga=clean_int(g("FGA")),
                        fg_pct=clean_float(g("FG%")),
                        fg3=clean_int(g("3P")),
                        fg3a=clean_int(g("3PA")),
                        fg3_pct=clean_float(g("3P%")),
                        ft=clean_int(g("FT")),
                        fta=clean_int(g("FTA")),
                        ft_pct=clean_float(g("FT%")),
                        orb=clean_int(g("ORB")),
                        drb=clean_int(g("DRB")),
                        trb=clean_int(g("TRB")),
                        ast=clean_int(g("AST")),
                        stl=clean_int(g("STL")),
                        blk=clean_int(g("BLK")),
                        tov=clean_int(g("TOV")),
                        pf=clean_int(g("PF")),
                        pts=clean_int(g("PTS")),
                        plus_minus=clean_int(g("Plus_Minus")),
                        game_score=clean_float(g("GmSc")),
                        ts_pct=clean_float(g("TS%")),
                        efg_pct=clean_float(g("eFG%")),
                        fg3a_rate=clean_float(g("3PAr")),
                        ft_rate=clean_float(g("FTr")),
                        orb_pct=clean_float(g("ORB%")),
                        drb_pct=clean_float(g("DRB%")),
                        trb_pct=clean_float(g("TRB%")),
                        ast_pct=clean_float(g("AST%")),
                        stl_pct=clean_float(g("STL%")),
                        blk_pct=clean_float(g("BLK%")),
                        tov_pct=clean_float(g("TOV%")),
                        usg_pct=clean_float(g("USG%")),
                        off_rating=clean_float(g("ORtg")),
                        def_rating=clean_float(g("DRtg")),
                        bpm=clean_float(g("BPM")),
                    )
                    session.add(p_stats)

                # Commit periodically
                if (idx + 1) % 10 == 0:
                    print(f"Processed {idx + 1}/{len(df)} games...")

            await session.commit()
            print("All data successfully inserted.")

        except Exception as e:
            await session.rollback()
            print(f"Error during data insertion: {e}")
            import traceback
            traceback.print_exc()


# If executed as main
if __name__ == "__main__":
    # Example usage: pass a DataFrame from your scraper
    # df = pd.DataFrame(...)  # Your DataFrame from game_player_stats.py
    # asyncio.run(populate_games_and_stats(df))
    print("This script is intended to be imported and run with a DataFrame from game_player_stats.py.")
