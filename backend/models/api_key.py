"""API key model for third-party integrations."""

from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class ApiKey(Base):
    """API key model for third-party integrations."""
    
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Key details
    key_hash = Column(String, unique=True, nullable=False)  # SHA256 hash, not plain text
    name = Column(String, nullable=False)
    
    # Scope
    scope = Column(String, nullable=False)  # Comma-separated: "trips.read", "trips.write", "locations.read", etc.
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)  # None = never expires
    
    # Usage tracking
    last_used_at = Column(DateTime)
    call_count = Column(String, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def is_valid(self) -> bool:
        """Check if API key is valid."""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True

    def __repr__(self):
        return f"<ApiKey {self.name}>"
