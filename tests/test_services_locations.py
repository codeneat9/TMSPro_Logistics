import pytest
from backend.services.locations import LocationsService
from backend.models.trip import Trip
from backend.models.user import User


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="customer@example.com",
        password_hash="hashed_password",
        full_name="John Customer",
        phone="+1234567890",
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
        user_id=test_user.id,
        pickup_lat=40.7128,
        pickup_lng=-74.0060,
        dropoff_lat=34.0522,
        dropoff_lng=-118.2437,
        cargo_description="Test cargo",
        cargo_weight_kg=100.0,
        cargo_volume=20.0
    )
    db_session.add(trip)
    db_session.commit()
    db_session.refresh(trip)
    return trip


class TestLocationsService:
    """Unit tests for LocationsService."""
    
    def test_record_location(self, db_session, test_trip):
        """Test recording a GPS location."""
        location = LocationsService.record_location(
            db=db_session,
            trip_id=test_trip.id,
            latitude=40.7128,
            longitude=-74.0060,
            altitude_meters=10.5,
            speed_kmh=45.0,
            heading=90,
            accuracy_meters=5.0,
        )
        
        assert location is not None
        assert location.trip_id == test_trip.id
        assert location.latitude == 40.7128
        assert location.speed_kmh == 45.0
    
    def test_get_latest_location(self, db_session, test_trip):
        """Test getting the latest location."""
        LocationsService.record_location(
            db=db_session,
            trip_id=test_trip.id,
            latitude=40.7128,
            longitude=-74.0060,
            speed_kmh=45.0,
        )
        
        LocationsService.record_location(
            db=db_session,
            trip_id=test_trip.id,
            latitude=40.7200,
            longitude=-74.0100,
            speed_kmh=50.0,
        )
        
        latest = LocationsService.get_latest_location(db_session, test_trip.id)
        
        assert latest is not None
        assert latest.latitude == 40.7200
        assert latest.speed_kmh == 50.0
    
    def test_get_recent_locations(self, db_session, test_trip):
        """Test getting recent locations within time window."""

        LocationsService.record_location(
            db=db_session,
            trip_id=test_trip.id,
            latitude=40.7128,
            longitude=-74.0060,
        )

        LocationsService.record_location(
            db=db_session,
            trip_id=test_trip.id,
            latitude=40.7200,
            longitude=-74.0100,
        )
        
        recent = LocationsService.get_recent_locations(db_session, test_trip.id, minutes=10)
        
        assert len(recent) >= 2
    
    def test_get_trip_locations(self, db_session, test_trip):
        """Test getting all locations for a trip."""
        for i in range(5):
            LocationsService.record_location(
                db=db_session,
                trip_id=test_trip.id,
                latitude=40.7128 + i * 0.001,
                longitude=-74.0060 + i * 0.001,
                speed_kmh=40.0 + i * 2,
            )

        locations, total = LocationsService.get_trip_locations(db_session, test_trip.id)

        assert total == 5
        assert len(locations) == 5
    
    def test_calculate_distance_traveled(self, db_session, test_trip):
        """Test distance calculation (simplified)."""
        LocationsService.record_location(
            db=db_session,
            trip_id=test_trip.id,
            latitude=40.7128,
            longitude=-74.0060,
        )
        
        LocationsService.record_location(
            db=db_session,
            trip_id=test_trip.id,
            latitude=40.7129,
            longitude=-74.0061,
        )
        
        distance = LocationsService.calculate_distance_traveled(db_session, test_trip.id)

        assert distance > 0
    
    def test_calculate_average_speed(self, db_session, test_trip):
        """Test average speed calculation."""
        LocationsService.record_location(
            db=db_session,
            trip_id=test_trip.id,
            latitude=40.7128,
            longitude=-74.0060,
            speed_kmh=40.0,
        )
        
        LocationsService.record_location(
            db=db_session,
            trip_id=test_trip.id,
            latitude=40.7200,
            longitude=-74.0100,
            speed_kmh=50.0,
        )
        
        LocationsService.record_location(
            db=db_session,
            trip_id=test_trip.id,
            latitude=40.7300,
            longitude=-74.0150,
            speed_kmh=60.0,
        )
        
        avg_speed = LocationsService.calculate_average_speed(db_session, test_trip.id)
        
        assert avg_speed > 0
        assert 40 <= avg_speed <= 60
    
    def test_get_speeding_events(self, db_session, test_trip):
        """Test detecting speeding violations."""
        speed_limit = 50  # km/h

        LocationsService.record_location(
            db=db_session,
            trip_id=test_trip.id,
            latitude=40.7128,
            longitude=-74.0060,
            speed_kmh=45.0,
        )

        LocationsService.record_location(
            db=db_session,
            trip_id=test_trip.id,
            latitude=40.7200,
            longitude=-74.0100,
            speed_kmh=65.0,
        )
        
        violations = LocationsService.get_speeding_events(
            db=db_session,
            trip_id=test_trip.id,
            speed_limit_kmh=speed_limit,
        )
        
        assert len(violations) >= 1
        assert violations[0].speed_kmh > speed_limit
