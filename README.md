# NBA Stats API

NBA Stats API is a FastAPI-based service that exposes NBA games, teams, players, and advanced stats from your PostgreSQL database. It is designed both for frontend consumption and for analytics/ML workflows.

## Overview

The API is built with:
- **FastAPI** (async)
- **SQLAlchemy Async** + **PostgreSQL**
- **Pydantic** schemas for validation and responses

**Core resources exposed:**
- **Teams** (`/api/v1/teams`)
- **Players** (`/api/v1/players`)
- **Games** (`/api/v1/games`)
- **Boxscores** (`/api/v1/games/{game_id}/boxscore`)
- **Team advanced stats rankings** (`/api/v1/stats/teams`)

## Project Structure

```bash
app/
  ├── main.py                 # FastAPI app, lifespan, include v1 router
  ├── core/
  │   └── database.py         # Async engine, AsyncSessionLocal, Base, get_db()
  ├── models/
  │   ├── team.py             # Team model
  │   ├── player.py           # Player model
  │   ├── game.py             # Game model
  │   ├── player_game_stats.py
  │   └── team_game_stats.py
  ├── schemas/
  │   ├── team.py             # TeamCreate, TeamResponse
  │   ├── player.py           # PlayerCreate, PlayerResponse
  │   ├── game.py             # GameCreate, GameResponse
  │   ├── player_game_stats.py
  │   ├── team_game_stats.py
  │   └── boxscore.py         # GameBoxscoreResponse
  └── api/
      └── v1/
          ├── router.py       # Aggregates v1 routes
          └── endpoints/      # API Routes definition
              ├── teams.py
              ├── players.py
              ├── games.py
              └── stats.py
```

## Setup

### Requirements
- Python 3.11+ (recommended)
- PostgreSQL database with populated tables (scripts provided)
- `DATABASE_URL` in `.env` following this format:
  ```text
  DATABASE_URL=postgres://user:password@host:port/dbname
  ```
  `app/core/database.py` handles: stripping `sslmode`, switching scheme to `postgresql+asyncpg://`, and creating the async engine and `AsyncSessionLocal`.

### Install Dependencies
Example using pip:
```bash
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg python-dotenv
```
(Adjust according to your package manager: Poetry, pipenv, etc.)

### Running the API
From the project root:
```bash
uvicorn app.main:app --port 8001 --reload
```
`--reload` enables hot reloading for development.

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## Lifespan & Database

`app/main.py` defines an async lifespan context which:
- **On Startup**: Creates all tables (`Base.metadata.create_all`) against the async engine.
- **On Shutdown**: Prints shutdown messages.

The `get_db` dependency in `app/core/database.py` provides an async session per request and closes it automatically.

## API v1

All version 1 routes are mounted under the `/api/v1` prefix.

### Teams Resources

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/teams` | List all teams. Supports filtering by conference, division, and search terms. |
| **GET** | `/teams/{team_id}` | Get details of a specific team by ID. |
| **GET** | `/teams/{team_id}/games` | Get games for a specific team. Supports season filtering. |

**Parameters:**
- `conference`: string (e.g., "East", "West")
- `division`: string
- `search`: search in full_name, city, name, abbreviation
- `is_playoffs`: boolean

### Players Resources

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/players` | List all players. Supports filtering by team, position, and name search. |
| **GET** | `/players/{player_id}` | Get details of a specific player profile. |
| **GET** | `/players/{player_id}/games` | Get game-by-game stats (boxscores) for a player. |

**Parameters:**
- `team_id`: filter by current team
- `position`: exact match (e.g., "G", "F")
- `search`: partial match against "first_name last_name"

### Games & Boxscores Resources

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/games` | List games. Filter by date range, season, teams, and playoffs. |
| **GET** | `/games/{game_id}` | Get basic info for a specific game. |
| **GET** | `/games/{game_id}/boxscore` | **Full Boxscore**: Includes game info, team stats, and all player stats. |
| **GET** | `/games/{game_id}/team-stats` | Advanced team stats for the game (home & visitor). |
| **GET** | `/games/{game_id}/player-stats` | Individual player stats for the game. |

**Parameters:**
- `season`: integer
- `from_date`, `to_date`: YYYY-MM-DD
- `is_playoffs`: boolean

### Stats & Rankings Resources

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/stats/teams` | Team rankings by season. Averages of advanced stats. |

**Parameters:**
- `season` (Required): Season year (e.g., 2025 for 2024-25).
- `sort_by`: `"offensive_rating"`, `"defensive_rating"`, or `"pace"`.
- `limit`: max results (default 30).

---

## Usage Examples

### 1. List Teams
```bash
curl "http://localhost:8001/api/v1/teams?search=nets"
```

### 2. Get Team Games (2024-25 Regular Season)
```bash
curl "http://localhost:8001/api/v1/teams/2/games?season=2024&is_playoffs=false&limit=20"
```

### 3. Get Player Boxscores (Season)
```bash
curl "http://localhost:8001/api/v1/players/201939/games?season=2024"
```

### 4. Get Full Game Boxscore
```bash
curl "http://localhost:8001/api/v1/games/12345/boxscore"
```

**Response Snippet:**
```json
{
  "game": { 
    "id": 12345,
    "home_team": { "abbreviation": "BOS" },
    "visitor_team": { "abbreviation": "NYK" },
    "home_score": 110,
    "visitor_score": 105
   },
  "team_stats": [ ... ],
  "player_stats": [ ... ]
}
```

### 5. Get Team Rankings (Offensive Rating)
```bash
curl "http://localhost:8001/api/v1/stats/teams?season=2024&sort_by=offensive_rating"
```

**Response Snippet:**
```json
[
  {
    "team_id": 1,
    "pace": 98.7,
    "offensive_rating": 115.2,
    "defensive_rating": 110.3,
    "effective_fg_pct": 0.543,
    "true_shooting_pct": 0.585
  }
]
```
These values are season averages calculated via SQL aggregation.
