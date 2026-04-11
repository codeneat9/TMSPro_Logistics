"""Location model for GPS tracking."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship

from backend.database import Base


class Location(Base):
    """Location model for high-frequency GPS data."""
    
    __tablename__ = "locations"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False, index=True)
    
    # GPS coordinates
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Movement data
    speed_kmh = Column(Float)
    heading = Column(Float)  # 0-360 degrees
    altitude = Column(Float)
    
    # Accuracy
    accuracy_meters = Column(Float)
    
    # Timestamp
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # Relationships
    trip = relationship("Trip", back_populates="locations")

    # Composite index for efficient time-series queries
    __table_args__ = (
        Index("ix_location_trip_time", "trip_id", "recorded_at"),
    )

    def __repr__(self):
        return f"<Location {self.trip_id} at {self.recorded_at}>"
