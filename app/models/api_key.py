from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class APIKey(Base):
    """
    API Key model for programmatic access to the API.
    
    Note: The actual API key is never stored in the database - only its Argon2 hash
    for security purposes. The last 8 characters are stored for UI display purposes.
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
    
    # Rate limiting plan associated with this specific key
    rate_limit_plan = Column(String(50), nullable=False, default="free")
    
    # Timestamp: when the API key was created
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    
    # Timestamp: when the API key was revoked (NULL if still active)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship: back reference to the User who owns this key
    user = relationship(
        "User", 
        back_populates="api_keys",
        lazy="joined"
    )

    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', last_chars='****{self.last_chars}')>"
