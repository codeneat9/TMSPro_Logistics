"""
Drivers Service
Handles driver profiles, status management, and location tracking
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.models.driver import Driver
from backend.models.user import User


class DriversService:
    """Service for driver operations"""
    
    @staticmethod
    def create_driver_profile(
        db: Session,
        user_id: str,
        license_number: str,
        vehicle_id: Optional[str] = None
    ) -> Driver:
        """Create a driver profile"""
        driver = Driver(
            user_id=user_id,
            license_number=license_number,
            vehicle_id=vehicle_id,
            status="offline",
            rating=5.0,
            total_trips=0,
            total_earnings=0.0
        )
        db.add(driver)
        db.commit()
        db.refresh(driver)
        return driver
    
    @staticmethod
    def get_driver(db: Session, driver_id: str) -> Optional[Driver]:
        """Get a driver by ID"""
        return db.query(Driver).filter(Driver.id == driver_id).first()
    
    @staticmethod
    def get_driver_by_user(db: Session, user_id: str) -> Optional[Driver]:
        """Get a driver by user ID"""
        return db.query(Driver).filter(Driver.user_id == user_id).first()
    
    @staticmethod
    def list_drivers(
        db: Session,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Driver], int]:
        """List drivers with optional filtering"""
        query = db.query(Driver)
        
        if status:
            query = query.filter(Driver.status == status)
        
        total = query.count()
        drivers = query.offset(offset).limit(limit).all()
        
        return drivers, total
    
    @staticmethod
    def update_driver_status(
        db: Session,
        driver_id: str,
        status: str
    ) -> Optional[Driver]:
        """Update driver status (online, offline, on_break, busy)"""
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        
        if not driver:
            return None
        
        valid_statuses = ["online", "offline", "on_break", "busy"]
        if status not in valid_statuses:
            return None
        
        driver.status = status
        db.commit()
        db.refresh(driver)
        return driver
    
    @staticmethod
    def update_driver_location(
        db: Session,
        driver_id: str,
        latitude: float,
        longitude: float,
        heading: Optional[float] = None,
        speed_kmh: Optional[float] = None
    ) -> Optional[Driver]:
        """Update driver current location"""
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        
        if not driver:
            return None
        
        driver.current_lat = latitude
        driver.current_lng = longitude
        driver.current_heading = heading
        driver.last_location_update = datetime.utcnow()
        
        db.commit()
        db.refresh(driver)
        return driver
    
    @staticmethod
    def assign_vehicle(
        db: Session,
        driver_id: str,
        vehicle_id: str
    ) -> Optional[Driver]:
        """Assign a vehicle to a driver"""
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        
        if not driver:
            return None
        
        driver.vehicle_id = vehicle_id
        db.commit()
        db.refresh(driver)
        return driver
    
    @staticmethod
    def update_driver_rating(
        db: Session,
        driver_id: str,
        new_rating: float
    ) -> Optional[Driver]:
        """Update driver rating (0-5 stars)"""
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        
        if not driver:
            return None
        
        # Calculate weighted average
        total_rating = (driver.rating * driver.total_trips) + new_rating
        driver.total_trips += 1
        driver.rating = round(total_rating / driver.total_trips, 1)
        
        db.commit()
        db.refresh(driver)
        return driver
    
    @staticmethod
    def add_earnings(
        db: Session,
        driver_id: str,
        amount: float
    ) -> Optional[Driver]:
        """Add earnings to driver account"""
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        
        if not driver:
            return None
        
        driver.total_earnings += amount
        db.commit()
        db.refresh(driver)
        return driver
    
    @staticmethod
    def get_nearby_drivers(
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        status: str = "online"
    ) -> List[Driver]:
        """Get drivers near a location (simplified - returns drivers with online status)"""
        # In production, use PostGIS for distance queries
        # For now, return online drivers sorted by rating
        return db.query(Driver).filter(
            Driver.status == status
        ).order_by(Driver.rating.desc()).limit(10).all()
