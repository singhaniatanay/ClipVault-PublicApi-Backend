import pytest
from fastapi.testclient import TestClient
from fastapi import status
from api.main import app
from unittest.mock import AsyncMock, patch
from api.services.auth import get_current_user
from api.services.supabase import get_database_service
from api.services.database import search_clips_for_user
from datetime import datetime

client = TestClient(app)


@pytest.fixture
def valid_jwt():
    return "test.jwt.token"


@pytest.fixture
def mock_search_results():
    return [
        {
            "clip_id": "19ee20b6-e47d-47a0-9b43-5eb59a187443",
            "source_url": "https://reddit.com/r/testpost",
            "title": "Test Clip Title",
            "description": "Test clip description",
            "transcript": "This is a test transcript with keyword",
            "summary": "Test summary with keyword",
            "created_at": datetime(2024, 1, 1, 12, 0, 0),
            "saved_at": datetime(2024, 1, 1, 12, 15, 0),
            "tags": [
                {"tag_id": "tag-1", "name": "news"},
                {"tag_id": "tag-2", "name": "tech"}
            ]
        }
    ]


def test_search_clips_success(valid_jwt, mock_search_results):
    """Test successful search with keyword query."""
    mock_db = AsyncMock()
    
    def mock_get_current_user():
        return {"sub": "user-uuid"}
    
    def mock_get_database_service():
        return mock_db
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_database_service] = mock_get_database_service
    
    with patch('api.routes.search.search_clips_for_user') as mock_search:
        mock_search.return_value = (mock_search_results, 1)
        
        try:
            response = client.get("/search?query=keyword", headers={"Authorization": f"Bearer {valid_jwt}"})
            if response.status_code != 200:
                print(f"Error response: {response.status_code} - {response.json()}")
            assert response.status_code == 200
            
            data = response.json()
            assert "clips" in data
            assert "pagination" in data
            assert len(data["clips"]) == 1
            assert data["clips"][0]["clip_id"] == "19ee20b6-e47d-47a0-9b43-5eb59a187443"
            assert data["pagination"]["total"] == 1
            assert data["pagination"]["page"] == 1
            assert data["pagination"]["limit"] == 40
            
            # Verify the search was called with correct parameters
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert call_args[1]["user_id"] == "user-uuid"
            assert call_args[1]["query"] == "keyword"
            assert call_args[1]["tags"] is None
            assert call_args[1]["page"] == 1
            assert call_args[1]["limit"] == 40
        finally:
            app.dependency_overrides.clear()


def test_search_clips_with_tags(valid_jwt, mock_search_results):
    """Test successful search with tag filtering."""
    mock_db = AsyncMock()
    
    def mock_get_current_user():
        return {"sub": "user-uuid"}
    
    def mock_get_database_service():
        return mock_db
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_database_service] = mock_get_database_service
    
    with patch('api.routes.search.search_clips_for_user') as mock_search:
        mock_search.return_value = (mock_search_results, 1)
        
        try:
            response = client.get("/search?tags=news,tech", headers={"Authorization": f"Bearer {valid_jwt}"})
            assert response.status_code == 200
            
            data = response.json()
            assert len(data["clips"]) == 1
            
            # Verify the search was called with correct parameters
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert call_args[1]["user_id"] == "user-uuid"
            assert call_args[1]["query"] is None
            assert call_args[1]["tags"] == ["news", "tech"]
            assert call_args[1]["page"] == 1
            assert call_args[1]["limit"] == 40
        finally:
            app.dependency_overrides.clear()


def test_search_clips_with_keyword_and_tags(valid_jwt, mock_search_results):
    """Test successful search with both keyword and tags."""
    mock_db = AsyncMock()
    
    def mock_get_current_user():
        return {"sub": "user-uuid"}
    
    def mock_get_database_service():
        return mock_db
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_database_service] = mock_get_database_service
    
    with patch('api.routes.search.search_clips_for_user') as mock_search:
        mock_search.return_value = (mock_search_results, 1)
        
        try:
            response = client.get(
                "/search?query=keyword&tags=news,tech&page=2&limit=20", 
                headers={"Authorization": f"Bearer {valid_jwt}"}
            )
            assert response.status_code == 200
            
            data = response.json()
            assert data["pagination"]["page"] == 2
            assert data["pagination"]["limit"] == 20
            
            # Verify the search was called with correct parameters
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert call_args[1]["user_id"] == "user-uuid"
            assert call_args[1]["query"] == "keyword"
            assert call_args[1]["tags"] == ["news", "tech"]
            assert call_args[1]["page"] == 2
            assert call_args[1]["limit"] == 20
        finally:
            app.dependency_overrides.clear()


