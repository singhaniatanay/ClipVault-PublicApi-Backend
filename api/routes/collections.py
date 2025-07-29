"""Collections CRUD endpoints for ClipVault Public API."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from api.services.database import (
    get_database_with_user, 
    create_collection, 
    get_user_collections, 
    get_collection_by_id,
    update_collection,
    delete_collection,
    add_clip_to_collection,
    remove_clip_from_collection
)
from api.schemas.collections import (
    CollectionCreateRequest,
    CollectionUpdateRequest,
    CollectionResponse,
    CollectionListResponse,
    CollectionDetailResponse,
    CollectionClipRequest
)

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("/", response_model=CollectionResponse, status_code=201)
async def create_collection_endpoint(
    request: CollectionCreateRequest,
    db_and_user: tuple = Depends(get_database_with_user)
):
    """Create a new collection."""
    db, user_id = db_and_user
    
    try:
        coll_id = await create_collection(
            db=db,
            user_id=user_id,
            name=request.name,
            description=request.description,
            is_smart=request.is_smart,
            rule_json=request.rule_json,
            is_public=request.is_public,
            color_hex=request.color_hex
        )
        
        # Fetch the created collection to return
        collection = await get_collection_by_id(db, user_id, coll_id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created collection"
            )
        
        return CollectionResponse(**collection)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create collection"
        )


@router.get("/", response_model=CollectionListResponse)
async def list_collections(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    include_clips_count: bool = Query(False, description="Include clip count per collection"),
    db_and_user: tuple = Depends(get_database_with_user)
):
    """Get all collections owned by the authenticated user."""
    db, user_id = db_and_user
    
    try:
        collections, total_count = await get_user_collections(
            db=db,
            user_id=user_id,
            page=page,
            limit=limit,
            include_clips_count=include_clips_count
        )
        
        total_pages = (total_count + limit - 1) // limit
        
        return CollectionListResponse(
            collections=[CollectionResponse(**coll) for coll in collections],
            total_count=total_count,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve collections"
        )


@router.get("/{coll_id}", response_model=CollectionDetailResponse)
async def get_collection(
    coll_id: str,
    include_clips: bool = Query(False, description="Include clips in response"),
    page: int = Query(1, ge=1, description="Page number for clips"),
    limit: int = Query(20, ge=1, le=100, description="Clips per page"),
    db_and_user: tuple = Depends(get_database_with_user)
):
    """Get a specific collection by ID."""
    db, user_id = db_and_user
    
    # Validate UUID format
    try:
        uuid.UUID(coll_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid collection ID format. Must be a valid UUID."
        )
    
    try:
        collection = await get_collection_by_id(
            db=db,
            user_id=user_id,
            coll_id=coll_id,
            include_clips=include_clips,
            page=page,
            limit=limit
        )
        
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found"
            )
        
        # Build response
        response_data = {
            "collection": CollectionResponse(**collection)
        }
        
        if include_clips and "clips" in collection:
            from api.schemas.collections import CollectionClipInfo
            response_data["clips"] = [CollectionClipInfo(**clip) for clip in collection["clips"]]
            response_data["total_clips"] = collection.get("total_clips", 0)
        
        return CollectionDetailResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve collection"
        )


@router.patch("/{coll_id}", response_model=CollectionResponse)
async def update_collection_endpoint(
    coll_id: str,
    request: CollectionUpdateRequest,
    db_and_user: tuple = Depends(get_database_with_user)
):
    """Update a collection."""
    db, user_id = db_and_user
    
    # Validate UUID format
    try:
        uuid.UUID(coll_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid collection ID format. Must be a valid UUID."
        )
    
    try:
        # Filter out None values
        update_data = {k: v for k, v in request.model_dump().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )
        
        collection = await update_collection(
            db=db,
            user_id=user_id,
            coll_id=coll_id,
            update_data=update_data
        )
        
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found"
            )
        
        return CollectionResponse(**collection)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update collection"
        )


@router.delete("/{coll_id}", status_code=204)
async def delete_collection_endpoint(
    coll_id: str,
    db_and_user: tuple = Depends(get_database_with_user)
):
    """Delete a collection."""
    db, user_id = db_and_user
    
    # Validate UUID format
    try:
        uuid.UUID(coll_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid collection ID format. Must be a valid UUID."
        )
    
    try:
        deleted = await delete_collection(
            db=db,
            user_id=user_id,
            coll_id=coll_id
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found"
            )
        
        return JSONResponse(status_code=204, content=None)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete collection"
        )


@router.post("/{coll_id}/clips", status_code=204)
async def add_clip_to_collection_endpoint(
    coll_id: str,
    request: CollectionClipRequest,
    db_and_user: tuple = Depends(get_database_with_user)
):
    """Add a clip to a collection."""
    db, user_id = db_and_user
    
    # Validate UUID format
    try:
        uuid.UUID(coll_id)
        uuid.UUID(str(request.clip_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid collection ID or clip ID format. Must be valid UUIDs."
        )
    
    try:
        added = await add_clip_to_collection(
            db=db,
            user_id=user_id,
            coll_id=coll_id,
            clip_id=str(request.clip_id)
        )
        
        if not added:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add clip to collection"
            )
        
        return JSONResponse(status_code=204, content=None)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add clip to collection"
        )


@router.delete("/{coll_id}/clips/{clip_id}", status_code=204)
async def remove_clip_from_collection_endpoint(
    coll_id: str,
    clip_id: str,
    db_and_user: tuple = Depends(get_database_with_user)
):
    """Remove a clip from a collection."""
    db, user_id = db_and_user
    
    # Validate UUID format
    try:
        uuid.UUID(coll_id)
        uuid.UUID(clip_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid collection ID or clip ID format. Must be valid UUIDs."
        )
    
    try:
        removed = await remove_clip_from_collection(
            db=db,
            user_id=user_id,
            coll_id=coll_id,
            clip_id=clip_id
        )
        
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection or clip not found, or clip not in collection"
            )
        
        return JSONResponse(status_code=204, content=None)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove clip from collection"
        ) 