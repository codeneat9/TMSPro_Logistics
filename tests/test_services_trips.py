import pytest
from backend.services.trips import TripsService
from backend.models.user import User


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="testuser@example.com",
        password_hash="hashed_password",
        full_name="Test User",
        phone="+1234567890",
        role="customer"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestTripsService:
    """Unit tests for TripsService."""
    
    def test_create_trip(self, db_session, test_user):
        """Test creating a new trip."""
        trip = TripsService.create_trip(
            db=db_session,
            user_id=test_user.id,
            pickup_lat=40.7128,
            pickup_lng=-74.0060,
            dropoff_lat=34.0522,
            dropoff_lng=-118.2437,
            cargo_description="Electronics",
            cargo_weight_kg=50.0,
        )

        assert trip is not None
        assert trip.user_id == test_user.id
        assert trip.pickup_lat == 40.7128
        assert trip.status == "pending"
    
    def test_get_trip(self, db_session, test_user):
        """Test retrieving a trip."""
        created_trip = TripsService.create_trip(
            db=db_session,
            user_id=test_user.id,
            pickup_lat=40.7128,
            pickup_lng=-74.0060,
            dropoff_lat=34.0522,
            dropoff_lng=-118.2437,
            cargo_description="Electronics",
            cargo_weight_kg=50.0,
        )

        retrieved_trip = TripsService.get_trip(db_session, created_trip.id)
        
        assert retrieved_trip is not None
        assert retrieved_trip.id == created_trip.id
        assert retrieved_trip.user_id == test_user.id
    
    def test_list_trips_by_customer(self, db_session, test_user):
        """Test listing trips for a customer."""
        kwargs = dict(
            db=db_session,
            user_id=test_user.id,
            pickup_lat=40.7128,
            pickup_lng=-74.0060,
            dropoff_lat=34.0522,
            dropoff_lng=-118.2437,
            cargo_description="Electronics",
            cargo_weight_kg=50.0,
        )

        TripsService.create_trip(**kwargs)
        TripsService.create_trip(**kwargs)

        trips, total = TripsService.list_trips(db_session, user_id=test_user.id)

        assert total >= 2
        assert len(trips) >= 2
    
    def test_update_trip(self, db_session, test_user):
        """Test updating trip fields."""
        trip = TripsService.create_trip(
            db=db_session,
            user_id=test_user.id,
            pickup_lat=40.7128,
            pickup_lng=-74.0060,
            dropoff_lat=34.0522,
            dropoff_lng=-118.2437,
            cargo_description="Electronics",
            cargo_weight_kg=50.0,
        )

        updated_trip = TripsService.update_trip(
            db_session,
            trip.id,
            cargo_description="Updated description",
        )
        
        assert updated_trip.cargo_description == "Updated description"
    
    def test_trip_status_workflow(self, db_session, test_user):
        """Test trip status transitions."""
        trip = TripsService.create_trip(
            db=db_session,
            user_id=test_user.id,
            pickup_lat=40.7128,
            pickup_lng=-74.0060,
            dropoff_lat=34.0522,
            dropoff_lng=-118.2437,
            cargo_description="Electronics",
            cargo_weight_kg=50.0,
        )

        assert trip.status == "pending"

        started_trip = TripsService.start_trip(db_session, trip.id)
        assert started_trip.status == "in_progress"

        completed_trip = TripsService.complete_trip(db_session, trip.id)
        assert completed_trip.status == "completed"
