import pytest
from fastapi.testclient import TestClient


class TestAuthAPI:
    """Integration tests for Authentication endpoints."""
    
    def test_register_endpoint(self, client):
        """Test user registration endpoint."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "full_name": "John Doe",
                "phone": "+1234567890"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 86400
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePassword123!",
                "full_name": "John Doe",
                "phone": "+1234567890"
            }
        )
        
        assert response.status_code >= 400
    
    def test_login_endpoint(self, client, auth_token):
        """Test user login endpoint."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    def test_login_wrong_password(self, client, auth_token):
        """Test login with wrong password."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401

    def test_me_endpoint(self, client, auth_headers):
        """Test current user profile endpoint."""
        response = client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"]
        assert data["email"] == "test@example.com"
        assert data["role"]


class TestTripsAPI:
    """Integration tests for Trips endpoints."""
    
    def test_create_trip_endpoint(self, client, auth_headers):
        """Test trip creation endpoint."""
        response = client.post(
            "/api/trips",
            headers=auth_headers,
            json={
                "user_id": "placeholder-user-id",
                "pickup_lat": 40.7128,
                "pickup_lng": -74.0060,
                "dropoff_lat": 34.0522,
                "dropoff_lng": -118.2437,
                "cargo_description": "Test Cargo",
                "cargo_weight_kg": 100.0
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
    
    def test_get_trip_endpoint(self, client, auth_headers):
        """Test getting trip details."""
        # Create a trip first
        create_response = client.post(
            "/api/trips",
            headers=auth_headers,
            json={
                "user_id": "placeholder-user-id",
                "pickup_lat": 40.7128,
                "pickup_lng": -74.0060,
                "dropoff_lat": 34.0522,
                "dropoff_lng": -118.2437,
                "cargo_description": "Test Cargo",
                "cargo_weight_kg": 100.0
            }
        )
        
        trip_id = create_response.json()["id"]
        
        # Get the trip
        response = client.get(
            f"/api/trips/{trip_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == trip_id
    
    def test_list_trips_endpoint(self, client, auth_headers):
        """Test listing trips."""
        response = client.get(
            "/api/trips",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)


class TestDriversAPI:
    """Integration tests for Drivers endpoints."""
    
    def test_list_drivers_endpoint(self, client):
        """Test listing drivers (public endpoint)."""
        response = client.get("/api/drivers")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "items" in data
    
    def test_get_driver_endpoint(self, client, auth_headers):
        """Test getting driver profile."""
        # Create a driver first
        create_response = client.post(
            "/api/drivers",
            headers=auth_headers,
            json={
                "license_number": "DL123456",
                "license_expiry": "2025-12-31",
                "phone_number": "+1234567890",
                "address": "123 Main Street"
            }
        )
        
        if create_response.status_code == 200:
            driver_id = create_response.json()["id"]
            
            response = client.get(
                f"/api/drivers/{driver_id}",
                headers=auth_headers
            )
            
            assert response.status_code == 200


class TestLocationsAPI:
    """Integration tests for Locations endpoints."""
    
    def test_record_location_endpoint(self, client, auth_headers):
        """Test recording GPS location."""
        # Create a trip first
        trip_response = client.post(
            "/api/trips",
            headers=auth_headers,
            json={
                "user_id": "placeholder-user-id",
                "pickup_lat": 40.7128,
                "pickup_lng": -74.0060,
                "dropoff_lat": 34.0522,
                "dropoff_lng": -118.2437,
                "cargo_description": "Test Cargo",
                "cargo_weight_kg": 100.0
            }
        )
        
        trip_id = trip_response.json()["id"]
        
        # Record location
        response = client.post(
            "/api/locations",
            headers=auth_headers,
            json={
                "trip_id": trip_id,
                "latitude": 40.7128,
                "longitude": -74.0060,
                "speed_kmh": 45.0,
                "heading": 90,
                "accuracy_meters": 5.0
            }
        )
        
        assert response.status_code == 201
    
    def test_get_trip_locations_endpoint(self, client, auth_headers):
        """Test getting trip location history."""
        response = client.get(
            "/api/locations/1",
            headers=auth_headers
        )
        
        # Should return 200 or 404 if trip not found
        assert response.status_code in [200, 404]


class TestRoutesAPI:
    """Integration tests for Routes endpoints."""
    
    def test_estimate_cost_endpoint(self, client, auth_headers):
        """Test cost estimation endpoint."""
        response = client.post(
            "/api/routes/estimate-cost",
            headers=auth_headers,
            params={
                "distance_km": 100,
                "duration_minutes": 60,
                "vehicle_type": "standard",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "estimated_cost" in data
        assert data["estimated_cost"] > 0
    
    def test_predict_delay_endpoint(self, client, auth_headers):
        """Test delay prediction endpoint."""
        response = client.post(
            "/api/routes/predict-delay",
            headers=auth_headers,
            params={
                "trip_id": "trip-test",
                "distance_km": 100,
                "hour_of_day": 14,
                "day_of_week": 3,
                "weather_condition": "clear",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "predicted_delay_minutes" in data
        assert data["predicted_delay_minutes"] >= 0
    
    def test_calculate_risk_endpoint(self, client, auth_headers):
        """Test risk calculation endpoint."""
        response = client.post(
            "/api/routes/calculate-risk",
            headers=auth_headers,
            params={
                "trip_id": "trip-test",
                "weather_condition": "rain",
                "traffic_condition": "congested",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "risk_score" in data
        assert 0 <= data["risk_score"] <= 100


class TestHealthCheck:
    """Integration tests for health check endpoint."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data
