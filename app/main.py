from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from typing import List
from fastapi.security import HTTPBearer, APIKeyHeader

from app.core.database import engine, Base
from app.api.v1.router import api_v1_router
from app.core.rate_limit import limiter

from slowapi.middleware import SlowAPIMiddleware


# --- Lifespan events (startup / shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context.

    On startup:
      - Log startup banner.
      - Ensure all database tables exist (create if missing).

    On shutdown:
      - Log shutdown banner.
    """
    print("\n" + "-" * 50)
    print("      STARTING UP NBA STATS API      ")
    print("-" * 50)

    async with engine.begin() as conn:
        # Create tables automatically if they do not exist
        await conn.run_sync(Base.metadata.create_all)

    yield

    print("\n" + "-" * 50)
    print("      SHUTTING DOWN API      ")
    print("-" * 50 + "\n")


# --- FastAPI application instance ---
app = FastAPI(
    title="NBA Stats API",
    version="1.0.0",
    lifespan=lifespan,
    description="""
    Public NBA statistics API with authentication.

    ## Authentication

    This API supports **two authentication methods**:

    ### 1. Supabase JWT (for web users)
    - Sign up through the frontend
    - Use the JWT token in the header: `Authorization: Bearer <token>`

    ### 2. API Key (for developers/scripts)
    - Generate your API key from `/users/me/api-keys`
    - Use the key in the header: `X-API-Key: <your-api-key>`

    All read-only endpoints require authentication.

    ----------- Rate Limiting -----------

    **Free Tier:** 100 requests/hour  
    **Pro Tier:** 1,000 requests/hour  
    **Enterprise Tier:** 10,000 requests/hour

    Response headers:
    - `X-RateLimit-Limit`: Total request limit
    - `X-RateLimit-Remaining`: Remaining requests
    - `X-RateLimit-Reset`: Unix timestamp when limit resets
    """
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# --- CORS configuration ---
# Allowed origins for browser-based clients (e.g. Next.js frontend).
# In development, localhost:3000 is common for Next.js.
# In production, add your real frontend domain (e.g. https://my-frontend.com).
origins = [
    "http://localhost:3000",        # Local Next.js dev server
    # "https://your-frontend.com",  # Production frontend (uncomment and adjust)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Explicit list of allowed origins
    allow_credentials=True,
    allow_methods=["*"],            # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],            # Allow all headers
)


# --- Root health / welcome endpoint --- 
@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request):
    """
    Simple health/welcome endpoint.

    Can be used by uptime checks or to verify that the API is running.
    """
    return {
        "message": "Welcome to the NBA Stats API",
        "status": "OK",
        "docs": "/docs",
        "authentication": {
            "jwt": "Authorization: Bearer <token>",
            "api_key": "X-API-Key: <key>"
        },
        "rate_limiting": {
            "free": "100/hour",
            "pro": "1000/hour",
            "enterprise": "10000/hour"
        }
    }


# --- Mount versioned API routers ---
# All versioned routes are exposed under /api/v1.
app.include_router(api_v1_router, prefix="/api/v1")
