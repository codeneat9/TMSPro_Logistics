import pytest
from sqlalchemy.orm import Session
from backend.services.locations import LocationsService
from backend.models.location import Location
from backend.models.trip import Trip
from backend.models.user import User
from datetime import datetime, timedelta


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="customer@example.com",
        hashed_password="hashed_password",
        first_name="John",
        last_name="Customer",
        role="customer"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_trip(db_session, test_user):
    """Create a test trip."""
    trip = Trip(
        customer_id=test_user.id,
        pickup_lat=40.7128,
        pickup_lng=-74.0060,
        dropoff_lat=34.0522,
        dropoff_lng=-118.2437,
        cargo_description="Test cargo",
        cargo_weight=100.0,
        cargo_volume=20.0
    )
    db_session.add(trip)
    db_session.commit()
    db_session.refresh(trip)
    return trip


@pytest.fixture
def locations_service(db_session):
    """Create LocationsService instance with test database."""
    return LocationsService(db_session)


class TestLocationsService:
    """Unit tests for LocationsService."""
    
    def test_record_location(self, locations_service, test_trip):
        """Test recording a GPS location."""
        location = locations_service.record_location(
            trip_id=test_trip.id,
            latitude=40.7128,
            longitude=-74.0060,
            altitude=10.5,
            speed=45.0,
            heading=90,
            accuracy=5.0
        )
        
        assert location is not None
        assert location.trip_id == test_trip.id
        assert location.latitude == 40.7128
        assert location.speed == 45.0
    
    def test_get_latest_location(self, locations_service, test_trip):
        """Test getting the latest location."""
        locations_service.record_location(
            trip_id=test_trip.id,
            latitude=40.7128,
            longitude=-74.0060,
            speed=45.0
        )
        
        locations_service.record_location(
            trip_id=test_trip.id,
            latitude=40.7200,
            longitude=-74.0100,
            speed=50.0
        )
        
        latest = locations_service.get_latest_location(test_trip.id)
        
        assert latest is not None
        assert latest.latitude == 40.7200
        assert latest.speed == 50.0
    
    def test_get_recent_locations(self, locations_service, test_trip):
        """Test getting recent locations within time window."""
        now = datetime.utcnow()
        
        # Record location 5 minutes ago
        locations_service.record_location(
            trip_id=test_trip.id,
            latitude=40.7128,
            longitude=-74.0060
        )
        
        # Record location now
        locations_service.record_location(
            trip_id=test_trip.id,
            latitude=40.7200,
            longitude=-74.0100
        )
        
        recent = locations_service.get_recent_locations(test_trip.id, minutes=10)
        
        assert len(recent) >= 2
    
    def test_get_trip_locations(self, locations_service, test_trip):
        """Test getting all locations for a trip."""
        for i in range(5):
            locations_service.record_location(
                trip_id=test_trip.id,
                latitude=40.7128 + i * 0.001,
                longitude=-74.0060 + i * 0.001,
                speed=40.0 + i * 2
            )
        
        locations = locations_service.get_trip_locations(test_trip.id)
        
        assert len(locations) == 5
    
    def test_calculate_distance_traveled(self, locations_service, test_trip):
        """Test distance calculation (simplified)."""
        locations_service.record_location(
            trip_id=test_trip.id,
            latitude=40.7128,
            longitude=-74.0060
        )
        
        locations_service.record_location(
            trip_id=test_trip.id,
            latitude=40.7129,
            longitude=-74.0061
        )
        
        distance = locations_service.calculate_distance_traveled(test_trip.id)
        
        # Distance between two nearby points
        assert distance > 0
    
    def test_calculate_average_speed(self, locations_service, test_trip):
        """Test average speed calculation."""
        locations_service.record_location(
            trip_id=test_trip.id,
            latitude=40.7128,
            longitude=-74.0060,
            speed=40.0
        )
        
        locations_service.record_location(
            trip_id=test_trip.id,
            latitude=40.7200,
            longitude=-74.0100,
            speed=50.0
        )
        
        locations_service.record_location(
            trip_id=test_trip.id,
            latitude=40.7300,
            longitude=-74.0150,
            speed=60.0
        )
        
        avg_speed = locations_service.calculate_average_speed(test_trip.id)
        
        assert avg_speed > 0
        assert 40 <= avg_speed <= 60
    
    def test_get_speeding_events(self, locations_service, test_trip):
        """Test detecting speeding violations."""
        speed_limit = 50  # km/h
        
        # Record normal speed
        locations_service.record_location(
            trip_id=test_trip.id,
            latitude=40.7128,
            longitude=-74.0060,
            speed=45.0
        )
        
        # Record speeding
        locations_service.record_location(
            trip_id=test_trip.id,
            latitude=40.7200,
            longitude=-74.0100,
            speed=65.0
        )
        
        violations = locations_service.get_speeding_events(test_trip.id, speed_limit)
        
        assert len(violations) >= 1
        assert violations[0].speed > speed_limit
