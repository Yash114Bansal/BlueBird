"""
Public event endpoints for Events Service.
These endpoints are accessible without authentication.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ...db.database import EventRepository
from ...db.redis_client import CacheManager
from ...schemas.event import EventResponse, EventListResponse
from ..dependencies import get_event_repository, get_cache_manager, get_current_user

router = APIRouter(prefix="/events", tags=["User Events"])


@router.get("/", response_model=EventListResponse)
async def list_events(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: dict = Depends(get_current_user),
    event_repo: EventRepository = Depends(get_event_repository),
    cache_manager: CacheManager = Depends(get_cache_manager)
):
    """
    List events with pagination and optional status filter.
    Requires user authentication.
    
    Args:
        page: Page number
        size: Page size
        status: Optional status filter
        event_repo: Event repository
        cache_manager: Cache manager
        
    Returns:
        Paginated list of events
    """
    try:
        # Check cache first
        cached_events = await cache_manager.get_cached_events_list(page, size, status)
        if cached_events:
            return cached_events
        
        # Calculate pagination
        skip = (page - 1) * size
        
        # Get events from database
        if status:
            events = event_repo.get_all(skip=skip, limit=size, status=status)
            total = event_repo.count(status=status)
        else:
            events = event_repo.get_all(skip=skip, limit=size)
            total = event_repo.count()
        
        # Prepare response
        response = {
            "events": events,
            "total": total,
            "page": page,
            "size": size,
            "has_next": (skip + size) < total,
            "has_prev": page > 1
        }
        
        # Cache the response
        await cache_manager.cache_events_list(response, page, size, status)
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list events: {str(e)}"
        )


@router.get("/upcoming", response_model=EventListResponse)
async def list_upcoming_events(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: dict = Depends(get_current_user),
    event_repo: EventRepository = Depends(get_event_repository),
    cache_manager: CacheManager = Depends(get_cache_manager)
):
    """
    List upcoming published events.
    Requires user authentication.
    
    Args:
        page: Page number
        size: Page size
        event_repo: Event repository
        cache_manager: Cache manager
        
    Returns:
        Paginated list of upcoming events
    """
    try:
        # Check cache first
        cached_events = await cache_manager.get_cached_events_list(page, size, "upcoming")
        if cached_events:
            return cached_events
        
        # Calculate pagination
        skip = (page - 1) * size
        
        # Get upcoming events from database
        events = event_repo.get_upcoming_events(skip=skip, limit=size)
        total = len(events) 
        
        # Prepare response
        response = {
            "events": events,
            "total": total,
            "page": page,
            "size": size,
            "has_next": (skip + size) < total,
            "has_prev": page > 1
        }
        
        # Cache the response
        await cache_manager.cache_events_list(response, page, size, "upcoming")
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list upcoming events: {str(e)}"
        )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    current_user: dict = Depends(get_current_user),
    event_repo: EventRepository = Depends(get_event_repository),
    cache_manager: CacheManager = Depends(get_cache_manager)
):
    """
    Get event by ID.
    Requires user authentication.
    
    Args:
        event_id: Event ID
        event_repo: Event repository
        cache_manager: Cache manager
        
    Returns:
        Event details
        
    Raises:
        HTTPException: If event not found
    """
    try:
        # Check cache first
        cached_event = await cache_manager.get_cached_event_detail(event_id)
        if cached_event:
            return cached_event
        
        # Get event from database
        event = event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        # Cache the event
        await cache_manager.cache_event_detail(event.__dict__, event_id)
        
        return event
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get event: {str(e)}"
        )


@router.get("/{event_id}/capacity")
async def get_event_capacity(
    event_id: int,
    current_user: dict = Depends(get_current_user),
    event_repo: EventRepository = Depends(get_event_repository)
):
    """
    Get event capacity information for booking service.
    Requires user authentication.
    
    Args:
        event_id: Event ID
        event_repo: Event repository
        
    Returns:
        Event capacity information
        
    Raises:
        HTTPException: If event not found
    """
    try:
        # Get event from database
        event = event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        return {
            "event_id": event.id,
            "total_capacity": event.capacity,
            "is_published": event.status == "published",
            "is_upcoming": event.is_upcoming,
            "price": float(event.price)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get event capacity: {str(e)}"
        )