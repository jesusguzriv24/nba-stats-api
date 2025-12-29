from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class APIUsageAggregateBase(BaseModel):
    """Base schema for API usage aggregate"""
    date: date
    hour: Optional[int] = Field(None, ge=0, le=23)
    request_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    rate_limited_count: int = Field(default=0, ge=0)
    avg_response_time_ms: Optional[int] = Field(None, ge=0)
    rate_limit_plan: Optional[str] = None


class APIUsageAggregateCreate(APIUsageAggregateBase):
    """Schema for creating usage aggregate"""
    user_id: int
    api_key_id: Optional[int] = None


class APIUsageAggregateResponse(APIUsageAggregateBase):
    """Schema for usage aggregate response"""
    id: int
    user_id: int
    api_key_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UsageStats(BaseModel):
    """Schema for usage statistics summary"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    rate_limited_requests: int
    avg_response_time_ms: Optional[float]
    period_start: datetime
    period_end: datetime
