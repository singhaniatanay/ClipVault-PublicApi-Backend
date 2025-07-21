"""Tests for Supabase database service."""

import pytest
import os
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from api.services.supabase import SupabaseDB, get_database_service, init_database_service
from api.services.database import get_database, get_database_with_user
from fastapi import HTTPException


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        "SUPABASE_URL": "https://test-project.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
        "SUPABASE_DB_PASSWORD": "test-db-password"
    }):
        yield


@pytest.fixture
async def db_service(mock_env_vars):
    """Create a database service for testing."""
    return SupabaseDB()


class TestSupabaseDB:
    """Test the SupabaseDB class."""

    def test_initialization_with_env_vars(self, mock_env_vars):
        """Test SupabaseDB initializes correctly with environment variables."""
        db = SupabaseDB()
        assert db.supabase_url == "https://test-project.supabase.co"
        assert db.service_role_key == "test-service-role-key"
        assert db.database_password == "test-db-password"
        assert db.pool is None

    def test_initialization_missing_env_vars(self):
        """Test SupabaseDB raises error when environment variables are missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing required Supabase environment variables"):
                SupabaseDB()

    def test_build_connection_string(self, db_service):
        """Test connection string building from Supabase URL."""
        connection_string = db_service._build_connection_string()
        
        expected = (
            "postgresql://postgres.test-project:test-db-password@"
            "aws-0-us-east-2.pooler.supabase.com:6543/postgres"
        )
        assert connection_string == expected

    @pytest.mark.asyncio
    async def test_initialization_success(self, db_service):
        """Test successful database pool initialization."""
        # Mock asyncpg.create_pool
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_connection.fetchval.return_value = 1
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        with patch('api.services.supabase.asyncpg.create_pool', return_value=mock_pool):
            await db_service.initialize()
            
            assert db_service.pool == mock_pool
            mock_connection.fetchval.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_initialization_failure(self, db_service):
        """Test database initialization failure handling."""
        with patch('api.services.supabase.asyncpg.create_pool', side_effect=Exception("Connection failed")):
            with pytest.raises(HTTPException) as exc_info:
                await db_service.initialize()
            
            assert exc_info.value.status_code == 503
            assert "Database service unavailable" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_close_pool(self, db_service):
        """Test closing database pool."""
        mock_pool = AsyncMock()
        db_service.pool = mock_pool
        
        await db_service.close()
        
        mock_pool.close.assert_called_once()
        assert db_service.pool is None

    def test_ensure_pool_available(self, db_service):
        """Test _ensure_pool when pool is available."""
        mock_pool = MagicMock()
        db_service.pool = mock_pool
        
        result = db_service._ensure_pool()
        assert result == mock_pool

    def test_ensure_pool_not_available(self, db_service):
        """Test _ensure_pool when pool is not initialized."""
        with pytest.raises(HTTPException) as exc_info:
            db_service._ensure_pool()
        
        assert exc_info.value.status_code == 503
        assert "Database connection pool not initialized" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_fetch_one_success(self, db_service):
        """Test successful fetch_one operation."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_row = {"id": 1, "name": "test"}
        mock_connection.fetchrow.return_value = mock_row
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        db_service.pool = mock_pool
        
        result = await db_service.fetch_one("SELECT * FROM test WHERE id = $1", 1, user_id="user123")
        
        assert result == mock_row
        mock_connection.execute.assert_called_once_with(
            "SELECT set_config('request.jwt.claims.sub', $1, true)",
            "user123"
        )

    @pytest.mark.asyncio
    async def test_fetch_one_no_result(self, db_service):
        """Test fetch_one when no result is found."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = None
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        db_service.pool = mock_pool
        
        result = await db_service.fetch_one("SELECT * FROM test WHERE id = $1", 999)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_all_success(self, db_service):
        """Test successful fetch_all operation."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_rows = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
        mock_connection.fetch.return_value = mock_rows
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        db_service.pool = mock_pool
        
        result = await db_service.fetch_all("SELECT * FROM test")
        
        assert result == mock_rows

    @pytest.mark.asyncio
    async def test_execute_success(self, db_service):
        """Test successful execute operation."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "INSERT 0 1"
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        db_service.pool = mock_pool
        
        # Mock the RLS context setting call separately
        mock_connection.execute.side_effect = [None, "INSERT 0 1"]
        
        result = await db_service.execute(
            "INSERT INTO test (name) VALUES ($1)", 
            "test", 
            user_id="user123"
        )
        
        assert result == "INSERT 0 1"

    @pytest.mark.asyncio
    async def test_execute_many_success(self, db_service):
        """Test successful execute_many operation."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        db_service.pool = mock_pool
        
        args_list = [("test1",), ("test2",), ("test3",)]
        
        await db_service.execute_many(
            "INSERT INTO test (name) VALUES ($1)", 
            args_list
        )
        
        mock_connection.executemany.assert_called_once_with(
            "INSERT INTO test (name) VALUES ($1)", 
            args_list
        )

    @pytest.mark.asyncio
    async def test_fetch_val_success(self, db_service):
        """Test successful fetch_val operation."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_connection.fetchval.return_value = 42
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        db_service.pool = mock_pool
        
        result = await db_service.fetch_val("SELECT COUNT(*) FROM test")
        
        assert result == 42

    @pytest.mark.asyncio
    async def test_health_check_success(self, db_service):
        """Test successful health check."""
        mock_pool = MagicMock()  # Use MagicMock for synchronous methods
        mock_pool.get_size.return_value = 5
        mock_pool.get_min_size.return_value = 2
        mock_pool.get_max_size.return_value = 20
        
        db_service.pool = mock_pool
        
        # Mock fetch_val to return 1
        with patch.object(db_service, 'fetch_val', return_value=1):
            result = await db_service.health_check()
        
        assert result["database"] == "healthy"
        assert result["pool_size"] == 5
        assert result["test_query_result"] == 1

    @pytest.mark.asyncio
    async def test_health_check_failure(self, db_service):
        """Test health check failure."""
        db_service.pool = None
        
        result = await db_service.health_check()
        
        assert result["database"] == "unhealthy"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_database_operation_failure(self, db_service):
        """Test database operation failure handling."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_connection.fetchrow.side_effect = Exception("Database error")
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        db_service.pool = mock_pool
        
        with pytest.raises(HTTPException) as exc_info:
            await db_service.fetch_one("SELECT * FROM test")
        
        assert exc_info.value.status_code == 500
        assert "Database query failed" in exc_info.value.detail


