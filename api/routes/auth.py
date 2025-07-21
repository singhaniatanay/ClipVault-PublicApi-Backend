"""Authentication routes for ClipVault Public API."""

import os
from typing import Dict, Any
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from api.services.auth import get_current_user, get_user_id, get_user_email, get_auth_service
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
    },
    summary="Get current user profile", 
    description="Retrieve the authenticated user's profile information"
)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)) -> UserProfile:
    """
    Get current authenticated user profile.
    
    Returns the profile information for the currently authenticated user
    based on the JWT token provided in the Authorization header.
    """
    try:
        user_id = get_user_id(current_user)
        user_email = get_user_email(current_user)
        
        logger.info("User profile requested", user_id=user_id, email=user_email)
        
        # Extract user information from JWT claims
        # In a full implementation, this would query the database for complete profile
        from datetime import datetime, timezone
        
        # Handle created_at timestamp (use iat from JWT if available)
        created_at = current_user.get("created_at")
        if not created_at and "iat" in current_user:
            created_at = datetime.fromtimestamp(current_user["iat"], timezone.utc)
        elif not created_at:
            created_at = datetime.now(timezone.utc)
        
        user_profile = UserProfile(
            id=user_id,
            email=user_email,
            email_verified=current_user.get("email_verified", False),
            phone=current_user.get("phone"),
            created_at=created_at,
            updated_at=current_user.get("updated_at"),
            last_sign_in_at=current_user.get("last_sign_in_at"),
            display_name=current_user.get("user_metadata", {}).get("display_name"),
            avatar_url=current_user.get("user_metadata", {}).get("avatar_url"),
            preferences=current_user.get("user_metadata", {}).get("preferences", {})
        )
        
        logger.debug("User profile retrieved successfully", user_id=user_id)
        return user_profile
        
    except Exception as e:
        logger.error("Failed to get user profile", error=str(e), user_claims=current_user)
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