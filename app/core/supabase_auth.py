"""
Utilities for validating Supabase JWT tokens and synchronizing users.
Supports both HS256 (legacy) and ES256 (new with JWKS).
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

# Security scheme
security = HTTPBearer(auto_error=False)

# Cache for JWKS
_jwks_cache = None


def get_jwks():
    """
    Fetch JWKS (JSON Web Key Set) from Supabase.
    Caches the result to avoid repeated requests.
    
    Returns:
        dict: JWKS containing public keys
    """
    global _jwks_cache
    
    if _jwks_cache is not None:
        return _jwks_cache
    
    if not SUPABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_URL not configured"
        )
    
    jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    
    try:
        print(f"[INFO] Fetching JWKS from: {jwks_url}")
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()
        _jwks_cache = response.json()
        print(f"[SUCCESS] JWKS fetched successfully")
        return _jwks_cache
    except Exception as e:
        print(f"[ERROR] Failed to fetch JWKS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch JWKS from Supabase: {str(e)}"
        )


def get_public_key_for_kid(kid: str) -> dict:
    """
    Get the public key (JWK) for a specific Key ID.
    
    Args:
        kid: Key ID from JWT header
        
    Returns:
        dict: JWK (JSON Web Key)
    """
    jwks = get_jwks()
    
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Public key not found for kid: {kid}"
    )


def decode_supabase_jwt(token: str) -> dict:
    """
    Decode and validate JWT from Supabase.
    
    Supports:
    - HS256/HS384/HS512 (Legacy with secret)
    - ES256 (New with JWKS public keys)
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Token payload
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        # Get header without validation to check algorithm
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        kid = header.get("kid")
        
        print(f"[INFO] JWT algorithm: {algorithm}, kid: {kid}")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token format: {str(e)}"
        )
    
    # Try HMAC algorithms first (HS256, HS384, HS512)
    if algorithm in ["HS256", "HS384", "HS512"]:
        if not SUPABASE_JWT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SUPABASE_JWT_SECRET not configured for HMAC validation"
            )
        
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=[algorithm],
                options={"verify_aud": False}
            )
            print(f"[SUCCESS] JWT validated with {algorithm}")
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    # Handle ES256 (Elliptic Curve) with public key from JWKS
    elif algorithm == "ES256":
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ES256 token missing 'kid' header"
            )
        
        # Get public key from JWKS
        public_key_jwk = get_public_key_for_kid(kid)
        
        try:
            # Decode using public key
            payload = jwt.decode(
                token,
                public_key_jwk,
                algorithms=["ES256"],
                options={"verify_aud": False}
            )
            print(f"[SUCCESS] JWT validated with ES256 (kid: {kid})")
            return payload
        except JWTError as e:
            print(f"[ERROR] ES256 validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid ES256 token: {str(e)}"
            )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unsupported JWT algorithm: {algorithm}"
        )


async def get_or_create_user_from_jwt(
    payload: dict,
    db: AsyncSession
) -> User:
    """
    Fetch or create user from JWT payload (lazy sync).
    
    Args:
        payload: Decoded JWT payload
        db: Database session
        
    Returns:
        User: User instance
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
    
    # Create if not found (lazy sync)
    if not user:
        user = User(
            supabase_user_id=supabase_user_id,
            email=email,
            role="user",
            is_active=True,
        #rate_limit_tier="free",
        #usage_count=0
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
        credentials: Authorization header credentials
        db: Database session
        
    Returns:
        User if valid JWT, None if no token
    """
    # Return None if no credentials (not an error)
    if not credentials:
        return None
    
    # Decode and validate JWT
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
