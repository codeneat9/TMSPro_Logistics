"""
Locations Service
Handles GPS tracking and real-time location updates
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.models.location import Location


class LocationsService:
    """Service for location tracking operations"""
    
    @staticmethod
    def record_location(
        db: Session,
        trip_id: str,
        latitude: float,
        longitude: float,
        speed_kmh: Optional[float] = None,
        heading: Optional[float] = None,
        accuracy_meters: Optional[float] = None,
        altitude_meters: Optional[float] = None
    ) -> Location:
        """Record a GPS location point for a trip"""
        location = Location(
            trip_id=trip_id,
            latitude=latitude,
            longitude=longitude,
            speed_kmh=speed_kmh,
            heading=heading,
            accuracy_meters=accuracy_meters,
            altitude=altitude_meters,
            recorded_at=datetime.utcnow()
        )
        db.add(location)
        db.commit()
        db.refresh(location)
        return location
    
    @staticmethod
    def get_trip_locations(
        db: Session,
        trip_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Location], int]:
        """Get location history for a trip"""
        query = db.query(Location).filter(Location.trip_id == trip_id)
        total = query.count()
        
        locations = query.order_by(Location.recorded_at).offset(offset).limit(limit).all()
        return locations, total
    
    @staticmethod
    def get_recent_locations(
        db: Session,
        trip_id: str,
        minutes: int = 5
    ) -> List[Location]:
        """Get location points from the last N minutes"""
        since = datetime.utcnow() - timedelta(minutes=minutes)
        
        return db.query(Location).filter(
            Location.trip_id == trip_id,
            Location.recorded_at >= since
        ).order_by(Location.recorded_at).all()
    
    @staticmethod
    def get_latest_location(db: Session, trip_id: str) -> Optional[Location]:
        """Get the most recent location for a trip"""
        return db.query(Location).filter(
            Location.trip_id == trip_id
        ).order_by(desc(Location.recorded_at)).first()
    
    @staticmethod
    def calculate_distance_traveled(
        db: Session,
        trip_id: str
    ) -> float:
        """Calculate total distance traveled in a trip (simplified)
        
        In production, use proper distance calculation:
        - Haversine formula for Great Circle distance
        - Or use PostGIS for accurate measurements
        """
        locations = db.query(Location).filter(
            Location.trip_id == trip_id
        ).order_by(Location.recorded_at).all()
        
        if len(locations) < 2:
            return 0.0
        
        # Simplified: count points as distance indicators
        # In production, calculate actual km using coordinates
        return float(len(locations) * 0.1)  # Placeholder: 100m per point
    
    @staticmethod
    def calculate_average_speed(
        db: Session,
        trip_id: str
    ) -> float:
        """Calculate average speed during trip"""
        locations = db.query(Location).filter(
            Location.trip_id == trip_id,
            Location.speed_kmh.isnot(None)
        ).all()
        
        if not locations:
            return 0.0
        
        total_speed = sum(loc.speed_kmh for loc in locations if loc.speed_kmh)
        return round(total_speed / len(locations), 2)
    
    @staticmethod
    def get_speeding_events(
        db: Session,
        trip_id: str,
        speed_limit_kmh: float = 60.0
    ) -> List[Location]:
        """Get location points where speed exceeded limit"""
        return db.query(Location).filter(
            Location.trip_id == trip_id,
            Location.speed_kmh > speed_limit_kmh
        ).all()
    
    @staticmethod
    def cleanup_old_locations(
        db: Session,
        days: int = 30
    ) -> int:
        """Delete location records older than N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted = db.query(Location).filter(
            Location.recorded_at < cutoff_date
        ).delete()
        
        db.commit()
        return deleted
