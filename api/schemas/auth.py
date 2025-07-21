"""Authentication-related Pydantic schemas."""

from typing import Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserProfile(BaseModel):
    """User profile response model."""
    id: str = Field(..., description="User ID (UUID)")
    email: Optional[EmailStr] = Field(None, description="User email address")
    email_verified: bool = Field(False, description="Whether email is verified")
    phone: Optional[str] = Field(None, description="User phone number")
    created_at: Union[datetime, str] = Field(..., description="Account creation timestamp")
    updated_at: Optional[Union[datetime, str]] = Field(None, description="Last profile update")
    last_sign_in_at: Optional[Union[datetime, str]] = Field(None, description="Last sign-in timestamp")
    
    @field_validator('created_at', 'updated_at', 'last_sign_in_at', mode='before')
    @classmethod
    def parse_datetime(cls, v):
        """Parse datetime strings to datetime objects."""
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                # If parsing fails, return as-is (will be validated by Pydantic)
                return v
        return v
    
    # App-specific profile fields
    display_name: Optional[str] = Field(None, description="User display name")
    avatar_url: Optional[str] = Field(None, description="Profile picture URL")
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="User preferences")
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class TokenExchangeRequest(BaseModel):
    """Request model for OAuth token exchange."""
    provider: str = Field(..., description="OAuth provider (google, github, etc.)")
    code: str = Field(..., description="Authorization code from OAuth flow")
    code_verifier: Optional[str] = Field(None, description="PKCE code verifier")
    redirect_uri: Optional[str] = Field(None, description="Redirect URI used in OAuth flow")


class TokenResponse(BaseModel):
    """Response model for successful authentication."""
    jwt: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    user: UserProfile = Field(..., description="User profile information")
    expires_in: int = Field(..., description="Token expiry time in seconds")
    token_type: str = Field(default="Bearer", description="Token type")


class AuthError(BaseModel):
    """Authentication error response."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class MeResponse(BaseModel):
    """Response model for /me endpoint."""
    user: UserProfile = Field(..., description="Current user profile")
    session: Dict[str, Any] = Field(..., description="Session information")
    
    
class JWTClaims(BaseModel):
    """JWT token claims model for validation."""
    sub: str = Field(..., description="Subject (user ID)")
    email: Optional[str] = Field(None, description="User email")
    role: str = Field(default="authenticated", description="User role")
    aud: str = Field(..., description="Audience")
    iss: str = Field(..., description="Issuer")
    iat: int = Field(..., description="Issued at timestamp")
    exp: int = Field(..., description="Expiration timestamp")
    
    # Supabase specific claims
    app_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    user_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict) 