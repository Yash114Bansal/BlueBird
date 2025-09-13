"""
Waitlist Service for high consistency waitlist operations.
Handles waitlist management, notifications, and priority ordering.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, update, and_, or_, func
import logging

from app.core.config import config
from app.db.database import db_manager
from app.db.redis_client import redis_manager, get_distributed_lock
from app.models.booking import (
    WaitlistEntry, WaitlistStatus, WaitlistAuditLog, 
    EventAvailability, Booking, BookingStatus
)
from app.schemas.booking import WaitlistJoin, WaitlistCancel
from .event_publisher import BookingEventPublisher
from .notification_service import notification_service

logger = logging.getLogger(__name__)


class WaitlistService:
    """
    High consistency waitlist service with atomic operations.
    Implements distributed locking and optimistic concurrency control.
    """
    
    def __init__(self):
        self.consistency_config = None
        self.waitlist_config = None
        self.event_publisher = None
    
    async def _get_configs(self):
        """Get configuration settings."""
        if not self.consistency_config:
            self.consistency_config = await config.get_consistency_config()
        if not self.waitlist_config:
            self.waitlist_config = await config.get_waitlist_config()
    
    async def _get_event_publisher(self):
        """Get event publisher instance."""
        if not self.event_publisher:
            await redis_manager.initialize()
            self.event_publisher = BookingEventPublisher(redis_manager)
        return self.event_publisher
    
    async def _get_next_priority(self, session: Session, event_id: int) -> int:
        """Get the next priority number for an event."""
        max_priority = session.query(func.max(WaitlistEntry.priority)).filter(
            and_(
                WaitlistEntry.event_id == event_id,
                WaitlistEntry.status.in_([WaitlistStatus.PENDING, WaitlistStatus.NOTIFIED])
            )
        ).scalar()
        
        return (max_priority or 0) + 1
    
    async def _create_waitlist_audit_log(
        self, 
        session: Session, 
        waitlist_entry_id: int, 
        action: str, 
        field_name: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        changed_by: Optional[int] = None,
        reason: Optional[str] = None
    ):
        """Create waitlist audit log entry."""
        audit_log = WaitlistAuditLog(
            waitlist_entry_id=waitlist_entry_id,
            action=action,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            reason=reason
        )
        session.add(audit_log)
    
    async def join_waitlist(
        self, 
        waitlist_data: WaitlistJoin, 
        user_id: int,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[WaitlistEntry, bool, int]:
        """
        Join the waitlist for an event.
        
        Args:
            waitlist_data: Waitlist join data
            user_id: ID of the user joining
            client_ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (WaitlistEntry object, success status, estimated position)
            
        Raises:
            Exception: If waitlist join fails
        """
        await self._get_configs()
        
        # Use distributed lock for high consistency
        lock_key = f"waitlist:event:{waitlist_data.event_id}"
        
        async with get_distributed_lock(
            lock_key, 
            timeout=self.consistency_config["lock_timeout_seconds"]
        ) as lock:
            try:
                with db_manager.get_transaction_session() as session:
                    # Check if user already has a waitlist entry for this event
                    existing_entry = session.query(WaitlistEntry).filter(
                        and_(
                            WaitlistEntry.user_id == user_id,
                            WaitlistEntry.event_id == waitlist_data.event_id,
                            WaitlistEntry.status.in_([WaitlistStatus.PENDING, WaitlistStatus.NOTIFIED])
                        )
                    ).first()
                    
                    if existing_entry:
                        raise Exception("User already has an active waitlist entry for this event")
                    
                    # Check if event exists and has availability record
                    availability = session.query(EventAvailability).filter(
                        EventAvailability.event_id == waitlist_data.event_id
                    ).first()
                    
                    if not availability:
                        raise Exception("Event not found or not available for booking")
                    
                    if availability.available_capacity >= waitlist_data.quantity:
                        raise Exception("Event has available capacity, no need to join waitlist")
                    
                    # Get next priority
                    priority = await self._get_next_priority(session, waitlist_data.event_id)
                    
                    # Create waitlist entry
                    waitlist_entry = WaitlistEntry(
                        user_id=user_id,
                        event_id=waitlist_data.event_id,
                        quantity=waitlist_data.quantity,
                        priority=priority,
                        status=WaitlistStatus.PENDING,
                        notes=waitlist_data.notes,
                        ip_address=client_ip,
                        user_agent=user_agent
                    )
                    
                    session.add(waitlist_entry)
                    session.flush()  # Get the waitlist entry ID
                    
                    # Create audit log
                    await self._create_waitlist_audit_log(
                        session, waitlist_entry.id, "JOIN", 
                        changed_by=user_id, reason="User joined waitlist"
                    )
                    
                    # Commit transaction
                    session.commit()
                    
                    # Refresh the waitlist entry
                    session.refresh(waitlist_entry)
                    
                    # Publish waitlist joined event
                    try:
                        publisher = await self._get_event_publisher()
                        await publisher.publish_waitlist_joined(waitlist_entry)
                    except Exception as e:
                        logger.error(f"Failed to publish waitlist joined event: {e}")
                    
                    # Send notification
                    try:
                        await notification_service.send_waitlist_joined(
                            user_id=user_id,
                            waitlist_data=waitlist_entry.to_dict(),
                            position=priority
                        )
                    except Exception as e:
                        logger.error(f"Failed to send waitlist joined notification: {e}")
                    
                    logger.info(f"User {user_id} joined waitlist for event {waitlist_data.event_id} with priority {priority}")
                    return waitlist_entry, True, priority
                    
            except Exception as e:
                logger.error(f"Failed to join waitlist: {e}")
                raise
    
    async def cancel_waitlist_entry(
        self, 
        waitlist_entry_id: int, 
        cancel_data: WaitlistCancel,
        user_id: Optional[int] = None
    ) -> Tuple[WaitlistEntry, bool]:
        """
        Cancel a waitlist entry.
        
        Args:
            waitlist_entry_id: ID of the waitlist entry to cancel
            cancel_data: Cancellation information
            user_id: ID of the user cancelling
            
        Returns:
            Tuple of (WaitlistEntry object, success status)
        """
        await self._get_configs()
        
        lock_key = f"waitlist:cancel:{waitlist_entry_id}"
        
        async with get_distributed_lock(
            lock_key, 
            timeout=self.consistency_config["lock_timeout_seconds"]
        ) as lock:
            try:
                with db_manager.get_transaction_session() as session:
                    # Get waitlist entry
                    waitlist_entry = session.query(WaitlistEntry).filter(
                        WaitlistEntry.id == waitlist_entry_id
                    ).first()
                    
                    if not waitlist_entry:
                        raise Exception("Waitlist entry not found")
                    
                    # Check if waitlist entry can be cancelled
                    if waitlist_entry.status in [WaitlistStatus.CANCELLED, WaitlistStatus.BOOKED]:
                        raise Exception(f"Waitlist entry cannot be cancelled in {waitlist_entry.status.value} status")
                    
                    # Update status
                    old_status = waitlist_entry.status.value
                    waitlist_entry.status = WaitlistStatus.CANCELLED
                    waitlist_entry.cancelled_at = datetime.now(timezone.utc)
                    waitlist_entry.version += 1
                    
                    # Create audit log
                    await self._create_waitlist_audit_log(
                        session, waitlist_entry_id, "CANCEL",
                        field_name="status",
                        old_value=old_status,
                        new_value=waitlist_entry.status.value,
                        changed_by=user_id,
                        reason=cancel_data.reason or "Waitlist entry cancelled"
                    )
                    
                    session.commit()
                    
                    # Refresh the waitlist entry
                    session.refresh(waitlist_entry)
                    
                    # Publish waitlist cancelled event
                    try:
                        publisher = await self._get_event_publisher()
                        await publisher.publish_waitlist_cancelled(waitlist_entry)
                    except Exception as e:
                        logger.error(f"Failed to publish waitlist cancelled event: {e}")
                    
                    # Send notification
                    try:
                        await notification_service.send_waitlist_cancellation(
                            user_id=waitlist_entry.user_id,
                            waitlist_data=waitlist_entry.to_dict()
                        )
                    except Exception as e:
                        logger.error(f"Failed to send waitlist cancellation notification: {e}")
                    
                    logger.info(f"Waitlist entry {waitlist_entry_id} cancelled")
                    return waitlist_entry, True
                    
            except Exception as e:
                logger.error(f"Failed to cancel waitlist entry {waitlist_entry_id}: {e}")
                raise
    
    async def notify_next_waitlist_entries(
        self, 
        event_id: int, 
        available_quantity: int
    ) -> List[WaitlistEntry]:
        """
        Notify the next waitlist entries when capacity becomes available.
        
        Args:
            event_id: ID of the event
            available_quantity: Available quantity to notify for
            
        Returns:
            List of notified waitlist entries
        """
        await self._get_configs()
        lock_key = f"waitlist:notify:{event_id}"
        
        async with get_distributed_lock(
            lock_key, 
            timeout=self.consistency_config["lock_timeout_seconds"]
        ) as lock:
            try:
                with db_manager.get_transaction_session() as session:
                    # Get pending waitlist entries ordered by priority
                    pending_entries = session.query(WaitlistEntry).filter(
                        and_(
                            WaitlistEntry.event_id == event_id,
                            WaitlistEntry.status == WaitlistStatus.PENDING
                        )
                    ).order_by(WaitlistEntry.priority.asc()).all()
                    
                    notified_entries = []
                    remaining_quantity = available_quantity
                    
                    # Set notification expiry time
                    notification_duration = timedelta(
                        minutes=self.waitlist_config.get("notification_expiry_minutes", 30)
                    )
                    expires_at = datetime.now(timezone.utc) + notification_duration
                    
                    for entry in pending_entries:
                        if remaining_quantity <= 0:
                            break
                        
                        if entry.quantity <= remaining_quantity:
                            # Notify this entry
                            old_status = entry.status.value
                            entry.status = WaitlistStatus.NOTIFIED
                            entry.notified_at = datetime.now(timezone.utc)
                            entry.expires_at = expires_at
                            entry.version += 1
                            
                            # Create audit log
                            await self._create_waitlist_audit_log(
                                session, entry.id, "NOTIFY",
                                field_name="status",
                                old_value=old_status,
                                new_value=entry.status.value,
                                reason="Notified of availability"
                            )
                            
                            # Send notification
                            try:
                                await notification_service.send_waitlist_notification(
                                    user_id=entry.user_id,
                                    waitlist_data=entry.to_dict(),
                                    expires_at=expires_at
                                )
                            except Exception as e:
                                logger.error(f"Failed to send waitlist notification: {e}")
                            
                            notified_entries.append(entry)
                            remaining_quantity -= entry.quantity
                    
                    session.commit()
                    
                    # Publish waitlist notification event
                    try:
                        publisher = await self._get_event_publisher()
                        await publisher.publish_waitlist_notifications_sent(event_id, len(notified_entries))
                    except Exception as e:
                        logger.error(f"Failed to publish waitlist notification event: {e}")
                    
                    logger.info(f"Notified {len(notified_entries)} waitlist entries for event {event_id}")
                    return notified_entries
                    
            except Exception as e:
                logger.error(f"Failed to notify waitlist entries for event {event_id}: {e}")
                return []
    
    async def expire_notifications(self) -> int:
        """
        Expire waitlist notifications that have passed their expiry time.
        
        Returns:
            Number of notifications expired
        """
        await self._get_configs()
        
        expired_count = 0
        
        try:
            with db_manager.get_transaction_session() as session:
                # Find expired notified entries
                expired_entries = session.query(WaitlistEntry).filter(
                    and_(
                        WaitlistEntry.status == WaitlistStatus.NOTIFIED,
                        WaitlistEntry.expires_at < datetime.now(timezone.utc)
                    )
                ).all()
                
                for entry in expired_entries:
                    # Update status
                    old_status = entry.status.value
                    entry.status = WaitlistStatus.EXPIRED
                    entry.version += 1
                    
                    # Create audit log
                    await self._create_waitlist_audit_log(
                        session, entry.id, "EXPIRE",
                        field_name="status",
                        old_value=old_status,
                        new_value=entry.status.value,
                        reason="Notification expired"
                    )
                    
                    expired_count += 1
                
                session.commit()
                
                if expired_count > 0:
                    logger.info(f"Expired {expired_count} waitlist notifications")
                
                return expired_count
                
        except Exception as e:
            logger.error(f"Failed to expire waitlist notifications: {e}")
            return 0
    
    async def get_waitlist_entry_by_id(
        self, 
        waitlist_entry_id: int, 
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> Optional[WaitlistEntry]:
        """
        Get waitlist entry by ID with access control.
        
        Args:
            waitlist_entry_id: ID of the waitlist entry
            user_id: ID of the requesting user
            is_admin: Whether the user is an admin
            
        Returns:
            WaitlistEntry object or None if not found/access denied
        """
        with db_manager.get_session() as session:
            query = session.query(WaitlistEntry).filter(WaitlistEntry.id == waitlist_entry_id)
            
            # Non-admin users can only see their own waitlist entries
            if not is_admin and user_id:
                query = query.filter(WaitlistEntry.user_id == user_id)
            
            return query.first()
    
    async def get_user_waitlist_entries(
        self, 
        user_id: int, 
        status: Optional[WaitlistStatus] = None,
        page: int = 1, 
        page_size: int = 20
    ) -> Tuple[List[WaitlistEntry], int]:
        """
        Get waitlist entries for a specific user with pagination.
        
        Args:
            user_id: ID of the user
            status: Optional status filter
            page: Page number
            page_size: Number of items per page
            
        Returns:
            Tuple of (waitlist entries list, total count)
        """
        with db_manager.get_session() as session:
            query = session.query(WaitlistEntry).filter(WaitlistEntry.user_id == user_id)
            
            if status:
                query = query.filter(WaitlistEntry.status == status)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * page_size
            entries = query.order_by(WaitlistEntry.joined_at.desc()).offset(offset).limit(page_size).all()
            
            return entries, total
    
    async def get_event_waitlist(
        self, 
        event_id: int, 
        status: Optional[WaitlistStatus] = None,
        page: int = 1, 
        page_size: int = 20
    ) -> Tuple[List[WaitlistEntry], int]:
        """
        Get waitlist entries for a specific event with pagination.
        
        Args:
            event_id: ID of the event
            status: Optional status filter
            page: Page number
            page_size: Number of items per page
            
        Returns:
            Tuple of (waitlist entries list, total count)
        """
        with db_manager.get_session() as session:
            query = session.query(WaitlistEntry).filter(WaitlistEntry.event_id == event_id)
            
            if status:
                query = query.filter(WaitlistEntry.status == status)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * page_size
            entries = query.order_by(WaitlistEntry.priority.asc()).offset(offset).limit(page_size).all()
            
            return entries, total
    
    async def get_waitlist_position(
        self, 
        waitlist_entry_id: int
    ) -> Optional[int]:
        """
        Get the position of a waitlist entry.
        
        Args:
            waitlist_entry_id: ID of the waitlist entry
            
        Returns:
            Position in waitlist or None if not found
        """
        with db_manager.get_session() as session:
            waitlist_entry = session.query(WaitlistEntry).filter(
                WaitlistEntry.id == waitlist_entry_id
            ).first()
            
            if not waitlist_entry:
                return None
            
            # Count entries with higher priority (lower priority number)
            position = session.query(WaitlistEntry).filter(
                and_(
                    WaitlistEntry.event_id == waitlist_entry.event_id,
                    WaitlistEntry.priority < waitlist_entry.priority,
                    WaitlistEntry.status.in_([WaitlistStatus.PENDING, WaitlistStatus.NOTIFIED])
                )
            ).count()
            
            return position + 1
    
    async def check_waitlist_eligibility(
        self, 
        event_id: int, 
        user_id: int,
        requested_quantity: int = 1
    ) -> dict:
        """
        Check if a user can join the waitlist for an event.
        
        Args:
            event_id: ID of the event
            user_id: ID of the user
            requested_quantity: Number of tickets requested
            
        Returns:
            Dictionary with eligibility information
        """
        try:
            with db_manager.get_session() as session:
                # Check event availability
                availability = session.query(EventAvailability).filter(
                    EventAvailability.event_id == event_id
                ).first()
                
                if not availability:
                    return {
                        "can_join": False,
                        "event_id": event_id
                    }
                
                # Check if event has available capacity
                event_available = availability.available_capacity >= requested_quantity
                
                # Check if user already has a waitlist entry
                existing_entry = session.query(WaitlistEntry).filter(
                    and_(
                        WaitlistEntry.user_id == user_id,
                        WaitlistEntry.event_id == event_id,
                        WaitlistEntry.status.in_([WaitlistStatus.PENDING, WaitlistStatus.NOTIFIED])
                    )
                ).first()
                
                has_existing_entry = existing_entry is not None
                existing_entry_status = existing_entry.status if existing_entry else None
                
                # Get total waitlist size for this event
                total_waitlist_size = session.query(WaitlistEntry).filter(
                    and_(
                        WaitlistEntry.event_id == event_id,
                        WaitlistEntry.status.in_([WaitlistStatus.PENDING, WaitlistStatus.NOTIFIED])
                    )
                ).count()
                
                # Calculate estimated position if joining waitlist
                estimated_position = total_waitlist_size + 1 if not has_existing_entry else None
                
                # Determine if user can join
                can_join = not event_available and not has_existing_entry
                
                # Determine reason if cannot join
                reason = None
                if event_available:
                    reason = "Event has available capacity - no need to join waitlist"
                elif has_existing_entry:
                    if existing_entry_status == WaitlistStatus.PENDING:
                        reason = "You already have a pending waitlist entry for this event"
                    elif existing_entry_status == WaitlistStatus.NOTIFIED:
                        reason = "You have already been notified about availability for this event"
                
                return {
                    "can_join": can_join,
                    "event_id": event_id
                }
                
        except Exception as e:
            logger.error(f"Failed to check waitlist eligibility: {e}")
            return {
                "can_join": False,
                "event_id": event_id
            }


# Global service instance
waitlist_service = WaitlistService()