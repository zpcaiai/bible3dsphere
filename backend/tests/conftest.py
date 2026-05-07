"""Test fixtures and configuration."""
import os
import sys
import pytest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use PostgreSQL for tests
os.environ['DATABASE_URL'] = 'postgresql://stephen@localhost:5432/biblesphere_test'
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only'
# Keep SMTP settings empty so email service is disabled in tests
# This ensures dev_code is returned instead of trying to send real emails
os.environ['SMTP_HOST'] = ''
os.environ['SMTP_USER'] = ''
os.environ['SMTP_PASS'] = ''
os.environ['WX_APP_ID'] = 'test_wx_app_id'
os.environ['WX_APP_SECRET'] = 'test_wx_secret'

from fastapi.testclient import TestClient

# Import after setting env vars
import main

# Create a mock rate limiter that doesn't actually limit
class MockLimiter:
    def limit(self, *args, **kwargs):
        def decorator(f):
            return f
        return decorator

    def __call__(self, *args, **kwargs):
        pass

    def _inject_headers(self, *args, **kwargs):
        pass

    def _check_request_limit(self, *args, **kwargs):
        return True  # Always allow


@pytest.fixture(scope='session', autouse=True)
def test_db():
    """Initialize PostgreSQL database for testing."""
    # Initialize database connection pool
    main._init_database()
    # Initialize database tables
    main._init_db()
    yield


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset rate limits before each test."""
    try:
        if hasattr(main.limiter, '_storage') and main.limiter._storage:
            main.limiter._storage.reset()
    except Exception:
        pass
    yield


@pytest.fixture
def client(test_db):
    """Create a test client with fresh database and cleared rate limits."""
    # Clear the rate limit storage before each test
    # The storage is a MemoryStorage object with a reset method
    try:
        if hasattr(main.limiter, '_storage') and main.limiter._storage:
            # Reset memory storage
            main.limiter._storage.reset()
    except Exception:
        pass  # If reset fails, just continue
    
    with TestClient(main.app) as test_client:
        yield test_client


# Counter for generating unique emails
_user_counter = 0

@pytest.fixture
def registered_user(client):
    """Create a registered user and return credentials."""
    global _user_counter
    _user_counter += 1
    email = f"test_user_{_user_counter}_{id(client)}@example.com"
    password = "testpassword123"
    nickname = "Test User"
    
    # Get verification code
    response = client.post("/api/auth/email/send-code", json={"email": email})
    assert response.status_code == 200
    data = response.json()
    code = data.get("dev_code")
    
    # Register
    response = client.post("/api/auth/email/register", json={
        "email": email,
        "code": code,
        "password": password,
        "nickname": nickname
    })
    assert response.status_code == 200
    data = response.json()
    
    return {
        "email": email,
        "password": password,
        "nickname": nickname,
        "token": data["token"],
        "user": data["user"]
    }


@pytest.fixture
def auth_headers(registered_user):
    """Return authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {registered_user['token']}"}
