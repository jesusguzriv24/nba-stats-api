import os
import time
import random
import logging
import urllib.request
import gzip
import re
import unicodedata
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

import pandas as pd
from bs4 import BeautifulSoup, Comment

# ----------------------------------------------------------------------
# 0. Configuration for seasons and game types
# ----------------------------------------------------------------------

SEASON_PHASES = {
    "2024-25": {
        "RS": "2024-10-22",  # Regular Season start
        "PI": "2025-04-15",  # Play-In start
        "PO": "2025-04-19",  # Playoffs start
    },
    "2025-26": {
        "RS": "2025-10-21",  # Regular Season start
        "PI": "2026-04-14",  # Play-In start
        "PO": "2026-04-18",  # Playoffs start
    },
}

def get_game_type(game_date_str: str, season_key: str = "2024-25") -> str:
    """
    Determine game type (RS, PI, PO) based on the game date and SEASON_PHASES.
    game_date_str: 'YYYY-MM-DD'
    """
    phases = SEASON_PHASES[season_key]

    d = datetime.strptime(game_date_str, "%Y-%m-%d").date()
    rs_start = datetime.strptime(phases["RS"], "%Y-%m-%d").date()
    pi_start = datetime.strptime(phases["PI"], "%Y-%m-%d").date()
    po_start = datetime.strptime(phases["PO"], "%Y-%m-%d").date()

    if d < pi_start:
        return "RS"
    elif pi_start <= d < po_start:
        return "PI"
    else:
        return "PO"
    
def get_season_key_for_date(game_date_str: str) -> str:
    """
    Map a game date (YYYY-MM-DD) to a season key in SEASON_PHASES.
    Example:
      2024-11-10 -> "2024-25"
      2025-03-01 -> "2024-25"
      2025-10-25 -> "2025-26"
      2025-12-11 -> "2025-26"
    """
    d = datetime.strptime(game_date_str, "%Y-%m-%d").date()

    # Simple rule: season runs from October to June
    if d.month >= 10:  # October, November, December
        season_start_year = d.year
        season_end_year = d.year + 1
    else:  # January..June
        season_start_year = d.year - 1
        season_end_year = d.year

    key = f"{season_start_year}-{str(season_end_year)[-2:]}"
    if key not in SEASON_PHASES:
        raise ValueError(f"Season key {key} not found in SEASON_PHASES")
    return key

# ----------------------------------------------------------------------
# 0. Player name normalization
# ---------------------------------------------------------------------- 
def normalize_player_name(name: str) -> str:
    """
    Normalize player names for API OUTPUT:
    - Remove accents but KEEP apostrophes
    - Preserve original capitalization
    Example: "De'Aaron Fox" -> "De'Aaron Fox"
    """
    if not name:
        return ""

    # Unicode normalize (remove accents)
    name_norm = unicodedata.normalize("NFD", name)
    name_norm = "".join(
        c for c in name_norm if unicodedata.category(c) != "Mn"
    )

    # Remove all non alphanumeric and non-space characters (apostrophes, etc.)
    name_norm = re.sub(r"[^a-zA-Z0-9\s\-\.']", "", name_norm)

    # Optional: strip extra spaces
    #name_norm = " ".join(name_norm.split())

    return name_norm.strip()


# ----------------------------------------------------------------------
# 0. Scraping configuration and logging
# ----------------------------------------------------------------------
SCRAPING_CONFIG = {
    "max_retries": 3,
    "base_delay": 4,          # Base seconds between requests
    "timeout": 30,            # HTTP timeout
    "retry_delays": [5, 10, 20],
    "max_random_delay": 2,    # Extra random delay
}

logger: Optional[logging.Logger] = None


def setup_logging() -> logging.Logger:
    """
    Configure structured logging to both file and console.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"nba_boxscores_{timestamp}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    log = logging.getLogger(__name__)
    log.info("=" * 80)
    log.info(" STARTING NBA BOXSCORES SCRAPING SESSION")
    log.info(f" Log file: {log_file}")
    log.info("=" * 80)
    return log


# ----------------------------------------------------------------------
# 1. URL generation from schedule DataFrame
# ----------------------------------------------------------------------
def build_boxscore_urls_from_schedule_df(
    schedule_df: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Build Basketball Reference boxscore URLs from the schedule DataFrame.

    Expected input columns in schedule_df:
      - Date : string in 'YYYY-MM-DD' format (from scrappers/schedule.py)
      - VT   : visiting team abbreviation (e.g. 'SAS')
      - HT   : home team abbreviation (e.g. 'NOP')
      - VT_PTS, HT_PTS : integer scores (0 allowed for not played yet)

    Output: list of dicts with:
      - date  (string, original Date)
      - visiting_team (abbr)
      - home_team     (abbr)
      - url           (boxscore URL)
      - vt_pts        (int)
      - ht_pts        (int)
    """
    print("=" * 60)
    print(" BUILDING BOXSCORE URLS FROM SCHEDULE DATAFRAME")
    print("=" * 60)

    games_urls: List[Dict[str, Any]] = []

    for idx, row in schedule_df.iterrows():
        date_str = str(row["Date"])
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")

        year = date_obj.strftime("%Y")
        month = date_obj.strftime("%m")
        day = date_obj.strftime("%d")

        visiting_team = str(row["VT"])
        home_team = str(row["HT"])

        url = (
            f"https://www.basketball-reference.com/boxscores/"
            f"{year}{month}{day}0{home_team}.html"
        )

        game_info = {
            "date": date_str,
            "visiting_team": visiting_team,
            "home_team": home_team,
            "url": url,
            "vt_pts": int(row["VT_PTS"]),
            "ht_pts": int(row["HT_PTS"]),
        }

        games_urls.append(game_info)

        print(
            f"[GAME] {date_str}: {visiting_team} @ {home_team} -> {url} "
            f"(VT_PTS={game_info['vt_pts']}, HT_PTS={game_info['ht_pts']})"
        )

    print("\n" + "-" * 60)
    print(f" TOTAL GAMES IN SCHEDULE DATAFRAME: {len(games_urls)}")
    print("-" * 60)

    return games_urls


