"""
Custom rate limiting implementation using Redis.

This module implements a sophisticated rate limiter that enforces limits
at three time windows: per minute, per hour, and per day. It integrates
with the subscription system to apply different limits based on user plans.

Key Features:
- Multi-window rate limiting (minute, hour, day)
- Integration with subscription plans
- Per-user and per-API-key tracking
- Automatic key expiration in Redis
- Graceful degradation if Redis is unavailable
"""
import os
import time
from typing import Optional
from fastapi import Request, HTTPException, status 
import redis.asyncio as aioredis


class RateLimiter:
    """
    Redis-based rate limiter with support for subscription plans.
    
    This class handles all rate limiting logic using Redis as the storage backend.
    It tracks request counts in three different time windows (minute, hour, day)
    and enforces limits based on the user's subscription plan.
    
    Attributes:
        redis: Async Redis client connection
        enabled: Whether rate limiting is enabled (False if Redis not configured)
    """
    
    def __init__(self):
        """
        Initialize the rate limiter with Redis connection.
        
        Attempts to connect to Redis using the REDIS_URL environment variable.
        If Redis is not configured, rate limiting will be disabled.
        """
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
        user_id: int,
        api_key_id: int = None,
        tier: str = "free",
        plan = None
    ) -> dict:
        """
        Check and enforce rate limits for a request.
        
        This method checks the request against three time windows:
        1. Per-minute limit (most restrictive, prevents burst traffic)
        2. Per-hour limit (medium-term usage control)
        3. Per-day limit (long-term usage quota)
        
        The limits are determined by the user's subscription plan. If any limit
        is exceeded, an HTTPException 429 is raised immediately.
        
        Redis Key Strategy:
        - Keys are namespaced by user_id or api_key_id
        - Each time window has its own key with automatic expiration
        - Example: "ratelimit:user:123:minute:1735430400"
        
        Args:
            request (Request): FastAPI request object
            user_id (int): ID of the user making the request
            api_key_id (int, optional): ID of API key if used for auth
            tier (str): Subscription tier name (free, premium, pro)
            plan (SubscriptionPlan, optional): Full plan object with limits
            
        Returns:
            dict: Rate limit information containing:
                - limit_minute, limit_hour, limit_day: Maximum allowed requests
                - remaining_minute, remaining_hour, remaining_day: Requests remaining
                - reset_minute, reset_hour, reset_day: Unix timestamps when limits reset
                - count_minute, count_hour, count_day: Current request counts
                
        Raises:
            HTTPException 429: If any rate limit is exceeded
        """
        # If Redis is not enabled, return permissive limits without enforcement
        if not self.enabled:
            return {"limit_minute": 10, "limit_hour": 100, "limit_day": 1000, 
                    "remaining_minute": 10, "remaining_hour": 100, "remaining_day": 1000,
                    "reset_minute": int(time.time()) + 60,
                    "reset_hour": int(time.time()) + 3600,
                    "reset_day": int(time.time()) + 86400}
        
        # Extract rate limits from subscription plan, or use defaults
        if plan:
            limit_per_minute = plan.rate_limit_per_minute
            limit_per_hour = plan.rate_limit_per_hour
            limit_per_day = plan.rate_limit_per_day
        else:
            # Default to free plan limits if no plan provided
            limit_per_minute = 10
            limit_per_hour = 100
            limit_per_day = 1000
        
        # Generate base key for Redis storage
        # Prefer API key ID for more granular tracking, fallback to user ID
        key_base = f"ratelimit:user:{user_id}"
        if api_key_id:
            key_base = f"ratelimit:apikey:{api_key_id}"
        
        # Get current time for window calculations
        current_time = int(time.time())
        
        # Calculate window start times (aligned to window boundaries)
        minute_start = (current_time // 60) * 60      # Start of current minute
        hour_start = (current_time // 3600) * 3600    # Start of current hour
        day_start = (current_time // 86400) * 86400   # Start of current day (UTC)
        
        # Generate Redis keys for each time window
        key_minute = f"{key_base}:minute:{minute_start}"
        key_hour = f"{key_base}:hour:{hour_start}"
        key_day = f"{key_base}:day:{day_start}"
        
        try:
            # Increment counters for each time window atomically
            # Using INCR command which is atomic and thread-safe
            count_minute = await self.redis.incr(key_minute)
            if count_minute == 1:
                # First request in this window - set expiration
                await self.redis.expire(key_minute, 60)
            
            count_hour = await self.redis.incr(key_hour)
            if count_hour == 1:
                # First request in this window - set expiration
                await self.redis.expire(key_hour, 3600)
            
            count_day = await self.redis.incr(key_day)
            if count_day == 1:
                # First request in this window - set expiration
                await self.redis.expire(key_day, 86400)
            
            # Calculate remaining requests for each window
            remaining_minute = max(0, limit_per_minute - count_minute)
            remaining_hour = max(0, limit_per_hour - count_hour)
            remaining_day = max(0, limit_per_day - count_day)
            
            # Calculate reset times (end of each window)
            reset_minute = minute_start + 60
            reset_hour = hour_start + 3600
            reset_day = day_start + 86400
            
            # Log current rate limit status for debugging
            print(f"[RATE LIMIT] Minute: {count_minute}/{limit_per_minute} | Hour: {count_hour}/{limit_per_hour} | Day: {count_day}/{limit_per_day}")
            
            # Check minute limit (most restrictive, checked first)
            if count_minute > limit_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {limit_per_minute} requests per minute. Resets at {reset_minute}",
                    headers={
                        "X-RateLimit-Limit-Minute": str(limit_per_minute),
                        "X-RateLimit-Remaining-Minute": "0",
                        "X-RateLimit-Reset-Minute": str(reset_minute),
                        "Retry-After": str(reset_minute - current_time)
                    }
                )
            
            # Check hour limit
            if count_hour > limit_per_hour:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {limit_per_hour} requests per hour. Resets at {reset_hour}",
                    headers={
                        "X-RateLimit-Limit-Hour": str(limit_per_hour),
                        "X-RateLimit-Remaining-Hour": "0",
                        "X-RateLimit-Reset-Hour": str(reset_hour),
                        "Retry-After": str(reset_hour - current_time)
                    }
                )
            
            # Check day limit
            if count_day > limit_per_day:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {limit_per_day} requests per day. Resets at {reset_day}",
                    headers={
                        "X-RateLimit-Limit-Day": str(limit_per_day),
                        "X-RateLimit-Remaining-Day": "0",
                        "X-RateLimit-Reset-Day": str(reset_day),
                        "Retry-After": str(reset_day - current_time)
                    }
                )
            
            # All limits passed - return rate limit info for response headers
            return {
                "limit_minute": limit_per_minute,
                "limit_hour": limit_per_hour,
                "limit_day": limit_per_day,
                "remaining_minute": remaining_minute,
                "remaining_hour": remaining_hour,
                "remaining_day": remaining_day,
                "reset_minute": reset_minute,
                "reset_hour": reset_hour,
                "reset_day": reset_day,
                "count_minute": count_minute,
                "count_hour": count_hour,
                "count_day": count_day
            }
            
        except HTTPException:
            # Re-raise rate limit exceeded exceptions
            raise
        except Exception as e:
            # On Redis errors, log and allow the request (fail open)
            # This prevents Redis outages from blocking all API traffic
            print(f"[RATE LIMIT] Error checking rate limit: {e}")
            return {
                "limit_minute": limit_per_minute,
                "limit_hour": limit_per_hour,
                "limit_day": limit_per_day,
                "remaining_minute": limit_per_minute,
                "remaining_hour": limit_per_hour,
                "remaining_day": limit_per_day,
                "reset_minute": minute_start + 60,
                "reset_hour": hour_start + 3600,
                "reset_day": day_start + 86400
            }


# Global singleton instance of the rate limiter
# Import this instance in other modules: from app.core.rate_limiter import rate_limiter
rate_limiter = RateLimiter()
