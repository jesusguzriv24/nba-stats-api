"""
Endpoints for user profile and API key management.

Updated to work with the new subscription system.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_active_user_subscription
from app.core.supabase_auth import get_current_user_from_supabase
from app.core.security import generate_api_key
from app.models.user import User
from app.models.api_key import APIKey
from app.schemas.user import UserResponse, UserWithKeysResponse
from app.schemas.api_key import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreateResponse
)

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint - no authentication required.
    
    Use this to verify the user service is running and responding.
    
    Returns:
        dict: Health status
    """
    return {"status": "healthy", "message": "User service is running"}


@router.get("/me", response_model=UserWithKeysResponse)
async def get_current_user_profile(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the authenticated user's profile information.
    
    Returns the current user's profile data including account details,
    the count of API keys they own, and their current subscription plan.
    
    Requires:
        - Valid Supabase JWT in Authorization header OR
        - Valid API key in X-API-Key header
    
    Returns:
        UserWithKeysResponse: User profile with API key count and subscription
    """
    # Count total API keys owned by this user
    result = await db.execute(
        select(func.count(APIKey.id)).where(APIKey.user_id == user.id)
    )
    api_keys_count = result.scalar()
    
    # Get active subscription
    subscription, plan = await get_active_user_subscription(user.id, db)
    
    return UserWithKeysResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,  
        supabase_user_id=user.supabase_user_id,
        api_keys_count=api_keys_count,
        current_plan=plan.plan_name if plan else "free",
        subscription_status=subscription.status if subscription else None
    )


@router.post("/me/api-keys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
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
    
    The API key inherits the rate limit from the user's current subscription plan.
    If the user upgrades/downgrades their subscription, all their API keys
    will automatically use the new rate limits.
    
    Requires:
        - Valid Supabase JWT in Authorization header
        - Active user account
    
    Args:
        data (APIKeyCreate): API key creation data (name, optional settings)
    
    Returns:
        APIKeyCreateResponse: New API key with complete key value
    """
    # Verify that the user account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Get user's current subscription plan (SAFE MODE)
    result = await get_active_user_subscription(user.id, db)
    
    if result:
        subscription, plan = result
        plan_name = plan.plan_name if plan else "free"
    else:
        subscription, plan = None, None
        plan_name = "free"
    
    # Generate cryptographically secure API key
    key_data = generate_api_key()
    
    # Create API key record in database
    new_api_key = APIKey(
        user_id=user.id,
        key_hash=key_data["key_hash"],
        name=data.name,
        last_chars=key_data["last_chars"],
        is_active=True,
        rate_limit_plan=plan_name,  # Set to user's current plan
        scopes=data.scopes,
        allowed_ips=data.allowed_ips,
        expires_at=data.expires_at
    )
    
    db.add(new_api_key)
    await db.commit()
    await db.refresh(new_api_key)
    
    print(f"[API KEY] Created '{data.name}' for {user.email} (ID: {new_api_key.id}) - Plan: {plan_name}")
    
    # Return response with complete key (shown only this time)
    return APIKeyCreateResponse(
        id=new_api_key.id,
        user_id=new_api_key.user_id,
        name=new_api_key.name,
        last_chars=new_api_key.last_chars,
        is_active=new_api_key.is_active,
        rate_limit_plan=new_api_key.rate_limit_plan,
        scopes=new_api_key.scopes,
        created_at=new_api_key.created_at,
        last_used_at=new_api_key.last_used_at,
        revoked_at=new_api_key.revoked_at,
        expires_at=new_api_key.expires_at,
        api_key=key_data["key"]  # Complete key only returned here
    )


@router.get("/me/api-keys", response_model=List[APIKeyResponse])
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
        - Valid Supabase JWT in Authorization header OR
        - Valid API key in X-API-Key header
    
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
        key_id (int): ID of the API key to revoke
    
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
    api_key.is_active = False
    api_key.revoked_at = datetime.now()
    
    await db.commit()
    
    print(f"[API KEY] Revoked '{api_key.name}' (ID: {api_key.id}) for user {user.email}")
    
    return None
