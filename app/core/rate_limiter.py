"""
Custom rate limiting implementation using Redis directly.
"""
import os
import time
from typing import Optional
from fastapi import Request, HTTPException, status
import redis.asyncio as aioredis


class RateLimiter:
    """
    Custom rate limiter using Redis.
    """
    
    def __init__(self):
        redis_url = os.getenv("REDIS_URL")
        
        if redis_url:
            print(f"[RATE LIMITER] Connecting to Redis: {redis_url[:30]}...")
            self.redis = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self.enabled = True
        else:
            print("[RATE LIMITER] Redis not configured, rate limiting disabled")
            self.redis = None
            self.enabled = False
    
    async def check_rate_limit(
        self,
        request: Request,
        tier: str = "free",
        limits: dict = None
    ) -> dict:
        """
        Check and enforce rate limit.
        
        Returns:
            dict: Rate limit info with keys: limit, remaining, reset
        """
        if not self.enabled:
            return {"limit": 100, "remaining": 100, "reset": int(time.time()) + 3600}
        
        if limits is None:
            limits = {
                "free": 100,
                "pro": 1000,
                "enterprise": 10000
            }
        
        limit = limits.get(tier, limits["free"])
        
        # Generate key for this user/API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            key = f"ratelimit:apikey:{api_key[-16:]}"
        elif hasattr(request.state, "user") and request.state.user:
            key = f"ratelimit:user:{request.state.user.id}"
        else:
            # Fallback to IP
            client_ip = request.client.host if request.client else "unknown"
            key = f"ratelimit:ip:{client_ip}"
        
        # Get current hour window
        current_time = int(time.time())
        window_start = (current_time // 3600) * 3600
        window_key = f"{key}:{window_start}"
        
        # Increment counter
        try:
            count = await self.redis.incr(window_key)
            
            # Set expiry on first request in window (1 hour)
            if count == 1:
                await self.redis.expire(window_key, 3600)
            
            remaining = max(0, limit - count)
            reset_time = window_start + 3600
            
            print(f"[RATE LIMIT] Key: {window_key} | Count: {count}/{limit} | Remaining: {remaining}")
            
            # Check if limit exceeded
            if count > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Limit: {limit} requests/hour. Resets at {reset_time}",
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(reset_time - current_time)
                    }
                )
            
            return {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "count": count
            }
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"[RATE LIMIT] Error checking rate limit: {e}")
            # On error, allow the request
            return {"limit": limit, "remaining": limit, "reset": window_start + 3600}


# Global instance
rate_limiter = RateLimiter()
