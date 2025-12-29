from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class APIUsageAggregate(Base):
    """
    Aggregated API usage statistics model.
    
    Stores pre-computed usage counts per user/API key for efficient
    rate limiting checks and usage reporting. Updated periodically
    or in real-time via Redis counters.
    """
    __tablename__ = "api_usage_aggregates"
    
    # Composite unique constraint to prevent duplicate entries
    __table_args__ = (
        UniqueConstraint('user_id', 'api_key_id', 'date', 'hour', name='uq_usage_aggregate'),
    )
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key: relationship to User
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Foreign key: relationship to APIKey (NULL for aggregated user stats)
    api_key_id = Column(
        Integer,
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Time dimensions for aggregation
    date = Column(Date, nullable=False, index=True)
    hour = Column(Integer, nullable=True)  # 0-23, NULL for daily aggregates
    
    # Aggregated counts
    request_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)  # 2xx responses
    error_count = Column(Integer, nullable=False, default=0)    # 4xx + 5xx responses
    rate_limited_count = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    avg_response_time_ms = Column(Integer, nullable=True)
    
    # Plan context at aggregation time
    rate_limit_plan = Column(String(50), nullable=True)
    
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
    user = relationship("User", back_populates="usage_aggregates", lazy="select")
    api_key = relationship("APIKey", back_populates="usage_aggregates", lazy="select")
    
    def __repr__(self):
        return f"<APIUsageAggregate(id={self.id}, user_id={self.user_id}, date={self.date}, requests={self.request_count})>"
