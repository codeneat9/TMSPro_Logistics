import pytest
import uuid
from backend.services.routes import RoutesService
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


class TestRoutesService:
    """Unit tests for RoutesService."""
    
    def test_create_route(self, db_session, test_trip):
        """Test creating a route."""
        route = RoutesService.create_route(
            db=db_session,
            trip_id=test_trip.id,
            route_type="optimal",
            distance_km=3980,
            duration_minutes=45000,
            polyline="encoded_polyline_data",
            predicted_cost=120.00,
            risk_score=0.25,
        )

        assert route is not None
        assert route.trip_id == test_trip.id
        assert route.distance_km == 3980
        assert route.predicted_cost == 120.00
    
    def test_get_route(self, db_session, test_trip):
        """Test retrieving a route."""
        created_route = RoutesService.create_route(
            db=db_session,
            trip_id=test_trip.id,
            route_type="optimal",
            distance_km=3980,
            duration_minutes=45000,
            polyline="encoded_polyline_data",
            predicted_cost=120.00,
        )
        retrieved_route = RoutesService.get_route(db_session, created_route.id)
        
        assert retrieved_route is not None
        assert retrieved_route.id == created_route.id
        assert retrieved_route.distance_km == 3980
    
    def test_get_trip_routes(self, db_session, test_trip):
        """Test getting all routes for a trip."""
        for i in range(3):
            RoutesService.create_route(
                db=db_session,
                trip_id=test_trip.id,
                route_type="optimal" if i == 0 else f"alternative_{i}",
                distance_km=3980 + i * 100,
                duration_minutes=45000 + i * 1000,
                polyline="encoded_polyline_data",
                predicted_cost=120.00,
            )

        routes = RoutesService.get_trip_routes(db_session, test_trip.id)
        
        assert len(routes) == 3
    
    def test_predict_delay(self, db_session):
        """Test delay prediction."""
        delay = RoutesService.predict_delay(
            db=db_session,
            trip_id=str(uuid.uuid4()),
            distance_km=3980,
            hour_of_day=14,
            day_of_week=3,
            weather_condition="clear",
        )
        
        assert delay > 0
        assert isinstance(delay, (int, float))
    
    def test_calculate_risk_score(self, db_session):
        """Test risk score calculation."""
        risk = RoutesService.calculate_risk_score(
            db=db_session,
            trip_id=str(uuid.uuid4()),
            weather_condition="rain",
            traffic_condition="congested",
        )
        
        assert 0 <= risk <= 100
        assert isinstance(risk, (int, float))
    
    def test_estimate_cost(self, db_session):
        """Test cost estimation."""
        cost = RoutesService.estimate_cost(
            db=db_session,
            distance_km=100,
            duration_minutes=60,
            vehicle_type="standard",
        )
        
        assert cost > 0
        assert isinstance(cost, (int, float))
    
    def test_select_route(self, db_session, test_trip):
        """Test selecting a route for a trip."""
        route = RoutesService.create_route(
            db=db_session,
            trip_id=test_trip.id,
            route_type="optimal",
            distance_km=3980,
            duration_minutes=45000,
            polyline="encoded_polyline_data",
            predicted_delay_minutes=12,
            predicted_cost=120.00,
        )

        updated_trip = RoutesService.select_route(db_session, test_trip.id, route.id)

        assert updated_trip.estimated_delay_minutes == 12
    
    def test_get_optimal_route(self, db_session, test_trip):
        """Test getting the optimal route (fastest)."""
        RoutesService.create_route(
            db=db_session,
            trip_id=test_trip.id,
            route_type="optimal",
            distance_km=3980,
            duration_minutes=45000,
            polyline="encoded_polyline_1",
            predicted_cost=120.00,
        )
        RoutesService.create_route(
            db=db_session,
            trip_id=test_trip.id,
            route_type="alternative_1",
            distance_km=4200,
            duration_minutes=50000,
            polyline="encoded_polyline_2",
            predicted_cost=100.00,
        )

        optimal = RoutesService.get_optimal_route(db_session, test_trip.id)
        
        assert optimal is not None
        assert optimal.route_type == "optimal"
