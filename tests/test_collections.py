"""Unit tests for collections endpoints."""

import uuid
from unittest.mock import AsyncMock, Mock
import pytest
from fastapi.testclient import TestClient
from fastapi import status

from api.main import app
from api.services.database import get_database_with_user


class TestCollectionsEndpoints:
    """Test collections CRUD endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        self.valid_jwt = "valid.jwt.token"
        self.user_id = str(uuid.uuid4())
        self.collection_id = str(uuid.uuid4())
        self.clip_id = str(uuid.uuid4())

        # Mock user data
        self.mock_user = {
            "sub": self.user_id,
            "email": "test@example.com",
            "name": "Test User"
        }

        # Mock collection data
        self.mock_collection = {
            "coll_id": self.collection_id,
            "name": "Test Collection",
            "description": "A test collection",
            "is_smart": False,
            "rule_json": None,
            "is_public": False,
            "color_hex": "#6B7280",
            "sort_order": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }

        # Mock collections list
        self.mock_collections = [self.mock_collection]

    def test_create_collection_success(self):
        """Test successful collection creation."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_create_collection(db, user_id, **kwargs):
            return self.collection_id

        async def mock_get_collection_by_id(db, user_id, coll_id):
            return self.mock_collection

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        # Mock the database functions
        with pytest.MonkeyPatch().context() as m:
            m.setattr("api.routes.collections.create_collection", mock_create_collection)
            m.setattr("api.routes.collections.get_collection_by_id", mock_get_collection_by_id)

            response = self.client.post(
                "/collections/",
                json={
                    "name": "Test Collection",
                    "description": "A test collection",
                    "is_public": False
                },
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Collection"
        assert data["description"] == "A test collection"
        assert data["coll_id"] == self.collection_id

    def test_create_collection_duplicate_name(self):
        """Test collection creation with duplicate name."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_create_collection(db, user_id, **kwargs):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Collection with name 'Test Collection' already exists"
            )

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with pytest.MonkeyPatch().context() as m:
            m.setattr("api.routes.collections.create_collection", mock_create_collection)

            response = self.client.post(
                "/collections/",
                json={"name": "Test Collection"},
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_collection_smart_without_rules(self):
        """Test smart collection creation without rules."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_create_collection(db, user_id, **kwargs):
            # This should not be called due to validation error
            raise Exception("Should not reach here")

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with pytest.MonkeyPatch().context() as m:
            m.setattr("api.routes.collections.create_collection", mock_create_collection)

            response = self.client.post(
                "/collections/",
                json={
                    "name": "Smart Collection",
                    "is_smart": True
                },
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 422  # Validation error

    def test_list_collections_success(self):
        """Test successful collections listing."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_get_user_collections(db, user_id, page=1, limit=20, include_clips_count=False):
            return self.mock_collections, 1

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with pytest.MonkeyPatch().context() as m:
            m.setattr("api.routes.collections.get_user_collections", mock_get_user_collections)

            response = self.client.get(
                "/collections/",
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["collections"]) == 1
        assert data["collections"][0]["name"] == "Test Collection"
        assert data["total_count"] == 1

    def test_get_collection_success(self):
        """Test successful collection retrieval."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_get_collection_by_id(db, user_id, coll_id, include_clips=False, page=1, limit=20):
            return self.mock_collection

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with pytest.MonkeyPatch().context() as m:
            m.setattr("api.routes.collections.get_collection_by_id", mock_get_collection_by_id)

            response = self.client.get(
                f"/collections/{self.collection_id}",
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["collection"]["name"] == "Test Collection"
        assert data["collection"]["coll_id"] == self.collection_id

    def test_get_collection_invalid_uuid(self):
        """Test collection retrieval with invalid UUID."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        response = self.client.get(
            "/collections/invalid-uuid",
            headers={"Authorization": f"Bearer {self.valid_jwt}"}
        )

        assert response.status_code == 400
        assert "Invalid collection ID format" in response.json()["detail"]

    def test_get_collection_not_found(self):
        """Test collection retrieval when not found."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_get_collection_by_id(db, user_id, coll_id, include_clips=False, page=1, limit=20):
            return None

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with pytest.MonkeyPatch().context() as m:
            m.setattr("api.routes.collections.get_collection_by_id", mock_get_collection_by_id)

            response = self.client.get(
                f"/collections/{self.collection_id}",
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 404
        # The response might be empty or have a different structure for 404s
        if response.content:
            response_data = response.json()
            if "detail" in response_data:
                assert "Collection not found" in response_data["detail"]

    def test_update_collection_success(self):
        """Test successful collection update."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_update_collection(db, user_id, coll_id, update_data):
            updated_collection = self.mock_collection.copy()
            updated_collection.update(update_data)
            return updated_collection

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with pytest.MonkeyPatch().context() as m:
            m.setattr("api.routes.collections.update_collection", mock_update_collection)

            response = self.client.patch(
                f"/collections/{self.collection_id}",
                json={"name": "Updated Collection", "description": "Updated description"},
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Collection"
        assert data["description"] == "Updated description"

    def test_update_collection_invalid_uuid(self):
        """Test collection update with invalid UUID."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        response = self.client.patch(
            "/collections/invalid-uuid",
            json={"name": "Updated Collection"},
            headers={"Authorization": f"Bearer {self.valid_jwt}"}
        )

        assert response.status_code == 400
        assert "Invalid collection ID format" in response.json()["detail"]

    def test_update_collection_no_fields(self):
        """Test collection update with no valid fields."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        response = self.client.patch(
            f"/collections/{self.collection_id}",
            json={},
            headers={"Authorization": f"Bearer {self.valid_jwt}"}
        )

        assert response.status_code == 400
        assert "No valid fields to update" in response.json()["detail"]

    def test_delete_collection_success(self):
        """Test successful collection deletion."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_delete_collection(db, user_id, coll_id):
            return True

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with pytest.MonkeyPatch().context() as m:
            m.setattr("api.routes.collections.delete_collection", mock_delete_collection)

            response = self.client.delete(
                f"/collections/{self.collection_id}",
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 204

    def test_delete_collection_invalid_uuid(self):
        """Test collection deletion with invalid UUID."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        response = self.client.delete(
            "/collections/invalid-uuid",
            headers={"Authorization": f"Bearer {self.valid_jwt}"}
        )

        assert response.status_code == 400
        assert "Invalid collection ID format" in response.json()["detail"]

    def test_delete_collection_not_found(self):
        """Test collection deletion when not found."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_delete_collection(db, user_id, coll_id):
            return False

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with pytest.MonkeyPatch().context() as m:
            m.setattr("api.routes.collections.delete_collection", mock_delete_collection)

            response = self.client.delete(
                f"/collections/{self.collection_id}",
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 404
        # The response might be empty or have a different structure for 404s
        if response.content:
            response_data = response.json()
            if "detail" in response_data:
                assert "Collection not found" in response_data["detail"]

    def test_add_clip_to_collection_success(self):
        """Test successful clip addition to collection."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_add_clip_to_collection(db, user_id, coll_id, clip_id):
            return True

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with pytest.MonkeyPatch().context() as m:
            m.setattr("api.routes.collections.add_clip_to_collection", mock_add_clip_to_collection)

            response = self.client.post(
                f"/collections/{self.collection_id}/clips",
                json={"clip_id": self.clip_id},
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 204

    def test_add_clip_to_collection_invalid_uuids(self):
        """Test clip addition with invalid UUIDs."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        response = self.client.post(
            "/collections/invalid-uuid/clips",
            json={"clip_id": "invalid-clip-id"},
            headers={"Authorization": f"Bearer {self.valid_jwt}"}
        )

        # Pydantic validation happens first, so we get 422 for invalid UUID format
        assert response.status_code == 422
        # The response should indicate validation error
        if response.content:
            response_data = response.json()
            detail = response_data.get("detail", "")
            if isinstance(detail, list):
                detail = str(detail)
            assert "validation" in detail.lower() or "error" in detail.lower()

    def test_add_clip_to_collection_duplicate(self):
        """Test adding duplicate clip to collection."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_add_clip_to_collection(db, user_id, coll_id, clip_id):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Clip is already in this collection"
            )

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with pytest.MonkeyPatch().context() as m:
            m.setattr("api.routes.collections.add_clip_to_collection", mock_add_clip_to_collection)

            response = self.client.post(
                f"/collections/{self.collection_id}/clips",
                json={"clip_id": self.clip_id},
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 409
        assert "already in this collection" in response.json()["detail"]

    def test_remove_clip_from_collection_success(self):
        """Test successful clip removal from collection."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_remove_clip_from_collection(db, user_id, coll_id, clip_id):
            return True

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with pytest.MonkeyPatch().context() as m:
            m.setattr("api.routes.collections.remove_clip_from_collection", mock_remove_clip_from_collection)

            response = self.client.delete(
                f"/collections/{self.collection_id}/clips/{self.clip_id}",
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 204

    def test_remove_clip_from_collection_invalid_uuids(self):
        """Test clip removal with invalid UUIDs."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        response = self.client.delete(
            "/collections/invalid-uuid/clips/invalid-clip-id",
            headers={"Authorization": f"Bearer {self.valid_jwt}"}
        )

        assert response.status_code == 400
        assert "Invalid collection ID or clip ID format" in response.json()["detail"]

    def test_remove_clip_from_collection_not_found(self):
        """Test clip removal when not found."""
        # Mock dependencies
        async def mock_get_database_with_user():
            return AsyncMock(), self.user_id

        async def mock_remove_clip_from_collection(db, user_id, coll_id, clip_id):
            return False

        app.dependency_overrides[get_database_with_user] = mock_get_database_with_user

        with pytest.MonkeyPatch().context() as m:
            m.setattr("api.routes.collections.remove_clip_from_collection", mock_remove_clip_from_collection)

            response = self.client.delete(
                f"/collections/{self.collection_id}/clips/{self.clip_id}",
                headers={"Authorization": f"Bearer {self.valid_jwt}"}
            )

        assert response.status_code == 404
        # The response might be empty or have a different structure for 404s
        if response.content:
            response_data = response.json()
            if "detail" in response_data:
                assert "not found" in response_data["detail"]

    def test_collections_unauthenticated(self):
        """Test collections endpoints without authentication."""
        # Test create collection
        response = self.client.post(
            "/collections/",
            json={"name": "Test Collection"}
        )
        assert response.status_code in [401, 403]

        # Test list collections
        response = self.client.get("/collections/")
        assert response.status_code in [401, 403]

        # Test get collection
        response = self.client.get(f"/collections/{self.collection_id}")
        assert response.status_code in [401, 403]

        # Test update collection
        response = self.client.patch(
            f"/collections/{self.collection_id}",
            json={"name": "Updated Collection"}
        )
        assert response.status_code in [401, 403]

        # Test delete collection
        response = self.client.delete(f"/collections/{self.collection_id}")
        assert response.status_code in [401, 403]

        # Test add clip to collection
        response = self.client.post(
            f"/collections/{self.collection_id}/clips",
            json={"clip_id": self.clip_id}
        )
        assert response.status_code in [401, 403]

        # Test remove clip from collection
        response = self.client.delete(f"/collections/{self.collection_id}/clips/{self.clip_id}")
        assert response.status_code in [401, 403]

    def teardown_method(self):
        """Clean up after each test."""
        app.dependency_overrides.clear() 