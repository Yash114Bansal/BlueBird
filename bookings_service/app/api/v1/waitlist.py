"""
Waitlist API endpoints for Bookings Service.
Handles waitlist management, joining, and cancellation.
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
    get_client_ip,
    get_user_agent
)
from app.db.database import get_db
from app.services.waitlist_service import waitlist_service
from app.schemas.booking import (
    WaitlistJoin, 
    WaitlistCancel,
    WaitlistEntryResponse, 
    WaitlistSummaryResponse,
    WaitlistJoinResponse,
    WaitlistCancelResponse,
    WaitlistListResponse,
    WaitlistQueryParams,
    WaitlistAuditLogResponse,
    WaitlistStatsResponse,
    WaitlistEligibilityResponse,
    BookingErrorResponse,
    BookingSuccessResponse,
    PaginatedResponse
)
from app.models.booking import WaitlistStatus, WaitlistAuditLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


@router.get("/check/{event_id}", response_model=WaitlistEligibilityResponse)
async def check_waitlist_eligibility(
    event_id: int = Path(..., description="Event ID to check waitlist eligibility for"),
    quantity: int = Query(1, ge=1, le=10, description="Number of tickets requested"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Check if user can join the waitlist for an event.
    
    Args:
        event_id: ID of the event
        quantity: Number of tickets requested
        user_id: Current user ID
        db: Database session
        
    Returns:
        Waitlist eligibility information
        
    Raises:
        HTTPException: If check fails
    """
    try:
        eligibility_info = await waitlist_service.check_waitlist_eligibility(
            event_id=event_id,
            user_id=user_id,
            requested_quantity=quantity
        )
        
        return WaitlistEligibilityResponse(**eligibility_info)
        
    except Exception as e:
        logger.error(f"Failed to check waitlist eligibility: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check waitlist eligibility"
        )


