"""Geofence model."""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Enum
import enum

from backend.database import Base


class GeofenceType(str, enum.Enum):
    """Geofence type enumeration."""
    RESTRICTED_ZONE = "restricted"
    DELIVERY_ZONE = "delivery_zone"
    DANGEROUS_AREA = "dangerous_area"
    REST_AREA = "rest_area"
    REFUEL_STATION = "refuel_station"


class GeofenceAction(str, enum.Enum):
    """Action to take when entering/exiting geofence."""
    ALERT = "alert"
    NOTIFY = "notify"
    RESTRICT = "restrict"
    LOG = "log"


class Geofence(Base):
    """Geofence model for zone-based alerts."""
    
    __tablename__ = "geofences"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True, nullable=False)  # Company that owns this geofence
    
    name = Column(String, nullable=False)
    description = Column(String)
    
    # Location
    center_latitude = Column(Float, nullable=False)
    center_longitude = Column(Float, nullable=False)
    radius_meters = Column(Float, nullable=False)
    
    # Type and action
    fence_type = Column(Enum(GeofenceType), default=GeofenceType.DELIVERY_ZONE, nullable=False)
    action_on_enter = Column(Enum(GeofenceAction), default=GeofenceAction.ALERT)
    action_on_exit = Column(Enum(GeofenceAction), default=GeofenceAction.ALERT)
    
    # Configuration
    is_active = Column(String, default=True)
    alerting_enabled = Column(String, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Geofence {self.name}>"
