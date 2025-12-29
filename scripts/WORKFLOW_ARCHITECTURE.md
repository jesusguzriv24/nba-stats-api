"""
Workflow Architecture and Flow Diagram

This document explains the complete workflow architecture and data flow
for the NBA Stats API test scripts.
"""

"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    NBA STATS API - TEST WORKFLOW                          ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: USER CREATION                                                   │
└──────────────────────────────────────────────────────────────────────────┘

    user_generator.py::create_test_user()
    ↓
    ┌─────────────────────────────────────┐
    │ 1. Check if user exists             │
    │ 2. Generate Supabase UUID (dummy)   │
    │ 3. Create User record               │
    │ 4. Store in users table             │
    └─────────────────────────────────────┘
    ↓
    User object created
    └─ id: int
    └─ email: str
    └─ supabase_user_id: UUID
    └─ role: 'user'
    └─ is_active: True
    └─ created_at: DateTime
    └─ updated_at: DateTime


┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: SUBSCRIPTION ASSIGNMENT                                         │
└──────────────────────────────────────────────────────────────────────────┘

    subscription_generator.py::assign_free_subscription()
    ↓
    ┌─────────────────────────────────────┐
    │ 1. Get or create SubscriptionPlan   │
    │    - plan_name: 'free'              │
    │    - rate_limit_per_minute: 10      │
    │    - rate_limit_per_hour: 100       │
    │    - rate_limit_per_day: 1000       │
    │    - price: $0 USD                  │
    │                                     │
    │ 2. Create UserSubscription record   │
    │ 3. Link user to plan                │
    │ 4. Set billing period (1 month)     │
    │ 5. Store in user_subscriptions      │
    └─────────────────────────────────────┘
    ↓
    UserSubscription object created
    └─ id: int
    └─ user_id: FK → User
    └─ plan_id: FK → SubscriptionPlan
    └─ status: 'active'
    └─ subscribed_at: DateTime
    └─ current_period_start: DateTime
    └─ current_period_end: DateTime (1 month from now)


┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: API KEY GENERATION                                              │
└──────────────────────────────────────────────────────────────────────────┘

    apikey_generator.py::create_api_key_for_user()
    ↓
    ┌─────────────────────────────────────┐
    │ 1. Generate secure random token     │
    │    using secrets.token_urlsafe()    │
    │                                     │
    │ 2. Prepend prefix: 'bestat_nba_'   │
    │                                     │
    │ 3. Hash with Argon2                 │
    │    (security.generate_api_key())    │
    │                                     │
    │ 4. Extract last 8 chars             │
    │                                     │
    │ 5. Create APIKey record             │
    │ 6. Store hash in database           │
    └─────────────────────────────────────┘
    ↓
    APIKey object created (database)     |    key_response (returned)
    ├─ id: int                           |    ├─ key: str (full, shown once)
    ├─ user_id: FK → User                |    ├─ key_hash: str (Argon2)
    ├─ key_hash: str (Argon2)            |    ├─ last_chars: str (...abcd)
    ├─ name: str                         |    └─ api_key_id: int
    ├─ last_chars: str                   |
    ├─ is_active: True                   |
    ├─ rate_limit_plan: 'free'           |
    ├─ created_at: DateTime              |
    └─ expires_at: DateTime              |


┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: API TESTING WITH RATE LIMITING                                  │
└──────────────────────────────────────────────────────────────────────────┘

    api_client.py::APIClient::test_endpoints_until_rate_limited()
    ↓
    For each request:
    ┌─────────────────────────────────────────────────────────┐
    │ 1. Add X-API-Key header to request                      │
    │    X-API-Key: bestat_nba_<token>                        │
    │                                                         │
    │ 2. Make HTTP GET request to endpoint                    │
    │    GET /v1/games/ HTTP/1.1                             │
    │    Host: localhost:8000                                │
    │    X-API-Key: bestat_nba_<token>                       │
    │                                                         │
    │ 3. Server-side (dependencies.py):                      │
    │    a. Extract X-API-Key header                         │
    │    b. Query database for matching API key              │
    │    c. Verify key using Argon2 hash                    │
    │    d. Get user and subscription                        │
    │    e. Check rate limits (Redis):                       │
    │       - Per minute: count in current minute             │
    │       - Per hour: count in current hour                 │
    │       - Per day: count in current day                   │
    │    f. If limit exceeded → return 429 Too Many Requests  │
    │    g. Log request to api_usage_logs                    │
    │    h. Return data                                       │
    │                                                         │
    │ 4. Client receives response:                            │
    │    - 200 OK → Request counted, continue                │
    │    - 429 Too Many Requests → Rate limited, stop        │
    │    - 4xx/5xx → Log error, continue                     │
    │                                                         │
    │ 5. Repeat with next endpoint (cycling through list)    │
    │                                                         │
    │ 6. Continue until:                                      │
    │    - HTTP 429 received (preferred), OR                 │
    │    - 1000 requests made (safety limit)                 │
    └─────────────────────────────────────────────────────────┘
    ↓
    Summary statistics:
    ├─ total_requests: int
    ├─ successful_requests: int
    ├─ failed_requests: int
    ├─ elapsed_time_seconds: float
    ├─ requests_per_minute: float
    ├─ rate_limited: bool
    └─ rate_limited_at: DateTime


╔═══════════════════════════════════════════════════════════════════════════╗
║                        DATABASE SCHEMA REFERENCE                          ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌──────────────┐         ┌─────────────────────┐        ┌──────────────────┐
│    users     │         │  subscription_plans │        │   api_keys       │
├──────────────┤         ├─────────────────────┤        ├──────────────────┤
│ id (PK)      │         │ id (PK)             │        │ id (PK)          │
│ email        │         │ plan_name (UQ)      │        │ user_id (FK)     │
│ supabase_id  │         │ display_name        │        │ key_hash         │
│ role         │         │ description         │        │ name             │
│ is_active    │         │ rate_limit_minute   │        │ last_chars       │
│ created_at   │         │ rate_limit_hour     │        │ is_active        │
│ updated_at   │         │ rate_limit_day      │        │ rate_limit_plan  │
└──────────────┘         │ price_monthly_cents │        │ created_at       │
       ▲                 │ price_yearly_cents  │        │ expires_at       │
       │                 │ is_active           │        │ revoked_at       │
       │                 │ features            │        └──────────────────┘
       │                 │ display_order       │                 │
       │                 └─────────────────────┘                 │
       │                         ▲                               │
       │                         │                               │
       │                         │                               │
       │         ┌───────────────────────────┐                   │
       │         │  user_subscriptions       │                   │
       │         ├───────────────────────────┤                   │
       │         │ id (PK)                   │                   │
       └─────────┤ user_id (FK) ─────────────┼───────────────────┘
                 │ plan_id (FK) ─────┐       │
                 │ status            │       │
                 │ subscribed_at     │       │
                 │ current_period_start│     │
                 │ current_period_end│       │
                 │ billing_cycle     │       │
                 │ payment_provider  │       │
                 └───────────────────┼───────┘
                                     │
                                     ↓
                          (references SubscriptionPlan)


╔═══════════════════════════════════════════════════════════════════════════╗
║                            RATE LIMITING FLOW                             ║
╚═══════════════════════════════════════════════════════════════════════════╝

Request arrives with X-API-Key header
        ↓
Verify API key against database (Argon2 hash)
        ↓
Get user and their active subscription
        ↓
Extract rate limit plan from subscription:
    └─ per_minute: 10
    └─ per_hour: 100
    └─ per_day: 1000
        ↓
Check Redis counters for this user:
    
    Key format: ratelimit:user:<user_id>:<window>:<timestamp>
    
    ├─ Per minute window:
    │  Key: ratelimit:user:1:minute:1735430400
    │  Count requests in last 60 seconds
    │  Expires: 60 seconds after last request
    │
    ├─ Per hour window:
    │  Key: ratelimit:user:1:hour:1735430400
    │  Count requests in last 3600 seconds
    │  Expires: 3600 seconds after last request
    │
    └─ Per day window:
       Key: ratelimit:user:1:day:20250101
       Count requests in last 86400 seconds
       Expires: 86400 seconds after last request
        ↓
