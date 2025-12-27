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

def get_dynamic_rate_limit() -> str:
    """
    Returns rate limit string based on tier set by middleware.
    
    NOTE: This function doesn't receive 'request' as parameter because
    SlowAPI 0.1.9 doesn't support it. Instead, we rely on the middleware
    setting request.state.rate_limit_tier before this is called.
    
    Returns:
        str: Rate limit (e.g., "1000/hour")
    """
    # This will be called by SlowAPI with access to request context
    # but we can't receive it as a parameter, so we return a lambda
    # that will be evaluated with the actual request
    return RATE_LIMIT_TIERS["free"]  # Default fallback


# 👇 VERDADERA SOLUCIÓN: Usar lambda con closure
# Esto crea una función que SlowAPI puede llamar con (request)
def rate_limit_by_tier(request: Request) -> str:
    """
    Dynamic rate limit function called by SlowAPI.
    
    Args:
        request: FastAPI Request object (passed by SlowAPI)
        
    Returns:
        str: Rate limit string
    """
    # Get tier from request.state (set by middleware)
    tier = getattr(request.state, "rate_limit_tier", "free")
    limit = RATE_LIMIT_TIERS.get(tier, RATE_LIMIT_TIERS["free"])
    
    print(f"[RATE LIMIT] Tier: {tier} -> Limit: {limit}")
    return limit