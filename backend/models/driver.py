"""Driver model."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


class DriverStatus(str, enum.Enum):
    """Driver status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_BREAK = "on_break"
    OFFLINE = "offline"


class Driver(Base):
    """Driver model for vehicle operators."""
    
    __tablename__ = "drivers"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    vehicle_id = Column(String, ForeignKey("vehicles.id"))
    license_number = Column(String, unique=True, nullable=False)
    license_expiry = Column(DateTime)
    status = Column(Enum(DriverStatus), default=DriverStatus.OFFLINE, nullable=False)
    rating = Column(Float, default=5.0)  # 0-5 star rating
    total_trips = Column(Integer, default=0)
    total_earnings = Column(Float, default=0.0)
    current_lat = Column(Float)
    current_lng = Column(Float)
    current_heading = Column(Float)  # 0-360 degrees
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="driver")
    vehicle = relationship("Vehicle", back_populates="drivers")
    trips = relationship("Trip", back_populates="driver", foreign_keys="Trip.driver_id")

    def __repr__(self):
        return f"<Driver {self.license_number}>"
