from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class SubscriptionPlan(Base):
    """
    Subscription plan configuration model.
    
    Defines available subscription tiers with their rate limits and pricing.
    This serves as the catalog of available plans that users can subscribe to.
    """
    __tablename__ = "subscription_plans"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Plan identifier: 'free', 'premium', 'pro'
    plan_name = Column(String(50), unique=True, nullable=False, index=True)
    
    # Human-readable display name
    display_name = Column(String(100), nullable=False)
    
    # Plan description for UI display
    description = Column(Text, nullable=True)
    
    # Rate limiting configuration
    rate_limit_per_minute = Column(Integer, nullable=False)
    rate_limit_per_hour = Column(Integer, nullable=False)
    rate_limit_per_day = Column(Integer, nullable=False)
    
    # Pricing information (in USD cents to avoid floating point issues)
    price_monthly_cents = Column(Integer, nullable=False, default=0)
    price_yearly_cents = Column(Integer, nullable=False, default=0)
    
    # Promotional pricing (NULL if no promotion active)
    promo_price_monthly_cents = Column(Integer, nullable=True)
    promo_price_yearly_cents = Column(Integer, nullable=True)
    promo_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Plan status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Feature flags (stored as JSON for flexibility)
    features = Column(Text, nullable=True)  # JSON string of features
    
    # Sort order for UI display
    display_order = Column(Integer, nullable=False, default=0)
    
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
    user_subscriptions = relationship(
        "UserSubscription",
        back_populates="plan",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<SubscriptionPlan(id={self.id}, plan_name='{self.plan_name}')>"
