from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from uuid import UUID


class CollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Collection name")
    description: Optional[str] = Field(None, max_length=500, description="Collection description")
    is_smart: bool = Field(False, description="Whether this is a smart collection with rules")
    rule_json: Optional[Dict[str, Any]] = Field(None, description="Smart collection rules")
    is_public: bool = Field(False, description="Whether this collection is publicly readable")
    color_hex: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="Collection color in hex format")

    @model_validator(mode='after')
    def validate_smart_collection_rules(self):
        if self.is_smart and self.rule_json is None:
            raise ValueError("rule_json is required for smart collections")
        return self


class CollectionUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Collection name")
    description: Optional[str] = Field(None, max_length=500, description="Collection description")
    rule_json: Optional[Dict[str, Any]] = Field(None, description="Smart collection rules")
    is_public: Optional[bool] = Field(None, description="Whether this collection is publicly readable")
    color_hex: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="Collection color in hex format")


class CollectionClipRequest(BaseModel):
    clip_id: UUID = Field(..., description="Clip ID to add to collection")


class CollectionResponse(BaseModel):
    coll_id: str
    name: str
    description: Optional[str] = None
    is_smart: bool
    rule_json: Optional[Dict[str, Any]] = None
    is_public: bool
    color_hex: Optional[str] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class CollectionClipInfo(BaseModel):
    clip_id: str
    source_url: str
    title: Optional[str] = None
    description: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    saved_at: datetime
    added_at: datetime


class CollectionDetailResponse(BaseModel):
    collection: CollectionResponse
    clips: Optional[List[CollectionClipInfo]] = None
    total_clips: Optional[int] = None


class CollectionListResponse(BaseModel):
    collections: List[CollectionResponse]
    total_count: int
    page: int
    limit: int
    total_pages: int 