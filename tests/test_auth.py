"""Tests for authentication service and routes."""

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from fastapi import HTTPException
from jose import jwt

from api.main import app
from api.services.auth import AuthService, get_current_user, get_user_id, get_user_email
from api.schemas.auth import UserProfile


# Test client
client = TestClient(app)

# Mock JWT secret for testing
TEST_JWT_SECRET = "test-secret-key-for-testing-only"
TEST_SUPABASE_URL = "https://test-project.supabase.co"


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        "SUPABASE_URL": TEST_SUPABASE_URL,
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
        "SUPABASE_JWT_SECRET": TEST_JWT_SECRET,
        "ENVIRONMENT": "test"
    }):
        yield


@pytest.fixture
def valid_jwt_token():
    """Create a valid JWT token for testing."""
    payload = {
        "sub": "12345678-1234-1234-1234-123456789012",
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "iss": "supabase",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        "email_verified": True,
        "user_metadata": {
            "display_name": "Test User",
            "avatar_url": "https://example.com/avatar.jpg"
        }
    }
    
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture
def expired_jwt_token():
    """Create an expired JWT token for testing."""
    payload = {
        "sub": "12345678-1234-1234-1234-123456789012",
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "iss": "supabase",
        "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
        "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
    }
    
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture
def invalid_jwt_token():
    """Create an invalid JWT token for testing."""
    return "invalid.jwt.token"


class TestAuthService:
    """Test the AuthService class."""

    @pytest.mark.asyncio
    async def test_auth_service_initialization(self, mock_env_vars):
        """Test AuthService initializes correctly with environment variables."""
        auth_service = AuthService()
        
        assert auth_service.supabase_url == TEST_SUPABASE_URL
        assert auth_service.jwt_secret == TEST_JWT_SECRET
        assert auth_service.jwks_cache is None

    def test_auth_service_missing_env_vars(self):
        """Test AuthService raises error when environment variables are missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing required Supabase environment variables"):
                AuthService()

    @pytest.mark.asyncio
    async def test_verify_jwt_with_secret_valid_token(self, mock_env_vars, valid_jwt_token):
        """Test JWT verification with valid token using secret."""
        auth_service = AuthService()
        
        result = await auth_service.verify_jwt(valid_jwt_token)
        
        assert result["sub"] == "12345678-1234-1234-1234-123456789012"
        assert result["email"] == "test@example.com"
        assert result["role"] == "authenticated"

    @pytest.mark.asyncio
    async def test_verify_jwt_with_expired_token(self, mock_env_vars, expired_jwt_token):
        """Test JWT verification fails with expired token."""
        auth_service = AuthService()
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.verify_jwt(expired_jwt_token)
        
        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_jwt_with_invalid_token(self, mock_env_vars, invalid_jwt_token):
        """Test JWT verification fails with invalid token."""
        auth_service = AuthService()
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.verify_jwt(invalid_jwt_token)
        
        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio 
    async def test_fetch_jwks_caching(self, mock_env_vars):
        """Test JWKS fetching and caching."""
        auth_service = AuthService()
        
        # Mock HTTP client response
        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": [{"kid": "test", "kty": "RSA"}]}
        mock_response.raise_for_status.return_value = None
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with patch.object(auth_service, 'get_http_client', return_value=mock_client):
            result = await auth_service.fetch_jwks()
            
            assert result == {"keys": [{"kid": "test", "kty": "RSA"}]}
            assert auth_service.jwks_cache is not None
            mock_client.get.assert_called_once_with(f"{TEST_SUPABASE_URL}/auth/v1/jwks")


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_me_endpoint_without_token(self):
        """Test /auth/me returns 401 without token."""
        response = client.get("/auth/me")
        
        assert response.status_code == 403  # FastAPI HTTPBearer returns 403 for missing auth

    @patch.dict(os.environ, {
        "SUPABASE_URL": TEST_SUPABASE_URL,
        "SUPABASE_JWT_SECRET": TEST_JWT_SECRET
    })
    def test_me_endpoint_with_valid_token(self, valid_jwt_token):
        """Test /auth/me returns user profile with valid token."""
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "12345678-1234-1234-1234-123456789012"
        assert data["email"] == "test@example.com"
        assert data["display_name"] == "Test User"

    @patch.dict(os.environ, {
        "SUPABASE_URL": TEST_SUPABASE_URL,
        "SUPABASE_JWT_SECRET": TEST_JWT_SECRET
    })
    def test_me_endpoint_with_invalid_token(self, invalid_jwt_token):
        """Test /auth/me returns 401 with invalid token."""
        headers = {"Authorization": f"Bearer {invalid_jwt_token}"}
        
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 401

    @patch.dict(os.environ, {
        "SUPABASE_URL": TEST_SUPABASE_URL,
        "SUPABASE_JWT_SECRET": TEST_JWT_SECRET
    })
    def test_verify_endpoint_with_valid_token(self, valid_jwt_token):
        """Test /auth/verify returns token validity info."""
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        
        response = client.get("/auth/verify", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user_id"] == "12345678-1234-1234-1234-123456789012"
        assert data["email"] == "test@example.com"

    def test_token_exchange_endpoint_not_implemented(self):
        """Test /auth/token returns 501 (not implemented yet)."""
        response = client.post("/auth/token", json={
            "provider": "google",
            "code": "test-auth-code"
        })
        
        assert response.status_code == 501


class TestAuthUtilities:
    """Test authentication utility functions."""

    def test_get_user_id_valid(self):
        """Test get_user_id extracts user ID correctly."""
        user = {"sub": "12345678-1234-1234-1234-123456789012"}
        
        result = get_user_id(user)
        
        assert result == "12345678-1234-1234-1234-123456789012"

    def test_get_user_id_missing(self):
        """Test get_user_id raises exception when user ID is missing."""
        user = {"email": "test@example.com"}
        
        with pytest.raises(HTTPException) as exc_info:
            get_user_id(user)
        
        assert exc_info.value.status_code == 401

    def test_get_user_email_valid(self):
        """Test get_user_email extracts email correctly."""
        user = {"email": "test@example.com"}
        
        result = get_user_email(user)
        
        assert result == "test@example.com"

    def test_get_user_email_missing(self):
        """Test get_user_email returns None when email is missing."""
        user = {"sub": "12345678-1234-1234-1234-123456789012"}
        
        result = get_user_email(user)
        
        assert result is None


class TestIntegration:
    """Integration tests for auth flow."""

    def test_ping_endpoint_works(self):
        """Test that basic ping endpoint still works."""
        response = client.get("/ping")
        
        assert response.status_code == 200
        data = response.json()
        assert data["pong"] is True

    def test_root_endpoint_works(self):
        """Test that root endpoint works."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "ClipVault Public API" in data["message"]

    def test_openapi_docs_accessible(self):
        """Test that OpenAPI docs are accessible."""
        response = client.get("/docs")
        
        # Should return HTML page for docs
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @patch.dict(os.environ, {
        "SUPABASE_URL": TEST_SUPABASE_URL,
        "SUPABASE_JWT_SECRET": TEST_JWT_SECRET
    })
    def test_full_auth_flow(self, valid_jwt_token):
        """Test complete authentication flow."""
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        
        # Test verify endpoint
        verify_response = client.get("/auth/verify", headers=headers)
        assert verify_response.status_code == 200
        
        # Test me endpoint 
        me_response = client.get("/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        # Verify consistent user data
        verify_data = verify_response.json()
        me_data = me_response.json()
        assert verify_data["user_id"] == me_data["id"]
        assert verify_data["email"] == me_data["email"] 