@router.post("/join", response_model=WaitlistJoinResponse, status_code=status.HTTP_201_CREATED)
async def join_waitlist(
    waitlist_data: WaitlistJoin,
    user_info: dict = Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    """
    Join the waitlist for an event.
    
    Args:
        waitlist_data: Waitlist join data
        user_info: Authenticated user information
        db: Database session
        
    Returns:
        Created waitlist entry details with position information
        
    Raises:
        HTTPException: If waitlist join fails
    """
    try:
        user_id = user_info["user_id"]
        client_ip = user_info["client_ip"]
        user_agent = user_info["user_agent"]
        
        # Join waitlist with high consistency
        waitlist_entry, success, position = await waitlist_service.join_waitlist(
            waitlist_data=waitlist_data,
            user_id=user_id,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to join waitlist"
            )
        
        # Convert to response format
        waitlist_response = WaitlistEntryResponse.from_orm(waitlist_entry)
        
        return WaitlistJoinResponse(
            success=True,
            message="Successfully joined waitlist",
            waitlist_entry=waitlist_response,
            estimated_position=position
        )
        
    except Exception as e:
        logger.error(f"Waitlist join failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=WaitlistListResponse)
async def get_user_waitlist_entries(
    status_filter: Optional[WaitlistStatus] = Query(None, description="Filter by waitlist status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get waitlist entries for the current user with pagination.
    
    Args:
        status_filter: Optional status filter
        page: Page number
        page_size: Number of items per page
        user_id: Current user ID
        db: Database session
        
    Returns:
        Paginated list of user waitlist entries
    """
    try:
        entries, total = await waitlist_service.get_user_waitlist_entries(
            user_id=user_id,
            status=status_filter,
            page=page,
            page_size=page_size
        )
        
        # Convert to response format
        waitlist_summaries = [WaitlistSummaryResponse.from_orm(entry) for entry in entries]
        
        # Calculate pagination info
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        return WaitlistListResponse(
            items=waitlist_summaries,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
    except Exception as e:
        logger.error(f"Failed to get user waitlist entries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve waitlist entries"
        )


@router.get("/{waitlist_entry_id}", response_model=WaitlistEntryResponse)
async def get_waitlist_entry(
    waitlist_entry_id: int = Path(..., description="Waitlist entry ID"),
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role),
    db: Session = Depends(get_db)
):
    """
    Get a specific waitlist entry by ID.
    
    Args:
        waitlist_entry_id: ID of the waitlist entry
        user_id: Current user ID
        user_role: Current user role
        db: Database session
        
    Returns:
        Waitlist entry details
        
    Raises:
        HTTPException: If waitlist entry not found or access denied
    """
    try:
        is_admin = user_role == "admin"
        waitlist_entry = await waitlist_service.get_waitlist_entry_by_id(
            waitlist_entry_id=waitlist_entry_id,
            user_id=user_id,
            is_admin=is_admin
        )
        
        if not waitlist_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waitlist entry not found or access denied"
            )
        
        return WaitlistEntryResponse.from_orm(waitlist_entry)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get waitlist entry {waitlist_entry_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve waitlist entry"
        )


@router.put("/{waitlist_entry_id}/cancel", response_model=WaitlistCancelResponse)
async def cancel_waitlist_entry(
    cancel_data: WaitlistCancel,
    waitlist_entry_id: int = Path(..., description="Waitlist entry ID"),
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role),
    db: Session = Depends(get_db)
):
    """
    Cancel a waitlist entry.
    
    Args:
        waitlist_entry_id: ID of the waitlist entry to cancel
        cancel_data: Cancellation information
        user_id: Current user ID
        user_role: Current user role
        db: Database session
        
    Returns:
        Cancellation response with waitlist entry details
        
    Raises:
        HTTPException: If cancellation fails
    """
    try:
        # Check permissions
        is_admin = user_role == "admin"
        if not is_admin:
            # Regular users can only cancel their own waitlist entries
            waitlist_entry = await waitlist_service.get_waitlist_entry_by_id(
                waitlist_entry_id=waitlist_entry_id,
                user_id=user_id,
                is_admin=False
            )
            if not waitlist_entry:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Waitlist entry not found or access denied"
                )
        
        # Cancel waitlist entry
        waitlist_entry, success = await waitlist_service.cancel_waitlist_entry(
            waitlist_entry_id=waitlist_entry_id,
            cancel_data=cancel_data,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel waitlist entry"
            )
        
        waitlist_response = WaitlistEntryResponse.from_orm(waitlist_entry)
        
        return WaitlistCancelResponse(
            success=True,
            message="Waitlist entry cancelled successfully",
            waitlist_entry=waitlist_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel waitlist entry {waitlist_entry_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{waitlist_entry_id}/position", response_model=dict)
async def get_waitlist_position(
    waitlist_entry_id: int = Path(..., description="Waitlist entry ID"),
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role),
    db: Session = Depends(get_db)
):
    """
    Get the position of a waitlist entry.
    
    Args:
        waitlist_entry_id: ID of the waitlist entry
        user_id: Current user ID
        user_role: Current user role
        db: Database session
        
    Returns:
        Position information
        
    Raises:
        HTTPException: If waitlist entry not found or access denied
    """
    try:
        # Check permissions
        is_admin = user_role == "admin"
        if not is_admin:
            # Regular users can only see their own waitlist entry positions
            waitlist_entry = await waitlist_service.get_waitlist_entry_by_id(
                waitlist_entry_id=waitlist_entry_id,
                user_id=user_id,
                is_admin=False
            )
            if not waitlist_entry:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Waitlist entry not found or access denied"
                )
        
        # Get position
        position = await waitlist_service.get_waitlist_position(waitlist_entry_id)
        
        if position is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waitlist entry not found"
            )
        
        return {
            "waitlist_entry_id": waitlist_entry_id,
            "position": position,
            "status": "active" if position > 0 else "inactive"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get waitlist position for entry {waitlist_entry_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve waitlist position"
        )


@router.get("/{waitlist_entry_id}/audit", response_model=List[WaitlistAuditLogResponse])
async def get_waitlist_audit_log(
    waitlist_entry_id: int = Path(..., description="Waitlist entry ID"),
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role),
    db: Session = Depends(get_db)
):
    """
    Get audit log for a specific waitlist entry.
    
    Args:
        waitlist_entry_id: ID of the waitlist entry
        user_id: Current user ID
        user_role: Current user role
        db: Database session
        
    Returns:
        List of audit log entries
        
    Raises:
        HTTPException: If access denied or waitlist entry not found
    """
    try:
        # Check permissions
        is_admin = user_role == "admin"
        if not is_admin:
            # Regular users can only see their own waitlist entry audit logs
            waitlist_entry = await waitlist_service.get_waitlist_entry_by_id(
                waitlist_entry_id=waitlist_entry_id,
                user_id=user_id,
                is_admin=False
            )
            if not waitlist_entry:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Waitlist entry not found or access denied"
                )
        
        # Get audit logs
        audit_logs = db.query(WaitlistAuditLog).filter(
            WaitlistAuditLog.waitlist_entry_id == waitlist_entry_id
        ).order_by(WaitlistAuditLog.changed_at.desc()).all()
        
        return [WaitlistAuditLogResponse.from_orm(log) for log in audit_logs]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit log for waitlist entry {waitlist_entry_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit log"
        )


# Admin endpoints
@router.get("/admin/event/{event_id}", response_model=WaitlistListResponse)
async def get_event_waitlist(
    event_id: int = Path(..., description="Event ID"),
    status_filter: Optional[WaitlistStatus] = Query(None, description="Filter by waitlist status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get waitlist entries for a specific event (admin only).
    
    Args:
        event_id: ID of the event
        status_filter: Optional status filter
        page: Page number
        page_size: Number of items per page
        admin_user: Admin user information
        db: Database session
        
    Returns:
        Paginated list of event waitlist entries
    """
    try:
        entries, total = await waitlist_service.get_event_waitlist(
            event_id=event_id,
            status=status_filter,
            page=page,
            page_size=page_size
        )
        
        # Convert to response format
        waitlist_summaries = [WaitlistSummaryResponse.from_orm(entry) for entry in entries]
        
        # Calculate pagination info
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        return WaitlistListResponse(
            items=waitlist_summaries,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
    except Exception as e:
        logger.error(f"Failed to get event waitlist for event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event waitlist"
        )


@router.post("/admin/notify/{event_id}", response_model=BookingSuccessResponse)
async def notify_waitlist_entries(
    event_id: int = Path(..., description="Event ID"),
    available_quantity: int = Query(..., ge=1, description="Available quantity to notify for"),
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Manually notify waitlist entries for an event (admin only).
    
    Args:
        event_id: ID of the event
        available_quantity: Available quantity to notify for
        admin_user: Admin user information
        db: Database session
        
    Returns:
        Success response with notification details
        
    Raises:
        HTTPException: If notification fails
    """
    try:
        # Notify waitlist entries
        notified_entries = await waitlist_service.notify_next_waitlist_entries(
            event_id=event_id,
            available_quantity=available_quantity
        )
        
        return BookingSuccessResponse(
            success=True,
            message=f"Notified {len(notified_entries)} waitlist entries",
            data={
                "event_id": event_id,
                "notifications_sent": len(notified_entries),
                "available_quantity": available_quantity
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to notify waitlist entries for event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )