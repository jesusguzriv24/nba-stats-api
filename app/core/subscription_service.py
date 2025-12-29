"""
Service layer for subscription management.

This module contains business logic for handling subscriptions, including
creating, updating, canceling subscriptions, and checking subscription status.
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user_subscription import UserSubscription
from app.models.subscription_plan import SubscriptionPlan
from app.schemas.user_subscription import UserSubscriptionCreate


class SubscriptionService:
    """
    Service class for subscription-related operations.
    
    This class encapsulates all business logic related to subscriptions,
    providing a clean interface for controllers/endpoints to use.
    """
    
    @staticmethod
    async def get_plan_by_name(db: AsyncSession, plan_name: str) -> SubscriptionPlan:
        """
        Retrieve a subscription plan by its name.
        
        Args:
            db (AsyncSession): Database session
            plan_name (str): Name of the plan (e.g., 'free', 'premium', 'pro')
            
        Returns:
            SubscriptionPlan: The subscription plan object
            
        Raises:
            HTTPException 404: If plan not found
        """
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.plan_name == plan_name)
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription plan '{plan_name}' not found"
            )
        
        return plan
    
    @staticmethod
    async def get_plan_by_id(db: AsyncSession, plan_id: int) -> SubscriptionPlan:
        """
        Retrieve a subscription plan by its ID.
        
        Args:
            db (AsyncSession): Database session
            plan_id (int): ID of the plan
            
        Returns:
            SubscriptionPlan: The subscription plan object
            
        Raises:
            HTTPException 404: If plan not found
        """
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription plan with ID {plan_id} not found"
            )
        
        return plan
    
    @staticmethod
    async def get_all_active_plans(db: AsyncSession) -> list[SubscriptionPlan]:
        """
        Retrieve all active subscription plans.
        
        Returns plans ordered by display_order for consistent UI presentation.
        
        Args:
            db (AsyncSession): Database session
            
        Returns:
            list[SubscriptionPlan]: List of active subscription plans
        """
        result = await db.execute(
            select(SubscriptionPlan)
            .where(SubscriptionPlan.is_active == True)
            .order_by(SubscriptionPlan.display_order)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_active_subscription(
        db: AsyncSession, 
        user_id: int
    ) -> UserSubscription | None:
        """
        Get the user's currently active subscription.
        
        A subscription is considered active if:
        - Status is 'active'
        - Current period has not ended yet
        
        Args:
            db (AsyncSession): Database session
            user_id (int): ID of the user
            
        Returns:
            UserSubscription | None: Active subscription or None if no active subscription
        """
        result = await db.execute(
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .where(UserSubscription.status == "active")
            .where(UserSubscription.current_period_end > datetime.now())
            .order_by(UserSubscription.current_period_end.desc())
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_subscription_history(
        db: AsyncSession, 
        user_id: int
    ) -> list[UserSubscription]:
        """
        Get all subscriptions for a user (current and historical).
        
        Returns subscriptions ordered by creation date (newest first).
        Useful for billing history and subscription management UI.
        
        Args:
            db (AsyncSession): Database session
            user_id (int): ID of the user
            
        Returns:
            list[UserSubscription]: List of all user subscriptions
        """
        result = await db.execute(
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .order_by(UserSubscription.created_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def create_subscription(
        db: AsyncSession,
        user_id: int,
        plan_name: str,
        billing_cycle: str = "monthly",
        payment_provider: str = None,
        payment_provider_subscription_id: str = None,
        trial_days: int = 0
    ) -> UserSubscription:
        """
        Create a new subscription for a user.
        
        This method handles the complete subscription creation process:
        1. Validates the plan exists and is active
        2. Checks for existing active subscriptions (optionally cancel them)
        3. Calculates subscription periods and pricing
        4. Creates the subscription record
        5. Handles trial periods if applicable
        
        Args:
            db (AsyncSession): Database session
            user_id (int): ID of the user subscribing
            plan_name (str): Name of the plan to subscribe to
            billing_cycle (str): 'monthly' or 'yearly'
            payment_provider (str, optional): Payment provider name (e.g., 'stripe')
            payment_provider_subscription_id (str, optional): Provider's subscription ID
            trial_days (int): Number of trial days (0 for no trial)
            
        Returns:
            UserSubscription: The created subscription
            
        Raises:
            HTTPException 400: If plan is not active or other validation fails
            HTTPException 404: If plan not found
        """
        # Retrieve the subscription plan
        plan = await SubscriptionService.get_plan_by_name(db, plan_name)
        
        # Verify plan is active
        if not plan.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subscription plan '{plan_name}' is not available"
            )
        
        # Check for existing active subscription
        existing_subscription = await SubscriptionService.get_active_subscription(
            db, user_id
        )
        
        if existing_subscription:
            # Optional: Auto-cancel existing subscription or raise error
            # For now, we'll allow multiple subscriptions but you may want to handle this
            print(f"[WARNING] User {user_id} already has active subscription {existing_subscription.id}")
        
        # Calculate subscription dates
        now = datetime.now()
        
        # Handle trial period
        if trial_days > 0:
            trial_start = now
            trial_end = now + timedelta(days=trial_days)
            current_period_start = trial_start
        else:
            trial_start = None
            trial_end = None
            current_period_start = now
        
        # Calculate period end based on billing cycle
        if billing_cycle == "yearly":
            current_period_end = current_period_start + timedelta(days=365)
            price_paid_cents = plan.price_yearly_cents
        else:  # monthly
            current_period_end = current_period_start + timedelta(days=30)
            price_paid_cents = plan.price_monthly_cents
        
        # Apply promotional pricing if active
        if plan.promo_expires_at and plan.promo_expires_at > now:
            if billing_cycle == "yearly" and plan.promo_price_yearly_cents:
                price_paid_cents = plan.promo_price_yearly_cents
            elif billing_cycle == "monthly" and plan.promo_price_monthly_cents:
                price_paid_cents = plan.promo_price_monthly_cents
        
        # Create subscription record
        new_subscription = UserSubscription(
            user_id=user_id,
            plan_id=plan.id,
            status="active",
            billing_cycle=billing_cycle,
            payment_provider=payment_provider,
            payment_provider_subscription_id=payment_provider_subscription_id,
            subscribed_at=now,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            trial_start=trial_start,
            trial_end=trial_end,
            price_paid_cents=price_paid_cents,
            auto_renew=True
        )
        
        db.add(new_subscription)
        await db.commit()
        await db.refresh(new_subscription)
        
        print(f"[SUCCESS] Created subscription {new_subscription.id} for user {user_id} - Plan: {plan_name}")
        
        return new_subscription
    
    @staticmethod
    async def cancel_subscription(
        db: AsyncSession,
        subscription_id: int,
        user_id: int,
        cancel_at_period_end: bool = True
    ) -> UserSubscription:
        """
        Cancel a user's subscription.
        
        Supports two cancellation modes:
        1. Immediate cancellation (cancel_at_period_end=False)
        2. Cancel at period end (cancel_at_period_end=True) - user keeps access until paid period ends
        
        Args:
            db (AsyncSession): Database session
            subscription_id (int): ID of subscription to cancel
            user_id (int): ID of user (for authorization check)
            cancel_at_period_end (bool): If True, access continues until period ends
            
        Returns:
            UserSubscription: The updated subscription
            
        Raises:
            HTTPException 404: If subscription not found
            HTTPException 403: If subscription doesn't belong to user
        """
        # Retrieve subscription
        result = await db.execute(
            select(UserSubscription).where(UserSubscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        # Verify ownership
        if subscription.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to cancel this subscription"
            )
        
        # Update subscription
        now = datetime.now()
        subscription.cancelled_at = now
        subscription.cancel_at_period_end = cancel_at_period_end
        subscription.auto_renew = False
        
        # If immediate cancellation, mark as cancelled now
        if not cancel_at_period_end:
            subscription.status = "cancelled"
            subscription.current_period_end = now
        
        await db.commit()
        await db.refresh(subscription)
        
        print(f"[SUCCESS] Cancelled subscription {subscription_id} for user {user_id}")
        
        return subscription
    
    @staticmethod
    async def reactivate_subscription(
        db: AsyncSession,
        subscription_id: int,
        user_id: int
    ) -> UserSubscription:
        """
        Reactivate a cancelled subscription (if not expired yet).
        
        This allows users to undo cancellation before the period ends.
        Only works if the subscription is still in the current paid period.
        
        Args:
            db (AsyncSession): Database session
            subscription_id (int): ID of subscription to reactivate
            user_id (int): ID of user (for authorization check)
            
        Returns:
            UserSubscription: The reactivated subscription
            
        Raises:
            HTTPException 404: If subscription not found
            HTTPException 403: If subscription doesn't belong to user
            HTTPException 400: If subscription has already expired
        """
        # Retrieve subscription
        result = await db.execute(
            select(UserSubscription).where(UserSubscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        # Verify ownership
        if subscription.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to reactivate this subscription"
            )
        
        # Check if subscription period has already ended
        if subscription.current_period_end < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reactivate expired subscription. Please create a new subscription."
            )
        
        # Reactivate subscription
        subscription.status = "active"
        subscription.cancelled_at = None
        subscription.cancel_at_period_end = False
        subscription.auto_renew = True
        
        await db.commit()
        await db.refresh(subscription)
        
        print(f"[SUCCESS] Reactivated subscription {subscription_id} for user {user_id}")
        
        return subscription
