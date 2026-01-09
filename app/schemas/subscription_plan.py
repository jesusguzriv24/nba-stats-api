from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


class SubscriptionPlanBase(BaseModel):
    """Base schema for subscription plan"""
    plan_name: str = Field(..., max_length=50)
    display_name: str = Field(..., max_length=100)
    description: Optional[str] = None
    rate_limit_per_minute: int = Field(..., ge=0)
    rate_limit_per_hour: int = Field(..., ge=0)
    rate_limit_per_day: int = Field(..., ge=0)
    max_api_keys: int = Field(default=1, ge=1)
    price_monthly_cents: int = Field(default=0, ge=0)
    price_yearly_cents: int = Field(default=0, ge=0)
    promo_price_monthly_cents: Optional[int] = Field(None, ge=0)
    promo_price_yearly_cents: Optional[int] = Field(None, ge=0)
    promo_expires_at: Optional[datetime] = None
    is_active: bool = True
    features: Optional[str] = None  # JSON string
    display_order: int = 0


class SubscriptionPlanCreate(SubscriptionPlanBase):
    """Schema for creating a new subscription plan"""
    pass


class SubscriptionPlanUpdate(BaseModel):
    """Schema for updating subscription plan (all fields optional)"""
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=0)
    rate_limit_per_hour: Optional[int] = Field(None, ge=0)
    rate_limit_per_day: Optional[int] = Field(None, ge=0)
    max_api_keys: Optional[int] = Field(None, ge=1)
    price_monthly_cents: Optional[int] = Field(None, ge=0)
    price_yearly_cents: Optional[int] = Field(None, ge=0)
    promo_price_monthly_cents: Optional[int] = Field(None, ge=0)
    promo_price_yearly_cents: Optional[int] = Field(None, ge=0)
    promo_expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    features: Optional[str] = None
    display_order: Optional[int] = None


class SubscriptionPlanResponse(SubscriptionPlanBase):
    """Schema for subscription plan response"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionPlanPublic(BaseModel):
    """Public schema for displaying plans to users (without internal details)"""
    id: int
    plan_name: str
    display_name: str
    description: Optional[str]
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    rate_limit_per_day: int
    max_api_keys: int
    price_monthly_cents: int
    price_yearly_cents: int
    promo_price_monthly_cents: Optional[int]
    promo_price_yearly_cents: Optional[int]
    promo_expires_at: Optional[datetime]
    features: Optional[str]
    display_order: int

    class Config:
        from_attributes = True
