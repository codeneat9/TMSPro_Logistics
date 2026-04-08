"""
Trips Routes
Provides endpoints for trip management
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import TripCreate, TripUpdate, TripResponse, TripDetailResponse
from backend.services.trips import TripsService
from backend.middleware.auth import get_current_user
from backend.models.user import User

router = APIRouter(
    prefix="/api/trips",
    tags=["trips"],
)


@router.post("", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_request: TripCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new trip
    
    - **pickup_lat**: Pickup latitude
    - **pickup_lng**: Pickup longitude
    - **dropoff_lat**: Dropoff latitude
    - **dropoff_lng**: Dropoff longitude
    - **cargo_description**: Optional cargo description
    - **cargo_weight_kg**: Optional cargo weight
    """
    trip = TripsService.create_trip(
        db=db,
        user_id=current_user.id,
        pickup_lat=trip_request.pickup_lat,
        pickup_lng=trip_request.pickup_lng,
        dropoff_lat=trip_request.dropoff_lat,
        dropoff_lng=trip_request.dropoff_lng,
        cargo_description=trip_request.cargo_description,
        cargo_weight_kg=trip_request.cargo_weight_kg
    )
    
    return trip


@router.get("/{trip_id}", response_model=TripDetailResponse)
async def get_trip(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get trip details including locations and routes"""
    trip = TripsService.get_trip(db, trip_id)
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    # Check authorization
    if trip.user_id != current_user.id and current_user.role not in ["admin", "company"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get locations and routes
    locations = TripsService.get_trip_locations(db, trip_id)
    routes = TripsService.get_trip_routes(db, trip_id)
    
    return {
        **trip.__dict__,
        "locations": locations,
        "routes": routes
    }


@router.get("", response_model=dict)
async def list_trips(
    status: str = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List trips for current user"""
    trips, total = TripsService.list_trips(
        db=db,
        user_id=current_user.id,
        status=status,
        limit=limit,
        offset=offset
    )
    
    return {
        "items": trips,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.patch("/{trip_id}", response_model=TripResponse)
async def update_trip(
    trip_id: str,
    update_request: TripUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update trip status or details"""
    trip = TripsService.get_trip(db, trip_id)
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    # Authorization check
    if trip.user_id != current_user.id and current_user.role not in ["admin", "company"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Update trip
    update_data = update_request.dict(exclude_unset=True)
    updated_trip = TripsService.update_trip(db, trip_id, **update_data)
    
    return updated_trip


@router.post("/{trip_id}/assign-driver", response_model=TripResponse)
async def assign_driver(
    trip_id: str,
    driver_id: str = Query(...),
    vehicle_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign a driver and vehicle to a trip"""
    trip = TripsService.get_trip(db, trip_id)
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    # Only dispatchers/admins can assign drivers
    if current_user.role not in ["admin", "company"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only dispatchers can assign drivers"
        )
    
    updated_trip = TripsService.assign_driver(db, trip_id, driver_id, vehicle_id)
    
    return updated_trip


@router.post("/{trip_id}/start", response_model=TripResponse)
async def start_trip(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a trip"""
    trip = TripsService.get_trip(db, trip_id)
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    # Check if user is the assigned driver
    if trip.driver_id and trip.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only assigned driver can start trip"
        )
    
    started_trip = TripsService.start_trip(db, trip_id)
    
    return started_trip


@router.post("/{trip_id}/complete", response_model=TripResponse)
async def complete_trip(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Complete a trip"""
    trip = TripsService.get_trip(db, trip_id)
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    completed_trip = TripsService.complete_trip(db, trip_id)
    
    return completed_trip
