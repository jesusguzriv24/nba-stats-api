"""
Main FastAPI application entry point.

This is the core application file that:
- Initializes the FastAPI app
- Configures middleware (CORS, rate limiting, logging)
- Mounts API routers
- Sets up lifespan events (startup/shutdown)
- Configures error handlers
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import List
from fastapi.security import HTTPBearer, APIKeyHeader

from app.core.database import engine, Base
from app.api.v1.router import api_v1_router
from app.core.middleware import (rate_limit_headers_middleware, usage_logging_middleware, request_id_middleware)


# --- Lifespan events (startup / shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events for the application.
    
    On startup:
    - Prints startup banner
    - Creates database tables if they don't exist
    - Initializes connections (Redis, etc.)
    
    On shutdown:
    - Prints shutdown banner
    - Closes connections gracefully
    
    Args:
        app (FastAPI): The FastAPI application instance
    """
    print("\n" + "-" * 50)
    print("      STARTING UP NBA STATS API      ")
    print("-" * 50)

    # Create database tables if they don't exist
    # Note: In production, use Alembic migrations instead
    async with engine.begin() as conn:
        # Import all models to ensure they're registered with Base.metadata

        from app.models import (user, api_key, subscription_plan, user_subscription, api_usage_log, api_usage_aggregate)
        await conn.run_sync(Base.metadata.create_all)
        print(" >> Database tables verified/created")

    print(" >> API is ready to accept requests")
    print("=" * 50 + "\n")

    yield

    # Shutdown
    print("\n" + "-" * 50)
    print("      SHUTTING DOWN API      ")
    print("-" * 50 + "\n")


# --- FastAPI application instance ---
app = FastAPI(
    title="NBA Stats API",
    version="1.0.0",
    lifespan=lifespan,
    description="""
    API for NBA statistics with subscription-based rate limiting.

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

    **Free Plan:** 10 req/min, 100 req/hour, 1,000 req/day
    **Premium Plan:** 100 req/min, 1,000 req/hour, 10,000 req/day
    **Pro Plan:** 1,000 req/min, 10,000 req/hour, 100,000 req/day

    Response headers:
    - `X-RateLimit-Limit`: Total request limit
    - `X-RateLimit-Remaining`: Remaining requests
    - `X-RateLimit-Reset`: Unix timestamp when limit resets
    """
)

# --- CORS configuration ---
# Allowed origins for browser-based clients (e.g. Next.js frontend).
# In development, localhost:3000 is common for Next.js.
# In production, add your real frontend domain (e.g. https://my-frontend.com).
origins = [
    "http://localhost:3000",        # Local Next.js dev server
    # "https://your-frontend.com",  # Production frontend (uncomment and adjust)
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Explicit list of allowed origins
    allow_credentials=True,
    allow_methods=["*"],            # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],            # Allow all headers
    expose_headers=[
        "x-ratelimit-limit-day",
        "x-ratelimit-remaining-day",
        "x-ratelimit-reset-day",
        "x-ratelimit-limit-minute", 
        "x-ratelimit-remaining-minute"
    ]
)

# Add custom middleware in correct order (LIFO - Last In, First Out execution)
# Order matters! Middleware is executed in reverse order of addition

# 1. Request ID middleware (first to execute, adds ID to all requests)
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Wrapper for request_id_middleware"""
    return await request_id_middleware(request, call_next)


# 2. Usage logging middleware (logs all requests with request ID)
@app.middleware("http")
async def log_usage(request: Request, call_next):
    """Wrapper for usage_logging_middleware"""
    return await usage_logging_middleware(request, call_next)


# 3. Rate limit headers middleware (adds headers after rate limit check)
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    """Wrapper for rate_limit_headers_middleware"""
    return await rate_limit_headers_middleware(request, call_next)

# --- Mount versioned API routers ---
# All versioned routes are exposed under /api/v1.
app.include_router(api_v1_router, prefix="/api/v1")

# --- Root health / welcome endpoint --- 
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information and health check.
    
    Returns basic information about the API including version,
    documentation links, and available endpoints.
    
    Returns:
        dict: API information
    """
    return {
        "message": "Welcome to the NBA Stats API",
        "version": "1.0.0",
        "status": "OK",
        "docs": "/docs",
        "authentication": {
            "jwt": "Authorization: Bearer <token>",
            "api_key": "X-API-Key: <key>"
        },
        "rate_limiting": {
            "free": "10/min, 100/hour, 1,000/day",
            "premium": "100/min, 1,000/hour, 10,000/day",
            "pro": "1,000/min, 10,000/hour, 100,000/day"
        }
    }

# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for uncaught exceptions.
    
    Catches any unhandled exceptions and returns a standardized
    error response instead of exposing internal error details.
    
    Args:
        request (Request): The request that caused the exception
        exc (Exception): The exception that was raised
        
    Returns:
        JSONResponse: Standardized error response
    """
    print(f"[GLOBAL ERROR HANDLER] Unhandled exception:")
    print(f"  Path: {request.url.path}")
    print(f"  Method: {request.method}")
    print(f"  Error: {type(exc).__name__}: {str(exc)}")
    
    # Don't expose internal error details in production
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": getattr(request.state, "request_id", None)
        }
    )

# Run application with uvicorn (for development only)
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (development only)
        log_level="info"
    )
