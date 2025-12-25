"""
Utilities for validating Supabase JWT tokens and synchronizing users.
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

# Supabase JWT secret from environment
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# Security scheme for FastAPI
security = HTTPBearer(auto_error=False)


def decode_supabase_jwt(token: str) -> dict:
    """
    Decode and validate a JWT issued by Supabase Auth.
    
    Attempts multiple HMAC algorithms: HS256, HS384, HS512.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Token payload with fields like 'sub', 'email', 'role', etc.
        
    Raises:
        HTTPException: If token is invalid or secret not configured
    """
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET not configured"
        )
    
    # List of algorithms to attempt
    algorithms_to_try = ["HS256", "HS384", "HS512"]
    
    # Try decoding with each algorithm
    for algorithm in algorithms_to_try:
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=[algorithm],
                options={"verify_aud": False}
            )
            print(f"[SUCCESS] JWT validated with {algorithm}")
            return payload
        except JWTError:
            continue
    
    # If no HMAC algorithm worked, token is invalid
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_or_create_user_from_jwt(
    payload: dict,
    db: AsyncSession
) -> User:
    """
    Fetch or create user from JWT payload (lazy sync).
    
    Searches for user by supabase_user_id and creates if not found.
    
    Args:
        payload: Decoded JWT payload
        db: Database session
        
    Returns:
        User: User instance
        
    Raises:
        HTTPException: If payload is missing required fields
    """
    supabase_user_id = payload.get("sub")
    email = payload.get("email")
    
    if not supabase_user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing sub or email"
        )
    
    # Search for existing user
    result = await db.execute(
        select(User).where(User.supabase_user_id == supabase_user_id)
    )
    user = result.scalar_one_or_none()
    
    # If not found, create (lazy sync)
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
        
        print(f"[SUCCESS] User created via lazy sync: {email} (ID: {user.id})")
    
    return user


async def get_current_user_from_supabase(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User | None:
    """
    Dependency to get current user from Supabase JWT.
    
    Returns None if no token present (allows dual auth with API keys).
    
    Args:
        credentials: Credentials from Authorization header
        db: Database session
        
    Returns:
        User if valid JWT found, None if no token present
        
    Raises:
        HTTPException 401: If token is present but invalid
        HTTPException 403: If user account is inactive
    """
    # If no credentials, return None (not an error)
    if not credentials:
        return None
    
    # Decode JWT
    payload = decode_supabase_jwt(credentials.credentials)
    
    # Get or create user in database
    user = await get_or_create_user_from_jwt(payload, db)
    
    # Validate user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user
