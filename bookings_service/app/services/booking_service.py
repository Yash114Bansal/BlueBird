"""
Booking Service for high consistency booking operations.
Handles booking creation, updates, and cancellation with atomic transactions.
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
import logging

from app.core.config import config
from app.db.database import db_manager
from app.db.redis_client import redis_manager, get_distributed_lock
from app.models.booking import Booking, BookingItem, BookingStatus, PaymentStatus, BookingAuditLog, EventAvailability
from app.schemas.booking import BookingCreate, BookingCancel
from .event_publisher import BookingEventPublisher
from .waitlist_service import waitlist_service
from .notification_service import notification_service

logger = logging.getLogger(__name__)


class BookingService:
    """
    High consistency booking service with atomic operations.
    Implements distributed locking and optimistic concurrency control.
    """
    
    def __init__(self):
        self.consistency_config = None
        self.booking_config = None
        self.event_publisher = None
    
    async def _get_configs(self):
        """Get configuration settings."""
        if not self.consistency_config:
            self.consistency_config = await config.get_consistency_config()
        if not self.booking_config:
            self.booking_config = await config.get_booking_config()
    
    async def _get_event_publisher(self):
        """Get event publisher instance."""
        if not self.event_publisher:
            await redis_manager.initialize()
            self.event_publisher = BookingEventPublisher(redis_manager)
        return self.event_publisher
    
    async def _generate_booking_reference(self) -> str:
        """Generate unique booking reference."""
        return f"BK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    async def get_event_price(self, event_id: int) -> Optional[Decimal]:
        """
        Get event price from EventAvailability.
        
        Args:
            event_id: ID of the event
            
        Returns:
            Event price or None if event not found
        """
        try:
            from app.models.booking import EventAvailability
            
            with db_manager.get_session() as session:
                availability = session.query(EventAvailability).filter(
                    EventAvailability.event_id == event_id
                ).first()
                
                if availability:
                    return availability.price
                else:
                    logger.warning(f"EventAvailability not found for event {event_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting event price for event {event_id}: {e}")
            return None
    
    async def _create_audit_log(
        self, 
        session: Session, 
        booking_id: int, 
        action: str, 
        field_name: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        changed_by: Optional[int] = None,
        reason: Optional[str] = None
    ):
        """Create audit log entry."""
        audit_log = BookingAuditLog(
            booking_id=booking_id,
            action=action,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            reason=reason
        )
        session.add(audit_log)
    
    async def create_booking(
        self, 
        booking_data: BookingCreate, 
        user_id: int,
        event_price: Decimal,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[Booking, bool]:
        """
        Create a new booking with high consistency.
        
        Args:
            booking_data: Booking creation data
            user_id: ID of the user creating the booking
            event_price: Price per ticket for the event
            client_ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (Booking object, success status)
            
        Raises:
            Exception: If booking creation fails
        """
        await self._get_configs()
        
        # Generate unique booking reference
        booking_reference = await self._generate_booking_reference()
        
        # Calculate total amount
        total_amount = event_price * booking_data.quantity
        
        # Set booking expiry time
        hold_duration = timedelta(minutes=self.booking_config["booking_hold_duration_minutes"])
        expires_at = datetime.now(timezone.utc) + hold_duration
        
        # Use distributed lock for high consistency
        lock_key = f"booking:event:{booking_data.event_id}"
        
        async with get_distributed_lock(
            lock_key, 
            timeout=self.consistency_config["lock_timeout_seconds"]
        ) as lock:
            try:
                with db_manager.get_transaction_session() as session:
                    # Check availability with optimistic locking
                    availability = await self._check_and_reserve_availability(
                        session, booking_data.event_id, booking_data.quantity
                    )
                    
                    if not availability:
                        raise Exception("Insufficient capacity for booking")
                    
                    # Create booking
                    booking = Booking(
                        user_id=user_id,
                        event_id=booking_data.event_id,
                        booking_reference=booking_reference,
                        quantity=booking_data.quantity,
                        total_amount=total_amount,
                        currency="USD",
                        status=BookingStatus.PENDING,
                        payment_status=PaymentStatus.PENDING,
                        expires_at=expires_at,
                        notes=booking_data.notes,
                        ip_address=client_ip,
                        user_agent=user_agent
                    )
                    
                    session.add(booking)
                    session.flush()  # Get the booking ID
                    
                    # Create booking item
                    booking_item = BookingItem(
                        booking_id=booking.id,
                        price_per_item=event_price,
                        quantity=booking_data.quantity,
                        total_price=total_amount
                    )
                    
                    session.add(booking_item)
                    
                    # Create audit log
                    await self._create_audit_log(
                        session, booking.id, "CREATE", 
                        changed_by=user_id, reason="Booking created"
                    )
                    
                    # Commit transaction
                    session.commit()
                    
                    # Refresh the booking to ensure it's properly loaded with relationships
                    session.refresh(booking)
                    
                    # Explicitly load booking_items to avoid lazy loading issues
                    _ = booking.booking_items
                    
                    # Publish booking created event
                    try:
                        publisher = await self._get_event_publisher()
                        await publisher.publish_booking_created(booking)
                    except Exception as e:
                        logger.error(f"Failed to publish booking created event: {e}")
                    
                    logger.info(f"Booking created successfully: {booking_reference}")
                    return booking, True
                    
            except Exception as e:
                logger.error(f"Failed to create booking: {e}")
                raise
    
    async def _check_and_reserve_availability(
        self, 
        session: Session, 
        event_id: int, 
        quantity: int
    ) -> bool:
        """
        Check and reserve availability with optimistic locking.
        
        Args:
            session: Database session
            event_id: Event ID
            quantity: Quantity to reserve
            
        Returns:
            True if reservation successful, False otherwise
        """
        from app.models.booking import EventAvailability
        
        # Get current availability with optimistic locking
        availability = session.query(EventAvailability).filter(
            EventAvailability.event_id == event_id
        ).first()
        
        if not availability:
            logger.warning(f"Availability record not found for event {event_id}")
            return False
        
        # Check if enough capacity is available
        if availability.available_capacity < quantity:
            return False
        
        # Reserve capacity with optimistic locking
        result = session.query(EventAvailability).filter(
            and_(
                EventAvailability.event_id == event_id,
                EventAvailability.version == availability.version,
                EventAvailability.available_capacity >= quantity
            )
        ).update({
            EventAvailability.available_capacity: EventAvailability.available_capacity - quantity,
            EventAvailability.reserved_capacity: EventAvailability.reserved_capacity + quantity,
            EventAvailability.version: EventAvailability.version + 1
        })
        
        return result > 0
    
    async def confirm_booking(
        self, 
        booking_id: int, 
        user_id: Optional[int] = None
    ) -> Tuple[Booking, bool]:
        """
        Confirm a booking (simplified without payment).
        
        Args:
            booking_id: ID of the booking to confirm
            user_id: ID of the user confirming (optional for admin)
            
        Returns:
            Tuple of (Booking object, success status)
        """
        await self._get_configs()
        
        lock_key = f"booking:confirm:{booking_id}"
        
        async with get_distributed_lock(
            lock_key, 
            timeout=self.consistency_config["lock_timeout_seconds"]
        ) as lock:
            try:
                with db_manager.get_transaction_session() as session:
                    # Get booking with optimistic locking
                    booking = session.query(Booking).filter(
                        and_(
                            Booking.id == booking_id,
                            Booking.status == BookingStatus.PENDING
                        )
                    ).first()
                    
                    if not booking:
                        raise Exception("Booking not found or not in pending status")
                    
                    # Check if booking has expired
                    if booking.is_expired:
                        # Mark as expired
                        booking.status = BookingStatus.EXPIRED
                        session.commit()
                        raise Exception("Booking has expired")
                    
                    # Update booking status
                    old_status = booking.status.value
                    booking.status = BookingStatus.CONFIRMED
                    booking.payment_status = PaymentStatus.COMPLETED  # Auto-complete payment
                    booking.confirmed_at = datetime.now(timezone.utc)
                    booking.version += 1
                    
                    # Update availability
                    await self._confirm_availability_reservation(
                        session, booking.event_id, booking.quantity
                    )
                    
                    # Create audit log
                    await self._create_audit_log(
                        session, booking_id, "CONFIRM",
                        field_name="status",
                        old_value=old_status,
                        new_value=booking.status.value,
                        changed_by=user_id,
                        reason="Booking confirmed"
                    )
                    
                    session.commit()
                    
                    # Eagerly load booking_items to avoid DetachedInstanceError
                    _ = booking.booking_items
                    
                    # Publish booking confirmed event
                    try:
                        publisher = await self._get_event_publisher()
                        await publisher.publish_booking_confirmed(booking)
                    except Exception as e:
                        logger.error(f"Failed to publish booking confirmed event: {e}")
                    
                    # Send booking confirmation notification
                    try:
                        # Get event name from availability database
                        event_name = await self._get_event_name(booking.event_id)
                        await notification_service.send_booking_confirmation(
                            user_id=booking.user_id,
                            booking_data={
                                'id': booking.id,
                                'event_name': event_name,  # Include actual event name
                                'quantity': booking.quantity,
                                'total_amount': float(booking.total_amount),
                                'created_at': booking.created_at.isoformat()
                            }
                        )
                    except Exception as e:
                        logger.error(f"Failed to send booking confirmation notification: {e}")
                    
                    logger.info(f"Booking confirmed: {booking.booking_reference}")
                    return booking, True
                    
            except Exception as e:
                logger.error(f"Failed to confirm booking {booking_id}: {e}")
                raise
    
    async def _confirm_availability_reservation(
        self, 
        session: Session, 
        event_id: int, 
        quantity: int
    ):
        """Move reserved capacity to confirmed capacity."""
        from app.models.booking import EventAvailability
        
        session.query(EventAvailability).filter(
            EventAvailability.event_id == event_id
        ).update({
            EventAvailability.reserved_capacity: EventAvailability.reserved_capacity - quantity,
            EventAvailability.confirmed_capacity: EventAvailability.confirmed_capacity + quantity,
            EventAvailability.version: EventAvailability.version + 1
        })
    
    async def cancel_booking(
        self, 
        booking_id: int, 
        cancel_data: BookingCancel,
        user_id: Optional[int] = None
    ) -> Tuple[Booking, bool]:
        """
        Cancel a booking and release capacity.
        
        Args:
            booking_id: ID of the booking to cancel
            cancel_data: Cancellation information
            user_id: ID of the user cancelling
            
        Returns:
            Tuple of (Booking object, success status)
        """
        await self._get_configs()
        
        lock_key = f"booking:cancel:{booking_id}"
        
        async with get_distributed_lock(
            lock_key, 
            timeout=self.consistency_config["lock_timeout_seconds"]
        ) as lock:
            try:
                with db_manager.get_transaction_session() as session:
                    # Get booking
                    booking = session.query(Booking).filter(
                        Booking.id == booking_id
                    ).first()
                    
                    if not booking:
                        raise Exception("Booking not found")
                    
                    # Check if booking can be cancelled
                    if booking.status in [BookingStatus.CANCELLED, BookingStatus.COMPLETED]:
                        raise Exception(f"Booking cannot be cancelled in {booking.status.value} status")
                    
                    # Update booking status
                    old_status = booking.status.value
                    booking.status = BookingStatus.CANCELLED
                    booking.cancelled_at = datetime.now(timezone.utc)
                    booking.version += 1
                    
                    # Release capacity based on previous status
                    if old_status == BookingStatus.PENDING.value:
                        # Release reserved capacity
                        logger.info(f"Releasing reserved capacity for event {booking.event_id}, quantity: {booking.quantity}")
                        await self._release_reserved_capacity(
                            session, booking.event_id, booking.quantity
                        )
                    elif old_status == BookingStatus.CONFIRMED.value:
                        # Release confirmed capacity
                        logger.info(f"Releasing confirmed capacity for event {booking.event_id}, quantity: {booking.quantity}")
                        await self._release_confirmed_capacity(
                            session, booking.event_id, booking.quantity
                        )
                    else:
                        logger.warning(f"Booking {booking_id} had status {old_status}, no capacity to release")
                    
                    # Create audit log
                    await self._create_audit_log(
                        session, booking_id, "CANCEL",
                        field_name="status",
                        old_value=old_status,
                        new_value=booking.status.value,
                        changed_by=user_id,
                        reason=cancel_data.reason or "Booking cancelled"
                    )
                    
                    session.commit()
                    
                    # Eagerly load booking_items to avoid DetachedInstanceError
                    _ = booking.booking_items
                    
                    # Publish booking cancelled event
                    try:
                        publisher = await self._get_event_publisher()
                        await publisher.publish_booking_cancelled(booking)
                    except Exception as e:
                        logger.error(f"Failed to publish booking cancelled event: {e}")
                    
                    # Notify waitlist entries if capacity was released
                    try:
                        if old_status in [BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]:
                            await waitlist_service.notify_next_waitlist_entries(
                                event_id=booking.event_id,
                                available_quantity=booking.quantity
                            )
                    except Exception as e:
                        logger.error(f"Failed to notify waitlist entries after booking cancellation: {e}")
                    
                    logger.info(f"Booking cancelled: {booking.booking_reference}")
                    return booking, True
                    
            except Exception as e:
                logger.error(f"Failed to cancel booking {booking_id}: {e}")
                raise
    
    async def _release_reserved_capacity(
        self, 
        session: Session, 
        event_id: int, 
        quantity: int
    ):
        """Release reserved capacity back to available."""
        from app.models.booking import EventAvailability
        
        # Get current availability before update
        availability = session.query(EventAvailability).filter(
            EventAvailability.event_id == event_id
        ).first()
        
        if availability:
            logger.info(f"Before releasing reserved capacity - Event {event_id}: reserved={availability.reserved_capacity}, available={availability.available_capacity}")
            
            session.query(EventAvailability).filter(
                EventAvailability.event_id == event_id
            ).update({
                EventAvailability.reserved_capacity: EventAvailability.reserved_capacity - quantity,
                EventAvailability.available_capacity: EventAvailability.available_capacity + quantity,
                EventAvailability.version: EventAvailability.version + 1
            })
            
            # Refresh and log after update
            session.refresh(availability)
            logger.info(f"After releasing reserved capacity - Event {event_id}: reserved={availability.reserved_capacity}, available={availability.available_capacity}")
        else:
            logger.error(f"EventAvailability not found for event {event_id}")
    
    async def _release_confirmed_capacity(
        self, 
        session: Session, 
        event_id: int, 
        quantity: int
    ):
        """Release confirmed capacity back to available."""
        from app.models.booking import EventAvailability
        
        # Get current availability before update
        availability = session.query(EventAvailability).filter(
            EventAvailability.event_id == event_id
        ).first()
        
        if availability:
            logger.info(f"Before releasing confirmed capacity - Event {event_id}: confirmed={availability.confirmed_capacity}, available={availability.available_capacity}")
            
            session.query(EventAvailability).filter(
                EventAvailability.event_id == event_id
            ).update({
                EventAvailability.confirmed_capacity: EventAvailability.confirmed_capacity - quantity,
                EventAvailability.available_capacity: EventAvailability.available_capacity + quantity,
                EventAvailability.version: EventAvailability.version + 1
            })
            
            # Refresh and log after update
            session.refresh(availability)
            logger.info(f"After releasing confirmed capacity - Event {event_id}: confirmed={availability.confirmed_capacity}, available={availability.available_capacity}")
        else:
            logger.error(f"EventAvailability not found for event {event_id}")
    
    async def get_booking_by_id(
        self, 
        booking_id: int, 
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> Optional[Booking]:
        """
        Get booking by ID with access control.
        
        Args:
            booking_id: ID of the booking
            user_id: ID of the requesting user
            is_admin: Whether the user is an admin
            
        Returns:
            Booking object or None if not found/access denied
        """
        with db_manager.get_session() as session:
            query = session.query(Booking).filter(Booking.id == booking_id)
            
            # Non-admin users can only see their own bookings
            if not is_admin and user_id:
                query = query.filter(Booking.user_id == user_id)
            
            booking = query.first()
            if booking:
                # Explicitly load booking_items to avoid lazy loading issues
                _ = booking.booking_items
            
            return booking
    
    async def get_user_bookings(
        self, 
        user_id: int, 
        status: Optional[BookingStatus] = None,
        page: int = 1, 
        page_size: int = 20
    ) -> Tuple[List[Booking], int]:
        """
        Get bookings for a specific user with pagination.
        
        Args:
            user_id: ID of the user
            status: Optional status filter
            page: Page number
            page_size: Number of items per page
            
        Returns:
            Tuple of (bookings list, total count)
        """
        with db_manager.get_session() as session:
            query = session.query(Booking).filter(Booking.user_id == user_id)
            
            if status:
                query = query.filter(Booking.status == status)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * page_size
            bookings = query.order_by(Booking.booking_date.desc()).offset(offset).limit(page_size).all()
            
            # Explicitly load booking_items for each booking to avoid lazy loading issues
            for booking in bookings:
                _ = booking.booking_items
            
            return bookings, total
    
    async def expire_pending_bookings(self) -> int:
        """
        Expire pending bookings that have passed their expiry time.
        
        Returns:
            Number of bookings expired
        """
        await self._get_configs()
        
        expired_count = 0
        
        try:
            with db_manager.get_transaction_session() as session:
                # Find expired pending bookings
                expired_bookings = session.query(Booking).filter(
                    and_(
                        Booking.status == BookingStatus.PENDING,
                        Booking.expires_at < datetime.now(timezone.utc)
                    )
                ).all()
                
                for booking in expired_bookings:
                    # Update status
                    booking.status = BookingStatus.EXPIRED
                    booking.version += 1
                    
                    # Release reserved capacity
                    await self._release_reserved_capacity(
                        session, booking.event_id, booking.quantity
                    )
                    
                    # Create audit log
                    await self._create_audit_log(
                        session, booking.id, "EXPIRE",
                        field_name="status",
                        old_value="pending",
                        new_value="expired",
                        reason="Booking expired due to timeout"
                    )
                    
                    expired_count += 1
                
                session.commit()
                
                if expired_count > 0:
                    logger.info(f"Expired {expired_count} pending bookings")
                    
                    # Notify waitlist entries for events that had expired bookings
                    try:
                        for booking in expired_bookings:
                            await waitlist_service.notify_next_waitlist_entries(
                                event_id=booking.event_id,
                                available_quantity=booking.quantity
                            )
                    except Exception as e:
                        logger.error(f"Failed to notify waitlist entries after booking expiry: {e}")
                
                return expired_count
                
        except Exception as e:
            logger.error(f"Failed to expire pending bookings: {e}")
            return 0
    
    async def _get_event_name(self, event_id: int) -> str:
        """
        Get event name from EventAvailability table.
        
        Args:
            event_id: Event ID
            
        Returns:
            Event name or generic fallback
        """
        try:
            with db_manager.get_session() as session:
                availability = session.query(EventAvailability).filter(
                    EventAvailability.event_id == event_id
                ).first()
                
                if availability and availability.event_name:
                    return availability.event_name
                else:
                    return f"Event {event_id}"  # Fallback
                    
        except Exception as e:
            logger.error(f"Failed to get event name for event {event_id}: {e}")
            return f"Event {event_id}"  # Fallback
    


# Global service instance
booking_service = BookingService()