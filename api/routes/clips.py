from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
import uuid
from api.schemas.clips import ClipCreateRequest, ClipCreateResponse, ClipDuplicateResponse, ClipDetailResponse, ClipModel, TagModel
from api.schemas.search import SearchResponse, SearchClip, PaginationInfo
from api.services.supabase import get_database_service, SupabaseDB
from api.services.database import upsert_clip, link_user_clip, get_clip_with_tags_for_user, search_clips_for_user
from api.services.pubsub import get_pubsub_service, PubSubService
from api.services.auth import get_current_user
from typing import Dict, Any
import structlog

router = APIRouter(prefix="/clips", tags=["clips"])
logger = structlog.get_logger()

@router.post(
    "/",
    response_model=ClipCreateResponse,
    responses={
        201: {"model": ClipCreateResponse},
        409: {"model": ClipDuplicateResponse},
        400: {"description": "Malformed or unsupported URL"},
        401: {"description": "Authentication required"},
    },
    summary="Save a new clip (link)",
    description="Idempotent save of a link and publish a clip.created event if new.",
    status_code=201
)
async def create_clip(
    req: ClipCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: SupabaseDB = Depends(get_database_service),
    pubsub: PubSubService = Depends(get_pubsub_service)
):
    user_id = current_user.get("sub") or current_user.get("user_id")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User ID not found in JWT claims")

    # Upsert the clip (idempotent)
    try:
        clip_id, is_new_clip = await upsert_clip(db, str(req.source_url))
    except HTTPException as e:
        logger.error("Clip upsert failed", error=str(e), url=str(req.source_url), user_id=user_id)
        raise
    except Exception as e:
        logger.error("Unexpected error in upsert_clip", error=str(e), url=str(req.source_url), user_id=user_id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save clip")

    # Link user to clip (idempotent)
    try:
        is_new_user_clip = await link_user_clip(db, user_id, clip_id)
    except Exception as e:
        logger.error("Failed to link user to clip", error=str(e), user_id=user_id, clip_id=clip_id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to link user to clip")

    # If user already saved this clip, return 409
    if not is_new_user_clip:
        logger.info("Duplicate clip save attempt", user_id=user_id, clip_id=clip_id)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Link already saved by user",
            headers={"X-Clip-Id": clip_id}
        )

    # Publish event if this is a new clip (not just a new user-clip link)
    if is_new_clip:
        try:
            await pubsub.publish_clip_created(
                clip_id=clip_id,
                source_url=str(req.source_url),
                user_id=user_id
            )
            logger.info("clip.created event published", clip_id=clip_id, user_id=user_id)
        except Exception as e:
            logger.error("Failed to publish clip.created event", error=str(e), clip_id=clip_id, user_id=user_id)
            # Do not block user on Pub/Sub failure

    logger.info("Clip saved successfully", user_id=user_id, clip_id=clip_id, is_new_clip=is_new_clip)
    return ClipCreateResponse(clip_id=clip_id, status="queued")

@router.get(
    "/",
    response_model=SearchResponse,
    responses={
        200: {"model": SearchResponse},
        401: {"description": "Authentication required"},
    },
    summary="Get all clips for the authenticated user",
    description="Retrieve all clips saved by the authenticated user with pagination."
)
async def get_all_clips(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(40, ge=1, le=100, description="Number of results per page (max 100)"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: SupabaseDB = Depends(get_database_service)
):
    """
    Get all clips for the authenticated user.
    
    - **page**: Page number (default: 1)
    - **limit**: Results per page (default: 40, max: 100)
    """
    user_id = current_user.get("sub") or current_user.get("user_id")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User ID not found in JWT claims")
    
    try:
        # Use search_clips_for_user with no query or tags to get all clips
        clips, total_count = await search_clips_for_user(
            db=db,
            user_id=user_id,
            query=None,
            tags=None,
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
            "All clips retrieved successfully",
            user_id=user_id,
            page=page,
            limit=limit,
            total_count=total_count,
            result_count=len(search_clips)
        )
        
        return SearchResponse(clips=search_clips, pagination=pagination)
        
    except Exception as e:
        logger.error(
            "Failed to get all clips",
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve clips"
        )

@router.get(
    "/{clip_id}",
    response_model=ClipDetailResponse,
    responses={
        200: {"model": ClipDetailResponse},
        400: {"description": "Invalid clip ID format"},
        404: {"description": "Clip not found or not accessible"},
        401: {"description": "Authentication required"},
    },
    summary="Get a clip by ID (with tags and saved_at)",
    description="Fetch a clip, its tags, and the saved_at timestamp for the authenticated user."
)
async def get_clip_by_id(
    clip_id: str = Path(..., description="The ID of the clip to fetch"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: SupabaseDB = Depends(get_database_service)
):
    # Validate UUID format before database query
    try:
        uuid.UUID(clip_id)
    except ValueError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, 
            detail="Invalid clip ID format. Must be a valid UUID."
        )
    
    user_id = current_user.get("sub") or current_user.get("user_id")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User ID not found in JWT claims")
    result = await get_clip_with_tags_for_user(db, user_id, clip_id)
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Clip not found or not accessible")
    # Build response
    clip = ClipModel(
        clip_id=result["clip_id"],
        source_url=result["source_url"],
        transcript=result.get("transcript"),
        summary=result.get("summary"),
        created_at=result["created_at"],
        updated_at=result.get("updated_at")
    )
    tags = [TagModel(**tag) for tag in result.get("tags", [])]
    saved_at = result["saved_at"]
    return ClipDetailResponse(clip=clip, tags=tags, saved_at=saved_at) 