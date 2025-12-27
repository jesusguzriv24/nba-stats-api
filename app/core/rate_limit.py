"""
Rate limiting configuration and utilities.
"""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from typing import Optional, Callable
from contextvars import ContextVar

# Context variable to store rate limit tier for current request
_rate_limit_tier: ContextVar[str] = ContextVar("rate_limit_tier", default="free")

def get_rate_limit_key(request: Request) -> str:
    """
    Custom key function for rate limiting.
    
    Priority:
    1. API Key (if present) - more granular control
    2. User ID from JWT (if authenticated)
    3. IP address (fallback)
    
    Returns:
        str: Unique identifier for rate limiting
    """
    # Check for API key in headers
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # Use last 16 chars of API key for identification
        return f"api_key:{api_key[-16:]}"
    
    # Check for authenticated user (JWT)
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"
    
    # Fallback to IP address
    return f"ip:{get_remote_address(request)}"


# Get Redis URL from environment
redis_url = os.getenv("REDIS_URL", "memory://")

# If Redis URL is not configured, use in-memory storage (for local dev)
if redis_url == "memory://":
    print("\n" + "="*60)
    print("⚠️  WARNING: Redis URL not configured")
    print("   Using in-memory storage (not recommended for production)")
    print("   Set REDIS_URL environment variable to use Redis")
    print("="*60 + "\n")

# Initialize limiter
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["100/hour"],  # Default limit for unauthenticated requests
    storage_uri=redis_url,  # Use in-memory storage (change to Redis in production)
    strategy="fixed-window",
    headers_enabled=True,
)

print(f"\nRate limiter initialized with storage: {redis_url}\n")

# Rate limit tiers
RATE_LIMIT_TIERS = {
    "free": "100/hour",      # Free tier: 100 requests/hour
    "pro": "1000/hour",      # Pro tier: 1000 requests/hour
    "enterprise": "10000/hour"  # Enterprise: 10000 requests/hour
}

def get_dynamic_rate_limit() -> str:
    """
    Returns rate limit based on tier stored in ContextVar.
    
    This function is called by SlowAPI WITHOUT arguments.
    The middleware sets the tier in a ContextVar that this function reads.
    
    Returns:
        str: Rate limit string (e.g., "1000/hour")
    """
    tier = _rate_limit_tier.get()
    limit = RATE_LIMIT_TIERS.get(tier, RATE_LIMIT_TIERS["free"])
    print(f"[RATE LIMIT] Tier: {tier} -> Limit: {limit}")
    return limit


def set_rate_limit_tier(tier: str) -> None:
    """
    Set the rate limit tier for the current request context.
    
    Called by middleware to set the tier before SlowAPI checks limits.
    
    Args:
        tier: Rate limit tier ("free", "pro", or "enterprise")
    """
    _rate_limit_tier.set(tier)