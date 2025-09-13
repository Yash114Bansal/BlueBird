"""
Booking API endpoints for Bookings Service.
Handles booking creation, confirmation, cancellation, and management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.api.dependencies import (
    get_current_user_id, 
    get_current_user_role,
    get_authenticated_user,
    get_admin_user,
    validate_booking_ownership,
    check_booking_permissions,
    get_client_ip,
    get_user_agent
)
from app.db.database import get_db
from app.services.booking_service import booking_service
from app.services.availability_service import availability_service
from app.schemas.booking import (
    BookingCreate, 
    BookingCancel,
    BookingResponse, 
    BookingSummaryResponse,
    BookingCreateResponse,
    BookingCancelResponse,
    BookingListResponse,
    BookingQueryParams,
    BookingErrorResponse,
    BookingSuccessResponse,
    PaginatedResponse
)
from app.models.booking import BookingStatus, BookingAuditLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=BookingCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_data: BookingCreate,
    user_info: dict = Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    """
    Create a new booking for an event.
    
    Args:
        booking_data: Booking creation data
        user_info: Authenticated user information
        db: Database session
        
    Returns:
        Created booking details with expiry information
        
    Raises:
        HTTPException: If booking creation fails
    """
    try:
        user_id = user_info["user_id"]
        client_ip = user_info["client_ip"]
        user_agent = user_info["user_agent"]
        
        # Get event price from EventAvailability
        event_price = await booking_service.get_event_price(booking_data.event_id)
        if event_price is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found or not available for booking"
            )
        
        # Create booking with high consistency
        booking, success = await booking_service.create_booking(
            booking_data=booking_data,
            user_id=user_id,
            event_price=event_price,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create booking"
            )
        
        # Convert to response format
        booking_response = BookingResponse.from_orm(booking)
        
        return BookingCreateResponse(
            success=True,
            message="Booking created successfully",
            booking=booking_response,
            expires_at=booking.expires_at
        )
        
    except Exception as e:
        logger.error(f"Booking creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=BookingListResponse)
async def get_user_bookings(
    status_filter: Optional[BookingStatus] = Query(None, description="Filter by booking status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get bookings for the current user with pagination.
    
    Args:
        status_filter: Optional status filter
        page: Page number
        page_size: Number of items per page
        user_id: Current user ID
        db: Database session
        
    Returns:
        Paginated list of user bookings
    """
    try:
        bookings, total = await booking_service.get_user_bookings(
            user_id=user_id,
            status=status_filter,
            page=page,
            page_size=page_size
        )
        
        # Convert to response format
        booking_summaries = [BookingSummaryResponse.from_orm(booking) for booking in bookings]
        
        # Calculate pagination info
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        return BookingListResponse(
            items=booking_summaries,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
    except Exception as e:
        logger.error(f"Failed to get user bookings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bookings"
        )


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: int = Path(..., description="Booking ID"),
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role),
    db: Session = Depends(get_db)
):
    """
    Get a specific booking by ID.
    
    Args:
        booking_id: ID of the booking
        user_id: Current user ID
        user_role: Current user role
        db: Database session
        
    Returns:
        Booking details
        
    Raises:
        HTTPException: If booking not found or access denied
    """
    try:
        is_admin = user_role == "admin"
        booking = await booking_service.get_booking_by_id(
            booking_id=booking_id,
            user_id=user_id,
            is_admin=is_admin
        )
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found or access denied"
            )
        
        return BookingResponse.from_orm(booking)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get booking {booking_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve booking"
        )


@router.put("/{booking_id}/confirm", response_model=BookingSuccessResponse)
async def confirm_booking(
    booking_id: int = Path(..., description="Booking ID"),
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role),
    db: Session = Depends(get_db)
):
    """
    Confirm a pending booking.
    
    Args:
        booking_id: ID of the booking to confirm
        user_id: Current user ID
        user_role: Current user role
        db: Database session
        
    Returns:
        Success response with booking details
        
    Raises:
        HTTPException: If confirmation fails
    """
    try:
        # Check permissions
        is_admin = user_role == "admin"
        if not is_admin:
            # Regular users can only confirm their own bookings
            await validate_booking_ownership(booking_id, user_id, user_role, db)
        
        # Confirm booking
        booking, success = await booking_service.confirm_booking(
            booking_id=booking_id,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to confirm booking"
            )
        
        return BookingSuccessResponse(
            success=True,
            message="Booking confirmed successfully",
            data={"booking_id": booking.id, "status": booking.status.value}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to confirm booking {booking_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{booking_id}/cancel", response_model=BookingCancelResponse)
async def cancel_booking(
    cancel_data: BookingCancel,
    booking_id: int = Path(..., description="Booking ID"),
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role),
    db: Session = Depends(get_db)
):
    """
    Cancel a booking.
    
    Args:
        booking_id: ID of the booking to cancel
        cancel_data: Cancellation information
        user_id: Current user ID
        user_role: Current user role
        db: Database session
        
    Returns:
        Cancellation response with booking details
        
    Raises:
        HTTPException: If cancellation fails
    """
    try:
        # Check permissions
        is_admin = user_role == "admin"
        if not is_admin:
            # Regular users can only cancel their own bookings
            await validate_booking_ownership(booking_id, user_id, user_role, db)
        
        # Cancel booking
        booking, success = await booking_service.cancel_booking(
            booking_id=booking_id,
            cancel_data=cancel_data,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel booking"
            )
        
        booking_response = BookingResponse.from_orm(booking)
        
        return BookingCancelResponse(
            success=True,
            message="Booking cancelled successfully",
            booking=booking_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel booking {booking_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )




@router.get("/{booking_id}/audit", response_model=List[dict])
async def get_booking_audit_log(
    booking_id: int = Path(..., description="Booking ID"),
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role),
    db: Session = Depends(get_db)
):
    """
    Get audit log for a specific booking.
    
    Args:
        booking_id: ID of the booking
        user_id: Current user ID
        user_role: Current user role
        db: Database session
        
    Returns:
        List of audit log entries
        
    Raises:
        HTTPException: If access denied or booking not found
    """
    try:
        # Check permissions
        is_admin = user_role == "admin"
        if not is_admin:
            # Regular users can only see their own booking audit logs
            await validate_booking_ownership(booking_id, user_id, user_role, db)
        
        # Get booking to ensure it exists and user has access
        booking = await booking_service.get_booking_by_id(
            booking_id=booking_id,
            user_id=user_id if not is_admin else None,
            is_admin=is_admin
        )
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found or access denied"
            )
        
        # Get audit logs
        audit_logs = db.query(BookingAuditLog).filter(
            BookingAuditLog.booking_id == booking_id
        ).order_by(BookingAuditLog.changed_at.desc()).all()
        
        return [log.to_dict() for log in audit_logs]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit log for booking {booking_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit log"
        )