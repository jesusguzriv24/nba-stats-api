"""
Endpoints for user profile and API key management.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.supabase_auth import get_current_user_from_supabase
from app.core.security import generate_api_key
from app.models.user import User
from app.models.api_key import APIKey
from app.schemas.user import UserResponse, UserWithKeysResponse
from app.schemas.api_key import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyResponseWithKey
)

from app.core.rate_limit import limiter, get_rate_limit_for_user

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint - no authentication required.
    
    Use this to verify the API is running and responding.
    """
    return {"status": "healthy", "message": "User service is running"}


@router.get("/me", response_model=UserWithKeysResponse)
@limiter.limit(get_rate_limit_for_user)
async def get_current_user_profile(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the authenticated user's profile information.
    
    Returns the current user's profile data including account details and
    the count of API keys they own.
    
    Requires:
        - Valid Supabase JWT in Authorization header
    
    Returns:
        UserWithKeysResponse: User profile with API key count
    """
    # Count total API keys owned by this user
    result = await db.execute(
        select(func.count(APIKey.id)).where(APIKey.user_id == user.id)
    )
    api_keys_count = result.scalar()
    
    return UserWithKeysResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        rate_limit_tier=user.rate_limit_tier,
        usage_count=user.usage_count,
        created_at=user.created_at,
        api_keys_count=api_keys_count
    )


@router.post("/me/api-keys", response_model=APIKeyResponseWithKey, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def create_api_key(
    request: Request,
    data: APIKeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a new API key for the authenticated user.
    
    IMPORTANT: The complete API key is shown ONLY ONCE in this response.
    Store it securely - you will not be able to retrieve or view it again after this response.
    If lost, the key must be revoked and a new one created.
    
    Requires:
        - Valid Supabase JWT in Authorization header
        - Active user account
    
    Returns:
        APIKeyResponseWithKey: New API key with complete key value
    """
    # Verify that the user account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Generate cryptographically secure API key
    key_data = generate_api_key()
    
    # Create API key record in database
    new_api_key = APIKey(
        user_id=user.id,
        key_hash=key_data["key_hash"],
        name=data.name,
        last_chars=key_data["last_chars"],
        is_active=True,
        rate_limit_plan=user.rate_limit_tier  # Inherit user's rate limiting plan
    )
    
    db.add(new_api_key)
    await db.commit()
    await db.refresh(new_api_key)
    
    print(f"API Key created: {data.name} for {user.email} (ID: {new_api_key.id})")
    
    # Return response with complete key (shown only this time)
    return APIKeyResponseWithKey(
        id=new_api_key.id,
        name=new_api_key.name,
        last_chars=new_api_key.last_chars,
        is_active=new_api_key.is_active,
        rate_limit_plan=new_api_key.rate_limit_plan,
        created_at=new_api_key.created_at,
        revoked_at=new_api_key.revoked_at,
        key=key_data["key"]  #Complete key only returned here
    )


@router.get("/me/api-keys", response_model=List[APIKeyResponse])
@limiter.limit(get_rate_limit_for_user)
async def list_my_api_keys(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all API keys owned by the authenticated user.
    
    Returns all API keys in descending order by creation date. Full keys are never
    displayed - only the last 8 characters are shown for security purposes.
    
    Requires:
        - Valid Supabase JWT in Authorization header
    
    Returns:
        List[APIKeyResponse]: List of user's API keys with metadata
    """
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == user.id)
        .order_by(APIKey.created_at.desc())
    )
    api_keys = result.scalars().all()
    
    return api_keys


@router.delete("/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/hour")
async def revoke_api_key(
    request: Request,
    key_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke (deactivate) an API key owned by the authenticated user.
    
    Revoking a key deactivates it immediately - it will no longer work for API requests.
    The key record is not deleted but marked as revoked for audit purposes.
    
    Requires:
        - Valid Supabase JWT in Authorization header
        - The API key must belong to the authenticated user
    
    Args:
        key_id: ID of the API key to revoke
    
    Raises:
        HTTPException 404: If the API key is not found or doesn't belong to the user
    """
    # Find the API key
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == user.id  # Ensure the key belongs to this user
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Mark key as revoked with timestamp
    from datetime import datetime, timezone
    api_key.is_active = False
    api_key.revoked_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    print(f"API Key revoked: {api_key.name} (ID: {api_key.id})")
    
    return None
