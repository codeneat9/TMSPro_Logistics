"""Vehicle model."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


class VehicleStatus(str, enum.Enum):
    """Vehicle status enumeration."""
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    INACTIVE = "inactive"


class Vehicle(Base):
    """Vehicle model for fleet management."""
    
    __tablename__ = "vehicles"

    id = Column(String, primary_key=True, index=True)
    registration_number = Column(String, unique=True, nullable=False, index=True)
    gps_device_id = Column(String, unique=True)
    capacity_kg = Column(Float, nullable=False)
    capacity_cubic_meters = Column(Float)
    status = Column(Enum(VehicleStatus), default=VehicleStatus.AVAILABLE, nullable=False)
    vehicle_type = Column(String)  # "van", "truck", "bike", etc.
    manufacture_year = Column(String)
    last_maintenance = Column(DateTime)
    rating = Column(Float, default=5.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    drivers = relationship("Driver", back_populates="vehicle")
    trips = relationship("Trip", back_populates="vehicle")

    def __repr__(self):
        return f"<Vehicle {self.registration_number}>"
