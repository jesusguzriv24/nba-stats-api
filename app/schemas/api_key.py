"""
Pydantic schemas for API Key models and validation.
"""
from datetime import datetime
from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    """
    Schema for creating a new API key.
    
    Attributes:
        name: Human-readable name for the API key for organizational purposes
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Descriptive name for the API key (e.g., 'Production API', 'Mobile App')",
        examples=["NBA Props Analyzer", "Production API", "Dev Environment"]
    )


class APIKeyResponse(BaseModel):
    """
    Schema for API key response (without exposing the full key).
    
    This schema is used for all API key queries and responses. The full key
    is never shown after the initial creation for security reasons.
    
    Attributes:
        id: Unique API key identifier
        name: Human-readable name of the key
        last_chars: Last 8 characters of the key (for identification)
        is_active: Whether the key is currently active
        rate_limit_plan: Associated rate limiting tier
        created_at: When the key was created
        revoked_at: When the key was revoked (None if still active)
    """
    id: int
    name: str
    last_chars: str
    is_active: bool
    rate_limit_plan: str
    created_at: datetime
    revoked_at: datetime | None = None
    
    class Config:
        from_attributes = True


class APIKeyResponseWithKey(APIKeyResponse):
    """
    Schema for API key response that includes the full key (creation response only).
    
    WARNING: The complete API key is shown only once during creation. The user is
    responsible for securely storing it. Once the user navigates away or the response
    is closed, the full key will never be displayed again.
    
    Attributes:
        key: The complete API key (shown only during creation)
    """
    key: str = Field(
        ...,
        description="⚠️ Complete API key. Store it securely - it will never be shown again."
    )
