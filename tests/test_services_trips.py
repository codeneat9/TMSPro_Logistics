import pytest
from sqlalchemy.orm import Session
from backend.services.trips import TripsService
from backend.models.trip import Trip
from backend.models.user import User
from backend.schemas import TripCreate
from datetime import datetime


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="testuser@example.com",
        hashed_password="hashed_password",
        first_name="Test",
        last_name="User",
        role="customer"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def trips_service(db_session):
    """Create TripsService instance with test database."""
    return TripsService(db_session)


class TestTripsService:
    """Unit tests for TripsService."""
    
    def test_create_trip(self, trips_service, test_user):
        """Test creating a new trip."""
        trip_data = CreateTripRequest(
            customer_id=test_user.id,
            pickup_lat=40.7128,
            pickup_lng=-74.0060,
            dropoff_lat=34.0522,
            dropoff_lng=-118.2437,
            cargo_description="Electronics",
            cargo_weight=50.0,
            cargo_volume=10.0,
            special_handling="Fragile"
        )
        
        trip = trips_service.create_trip(trip_data)
        
        assert trip is not None
        assert trip.customer_id == test_user.id
        assert trip.pickup_lat == 40.7128
        assert trip.status == "pending"
    
    def test_get_trip(self, trips_service, test_user):
        """Test retrieving a trip."""
        trip_data = CreateTripRequest(
            customer_id=test_user.id,
            pickup_lat=40.7128,
            pickup_lng=-74.0060,
            dropoff_lat=34.0522,
            dropoff_lng=-118.2437,
            cargo_description="Electronics",
            cargo_weight=50.0,
            cargo_volume=10.0
        )
        
        created_trip = trips_service.create_trip(trip_data)
        retrieved_trip = trips_service.get_trip(created_trip.id)
        
        assert retrieved_trip is not None
        assert retrieved_trip.id == created_trip.id
        assert retrieved_trip.customer_id == test_user.id
    
    def test_list_trips_by_customer(self, trips_service, test_user):
        """Test listing trips for a customer."""
        trip_data = CreateTripRequest(
            customer_id=test_user.id,
            pickup_lat=40.7128,
            pickup_lng=-74.0060,
            dropoff_lat=34.0522,
            dropoff_lng=-118.2437,
            cargo_description="Electronics",
            cargo_weight=50.0,
            cargo_volume=10.0
        )
        
        trips_service.create_trip(trip_data)
        trips_service.create_trip(trip_data)
        
        trips = trips_service.list_trips(customer_id=test_user.id)
        
        assert len(trips) >= 2
    
    def test_update_trip(self, trips_service, test_user):
        """Test updating trip fields."""
        trip_data = CreateTripRequest(
            customer_id=test_user.id,
            pickup_lat=40.7128,
            pickup_lng=-74.0060,
            dropoff_lat=34.0522,
            dropoff_lng=-118.2437,
            cargo_description="Electronics",
            cargo_weight=50.0,
            cargo_volume=10.0
        )
        
        trip = trips_service.create_trip(trip_data)
        updated_trip = trips_service.update_trip(trip.id, {"cargo_description": "Updated description"})
        
        assert updated_trip.cargo_description == "Updated description"
    
    def test_trip_status_workflow(self, trips_service, test_user):
        """Test trip status transitions."""
        trip_data = CreateTripRequest(
            customer_id=test_user.id,
            pickup_lat=40.7128,
            pickup_lng=-74.0060,
            dropoff_lat=34.0522,
            dropoff_lng=-118.2437,
            cargo_description="Electronics",
            cargo_weight=50.0,
            cargo_volume=10.0
        )
        
        trip = trips_service.create_trip(trip_data)
        assert trip.status == "pending"
        
        started_trip = trips_service.start_trip(trip.id)
        assert started_trip.status == "in_progress"
        
        completed_trip = trips_service.complete_trip(trip.id)
        assert completed_trip.status == "completed"
