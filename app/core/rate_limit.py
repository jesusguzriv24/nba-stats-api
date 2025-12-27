"""
Rate limiting configuration and utilities.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from typing import Optional, Callable


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


# Initialize limiter
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["100/hour"],  # Default limit for unauthenticated requests
    storage_uri="memory://",  # Use in-memory storage (change to Redis in production)
    strategy="fixed-window"
)


# Rate limit tiers
RATE_LIMIT_TIERS = {
    "free": "100/hour",      # Free tier: 100 requests/hour
    "pro": "1000/hour",      # Pro tier: 1000 requests/hour
    "enterprise": "10000/hour"  # Enterprise: 10000 requests/hour
}


def get_rate_limit_for_user(request: Request) -> str:
    """
    Get rate limit based on user's tier.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Rate limit string (e.g., "1000/hour")
    """
    # Check if user is authenticated and has a tier
    if hasattr(request.state, "user") and request.state.user:
        tier = request.state.user.rate_limit_tier
        limit = RATE_LIMIT_TIERS.get(tier, RATE_LIMIT_TIERS["free"])
        print(f"[RATE LIMIT] User {request.state.user.email} tier: {tier} -> {limit}")
        return limit
    
    # Default to free tier
    print(f"[RATE LIMIT] No authenticated user, using default: {RATE_LIMIT_TIERS['free']}")
    return RATE_LIMIT_TIERS["free"]