def test_search_clips_empty_results(valid_jwt):
    """Test search with no results."""
    mock_db = AsyncMock()
    
    def mock_get_current_user():
        return {"sub": "user-uuid"}
    
    def mock_get_database_service():
        return mock_db
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_database_service] = mock_get_database_service
    
    with patch('api.routes.search.search_clips_for_user') as mock_search:
        mock_search.return_value = ([], 0)
        
        try:
            response = client.get("/search?query=nonexistent", headers={"Authorization": f"Bearer {valid_jwt}"})
            assert response.status_code == 200
            
            data = response.json()
            assert len(data["clips"]) == 0
            assert data["pagination"]["total"] == 0
            assert not data["pagination"]["has_next"]
            assert not data["pagination"]["has_prev"]
        finally:
            app.dependency_overrides.clear()


def test_search_clips_unauthenticated():
    """Test search without authentication."""
    app.dependency_overrides.clear()
    response = client.get("/search?q=keyword")
    assert response.status_code in (401, 403)


def test_search_clips_no_criteria(valid_jwt):
    """Test search without any search criteria."""
    def mock_get_current_user():
        return {"sub": "user-uuid"}
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    try:
        response = client.get("/search", headers={"Authorization": f"Bearer {valid_jwt}"})
        assert response.status_code == 400
        data = response.json()
        assert "At least one search criteria" in data["detail"]
    finally:
        app.dependency_overrides.clear()


def test_search_clips_empty_query(valid_jwt):
    """Test search with empty query string."""
    def mock_get_current_user():
        return {"sub": "user-uuid"}
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    try:
        response = client.get("/search?query=", headers={"Authorization": f"Bearer {valid_jwt}"})
        assert response.status_code == 400
        data = response.json()
        assert "At least one search criteria" in data["detail"]
    finally:
        app.dependency_overrides.clear()


def test_search_clips_empty_tags(valid_jwt):
    """Test search with empty tags."""
    def mock_get_current_user():
        return {"sub": "user-uuid"}
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    try:
        response = client.get("/search?tags=", headers={"Authorization": f"Bearer {valid_jwt}"})
        assert response.status_code == 400
        data = response.json()
        assert "At least one search criteria" in data["detail"]
    finally:
        app.dependency_overrides.clear()


def test_search_clips_invalid_page(valid_jwt):
    """Test search with invalid page number."""
    def mock_get_current_user():
        return {"sub": "user-uuid"}
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    try:
        response = client.get("/search?query=keyword&page=0", headers={"Authorization": f"Bearer {valid_jwt}"})
        assert response.status_code == 422  # Validation error
    finally:
        app.dependency_overrides.clear()


def test_search_clips_invalid_limit(valid_jwt):
    """Test search with invalid limit."""
    def mock_get_current_user():
        return {"sub": "user-uuid"}
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    try:
        response = client.get("/search?query=keyword&limit=101", headers={"Authorization": f"Bearer {valid_jwt}"})
        assert response.status_code == 422  # Validation error
    finally:
        app.dependency_overrides.clear()


def test_search_clips_pagination(valid_jwt):
    """Test search pagination with multiple results."""
    mock_db = AsyncMock()
    
    def mock_get_current_user():
        return {"sub": "user-uuid"}
    
    def mock_get_database_service():
        return mock_db
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_database_service] = mock_get_database_service
    
    with patch('api.routes.search.search_clips_for_user') as mock_search:
        # Mock 100 total results, 40 per page
        mock_search.return_value = ([], 100)
        
        try:
            response = client.get("/search?query=keyword&page=2", headers={"Authorization": f"Bearer {valid_jwt}"})
            assert response.status_code == 200
            
            data = response.json()
            assert data["pagination"]["total"] == 100
            assert data["pagination"]["page"] == 2
            assert data["pagination"]["has_next"]  # Should have next page
            assert data["pagination"]["has_prev"]  # Should have previous page
        finally:
            app.dependency_overrides.clear() 