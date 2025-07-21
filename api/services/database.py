"""FastAPI dependencies for database service integration."""

from typing import Optional
from fastapi import Depends
from api.services.supabase import get_database_service, SupabaseDB
from api.services.auth import get_current_user, get_optional_user


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
        raise ValueError("User ID not found in JWT claims")
    
    return db, user_id


async def get_database_with_optional_user(
    db: SupabaseDB = Depends(get_database),
    current_user: Optional[dict] = Depends(get_optional_user)
) -> tuple[SupabaseDB, Optional[str]]:
    """FastAPI dependency to get database service with optional user context."""
    user_id = None
    if current_user:
        user_id = current_user.get("sub") or current_user.get("user_id")
    
    return db, user_id 