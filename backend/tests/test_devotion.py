"""Devotion journal and user-related endpoint tests."""
import pytest
import time


class TestDevotionJournals:
    """Tests for devotion journal endpoints."""
    
    def test_get_journals_authenticated(self, client, auth_headers):
        """Test getting journals when authenticated."""
        response = client.get("/api/devotion/journals", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "items" in data
        assert "total" in data
    
    def test_get_journals_unauthenticated(self, client):
        """Test getting journals without authentication."""
        response = client.get("/api/devotion/journals")
        assert response.status_code == 401
    
    def test_create_journal(self, client, auth_headers):
        """Test creating a new journal entry."""
        today = time.strftime("%Y-%m-%d")
        response = client.post("/api/devotion/journals", json={
            "date": today,
            "title": "Test Journal Entry",
            "scripture": "John 3:16",
            "observation": "God loves the world",
            "reflection": "This shows God's great love",
            "application": "I should love others",
            "prayer": "Help me love like You",
            "mood": "peaceful"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "journal" in data
        assert data["journal"]["title"] == "Test Journal Entry"
    
    def test_create_journal_missing_required(self, client, auth_headers):
        """Test creating journal without required date field."""
        response = client.post("/api/devotion/journals", json={
            "title": "Test Entry"
        }, headers=auth_headers)
        assert response.status_code == 422
    
    def test_get_journal_by_id(self, client, auth_headers):
        """Test getting a specific journal by ID."""
        # First create a journal
        today = time.strftime("%Y-%m-%d")
        response = client.post("/api/devotion/journals", json={
            "date": today,
            "title": "Journal for Get Test",
            "scripture": "Psalm 23:1"
        }, headers=auth_headers)
        journal_id = response.json()["journal"]["id"]
        
        # Now get it
        response = client.get(f"/api/devotion/journals/{journal_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["journal"]["title"] == "Journal for Get Test"
    
    def test_get_journal_not_found(self, client, auth_headers):
        """Test getting non-existent journal."""
        response = client.get("/api/devotion/journals/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_update_journal(self, client, auth_headers):
        """Test updating an existing journal."""
        # Create first
        today = time.strftime("%Y-%m-%d")
        response = client.post("/api/devotion/journals", json={
            "date": today,
            "title": "Original Title"
        }, headers=auth_headers)
        journal_id = response.json()["journal"]["id"]
        
        # Update
        response = client.post("/api/devotion/journals", json={
            "date": today,
            "title": "Updated Title",
            "scripture": "Updated scripture"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["journal"]["title"] == "Updated Title"
    
    def test_delete_journal(self, client, auth_headers):
        """Test deleting a journal."""
        # Create first
        today = time.strftime("%Y-%m-%d")
        response = client.post("/api/devotion/journals", json={
            "date": today,
            "title": "To be deleted"
        }, headers=auth_headers)
        journal_id = response.json()["journal"]["id"]
        
        # Delete
        response = client.delete(f"/api/devotion/journals/{journal_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        
        # Verify deleted
        response = client.get(f"/api/devotion/journals/{journal_id}", headers=auth_headers)
        assert response.status_code == 404
    
    def test_delete_journal_not_found(self, client, auth_headers):
        """Test deleting non-existent journal."""
        response = client.delete("/api/devotion/journals/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_delete_other_user_journal(self, client):
        """Test cannot delete another user's journal."""
        # This would require creating two users - skipping for now
        pass


class TestUserCheckin:
    """Tests for user checkin endpoints."""
    
    def test_checkin_authenticated(self, client, auth_headers):
        """Test checkin with authentication."""
        response = client.post("/api/user/checkin", json={
            "emotionLabel": "喜悦",
            "emotionQuery": "今天感觉很开心",
            "scenarioCategory": "工作",
            "scenarioDetail": "项目进展顺利",
            "driverType": "内在动力",
            "driverOption": "完成目标",
            "mood": "很好",
            "sleep": "充足",
            "energy": "高",
            "gratitude": "感谢神的带领"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        # Response may have gratitudeScripture or tags_extracted
        assert "gratitudeScripture" in data or "tags_extracted" in data or "scripture" in data
    
    def test_checkin_unauthenticated(self, client):
        """Test checkin without authentication (guest mode)."""
        response = client.post("/api/user/checkin", json={
            "emotionLabel": "平安",
            "mood": "平静"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        # Response may have gratitudeScripture or tags_extracted
        assert "gratitudeScripture" in data or "tags_extracted" in data or "scripture" in data
    
    def test_get_user_tags_authenticated(self, client, auth_headers):
        """Test getting user tags when authenticated."""
        # First do a checkin to generate tags
        client.post("/api/user/checkin", json={
            "emotionLabel": "喜乐",
            "scenarioCategory": "家庭"
        }, headers=auth_headers)
        
        response = client.get("/api/user/tags", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert "tags" in data
    
    def test_get_user_tags_unauthenticated(self, client):
        """Test getting user tags without authentication."""
        response = client.get("/api/user/tags")
        assert response.status_code == 401


class TestSecurityHeaders:
    """Tests for security headers."""
    
    def test_security_headers_present(self, client):
        """Test that security headers are present."""
        response = client.get("/api/health")
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
