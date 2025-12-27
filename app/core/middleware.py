"""
Custom middleware for setting rate limit tier before SlowAPI check.
"""
from fastapi import Request
from fastapi.responses import Response
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

    # Store limit info for later
    limit_string = RATE_LIMIT_TIERS.get(tier, RATE_LIMIT_TIERS["free"])
    limit_value = int(limit_string.split("/")[0])
    request.state.rate_limit_max = limit_value
    
    # Call next middleware/endpoint (SlowAPI will increment counter here)
    response = await call_next(request)
    
    # inject headers (after SlowAPI has processed the request)
    try:
        # Check if this is a rate limit error response (429)
        if response.status_code == 429:
            # Rate limit exceeded - set remaining to 0
            remaining = 0
        else:
            # Use the stats that SlowAPI attached to the request
            # SlowAPI stores the count in request.state after processing
            if hasattr(request.state, "view_rate_limit"):
                # SlowAPI sets this attribute with rate limit info
                current_count = getattr(request.state.view_rate_limit, "current", 0)
                remaining = max(0, limit_value - current_count)
                print(f"[HEADERS] Using SlowAPI stats - Current: {current_count}, Remaining: {remaining}")
            else:
                # Fallback: Try to read directly from Redis
                rate_limit_key = limiter._key_func(request)
                storage = limiter._storage
                
                # SlowAPI uses limits library internally which stores with this pattern
                # We need to check the actual keys in Redis
                window_key = f"{rate_limit_key}:{limit_string}"
                
                try:
                    # Access Redis directly
                    if hasattr(storage, 'storage'):
                        redis_client = storage.storage
                        # Try different key patterns
                        patterns_to_try = [
                            window_key,
                            f"LIMITER/{window_key}",
                            f"LIMITER/{rate_limit_key}/{limit_string}",
                            rate_limit_key,
                        ]
                        
                        current_count = None
                        for pattern in patterns_to_try:
                            val = redis_client.get(pattern)
                            if val:
                                current_count = int(val)
                                print(f"[HEADERS] Found count {current_count} at key: {pattern}")
                                break
                        
                        if current_count is not None:
                            remaining = max(0, limit_value - current_count)
                        else:
                            print(f"[HEADERS] No count found in Redis, assuming first request")
                            remaining = limit_value - 1
                    else:
                        remaining = limit_value - 1
                        
                except Exception as redis_error:
                    print(f"[HEADERS] Redis read error: {redis_error}")
                    remaining = limit_value - 1
        
        # Calculate reset time (next hour boundary)
        current_time = int(time.time())
        reset_time = ((current_time // 3600) + 1) * 3600
        
        # Add headers to response
        response.headers["X-RateLimit-Limit"] = str(limit_value)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        print(f"[HEADERS] Final - Limit: {limit_value} | Remaining: {remaining} | Reset: {reset_time}")
        
    except Exception as e:
        print(f"[HEADERS] Error: {type(e).__name__}: {e}")
    
    return response

async def rate_limit_headers_middleware(request: Request, call_next):
    """
    Add rate limit headers to response if available in request.state.
    """
    response = await call_next(request)
    
    # Add rate limit headers if they were set by authentication
    if hasattr(request.state, "rate_limit_info"):
        info = request.state.rate_limit_info
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
    
    return response
