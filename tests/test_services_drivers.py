import uuid
import pytest
from backend.services.drivers import DriversService
from backend.models.vehicle import Vehicle
from backend.models.user import User


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="driver@example.com",
        password_hash="hashed_password",
        full_name="John Driver",
        phone="+1234567890",
        role="driver"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_vehicle(db_session):
    """Create a test vehicle."""
    vehicle = Vehicle(
        id=str(uuid.uuid4()),
        registration_number="ABC123",
        vehicle_type="truck",
        capacity_kg=20000,
        capacity_cubic_meters=50,
        manufacture_year="2022"
    )
    db_session.add(vehicle)
    db_session.commit()
    db_session.refresh(vehicle)
    return vehicle


class TestDriversService:
    """Unit tests for DriversService."""
    
    def test_create_driver_profile(self, db_session, test_user):
        """Test creating a driver profile."""
        driver = DriversService.create_driver_profile(
            db=db_session,
            user_id=test_user.id,
            license_number="DL123456",
        )

        assert driver is not None
        assert driver.user_id == test_user.id
        assert driver.license_number == "DL123456"
        assert driver.status == "offline"
    
    def test_get_driver(self, db_session, test_user):
        """Test retrieving a driver."""
        created_driver = DriversService.create_driver_profile(
            db=db_session,
            user_id=test_user.id,
            license_number="DL123456",
        )
        retrieved_driver = DriversService.get_driver(db_session, created_driver.id)
        
        assert retrieved_driver is not None
        assert retrieved_driver.id == created_driver.id
        assert retrieved_driver.license_number == "DL123456"
    
    def test_update_driver_status(self, db_session, test_user):
        """Test updating driver status."""
        driver = DriversService.create_driver_profile(
            db=db_session,
            user_id=test_user.id,
            license_number="DL123456",
        )

        assert driver.status == "offline"

        updated_driver = DriversService.update_driver_status(db_session, driver.id, "online")
        assert updated_driver.status == "active"

        updated_driver = DriversService.update_driver_status(db_session, driver.id, "break")
        assert updated_driver.status == "on_break"
    
    def test_update_driver_location(self, db_session, test_user):
        """Test updating driver location."""
        driver = DriversService.create_driver_profile(
            db=db_session,
            user_id=test_user.id,
            license_number="DL123456",
        )

        updated_driver = DriversService.update_driver_location(
            db=db_session,
            driver_id=driver.id,
            latitude=40.7128,
            longitude=-74.0060,
        )
        
        assert updated_driver.current_lat == 40.7128
        assert updated_driver.current_lng == -74.0060
    
    def test_assign_vehicle(self, db_session, test_user, test_vehicle):
        """Test assigning vehicle to driver."""
        driver = DriversService.create_driver_profile(
            db=db_session,
            user_id=test_user.id,
            license_number="DL123456",
        )

        updated_driver = DriversService.assign_vehicle(db_session, driver.id, test_vehicle.id)
        
        assert updated_driver.vehicle_id == test_vehicle.id
    
    def test_update_driver_rating(self, db_session, test_user):
        """Test updating driver rating."""
        driver = DriversService.create_driver_profile(
            db=db_session,
            user_id=test_user.id,
            license_number="DL123456",
        )

        assert driver.rating == 5.0

        updated_driver = DriversService.update_driver_rating(db_session, driver.id, 4)
        assert updated_driver.rating == 4.0

        updated_driver = DriversService.update_driver_rating(db_session, driver.id, 5)
        assert updated_driver.rating == 4.5
    
    def test_add_earnings(self, db_session, test_user):
        """Test adding earnings to driver."""
        driver = DriversService.create_driver_profile(
            db=db_session,
            user_id=test_user.id,
            license_number="DL123456",
        )

        initial_earnings = driver.total_earnings or 0.0

        updated_driver = DriversService.add_earnings(db_session, driver.id, 100.0)
        
        assert updated_driver.total_earnings == initial_earnings + 100.0
    
    def test_list_drivers(self, db_session):
        """Test listing all drivers."""
        user1 = User(
            email="driver1@example.com",
            password_hash="hashed_password",
            full_name="Driver One",
            phone="+1234567891",
            role="driver",
        )
        user2 = User(
            email="driver2@example.com",
            password_hash="hashed_password",
            full_name="Driver Two",
            phone="+1234567892",
            role="driver",
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        DriversService.create_driver_profile(
            db=db_session,
            user_id=user1.id,
            license_number="DL123456",
        )
        DriversService.create_driver_profile(
            db=db_session,
            user_id=user2.id,
            license_number="DL654321",
        )

        drivers, total = DriversService.list_drivers(db_session)

        assert total >= 2
        assert len(drivers) >= 2
