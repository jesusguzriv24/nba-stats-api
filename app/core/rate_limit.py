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

class DynamicRateLimit:
    """
    Callable class that returns dynamic rate limits based on user tier.
    
    SlowAPI will instantiate this and call it with: callable(request)
    """
    
    def __call__(self, request: Request) -> str:
        """
        Returns rate limit string based on authenticated user's tier.
        
        This is called by SlowAPI BEFORE the endpoint dependencies run,
        so we need to perform authentication here synchronously.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            str: Rate limit (e.g., "1000/hour")
        """
        # IMPORTANT: We can't access request.state.user here because
        # dependencies haven't run yet. We need to check headers directly.
        
        # Try to get user tier from a custom header (set by middleware)
        user_tier = getattr(request.state, "rate_limit_tier", None)
        
        if user_tier:
            limit = RATE_LIMIT_TIERS.get(user_tier, RATE_LIMIT_TIERS["free"])
            print(f"[RATE LIMIT] Dynamic tier: {user_tier} -> {limit}")
            return limit
        
        # Default to free tier
        default = RATE_LIMIT_TIERS["free"]
        print(f"[RATE LIMIT] No tier found, using default: {default}")
        return default

# Create singleton instance
dynamic_rate_limit = DynamicRateLimit()