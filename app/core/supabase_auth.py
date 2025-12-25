"""
Utilities for validating Supabase JWT tokens and synchronizing users.
"""
import os
import requests
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv

from app.core.database import get_db
from app.models.user import User

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# Security scheme for FastAPI
security = HTTPBearer(auto_error=False)

# Cache for JWKS (public keys)
_jwks_cache = None


def get_jwks():
    """
    Fetch public keys (JWKS) from Supabase for validating ES256 tokens.
    
    Caches the keys to avoid repeated network calls.
    """
    global _jwks_cache
    
    if _jwks_cache is not None:
        return _jwks_cache
    
    try:
        # Supabase exposes public keys at /.well-known/jwks.json
        jwks_url = f"{SUPABASE_URL}/auth/v1/jwks"
        response = requests.get(jwks_url, timeout=5)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache
    except Exception as e:
        print(f"[WARNING] Failed to fetch JWKS from Supabase: {e}")
        return None


def decode_supabase_jwt(token: str) -> dict:
    """
    Decode and validate a JWT issued by Supabase Auth.
    
    Supports both HS256 (legacy) and ES256 (current) algorithms.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Token payload with fields like 'sub', 'email', 'role', etc.
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    # Try HS256 first (legacy, for compatibility)
    if SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            print("[SUCCESS] JWT validated with HS256")
            return payload
        except JWTError as e:
            print(f"[INFO] HS256 validation failed: {e}, trying ES256...")
    
    # Try ES256 with JWKS
    try:
        # Get header without validation to extract 'kid'
        unverified_header = jwt.get_unverified_header(token)
        algorithm = unverified_header.get("alg", "ES256")
        kid = unverified_header.get("kid")
        
        print(f"[INFO] Token algorithm: {algorithm}, key ID: {kid}")
        
        # Fetch JWKS
        jwks = get_jwks()
        if not jwks:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not fetch JWKS from Supabase"
            )
        
        # Find the correct public key
        public_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                public_key = key
                break
        
        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not find public key for kid: {kid}"
            )
        
        # Validate token with public key
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[algorithm],
            options={"verify_aud": False}
        )
        
        print(f"[SUCCESS] JWT validated with {algorithm}")
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
    
    Returns None if no token (allows dual auth with API keys).
    
    Args:
        credentials: Credentials from Authorization header
        db: Database session
        
    Returns:
        User if valid JWT found, None if no token present
        
    Raises:
        HTTPException 401: If token is present but invalid
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
