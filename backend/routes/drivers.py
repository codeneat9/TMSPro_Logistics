"""
Drivers Routes
Provides endpoints for driver management
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import DriverCreate, DriverUpdate, DriverResponse
from backend.services.drivers import DriversService
from backend.middleware.auth import get_current_user
from backend.models.user import User

router = APIRouter(
    prefix="/api/drivers",
    tags=["drivers"],
)


@router.post("", response_model=DriverResponse, status_code=status.HTTP_201_CREATED)
async def create_driver_profile(
    driver_request: DriverCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a driver profile
    
    - **license_number**: Driver license number
    - **vehicle_id**: Optional vehicle ID to assign
    """
    # Check if user already has a driver profile
    existing = DriversService.get_driver_by_user(db, current_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a driver profile"
        )
    
    driver = DriversService.create_driver_profile(
        db=db,
        user_id=current_user.id,
        license_number=driver_request.license_number,
        vehicle_id=driver_request.vehicle_id
    )
    
    return driver


@router.get("/profile", response_model=DriverResponse)
async def get_my_driver_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's driver profile"""
    driver = DriversService.get_driver_by_user(db, current_user.id)
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    return driver


@router.get("/{driver_id}", response_model=DriverResponse)
async def get_driver(
    driver_id: str,
    db: Session = Depends(get_db)
):
    """Get driver information"""
    driver = DriversService.get_driver(db, driver_id)
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    return driver


@router.get("", response_model=dict)
async def list_drivers(
    status: str = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List drivers (public endpoint)"""
    drivers, total = DriversService.list_drivers(
        db=db,
        status=status,
        limit=limit,
        offset=offset
    )
    
    return {
        "items": drivers,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.patch("/{driver_id}/status", response_model=DriverResponse)
async def update_driver_status(
    driver_id: str,
    new_status: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update driver status
    
    Valid statuses: online, offline, on_break, busy
    """
    driver = DriversService.get_driver(db, driver_id)
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    # Only the driver or admin can update status
    if driver.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    updated_driver = DriversService.update_driver_status(db, driver_id, new_status)
    
    if not updated_driver:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status"
        )
    
    return updated_driver


@router.post("/{driver_id}/location", response_model=DriverResponse)
async def update_driver_location(
    driver_id: str,
    latitude: float = Query(...),
    longitude: float = Query(...),
    heading: float = Query(None),
    speed_kmh: float = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update driver current location"""
    driver = DriversService.get_driver(db, driver_id)
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    # Only the driver or admin can update location
    if driver.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    updated_driver = DriversService.update_driver_location(
        db=db,
        driver_id=driver_id,
        latitude=latitude,
        longitude=longitude,
        heading=heading,
        speed_kmh=speed_kmh
    )
    
    return updated_driver


@router.post("/{driver_id}/assign-vehicle", response_model=DriverResponse)
async def assign_vehicle(
    driver_id: str,
    vehicle_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign a vehicle to a driver"""
    driver = DriversService.get_driver(db, driver_id)
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    # Only admin or company can assign vehicles
    if current_user.role not in ["admin", "company"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    updated_driver = DriversService.assign_vehicle(db, driver_id, vehicle_id)
    
    return updated_driver


@router.get("/nearby", response_model=dict)
async def get_nearby_drivers(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius_km: float = Query(5.0),
    db: Session = Depends(get_db)
):
    """Get drivers near a location"""
    drivers = DriversService.get_nearby_drivers(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        status="online"
    )
    
    return {
        "items": drivers,
        "total": len(drivers)
    }
