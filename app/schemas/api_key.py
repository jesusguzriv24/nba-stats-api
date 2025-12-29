"""
Pydantic schemas for APIKey model.

Updated to work with the new subscription system.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class APIKeyBase(BaseModel):
    """
    Base schema for API key with common fields.
    """
    name: str = Field(..., max_length=100)
    scopes: Optional[str] = Field(None, max_length=500)
    allowed_ips: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = None


class APIKeyCreate(BaseModel):
    """
    Schema for creating a new API key.
    
    Only requires name and optional security settings.
    The rate_limit_plan is automatically set based on user's subscription.
    """
    name: str = Field(..., max_length=100, description="Human-readable name for this API key")
    scopes: Optional[str] = Field(None, max_length=500, description="Comma-separated list of scopes/permissions")
    allowed_ips: Optional[str] = Field(None, max_length=500, description="Comma-separated list of allowed IP addresses")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date for temporary keys")


class APIKeyUpdate(BaseModel):
    """
    Schema for updating API key (all fields optional).
    
    Allows updating name, status, custom rate limits, and security settings.
    """
    name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    custom_rate_limit_per_minute: Optional[int] = Field(None, ge=0)
    custom_rate_limit_per_hour: Optional[int] = Field(None, ge=0)
    custom_rate_limit_per_day: Optional[int] = Field(None, ge=0)
    scopes: Optional[str] = None
    allowed_ips: Optional[str] = None
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    """
    Schema for API key response (without sensitive data).
    
    Never includes the actual API key - only the last 8 characters
    are shown for identification purposes.
    """
    id: int
    user_id: int
    name: str
    last_chars: str
    is_active: bool
    rate_limit_plan: str
    custom_rate_limit_per_minute: Optional[int]
    custom_rate_limit_per_hour: Optional[int]
    custom_rate_limit_per_day: Optional[int]
    scopes: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    revoked_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyCreateResponse(APIKeyResponse):
    """
    Schema for API key creation response (includes the actual key once).
    
    IMPORTANT: This is the ONLY time the complete API key is returned.
    The key should be displayed to the user immediately and they should
    store it securely. It cannot be retrieved again.
    """
    api_key: str = Field(..., description="Complete API key - SHOWN ONLY ONCE")


class APIKeyWithUsage(APIKeyResponse):
    """
    Schema for API key with current usage statistics.
    
    Includes real-time usage counts for monitoring purposes.
    """
    usage_today: int
    usage_this_hour: int
    usage_this_minute: int

    class Config:
        from_attributes = True
