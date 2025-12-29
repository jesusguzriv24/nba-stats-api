from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class APIUsageLog(Base):
    """
    API usage log model for tracking individual API requests.
    
    Records every API request with detailed information for analytics,
    monitoring, and rate limiting enforcement. Critical for audit trails.
    """
    __tablename__ = "api_usage_logs"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key: relationship to User
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Foreign key: relationship to APIKey
    api_key_id = Column(
        Integer,
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Request information
    endpoint = Column(String(255), nullable=False, index=True)
    http_method = Column(String(10), nullable=False)
    
    # Response information
    status_code = Column(Integer, nullable=False, index=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Request metadata
    ip_address = Column(String(45), nullable=True, index=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Tracking information
    request_id = Column(String(100), nullable=True, index=True)
    
    # Rate limiting context at request time
    rate_limit_plan = Column(String(50), nullable=True)
    rate_limited = Column(Boolean, nullable=False, default=False)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Request timestamp (indexed for time-based queries)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Relationships
    user = relationship("User", back_populates="usage_logs", lazy="select")
    api_key = relationship("APIKey", back_populates="usage_logs", lazy="select")
    
    def __repr__(self):
        return f"<APIUsageLog(id={self.id}, user_id={self.user_id}, endpoint='{self.endpoint}', status={self.status_code})>"