# ----------------------------------------------------------------------
# 2. HTML fetch with retries (urllib)
# ----------------------------------------------------------------------
def fetch_html_with_urllib(url: str, retry_count: int = 0) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Fetch raw HTML using urllib with robust error handling and retry logic.

    Returns:
      (success: bool, error_message: Optional[str], html_content: Optional[str])
    """
    global logger
    if logger is None:
        logger = setup_logging()

    if retry_count == 0:
        logger.info(f"[HTTP] Fetching HTML: {url}")
    else:
        logger.info(
            f"[HTTP] Retry {retry_count}/{SCRAPING_CONFIG['max_retries']} for: {url}"
        )

    try:
        req = urllib.request.Request(url)
        req.add_header(
            "User-Agent",
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        req.add_header(
            "Accept",
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        )
        req.add_header("Accept-Language", "en-US,en;q=0.5")
        req.add_header("Accept-Encoding", "gzip, deflate")
        req.add_header("DNT", "1")
        req.add_header("Connection", "keep-alive")
        req.add_header("Upgrade-Insecure-Requests", "1")

        start_time = time.time()
        with urllib.request.urlopen(req, timeout=SCRAPING_CONFIG["timeout"]) as response:
            response_time = time.time() - start_time
            status_code = response.getcode()
            content = response.read()

            if content.startswith(b"\x1f\x8b"):  # GZIP magic number
                html_content = gzip.decompress(content).decode("utf-8")
                logger.info("[HTTP] GZIP content decompressed")
            else:
                html_content = content.decode("utf-8")

        logger.info(
            f"[HTTP] OK - size={len(html_content):,} chars, "
            f"time={response_time:.2f}s, status={status_code}"
        )

        base_delay = SCRAPING_CONFIG["base_delay"]
        random_delay = random.uniform(0, SCRAPING_CONFIG["max_random_delay"])
        total_delay = base_delay + random_delay
        logger.info(f"[DELAY] Sleeping {total_delay:.1f} seconds (anti-bot)")
        time.sleep(total_delay)

        return True, None, html_content

    except urllib.error.HTTPError as e:
        error_msg = f"HTTP Error {e.code}: {e.reason}"
        logger.error(error_msg)

        should_retry = e.code in [429, 500, 502, 503, 504, 403]
        if should_retry and retry_count < SCRAPING_CONFIG["max_retries"]:
            delay = SCRAPING_CONFIG["retry_delays"][
                min(retry_count, len(SCRAPING_CONFIG["retry_delays"]) - 1)
            ]
            logger.info(f"[RETRY] Waiting {delay} seconds before retry (HTTP error)")
            time.sleep(delay)
            return fetch_html_with_urllib(url, retry_count + 1)

        return False, error_msg, None

    except urllib.error.URLError as e:
        error_msg = f"URL Error: {e.reason}"
        logger.error(error_msg)

        if retry_count < SCRAPING_CONFIG["max_retries"]:
            delay = SCRAPING_CONFIG["retry_delays"][
                min(retry_count, len(SCRAPING_CONFIG["retry_delays"]) - 1)
            ]
            logger.info(f"[RETRY] Waiting {delay} seconds before retry (connectivity)")
            time.sleep(delay)
            return fetch_html_with_urllib(url, retry_count + 1)

        return False, error_msg, None

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)

        if retry_count < SCRAPING_CONFIG["max_retries"]:
            delay = SCRAPING_CONFIG["retry_delays"][
                min(retry_count, len(SCRAPING_CONFIG["retry_delays"]) - 1)
            ]
            logger.info(f"[RETRY] Waiting {delay} seconds before retry (unexpected)")
            time.sleep(delay)
            return fetch_html_with_urllib(url, retry_count + 1)

        return False, error_msg, None


# ----------------------------------------------------------------------
# 3. Helpers to detect teams from HTML (safety)
# ----------------------------------------------------------------------
def detect_teams_from_html(html_content: str) -> Optional[List[str]]:
    """
    Detect team codes from HTML by inspecting box-XXX-game-basic tables.
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        basic_tables = soup.find_all("table", id=re.compile(r"box-[A-Z]{3}-game-basic"))

        teams: List[str] = []
        for table in basic_tables:
            table_id = table.get("id")
            match = re.search(r"box-([A-Z]{3})-game-basic", table_id or "")
            if match:
                teams.append(match.group(1))

        return teams if len(teams) >= 2 else None

    except Exception:
        return None


