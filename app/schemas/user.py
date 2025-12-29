"""
Pydantic schemas for User model.

Updated to work with the new subscription system.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

from app.schemas.api_key import APIKeyResponse
from app.schemas.user_subscription import UserSubscriptionResponse


class UserBase(BaseModel):
    """
    Base schema for user with common fields.
    """
    email: EmailStr
    role: str = Field(default="user", max_length=50)
    is_active: bool = True


class UserCreate(UserBase):
    """
    Schema for creating a new user (via webhook from Supabase).
    
    This is used when synchronizing users from Supabase Auth
    to our local database.
    """
    supabase_user_id: str = Field(..., max_length=255)


class UserUpdate(BaseModel):
    """
    Schema for updating user (all fields optional).
    """
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """
    Schema for user response (basic info).
    """
    id: int
    supabase_user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserWithKeysResponse(UserResponse):
    """
    Schema for user with API key count and subscription info.
    
    This is returned from the /me endpoint to show the user
    their profile along with API key count and current plan.
    """
    api_keys_count: int
    current_plan: str  # Plan name (free, premium, pro)
    subscription_status: Optional[str] = None  # active, cancelled, expired, etc.
    
    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """
    Detailed user response with relationships (admin only).
    
    This includes full details of all API keys and subscriptions.
    Should only be used for admin endpoints.
    """
    api_keys: List["APIKeyResponse"] = []
    subscriptions: List["UserSubscriptionResponse"] = []

    class Config:
        from_attributes = True
