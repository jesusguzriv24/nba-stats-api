from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserSubscription(Base):
    """
    User subscription model.
    
    Tracks individual user subscriptions to specific plans, including
    purchase dates, renewal dates, and subscription status.
    """
    __tablename__ = "user_subscriptions"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key: relationship to User
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Foreign key: relationship to SubscriptionPlan
    plan_id = Column(
        Integer,
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Subscription status: 'active', 'cancelled', 'expired', 'past_due'
    status = Column(String(50), nullable=False, default="active", index=True)
    
    # Billing cycle: 'monthly', 'yearly'
    billing_cycle = Column(String(50), nullable=False, default="monthly")
    
    # Payment information
    payment_provider = Column(String(50), nullable=True)  # 'stripe', 'paypal', etc.
    payment_provider_subscription_id = Column(String(255), nullable=True, index=True)
    
    # Subscription dates
    subscribed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Cancellation information
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    
    # Trial information
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    
    # Price paid (snapshot at subscription time, in cents)
    price_paid_cents = Column(Integer, nullable=False)
    
    # Auto-renewal flag
    auto_renew = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    user = relationship(
        "User",
        back_populates="subscriptions",
        lazy="joined"
    )
    plan = relationship(
        "SubscriptionPlan",
        back_populates="user_subscriptions",
        lazy="joined"
    )
    
    def __repr__(self):
        return f"<UserSubscription(id={self.id}, user_id={self.user_id}, plan_id={self.plan_id}, status='{self.status}')>"
