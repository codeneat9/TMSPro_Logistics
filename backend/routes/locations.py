"""
Locations Routes
Provides endpoints for GPS tracking
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import LocationCreate, LocationResponse
from backend.services.locations import LocationsService
from backend.middleware.auth import get_current_user
from backend.models.user import User

router = APIRouter(
    prefix="/api/locations",
    tags=["locations"],
)


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def record_location(
    location_request: LocationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record a GPS location point for a trip
    
    - **trip_id**: Trip ID
    - **latitude**: GPS latitude
    - **longitude**: GPS longitude
    - **speed_kmh**: Optional current speed
    - **heading**: Optional direction heading
    - **accuracy_meters**: Optional GPS accuracy
    """
    location = LocationsService.record_location(
        db=db,
        trip_id=location_request.trip_id,
        latitude=location_request.latitude,
        longitude=location_request.longitude,
        speed_kmh=location_request.speed_kmh,
        heading=location_request.heading,
        accuracy_meters=location_request.accuracy_meters
    )
    
    return location


@router.get("/{trip_id}", response_model=dict)
async def get_trip_locations(
    trip_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get location history for a trip"""
    locations, total = LocationsService.get_trip_locations(
        db=db,
        trip_id=trip_id,
        limit=limit,
        offset=offset
    )
    
    return {
        "items": locations,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{trip_id}/recent", response_model=dict)
async def get_recent_locations(
    trip_id: str,
    minutes: int = Query(5, ge=1, le=60),
    db: Session = Depends(get_db)
):
    """Get location points from the last N minutes"""
    locations = LocationsService.get_recent_locations(
        db=db,
        trip_id=trip_id,
        minutes=minutes
    )
    
    return {
        "items": locations,
        "total": len(locations)
    }


@router.get("/{trip_id}/latest", response_model=LocationResponse)
async def get_latest_location(
    trip_id: str,
    db: Session = Depends(get_db)
):
    """Get the most recent location for a trip"""
    location = LocationsService.get_latest_location(db, trip_id)
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No locations recorded for this trip"
        )
    
    return location


@router.get("/{trip_id}/stats", response_model=dict)
async def get_location_statistics(
    trip_id: str,
    db: Session = Depends(get_db)
):
    """Get statistics based on location data"""
    distance = LocationsService.calculate_distance_traveled(db, trip_id)
    avg_speed = LocationsService.calculate_average_speed(db, trip_id)
    speeding_events = LocationsService.get_speeding_events(db, trip_id, speed_limit_kmh=60.0)
    
    return {
        "distance_km": distance,
        "average_speed_kmh": avg_speed,
        "speeding_events_count": len(speeding_events),
        "speed_limit_kmh": 60.0
    }


@router.get("/{trip_id}/speed-violations", response_model=dict)
async def get_speeding_events(
    trip_id: str,
    speed_limit_kmh: float = Query(60.0),
    db: Session = Depends(get_db)
):
    """Get locations where speed exceeded limit"""
    violations = LocationsService.get_speeding_events(
        db=db,
        trip_id=trip_id,
        speed_limit_kmh=speed_limit_kmh
    )
    
    return {
        "items": violations,
        "total": len(violations),
        "limit_kmh": speed_limit_kmh
    }
