import pytest
import tempfile
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.database import get_db
from backend.database import Base
from backend import models  # Ensure model modules are imported and registered on Base.metadata
from fastapi.testclient import TestClient
from backend.main import app


# Create a temporary database for testing
@pytest.fixture(scope="session")
def test_db_url():
    """Create a temporary SQLite database for testing."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    yield f"sqlite:///{db_path}"
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture(scope="session")
def engine(test_db_url):
    """Create test database engine."""
    engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine):
    """Create a database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Create test client with test database."""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_token(client):
    """Create a test auth token for authenticated requests."""
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User",
            "phone": "+1234567890"
        }
    )
    
    if register_response.status_code in [200, 201]:
        return register_response.json()["access_token"]
    
    return None


@pytest.fixture
def auth_headers(auth_token):
    """Return authorization headers with Bearer token."""
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}
    return {}


@pytest.fixture
def admin_token(client):
    """Create an admin auth token for privileged endpoints."""
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "password": "AdminPassword123!",
            "full_name": "Admin User",
            "phone": "+1234567891",
            "role": "admin"
        }
    )

    if register_response.status_code in [200, 201]:
        return register_response.json()["access_token"]

    return None


@pytest.fixture
def admin_auth_headers(admin_token):
    """Return authorization headers for admin user."""
    if admin_token:
        return {"Authorization": f"Bearer {admin_token}"}
    return {}
