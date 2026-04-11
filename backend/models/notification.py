"""Notification model."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


class NotificationType(str, enum.Enum):
    """Notification type enumeration."""
    TRIP_STARTED = "trip_started"
    TRIP_COMPLETED = "trip_completed"
    TRIP_DELAYED = "trip_delayed"
    TRIP_ASSIGNED = "trip_assigned"
    DRIVER_NEARBY = "driver_nearby"
    GEOFENCE_ALERT = "geofence_alert"
    REROUTE_SUGGESTED = "reroute_suggested"
    EMERGENCY = "emergency"
    SYSTEM = "system"


class Notification(Base):
    """Notification model for user alerts."""
    
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), index=True)
    
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    
    # Delivery status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    
    # Push notification tracking
    sent_via_fcm = Column(Boolean, default=False)
    fcm_response = Column(String)  # Success/failure response from FCM
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="notifications")
    trip = relationship("Trip", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.type} to {self.user_id}>"
