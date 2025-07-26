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

@pytest.mark.asyncio
async def test_get_clip_by_id_success(valid_jwt):
    mock_db = AsyncMock()
    mock_clip = {
        "clip_id": "19ee20b6-e47d-47a0-9b43-5eb59a187443",
        "source_url": "https://reddit.com/r/testpost",
        "transcript": "test transcript",
        "summary": "test summary",
        "created_at": "2024-07-25T12:00:00Z",
        "updated_at": "2024-07-25T12:10:00Z",
        "saved_at": "2024-07-25T12:15:00Z",
        "tags": [
            {"tag_id": "tag-1", "name": "news"},
            {"tag_id": "tag-2", "name": "reddit"}
        ]
    }
    mock_db.get_clip_with_tags_for_user.return_value = mock_clip
    async def mock_get_current_user():
        return {"sub": "user-uuid"}
    async def mock_get_database_service():
        return mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_database_service] = mock_get_database_service
    try:
        response = client.get("/clips/19ee20b6-e47d-47a0-9b43-5eb59a187443", headers={"Authorization": f"Bearer {valid_jwt}"})
        assert response.status_code == 200
        data = response.json()
        assert data["clip"]["clip_id"] == "19ee20b6-e47d-47a0-9b43-5eb59a187443"
        assert data["clip"]["source_url"] == "https://reddit.com/r/testpost"
        assert data["tags"] == mock_clip["tags"]
        assert data["saved_at"] == mock_clip["saved_at"]
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_get_clip_by_id_not_found(valid_jwt):
    mock_db = AsyncMock()
    mock_db.get_clip_with_tags_for_user.return_value = None
    async def mock_get_current_user():
        return {"sub": "user-uuid"}
    async def mock_get_database_service():
        return mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_database_service] = mock_get_database_service
    try:
        response = client.get("/clips/00000000-0000-0000-0000-000000000000", headers={"Authorization": f"Bearer {valid_jwt}"})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_get_clip_by_id_unauthenticated():
    app.dependency_overrides.clear()
    response = client.get("/clips/19ee20b6-e47d-47a0-9b43-5eb59a187443")
    assert response.status_code in (401, 403)

@pytest.mark.asyncio
async def test_get_clip_by_id_invalid_uuid(valid_jwt):
    async def mock_get_current_user():
        return {"sub": "user-uuid"}
    app.dependency_overrides[get_current_user] = mock_get_current_user
    try:
        response = client.get("/clips/invalid-uuid-format", headers={"Authorization": f"Bearer {valid_jwt}"})
        assert response.status_code == 400
        data = response.json()
        assert "Invalid clip ID format" in data["detail"]
    finally:
        app.dependency_overrides.clear() 