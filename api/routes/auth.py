"""Authentication routes for ClipVault Public API."""

import os
from typing import Dict, Any
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from api.services.auth import get_current_user, get_user_id, get_user_email, get_auth_service
from api.services.database import get_database
from api.schemas.auth import (
    MeResponse, 
    UserProfile, 
    TokenExchangeRequest, 
    TokenResponse,
    AuthError
)

logger = structlog.get_logger()

# Create router for auth endpoints
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/token",
    response_model=TokenResponse,
    responses={
        401: {"model": AuthError, "description": "Invalid authorization code"},
        400: {"model": AuthError, "description": "Bad request"},
    },
    summary="Exchange OAuth code for JWT token",
    description="Exchange OAuth authorization code for Supabase JWT token using PKCE flow"
)
async def exchange_token(request: TokenExchangeRequest) -> TokenResponse:
    """
    Exchange OAuth authorization code for JWT token.
    
    This endpoint handles the OAuth callback by exchanging the authorization code
    for a Supabase session token. Currently supports Google OAuth.
    """
    try:
        logger.info(
            "Token exchange requested", 
            provider=request.provider,
            has_code=bool(request.code),
            has_code_verifier=bool(request.code_verifier)
        )
        
        # Validate provider (currently only support Google)
        if request.provider != "google":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {request.provider}. Currently only 'google' is supported."
            )
        
        # Get auth service
        auth_service = get_auth_service()
        
        # Exchange OAuth code for Supabase session
        token_data = await auth_service.exchange_oauth_code(
            provider=request.provider,
            code=request.code,
            code_verifier=request.code_verifier,
            redirect_uri=request.redirect_uri
        )
        
        # Extract user information from Supabase response
        supabase_user = token_data.get("user", {})
        user_metadata = supabase_user.get("user_metadata", {})
        
        # Build UserProfile from Supabase user data
        user_profile = UserProfile(
            id=supabase_user.get("id"),
            email=supabase_user.get("email"),
            email_verified=supabase_user.get("email_verified", False),
            phone=supabase_user.get("phone"),
            created_at=supabase_user.get("created_at"),
            updated_at=supabase_user.get("updated_at"),
            last_sign_in_at=supabase_user.get("last_sign_in_at"),
            display_name=user_metadata.get("full_name") or user_metadata.get("name"),
            avatar_url=user_metadata.get("avatar_url") or user_metadata.get("picture"),
            preferences=user_metadata.get("preferences", {})
        )
        
        # Build TokenResponse
        response = TokenResponse(
            jwt=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            user=user_profile,
            expires_in=token_data.get("expires_in", 3600),  # Default to 1 hour
            token_type=token_data.get("token_type", "Bearer")
        )
        
        logger.info(
            "OAuth token exchange successful", 
            provider=request.provider,
            user_id=user_profile.id,
            user_email=user_profile.email
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (from auth service)
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during token exchange",
            provider=request.provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token exchange failed due to internal error"
        )


@router.get(
    "/me",
    response_model=UserProfile,
    responses={
        401: {"model": AuthError, "description": "Authentication required"},
        403: {"model": AuthError, "description": "Access forbidden"},
        404: {"model": AuthError, "description": "User not found"},
    },
    summary="Get current user profile", 
    description="Retrieve the authenticated user's profile information from database"
)
async def get_me(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db = Depends(get_database)
) -> UserProfile:
    """
    Get current authenticated user profile.
    
    Returns the profile information for the currently authenticated user
    by querying the auth.users table in the database.
    """
    try:
        user_id = get_user_id(current_user)
        logger.info("User profile requested", user_id=user_id)
        
        # Query auth.users table for complete user profile
        user_data = await db.get_user_profile(user_id)
        
        if not user_data:
            logger.warning("User not found in database", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        logger.debug(
            "Raw user data from database",
            user_id=user_id,
            has_user_metadata=bool(user_data.get("user_metadata"))
        )
        
        # Extract metadata from database fields (Supabase uses raw_user_meta_data)
        user_metadata = user_data.get("user_metadata") or {}  # This is now set to raw_user_meta_data
        raw_metadata = user_data.get("raw_user_meta_data") or {}  # Direct access for fallback
        
        # Build UserProfile from database data with fallbacks
        # Based on actual Supabase schema: raw_user_meta_data contains name, full_name, avatar_url, picture
        display_name = (
            user_metadata.get("name") or           # Supabase stores "name" 
            user_metadata.get("full_name") or      # Also stores "full_name"
            raw_metadata.get("name") or            # Fallback to raw access
            raw_metadata.get("full_name")
        )
        
        avatar_url = (
            user_metadata.get("avatar_url") or     # Supabase stores "avatar_url"
            user_metadata.get("picture") or        # Also stores "picture" 
            raw_metadata.get("avatar_url") or      # Fallback to raw access
            raw_metadata.get("picture")
        )
        
        user_profile = UserProfile(
            id=user_data["id"],
            email=user_data["email"],
            email_verified=user_data.get("email_verified", False),
            phone=user_data.get("phone"),
            created_at=user_data["created_at"],
            updated_at=user_data.get("updated_at"),
            last_sign_in_at=user_data.get("last_sign_in_at"),
            display_name=display_name,
            avatar_url=avatar_url,
            preferences=user_metadata.get("preferences", {})
        )
        
        logger.debug(
            "User profile retrieved from database successfully", 
            user_id=user_id,
            email=user_profile.email,
            has_display_name=bool(user_profile.display_name),
            has_avatar=bool(user_profile.avatar_url)
        )
        
        return user_profile
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        logger.error(
            "Unexpected error retrieving user profile", 
            error=str(e), 
            user_id=get_user_id(current_user) if current_user else None,
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )




# Additional auth utility endpoints

@router.get(
    "/verify",
    summary="Verify JWT token validity",
    description="Verify that the provided JWT token is valid and not expired"
)
async def verify_token(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Verify JWT token validity.
    
    This endpoint can be used by clients to verify that their JWT token
    is still valid without retrieving full user profile information.
    """
    return {
        "valid": True,
        "user_id": get_user_id(current_user),
        "email": get_user_email(current_user),
        "role": current_user.get("role", "authenticated"),
        "expires_at": current_user.get("exp")
    }


# Note: Exception handlers need to be registered on the main FastAPI app, not the router 