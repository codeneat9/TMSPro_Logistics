"""Compliance log model."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class ComplianceLog(Base):
    """Compliance log model for audit trail."""
    
    __tablename__ = "compliance_logs"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False, index=True)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False, index=True)
    
    # Event
    event_type = Column(String, nullable=False)  # "speeding", "harsh_brake", "off_route", "rest_violation", etc.
    event_description = Column(String)
    severity = Column(String)  # "low", "medium", "high", "critical"
    
    # Details
    details = Column(String)  # JSON or text with event details
    
    # Location
    latitude = Column(String)
    longitude = Column(String)
    
    # Action taken
    action_taken = Column(String)  # "warning_issued", "incident_logged", "escalated", etc.
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    trip = relationship("Trip", back_populates="compliance_logs")
    driver = relationship("Driver", foreign_keys=[driver_id])

    def __repr__(self):
        return f"<ComplianceLog {self.event_type} for Trip {self.trip_id}>"
