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
        email = f"register_test_{int(time.time())}@test.com"
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
        assert "token" not in data
        assert response.cookies.get("biblesphere_session")
        set_cookie = response.headers['set-cookie'].lower()
        assert 'httponly' in set_cookie
        assert 'samesite=lax' in set_cookie
        assert "user" in data
        assert data["user"]["email"] == email
    
    def test_session_token_stays_out_of_the_body_same_origin(self, client):
        """同域下，会话凭据只走 HttpOnly cookie，绝不出现在 JS 可读的响应体里。

        这是 test_register_success / test_login_success 已经断言的口径，这里单列一条，
        是为了让「同域不返回 token」这件事本身有名字——否则下次有人为了跨域方便，
        很容易顺手把 token 加回去，而上面两条用例的失败信息看不出这是安全回退。
        """
        email = f"same_origin_{int(time.time() * 1000)}@test.com"
        code = client.post("/api/auth/email/send-code", json={"email": email}).json()["dev_code"]
        reg = client.post("/api/auth/email/register", json={
            "email": email, "code": code, "password": "testpassword123", "nickname": "SameOrigin",
        })
        assert reg.status_code == 200
        assert "token" not in reg.json()
        assert reg.cookies.get("biblesphere_session")

        login = client.post("/api/auth/email/login", json={"email": email, "password": "testpassword123"})
        assert login.status_code == 200
        assert "token" not in login.json()

    def test_cross_origin_still_gets_a_bearer_token(self, client):
        """跨域时必须仍然返回 token——否则跨域部署会彻底登不上。

        前端 fetch 用的是 `credentials: 'same-origin'`：API 换了域名后 cookie 根本不会
        被发送，Bearer 是唯一活路。所以「同域不给、跨域给」这两条必须成对存在，
        任何一条单独存在都会把另一半悄悄改坏。
        """
        email = f"cross_origin_{int(time.time() * 1000)}@test.com"
        code = client.post("/api/auth/email/send-code", json={"email": email}).json()["dev_code"]
        client.post("/api/auth/email/register", json={
            "email": email, "code": code, "password": "testpassword123", "nickname": "CrossOrigin",
        })

        cross = client.post(
            "/api/auth/email/login",
            json={"email": email, "password": "testpassword123"},
            headers={"Origin": "https://app.example.com", "Host": "api.example.com"},
        )
        assert cross.status_code == 200
        assert cross.json().get("token"), "跨域登录没有拿到 Bearer token，跨域部署将无法登录"

        # 带 Origin 但同源，仍然不给 token（Origin 存在 ≠ 跨域）
        same = client.post(
            "/api/auth/email/login",
            json={"email": email, "password": "testpassword123"},
            headers={"Origin": "https://api.example.com", "Host": "api.example.com"},
        )
        assert "token" not in same.json()

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
        assert "token" not in data
        assert response.cookies.get("biblesphere_session")
        assert "user" in data
        assert data["user"]["email"] == registered_user["email"]

    def test_builtin_john_account_can_login(self, client):
        """The documented first-run account remains available after startup."""
        response = client.post("/api/auth/email/login", json={
            "email": "john@biblesphere.com",
            "password": "John",
        })
        assert response.status_code == 200
        assert response.json()["user"]["email"] == "john@biblesphere.com"
        assert response.cookies.get("biblesphere_session")
    
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


class TestWebSocketTicket:
    def test_ticket_is_short_lived_credential_not_session_token(self, client, registered_user):
        response = client.post('/api/rtc/ws-ticket')
        assert response.status_code == 200
        data = response.json()
        assert data['ticket']
        assert data['expires_in'] == 30
        assert registered_user['token'] not in response.text

        with client.websocket_connect(f"/api/ws/rtc?ticket={data['ticket']}") as websocket:
            ready = websocket.receive_json()
            assert ready['type'] == 'ready'
            assert ready['email'] == registered_user['email']