# ----------------------------------------------------------------------
# 4. Extract line score (points by quarter and OT)
# ----------------------------------------------------------------------
def extract_line_score(html_content: str) -> Optional[Dict[str, Any]]:
    """
    Extract line_score table (points by quarter and OT) and return
    a single-row dict with VT_* and HT_* fields.
    """
    print("\n" + "=" * 60)
    print(" EXTRACTING LINE SCORE TABLE")
    print("=" * 60)

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        all_line_score_div = soup.find("div", {"id": "all_line_score"})

        if not all_line_score_div:
            print("[WARN] 'all_line_score' div not found")
            return None

        html_comments = all_line_score_div.find_all(
            string=lambda text: isinstance(text, Comment)
        )

        line_score_table = None
        for comment in html_comments:
            comment_soup = BeautifulSoup(str(comment), "html.parser")
            table = comment_soup.find("table", {"id": "line_score"})
            if table:
                line_score_table = table
                print("[INFO] 'line_score' table found inside HTML comment")
                break

        if not line_score_table:
            print("[WARN] 'line_score' table not found in comments")
            return None

        tbody = line_score_table.find("tbody")
        if not tbody:
            print("[WARN] 'line_score' tbody not found")
            return None

        rows = tbody.find_all("tr")
        print(f"[INFO] Found {len(rows)} team rows in line_score")

        teams_data: List[Dict[str, Any]] = []

        for i, row in enumerate(rows):
            team_th = row.find("th")
            if not team_th:
                print(f"[WARN] Row {i+1}: missing team header")
                continue

            team_link = team_th.find("a")
            team_name = (
                team_link.text.strip() if team_link else team_th.text.strip()
            )

            quarters = row.find_all("td")
            if len(quarters) < 5:
                print(
                    f"[WARN] Row {i+1}: only {len(quarters)} columns, expected at least 5"
                )
                continue

            def safe_int(td):
                text = td.text.strip()
                return int(text) if text else 0

            q1 = safe_int(quarters[0])
            q2 = safe_int(quarters[1])
            q3 = safe_int(quarters[2])
            q4 = safe_int(quarters[3])

            ot1 = ot2 = ot3 = ot4 = 0
            total_index = len(quarters) - 1

            if len(quarters) > 5:
                ot1 = safe_int(quarters[4])
            if len(quarters) > 6:
                ot2 = safe_int(quarters[5])
            if len(quarters) > 7:
                ot3 = safe_int(quarters[6])
            if len(quarters) > 8:
                ot4 = safe_int(quarters[7])

            total_td = quarters[total_index]
            strong_tag = total_td.find("strong")
            total_points_text = (
                strong_tag.text.strip() if strong_tag else total_td.text.strip()
            )
            total_points = int(total_points_text) if total_points_text else 0

            team_data = {
                "team": team_name,
                "q1": q1,
                "q2": q2,
                "q3": q3,
                "q4": q4,
                "ot1": ot1,
                "ot2": ot2,
                "ot3": ot3,
                "ot4": ot4,
                "total": total_points,
            }
            teams_data.append(team_data)

        if len(teams_data) < 2:
            print("[WARN] Not enough teams in line_score (expected 2)")
            return None

        visiting_team = teams_data[0]
        home_team = teams_data[1]

        single_row_data = {
            "VT": visiting_team["team"],
            "VT_Q1": visiting_team["q1"],
            "VT_Q2": visiting_team["q2"],
            "VT_Q3": visiting_team["q3"],
            "VT_Q4": visiting_team["q4"],
            "VT_OT1": visiting_team["ot1"],
            "VT_OT2": visiting_team["ot2"],
            "VT_OT3": visiting_team["ot3"],
            "VT_OT4": visiting_team["ot4"],
            "VT_Total": visiting_team["total"],
            "HT": home_team["team"],
            "HT_Q1": home_team["q1"],
            "HT_Q2": home_team["q2"],
            "HT_Q3": home_team["q3"],
            "HT_Q4": home_team["q4"],
            "HT_OT1": home_team["ot1"],
            "HT_OT2": home_team["ot2"],
            "HT_OT3": home_team["ot3"],
            "HT_OT4": home_team["ot4"],
            "HT_Total": home_team["total"],
        }

        print("[INFO] Line score extracted into a single-row structure")
        return single_row_data

    except Exception as e:
        print(f"[ERROR] Line score extraction error: {e}")
        return None


