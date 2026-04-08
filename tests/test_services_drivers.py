import pytest
from sqlalchemy.orm import Session
from backend.services.drivers import DriversService
from backend.models.driver import Driver
from backend.models.vehicle import Vehicle
from backend.models.user import User
from backend.schemas import DriverCreate


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="driver@example.com",
        hashed_password="hashed_password",
        first_name="John",
        last_name="Driver",
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
        registration_number="ABC123",
        vehicle_type="truck",
        model="Volvo FH16",
        year=2022,
        capacity_kg=20000,
        capacity_cubic_meters=50,
        color="White"
    )
    db_session.add(vehicle)
    db_session.commit()
    db_session.refresh(vehicle)
    return vehicle


@pytest.fixture
def drivers_service(db_session):
    """Create DriversService instance with test database."""
    return DriversService(db_session)


class TestDriversService:
    """Unit tests for DriversService."""
    
    def test_create_driver_profile(self, drivers_service, test_user):
        """Test creating a driver profile."""
        driver_data = CreateDriverRequest(
            user_id=test_user.id,
            license_number="DL123456",
            license_expiry="2025-12-31",
            phone_number="+1234567890",
            address="123 Main Street"
        )
        
        driver = drivers_service.create_driver_profile(driver_data)
        
        assert driver is not None
        assert driver.user_id == test_user.id
        assert driver.license_number == "DL123456"
        assert driver.status == "offline"
    
    def test_get_driver(self, drivers_service, test_user):
        """Test retrieving a driver."""
        driver_data = CreateDriverRequest(
            user_id=test_user.id,
            license_number="DL123456",
            license_expiry="2025-12-31",
            phone_number="+1234567890",
            address="123 Main Street"
        )
        
        created_driver = drivers_service.create_driver_profile(driver_data)
        retrieved_driver = drivers_service.get_driver(created_driver.id)
        
        assert retrieved_driver is not None
        assert retrieved_driver.id == created_driver.id
        assert retrieved_driver.license_number == "DL123456"
    
    def test_update_driver_status(self, drivers_service, test_user):
        """Test updating driver status."""
        driver_data = CreateDriverRequest(
            user_id=test_user.id,
            license_number="DL123456",
            license_expiry="2025-12-31",
            phone_number="+1234567890",
            address="123 Main Street"
        )
        
        driver = drivers_service.create_driver_profile(driver_data)
        assert driver.status == "offline"
        
        updated_driver = drivers_service.update_driver_status(driver.id, "online")
        assert updated_driver.status == "online"
        
        updated_driver = drivers_service.update_driver_status(driver.id, "break")
        assert updated_driver.status == "break"
    
    def test_update_driver_location(self, drivers_service, test_user):
        """Test updating driver location."""
        driver_data = CreateDriverRequest(
            user_id=test_user.id,
            license_number="DL123456",
            license_expiry="2025-12-31",
            phone_number="+1234567890",
            address="123 Main Street"
        )
        
        driver = drivers_service.create_driver_profile(driver_data)
        updated_driver = drivers_service.update_driver_location(
            driver.id, 
            lat=40.7128, 
            lng=-74.0060
        )
        
        assert updated_driver.current_lat == 40.7128
        assert updated_driver.current_lng == -74.0060
    
    def test_assign_vehicle(self, drivers_service, test_user, test_vehicle):
        """Test assigning vehicle to driver."""
        driver_data = CreateDriverRequest(
            user_id=test_user.id,
            license_number="DL123456",
            license_expiry="2025-12-31",
            phone_number="+1234567890",
            address="123 Main Street"
        )
        
        driver = drivers_service.create_driver_profile(driver_data)
        updated_driver = drivers_service.assign_vehicle(driver.id, test_vehicle.id)
        
        assert updated_driver.vehicle_id == test_vehicle.id
    
    def test_update_driver_rating(self, drivers_service, test_user):
        """Test updating driver rating."""
        driver_data = CreateDriverRequest(
            user_id=test_user.id,
            license_number="DL123456",
            license_expiry="2025-12-31",
            phone_number="+1234567890",
            address="123 Main Street"
        )
        
        driver = drivers_service.create_driver_profile(driver_data)
        assert driver.rating == 5.0
        
        # Add a 4-star rating
        updated_driver = drivers_service.update_driver_rating(driver.id, 4)
        assert updated_driver.rating == 4.5  # (5+4)/2
        
        # Add a 5-star rating
        updated_driver = drivers_service.update_driver_rating(driver.id, 5)
        assert updated_driver.rating == 4.666666  # (5+4+5)/3 ~= 4.667
    
    def test_add_earnings(self, drivers_service, test_user):
        """Test adding earnings to driver."""
        driver_data = CreateDriverRequest(
            user_id=test_user.id,
            license_number="DL123456",
            license_expiry="2025-12-31",
            phone_number="+1234567890",
            address="123 Main Street"
        )
        
        driver = drivers_service.create_driver_profile(driver_data)
        initial_earnings = driver.total_earnings or 0.0
        
        updated_driver = drivers_service.add_earnings(driver.id, 100.0)
        
        assert updated_driver.total_earnings == initial_earnings + 100.0
    
    def test_list_drivers(self, drivers_service, test_user):
        """Test listing all drivers."""
        driver_data = CreateDriverRequest(
            user_id=test_user.id,
            license_number="DL123456",
            license_expiry="2025-12-31",
            phone_number="+1234567890",
            address="123 Main Street"
        )
        
        drivers_service.create_driver_profile(driver_data)
        drivers_service.create_driver_profile(driver_data)
        
        drivers = drivers_service.list_drivers()
        
        assert len(drivers) >= 2
