"""
Custom middleware for setting rate limit tier before SlowAPI check.
"""
from fastapi import Request
from app.core.security import verify_api_key
from app.models.api_key import APIKey
from app.models.user import User
from sqlalchemy import select
from app.core.database import async_session_maker
from app.core.rate_limit import set_rate_limit_tier, limiter, RATE_LIMIT_TIERS
import time

async def rate_limit_tier_middleware(request: Request, call_next):
    """
    Middleware that sets rate_limit_tier in ContextVar BEFORE SlowAPI runs.
    """
    # Default tier
    tier = "free"
    
    # Check for API key
    api_key = request.headers.get("X-API-Key")
    
    if api_key:
        try:
            async with async_session_maker() as db:
                # Query active API keys
                result = await db.execute(
                    select(APIKey)
                    .where(APIKey.is_active == True)
                    .where(APIKey.revoked_at == None)
                )
                active_keys = result.scalars().all()
                
                # Find matching key
                matched_key = None
                for db_key in active_keys:
                    if verify_api_key(api_key, db_key.key_hash):
                        matched_key = db_key
                        break
                
                if matched_key:
                    # Get user and their tier
                    result = await db.execute(
                        select(User).where(User.id == matched_key.user_id)
                    )
                    user = result.scalar_one_or_none()
                    
                    if user and user.is_active:
                        tier = user.rate_limit_tier
                        print(f"[MIDDLEWARE] Set tier for {user.email}: {tier}")
        
        except Exception as e:
            print(f"[MIDDLEWARE] Error checking API key: {e}")
    
    # Set tier in ContextVar
    set_rate_limit_tier(tier)
    request.state.rate_limit_tier = tier
    
    # Call next middleware/endpoint
    response = await call_next(request)
    
    # 👇 INJECT RATE LIMIT HEADERS MANUALLY
    try:
        # Get the rate limit key
        rate_limit_key = limiter._key_func(request)
        
        # Get limit from tier
        limit_string = RATE_LIMIT_TIERS.get(tier, RATE_LIMIT_TIERS["free"])
        limit_value = int(limit_string.split("/")[0])
        
        # Get storage instance
        storage = limiter._storage
        
        # Get current window stats
        # SlowAPI stores data with a specific key format
        window_key = f"LIMITER/{rate_limit_key}/{limit_string}"
        
        print(f"[DEBUG] Storage type: {type(storage).__name__}")
        print(f"[DEBUG] Rate limit key: {rate_limit_key}")
        print(f"[DEBUG] Window key: {window_key}")
        
        # Try to get the count
        try:
            current_count = storage.get(window_key)
            print(f"[DEBUG] Current count from storage: {current_count}")
            
            if current_count and isinstance(current_count, (int, str)):
                remaining = max(0, limit_value - int(current_count))
            else:
                remaining = limit_value - 1  # Assume 1 request was made (this one)
                
        except Exception as storage_error:
            print(f"[DEBUG] Error getting count: {storage_error}")
            remaining = limit_value - 1
        
        # Calculate reset time (next hour)
        current_time = int(time.time())
        # Round up to next hour boundary
        reset_time = ((current_time // 3600) + 1) * 3600
        
        print(f"[HEADERS] Limit: {limit_value} | Remaining: {remaining} | Reset: {reset_time}")
        
        # Add headers to response
        response.headers["X-RateLimit-Limit"] = str(limit_value)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
    except Exception as e:
        print(f"[HEADERS] Error adding rate limit headers: {type(e).__name__}: {e}")
    
    return response

async def rate_limit_headers_middleware(request: Request, call_next):
    """
    Middleware that adds rate limit headers to responses.
    
    Headers added:
    - X-RateLimit-Limit: Total requests allowed in window
    - X-RateLimit-Remaining: Remaining requests in current window
    - X-RateLimit-Reset: Unix timestamp when limit resets
    """
    response = await call_next(request)
    
    # Get rate limit info from SlowAPI's limiter
    try:
        # Get the rate limit key for this request
        rate_limit_key = limiter._key_func(request)
        
        # Get tier from request.state
        tier = getattr(request.state, "rate_limit_tier", "free")
        
        # Parse limit from tier (e.g., "100/hour" -> 100)
        from app.core.rate_limit import RATE_LIMIT_TIERS
        limit_string = RATE_LIMIT_TIERS.get(tier, RATE_LIMIT_TIERS["free"])
        limit_value = int(limit_string.split("/")[0])
        
        # Get current window stats from limiter
        window_stats = limiter._storage.get(rate_limit_key)
        
        if window_stats:
            remaining = max(0, limit_value - window_stats)
        else:
            remaining = limit_value
        
        # Calculate reset time (next hour)
        current_time = int(time.time())
        reset_time = current_time + 3600  # 1 hour from now
        
        # Add headers
        response.headers["X-RateLimit-Limit"] = str(limit_value)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
    except Exception as e:
        # If we can't get stats, don't fail the request
        print(f"[HEADERS] Error adding rate limit headers: {e}")
    
    return response
