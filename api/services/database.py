"""Database service dependencies for FastAPI routes."""

from typing import Optional, Tuple, List, Dict, Any
from fastapi import Depends, HTTPException, status

from api.services.supabase import get_database_service, SupabaseDB
from api.services.auth import get_current_user


async def get_database() -> SupabaseDB:
    """FastAPI dependency to get database service."""
    return get_database_service()


async def get_database_with_user(
    db: SupabaseDB = Depends(get_database),
    current_user: dict = Depends(get_current_user)
) -> tuple[SupabaseDB, str]:
    """FastAPI dependency to get database service with authenticated user context."""
    user_id = current_user.get("sub") or current_user.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in JWT claims"
        )
    
    return db, user_id


async def get_database_with_optional_user(
    db: SupabaseDB = Depends(get_database),
    current_user: Optional[dict] = None  # Note: We'll need to implement get_optional_user
) -> tuple[SupabaseDB, Optional[str]]:
    """FastAPI dependency to get database service with optional user context."""
    user_id = None
    if current_user:
        user_id = current_user.get("sub") or current_user.get("user_id")
    
    return db, user_id 

async def upsert_clip(db: SupabaseDB, source_url: str) -> Tuple[str, bool]:
    """Thin interface for upserting a clip, delegates to SupabaseDB."""
    return await db.upsert_clip(source_url)

async def link_user_clip(db: SupabaseDB, user_id: str, clip_id: str) -> bool:
    """Thin interface for linking a user to a clip, delegates to SupabaseDB."""
    return await db.link_user_clip(user_id, clip_id) 

async def get_clip_with_tags_for_user(db: SupabaseDB, user_id: str, clip_id: str):
    """Thin interface for fetching a clip with tags and saved_at for a user."""
    return await db.get_clip_with_tags_for_user(user_id, clip_id)

async def search_clips_for_user(
    db: SupabaseDB, 
    user_id: str, 
    query: Optional[str] = None, 
    tags: Optional[List[str]] = None,
    page: int = 1,
    limit: int = 40
) -> tuple[List[Dict[str, Any]], int]:
    """Thin interface for searching clips for a user with FTS and tag filtering."""
    return await db.search_clips_for_user(user_id, query, tags, page, limit)

# ============================================================================
# Collections Interface Functions
# ============================================================================

async def create_collection(
    db: SupabaseDB, 
    user_id: str, 
    name: str, 
    description: Optional[str] = None,
    is_smart: bool = False,
    rule_json: Optional[Dict[str, Any]] = None,
    is_public: bool = False,
    color_hex: Optional[str] = None
) -> str:
    """Thin interface for creating a collection."""
    return await db.create_collection(user_id, name, description, is_smart, rule_json, is_public, color_hex)

async def get_user_collections(
    db: SupabaseDB, 
    user_id: str, 
    page: int = 1, 
    limit: int = 20,
    include_clips_count: bool = False
) -> tuple[List[Dict[str, Any]], int]:
    """Thin interface for getting user collections with pagination."""
    return await db.get_user_collections(user_id, page, limit, include_clips_count)

async def get_collection_by_id(
    db: SupabaseDB, 
    user_id: str, 
    coll_id: str, 
    include_clips: bool = False,
    page: int = 1,
    limit: int = 20
) -> Optional[Dict[str, Any]]:
    """Thin interface for getting a specific collection by ID."""
    return await db.get_collection_by_id(user_id, coll_id, include_clips, page, limit)

async def update_collection(
    db: SupabaseDB, 
    user_id: str, 
    coll_id: str, 
    update_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Thin interface for updating a collection."""
    return await db.update_collection(user_id, coll_id, update_data)

async def delete_collection(db: SupabaseDB, user_id: str, coll_id: str) -> bool:
    """Thin interface for deleting a collection."""
    return await db.delete_collection(user_id, coll_id)

async def add_clip_to_collection(db: SupabaseDB, user_id: str, coll_id: str, clip_id: str) -> bool:
    """Thin interface for adding a clip to a collection."""
    return await db.add_clip_to_collection(user_id, coll_id, clip_id)

async def remove_clip_from_collection(db: SupabaseDB, user_id: str, coll_id: str, clip_id: str) -> bool:
    """Thin interface for removing a clip from a collection."""
    return await db.remove_clip_from_collection(user_id, coll_id, clip_id) 