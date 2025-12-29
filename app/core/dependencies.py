"""
FastAPI dependencies for authentication and authorization.

Supports both Supabase JWT tokens and custom API keys for API authentication.
This module provides flexible authentication options for different API consumers.
Now integrated with subscription plans and usage tracking.
"""
from fastapi import Depends, HTTPException, status, Security, Request 
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.core.security import verify_api_key
from app.core.supabase_auth import get_current_user_from_supabase
from app.core.rate_limiter import rate_limiter
from app.models.user import User
from app.models.api_key import APIKey
from app.models.user_subscription import UserSubscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.api_usage_log import APIUsageLog

# HTTP security scheme for API Key header extraction
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_active_user_subscription(user_id: int, db: AsyncSession):
    """
    Retrieve the active subscription for a user.
    
    This function queries the database to find the user's active subscription
    along with the associated plan details. If no active subscription is found,
    it returns the free plan as default.
    
    Args:
        user_id (int): The ID of the user
        db (AsyncSession): Database session
        
    Returns:
        tuple: (UserSubscription or None, SubscriptionPlan)
               - First element: Active subscription record (None if no active subscription)
               - Second element: Associated plan (free plan if no subscription)
    """
    # Query for active subscriptions that haven't expired yet
    result = await db.execute(
        select(UserSubscription, SubscriptionPlan)
        .join(SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id)
        .where(UserSubscription.user_id == user_id)
        .where(UserSubscription.status == "active")
        .where(UserSubscription.current_period_end > datetime.now())
        .order_by(UserSubscription.current_period_end.desc())
    )
    result_tuple = result.first()
    
    # If active subscription found, return it with the plan
    if result_tuple:
        return result_tuple[0], result_tuple[1]
    
    # If no active subscription, return None and the free plan
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.plan_name == "free")
    )
    free_plan = result.scalar_one_or_none()
    return None, free_plan


async def log_api_usage(
    db: AsyncSession,
    user_id: int,
    api_key_id: int = None,
    endpoint: str = "",
    http_method: str = "GET",
    status_code: int = 200,
    response_time_ms: int = None,
    ip_address: str = None,
    user_agent: str = None,
    request_id: str = None,
    rate_limit_plan: str = None,
    rate_limited: bool = False,
    error_message: str = None
):
    """
    Log API usage to the database for analytics and monitoring.
    
    This function creates a new entry in the api_usage_logs table with detailed
    information about each API request. This data is used for:
    - Analytics and reporting
    - Rate limit enforcement verification
    - Security auditing
    - Performance monitoring
    
    Args:
        db (AsyncSession): Database session
        user_id (int): ID of the user making the request
        api_key_id (int, optional): ID of the API key used (if applicable)
        endpoint (str): The API endpoint path that was called
        http_method (str): HTTP method (GET, POST, PUT, DELETE, etc.)
        status_code (int): HTTP response status code
        response_time_ms (int, optional): Response time in milliseconds
        ip_address (str, optional): Client IP address
        user_agent (str, optional): Client user agent string
        request_id (str, optional): Unique request identifier for tracking
        rate_limit_plan (str, optional): Rate limit plan active at request time
        rate_limited (bool): Whether the request was rate limited
        error_message (str, optional): Error message if request failed
    """
    try:
        # Create new usage log entry
        log_entry = APIUsageLog(
            user_id=user_id,
            api_key_id=api_key_id,
            endpoint=endpoint,
            http_method=http_method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            rate_limit_plan=rate_limit_plan,
            rate_limited=rate_limited,
            error_message=error_message
        )
        db.add(log_entry)
        await db.commit()
    except Exception as e:
        # Log error but don't fail the request
        print(f"[ERROR] Failed to log API usage: {e}")


