"""
API endpoints for subscription management.

This module provides REST API endpoints for users to:
- View available subscription plans
- Subscribe to a plan
- View their current subscription
- View subscription history
- Cancel subscriptions
- Reactivate cancelled subscriptions
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.subscription_plan import SubscriptionPlanPublic
from app.schemas.user_subscription import (
    UserSubscriptionResponse,
    UserSubscriptionCreate,
    UserSubscriptionWithPlan
)
from app.core.subscription_service import SubscriptionService

router = APIRouter()


@router.get("/plans", response_model=List[SubscriptionPlanPublic])
async def list_subscription_plans(db: AsyncSession = Depends(get_db)):
    """
    Get all available subscription plans.
    
    Returns all active subscription plans with their pricing and rate limits.
    This endpoint does NOT require authentication - it's public information
    for users to see available plans before signing up.
    
    Returns:
        List[SubscriptionPlanPublic]: List of available subscription plans
    """
    plans = await SubscriptionService.get_all_active_plans(db)
    return plans


@router.get("/me", response_model=UserSubscriptionWithPlan)
async def get_my_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the authenticated user's current active subscription.
    
    Returns the user's active subscription along with the plan details.
    If the user has no active subscription, returns 404.
    
    Requires:
        - Valid authentication (JWT or API Key)
    
    Returns:
        UserSubscriptionWithPlan: Active subscription with plan details
        
    Raises:
        HTTPException 404: If user has no active subscription
    """
    subscription = await SubscriptionService.get_active_subscription(db, user.id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found. You are on the free plan."
        )
    
    # Load plan relationship if not already loaded
    await db.refresh(subscription, ["plan"])
    
    return subscription


@router.get("/me/history", response_model=List[UserSubscriptionWithPlan])
async def get_my_subscription_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the authenticated user's subscription history.
    
    Returns all subscriptions (active, cancelled, expired) for the user,
    ordered by creation date (newest first). Useful for billing history.
    
    Requires:
        - Valid authentication (JWT or API Key)
    
    Returns:
        List[UserSubscriptionWithPlan]: List of all user subscriptions
    """
    subscriptions = await SubscriptionService.get_subscription_history(db, user.id)
    
    # Load plan relationships
    for subscription in subscriptions:
        await db.refresh(subscription, ["plan"])
    
    return subscriptions


@router.post("/subscribe", response_model=UserSubscriptionWithPlan, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    plan_name: str,
    billing_cycle: str = "monthly",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Subscribe to a plan.
    
    Creates a new subscription for the authenticated user. This is typically
    called after successful payment processing in your payment flow.
    
    Flow:
    1. User selects a plan in your frontend
    2. Frontend initiates payment with payment provider (Stripe, PayPal, etc.)
    3. Payment provider processes payment
    4. Your webhook receives payment confirmation
    5. Webhook calls this endpoint to create the subscription
    
    Args:
        plan_name (str): Name of plan to subscribe to (free, premium, pro)
        billing_cycle (str): Billing cycle - 'monthly' or 'yearly'
        
    Requires:
        - Valid authentication (JWT or API Key)
        - Active user account
    
    Returns:
        UserSubscriptionWithPlan: Created subscription with plan details
        
    Raises:
        HTTPException 400: If plan is invalid or billing cycle is invalid
        HTTPException 404: If plan not found
    """
    # Validate billing cycle
    if billing_cycle not in ["monthly", "yearly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Billing cycle must be 'monthly' or 'yearly'"
        )
    
    # Create subscription
    subscription = await SubscriptionService.create_subscription(
        db=db,
        user_id=user.id,
        plan_name=plan_name,
        billing_cycle=billing_cycle,
        payment_provider=None,  # Set this based on your payment flow
        payment_provider_subscription_id=None,  # Set this from payment webhook
        trial_days=0  # Set to > 0 if offering trial
    )
    
    # Load plan relationship
    await db.refresh(subscription, ["plan"])
    
    return subscription


@router.post("/me/cancel", response_model=UserSubscriptionWithPlan)
async def cancel_my_subscription(
    cancel_immediately: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel the authenticated user's active subscription.
    
    Supports two cancellation modes:
    - cancel_immediately=False (default): User keeps access until period ends
    - cancel_immediately=True: Access is revoked immediately
    
    Args:
        cancel_immediately (bool): If True, cancel immediately; if False, cancel at period end
        
    Requires:
        - Valid authentication (JWT or API Key)
        - Active subscription
    
    Returns:
        UserSubscriptionWithPlan: Updated subscription
        
    Raises:
        HTTPException 404: If no active subscription found
    """
    # Get active subscription
    subscription = await SubscriptionService.get_active_subscription(db, user.id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription to cancel"
        )
    
    # Cancel subscription
    subscription = await SubscriptionService.cancel_subscription(
        db=db,
        subscription_id=subscription.id,
        user_id=user.id,
        cancel_at_period_end=not cancel_immediately
    )
    
    # Load plan relationship
    await db.refresh(subscription, ["plan"])
    
    return subscription


@router.post("/me/reactivate", response_model=UserSubscriptionWithPlan)
async def reactivate_my_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reactivate a cancelled subscription.
    
    Allows users to undo cancellation before the subscription period ends.
    This only works if the subscription is still in its paid period.
    
    Requires:
        - Valid authentication (JWT or API Key)
        - Previously cancelled subscription that hasn't expired yet
    
    Returns:
        UserSubscriptionWithPlan: Reactivated subscription
        
    Raises:
        HTTPException 404: If no cancelled subscription found
        HTTPException 400: If subscription has already expired
    """
    # Get active subscription (even if cancelled, it may still be in valid period)
    subscription = await SubscriptionService.get_active_subscription(db, user.id)
    
    if not subscription or not subscription.cancelled_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cancelled subscription found to reactivate"
        )
    
    # Reactivate subscription
    subscription = await SubscriptionService.reactivate_subscription(
        db=db,
        subscription_id=subscription.id,
        user_id=user.id
    )
    
    # Load plan relationship
    await db.refresh(subscription, ["plan"])
    
    return subscription
