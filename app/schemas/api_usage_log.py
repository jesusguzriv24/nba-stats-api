from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class APIUsageLogBase(BaseModel):
    """Base schema for API usage log"""
    endpoint: str = Field(..., max_length=255)
    http_method: str = Field(..., max_length=10)
    status_code: int = Field(..., ge=100, le=599)
    response_time_ms: Optional[int] = Field(None, ge=0)
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = None
    request_id: Optional[str] = Field(None, max_length=100)
    rate_limit_plan: Optional[str] = None
    rate_limited: bool = False
    error_message: Optional[str] = None


class APIUsageLogCreate(APIUsageLogBase):
    """Schema for creating API usage log"""
    user_id: int
    api_key_id: Optional[int] = None


class APIUsageLogResponse(APIUsageLogBase):
    """Schema for API usage log response"""
    id: int
    user_id: int
    api_key_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
