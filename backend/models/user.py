"""User model."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration."""
    CUSTOMER = "customer"
    DRIVER = "driver"
    ADMIN = "admin"
    COMPANY = "company"


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)
    phone = Column(String, index=True)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    driver = relationship("Driver", back_populates="user", uselist=False)
    trips = relationship("Trip", back_populates="user", foreign_keys="Trip.user_id")
    notifications = relationship("Notification", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"