# ----------------------------------------------------------------------
# 5. Four Factors extraction (team advanced stats)
# ----------------------------------------------------------------------
def extract_four_factors(html_content: str) -> Optional[List[Dict[str, Any]]]:
    """
    Extract four_factors table: pace, eFG%, TOV%, ORB%, FT rate, Off Rtg.
    Returns a list of dicts, one per team.
    """
    print("\n" + "=" * 60)
    print(" EXTRACTING FOUR FACTORS TABLE")
    print("=" * 60)

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        all_four_factors_div = soup.find("div", {"id": "all_four_factors"})

        if not all_four_factors_div:
            print("[WARN] 'all_four_factors' div not found")
            return None

        html_comments = all_four_factors_div.find_all(
            string=lambda text: isinstance(text, Comment)
        )

        four_factors_table = None
        for comment in html_comments:
            comment_soup = BeautifulSoup(str(comment), "html.parser")
            table = comment_soup.find("table", {"id": "four_factors"})
            if table:
                four_factors_table = table
                print("[INFO] 'four_factors' table found inside HTML comment")
                break

        if not four_factors_table:
            print("[WARN] 'four_factors' table not found in comments")
            return None

        tbody = four_factors_table.find("tbody")
        if not tbody:
            print("[WARN] four_factors tbody not found")
            return None

        rows = tbody.find_all("tr")
        print(f"[INFO] Found {len(rows)} team rows in four_factors")

        teams_four_factors: List[Dict[str, Any]] = []

        for i, row in enumerate(rows):
            team_th = row.find("th")
            if not team_th:
                print(f"[WARN] Row {i+1}: missing team header in four_factors")
                continue

            team_link = team_th.find("a")
            team_name = (
                team_link.text.strip() if team_link else team_th.text.strip()
            )

            stats = row.find_all("td")
            if len(stats) < 6:
                print(
                    f"[WARN] Row {i+1}: only {len(stats)} columns in four_factors, expected 6"
                )
                continue

            def safe_float(td):
                text = td.text.strip()
                if not text:
                    return 0.0
                if text.startswith("."):
                    return float("0" + text)
                return float(text)

            team_four_factors = {
                "team": team_name,
                "pace": safe_float(stats[0]),
                "efg_pct": safe_float(stats[1]),
                "tov_pct": safe_float(stats[2]),
                "orb_pct": safe_float(stats[3]),
                "ft_rate": safe_float(stats[4]),
                "off_rtg": safe_float(stats[5]),
            }

            teams_four_factors.append(team_four_factors)

        return teams_four_factors

    except Exception as e:
        print(f"[ERROR] Four factors extraction error: {e}")
        return None


# ----------------------------------------------------------------------
# 6. Player basic stats extraction (per game, both teams)
# ----------------------------------------------------------------------
def extract_player_stats(
    html_content: str, visiting_team: str, home_team: str
) -> Dict[str, Any]:
    """
    Extract player basic stats (Starters and Reserves) for both teams.

    - Starters: up to 5 per team (no forced padding).
    - Reserves: up to MAX_RESERVES per team.
      If a team has fewer than MAX_RESERVES real reserves,
      missing slots are filled with:
        Name = "NO INFO"
        All numeric stats = 0
    """
    print("\n" + "=" * 60)
    print(" EXTRACTING PLAYER BASIC STATS")
    print("=" * 60)

    soup = BeautifulSoup(html_content, "html.parser")

    team_tables = {
        "VT": soup.find("table", {"id": f"box-{visiting_team}-game-basic"}),
        "HT": soup.find("table", {"id": f"box-{home_team}-game-basic"}),
    }

    all_player_data: Dict[str, Any] = {}
    MAX_RESERVES = 10  # number of reserve slots per team

    for team_type, table in team_tables.items():
        if not table:
            print(f"[WARN] Basic stats table not found for {team_type}")
            continue

        print(f"[INFO] Basic stats table found for {team_type}")

        tbody = table.find("tbody")
        if not tbody:
            print(f"[WARN] Basic stats tbody not found for {team_type}")
            continue

        all_rows = tbody.find_all("tr")
        starters: List[Any] = []
        reserves: List[Any] = []
        current_section = "starters"

        for row in all_rows:
            th = row.find("th")
            # Section headers (Starters / Reserves)
            if th and "thead" in row.get("class", []):
                if "Reserves" in th.text:
                    current_section = "reserves"
                continue

            # Skip Team Totals rows
            if th and "Team Totals" in th.text:
                continue

            # Assign row to starters or reserves
            if current_section == "starters":
                starters.append(row)
            else:
                reserves.append(row)

        print(
            f"[INFO] {team_type}: {len(starters)} starters rows, {len(reserves)} reserves rows"
        )

        # Process Starters (up to 5)
        for i, row in enumerate(starters[:5]):
            player_data = extract_player_row_data(row, team_type, "ST", i + 1)
            if player_data:
                all_player_data.update(player_data)

        # Process Reserves (real rows, up to MAX_RESERVES)
        reserve_slots_used = 0
        for i, row in enumerate(reserves[:MAX_RESERVES]):
            slot_index = i + 1
            player_data = extract_player_row_data(row, team_type, "RS", slot_index)
            if player_data:
                all_player_data.update(player_data)
                reserve_slots_used += 1

        # Fill missing reserve slots with NO INFO and zeros
        if reserve_slots_used < MAX_RESERVES:
            print(
                f"[INFO] {team_type}: filling {MAX_RESERVES - reserve_slots_used} empty reserve slots with NO INFO"
            )

        for slot in range(reserve_slots_used + 1, MAX_RESERVES + 1):
            prefix = f"{team_type}_RS_P{slot}_"
            placeholder = {
                f"{prefix}Name": "NO INFO",
                f"{prefix}MP": 0.0,
                f"{prefix}FG": 0,
                f"{prefix}FGA": 0,
                f"{prefix}FG%": 0.0,
                f"{prefix}3P": 0,
                f"{prefix}3PA": 0,
                f"{prefix}3P%": 0.0,
                f"{prefix}FT": 0,
                f"{prefix}FTA": 0,
                f"{prefix}FT%": 0.0,
                f"{prefix}ORB": 0,
                f"{prefix}DRB": 0,
                f"{prefix}TRB": 0,
                f"{prefix}AST": 0,
                f"{prefix}STL": 0,
                f"{prefix}BLK": 0,
                f"{prefix}TOV": 0,
                f"{prefix}PF": 0,
                f"{prefix}PTS": 0,
                f"{prefix}GmSc": 0.0,
                f"{prefix}Plus_Minus": 0,
            }
            all_player_data.update(placeholder)

    return all_player_data


