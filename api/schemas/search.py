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
    """Simplified clip model for search results."""
    clip_id: str
    source_url: str
    title: Optional[str] = None
    description: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
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