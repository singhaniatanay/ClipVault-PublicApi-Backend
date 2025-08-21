"""Digest routes for ClipVault Public API."""

from typing import Dict, Any
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime

from api.services.auth import get_current_user, get_user_id
from api.services.database import get_database_with_user
from api.services.digest import generate_digest_html
from api.schemas.digest import (
    DigestPreferences,
    DigestPreviewRequest,
    DigestPreviewResponse,
    DigestSubscribeRequest,
    DigestSubscribeResponse,
    ProfileResponse
)

logger = structlog.get_logger()

# Create router for digest endpoints
router = APIRouter(prefix="/digest", tags=["Digest"])


@router.get(
    "/preferences",
    response_model=DigestPreferences,
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "User profile not found"},
    },
    summary="Get user's digest preferences",
    description="Retrieve the authenticated user's digest preferences from their profile"
)
async def get_digest_preferences(
    db, user_id = Depends(get_database_with_user),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> DigestPreferences:
    """Get user's digest preferences."""
    try:
        logger.info("Digest preferences requested", user_id=user_id)
        
        # Get digest preferences from database
        preferences = await db.get_digest_preferences(user_id)
        
        if not preferences:
            # Create default profile if it doesn't exist
            logger.info("Creating default digest profile", user_id=user_id)
            default_prefs = {
                "digest_enabled": True,
                "digest_cadence": "weekly",
                "digest_time": "09:00:00",
                "digest_day": 1
            }
            
            success = await db.create_user_digest_profile(user_id, default_prefs)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create digest profile"
                )
            
            preferences = default_prefs
        
        # Convert time string to time object if needed
        if isinstance(preferences.get("digest_time"), str):
            from datetime import time
            time_str = preferences["digest_time"]
            if len(time_str) == 8:  # HH:MM:SS format
                hour, minute, second = map(int, time_str.split(":"))
                preferences["digest_time"] = time(hour, minute, second)
        
        logger.debug(
            "Digest preferences retrieved",
            user_id=user_id,
            preferences=preferences
        )
        
        return DigestPreferences(**preferences)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get digest preferences",
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve digest preferences"
        )


@router.put(
    "/preferences",
    response_model=DigestPreferences,
    responses={
        401: {"description": "Authentication required"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
    summary="Update user's digest preferences",
    description="Update the authenticated user's digest preferences in their profile"
)
async def update_digest_preferences(
    preferences: DigestPreferences,
    db, user_id = Depends(get_database_with_user),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> DigestPreferences:
    """Update user's digest preferences."""
    try:
        logger.info(
            "Digest preferences update requested",
            user_id=user_id,
            preferences=preferences.model_dump()
        )
        
        # Convert preferences to dict for database update
        prefs_dict = preferences.model_dump()
        
        # Ensure profile exists
        profile = await db.get_user_digest_profile(user_id)
        if not profile:
            # Create profile with new preferences
            success = await db.create_user_digest_profile(user_id, prefs_dict)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create digest profile"
                )
        else:
            # Update existing profile
            success = await db.update_digest_preferences(user_id, prefs_dict)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update digest preferences"
                )
        
        logger.info(
            "Digest preferences updated successfully",
            user_id=user_id
        )
        
        return preferences
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update digest preferences",
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update digest preferences"
        )


@router.get(
    "/preview",
    response_model=DigestPreviewResponse,
    responses={
        401: {"description": "Authentication required"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
    summary="Generate digest preview",
    description="Generate an HTML preview of the user's digest with their latest clips"
)
async def get_digest_preview(
    request: DigestPreviewRequest,
    db, user_id = Depends(get_database_with_user),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> DigestPreviewResponse:
    """Generate HTML preview of digest."""
    try:
        logger.info(
            "Digest preview requested",
            user_id=user_id,
            template_type=request.template_type
        )
        
        # Get user's display name from auth.users
        user_data = await db.get_user_profile(user_id)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Extract display name from user metadata
        user_metadata = user_data.get("user_metadata", {})
        display_name = (
            user_metadata.get("name") or
            user_metadata.get("full_name") or
            user_data.get("email", "User")
        )
        
        # Get latest clips for digest
        clips = await db.get_latest_clips_for_digest(user_id, limit=3)
        
        # Generate HTML content
        html_content = generate_digest_html(
            user_name=display_name,
            clips=clips,
            digest_type=request.template_type
        )
        
        logger.info(
            "Digest preview generated successfully",
            user_id=user_id,
            clip_count=len(clips),
            template_type=request.template_type
        )
        
        return DigestPreviewResponse(
            html_content=html_content,
            clip_count=len(clips),
            preview_date=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to generate digest preview",
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate digest preview"
        )


@router.post(
    "/subscribe",
    response_model=DigestSubscribeResponse,
    responses={
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"},
    },
    summary="Enable digest subscription",
    description="Enable the authenticated user's digest subscription"
)
async def subscribe_to_digest(
    request: DigestSubscribeRequest,
    db, user_id = Depends(get_database_with_user),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> DigestSubscribeResponse:
    """Enable digest subscription."""
    try:
        logger.info(
            "Digest subscription request",
            user_id=user_id,
            enabled=request.enabled
        )
        
        # Update digest preferences
        success = await db.update_digest_preferences(user_id, {
            "digest_enabled": request.enabled
        })
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update digest subscription"
            )
        
        message = "Digest subscription enabled" if request.enabled else "Digest subscription disabled"
        
        logger.info(
            "Digest subscription updated",
            user_id=user_id,
            enabled=request.enabled
        )
        
        return DigestSubscribeResponse(
            enabled=request.enabled,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update digest subscription",
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update digest subscription"
        )


@router.delete(
    "/subscribe",
    response_model=DigestSubscribeResponse,
    responses={
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"},
    },
    summary="Disable digest subscription",
    description="Disable the authenticated user's digest subscription"
)
async def unsubscribe_from_digest(
    db, user_id = Depends(get_database_with_user),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> DigestSubscribeResponse:
    """Disable digest subscription."""
    try:
        logger.info("Digest unsubscription requested", user_id=user_id)
        
        # Update digest preferences to disable
        success = await db.update_digest_preferences(user_id, {
            "digest_enabled": False
        })
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to disable digest subscription"
            )
        
        logger.info("Digest subscription disabled", user_id=user_id)
        
        return DigestSubscribeResponse(
            enabled=False,
            message="Digest subscription disabled"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to disable digest subscription",
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable digest subscription"
        ) 