def extract_player_row_data(
    row, team_type: str, player_type: str, player_num: int
) -> Optional[Dict[str, Any]]:
    """
    Extract basic stats for a single player row.
    """
    try:
        th = row.find("th")
        if not th:
            return None

        player_link = th.find("a")
        raw_name = player_link.text.strip() if player_link else th.text.strip()
        player_name = normalize_player_name(raw_name)

        stats = row.find_all("td")

        reason_td = row.find("td", {"data-stat": "reason"})
        prefix = f"{team_type}_{player_type}_P{player_num}_"

        if reason_td:
            player_data = {
                f"{prefix}Name": player_name or "",
                f"{prefix}MP": 0.0,
                f"{prefix}FG": 0,
                f"{prefix}FGA": 0,
                f"{prefix}FG%": 0.0,
                f"{prefix}3P": 0,
                f"{prefix}3PA": 0,
                f"{prefix}3P%": 0.0,
                f"{prefix}FT": 0,
                f"{prefix}FTA": 0,
                f"{prefix}FT%": 0.0,
                f"{prefix}ORB": 0,
                f"{prefix}DRB": 0,
                f"{prefix}TRB": 0,
                f"{prefix}AST": 0,
                f"{prefix}STL": 0,
                f"{prefix}BLK": 0,
                f"{prefix}TOV": 0,
                f"{prefix}PF": 0,
                f"{prefix}PTS": 0,
                f"{prefix}GmSc": 0.0,
                f"{prefix}Plus_Minus": 0,
            }
            return player_data

        if len(stats) < 21:
            return None

        def safe_convert(td, conv, default=0):
            try:
                text = td.text.strip()
                if not text:
                    return default
                if conv is float and text.startswith("."):
                    return conv("0" + text)
                return conv(text)
            except Exception:
                return default

        def convert_minutes_to_decimal(mp_text: str) -> float:
            mp_text = mp_text.strip()
            if not mp_text:
                return 0.0
            if ":" in mp_text:
                decimal_format = mp_text.replace(":", ".")
                try:
                    return float(decimal_format)
                except Exception:
                    return 0.0
            try:
                return float(mp_text)
            except Exception:
                return 0.0

        player_data = {
            f"{prefix}Name": player_name,
            f"{prefix}MP": convert_minutes_to_decimal(stats[0].text),
            f"{prefix}FG": safe_convert(stats[1], int),
            f"{prefix}FGA": safe_convert(stats[2], int),
            f"{prefix}FG%": safe_convert(stats[3], float),
            f"{prefix}3P": safe_convert(stats[4], int),
            f"{prefix}3PA": safe_convert(stats[5], int),
            f"{prefix}3P%": safe_convert(stats[6], float),
            f"{prefix}FT": safe_convert(stats[7], int),
            f"{prefix}FTA": safe_convert(stats[8], int),
            f"{prefix}FT%": safe_convert(stats[9], float),
            f"{prefix}ORB": safe_convert(stats[10], int),
            f"{prefix}DRB": safe_convert(stats[11], int),
            f"{prefix}TRB": safe_convert(stats[12], int),
            f"{prefix}AST": safe_convert(stats[13], int),
            f"{prefix}STL": safe_convert(stats[14], int),
            f"{prefix}BLK": safe_convert(stats[15], int),
            f"{prefix}TOV": safe_convert(stats[16], int),
            f"{prefix}PF": safe_convert(stats[17], int),
            f"{prefix}PTS": safe_convert(stats[18], int),
            f"{prefix}GmSc": safe_convert(stats[19], float),
            f"{prefix}Plus_Minus": safe_convert(stats[20], int),
        }

        return player_data

    except Exception:
        return None


