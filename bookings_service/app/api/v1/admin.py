"""
Admin API endpoints for Bookings Service.
Handles administrative operations for bookings and availability management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.api.dependencies import (
    get_admin_user,
    get_client_ip,
    get_user_agent
)
from app.db.database import get_db
from app.services.booking_service import booking_service
from app.services.availability_service import availability_service
from app.schemas.booking import (
    BookingResponse,
    BookingSummaryResponse,
    BookingListResponse,
    BookingQueryParams,
    BookingStatsResponse,
    BookingSuccessResponse,
    BookingErrorResponse,
    PaginatedResponse
)
from app.models.booking import Booking, BookingStatus, BookingAuditLog
from sqlalchemy import and_

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/bookings", response_model=BookingListResponse)
async def get_all_bookings(
    status_filter: Optional[BookingStatus] = Query(None, description="Filter by booking status"),
    event_id: Optional[int] = Query(None, description="Filter by event ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get all bookings with admin filters (Admin only).
    
    Args:
        status_filter: Optional status filter
        event_id: Optional event ID filter
        user_id: Optional user ID filter
        page: Page number
        page_size: Number of items per page
        admin_user: Admin user information
        db: Database session
        
    Returns:
        Paginated list of all bookings
    """
    try:
        # Build query
        query = db.query(Booking)
        
        # Apply filters
        if status_filter:
            query = query.filter(Booking.status == status_filter)
        
        if event_id:
            query = query.filter(Booking.event_id == event_id)
        
        if user_id:
            query = query.filter(Booking.user_id == user_id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        bookings = query.order_by(Booking.booking_date.desc()).offset(offset).limit(page_size).all()
        
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
        logger.error(f"Failed to get all bookings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bookings"
        )


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
async def get_booking_admin(
    booking_id: int = Path(..., description="Booking ID"),
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific booking by ID (Admin only).
    
    Args:
        booking_id: ID of the booking
        admin_user: Admin user information
        db: Database session
        
    Returns:
        Complete booking details
        
    Raises:
        HTTPException: If booking not found
    """
    try:
        # Get booking (admin can access any booking)
        booking = await booking_service.get_booking_by_id(
            booking_id=booking_id,
            user_id=None,
            is_admin=True
        )
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
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


@router.put("/bookings/{booking_id}/status", response_model=BookingSuccessResponse)
async def update_booking_status(
    booking_id: int = Path(..., description="Booking ID"),
    new_status: BookingStatus = Query(..., description="New booking status"),
    reason: Optional[str] = Query(None, description="Reason for status change"),
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update booking status (Admin only).
    
    Args:
        booking_id: ID of the booking
        new_status: New booking status
        reason: Reason for status change
        admin_user: Admin user information
        db: Database session
        
    Returns:
        Success response
        
    Raises:
        HTTPException: If update fails
    """
    try:
        # Get current booking
        booking = await booking_service.get_booking_by_id(
            booking_id=booking_id,
            user_id=None,
            is_admin=True
        )
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Update status
        old_status = booking.status
        booking.status = new_status
        booking.version += 1
        
        # Create audit log
        audit_log = BookingAuditLog(
            booking_id=booking_id,
            action="ADMIN_STATUS_UPDATE",
            field_name="status",
            old_value=old_status.value,
            new_value=new_status.value,
            changed_by=admin_user["user_id"],
            reason=reason or "Admin status update"
        )
        
        db.add(audit_log)
        db.commit()
        
        return BookingSuccessResponse(
            success=True,
            message=f"Booking status updated to {new_status.value}",
            data={
                "booking_id": booking_id,
                "old_status": old_status.value,
                "new_status": new_status.value
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update booking status {booking_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/bookings/{booking_id}", response_model=BookingSuccessResponse)
async def delete_booking(
    booking_id: int = Path(..., description="Booking ID"),
    reason: Optional[str] = Query(None, description="Reason for deletion"),
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete a booking (Admin only).
    
    Args:
        booking_id: ID of the booking
        reason: Reason for deletion
        admin_user: Admin user information
        db: Database session
        
    Returns:
        Success response
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        # Get current booking
        booking = await booking_service.get_booking_by_id(
            booking_id=booking_id,
            user_id=None,
            is_admin=True
        )
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Create audit log before deletion
        audit_log = BookingAuditLog(
            booking_id=booking_id,
            action="ADMIN_DELETE",
            reason=reason or "Admin deletion"
        )
        
        db.add(audit_log)
        
        # Delete booking (cascade will handle related records)
        db.delete(booking)
        db.commit()
        
        return BookingSuccessResponse(
            success=True,
            message="Booking deleted successfully",
            data={"booking_id": booking_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete booking {booking_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/bookings/stats", response_model=BookingStatsResponse)
async def get_booking_stats(
    period_days: int = Query(30, ge=1, le=365, description="Period in days"),
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get booking statistics (Admin only).
    
    Args:
        period_days: Period in days for statistics
        admin_user: Admin user information
        db: Database session
        
    Returns:
        Booking statistics
        
    Raises:
        HTTPException: If stats retrieval fails
    """
    try:
        from datetime import datetime, timedelta
        
        # Calculate period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Get statistics
        total_bookings = db.query(Booking).filter(
            Booking.booking_date >= start_date
        ).count()
        
        confirmed_bookings = db.query(Booking).filter(
            and_(
                Booking.booking_date >= start_date,
                Booking.status == BookingStatus.CONFIRMED
            )
        ).count()
        
        pending_bookings = db.query(Booking).filter(
            and_(
                Booking.booking_date >= start_date,
                Booking.status == BookingStatus.PENDING
            )
        ).count()
        
        cancelled_bookings = db.query(Booking).filter(
            and_(
                Booking.booking_date >= start_date,
                Booking.status == BookingStatus.CANCELLED
            )
        ).count()
        
        # Calculate revenue
        confirmed_bookings_query = db.query(Booking).filter(
            and_(
                Booking.booking_date >= start_date,
                Booking.status == BookingStatus.CONFIRMED
            )
        )
        
        total_revenue = sum(booking.total_amount for booking in confirmed_bookings_query.all())
        
        # Calculate averages
        average_booking_value = total_revenue / confirmed_bookings if confirmed_bookings > 0 else 0
        conversion_rate = (confirmed_bookings / total_bookings * 100) if total_bookings > 0 else 0
        
        return BookingStatsResponse(
            total_bookings=total_bookings,
            confirmed_bookings=confirmed_bookings,
            pending_bookings=pending_bookings,
            cancelled_bookings=cancelled_bookings,
            total_revenue=float(total_revenue),
            average_booking_value=float(average_booking_value),
            conversion_rate=round(conversion_rate, 2),
            period_start=start_date,
            period_end=end_date
        )
        
    except Exception as e:
        logger.error(f"Failed to get booking stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve booking statistics"
        )


@router.post("/bookings/expire", response_model=BookingSuccessResponse)
async def expire_pending_bookings(
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Manually expire pending bookings (Admin only).
    
    Args:
        admin_user: Admin user information
        db: Database session
        
    Returns:
        Success response with number of expired bookings
        
    Raises:
        HTTPException: If expiry process fails
    """
    try:
        # Run expiry process
        expired_count = await booking_service.expire_pending_bookings()
        
        return BookingSuccessResponse(
            success=True,
            message=f"Expired {expired_count} pending bookings",
            data={"expired_count": expired_count}
        )
        
    except Exception as e:
        logger.error(f"Failed to expire pending bookings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to expire pending bookings"
        )


@router.get("/audit-logs", response_model=List[dict])
async def get_audit_logs(
    booking_id: Optional[int] = Query(None, description="Filter by booking ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page"),
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get audit logs with filters (Admin only).
    
    Args:
        booking_id: Optional booking ID filter
        action: Optional action filter
        user_id: Optional user ID filter
        page: Page number
        page_size: Number of items per page
        admin_user: Admin user information
        db: Database session
        
    Returns:
        List of audit log entries
        
    Raises:
        HTTPException: If audit logs retrieval fails
    """
    try:
        # Build query
        query = db.query(BookingAuditLog)
        
        # Apply filters
        if booking_id:
            query = query.filter(BookingAuditLog.booking_id == booking_id)
        
        if action:
            query = query.filter(BookingAuditLog.action == action)
        
        if user_id:
            query = query.filter(BookingAuditLog.changed_by == user_id)
        
        # Apply pagination
        offset = (page - 1) * page_size
        audit_logs = query.order_by(BookingAuditLog.changed_at.desc()).offset(offset).limit(page_size).all()
        
        return [log.to_dict() for log in audit_logs]
        
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs"
        )