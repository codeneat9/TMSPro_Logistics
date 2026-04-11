"""Trip model."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Float, DateTime, Boolean, ForeignKey, Enum, JSON, Integer
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


class TripStatus(str, enum.Enum):
    """Trip status enumeration."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Trip(Base):
    """Trip model for shipments/deliveries."""
    
    __tablename__ = "trips"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    driver_id = Column(String, ForeignKey("drivers.id"))
    vehicle_id = Column(String, ForeignKey("vehicles.id"))
    status = Column(Enum(TripStatus), default=TripStatus.PENDING, nullable=False, index=True)
    
    # Locations
    pickup_lat = Column(Float, nullable=False)
    pickup_lng = Column(Float, nullable=False)
    dropoff_lat = Column(Float, nullable=False)
    dropoff_lng = Column(Float, nullable=False)
    
    # Cargo details
    cargo_description = Column(String)
    cargo_weight_kg = Column(Float)
    cargo_volume = Column(Float)
    special_handling = Column(String)  # "fragile", "hazardous", etc.
    
    # Timestamps
    scheduled_time = Column(DateTime)
    started_at = Column(DateTime)
    estimated_arrival = Column(DateTime)
    actual_arrival = Column(DateTime)
    
    # Metrics
    estimated_delay_minutes = Column(Integer)
    actual_delay_minutes = Column(Integer)
    trip_cost = Column(Float)
    
    # Route reference
    selected_route_polyline = Column(String)  # GeoJSON or encoded polyline
    
    # Additional
    notes = Column(String)
    proof_of_delivery = Column(String)  # URL/path to POD image/signature
    is_urgent = Column(Boolean, default=False)
    requires_signature = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="trips", foreign_keys=[user_id])
    driver = relationship("Driver", back_populates="trips", foreign_keys=[driver_id])
    vehicle = relationship("Vehicle", back_populates="trips")
    routes = relationship("Route", back_populates="trip")
    locations = relationship("Location", back_populates="trip", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="trip", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="trip", uselist=False)
    analytics = relationship("Analytics", back_populates="trip", uselist=False)
    compliance_logs = relationship("ComplianceLog", back_populates="trip")
    trip_logs = relationship("TripLog", back_populates="trip", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Trip {self.id}>"
