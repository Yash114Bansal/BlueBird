"""
Availability API endpoints for Bookings Service.
Handles event availability checking and capacity management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.api.dependencies import (
    get_current_user_id, 
    get_authenticated_user,
    get_admin_user,
    get_client_ip,
    get_user_agent
)
from app.db.database import get_db
from app.services.availability_service import availability_service
from app.schemas.booking import (
    EventAvailabilityResponse,
    AvailabilityQueryParams,
    BookingErrorResponse,
    BookingSuccessResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/availability", tags=["availability"])


@router.get("/events/{event_id}", response_model=EventAvailabilityResponse)
async def get_event_availability(
    event_id: int = Path(..., description="Event ID"),
    include_reserved: bool = Query(False, description="Include reserved capacity in response"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get current availability for a specific event.
    
    Args:
        event_id: ID of the event
        include_reserved: Whether to include reserved capacity details
        user_id: Current user ID
        db: Database session
        
    Returns:
        Event availability information
        
    Raises:
        HTTPException: If event not found or access denied
    """
    try:
        # Get availability from service
        availability = await availability_service.get_event_availability(
            event_id=event_id,
            use_cache=True
        )
        
        if not availability:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event availability not found"
            )
        
        # Convert to response format
        availability_response = EventAvailabilityResponse.from_orm(availability)
        
        # Calculate utilization percentage
        if availability.total_capacity > 0:
            utilization = ((availability.reserved_capacity + availability.confirmed_capacity) / 
                          availability.total_capacity) * 100
            availability_response.utilization_percentage = round(utilization, 2)
        
        return availability_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get availability for event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event availability"
        )


@router.get("/events/{event_id}/check", response_model=dict)
async def check_availability(
    event_id: int = Path(..., description="Event ID"),
    quantity: int = Query(..., ge=1, le=10, description="Quantity to check availability for"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Check if requested quantity is available for an event.
    
    Args:
        event_id: ID of the event
        quantity: Quantity to check
        user_id: Current user ID
        db: Database session
        
    Returns:
        Availability check result
        
    Raises:
        HTTPException: If check fails
    """
    try:
        # Check availability
        is_available, availability = await availability_service.check_availability(
            event_id=event_id,
            quantity=quantity
        )
        
        if not availability:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event availability not found"
            )
        
        return {
            "event_id": event_id,
            "requested_quantity": quantity,
            "is_available": is_available,
            "available_capacity": availability.available_capacity,
            "total_capacity": availability.total_capacity,
            "utilization_percentage": availability.utilization_percentage,
            "message": "Available" if is_available else "Insufficient capacity"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check availability for event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check availability"
        )


@router.get("/stats", response_model=dict)
async def get_availability_stats(
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get overall availability statistics (Admin only).
    
    Args:
        admin_user: Admin user information
        db: Database session
        
    Returns:
        Overall availability statistics
        
    Raises:
        HTTPException: If access denied or stats retrieval fails
    """
    try:
        # Get statistics from service
        stats = await availability_service.get_availability_stats()
        
        return {
            "success": True,
            "data": stats,
            "message": "Availability statistics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to get availability stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve availability statistics"
        )


@router.post("/events/{event_id}/capacity", response_model=BookingSuccessResponse)
async def create_event_availability(
    event_id: int = Path(..., description="Event ID"),
    total_capacity: int = Query(..., ge=1, description="Total capacity for the event"),
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create availability record for a new event (Admin only).
    
    Args:
        event_id: ID of the event
        total_capacity: Total capacity for the event
        admin_user: Admin user information
        db: Database session
        
    Returns:
        Success response with created availability details
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        # Create availability record
        availability = await availability_service.create_event_availability(
            event_id=event_id,
            total_capacity=total_capacity
        )
        
        return BookingSuccessResponse(
            success=True,
            message="Event availability created successfully",
            data={
                "event_id": availability.event_id,
                "total_capacity": availability.total_capacity,
                "available_capacity": availability.available_capacity
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to create availability for event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/events/{event_id}/capacity", response_model=BookingSuccessResponse)
async def update_event_capacity(
    event_id: int = Path(..., description="Event ID"),
    new_total_capacity: int = Query(..., ge=1, description="New total capacity"),
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update total capacity for an event (Admin only).
    
    Args:
        event_id: ID of the event
        new_total_capacity: New total capacity
        admin_user: Admin user information
        db: Database session
        
    Returns:
        Success response with updated availability details
        
    Raises:
        HTTPException: If update fails
    """
    try:
        # Update capacity
        success, availability = await availability_service.update_event_capacity(
            event_id=event_id,
            new_total_capacity=new_total_capacity
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event availability not found"
            )
        
        return BookingSuccessResponse(
            success=True,
            message="Event capacity updated successfully",
            data={
                "event_id": availability.event_id,
                "total_capacity": availability.total_capacity,
                "available_capacity": availability.available_capacity,
                "reserved_capacity": availability.reserved_capacity,
                "confirmed_capacity": availability.confirmed_capacity
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update capacity for event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/events/{event_id}/reserve", response_model=dict)
async def reserve_capacity(
    event_id: int = Path(..., description="Event ID"),
    quantity: int = Query(..., ge=1, le=10, description="Quantity to reserve"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Reserve capacity for an event (for testing/admin purposes).
    
    Args:
        event_id: ID of the event
        quantity: Quantity to reserve
        user_id: Current user ID
        db: Database session
        
    Returns:
        Reservation result
        
    Raises:
        HTTPException: If reservation fails
    """
    try:
        # Reserve capacity
        success, availability = await availability_service.reserve_capacity(
            event_id=event_id,
            quantity=quantity,
            timeout_seconds=30
        )
        
        if not success:
            return {
                "success": False,
                "message": "Failed to reserve capacity",
                "available_capacity": availability.available_capacity if availability else 0,
                "reason": "Insufficient capacity or conflict"
            }
        
        return {
            "success": True,
            "message": f"Successfully reserved {quantity} capacity",
            "data": {
                "event_id": event_id,
                "reserved_quantity": quantity,
                "available_capacity": availability.available_capacity,
                "reserved_capacity": availability.reserved_capacity,
                "version": availability.version
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to reserve capacity for event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/events/{event_id}/release", response_model=dict)
async def release_capacity(
    event_id: int = Path(..., description="Event ID"),
    quantity: int = Query(..., ge=1, le=10, description="Quantity to release"),
    capacity_type: str = Query("reserved", regex="^(reserved|confirmed)$", description="Type of capacity to release"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Release capacity for an event (for testing/admin purposes).
    
    Args:
        event_id: ID of the event
        quantity: Quantity to release
        capacity_type: Type of capacity to release (reserved or confirmed)
        user_id: Current user ID
        db: Database session
        
    Returns:
        Release result
        
    Raises:
        HTTPException: If release fails
    """
    try:
        # Release capacity
        success, availability = await availability_service.release_capacity(
            event_id=event_id,
            quantity=quantity,
            capacity_type=capacity_type
        )
        
        if not success:
            return {
                "success": False,
                "message": "Failed to release capacity",
                "reason": "Insufficient capacity to release or conflict"
            }
        
        return {
            "success": True,
            "message": f"Successfully released {quantity} {capacity_type} capacity",
            "data": {
                "event_id": event_id,
                "released_quantity": quantity,
                "capacity_type": capacity_type,
                "available_capacity": availability.available_capacity,
                "reserved_capacity": availability.reserved_capacity,
                "confirmed_capacity": availability.confirmed_capacity,
                "version": availability.version
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to release capacity for event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )