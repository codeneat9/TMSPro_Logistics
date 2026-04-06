"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ==================== User Schemas ====================

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = "customer"


class UserRegister(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Driver Schemas ====================

class DriverBase(BaseModel):
    user_id: str
    vehicle_id: Optional[str] = None
    license_number: str
    status: str = "offline"


class DriverCreate(DriverBase):
    pass


class DriverUpdate(BaseModel):
    vehicle_id: Optional[str] = None
    status: Optional[str] = None
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    current_heading: Optional[float] = None


class DriverResponse(DriverBase):
    id: str
    rating: float
    total_trips: int
    total_earnings: float
    current_lat: Optional[float]
    current_lng: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Vehicle Schemas ====================

class VehicleBase(BaseModel):
    registration_number: str
    capacity_kg: float
    vehicle_type: str


class VehicleCreate(VehicleBase):
    gps_device_id: Optional[str] = None


class VehicleResponse(VehicleBase):
    id: str
    status: str
    rating: float
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Location Schemas ====================

class LocationCreate(BaseModel):
    trip_id: str
    latitude: float
    longitude: float
    speed_kmh: Optional[float] = None
    heading: Optional[float] = None
    accuracy_meters: Optional[float] = None


class LocationResponse(LocationCreate):
    id: str
    recorded_at: datetime

    class Config:
        from_attributes = True


# ==================== Trip Schemas ====================

class TripBase(BaseModel):
    user_id: str
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float
    cargo_description: Optional[str] = None
    cargo_weight_kg: Optional[float] = None


class TripCreate(TripBase):
    pass


class TripUpdate(BaseModel):
    driver_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    status: Optional[str] = None
    estimated_arrival: Optional[datetime] = None
    notes: Optional[str] = None


class TripResponse(TripBase):
    id: str
    driver_id: Optional[str]
    vehicle_id: Optional[str]
    status: str
    estimated_arrival: Optional[datetime]
    estimated_delay_minutes: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class TripDetailResponse(TripResponse):
    locations: List[LocationResponse] = []
    routes: List["RouteResponse"] = []


# ==================== Route Schemas ====================

class RouteBase(BaseModel):
    trip_id: str
    distance_km: float
    duration_minutes: int
    route_type: str


class RouteCreate(RouteBase):
    polyline: str


class RouteResponse(RouteBase):
    id: str
    polyline: str
    predicted_delay_minutes: int
    predicted_cost: Optional[float]
    risk_score: Optional[float]

    class Config:
        from_attributes = True


# ==================== Notification Schemas ====================

class NotificationCreate(BaseModel):
    user_id: str
    type: str
    title: str
    message: str
    trip_id: Optional[str] = None


class NotificationResponse(NotificationCreate):
    id: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Auth Schemas ====================

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    refresh_token: str


# ==================== Analytics Schemas ====================

class AnalyticsResponse(BaseModel):
    id: str
    trip_id: str
    driver_id: str
    predicted_delay_minutes: Optional[int]
    actual_delay_minutes: Optional[int]
    trip_cost: float
    efficiency_score: Optional[float]
    on_time_percentage: Optional[float]
    total_distance_km: float

    class Config:
        from_attributes = True


# ==================== Error Schemas ====================

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int


# Update forward references
TripDetailResponse.update_forward_refs()
