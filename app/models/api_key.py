from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class APIKey(Base):
    """
    API Key model for programmatic access to the API.
    
    Note: The actual API key is never stored in the database - only its Argon2 hash
    for security purposes. The last 8 characters are stored for UI display purposes.
    Rate limiting is determined by the user's active subscription plan.
    """
    __tablename__ = "api_keys"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key: relationship to the User who owns this API key
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Argon2 hash of the actual API key (never store the raw key)
    key_hash = Column(String(255), nullable=False, index=True)
    
    # Human-readable name for this API key (e.g., "Production API", "Development Key")
    name = Column(String(100), nullable=False)
    
    # Last 8 characters of the API key (for display in UI without exposing full key)
    last_chars = Column(String(8), nullable=False)
    
    # Status of the API key
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Rate limiting plan reference (links to subscription_plans.plan_name)
    # This is derived from the user's active subscription but can be overridden
    rate_limit_plan = Column(String(50), nullable=False, default="free", index=True)
    
    # Optional: Per-key rate limit override (NULL means use plan defaults)
    custom_rate_limit_per_minute = Column(Integer, nullable=True)
    custom_rate_limit_per_hour = Column(Integer, nullable=True)
    custom_rate_limit_per_day = Column(Integer, nullable=True)
    
    # Scope/permissions for this specific key (JSON string for flexibility)
    scopes = Column(String(500), nullable=True)
    
    # Security: IP whitelist (comma-separated IPs, NULL for no restriction)
    allowed_ips = Column(String(500), nullable=True)
    
    # Timestamp: when the API key was created
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Timestamp: when the API key was last used
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamp: when the API key was revoked (NULL if still active)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamp: optional expiration date for the key
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship: back reference to the User who owns this key
    user = relationship(
        "User",
        back_populates="api_keys",
        lazy="joined"
    )
    
    # Relationships: Usage logs for this specific key
    usage_logs = relationship(
        "APIUsageLog",
        back_populates="api_key",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Relationships: Aggregated usage for this key
    usage_aggregates = relationship(
        "APIUsageAggregate",
        back_populates="api_key",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', last_chars='****{self.last_chars}')>"
