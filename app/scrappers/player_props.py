import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
URL = "https://www.scoresandodds.com/nba/props"

PROPS_TO_SCRAPE = [
    "Points",
    "Rebounds",
    "Assists",
    "Blocks",
    "Steals",
    "3 Pointers",
    "Points & Rebounds",
    "Points & Assists",
    "Points, Rebounds, & Assists",
    "Rebounds & Assists"
]

# Dictionary to rename props before saving
PROP_MAPPING = {
    "Points": "P",
    "Rebounds": "R",
    "Assists": "A",
    "Blocks": "B",
    "Steals": "S",
    "3 Pointers": "3P",
    "Points & Rebounds": "PR",
    "Points & Assists": "PA",
    "Points, Rebounds, & Assists": "PRA",
    "Rebounds & Assists": "RA"
}

def clean_line_value(text):
    """Parses numeric value from strings like 'o31.5' or 'u32.5'."""
    if not text:
        return None
    match = re.search(r"(\d+(\.\d+)?)", text)
    if match:
        return float(match.group(1))
    return None

def clean_odds(text):
    """Parses betting odds to integer (e.g., '-110')."""
    if not text:
        return None
    try:
        return int(text.replace("+", ""))
    except ValueError:
        return None

def handle_cookie_banner(driver, wait):
    """Closes the cookie banner to avoid interaction issues."""
    try:
        accept_btn = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
        accept_btn.click()
        print("[INFO] Cookie banner closed.")
        time.sleep(1)
    except:
        pass

def scrape_nba_props() -> pd.DataFrame:
    """
    Scrapes NBA player props and odds using Selenium.
    Returns a DataFrame with the following columns:
    name, last_name, player_team, opp_team, prop, line, over_odds, under_odds
    """
    options = webdriver.ChromeOptions()
    # Headless mode for Linux/GitHub Actions
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    all_data = []

    try:
        print(f"[STATUS] Accessing: {URL}")
        driver.get(URL)
        wait = WebDriverWait(driver, 15)
        
        handle_cookie_banner(driver, wait)
        
        # Wait for props picker
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "filters-prop-picker")))

        for prop_name in PROPS_TO_SCRAPE:
            print(f"\n--- Scraping: {prop_name} ---")
            
            try:
                # Open dropdown
                dropdown_trigger = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.filters-prop-picker span[data-role='openable']")
                ))
                driver.execute_script("arguments[0].click();", dropdown_trigger)
                time.sleep(1) 
                
                # Select prop option
                options_list = driver.find_elements(By.CSS_SELECTOR, "ul#prop-options li")
                target_option = None
                for opt in options_list:
                    try:
                        span_text = opt.find_element(By.TAG_NAME, "span").text.strip()
                        if span_text == prop_name:
                            target_option = opt
                            break
                    except:
                        continue
                
                if target_option:
                    driver.execute_script("arguments[0].click();", target_option)
                    print(f"  [OK] Selected: {prop_name}")
                else:
                    print(f"  [WARN] Option not found: {prop_name}")
                    driver.execute_script("document.body.click();")
                    continue

                # Wait for results to update
                time.sleep(4) 
                
                # Find table items
                try:
                    ul_table = driver.find_element(By.CSS_SELECTOR, "ul.table-list")
                    items = ul_table.find_elements(By.TAG_NAME, "li")
                except:
                    print(f"  [INFO] No data for {prop_name}")
                    items = []

                for li in items:
                    if "border" not in (li.get_attribute("class") or ""):
                        continue
                        
                    try:
                        # Player Name
                        name_tag = li.find_element(By.CSS_SELECTOR, "div.props-name a")
                        full_name = name_tag.text.strip()
                        p_name, p_last_name = full_name.split(" ", 1) if " " in full_name else (full_name, "")

                        # Team Information
                        teams_span = li.find_element(By.CSS_SELECTOR, "div.props-name span.bold.small.gray")
                        teams_text = teams_span.text.strip().replace(" vs ", " @ ").replace(" VS ", " @ ")
                        
                        if "@" in teams_text:
                            parts = teams_text.split("@")
                            player_team = parts[0].strip()
                            opp_team = parts[1].strip()
                        else:
                            player_team, opp_team = teams_text, "N/A"

                        # Line and Odds Containers
                        # Expected: 2 containers for 'best-odds row' (Over and Under)
                        odds_rows = li.find_elements(By.CSS_SELECTOR, "div.best-odds.row")
                        
                        prop_line = None
                        o_odds = None
                        u_odds = None

                        if len(odds_rows) >= 2:
                            # Over Data
                            over_container = odds_rows[0]
                            try:
                                line_span = over_container.find_element(By.CSS_SELECTOR, "span.data-moneyline")
                                o_odds_tag = over_container.find_element(By.CSS_SELECTOR, "small.data-odds.best")
                                prop_line = clean_line_value(line_span.text.strip())
                                o_odds = clean_odds(o_odds_tag.text.strip())
                            except:
                                pass

                            # Under Data
                            under_container = odds_rows[1]
                            try:
                                u_odds_tag = under_container.find_element(By.CSS_SELECTOR, "small.data-odds.best")
                                u_odds = clean_odds(u_odds_tag.text.strip())
                            except:
                                pass

                        # Only add if we have a valid line
                        if prop_line is not None:
                            all_data.append({
                                "name": p_name,
                                "last_name": p_last_name,
                                "player_team": player_team,
                                "opp_team": opp_team,
                                "prop": prop_name,
                                "line": prop_line,
                                "over_odds": o_odds,
                                "under_odds": u_odds
                            })

                    except Exception:
                        continue
                
            except Exception as e:
                print(f"  [ERROR] Block error {prop_name}: {e}")
                continue

    except Exception as main_e:
        print(f"[FATAL] Critical failure: {main_e}")
    finally:
        driver.quit()
        
    if not all_data:
        print("[ERROR] No data scraped.")
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df["prop"] = df["prop"].replace(PROP_MAPPING)
    
    print(f"\n[DONE] Scraped {len(df)} player props.")
    return df

if __name__ == "__main__":
    df_results = scrape_nba_props()
    if not df_results.empty:
        print(df_results.head())
        df_results.to_csv("test_props.csv", index=False)
