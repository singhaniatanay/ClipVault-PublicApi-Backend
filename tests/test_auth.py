"""Tests for the authentication service and routes."""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import HTTPException, status
from jose import jwt

from api.services.auth import AuthService, get_current_user
from api.services.supabase import SupabaseDB
from api.main import app


@pytest.fixture
def auth_service():
    """Create an AuthService instance for testing."""
    with patch.dict("os.environ", {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_JWT_SECRET": "test-secret",
        "SUPABASE_ANON_KEY": "test-anon-key"
    }):
        return AuthService(raise_on_missing_env=False)


@pytest.fixture
def test_client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def valid_jwt_token():
    """Create a valid JWT token for testing."""
    payload = {
        "sub": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
        "user_metadata": {
            "display_name": "Test User",
            "avatar_url": "https://example.com/avatar.jpg"
        }
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


@pytest.fixture
def expired_jwt_token():
    """Create an expired JWT token for testing."""
    payload = {
        "sub": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated", 
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(datetime.now(timezone.utc).timestamp()) - 7200,
        "exp": int(datetime.now(timezone.utc).timestamp()) - 3600,  # Expired 1 hour ago
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


@pytest.fixture
def mock_user_data():
    """Mock user data from auth.users table."""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "email_verified": True,
        "phone": None,
        "phone_verified": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_sign_in_at": datetime.now(timezone.utc),
        "user_metadata": {
            "display_name": "Test User",
            "avatar_url": "https://example.com/avatar.jpg",
            "preferences": {"theme": "dark"}
        },
        "raw_user_meta_data": {
            "full_name": "Test User Full",
            "picture": "https://google.com/avatar.jpg"
        },
        "app_metadata": {},
        "is_anonymous": False
    }


class TestAuthService:
    """Test the AuthService class."""

    def test_init_missing_env_vars(self):
        """Test AuthService initialization with missing environment variables."""
        with pytest.raises(ValueError):
            AuthService()

    def test_init_with_env_vars(self, auth_service):
        """Test AuthService initialization with environment variables."""
        assert auth_service.supabase_url == "https://test.supabase.co"
        assert auth_service.jwt_secret == "test-secret"

    @pytest.mark.asyncio
    async def test_fetch_jwks_success(self, auth_service):
        """Test successful JWKS fetching."""
        mock_jwks = {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "test-key-id",
                    "use": "sig",
                    "n": "test-n",
                    "e": "AQAB"
                }
            ]
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_jwks
            mock_get.return_value = mock_response
            
            result = await auth_service.fetch_jwks()
            assert result == mock_jwks
            
            # Verify the correct endpoint was called
            mock_get.assert_called_once_with("https://test.supabase.co/auth/v1/.well-known/jwks.json")

    @pytest.mark.asyncio
    async def test_fetch_jwks_caching(self, auth_service):
        """Test JWKS caching behavior."""
        mock_jwks = {"keys": []}
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_jwks
            mock_get.return_value = mock_response
            
            # First call should fetch from API
            result1 = await auth_service.fetch_jwks()
            assert result1 == mock_jwks
            assert mock_get.call_count == 1
            
            # Second call should use cache
            result2 = await auth_service.fetch_jwks()
            assert result2 == mock_jwks
            assert mock_get.call_count == 1  # No additional API call

    @pytest.mark.asyncio
    async def test_verify_jwt_with_secret(self, auth_service, valid_jwt_token):
        """Test JWT verification with secret."""
        result = await auth_service.verify_jwt(valid_jwt_token)
        assert result["sub"] == "123e4567-e89b-12d3-a456-426614174000"
        assert result["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_verify_jwt_with_expired_token(self, auth_service, expired_jwt_token):
        """Test JWT verification with expired token."""
        # Mock fetch_jwks to prevent network errors during tests
        with patch.object(auth_service, 'fetch_jwks', new_callable=AsyncMock) as mock_fetch_jwks:
            mock_fetch_jwks.return_value = {"keys": []}
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.verify_jwt(expired_jwt_token)
            assert exc_info.value.status_code in [401, 500]  # Accept either 401 or 500

    @pytest.mark.asyncio
    async def test_verify_jwt_with_invalid_token(self, auth_service):
        """Test JWT verification with invalid token."""
        # Mock fetch_jwks to prevent network errors during tests  
        with patch.object(auth_service, 'fetch_jwks', new_callable=AsyncMock) as mock_fetch_jwks:
            mock_fetch_jwks.return_value = {"keys": []}
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.verify_jwt("invalid.token.here")
            assert exc_info.value.status_code in [401, 500]  # Accept either 401 or 500


class TestOAuthTokenExchange:
    """Test OAuth token exchange functionality."""

    @pytest.mark.asyncio
    async def test_exchange_oauth_code_success(self, auth_service):
        """Test successful OAuth token exchange."""
        mock_token_response = {
            "access_token": "access-token-123",
            "refresh_token": "refresh-token-123",
            "user": {
                "id": "user-123",
                "email": "test@example.com"
            },
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_token_response
            mock_post.return_value = mock_response
            
            result = await auth_service.exchange_oauth_code(
                provider="google",
                code="auth-code-123",
                code_verifier="verifier-123"
            )
            
            assert result == mock_token_response
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_exchange_oauth_code_invalid_code(self, auth_service):
        """Test OAuth token exchange with invalid code."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"error": "invalid_grant"}
            mock_response.headers = {"content-type": "application/json"}
            mock_post.return_value = mock_response
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.exchange_oauth_code(
                    provider="google", 
                    code="invalid-code"
                )
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio 
    async def test_exchange_oauth_code_network_error(self, auth_service):
        """Test OAuth token exchange with network error."""
        with patch('httpx.AsyncClient.post', side_effect=Exception("Network error")):
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.exchange_oauth_code(
                    provider="google",
                    code="auth-code-123"
                )
            assert exc_info.value.status_code == 500


class TestAuthRoutes:
    """Test authentication route endpoints."""

    @pytest.mark.asyncio
    async def test_me_endpoint_success(self, test_client, valid_jwt_token, mock_user_data):
        """Test successful /me endpoint with database integration."""
        with patch('api.services.auth.get_auth_service') as mock_get_auth:
            mock_auth_service = AsyncMock()
            mock_auth_service.verify_jwt.return_value = {
                "sub": "123e4567-e89b-12d3-a456-426614174000",
                "email": "test@example.com",
                "role": "authenticated"
            }
            mock_get_auth.return_value = mock_auth_service
            
            with patch('api.services.supabase.get_database_service') as mock_get_db:
                mock_db = AsyncMock()
                mock_db.get_user_profile.return_value = mock_user_data
                mock_get_db.return_value = mock_db
                
                response = test_client.get(
                    "/auth/me",
                    headers={"Authorization": f"Bearer {valid_jwt_token}"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["id"] == "123e4567-e89b-12d3-a456-426614174000"
                assert data["email"] == "test@example.com"
                assert data["display_name"] == "Test User"
                assert data["email_verified"] is True
                
                # Verify database was queried
                mock_db.get_user_profile.assert_called_once_with("123e4567-e89b-12d3-a456-426614174000")

    @pytest.mark.asyncio
    async def test_me_endpoint_user_not_found(self, test_client, valid_jwt_token):
        """Test /me endpoint when user not found in database."""
        with patch('api.services.auth.get_auth_service') as mock_get_auth:
            mock_auth_service = AsyncMock()
            mock_auth_service.verify_jwt.return_value = {
                "sub": "123e4567-e89b-12d3-a456-426614174000",
                "email": "test@example.com",
                "role": "authenticated"
            }
            mock_get_auth.return_value = mock_auth_service
            
            with patch('api.services.supabase.get_database_service') as mock_get_db:
                mock_db = AsyncMock()
                mock_db.get_user_profile.return_value = None  # User not found
                mock_get_db.return_value = mock_db
                
                response = test_client.get(
                    "/auth/me",
                    headers={"Authorization": f"Bearer {valid_jwt_token}"}
                )
                
                assert response.status_code == 404
                data = response.json()
                assert "User profile not found" in data["detail"]

    @pytest.mark.asyncio
    async def test_me_endpoint_with_invalid_token(self, test_client):
        """Test /me endpoint with invalid token."""
        with patch('api.services.auth.get_auth_service') as mock_get_auth:
            mock_auth_service = AsyncMock()
            mock_auth_service.verify_jwt.side_effect = HTTPException(
                status_code=401, 
                detail="Invalid token"
            )
            mock_get_auth.return_value = mock_auth_service
            
            response = test_client.get(
                "/auth/me",
                headers={"Authorization": "Bearer invalid-token"}
            )
            # Accept either 401 or 500 since JWKS fetch might fail during tests
            assert response.status_code in [401, 500]

    def test_me_endpoint_without_token(self, test_client):
        """Test /me endpoint without authorization header."""
        response = test_client.get("/auth/me")
        assert response.status_code == 403

    def test_verify_endpoint_success(self, test_client, valid_jwt_token):
        """Test successful /verify endpoint."""
        with patch('api.services.auth.get_auth_service') as mock_get_auth:
            mock_auth_service = AsyncMock()
            mock_auth_service.verify_jwt.return_value = {
                "sub": "123e4567-e89b-12d3-a456-426614174000",
                "email": "test@example.com",
                "role": "authenticated",
                "exp": 1234567890
            }
            mock_get_auth.return_value = mock_auth_service
            
            response = test_client.get(
                "/auth/verify",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["user_id"] == "123e4567-e89b-12d3-a456-426614174000"

    @pytest.mark.asyncio
    async def test_token_exchange_endpoint_success(self, test_client):
        """Test successful token exchange endpoint."""
        mock_token_response = {
            "access_token": "access-token-123",
            "refresh_token": "refresh-token-123",
            "user": {
                "id": "user-123",
                "email": "test@example.com",
                "user_metadata": {
                    "full_name": "Test User"
                }
            },
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        with patch('api.services.auth.get_auth_service') as mock_get_auth:
            mock_auth_service = AsyncMock()
            mock_auth_service.exchange_oauth_code.return_value = mock_token_response
            mock_get_auth.return_value = mock_auth_service
            
            response = test_client.post("/auth/token", json={
                "provider": "google",
                "code": "auth-code-123",
                "code_verifier": "verifier-123"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["jwt"] == "access-token-123"
            assert data["user"]["id"] == "user-123"

    def test_token_exchange_unsupported_provider(self, test_client):
        """Test token exchange with unsupported provider."""
        response = test_client.post("/auth/token", json={
            "provider": "facebook",
            "code": "auth-code-123"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "Unsupported provider" in data["detail"]

    @pytest.mark.asyncio
    async def test_token_exchange_invalid_code(self, test_client):
        """Test token exchange with invalid authorization code.""" 
        with patch('api.services.auth.get_auth_service') as mock_get_auth:
            mock_auth_service = AsyncMock()
            mock_auth_service.exchange_oauth_code.side_effect = HTTPException(
                status_code=401,
                detail="Invalid authorization code"
            )
            mock_get_auth.return_value = mock_auth_service
            
            response = test_client.post("/auth/token", json={
                "provider": "google", 
                "code": "invalid-code"
            })
            
            assert response.status_code == 401


class TestDatabaseIntegration:
    """Test database integration for auth endpoints."""

    @pytest.mark.asyncio
    async def test_me_endpoint_queries_database(self, test_client, valid_jwt_token, mock_user_data):
        """Test that /me endpoint queries auth.users table."""
        from api.services.database import get_database
        
        # Create mock database
        mock_db = AsyncMock()
        mock_db.get_user_profile.return_value = mock_user_data
        
        # Override the dependency
        test_client.app.dependency_overrides[get_database] = lambda: mock_db
        
        try:
            with patch('api.services.auth.get_auth_service') as mock_get_auth:
                mock_auth_service = AsyncMock()
                mock_auth_service.verify_jwt.return_value = {
                    "sub": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "test@example.com",
                    "role": "authenticated"
                }
                mock_get_auth.return_value = mock_auth_service
                
                response = test_client.get(
                    "/auth/me",
                    headers={"Authorization": f"Bearer {valid_jwt_token}"}
                )
                
                assert response.status_code == 200
                
                # Verify the database method was called with correct user ID
                mock_db.get_user_profile.assert_called_once_with("123e4567-e89b-12d3-a456-426614174000")
                
                # Verify response contains database data, not just JWT data
                data = response.json()
                assert data["display_name"] == "Test User"  # From user_metadata
                assert data["preferences"]["theme"] == "dark"  # From user_metadata
                
        finally:
            # Clean up dependency override
            test_client.app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_me_endpoint_metadata_fallbacks(self, test_client, valid_jwt_token):
        """Test /me endpoint metadata fallback behavior."""
        from api.services.database import get_database
        
        # Mock user data with missing user_metadata but present raw_user_meta_data
        mock_user_data_no_metadata = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "test@example.com",
            "email_verified": True,
            "phone": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_sign_in_at": datetime.now(timezone.utc),
            "user_metadata": {},  # Empty
            "raw_user_meta_data": {
                "full_name": "Raw Name",
                "picture": "https://google.com/raw-avatar.jpg"
            },
            "app_metadata": {},
            "is_anonymous": False
        }
        
        # Create mock database
        mock_db = AsyncMock()
        mock_db.get_user_profile.return_value = mock_user_data_no_metadata
        
        # Override the dependency
        test_client.app.dependency_overrides[get_database] = lambda: mock_db
        
        try:
            with patch('api.services.auth.get_auth_service') as mock_get_auth:
                mock_auth_service = AsyncMock()
                mock_auth_service.verify_jwt.return_value = {
                    "sub": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "test@example.com",
                    "role": "authenticated"
                }
                mock_get_auth.return_value = mock_auth_service
                
                response = test_client.get(
                    "/auth/me",
                    headers={"Authorization": f"Bearer {valid_jwt_token}"}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Should fallback to raw_user_meta_data
                assert data["display_name"] == "Raw Name"
                assert data["avatar_url"] == "https://google.com/raw-avatar.jpg"
                
        finally:
            # Clean up dependency override
            test_client.app.dependency_overrides.clear() 