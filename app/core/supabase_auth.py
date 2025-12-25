"""
Utilities for validating Supabase Auth JWT tokens and synchronizing users.
"""
import os
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv

from app.core.database import get_db
from app.models.user import User

load_dotenv()

# Supabase authentication configuration
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_JWT_ALGORITHM = "HS256"

# FastAPI security scheme for HTTP Bearer token (auto_error=False to allow flexible auth)
security = HTTPBearer(auto_error=False)


def decode_supabase_jwt(token: str) -> dict:
    """
    Decode and validate a JWT token issued by Supabase Auth.
    
    This function verifies the JWT signature using the Supabase secret key
    and returns the decoded payload. The 'aud' claim is not verified as
    Supabase doesn't always include it.
    
    Args:
        token (str): JWT token string to decode and validate
        
    Returns:
        dict: Decoded JWT payload containing 'sub', 'email', 'role', and other claims
        
    Raises:
        HTTPException: 500 if SUPABASE_JWT_SECRET is not configured
        HTTPException: 401 if the token is invalid, expired, or malformed
    """
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET not configured"
        )
    
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[SUPABASE_JWT_ALGORITHM],
            options={"verify_aud": False}  # Supabase doesn't always include 'aud' claim
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_or_create_user_from_jwt(
    payload: dict,
    db: AsyncSession
) -> User:
    """
    Retrieve or create a user based on JWT payload.
    
    This function implements lazy synchronization: it searches for an existing user
    by their Supabase user ID. If the user doesn't exist, a new user record is
    automatically created with default settings (free tier, active status).
    
    Args:
        payload (dict): Decoded JWT payload from Supabase Auth
        db (AsyncSession): Async database session
        
    Returns:
        User: User model instance (newly created or existing)
        
    Raises:
        HTTPException: 401 if 'sub' or 'email' is missing from the token payload
    """
    supabase_user_id = payload.get("sub")
    email = payload.get("email")
    
    if not supabase_user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing sub or email"
        )
    
    # Query database for existing user by Supabase user ID
    result = await db.execute(
        select(User).where(User.supabase_user_id == supabase_user_id)
    )
    user = result.scalar_one_or_none()
    
    # Create new user if not found (lazy synchronization approach)
    if not user:
        user = User(
            supabase_user_id=supabase_user_id,
            email=email,
            role="user",
            is_active=True,
            rate_limit_tier="free",
            usage_count=0
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        print(f"✅ User created via lazy sync: {email} (ID: {user.id})")
    
    return user


async def get_current_user_from_supabase(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User | None:
    """
    FastAPI dependency to extract and validate the current authenticated user from JWT.
    
    This dependency has been updated to support flexible dual authentication (JWT + API Key).
    It now returns None if no token is provided instead of raising an error, allowing
    fallback to other authentication methods like API keys.
    
    When a token is provided, it must be valid and the user account must be active.
    
    Usage in endpoints:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user_from_supabase)):
            return {"user_id": user.id, "email": user.email}
    
    Args:
        credentials (HTTPAuthorizationCredentials): HTTP Bearer token from Authorization header
        db (AsyncSession): Async database session
        
    Returns:
        User | None: Authenticated user if valid JWT provided, None if no credentials
        
    Raises:
        HTTPException: 401 if token is provided but invalid
        HTTPException: 403 if user account is inactive
    """
    # Return None if no credentials provided (allows fallback to API key auth)
    if not credentials:
        return None
    
    # Decode and validate JWT token from the Authorization header
    payload = decode_supabase_jwt(credentials.credentials)
    
    # Retrieve existing user or create new one via lazy sync
    user = await get_or_create_user_from_jwt(payload, db)
    
    # Verify that the user account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user
