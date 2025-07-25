import pytest
from fastapi.testclient import TestClient
from fastapi import status
from api.main import app
from unittest.mock import AsyncMock
from api.schemas.clips import ClipCreateRequest
from api.services.auth import get_current_user
from api.services.supabase import get_database_service
from api.services.pubsub import get_pubsub_service

client = TestClient(app)

@pytest.fixture
def valid_jwt():
    return "test.jwt.token"

@pytest.fixture
def valid_clip_request():
    return {"source_url": "https://reddit.com/r/testpost", "media_type": "link"}

@pytest.mark.asyncio
async def test_create_clip_success(valid_jwt, valid_clip_request):
    mock_db = AsyncMock()
    mock_db.upsert_clip.return_value = ("clip-uuid", True)
    mock_db.link_user_clip.return_value = True
    mock_pubsub = AsyncMock()
    mock_pubsub.publish_clip_created.return_value = True
    async def mock_get_current_user():
        return {"sub": "user-uuid"}
    async def mock_get_database_service():
        return mock_db
    async def mock_get_pubsub_service():
        return mock_pubsub
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_database_service] = mock_get_database_service
    app.dependency_overrides[get_pubsub_service] = mock_get_pubsub_service
    try:
        response = client.post("/clips", json=valid_clip_request, headers={"Authorization": f"Bearer {valid_jwt}"})
        assert response.status_code == 201
        data = response.json()
        assert data["clip_id"] == "clip-uuid"
        assert data["status"] == "queued"
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_clip_duplicate(valid_jwt, valid_clip_request):
    mock_db = AsyncMock()
    mock_db.upsert_clip.return_value = ("clip-uuid", False)
    mock_db.link_user_clip.return_value = False
    mock_pubsub = AsyncMock()
    mock_pubsub.publish_clip_created.return_value = True
    async def mock_get_current_user():
        return {"sub": "user-uuid"}
    async def mock_get_database_service():
        return mock_db
    async def mock_get_pubsub_service():
        return mock_pubsub
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_database_service] = mock_get_database_service
    app.dependency_overrides[get_pubsub_service] = mock_get_pubsub_service
    try:
        response = client.post("/clips", json=valid_clip_request, headers={"Authorization": f"Bearer {valid_jwt}"})
        assert response.status_code == 409
        assert "Link already saved by user" in response.text
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_clip_unsupported_url(valid_jwt):
    bad_req = {"source_url": "https://notarealwebsite.abc/", "media_type": "link"}
    mock_pubsub = AsyncMock()
    mock_pubsub.publish_clip_created.return_value = True
    async def mock_get_current_user():
        return {"sub": "user-uuid"}
    async def mock_get_pubsub_service():
        return mock_pubsub
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_pubsub_service] = mock_get_pubsub_service
    try:
        response = client.post("/clips", json=bad_req, headers={"Authorization": f"Bearer {valid_jwt}"})
        assert response.status_code == 422  # Pydantic validation error
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_clip_unauthenticated(valid_clip_request):
    app.dependency_overrides.clear()
    response = client.post("/clips", json=valid_clip_request)
    # Accept both 401 and 403 as valid unauthenticated responses
    assert response.status_code in (401, 403) 