async def get_current_user_from_api_key(
    request: Request,
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> User | None:
    """
    Validate an API key from the X-API-Key header and return the associated user.
    
    This dependency extracts the API key from the request header, searches for a matching
    key in the database, verifies it using secure hashing, retrieves the user's active
    subscription plan, and enforces rate limits based on that plan.
    
    Flow:
    1. Extract API key from X-API-Key header
    2. Query database for active, non-revoked, non-expired keys
    3. Verify the provided key against stored hashes using Argon2
    4. Retrieve the associated user and verify account is active
    5. Get user's active subscription plan (or default to free)
    6. Check rate limits based on subscription plan
    7. Update API key's last_used_at timestamp
    8. Store user, api_key, and plan in request.state for later use
    
    Args:
        request (Request): FastAPI request object
        api_key (str): API key from X-API-Key header (optional)
        db (AsyncSession): Async database session
        
    Returns:
        User | None: User object if key is valid, None if no key provided
        
    Raises:
        HTTPException 401: If API key is invalid, expired, or revoked
        HTTPException 401: If associated user account is inactive
        HTTPException 429: If rate limit is exceeded
        HTTPException 500: If internal error occurs
    """
    try: 
        # Return None if no API key in header (allows fallback to other auth methods)
        if not api_key:
            print("No API key provided")
            return None
    
        print(f"Validating API Key: {api_key[:20]}...")
    
        # Query all active, non-revoked, non-expired API keys
        result = await db.execute(
            select(APIKey)
            .where(APIKey.is_active == True)
            .where(APIKey.revoked_at == None)
            .where(APIKey.expires_at == None or APIKey.expires_at > datetime.now())
        )
        active_keys = result.scalars().all()

        print(f"Total active keys in DB: {len(active_keys)}")
    
        # Verify the provided key against each stored hash (secure comparison using Argon2)
        matched_key = None
        for db_key in active_keys:
            if verify_api_key(api_key, db_key.key_hash):
                matched_key = db_key
                break
    
        # If no matching key found, authentication fails
        if not matched_key:
            print(f"Invalid or revoked API Key")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
    
        # Retrieve the user associated with this API key
        print(f"Searching for user ID: {matched_key.user_id}")
        result = await db.execute(
            select(User).where(User.id == matched_key.user_id)
        )
        user = result.scalar_one_or_none()
    
        # Verify user exists
        if not user:
            print(f"User not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Verify user account is active
        if not user.is_active:
            print(f"Inactive user: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
    
        print(f"Valid API Key for: {user.email}")

        # Get user's active subscription and plan (or default to free plan)
        subscription, plan = await get_active_user_subscription(user.id, db)
        
        # Extract plan name for rate limiting
        tier = plan.plan_name if plan else "free"
        
        # Check and enforce rate limits based on subscription plan
        # This will raise HTTPException 429 if rate limit is exceeded
        rate_limit_info = await rate_limiter.check_rate_limit(
            request=request,
            user_id=user.id,
            api_key_id=matched_key.id,
            tier=tier,
            plan=plan
        )

        # Store rate limit info in request.state for response headers
        request.state.rate_limit_info = rate_limit_info
        
        # Store user, API key, and subscription plan in request.state
        # These can be accessed in endpoints and middleware
        request.state.user = user
        request.state.api_key = matched_key
        request.state.subscription_plan = plan

        # Update the API key's last_used_at timestamp for monitoring
        matched_key.last_used_at = datetime.now()
        await db.commit()
    
        return user

    except HTTPException:
        # Re-raise HTTP exceptions (authentication failures, rate limits, etc.)
        raise
    except Exception as e:
        # Catch any unexpected errors and return 500
        print(f"\nERROR in get_current_user_from_api_key:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


async def get_current_user(
    request: Request,
    jwt_user: User = Depends(get_current_user_from_supabase),
    api_key_user: User | None = Depends(get_current_user_from_api_key),
) -> User:
    """
    Authentication dependency that accepts both JWT and API Key methods.
    
    This is the main authentication dependency used by protected endpoints.
    It attempts to authenticate using either Supabase JWT or custom API Key,
    with JWT taking priority if both are provided.
    
    Authentication Priority:
        1. Supabase JWT in Authorization header (highest priority)
        2. API Key in X-API-Key header (fallback)
        3. Raises 401 if neither is valid
    
    Usage in endpoints:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id, "email": user.email}
    
    Args:
        request (Request): FastAPI request object
        jwt_user (User): Authenticated user from JWT token (if present)
        api_key_user (User | None): Authenticated user from API key (if present)
        
    Returns:
        User: Authenticated user object
        
    Raises:
        HTTPException 401: If neither JWT nor API key are valid
    """
    # Use JWT user if available (higher priority)
    if jwt_user:
        print(f"Authenticated via JWT: {jwt_user.email}")
        request.state.user = jwt_user
        return jwt_user
    
    # Fallback to API Key user if JWT not available
    if api_key_user:
        print(f"Authenticated via API Key: {api_key_user.email}")
        return api_key_user
    
    # Neither authentication method succeeded
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication credentials. Provide either JWT token (Authorization: Bearer) or API key (X-API-Key)",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_admin(
    user: User = Depends(get_current_user)
) -> User:
    """
    Authorization dependency that requires admin privileges.
    
    This dependency should be used on endpoints that only admin users can access.
    It verifies that the authenticated user has the 'admin' role.
    
    Usage in admin-only endpoints:
        @app.post("/admin/settings")
        async def update_settings(user: User = Depends(require_admin)):
            # Only admin users can execute this endpoint
            ...
    
    Args:
        user (User): Currently authenticated user
        
    Returns:
        User: The admin user object
        
    Raises:
        HTTPException 403: If user does not have admin role
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires admin privileges"
        )
    return user
