"""Test fixtures and configuration."""
import os
import sys
import pytest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
# ...and the tests directory itself, so suites can share helper modules
# (e.g. `emd_schema_catalog`) without every caller setting PYTHONPATH.
sys.path.insert(0, str(Path(__file__).parent))

# Use PostgreSQL for tests
os.environ['DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:5431/postgres'
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only'
# Keep SMTP settings empty so email service is disabled in tests
# This ensures dev_code is returned instead of trying to send real emails
os.environ['SMTP_HOST'] = ''
os.environ['SMTP_USER'] = ''
os.environ['SMTP_PASS'] = ''
os.environ['WX_APP_ID'] = 'test_wx_app_id'
os.environ['WX_APP_SECRET'] = 'test_wx_secret'
os.environ['ALLOW_DEV_AUTH_CODE'] = 'true'

# Keep tests deterministic and prevent a developer shell/.env from turning
# fallback tests into paid external provider calls.
for _provider_key in (
    'OPENAI_API_KEY', 'SILICONFLOW_API_KEY', 'ANTHROPIC_API_KEY',
    'DEEPSEEK_API_KEY', 'GOOGLE_API_KEY', 'GEMINI_API_KEY', 'LLM_API_KEY',
):
    os.environ[_provider_key] = ''

# NOTE: The full application (`import main`) and the FastAPI TestClient pull in
# heavy optional dependencies and, at first use, a live PostgreSQL connection.
# Importing them at module import time makes `pytest --collect-only` fail on any
# machine without the full dependency set / a test database. Gate the imports so
# collection always succeeds; tests that actually exercise the app skip cleanly
# when the app cannot be imported.
try:
    from fastapi.testclient import TestClient
    import main
except Exception as _app_import_error:  # pragma: no cover - env-dependent
    TestClient = None
    main = None
    _APP_IMPORT_ERROR = _app_import_error
else:
    _APP_IMPORT_ERROR = None


def _require_app():
    """Skip the current test if the app / deps could not be imported."""
    if main is None or TestClient is None:
        pytest.skip(f"app import unavailable: {_APP_IMPORT_ERROR}")


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


@pytest.fixture(scope='session')
def _test_db_session():
    """Initialize PostgreSQL database for testing."""
    _require_app()
    # Initialize database connection pool
    main._init_database()
    # Initialize database tables
    main._init_db()
    yield


@pytest.fixture(autouse=True)
def test_db(request):
    """Initialize PostgreSQL database unless a test is marked no_db."""
    if request.node.get_closest_marker("no_db"):
        yield
        return
    request.getfixturevalue("_test_db_session")
    yield


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset rate limits before each test."""
    try:
        if main is not None and hasattr(main.limiter, '_storage') and main.limiter._storage:
            main.limiter._storage.reset()
    except Exception:
        pass
    yield


@pytest.fixture
def client(test_db):
    """Create a test client with fresh database and cleared rate limits."""
    _require_app()
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
        # Tests may continue exercising native Bearer compatibility, but browser
        # responses no longer expose the credential in JSON.
        "token": client.cookies.get("biblesphere_session"),
        "user": data["user"]
    }


@pytest.fixture
def auth_headers(registered_user):
    """Return authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {registered_user['token']}"}


@pytest.fixture
def church_auth_headers(client, auth_headers, registered_user):
    """Authenticated user with the church membership required for prayer posts."""
    response = client.post(
        "/api/church/create",
        json={"name": f"Test Church {_user_counter}"},
        headers=auth_headers,
    )
    assert response.status_code in (200, 409)
    return auth_headers
