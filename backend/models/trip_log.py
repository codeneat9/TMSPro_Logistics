"""Trip log model for operational and decision audit trail."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class TripLog(Base):
    """Trip-level audit log entries."""

    __tablename__ = "trip_logs"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False, index=True)
    actor_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)

    event_type = Column(String, nullable=False)  # agent_decision, status_change, reroute
    message = Column(String, nullable=False)
    details = Column(String, nullable=True)  # JSON string payload

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    trip = relationship("Trip", back_populates="trip_logs")

    def __repr__(self):
        return f"<TripLog {self.event_type} for Trip {self.trip_id}>"
