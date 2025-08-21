"""Unit tests for digest functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import time, datetime
from fastapi.testclient import TestClient
from fastapi import HTTPException

from api.main import app
from api.services.database import get_database_with_user
from api.schemas.digest import DigestPreferences, DigestPreviewRequest


class TestDigestEndpoints:
    """Test digest API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        self.user_id = "123e4567-e89b-12d3-a456-426614174000"
        self.valid_jwt = "valid.jwt.token"
        
        # Mock user data
        self.mock_user_data = {
            "id": self.user_id,
            "email": "test@example.com",
            "user_metadata": {
                "name": "Test User",
                "full_name": "Test User Full"
            }
        }
        
        # Mock digest profile data
        self.mock_digest_profile = {
            "user_id": self.user_id,
            "digest_enabled": True,
            "digest_cadence": "weekly",
            "digest_time": "09:00:00",
            "digest_day": 1,
            "last_digest_sent": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # Mock clips data
        self.mock_clips = [
            {
                "clip_id": "clip-1",
                "source_url": "https://example.com/1",
                "title": "Test Clip 1",
                "description": "Test description 1",
                "thumbnail_url": "https://example.com/thumb1.jpg",
                "saved_at": datetime.now()
            },
            {
                "clip_id": "clip-2", 
                "source_url": "https://example.com/2",
                "title": "Test Clip 2",
                "description": "Test description 2",
                "saved_at": datetime.now()
            }
        ]

    def teardown_method(self):
        """Clean up after tests."""
        # Clear any dependency overrides
        app.dependency_overrides.clear()

    def test_get_digest_preferences_success(self):
        """Test successful digest preferences retrieval."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_get_digest_preferences(db, user_id):
            return {
                "digest_enabled": True,
                "digest_cadence": "weekly",
                "digest_time": "09:00:00",
                "digest_day": 1
            }

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with patch("api.routes.digest.get_digest_preferences", mock_get_digest_preferences):
            response = self.client.get(
                "/digest/preferences",
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["digest_enabled"] is True
        assert data["digest_cadence"] == "weekly"
        assert data["digest_time"] == "09:00:00"
        assert data["digest_day"] == 1

    def test_get_digest_preferences_create_default(self):
        """Test digest preferences retrieval with default profile creation."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_get_digest_preferences(db, user_id):
            return None  # No existing profile

        async def mock_create_user_digest_profile(db, user_id, profile_data):
            return True

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with patch("api.routes.digest.get_digest_preferences", mock_get_digest_preferences), \
             patch("api.routes.digest.create_user_digest_profile", mock_create_user_digest_profile):
            response = self.client.get(
                "/digest/preferences",
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["digest_enabled"] is True
        assert data["digest_cadence"] == "weekly"

    def test_update_digest_preferences_success(self):
        """Test successful digest preferences update."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_get_user_digest_profile(db, user_id):
            return self.mock_digest_profile

        async def mock_update_digest_preferences(db, user_id, preferences):
            return True

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with patch("api.routes.digest.get_user_digest_profile", mock_get_user_digest_profile), \
             patch("api.routes.digest.update_digest_preferences", mock_update_digest_preferences):
            response = self.client.put(
                "/digest/preferences",
                json={
                    "digest_enabled": False,
                    "digest_cadence": "daily",
                    "digest_time": "18:00:00",
                    "digest_day": 5
                },
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["digest_enabled"] is False
        assert data["digest_cadence"] == "daily"
        assert data["digest_time"] == "18:00:00"
        assert data["digest_day"] == 5

    def test_update_digest_preferences_create_profile(self):
        """Test digest preferences update with profile creation."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_get_user_digest_profile(db, user_id):
            return None  # No existing profile

        async def mock_create_user_digest_profile(db, user_id, profile_data):
            return True

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with patch("api.routes.digest.get_user_digest_profile", mock_get_user_digest_profile), \
             patch("api.routes.digest.create_user_digest_profile", mock_create_user_digest_profile):
            response = self.client.put(
                "/digest/preferences",
                json={
                    "digest_enabled": True,
                    "digest_cadence": "monthly",
                    "digest_time": "10:00:00",
                    "digest_day": 1
                },
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["digest_enabled"] is True
        assert data["digest_cadence"] == "monthly"

    def test_update_digest_preferences_validation_error(self):
        """Test digest preferences update with validation error."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        response = self.client.put(
            "/digest/preferences",
            json={
                "digest_enabled": True,
                "digest_cadence": "invalid",  # Invalid cadence
                "digest_time": "25:00:00",    # Invalid time
                "digest_day": 8               # Invalid day
            },
            headers={"Authorization": f"Bearer {self.valid_jwt}"}
        )

        assert response.status_code == 422

    def test_get_digest_preview_success(self):
        """Test successful digest preview generation."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_get_user_profile(db, user_id):
            return self.mock_user_data

        async def mock_get_latest_clips_for_digest(db, user_id, limit):
            return self.mock_clips

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with patch("api.routes.digest.get_user_profile", mock_get_user_profile), \
             patch("api.routes.digest.get_latest_clips_for_digest", mock_get_latest_clips_for_digest):
            response = self.client.get(
                "/digest/preview?template_type=weekly",
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "html_content" in data
        assert data["clip_count"] == 2
        assert "preview_date" in data
        assert "Test User" in data["html_content"]
        assert "Test Clip 1" in data["html_content"]

    def test_get_digest_preview_no_clips(self):
        """Test digest preview generation with no clips."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_get_user_profile(db, user_id):
            return self.mock_user_data

        async def mock_get_latest_clips_for_digest(db, user_id, limit):
            return []  # No clips

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with patch("api.routes.digest.get_user_profile", mock_get_user_profile), \
             patch("api.routes.digest.get_latest_clips_for_digest", mock_get_latest_clips_for_digest):
            response = self.client.get(
                "/digest/preview?template_type=daily",
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["clip_count"] == 0
        assert "No clips saved yet" in data["html_content"]

    def test_subscribe_to_digest_success(self):
        """Test successful digest subscription."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_update_digest_preferences(db, user_id, preferences):
            return True

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with patch("api.routes.digest.update_digest_preferences", mock_update_digest_preferences):
            response = self.client.post(
                "/digest/subscribe",
                json={"enabled": True},
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert "enabled" in data["message"]

    def test_unsubscribe_from_digest_success(self):
        """Test successful digest unsubscription."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_update_digest_preferences(db, user_id, preferences):
            return True

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with patch("api.routes.digest.update_digest_preferences", mock_update_digest_preferences):
            response = self.client.delete(
                "/digest/subscribe",
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert "disabled" in data["message"]

    def test_digest_endpoints_unauthenticated(self):
        """Test digest endpoints without authentication."""
        # Test without Authorization header
        response = self.client.get("/digest/preferences")
        assert response.status_code == 401

        response = self.client.put("/digest/preferences", json={})
        assert response.status_code == 401

        response = self.client.get("/digest/preview")
        assert response.status_code == 401

        response = self.client.post("/digest/subscribe", json={})
        assert response.status_code == 401

        response = self.client.delete("/digest/subscribe")
        assert response.status_code == 401

    def test_digest_preferences_validation(self):
        """Test digest preferences validation."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        # Test invalid cadence
        response = self.client.put(
            "/digest/preferences",
            json={"digest_cadence": "invalid"},
            headers={"Authorization": f"Bearer {self.valid_jwt}"}
        )
        assert response.status_code == 422

        # Test invalid day
        response = self.client.put(
            "/digest/preferences",
            json={"digest_day": 0},  # Invalid day
            headers={"Authorization": f"Bearer {self.valid_jwt}"}
        )
        assert response.status_code == 422

        # Test invalid day (too high)
        response = self.client.put(
            "/digest/preferences",
            json={"digest_day": 8},  # Invalid day
            headers={"Authorization": f"Bearer {self.valid_jwt}"}
        )
        assert response.status_code == 422


class TestDigestService:
    """Test digest service functions."""
    
    def test_generate_digest_html(self):
        """Test HTML generation for digest."""
        from api.services.digest import generate_digest_html
        
        user_name = "Test User"
        clips = [
            {
                "title": "Test Clip",
                "description": "Test Description",
                "source_url": "https://example.com",
                "thumbnail_url": "https://example.com/thumb.jpg"
            }
        ]
        
        html = generate_digest_html(user_name, clips, "weekly")
        
        assert "Test User" in html
        assert "Test Clip" in html
        assert "Test Description" in html
        assert "https://example.com" in html
        assert "weekly" in html
        assert "ClipVault Digest" in html

    def test_generate_digest_html_no_clips(self):
        """Test HTML generation for digest with no clips."""
        from api.services.digest import generate_digest_html
        
        user_name = "Test User"
        clips = []
        
        html = generate_digest_html(user_name, clips, "daily")
        
        assert "Test User" in html
        assert "No clips saved yet" in html
        assert "daily" in html

    def test_get_digest_subject_line(self):
        """Test subject line generation."""
        from api.services.digest import get_digest_subject_line
        
        # Test daily digest
        subject = get_digest_subject_line("daily", 3)
        assert "Daily" in subject
        assert "3" in subject
        
        # Test weekly digest
        subject = get_digest_subject_line("weekly", 5)
        assert "Weekly" in subject
        assert "5" in subject
        
        # Test monthly digest
        subject = get_digest_subject_line("monthly", 10)
        assert "Monthly" in subject
        assert "10" in subject

    def test_format_digest_summary(self):
        """Test digest summary formatting."""
        from api.services.digest import format_digest_summary
        
        clips = [
            {"title": "Clip 1", "source_url": "https://example.com/1"},
            {"title": "Clip 2", "source_url": "https://example.com/2"}
        ]
        
        summary = format_digest_summary(clips)
        
        assert "2 clip(s)" in summary
        assert "Clip 1" in summary
        assert "Clip 2" in summary
        assert "https://example.com/1" in summary
        assert "https://example.com/2" in summary

    def test_format_digest_summary_no_clips(self):
        """Test digest summary formatting with no clips."""
        from api.services.digest import format_digest_summary
        
        summary = format_digest_summary([])
        assert "No clips saved in this period" in summary 