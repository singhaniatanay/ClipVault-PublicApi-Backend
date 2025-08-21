from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from api.schemas.clips import TagModel


class SearchRequest(BaseModel):
    """Search request parameters."""
    q: Optional[str] = Field(None, description="Search query for transcript and summary content")
    tags: Optional[List[str]] = Field(None, description="Filter by tag names")
    page: int = Field(1, ge=1, description="Page number (1-based)")
    limit: int = Field(40, ge=1, le=100, description="Number of results per page (max 100)")

    @field_validator("q")
    @classmethod
    def validate_query(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Search query cannot be empty")
        return v.strip() if v else None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        if v is not None:
            # Remove empty tags and normalize
            tags = [tag.strip() for tag in v if tag.strip()]
            if not tags:
                raise ValueError("At least one non-empty tag must be provided")
            return tags
        return v


class SearchClip(BaseModel):
    """Complete clip model for search results."""
    clip_id: str
    source_url: str
    media_type: str = "link"
    title: Optional[str] = None
    description: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    word_count: Optional[int] = None
    language_code: Optional[str] = "en"
    status: str = "pending"
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # AI Processing fields
    ocr_text: Optional[str] = None
    ocr_regions_count: Optional[int] = None
    ai_category: Optional[str] = None
    ai_extracted_data: Optional[dict] = None
    ai_confidence: Optional[float] = None
    universal_actions: Optional[list] = None
    contact_info: Optional[dict] = None
    locations: Optional[list] = None
    platforms_found: Optional[dict] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_duration_seconds: Optional[float] = None
    ai_model_used: Optional[str] = None
    processing_cost: Optional[float] = None
    ai_description: Optional[str] = None
    # User-specific fields
    saved_at: datetime
    tags: List[TagModel] = Field(default_factory=list)


class PaginationInfo(BaseModel):
    """Pagination metadata."""
    page: int
    limit: int
    total: int
    has_next: bool
    has_prev: bool


class SearchResponse(BaseModel):
    """Search response with paginated results."""
    clips: List[SearchClip]
    pagination: PaginationInfo 