"""
Trips Service
Handles trip creation, updates, tracking, and delay predictions
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.models.trip import Trip
from backend.models.location import Location
from backend.models.route import Route


class TripsService:
    """Service for trip operations"""
    
    @staticmethod
    def create_trip(
        db: Session,
        user_id: str,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
        cargo_description: Optional[str] = None,
        cargo_weight_kg: Optional[float] = None
    ) -> Trip:
        """Create a new trip"""
        trip = Trip(
            user_id=user_id,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_lat=dropoff_lat,
            dropoff_lng=dropoff_lng,
            cargo_description=cargo_description,
            cargo_weight_kg=cargo_weight_kg,
            status="pending"
        )
        db.add(trip)
        db.commit()
        db.refresh(trip)
        return trip
    
    @staticmethod
    def get_trip(db: Session, trip_id: str) -> Optional[Trip]:
        """Get a trip by ID"""
        return db.query(Trip).filter(Trip.id == trip_id).first()
    
    @staticmethod
    def list_trips(
        db: Session,
        user_id: Optional[str] = None,
        driver_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Trip], int]:
        """List trips with optional filtering"""
        query = db.query(Trip)
        
        if user_id:
            query = query.filter(Trip.user_id == user_id)
        if driver_id:
            query = query.filter(Trip.driver_id == driver_id)
        if status:
            query = query.filter(Trip.status == status)
        
        total = query.count()
        trips = query.order_by(desc(Trip.created_at)).offset(offset).limit(limit).all()
        
        return trips, total
    
    @staticmethod
    def update_trip(
        db: Session,
        trip_id: str,
        **kwargs
    ) -> Optional[Trip]:
        """Update a trip"""
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        
        if not trip:
            return None
        
        allowed_fields = {
            "driver_id", "vehicle_id", "status", "estimated_arrival",
            "notes", "estimated_delay_minutes"
        }
        
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(trip, key, value)
        
        db.commit()
        db.refresh(trip)
        return trip
    
    @staticmethod
    def assign_driver(
        db: Session,
        trip_id: str,
        driver_id: str,
        vehicle_id: str
    ) -> Optional[Trip]:
        """Assign a driver and vehicle to a trip"""
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        
        if not trip:
            return None
        
        trip.driver_id = driver_id
        trip.vehicle_id = vehicle_id
        trip.status = "assigned"
        
        db.commit()
        db.refresh(trip)
        return trip
    
    @staticmethod
    def start_trip(db: Session, trip_id: str) -> Optional[Trip]:
        """Start a trip"""
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        
        if not trip:
            return None
        
        trip.status = "in_progress"
        db.commit()
        db.refresh(trip)
        return trip
    
    @staticmethod
    def complete_trip(db: Session, trip_id: str) -> Optional[Trip]:
        """Complete a trip"""
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        
        if not trip:
            return None
        
        trip.status = "completed"
        db.commit()
        db.refresh(trip)
        return trip
    
    @staticmethod
    def get_trip_locations(db: Session, trip_id: str) -> List[Location]:
        """Get all location points for a trip"""
        return db.query(Location).filter(
            Location.trip_id == trip_id
        ).order_by(Location.recorded_at).all()
    
    @staticmethod
    def get_trip_routes(db: Session, trip_id: str) -> List[Route]:
        """Get all route alternatives for a trip"""
        return db.query(Route).filter(Route.trip_id == trip_id).all()