# ----------------------------------------------------------------------
# 7. Player advanced stats extraction
# ----------------------------------------------------------------------
def extract_player_advanced_stats(
    html_content: str, visiting_team: str, home_team: str
) -> Dict[str, Any]:
    """
    Extract player advanced stats (Starters and Reserves) for both teams.
    Returns a flat dict with keys like 'VT_ST_P1_TS%', 'HT_RS_P3_DRtg', etc.

    - Starters: up to 5 per team.
    - Reserves: up to MAX_RESERVES per team.
      If there are fewer real reserves, remaining slots are filled
      with all advanced stats set to 0.
    """
    print("\n" + "=" * 60)
    print(" EXTRACTING PLAYER ADVANCED STATS")
    print("=" * 60)

    soup = BeautifulSoup(html_content, "html.parser")

    team_tables = {
        "VT": soup.find("table", {"id": f"box-{visiting_team}-game-advanced"}),
        "HT": soup.find("table", {"id": f"box-{home_team}-game-advanced"}),
    }

    all_advanced_data: Dict[str, Any] = {}
    MAX_RESERVES = 10

    for team_type, table in team_tables.items():
        if not table:
            print(f"[WARN] Advanced stats table not found for {team_type}")
            continue

        print(f"[INFO] Advanced stats table found for {team_type}")

        tbody = table.find("tbody")
        if not tbody:
            print(f"[WARN] Advanced stats tbody not found for {team_type}")
            continue

        all_rows = tbody.find_all("tr")
        starters: List[Any] = []
        reserves: List[Any] = []
        current_section = "starters"

        for row in all_rows:
            th = row.find("th")
            if th and "thead" in row.get("class", []):
                if "Reserves" in th.text:
                    current_section = "reserves"
                continue

            if th and "Team Totals" in th.text:
                continue

            if current_section == "starters":
                starters.append(row)
            else:
                reserves.append(row)

        print(
            f"[INFO] {team_type}: {len(starters)} starters advanced rows, "
            f"{len(reserves)} reserves advanced rows"
        )

        # Starters (up to 5)
        for i, row in enumerate(starters[:5]):
            advanced_data = extract_player_advanced_row_data(
                row, team_type, "ST", i + 1
            )
            if advanced_data:
                all_advanced_data.update(advanced_data)

        # Reserves (real rows, up to MAX_RESERVES)
        reserve_slots_used = 0
        for i, row in enumerate(reserves[:MAX_RESERVES]):
            slot_index = i + 1
            advanced_data = extract_player_advanced_row_data(
                row, team_type, "RS", slot_index
            )
            if advanced_data:
                all_advanced_data.update(advanced_data)
                reserve_slots_used += 1

        # Fill missing reserve slots with zeros (advanced stats)
        if reserve_slots_used < MAX_RESERVES:
            print(
                f"[INFO] {team_type}: filling {MAX_RESERVES - reserve_slots_used} "
                f"empty advanced reserve slots with zeros"
            )

        for slot in range(reserve_slots_used + 1, MAX_RESERVES + 1):
            prefix = f"{team_type}_RS_P{slot}_"
            advanced_placeholder = {
                f"{prefix}TS%": 0.0,
                f"{prefix}eFG%": 0.0,
                f"{prefix}3PAr": 0.0,
                f"{prefix}FTr": 0.0,
                f"{prefix}ORB%": 0.0,
                f"{prefix}DRB%": 0.0,
                f"{prefix}TRB%": 0.0,
                f"{prefix}AST%": 0.0,
                f"{prefix}STL%": 0.0,
                f"{prefix}BLK%": 0.0,
                f"{prefix}TOV%": 0.0,
                f"{prefix}USG%": 0.0,
                f"{prefix}ORtg": 0,
                f"{prefix}DRtg": 0,
                f"{prefix}BPM": 0.0,
            }
            all_advanced_data.update(advanced_placeholder)

    return all_advanced_data


