"""
FastAPI dependencies for authentication and authorization.

Supports both Supabase JWT tokens and custom API keys for API authentication.
This module provides flexible authentication options for different API consumers.
"""
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_api_key
from app.core.supabase_auth import get_current_user_from_supabase
from app.models.user import User
from app.models.api_key import APIKey

# HTTP security scheme for API Key header extraction
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user_from_api_key(
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> User | None:
    """
    Validate an API key from the X-API-Key header and return the associated user.
    
    This dependency extracts the API key from the request header, searches for a matching
    key in the database, verifies it using secure hashing, and returns the associated user.
    If no API key is provided, returns None (not an error - used for flexible auth).
    
    Args:
        api_key (str): API key from X-API-Key header (optional)
        db (AsyncSession): Async database session
        
    Returns:
        User | None: User object if key is valid, None if no key provided
        
    Raises:
        HTTPException 401: If API key is invalid, expired, or revoked
        HTTPException 401: If associated user account is inactive
    """
    # Return None if no API key in header (allows fallback to other auth methods)
    if not api_key:
        return None
    
    print(f"🔑 Validating API Key: {api_key[:20]}...")
    
    # Query all active, non-revoked API keys
    result = await db.execute(
        select(APIKey)
        .where(APIKey.is_active == True)
        .where(APIKey.revoked_at == None)
    )
    active_keys = result.scalars().all()
    
    # Verify the provided key against each stored hash (secure comparison)
    matched_key = None
    for db_key in active_keys:
        if verify_api_key(api_key, db_key.key_hash):
            matched_key = db_key
            break
    
    if not matched_key:
        print(f"❌ Invalid or revoked API Key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Retrieve the user associated with this API key
    result = await db.execute(
        select(User).where(User.id == matched_key.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        print(f"❌ Associated user account is inactive")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    print(f"✅ Valid API Key for: {user.email}")
    
    # Increment usage counter for metrics and monitoring
    user.usage_count += 1
    await db.commit()
    
    return user


async def get_current_user(
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
        jwt_user (User): Authenticated user from JWT token (if present)
        api_key_user (User | None): Authenticated user from API key (if present)
        
    Returns:
        User: Authenticated user object
        
    Raises:
        HTTPException 401: If neither JWT nor API key are valid
    """
    # Use JWT user if available (higher priority)
    if jwt_user:
        print(f"👤 Authenticated via JWT: {jwt_user.email}")
        return jwt_user
    
    # Fallback to API Key user if JWT not available
    if api_key_user:
        print(f"🔑 Authenticated via API Key: {api_key_user.email}")
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
