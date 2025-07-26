from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, Optional, List
import structlog
from api.schemas.search import SearchRequest, SearchResponse, SearchClip, PaginationInfo
from api.services.supabase import get_database_service, SupabaseDB
from api.services.database import search_clips_for_user
from api.services.auth import get_current_user

router = APIRouter(prefix="/search", tags=["search"])
logger = structlog.get_logger()


@router.get(
    "/",
    response_model=SearchResponse,
    responses={
        200: {"model": SearchResponse},
        400: {"description": "Invalid search parameters"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation error"},
    },
    summary="Search clips by keyword and tags",
    description="Search user's saved clips using full-text search across transcript and summary, with optional tag filtering."
)
async def search_clips(
    q: Optional[str] = Query(None, alias="query", description="Search query for transcript and summary content"),
    tags: Optional[str] = Query(None, description="Comma-separated list of tag names to filter by"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(40, ge=1, le=100, description="Number of results per page (max 100)"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: SupabaseDB = Depends(get_database_service)
):
    """
    Search clips for the authenticated user.
    
    - **q**: Optional search query for full-text search across transcript and summary
    - **tags**: Optional comma-separated list of tag names to filter by
    - **page**: Page number (default: 1)
    - **limit**: Results per page (default: 40, max: 100)
    """
    # Debug logging
    logger.info(f"Search route called with q={q}, tags={tags}, page={page}, limit={limit}")
    
    user_id = current_user.get("sub") or current_user.get("user_id")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User ID not found in JWT claims")
    
    # Parse and validate search parameters
    try:
        # Parse tags from comma-separated string
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            if not tag_list:
                raise ValueError("At least one non-empty tag must be provided")
        
        # Validate query
        if q is not None and len(q.strip()) == 0:
            q = None
        
        # Validate that at least one search criteria is provided
        if not q and not tag_list:
            raise ValueError("At least one search criteria (query or tags) must be provided")
            
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    try:
        # Execute search
        clips, total_count = await search_clips_for_user(
            db=db,
            user_id=user_id,
            query=q,
            tags=tag_list,
            page=page,
            limit=limit
        )
        
        # Build response
        search_clips = []
        for clip_data in clips:
            search_clip = SearchClip(
                clip_id=clip_data["clip_id"],
                source_url=clip_data["source_url"],
                title=clip_data.get("title"),
                description=clip_data.get("description"),
                transcript=clip_data.get("transcript"),
                summary=clip_data.get("summary"),
                created_at=clip_data["created_at"],
                saved_at=clip_data["saved_at"],
                tags=clip_data.get("tags", [])
            )
            search_clips.append(search_clip)
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        pagination = PaginationInfo(
            page=page,
            limit=limit,
            total=total_count,
            has_next=has_next,
            has_prev=has_prev
        )
        
        logger.info(
            "Search completed successfully",
            user_id=user_id,
            query=q,
            tags=tag_list,
            page=page,
            limit=limit,
            total_count=total_count,
            result_count=len(search_clips)
        )
        
        return SearchResponse(clips=search_clips, pagination=pagination)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Search failed",
            error=str(e),
            user_id=user_id,
            query=q,
            tags=tag_list
        )
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search operation failed"
        ) 