def extract_player_advanced_row_data(
    row, team_type: str, player_type: str, player_num: int
) -> Optional[Dict[str, Any]]:
    """
    Extract advanced stats for a single player row.
    """
    try:
        reason_td = row.find("td", {"data-stat": "reason"})
        prefix = f"{team_type}_{player_type}_P{player_num}_"

        # If player did not play, return all advanced stats as 0
        if reason_td:
            th = row.find("th")
            if th:
                player_link = th.find("a")
                raw_name = player_link.text.strip() if player_link else th.text.strip()
                _normalized_name = normalize_player_name(raw_name)

            advanced_data = {
                f"{prefix}TS%": 0.0,
                f"{prefix}eFG%": 0.0,
                f"{prefix}3PAr": 0.0,
                f"{prefix}FTr": 0.0,
                f"{prefix}ORB%": 0.0,
                f"{prefix}DRB%": 0.0,
                f"{prefix}TRB%": 0.0,
                f"{prefix}AST%": 0.0,
                f"{prefix}STL%": 0.0,
                f"{prefix}BLK%": 0.0,
                f"{prefix}TOV%": 0.0,
                f"{prefix}USG%": 0.0,
                f"{prefix}ORtg": 0,
                f"{prefix}DRtg": 0,
                f"{prefix}BPM": 0.0,
            }
            return advanced_data

        # Normal row with advanced stats
        stats = row.find_all("td")
        if len(stats) < 16:
            return None

        def safe_convert(td, conv, default=0.0):
            try:
                text = td.text.strip()
                if not text:
                    return default
                if conv is float and text.startswith("."):
                    return conv("0" + text)
                return conv(text)
            except Exception:
                return default

        advanced_data = {
            f"{prefix}TS%": safe_convert(stats[1], float),
            f"{prefix}eFG%": safe_convert(stats[2], float),
            f"{prefix}3PAr": safe_convert(stats[3], float),
            f"{prefix}FTr": safe_convert(stats[4], float),
            f"{prefix}ORB%": safe_convert(stats[5], float),
            f"{prefix}DRB%": safe_convert(stats[6], float),
            f"{prefix}TRB%": safe_convert(stats[7], float),
            f"{prefix}AST%": safe_convert(stats[8], float),
            f"{prefix}STL%": safe_convert(stats[9], float),
            f"{prefix}BLK%": safe_convert(stats[10], float),
            f"{prefix}TOV%": safe_convert(stats[11], float),
            f"{prefix}USG%": safe_convert(stats[12], float),
            f"{prefix}ORtg": safe_convert(stats[13], int, default=0),
            f"{prefix}DRtg": safe_convert(stats[14], int, default=0),
            f"{prefix}BPM": safe_convert(stats[15], float),
        }

        return advanced_data

    except Exception:
        return None


