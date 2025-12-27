"""
Custom middleware for setting rate limit tier before SlowAPI check.
"""
from fastapi import Request
from app.core.security import verify_api_key
from app.models.api_key import APIKey
from app.models.user import User
from sqlalchemy import select
from app.core.database import async_session_maker
from app.core.rate_limit import set_rate_limit_tier


async def rate_limit_tier_middleware(request: Request, call_next):
    """
    Middleware that sets rate_limit_tier in ContextVar BEFORE SlowAPI runs.
    
    This allows dynamic rate limiting based on user tier without modifying
    the SlowAPI execution order.
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
            # Continue with default tier on error
    
    set_rate_limit_tier(tier)

    request.state.rate_limit_tier = tier
    
    response = await call_next(request)
    return response