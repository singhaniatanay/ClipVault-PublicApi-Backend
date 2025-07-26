"""Supabase Postgres database service for ClipVault Public API."""

import os
import asyncio
import json
from typing import Any, Dict, List, Optional, Union, AsyncContextManager
from contextlib import asynccontextmanager
import asyncpg
import structlog
from fastapi import HTTPException, status

logger = structlog.get_logger()


class SupabaseDB:
    """Supabase PostgreSQL database service with connection pooling and RLS support."""
    
    def __init__(self):
        """Initialize the database service."""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.database_password = os.getenv("SUPABASE_DB_PASSWORD")
        self.pool: Optional[asyncpg.Pool] = None
        
        if not all([self.supabase_url, self.database_password]):
            raise ValueError("Missing required Supabase environment variables for database")
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from Supabase URL."""
        if not self.supabase_url or not self.database_password:
            raise ValueError("SUPABASE_URL and SUPABASE_DB_PASSWORD are required")
            
        # Extract project reference from Supabase URL
        # Format: https://project-ref.supabase.co
        project_ref = self.supabase_url.replace("https://", "").replace(".supabase.co", "")
        
        # Build PostgreSQL connection string using Supabase pooler
        # Supabase uses connection pooling with a specific hostname format
        connection_string = (
            f"postgresql://postgres.{project_ref}:{self.database_password}@"
            f"aws-0-us-east-2.pooler.supabase.com:6543/postgres"
        )
        
        logger.debug("Database connection string built", project_ref=project_ref)
        return connection_string
    
    
    async def initialize(self) -> None:
        """Initialize the database connection pool."""
        try:
            dsn = self._build_connection_string()             # keep your helper
            logger.info("Initializing database connection pool")

            self.pool = await asyncpg.create_pool(
                dsn,                     # <-- pass as DSN
                ssl="require",           # always encrypt
                statement_cache_size=0,  # <-- KEY LINE: disable prepared‑stmt cache
                min_size=2,
                max_size=20,
                max_queries=50_000,
                max_inactive_connection_lifetime=300,
                timeout=30,
                command_timeout=60,
                server_settings={
                    "application_name": "clipvault-api",
                    "timezone": "UTC",
                },
            )

            async with self.pool.acquire() as conn:
                assert await conn.fetchval("SELECT 1") == 1

            logger.info("Database connection pool initialized")

        except Exception as e:
            logger.error("Database init failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable",
            )

    
    async def close(self) -> None:
        """Close the database connection pool."""
        if self.pool:
            logger.info("Closing database connection pool")
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")
    
    def _ensure_pool(self) -> asyncpg.Pool:
        """Ensure database pool is available."""
        if not self.pool:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection pool not initialized"
            )
        return self.pool
    
    @asynccontextmanager
    async def _get_connection(self, user_id: Optional[str] = None) -> AsyncContextManager[asyncpg.Connection]:
        """Get database connection with optional RLS user context."""
        pool = self._ensure_pool()
        
        async with pool.acquire() as conn:
            try:
                # Set RLS user context if provided
                if user_id:
                    await conn.execute(
                        "SELECT set_config('request.jwt.claims.sub', $1, true)",
                        user_id
                    )
                    logger.debug("Set RLS user context", user_id=user_id)
                
                yield conn
                
            except Exception as e:
                logger.error(
                    "Database connection error",
                    error=str(e),
                    user_id=user_id
                )
                raise

    @asynccontextmanager
    async def _get_auth_connection(self) -> AsyncContextManager[asyncpg.Connection]:
        """Get database connection with service role for auth schema access."""
        pool = self._ensure_pool()
        
        async with pool.acquire() as conn:
            try:
                # Note: For auth.users access, we rely on the connection having 
                # appropriate permissions through the service role configured 
                # in the connection string
                logger.debug("Acquired connection for auth schema access")
                yield conn
                
            except Exception as e:
                logger.error("Auth schema connection error", error=str(e))
                raise
    
    async def fetch_one(
        self, 
        query: str, 
        *args, 
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single row from the database."""
        try:
            async with self._get_connection(user_id) as conn:
                row = await conn.fetchrow(query, *args)
                result = dict(row) if row else None
                
                logger.debug(
                    "Database fetch_one executed",
                    query=query[:100],
                    args_count=len(args),
                    has_result=result is not None,
                    user_id=user_id
                )
                
                return result
                
        except Exception as e:
            logger.error(
                "Database fetch_one failed",
                error=str(e),
                query=query[:100],
                user_id=user_id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database query failed"
            )
    
    async def fetch_all(
        self, 
        query: str, 
        *args, 
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch multiple rows from the database."""
        try:
            async with self._get_connection(user_id) as conn:
                rows = await conn.fetch(query, *args)
                results = [dict(row) for row in rows]
                
                logger.debug(
                    "Database fetch_all executed",
                    query=query[:100],
                    args_count=len(args),
                    row_count=len(results),
                    user_id=user_id
                )
                
                return results
                
        except Exception as e:
            logger.error(
                "Database fetch_all failed",
                error=str(e),
                query=query[:100],
                user_id=user_id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database query failed"
            )
    
    async def execute(
        self, 
        query: str, 
        *args, 
        user_id: Optional[str] = None
    ) -> str:
        """Execute a query (INSERT/UPDATE/DELETE) and return status."""
        try:
            async with self._get_connection(user_id) as conn:
                status_result = await conn.execute(query, *args)
                
                logger.debug(
                    "Database execute completed",
                    query=query[:100],
                    args_count=len(args),
                    status=status_result,
                    user_id=user_id
                )
                
                return status_result
                
        except Exception as e:
            logger.error(
                "Database execute failed",
                error=str(e),
                query=query[:100],
                user_id=user_id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database operation failed"
            )
    
    async def execute_many(
        self, 
        query: str, 
        args_list: List[tuple], 
        user_id: Optional[str] = None
    ) -> str:
        """Execute a query multiple times with different arguments."""
        try:
            async with self._get_connection(user_id) as conn:
                status_result = await conn.executemany(query, args_list)
                
                logger.debug(
                    "Database execute_many completed",
                    query=query[:100],
                    batch_count=len(args_list),
                    status=status_result,
                    user_id=user_id
                )
                
                return status_result
                
        except Exception as e:
            logger.error(
                "Database execute_many failed",
                error=str(e),
                query=query[:100],
                user_id=user_id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database batch operation failed"
            )
    
    async def fetch_val(
        self, 
        query: str, 
        *args, 
        user_id: Optional[str] = None
    ) -> Any:
        """Fetch a single value from the database."""
        try:
            async with self._get_connection(user_id) as conn:
                result = await conn.fetchval(query, *args)
                
                logger.debug(
                    "Database fetch_val executed",
                    query=query[:100],
                    args_count=len(args),
                    user_id=user_id
                )
                
                return result
                
        except Exception as e:
            logger.error(
                "Database fetch_val failed",
                error=str(e),
                query=query[:100],
                user_id=user_id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database query failed"
            )

    # Auth-specific methods for accessing auth.users table
    

    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from auth.users table.
        
        Args:
            user_id: User UUID to fetch profile for
            
        Returns:
            Dict containing user profile data or None if not found
            
        Raises:
            HTTPException: If database query fails
        """
        try:
            logger.debug(
                "Starting user profile fetch",
                user_id=user_id,
                table="auth.users"
            )
            
            async with self._get_auth_connection() as conn:
                # Query all needed columns in one go based on actual Supabase schema
                try:
                    row = await conn.fetchrow(
                        """
                        SELECT id, email, 
                               email_confirmed_at IS NOT NULL as email_verified,
                               phone, 
                               phone_confirmed_at IS NOT NULL as phone_verified,
                               created_at, updated_at, last_sign_in_at,
                               raw_user_meta_data, raw_app_meta_data,
                               is_anonymous
                        FROM auth.users 
                        WHERE id = $1
                        """,
                        user_id
                    )
                    
                    if not row:
                        logger.warning(
                            "User not found in auth.users table",
                            user_id=user_id
                        )
                        return None
                    
                    result = dict(row)
                    
                    # Parse JSON fields if they're strings
                    if result.get("raw_user_meta_data") and isinstance(result["raw_user_meta_data"], str):
                        try:
                            result["raw_user_meta_data"] = json.loads(result["raw_user_meta_data"])
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse raw_user_meta_data as JSON", user_id=user_id)
                            result["raw_user_meta_data"] = {}
                    
                    if result.get("raw_app_meta_data") and isinstance(result["raw_app_meta_data"], str):
                        try:
                            result["raw_app_meta_data"] = json.loads(result["raw_app_meta_data"])
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse raw_app_meta_data as JSON", user_id=user_id)
                            result["raw_app_meta_data"] = {}
                    
                    # Set user_metadata to raw_user_meta_data for compatibility with our UserProfile schema
                    result["user_metadata"] = result.get("raw_user_meta_data", {})
                    
                    logger.debug(
                        "User data fetched successfully",
                        user_id=user_id,
                        has_email=bool(result.get("email")),
                        email_verified=result.get("email_verified"),
                        has_raw_user_metadata=bool(result.get("raw_user_meta_data"))
                    )
                    
                    # Convert UUID objects to strings for Pydantic compatibility
                    if "id" in result and result["id"]:
                        result["id"] = str(result["id"])
                    
                    logger.info(
                        "User profile fetched successfully from auth.users",
                        user_id=user_id,
                        email=result.get("email"),
                        has_metadata=bool(result.get("user_metadata"))
                    )
                    
                    return result
                    
                except Exception as query_error:
                    logger.error(
                        "Failed to execute user profile query",
                        error=str(query_error),
                        user_id=user_id,
                        query_type="unified_query"
                    )
                    raise
                
        except Exception as e:
            logger.error(
                "Failed to fetch user profile from auth.users",
                error=str(e),
                user_id=user_id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user profile"
            )
    
    async def update_user_metadata(
        self, 
        user_id: str, 
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update user metadata in auth.users table.
        
        Args:
            user_id: User's UUID
            metadata: Metadata dictionary to update
            
        Returns:
            bool: True if update successful
        """
        try:
            async with self._get_auth_connection() as conn:
                await conn.execute(
                    """
                    UPDATE auth.users 
                    SET raw_user_meta_data = raw_user_meta_data || $1::jsonb,
                        updated_at = NOW()
                    WHERE id = $2
                    """,
                    json.dumps(metadata),
                    user_id
                )
                
                logger.info(
                    "User metadata updated successfully",
                    user_id=user_id
                )
                
                return True
                
        except Exception as e:
            logger.error(
                "Failed to update user metadata",
                error=str(e),
                user_id=user_id
            )
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health and connection pool status."""
        try:
            pool = self._ensure_pool()
            
            # Test query
            start_time = asyncio.get_event_loop().time()
            result = await self.fetch_val("SELECT 1")
            query_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return {
                "database": "healthy",
                "pool_size": pool.get_size(),
                "pool_min_size": pool.get_min_size(),
                "pool_max_size": pool.get_max_size(),
                "query_time_ms": round(query_time, 2),
                "test_query_result": result
            }
            
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "database": "unhealthy",
                "error": str(e)
            }

    async def upsert_clip(self, source_url: str) -> tuple[str, bool]:
        """
        Insert a new clip if it doesn't exist, or return the existing one.
        Returns (clip_id, is_new).
        """
        sql = """
        INSERT INTO clips (source_url)
        VALUES ($1)
        ON CONFLICT (source_url) DO UPDATE SET source_url = EXCLUDED.source_url
        RETURNING clip_id, (xmax = 0) AS is_new
        """
        try:
            async with self._get_connection() as conn:
                row = await conn.fetchrow(sql, source_url)
                if not row or "clip_id" not in row:
                    logger.error("Failed to upsert clip", source_url=source_url)
                    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upsert clip")
                return str(row["clip_id"]), bool(row["is_new"])
        except Exception as e:
            logger.error("DB error in upsert_clip", error=str(e), source_url=source_url)
            raise

    async def link_user_clip(self, user_id: str, clip_id: str) -> bool:
        """
        Link a user to a clip (user_clips table). Returns True if new, False if already linked.
        """
        sql = """
        INSERT INTO user_clips (owner_uid, clip_id)
        VALUES ($1, $2)
        ON CONFLICT DO NOTHING
        RETURNING owner_uid
        """
        try:
            async with self._get_connection(user_id) as conn:
                row = await conn.fetchrow(sql, user_id, clip_id)
                return row is not None
        except Exception as e:
            logger.error("DB error in link_user_clip", error=str(e), user_id=user_id, clip_id=clip_id)
            raise

    async def get_clip_with_tags_for_user(self, user_id: str, clip_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a clip by ID for a user, including tags and saved_at.
        Returns None if not found or not accessible.
        """
        sql = """
        SELECT c.clip_id, c.source_url, c.transcript, c.summary, c.created_at, c.updated_at,
               uc.saved_at,
               COALESCE(json_agg(json_build_object('tag_id', t.tag_id, 'name', t.name)) FILTER (WHERE t.tag_id IS NOT NULL), '[]') AS tags
        FROM clips c
        JOIN user_clips uc ON uc.clip_id = c.clip_id
        LEFT JOIN clip_tags ct ON ct.clip_id = c.clip_id
        LEFT JOIN tags t ON t.tag_id = ct.tag_id
        WHERE c.clip_id = $1 AND uc.owner_uid = $2
        GROUP BY c.clip_id, c.source_url, c.transcript, c.summary, c.created_at, c.updated_at, uc.saved_at
        """
        try:
            async with self._get_connection(user_id) as conn:
                row = await conn.fetchrow(sql, clip_id, user_id)
                if not row:
                    return None
                result = dict(row)
                # Convert UUID to string for clip_id
                if "clip_id" in result and result["clip_id"]:
                    result["clip_id"] = str(result["clip_id"])
                # Parse tags JSON
                if isinstance(result.get('tags'), str):
                    result['tags'] = json.loads(result['tags'])
                return result
        except Exception as e:
            logger.error("DB error in get_clip_with_tags_for_user", error=str(e), user_id=user_id, clip_id=clip_id)
            raise


# Global instance (lazy initialization)
_db_instance: Optional[SupabaseDB] = None


def get_database_service() -> SupabaseDB:
    """Get or create the global database service instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = SupabaseDB()
    return _db_instance


async def init_database_service() -> None:
    """Initialize the database service on app startup."""
    try:
        logger.info("Initializing database service")
        db_service = get_database_service()
        await db_service.initialize()
        logger.info("Database service initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database service", error=str(e))
        raise


async def shutdown_database_service() -> None:
    """Cleanup database service on app shutdown."""
    global _db_instance
    if _db_instance:
        logger.info("Shutting down database service")
        await _db_instance.close()
        _db_instance = None
        logger.info("Database service shut down successfully") 