# ----------------------------------------------------------------------
# 8. High-level: process a single game and all games
# ----------------------------------------------------------------------
def extract_combined_game_data(game_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Given game_info with fields:
      - date (YYYY-MM-DD)
      - visiting_team (abbr)
      - home_team (abbr)
      - vt_pts, ht_pts

    Fetch HTML and extract:
      - line score (per quarter)
      - four factors
      - player basic stats
      - player advanced stats

    Return a flat dict representing one game (one row for later DataFrame).
    """
    date_str = game_info["date"]
    visiting_team = game_info["visiting_team"]
    home_team = game_info["home_team"]
    url = game_info["url"]

    print("\n" + "=" * 60)
    print(f" PROCESSING GAME: {date_str} - {visiting_team} @ {home_team}")
    print("=" * 60)
    print(f"[URL] {url}")

    success, error_msg, html_content = fetch_html_with_urllib(url)
    if not success or not html_content:
        print(f"[ERROR] Could not download HTML for this game: {error_msg}")
        return None

    line_score_data = extract_line_score(html_content)
    four_factors = extract_four_factors(html_content) or []
    player_basic = extract_player_stats(html_content, visiting_team, home_team)
    player_adv = extract_player_advanced_stats(html_content, visiting_team, home_team)

    game_row: Dict[str, Any] = {
        "Date": date_str,
        "VT": visiting_team,
        "HT": home_team,
        "VT_PTS": int(game_info["vt_pts"]),
        "HT_PTS": int(game_info["ht_pts"]),
    }

    if line_score_data:
        game_row.update(line_score_data)

    if len(four_factors) >= 2:
        ff_vt = four_factors[0]
        ff_ht = four_factors[1]

        game_row.update(
            {
                "VT_pace": ff_vt["pace"],
                "VT_efg_pct": ff_vt["efg_pct"],
                "VT_tov_pct": ff_vt["tov_pct"],
                "VT_orb_pct": ff_vt["orb_pct"],
                "VT_ft_rate": ff_vt["ft_rate"],
                "VT_off_rtg": ff_vt["off_rtg"],
                "HT_pace": ff_ht["pace"],
                "HT_efg_pct": ff_ht["efg_pct"],
                "HT_tov_pct": ff_ht["tov_pct"],
                "HT_orb_pct": ff_ht["orb_pct"],
                "HT_ft_rate": ff_ht["ft_rate"],
                "HT_off_rtg": ff_ht["off_rtg"],
            }
        )

    game_row.update(player_basic)
    game_row.update(player_adv)

    print("[INFO] Game data extracted successfully")
    return game_row

def process_games_from_schedule_df(schedule_df: pd.DataFrame) -> pd.DataFrame:
    """
    High-level function:

    - Build boxscore URLs from schedule_df
    - For each game, fetch and parse HTML
    - Return a combined DataFrame, one row per game

    This function does NOT insert into the database.
    """
    games_urls = build_boxscore_urls_from_schedule_df(schedule_df)

    all_game_rows: List[Dict[str, Any]] = []
    processed = 0
    failed = 0

    for game_info in games_urls:
        combined_data = extract_combined_game_data(game_info)
        if combined_data:
            all_game_rows.append(combined_data)
            processed += 1
        else:
            failed += 1

        print("-" * 60)
        print(f"[SUMMARY] Processed: {processed} | Failed: {failed}")
        print("-" * 60)

    if not all_game_rows:
        print("[FAIL] No games could be processed.")
        return pd.DataFrame()

    df_games = pd.DataFrame(all_game_rows)

    # Desired column order
    desired_columns = [
        "Date",
        "Game_Type",
        "VT",
        "VT_Q1",
        "VT_Q2",
        "VT_Q3",
        "VT_Q4",
        "VT_OT1",
        "VT_OT2",
        "VT_OT3",
        "VT_OT4",
        "VT_Total",
        "VT_pace",      # mapped to VT_Pace
        "VT_efg_pct",   # mapped to VT_eFG%
        "VT_tov_pct",   # mapped to VT_TOV%
        "VT_orb_pct",   # mapped to VT_ORB%
        "VT_ft_rate",   # mapped to VT_FT/FGA
        "VT_off_rtg",   # mapped to VT_ORtg
        "HT",
        "HT_Q1",
        "HT_Q2",
        "HT_Q3",
        "HT_Q4",
        "HT_OT1",
        "HT_OT2",
        "HT_OT3",
        "HT_OT4",
        "HT_Total",
        "HT_pace",
        "HT_efg_pct",
        "HT_tov_pct",
        "HT_orb_pct",
        "HT_ft_rate",
        "HT_off_rtg",
    ]

    # Keep only columns that actually exist in df_games
    existing_order = [c for c in desired_columns if c in df_games.columns]
    other_columns = [c for c in df_games.columns if c not in existing_order]

    # Reorder: first the desired ones in order, then any remaining
    df_games = df_games[existing_order + other_columns]

    # Rename four factors columns to final names
    rename_map = {
        "VT_pace": "VT_Pace",
        "VT_efg_pct": "VT_eFG%",
        "VT_tov_pct": "VT_TOV%",
        "VT_orb_pct": "VT_ORB%",
        "VT_ft_rate": "VT_FT/FGA",
        "VT_off_rtg": "VT_ORtg",
        "HT_pace": "HT_Pace",
        "HT_efg_pct": "HT_eFG%",
        "HT_tov_pct": "HT_TOV%",
        "HT_orb_pct": "HT_ORB%",
        "HT_ft_rate": "HT_FT/FGA",
        "HT_off_rtg": "HT_ORtg",
    }

    df_games = df_games.rename(columns=rename_map)
    
    df_games["Game_Type"] = df_games["Date"].apply(
    lambda x: get_game_type(x, season_key=get_season_key_for_date(x))
    )

    df_games = df_games.sort_values(by="Date", ascending=True).reset_index(drop=True)

    print("\n" + "=" * 60)
    print(" FINAL GAMES DATAFRAME READY")
    print("=" * 60)
    print(f" > Rows: {len(df_games)}")
    print(f" > Columns: {len(df_games.columns)}")
    print("=" * 60)

    return df_games


def generate_test_boxscores_csv(schedule_df: pd.DataFrame, output_dir: str = "scripts/data/raw/boxscores") -> Path:
    """
    Helper function for testing:
    - Process all games in the schedule_df with process_games_from_schedule_df
    - Save the resulting DataFrame as a CSV file
    - Return the Path to the generated CSV

    This does NOT insert into the database, it only writes a CSV.
    """
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(" BOXSCORES SCRAPER - TEST CSV MODE")
    print("=" * 60)

    # Process all games and get a combined DataFrame
    df_games = process_games_from_schedule_df(schedule_df)
    df_games['Game_Type'] = df_games['Date'].apply(lambda x: get_game_type(x, season_key="2024-25"))

    if df_games.empty:
        print("[WARN] Resulting games DataFrame is empty. CSV will not be created.")
        return output_path / "nba_boxscores_test.csv"

    # Build output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"nba_boxscores_test_{timestamp}.csv"

    # Save to CSV
    df_games.to_csv(output_file, index=False)

    print("\n" + "-" * 60)
    print(" TEST BOXSCORES CSV GENERATED")
    print("-" * 60)
    print(f" > File:   {output_file}")
    print(f" > Rows:   {len(df_games)}")
    print(f" > Cols:   {len(df_games.columns)}")
    print("-" * 60)

    return output_file
