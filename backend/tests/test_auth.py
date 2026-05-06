"""Authentication endpoint tests."""
import pytest
import time


class TestEmailAuth:
    """Tests for email authentication endpoints."""
    
    def test_send_code_success(self, client):
        """Test sending verification code to new email."""
        response = client.post("/api/auth/email/send-code", json={
            "email": "new_user@test.com"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "dev_code" in data
    
    def test_send_code_already_registered(self, client, registered_user):
        """Test sending code to already registered email."""
        response = client.post("/api/auth/email/send-code", json={
            "email": registered_user["email"]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["registered"] is True
    
    def test_send_code_invalid_email(self, client):
        """Test sending code to invalid email."""
        response = client.post("/api/auth/email/send-code", json={
            "email": "invalid-email"
        })
        assert response.status_code == 400
    
    def test_register_success(self, client):
        """Test successful registration."""
        email = "register_test@test.com"
        password = "testpassword123"
        
        # Get code
        response = client.post("/api/auth/email/send-code", json={"email": email})
        assert response.status_code == 200
        code = response.json()["dev_code"]
        
        # Register
        response = client.post("/api/auth/email/register", json={
            "email": email,
            "code": code,
            "password": password,
            "nickname": "Test User"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == email
    
    def test_register_invalid_code(self, client):
        """Test registration with invalid code."""
        response = client.post("/api/auth/email/register", json={
            "email": "test_invalid@test.com",
            "code": "000000",
            "password": "testpassword123"
        })
        assert response.status_code == 400
    
    def test_register_duplicate_email(self, client, registered_user):
        """Test registration with duplicate email."""
        # Get a new code
        response = client.post("/api/auth/email/send-code", json={
            "email": "another_new@test.com"
        })
        code = response.json()["dev_code"]
        
        # Try to register with existing email (directly using different code)
        response = client.post("/api/auth/email/register", json={
            "email": registered_user["email"],
            "code": code,
            "password": "anotherpassword123"
        })
        # API returns 409 or 400 for duplicate email
        assert response.status_code in [409, 400]
    
    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        email = "weak_pass@test.com"
        
        response = client.post("/api/auth/email/send-code", json={"email": email})
        code = response.json()["dev_code"]
        
        response = client.post("/api/auth/email/register", json={
            "email": email,
            "code": code,
            "password": "123"  # Too short
        })
        assert response.status_code == 422
    
    def test_login_success(self, client, registered_user):
        """Test successful login."""
        response = client.post("/api/auth/email/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == registered_user["email"]
    
    def test_login_wrong_password(self, client, registered_user):
        """Test login with wrong password."""
        response = client.post("/api/auth/email/login", json={
            "email": registered_user["email"],
            "password": "wrongpassword"
        })
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post("/api/auth/email/login", json={
            "email": "nonexistent@example.com",
            "password": "somepassword123"
        })
        assert response.status_code == 401
    
    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format."""
        response = client.post("/api/auth/email/login", json={
            "email": "not-an-email",
            "password": "password123"
        })
        # API may return 401 (auth failed) or 422 (validation error)
        assert response.status_code in [401, 422]


class TestPasswordReset:
    """Tests for password reset functionality."""
    
    def test_send_reset_code_success(self, client, registered_user):
        """Test sending reset code to registered email."""
        response = client.post("/api/auth/email/send-reset-code", json={
            "email": registered_user["email"]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "dev_code" in data
    
    def test_send_reset_code_unregistered(self, client):
        """Test sending reset code to unregistered email."""
        response = client.post("/api/auth/email/send-reset-code", json={
            "email": "not_registered@example.com"
        })
        assert response.status_code == 404
    
    def test_reset_password_success(self, client, registered_user):
        """Test successful password reset."""
        email = registered_user["email"]
        
        # Get reset code
        response = client.post("/api/auth/email/send-reset-code", json={"email": email})
        code = response.json()["dev_code"]
        
        # Reset password
        new_password = "newpassword123"
        response = client.post("/api/auth/email/reset-password", json={
            "email": email,
            "code": code,
            "password": new_password
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        
        # Verify can login with new password
        response = client.post("/api/auth/email/login", json={
            "email": email,
            "password": new_password
        })
        assert response.status_code == 200
    
    def test_reset_password_invalid_code(self, client, registered_user):
        """Test password reset with invalid code."""
        response = client.post("/api/auth/email/reset-password", json={
            "email": registered_user["email"],
            "code": "000000",
            "password": "newpassword123"
        })
        assert response.status_code == 400


class TestAuthMe:
    """Tests for /api/auth/me endpoint."""
    
    def test_get_current_user_authenticated(self, client, auth_headers, registered_user):
        """Test getting current user info when authenticated."""
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "user" in data
        assert data["user"]["email"] == registered_user["email"]
    
    def test_get_current_user_unauthenticated(self, client):
        """Test getting current user info without authentication."""
        response = client.get("/api/auth/me")
        # API returns 200 or 401 depending on implementation
        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert data["user"] is None
        else:
            assert response.status_code == 401


class TestLogout:
    """Tests for logout functionality."""
    
    def test_logout_success(self, client, auth_headers, registered_user):
        """Test successful logout."""
        response = client.post("/api/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        
        # Verify token is invalidated or user is None
        response = client.get("/api/auth/me", headers=auth_headers)
        if response.status_code == 200:
            assert response.json().get("user") is None
        else:
            assert response.status_code in [401, 403]
    
    def test_logout_without_token(self, client):
        """Test logout without token."""
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
