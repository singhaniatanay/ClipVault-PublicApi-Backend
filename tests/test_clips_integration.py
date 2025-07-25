import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.services.supabase import SupabaseDB
from api.services.pubsub import PubSubService
from api.services.auth import get_current_user
from api.services.supabase import get_database_service
from api.services.pubsub import get_pubsub_service
from unittest.mock import AsyncMock

client = TestClient(app)

@pytest.mark.asyncio
async def test_clips_post_new_clip():
    mock_db = AsyncMock(spec=SupabaseDB)
    mock_db.upsert_clip.return_value = ("clip-uuid", True)
    mock_db.link_user_clip.return_value = True
    mock_pubsub = AsyncMock(spec=PubSubService)
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
        req = {"source_url": "https://reddit.com/r/testpost", "media_type": "link"}
        response = client.post("/clips", json=req, headers={"Authorization": "Bearer test.jwt.token"})
        assert response.status_code == 201
        assert response.json()["clip_id"] == "clip-uuid"
        assert response.json()["status"] == "queued"
        mock_pubsub.publish_clip_created.assert_awaited_once()
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_clips_post_duplicate_clip():
    mock_db = AsyncMock(spec=SupabaseDB)
    mock_db.upsert_clip.return_value = ("clip-uuid", False)
    mock_db.link_user_clip.return_value = False
    mock_pubsub = AsyncMock(spec=PubSubService)
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
        req = {"source_url": "https://reddit.com/r/testpost", "media_type": "link"}
        response = client.post("/clips", json=req, headers={"Authorization": "Bearer test.jwt.token"})
        assert response.status_code == 409
        assert "Link already saved by user" in response.text
    finally:
        app.dependency_overrides.clear() 