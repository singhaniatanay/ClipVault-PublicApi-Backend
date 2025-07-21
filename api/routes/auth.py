"""Authentication routes for ClipVault Public API."""

import os
from typing import Dict, Any
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from api.services.auth import get_current_user, get_user_id, get_user_email
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
    
    **Note**: This is a placeholder implementation. Full OAuth integration 
    will be implemented when frontend integration begins.
    """
    # TODO: Implement actual Supabase OAuth token exchange
    # For now, return a placeholder response to satisfy the LLD
    
    logger.info(
        "Token exchange requested", 
        provider=request.provider,
        has_code=bool(request.code),
        has_code_verifier=bool(request.code_verifier)
    )
    
    # Placeholder implementation - will be replaced with actual Supabase integration
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OAuth token exchange not yet implemented. Use direct JWT for testing."
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