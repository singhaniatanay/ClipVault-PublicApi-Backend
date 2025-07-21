"""Supabase Authentication service for ClipVault Public API."""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import httpx
import structlog
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
import asyncio
from functools import lru_cache

logger = structlog.get_logger()

# FastAPI HTTP Bearer security scheme
security = HTTPBearer()

class AuthService:
    """Supabase Authentication service."""
    
    def __init__(self, raise_on_missing_env: bool = True):
        """Initialize the auth service."""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY") 
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
       
        if raise_on_missing_env and not all([self.supabase_url, self.jwt_secret]):
            raise ValueError("Missing required Supabase environment variables")
            
        self.jwks_cache: Optional[Dict] = None
        self.jwks_cache_expiry: Optional[datetime] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        
    async def get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
        
    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def fetch_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Supabase and cache it."""
        try:
            # Check cache first (cache for 1 hour)
            if (self.jwks_cache and self.jwks_cache_expiry and 
                datetime.now(timezone.utc) < self.jwks_cache_expiry):
                return self.jwks_cache
                
            client = await self.get_http_client()
            jwks_url = f"{self.supabase_url}/auth/v1/.well-known/jwks.json"
            
            logger.info("Fetching JWKS from Supabase", url=jwks_url)
            
            response = await client.get(jwks_url)
            response.raise_for_status()
            
            jwks_data = response.json()
            self.jwks_cache = jwks_data
            # Cache for 1 hour
            self.jwks_cache_expiry = datetime.now(timezone.utc).replace(
                hour=datetime.now(timezone.utc).hour + 1
            )
            
            logger.info("JWKS fetched and cached successfully")
            return jwks_data
            
        except Exception as e:
            logger.error("Failed to fetch JWKS", error=str(e))
            # Don't raise HTTPException here - let the caller handle it
            raise e
    
    def get_signing_key(self, token: str, jwks: Dict[str, Any]) -> str:
        """Get the signing key for JWT verification."""
        try:
            # Decode token header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise JWTError("Token missing kid in header")
                
            # Find matching key in JWKS
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    return jwk.construct(key).key
                    
            raise JWTError(f"Unable to find kid '{kid}' in JWKS")
            
        except Exception as e:
            logger.error("Failed to get signing key", error=str(e))
            raise JWTError("Invalid token header")

    async def verify_jwt(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return claims."""
        try:
            # For development, we can use the JWT secret directly
            # In production, we should use JWKS
            
            # Try JWT secret first (simpler for development)
            if self.jwt_secret:
                try:
                    payload = jwt.decode(
                        token,
                        self.jwt_secret,
                        algorithms=["HS256"],
                        audience="authenticated"
                    )
                    logger.debug("JWT verified with secret", sub=payload.get("sub"))
                    return payload
                except JWTError:
                    logger.debug("JWT secret verification failed, trying JWKS")
            
            # Fallback to JWKS verification
            jwks = await self.fetch_jwks()
            signing_key = self.get_signing_key(token, jwks)
            
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience="authenticated"
            )
            
            logger.debug("JWT verified with JWKS", sub=payload.get("sub"))
            return payload
            
        except JWTError as e:
            logger.warning("JWT verification failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error("Unexpected error during JWT verification", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication error"
            )

# Global auth service instance - lazy initialization
_auth_service: Optional[AuthService] = None

def get_auth_service() -> AuthService:
    """Get or create the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """FastAPI dependency to get current authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract token from Bearer scheme
    token = credentials.credentials
    
    # Verify JWT and return user claims
    auth_service = get_auth_service()
    user_claims = await auth_service.verify_jwt(token)
    
    # Add some convenience fields
    user_claims["user_id"] = user_claims.get("sub")
    
    return user_claims

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """FastAPI dependency to get current user if token is provided (optional auth)."""
    if not credentials:
        return None
        
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

# Utility functions for specific user info extraction
def get_user_id(user: Dict[str, Any]) -> str:
    """Extract user ID from user claims."""
    user_id = user.get("sub") or user.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user token - missing user ID"
        )
    return user_id

def get_user_email(user: Dict[str, Any]) -> Optional[str]:
    """Extract user email from user claims."""
    return user.get("email")

def get_user_role(user: Dict[str, Any]) -> str:
    """Extract user role from user claims."""
    return user.get("role", "authenticated")

# Startup and shutdown functions
async def init_auth_service():
    """Initialize auth service on app startup."""
    try:
        logger.info("Initializing auth service")
        # Pre-fetch JWKS on startup (but don't fail if it doesn't work)
        auth_service = get_auth_service()
        try:
            await auth_service.fetch_jwks()
            logger.info("JWKS pre-fetched successfully")
        except Exception as jwks_error:
            logger.warning("JWKS pre-fetch failed, will use JWT secret verification", error=str(jwks_error))
            # This is fine - we can still verify JWTs using the secret
        logger.info("Auth service initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize auth service", error=str(e))
        # Don't fail startup - we can still work with JWT secret verification
        
async def shutdown_auth_service():
    """Cleanup auth service on app shutdown."""
    global _auth_service
    logger.info("Shutting down auth service")
    if _auth_service:
        await _auth_service.close() 