If any counter exceeds limit:
    └─ Return 429 Too Many Requests
       └─ Client stops making requests
       └─ Rate limit goal achieved! ✓
        ↓
Otherwise:
    ├─ Increment all three counters
    ├─ Process request
    ├─ Log to api_usage_logs
    └─ Return 200 OK


╔═══════════════════════════════════════════════════════════════════════════╗
║                         API SECURITY FLOW                                 ║
╚═══════════════════════════════════════════════════════════════════════════╝

1. KEY GENERATION (at creation time):
   ┌──────────────────────────────────────┐
   │ Generate: "bestat_nba_xK9mP2vQ7sL4..." (never stored)
   │          ↓
   │ Hash:     "$argon2id$v=19$m=65540,..." (stored in DB)
   │          ↓
   │ Display:  "...sL4nR8" (shown in UI)
   └──────────────────────────────────────┘

2. KEY VERIFICATION (at each request):
   ┌──────────────────────────────────────┐
   │ Client provides: "bestat_nba_xK9mP2..."
   │                 ↓
   │ Compare using pwd_context.verify()
   │ (secure constant-time comparison)
   │                 ↓
   │ If match: Allow request ✓
   │ If no match: Reject with 401 ✗
   └──────────────────────────────────────┘

3. KEY REVOCATION:
   ┌──────────────────────────────────────┐
   │ Set is_active = False
   │ Set revoked_at = NOW()
   │          ↓
   │ Future requests with this key
   │ are rejected with 401
   └──────────────────────────────────────┘


╔═══════════════════════════════════════════════════════════════════════════╗
║                         MODULE DEPENDENCIES                               ║
╚═══════════════════════════════════════════════════════════════════════════╝

main_test_flow.py
    ├── imports user_generator.py
    │   └── imports app.models.user
    │       └── imports app.core.database
    │
    ├── imports subscription_generator.py
    │   ├── imports app.models.user_subscription
    │   ├── imports app.models.subscription_plan
    │   └── imports app.core.database
    │
    ├── imports apikey_generator.py
    │   ├── imports app.models.api_key
    │   ├── imports app.core.security (generate_api_key)
    │   └── imports app.core.database
    │
    └── imports api_client.py
        └── uses httpx (external HTTP client)

config.py
    └── uses dotenv (load environment variables)


╔═══════════════════════════════════════════════════════════════════════════╗
║                         EXECUTION TIMELINE                                ║
╚═══════════════════════════════════════════════════════════════════════════╝

Time  │ Action                                    │ Duration
──────┼───────────────────────────────────────────┼──────────
T+0s  │ Start: Create test user                   │
T+1s  │ ✓ User created (ID: 1)                    │ 1s
      │                                           │
T+1s  │ Start: Assign free subscription           │
T+2s  │ ✓ Subscription created (ID: 1)            │ 1s
      │                                           │
T+2s  │ Start: Generate API key                   │
T+3s  │ ✓ API key created (ID: 1)                 │ 1s
      │                                           │
T+3s  │ Start: Test API endpoints                 │
T+3s  │ Request 1: /v1/games/ → 200 OK            │ 50ms delay
T+3s  │ Request 2: /v1/players/ → 200 OK          │ 50ms delay
T+4s  │ Request 3: /v1/teams/ → 200 OK            │ 50ms delay
T+4s  │ Request 4: /v1/games/ → 200 OK            │ 50ms delay
...   │ ...                                       │
T+5s  │ Request 10: /v1/teams/ → 429 Rate Limited │ 50ms delay
T+5s  │ ✓ Rate limit reached!                     │ ~2s
      │                                           │
T+5s  │ ✓ Test completed successfully             │ ~5s total
──────┴───────────────────────────────────────────┴──────────
"""

# This is a documentation file - no executable code below
