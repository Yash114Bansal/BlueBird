"""
Admin event management endpoints for Events Service.
These endpoints require admin authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db.database import EventRepository
from ...db.redis_client import CacheManager
from ...schemas.event import EventCreate, EventUpdate, EventResponse, MessageResponse
from ...services.event_publisher import EventPublisher
from ..dependencies import (
    get_event_repository, get_cache_manager, get_current_admin_user
)

router = APIRouter(prefix="/admin/events", tags=["Admin Events"])


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    current_user: dict = Depends(get_current_admin_user),
    event_repo: EventRepository = Depends(get_event_repository),
    cache_manager: CacheManager = Depends(get_cache_manager)
):
    """
    Create a new event (admin only).
    
    Args:
        event_data: Event creation data
        current_user: Current admin user
        event_repo: Event repository
        cache_manager: Cache manager
        
    Returns:
        Created event
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        # Create event
        event_dict = event_data.dict()
        event_dict["created_by"] = current_user["user_id"]
        
        event = event_repo.create(event_dict)
        
        # Invalidate events list cache
        await cache_manager.delete_pattern("events:list:*")
        
        # Publish event created notification
        event_publisher = EventPublisher(cache_manager)
        await event_publisher.publish_event_created(event)
        
        return event
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    current_user: dict = Depends(get_current_admin_user),
    event_repo: EventRepository = Depends(get_event_repository),
    cache_manager: CacheManager = Depends(get_cache_manager)
):
    """
    Update an event (admin only).
    
    Args:
        event_id: Event ID
        event_data: Event update data
        current_user: Current admin user
        event_repo: Event repository
        cache_manager: Cache manager
        
    Returns:
        Updated event
        
    Raises:
        HTTPException: If event not found or update fails
    """
    try:
        # Check if event exists
        existing_event = event_repo.get_by_id(event_id)
        if not existing_event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        # Update event
        update_data = event_data.dict(exclude_unset=True)
        updated_event = event_repo.update(event_id, update_data)
        
        if not updated_event:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update event"
            )
        
        # Invalidate caches
        await cache_manager.invalidate_event_cache(event_id)
        
        # Publish event updated notification
        event_publisher = EventPublisher(cache_manager)
        await event_publisher.publish_event_updated(updated_event)
        
        return updated_event
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update event: {str(e)}"
        )


@router.delete("/{event_id}", response_model=MessageResponse)
async def delete_event(
    event_id: int,
    current_user: dict = Depends(get_current_admin_user),
    event_repo: EventRepository = Depends(get_event_repository),
    cache_manager: CacheManager = Depends(get_cache_manager)
):
    """
    Delete an event (admin only).
    
    Args:
        event_id: Event ID
        current_user: Current admin user
        event_repo: Event repository
        cache_manager: Cache manager
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If event not found or deletion fails
    """
    try:
        # Check if event exists
        existing_event = event_repo.get_by_id(event_id)
        if not existing_event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        # Delete event
        success = event_repo.delete(event_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete event"
            )
        
        # Invalidate caches
        await cache_manager.invalidate_event_cache(event_id)
        
        # Publish event deleted notification
        event_publisher = EventPublisher(cache_manager)
        await event_publisher.publish_event_deleted(event_id)
        
        return MessageResponse(message="Event deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event: {str(e)}"
        )