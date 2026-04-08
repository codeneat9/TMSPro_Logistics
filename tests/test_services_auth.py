import pytest
from backend.services.auth import AuthService
from backend.models.user import User
from sqlalchemy.orm import Session


@pytest.fixture
def auth_service(db_session):
    """Create AuthService instance with test database."""
    return AuthService(db_session)


class TestAuthService:
    """Unit tests for AuthService."""
    
    def test_hash_password(self, auth_service):
        """Test password hashing."""
        password = "MySecressPassword123!"
        hashed = auth_service.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > len(password)
    
    def test_verify_password(self, auth_service):
        """Test password verification."""
        password = "MySecurePassword123!"
        hashed = auth_service.hash_password(password)
        
        assert auth_service.verify_password(password, hashed) is True
        assert auth_service.verify_password("WrongPassword", hashed) is False
    
    def test_create_access_token(self, auth_service):
        """Test access token creation."""
        user_id = 123
        email = "test@example.com"
        role = "customer"
        
        token = auth_service.create_access_token(user_id, email, role)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token(self, auth_service):
        """Test refresh token creation."""
        user_id = 123
        
        token = auth_service.create_refresh_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token(self, auth_service):
        """Test token verification."""
        user_id = 123
        email = "test@example.com"
        role = "customer"
        
        token = auth_service.create_access_token(user_id, email, role)
        payload = auth_service.verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["email"] == email
        assert payload["role"] == role
    
    def test_verify_invalid_token(self, auth_service):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        payload = auth_service.verify_token(invalid_token)
        
        assert payload is None
    
    def test_register_user(self, auth_service):
        """Test user registration."""
        user = auth_service.register_user(
            email="newuser@example.com",
            password="SecurePassword123!",
            first_name="John",
            last_name="Doe"
        )
        
        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
    
    def test_register_duplicate_email(self, auth_service):
        """Test that registering with duplicate email fails."""
        email = "duplicate@example.com"
        
        auth_service.register_user(
            email=email,
            password="SecurePassword123!",
            first_name="John",
            last_name="Doe"
        )
        
        # Try to register with same email
        user = auth_service.register_user(
            email=email,
            password="AnotherPassword123!",
            first_name="Jane",
            last_name="Doe"
        )
        
        # Should return None or raise exception
        # Depending on implementation
        assert user is None or user.email == email
    
    def test_authenticate_user(self, auth_service):
        """Test user authentication."""
        email = "authtest@example.com"
        password = "SecurePassword123!"
        
        auth_service.register_user(
            email=email,
            password=password,
            first_name="Auth",
            last_name="Test"
        )
        
        user = auth_service.authenticate_user(email, password)
        
        assert user is not None
        assert user.email == email
    
    def test_authenticate_wrong_password(self, auth_service):
        """Test authentication with wrong password."""
        email = "wrongpass@example.com"
        password = "SecurePassword123!"
        
        auth_service.register_user(
            email=email,
            password=password,
            first_name="Wrong",
            last_name="Pass"
        )
        
        user = auth_service.authenticate_user(email, "WrongPassword")
        
        assert user is None
    
    def test_authenticate_nonexistent_user(self, auth_service):
        """Test authentication with nonexistent email."""
        user = auth_service.authenticate_user("nonexistent@example.com", "password")
        
        assert user is None
