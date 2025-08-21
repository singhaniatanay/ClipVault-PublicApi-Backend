"""Digest-related Pydantic schemas."""

from typing import Optional, Literal
from datetime import time, datetime
from pydantic import BaseModel, Field


class DigestPreferences(BaseModel):
    """Digest preferences model."""
    digest_enabled: bool = True
    digest_cadence: Literal['daily', 'weekly', 'monthly'] = 'weekly'
    digest_time: Optional[time] = Field(default=time(9, 0), description="Time for digest delivery (HH:MM)")
    digest_day: Optional[int] = Field(default=1, ge=1, le=7, description="Day of week for weekly digests (1=Monday, 7=Sunday)")


class DigestPreviewRequest(BaseModel):
    """Request model for digest preview generation."""
    template_type: Literal['daily', 'weekly', 'monthly'] = 'weekly'


class DigestPreviewResponse(BaseModel):
    """Response model for digest preview."""
    html_content: str = Field(..., description="Generated HTML content for digest")
    clip_count: int = Field(..., description="Number of clips included in preview")
    preview_date: datetime = Field(..., description="Date/time of preview generation")


class ProfileResponse(BaseModel):
    """User profile response model with digest preferences."""
    user_id: str = Field(..., description="User ID")
    digest_enabled: bool = True
    digest_cadence: str = 'weekly'
    digest_time: Optional[time] = None
    digest_day: Optional[int] = None
    last_digest_sent: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DigestSubscribeRequest(BaseModel):
    """Request model for digest subscription."""
    enabled: bool = Field(..., description="Whether to enable or disable digest subscription")


class DigestSubscribeResponse(BaseModel):
    """Response model for digest subscription."""
    enabled: bool = Field(..., description="Current digest subscription status")
    message: str = Field(..., description="Status message") 