class TestDatabaseDependencies:
    """Test FastAPI database dependencies."""

    @pytest.mark.asyncio
    async def test_get_database_dependency(self, mock_env_vars):
        """Test get_database FastAPI dependency."""
        db = await get_database()
        assert isinstance(db, SupabaseDB)

    @pytest.mark.asyncio
    async def test_get_database_with_user_dependency(self, mock_env_vars):
        """Test get_database_with_user FastAPI dependency."""
        from api.services.database import get_database_with_user
        
        # Mock the dependencies
        mock_db = SupabaseDB()
        mock_user = {"sub": "user123", "email": "test@example.com"}
        
        # Test the dependency function directly
        db, user_id = await get_database_with_user(mock_db, mock_user)
        
        assert db == mock_db
        assert user_id == "user123"

    @pytest.mark.asyncio
    async def test_get_database_with_user_missing_id(self, mock_env_vars):
        """Test get_database_with_user when user ID is missing."""
        from api.services.database import get_database_with_user
        
        mock_db = SupabaseDB()
        mock_user = {"email": "test@example.com"}  # Missing sub/user_id
        
        with pytest.raises(ValueError, match="User ID not found in JWT claims"):
            await get_database_with_user(mock_db, mock_user)


class TestDatabaseIntegration:
    """Integration tests for database service."""

    @pytest.mark.asyncio
    async def test_database_service_singleton(self, mock_env_vars):
        """Test that database service is a singleton."""
        db1 = get_database_service()
        db2 = get_database_service()
        
        assert db1 is db2

    @pytest.mark.asyncio
    async def test_init_database_service_success(self, mock_env_vars):
        """Test successful database service initialization."""
        with patch.object(SupabaseDB, 'initialize') as mock_init:
            await init_database_service()
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_database_service_failure(self, mock_env_vars):
        """Test database service initialization failure."""
        with patch.object(SupabaseDB, 'initialize', side_effect=Exception("Init failed")):
            with pytest.raises(Exception, match="Init failed"):
                await init_database_service() 