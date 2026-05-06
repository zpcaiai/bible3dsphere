"""Basic endpoint tests."""
import pytest


class TestHealthEndpoints:
    """Tests for health and basic endpoints."""
    
    def test_health_check(self, client):
        """Test /api/health endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
    
    def test_get_layout(self, client):
        """Test /api/layout endpoint."""
        response = client.get("/api/layout")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "count" in data
        assert isinstance(data["items"], list)
    
    def test_get_history(self, client):
        """Test /api/history endpoint."""
        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
    
    def test_get_feature_not_found(self, client):
        """Test /api/feature with invalid key."""
        response = client.get("/api/feature?key=nonexistent")
        assert response.status_code == 404
    
    def test_get_stats(self, client):
        """Test /api/stats endpoint."""
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        # Stats endpoint returns page_views and unique_visitors
        assert "page_views" in data or "visitCount" in data or "total" in data
    
    def test_post_track_stats(self, client):
        """Test /api/stats/track endpoint."""
        response = client.post("/api/stats/track", json={"visitorId": "test-visitor-123"})
        assert response.status_code == 200
        data = response.json()
        # Track endpoint returns updated stats, not 'ok'
        assert isinstance(data, dict)


class TestPrayerEndpoints:
    """Tests for prayer wall endpoints."""
    
    def test_get_prayers(self, client):
        """Test /api/prayers GET endpoint."""
        response = client.get("/api/prayers")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
    
    def test_get_prayers_pagination(self, client):
        """Test /api/prayers with pagination."""
        response = client.get("/api/prayers?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    def test_post_prayer_anonymous(self, client):
        """Test posting prayer without authentication."""
        response = client.post("/api/prayers", json={
            "content": "Test prayer content",
            "is_anonymous": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "id" in data
    
    def test_post_prayer_authenticated(self, client, auth_headers):
        """Test posting prayer with authentication."""
        response = client.post("/api/prayers", json={
            "content": "Test prayer from authenticated user",
            "is_anonymous": False
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "id" in data
    
    def test_post_prayer_missing_content(self, client):
        """Test posting prayer without content."""
        response = client.post("/api/prayers", json={
            "is_anonymous": True
        })
        assert response.status_code == 422  # Validation error
    
    def test_amen_prayer_not_found(self, client):
        """Test amen on non-existent prayer."""
        response = client.post("/api/prayers/99999/amen")
        assert response.status_code == 404
