from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum

from app.schemas.subscription_plan import SubscriptionPlanResponse


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration"""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"


class BillingCycle(str, Enum):
    """Billing cycle enumeration"""
    MONTHLY = "monthly"
    YEARLY = "yearly"


class UserSubscriptionBase(BaseModel):
    """Base schema for user subscription"""
    plan_id: int
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    payment_provider: Optional[str] = None
    payment_provider_subscription_id: Optional[str] = None
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    price_paid_cents: int = Field(..., ge=0)
    auto_renew: bool = True


class UserSubscriptionCreate(BaseModel):
    """Schema for creating a user subscription"""
    user_id: int
    plan_id: int
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    payment_provider: Optional[str] = None
    payment_provider_subscription_id: Optional[str] = None
    current_period_start: datetime
    current_period_end: datetime
    price_paid_cents: int = Field(..., ge=0)
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None


class UserSubscriptionUpdate(BaseModel):
    """Schema for updating user subscription"""
    status: Optional[SubscriptionStatus] = None
    current_period_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = None
    auto_renew: Optional[bool] = None


class UserSubscriptionResponse(UserSubscriptionBase):
    """Schema for user subscription response"""
    id: int
    user_id: int
    subscribed_at: datetime
    cancelled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserSubscriptionWithPlan(UserSubscriptionResponse):
    """Schema including plan details"""
    plan: "SubscriptionPlanResponse"  # Forward reference

    class Config:
        from_attributes = True
