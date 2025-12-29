from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    """
    User model synchronized with Supabase Auth.
    
    Note: Passwords are not stored here - Supabase Auth manages authentication.
    This model only stores user metadata and account information.
    """
    __tablename__ = "users"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Supabase Auth UUID (auth.users.id)
    supabase_user_id = Column(String(255), unique=True, index=True, nullable=False)
    
    # User email address
    email = Column(String(255), unique=True, index=True, nullable=False)
    
    # User role: 'user', 'admin', etc.
    role = Column(String(50), nullable=False, default="user")
    
    # Account status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps: when the user account was created
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Timestamps: when the user account was last updated
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships: One user can have multiple API keys
    api_keys = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Relationships: One user can have multiple subscriptions (historical)
    subscriptions = relationship(
        "UserSubscription",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Relationships: Usage logs for analytics
    usage_logs = relationship(
        "APIUsageLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Relationships: Aggregated usage statistics
    usage_aggregates = relationship(
        "APIUsageAggregate",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
