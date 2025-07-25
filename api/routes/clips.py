from fastapi import APIRouter, Depends, HTTPException, status
from api.schemas.clips import ClipCreateRequest, ClipCreateResponse, ClipDuplicateResponse
from api.services.supabase import get_database_service, SupabaseDB
from api.services.database import upsert_clip, link_user_clip
from api.services.pubsub import get_pubsub_service, PubSubService
from api.services.auth import get_current_user
from typing import Dict, Any
import structlog

router = APIRouter()
logger = structlog.get_logger()

@router.post(
    "/clips",
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