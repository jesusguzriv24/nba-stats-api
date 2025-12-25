"""
Pydantic schemas for User models and validation.
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    """
    Schema for user response data.
    
    This schema is used for all user queries and API responses. It contains
    public user information without sensitive data.
    
    Attributes:
        id: Unique user identifier
        email: User email address (validated format)
        role: User role ('user', 'admin', etc.)
        is_active: Account status
        rate_limit_tier: Associated rate limiting plan ('free', 'pro', 'enterprise')
        usage_count: Total API usage counter
        created_at: Account creation timestamp
    """
    id: int
    email: EmailStr
    role: str
    is_active: bool
    rate_limit_tier: str
    usage_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserWithKeysResponse(UserResponse):
    """
    Schema for user response with API key count.
    
    Extends UserResponse with additional metadata about the user's API keys.
    Useful for endpoints that need to show key management information.
    
    Attributes:
        api_keys_count: Total number of API keys owned by the user
    """
    api_keys_count: int
