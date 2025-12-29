"""
Module for managing user subscriptions.

This module provides functionality to assign subscription plans to users.
It handles the creation of UserSubscription records linking users to plans.
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from dateutil.relativedelta import relativedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user_subscription import UserSubscription
from app.models.subscription_plan import SubscriptionPlan
from app.core.database import async_session_maker


async def get_or_create_free_plan() -> SubscriptionPlan:
    """
    Get the 'free' subscription plan, create it if it doesn't exist.
    
    Returns:
        SubscriptionPlan: The free plan object
    """
    async with async_session_maker() as session:
        # Try to get existing free plan
        result = await session.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.plan_name == "free")
        )
        free_plan = result.scalar_one_or_none()
        
        if free_plan:
            return free_plan
        
        # Create free plan if it doesn't exist
        print("  [*] Free plan not found, creating it...")
        free_plan = SubscriptionPlan(
            plan_name="free",
            display_name="Free Plan",
            description="Free tier with limited API access",
            rate_limit_per_minute=10,
            rate_limit_per_hour=100,
            rate_limit_per_day=1000,
            price_monthly_cents=0,
            price_yearly_cents=0,
            is_active=True,
            display_order=1,
            features='["basic_access", "rate_limited"]'
        )
        session.add(free_plan)
        await session.commit()
        await session.refresh(free_plan)
        print(f"  [+] Free plan created with ID: {free_plan.id}")
        
        return free_plan


async def assign_free_subscription(user) -> tuple[UserSubscription, str]:
    """
    Assign a free subscription plan to a user.
    
    Args:
        user: The user object to assign subscription to
    
    Returns:
        tuple[UserSubscription, str]: Created subscription and status message
    
    Raises:
        Exception: If user doesn't exist or plan not found
    """
    async with async_session_maker() as session:
        user_id = user.id
        
        # Check if user already has active subscription
        result = await session.execute(
            text("SELECT id FROM user_subscriptions WHERE user_id = :user_id AND status = 'active'"),
            {"user_id": user_id}
        )
        existing_sub = result.scalar_one_or_none()
        
        if existing_sub:
            result = await session.execute(
                select(UserSubscription).where(UserSubscription.id == existing_sub)
            )
            sub = result.scalar_one_or_none()
            return sub, f"User already has an active subscription"
        
        # Get or create free plan
        free_plan = await get_or_create_free_plan()
        
        # Create subscription with 1 month validity
        now = datetime.now()
        next_month = now + relativedelta(months=1)
        
        new_subscription = UserSubscription(
            user_id=user_id,
            plan_id=free_plan.id,
            status="active",
            billing_cycle="monthly",
            subscribed_at=now,
            current_period_start=now,
            current_period_end=next_month,
            price_paid_cents=0  # Free plan costs nothing
        )
        
        session.add(new_subscription)
        await session.commit()
        await session.refresh(new_subscription)
        
        message = (
            f"✓ Free subscription assigned successfully!\n"
            f"  - Subscription ID: {new_subscription.id}\n"
            f"  - Plan: {free_plan.plan_name}\n"
            f"  - Status: {new_subscription.status}\n"
            f"  - Period: {new_subscription.subscribed_at.date()} to {new_subscription.current_period_end.date()}\n"
            f"  - Rate Limits:\n"
            f"    • Per Minute: {free_plan.rate_limit_per_minute}\n"
            f"    • Per Hour: {free_plan.rate_limit_per_hour}\n"
            f"    • Per Day: {free_plan.rate_limit_per_day}"
        )
        
        return new_subscription, message


async def get_user_subscription(user_id: int) -> UserSubscription | None:
    """
    Get the active subscription for a user.
    
    Args:
        user_id (int): User ID
    
    Returns:
        UserSubscription | None: Active subscription if found, None otherwise
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .where(UserSubscription.status == "active")
        )
        return result.scalar_one_or_none()


async def get_subscription_plan(plan_name: str) -> SubscriptionPlan | None:
    """
    Get a subscription plan by name.
    
    Args:
        plan_name (str): Plan name (e.g., "free", "premium")
    
    Returns:
        SubscriptionPlan | None: Plan object if found, None otherwise
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.plan_name == plan_name)
        )
        return result.scalar_one_or_none()


if __name__ == "__main__":
    # Test creating a subscription
    async def main():
        from user_generator import create_test_user
        
        print("\n" + "="*60)
        print("TEST: Creating user and assigning subscription")
        print("="*60 + "\n")
        
        user, user_msg = await create_test_user("test_subscription@example.com")
        print(user_msg)
        
        print("\n" + "-"*60 + "\n")
        
        subscription, sub_msg = await assign_free_subscription(user)
        print(sub_msg)
        
        print("\n" + "="*60 + "\n")
    
    asyncio.run(main())
