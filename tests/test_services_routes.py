import pytest
from sqlalchemy.orm import Session
from backend.services.routes import RoutesService
from backend.models.route import Route
from backend.models.trip import Trip
from backend.models.user import User
from backend.schemas import RouteCreate


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
def routes_service(db_session):
    """Create RoutesService instance with test database."""
    return RoutesService(db_session)


class TestRoutesService:
    """Unit tests for RoutesService."""
    
    def test_create_route(self, routes_service, test_trip):
        """Test creating a route."""
        route_data = CreateRouteRequest(
            trip_id=test_trip.id,
            route_type="fastest",
            origin_lat=40.7128,
            origin_lng=-74.0060,
            destination_lat=34.0522,
            destination_lng=-118.2437,
            distance=3980,
            duration=45000,
            polyline="encoded_polyline_data",
            toll_cost=25.50,
            fuel_cost=120.00
        )
        
        route = routes_service.create_route(route_data)
        
        assert route is not None
        assert route.trip_id == test_trip.id
        assert route.distance == 3980
        assert route.toll_cost == 25.50
    
    def test_get_route(self, routes_service, test_trip):
        """Test retrieving a route."""
        route_data = CreateRouteRequest(
            trip_id=test_trip.id,
            route_type="fastest",
            origin_lat=40.7128,
            origin_lng=-74.0060,
            destination_lat=34.0522,
            destination_lng=-118.2437,
            distance=3980,
            duration=45000,
            polyline="encoded_polyline_data",
            toll_cost=25.50,
            fuel_cost=120.00
        )
        
        created_route = routes_service.create_route(route_data)
        retrieved_route = routes_service.get_route(created_route.id)
        
        assert retrieved_route is not None
        assert retrieved_route.id == created_route.id
        assert retrieved_route.distance == 3980
    
    def test_get_trip_routes(self, routes_service, test_trip):
        """Test getting all routes for a trip."""
        for i in range(3):
            route_data = CreateRouteRequest(
                trip_id=test_trip.id,
                route_type="fastest" if i == 0 else "economical",
                origin_lat=40.7128,
                origin_lng=-74.0060,
                destination_lat=34.0522,
                destination_lng=-118.2437,
                distance=3980 + i * 100,
                duration=45000 + i * 1000,
                polyline="encoded_polyline_data",
                toll_cost=25.50,
                fuel_cost=120.00
            )
            routes_service.create_route(route_data)
        
        routes = routes_service.get_trip_routes(test_trip.id)
        
        assert len(routes) == 3
    
    def test_predict_delay(self, routes_service):
        """Test delay prediction."""
        delay = routes_service.predict_delay(
            distance_km=3980,
            hour=14,
            day_of_week=3,
            weather_condition="clear",
            traffic_level="medium"
        )
        
        assert delay > 0
        assert isinstance(delay, (int, float))
    
    def test_calculate_risk_score(self, routes_service):
        """Test risk score calculation."""
        risk = routes_service.calculate_risk_score(
            distance=3980,
            average_speed=100,
            weather="rainy",
            traffic_level="heavy",
            time_of_day=22
        )
        
        assert 0 <= risk <= 100
        assert isinstance(risk, (int, float))
    
    def test_estimate_cost(self, routes_service, test_trip):
        """Test cost estimation."""
        cost = routes_service.estimate_cost(
            base_rate=10.0,
            distance_km=100,
            duration_minutes=60,
            vehicle_type="truck",
            surge_multiplier=1.5
        )
        
        assert cost > 0
        assert isinstance(cost, (int, float))
    
    def test_select_route(self, routes_service, test_trip):
        """Test selecting a route for a trip."""
        route_data = CreateRouteRequest(
            trip_id=test_trip.id,
            route_type="fastest",
            origin_lat=40.7128,
            origin_lng=-74.0060,
            destination_lat=34.0522,
            destination_lng=-118.2437,
            distance=3980,
            duration=45000,
            polyline="encoded_polyline_data",
            toll_cost=25.50,
            fuel_cost=120.00
        )
        
        route = routes_service.create_route(route_data)
        updated_trip = routes_service.select_route(test_trip.id, route.id)
        
        assert updated_trip.selected_route_id == route.id
    
    def test_get_optimal_route(self, routes_service, test_trip):
        """Test getting the optimal route (fastest)."""
        routes_data = [
            CreateRouteRequest(
                trip_id=test_trip.id,
                route_type="fastest",
                origin_lat=40.7128,
                origin_lng=-74.0060,
                destination_lat=34.0522,
                destination_lng=-118.2437,
                distance=3980,
                duration=45000,
                polyline="encoded_polyline_1",
                toll_cost=25.50,
                fuel_cost=120.00
            ),
            CreateRouteRequest(
                trip_id=test_trip.id,
                route_type="economical",
                origin_lat=40.7128,
                origin_lng=-74.0060,
                destination_lat=34.0522,
                destination_lng=-118.2437,
                distance=4200,
                duration=50000,
                polyline="encoded_polyline_2",
                toll_cost=5.00,
                fuel_cost=100.00
            )
        ]
        
        for data in routes_data:
            routes_service.create_route(data)
        
        optimal = routes_service.get_optimal_route(test_trip.id)
        
        assert optimal is not None
        assert optimal.route_type == "fastest"
