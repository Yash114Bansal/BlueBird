"""
Event Publisher Service for Bookings Service.
Publishes booking events to Redis for inter-service communication.
"""

import json
import logging
from typing import Dict, Any
from ..db.redis_client import RedisManager

logger = logging.getLogger(__name__)


class BookingEventPublisher:
    """
    Publishes booking events to Redis channels for inter-service communication.
    """
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        self.channel_prefix = "evently:bookings"
    
    async def publish_booking_created(self, booking):
        """
        Publish booking created notification.
        
        Args:
            booking: Booking object to publish
        """
        try:
            channel = f"{self.channel_prefix}:created"
            message = {
                "type": "BookingCreated",
                "booking_id": booking.id,
                "event_id": booking.event_id,
                "user_id": booking.user_id,
                "booking_data": {
                    "id": booking.id,
                    "event_id": booking.event_id,
                    "user_id": booking.user_id,
                    "booking_reference": booking.booking_reference,
                    "quantity": booking.quantity,
                    "total_amount": float(booking.total_amount) if booking.total_amount else 0.0,
                    "currency": booking.currency,
                    "status": booking.status.value if booking.status else None,
                    "payment_status": booking.payment_status.value if booking.payment_status else None,
                    "created_at": booking.created_at.isoformat() if booking.created_at else None,
                    "expires_at": booking.expires_at.isoformat() if booking.expires_at else None
                }
            }
            
            await self.redis_manager.publish(channel, json.dumps(message))
            logger.info(f"Published BookingCreated for booking {booking.id}")
            
        except Exception as e:
            logger.error(f"Failed to publish BookingCreated: {e}")
    
    async def publish_booking_confirmed(self, booking):
        """
        Publish booking confirmed notification.
        
        Args:
            booking: Booking object to publish
        """
        try:
            channel = f"{self.channel_prefix}:confirmed"
            message = {
                "type": "BookingConfirmed",
                "booking_id": booking.id,
                "event_id": booking.event_id,
                "user_id": booking.user_id,
                "booking_data": {
                    "id": booking.id,
                    "event_id": booking.event_id,
                    "user_id": booking.user_id,
                    "booking_reference": booking.booking_reference,
                    "quantity": booking.quantity,
                    "total_amount": float(booking.total_amount) if booking.total_amount else 0.0,
                    "currency": booking.currency,
                    "status": booking.status.value if booking.status else None,
                    "payment_status": booking.payment_status.value if booking.payment_status else None,
                    "confirmed_at": booking.updated_at.isoformat() if booking.updated_at else None
                }
            }
            
            await self.redis_manager.publish(channel, json.dumps(message))
            logger.info(f"Published BookingConfirmed for booking {booking.id}")
            
        except Exception as e:
            logger.error(f"Failed to publish BookingConfirmed: {e}")
    
    async def publish_booking_cancelled(self, booking):
        """
        Publish booking cancelled notification.
        
        Args:
            booking: Booking object to publish
        """
        try:
            channel = f"{self.channel_prefix}:cancelled"
            message = {
                "type": "BookingCancelled",
                "booking_id": booking.id,
                "event_id": booking.event_id,
                "user_id": booking.user_id,
                "booking_data": {
                    "id": booking.id,
                    "event_id": booking.event_id,
                    "user_id": booking.user_id,
                    "booking_reference": booking.booking_reference,
                    "quantity": booking.quantity,
                    "total_amount": float(booking.total_amount) if booking.total_amount else 0.0,
                    "currency": booking.currency,
                    "status": booking.status.value if booking.status else None,
                    "payment_status": booking.payment_status.value if booking.payment_status else None,
                    "cancelled_at": booking.updated_at.isoformat() if booking.updated_at else None,
                    "cancellation_reason": getattr(booking, 'cancellation_reason', None)
                }
            }
            
            await self.redis_manager.publish(channel, json.dumps(message))
            logger.info(f"Published BookingCancelled for booking {booking.id}")
            
        except Exception as e:
            logger.error(f"Failed to publish BookingCancelled: {e}")
    
    async def publish_booking_expired(self, booking):
        """
        Publish booking expired notification.
        
        Args:
            booking: Booking object to publish
        """
        try:
            channel = f"{self.channel_prefix}:expired"
            message = {
                "type": "BookingExpired",
                "booking_id": booking.id,
                "event_id": booking.event_id,
                "user_id": booking.user_id,
                "booking_data": {
                    "id": booking.id,
                    "event_id": booking.event_id,
                    "user_id": booking.user_id,
                    "booking_reference": booking.booking_reference,
                    "quantity": booking.quantity,
                    "total_amount": float(booking.total_amount) if booking.total_amount else 0.0,
                    "currency": booking.currency,
                    "status": booking.status.value if booking.status else None,
                    "expired_at": booking.updated_at.isoformat() if booking.updated_at else None
                }
            }
            
            await self.redis_manager.publish(channel, json.dumps(message))
            logger.info(f"Published BookingExpired for booking {booking.id}")
            
        except Exception as e:
            logger.error(f"Failed to publish BookingExpired: {e}")
    
    async def publish_booking_payment_completed(self, booking):
        """
        Publish booking payment completed notification.
        
        Args:
            booking: Booking object to publish
        """
        try:
            channel = f"{self.channel_prefix}:payment_completed"
            message = {
                "type": "BookingPaymentCompleted",
                "booking_id": booking.id,
                "event_id": booking.event_id,
                "user_id": booking.user_id,
                "booking_data": {
                    "id": booking.id,
                    "event_id": booking.event_id,
                    "user_id": booking.user_id,
                    "booking_reference": booking.booking_reference,
                    "quantity": booking.quantity,
                    "total_amount": float(booking.total_amount) if booking.total_amount else 0.0,
                    "currency": booking.currency,
                    "status": booking.status.value if booking.status else None,
                    "payment_status": booking.payment_status.value if booking.payment_status else None,
                    "payment_completed_at": booking.updated_at.isoformat() if booking.updated_at else None
                }
            }
            
            await self.redis_manager.publish(channel, json.dumps(message))
            logger.info(f"Published BookingPaymentCompleted for booking {booking.id}")
            
        except Exception as e:
            logger.error(f"Failed to publish BookingPaymentCompleted: {e}")
    
    async def publish_waitlist_joined(self, waitlist_entry):
        """
        Publish waitlist joined notification.
        
        Args:
            waitlist_entry: WaitlistEntry object to publish
        """
        try:
            channel = f"{self.channel_prefix}:waitlist_joined"
            message = {
                "type": "WaitlistJoined",
                "waitlist_entry_id": waitlist_entry.id,
                "event_id": waitlist_entry.event_id,
                "user_id": waitlist_entry.user_id,
                "waitlist_data": {
                    "id": waitlist_entry.id,
                    "event_id": waitlist_entry.event_id,
                    "user_id": waitlist_entry.user_id,
                    "quantity": waitlist_entry.quantity,
                    "priority": waitlist_entry.priority,
                    "status": waitlist_entry.status.value if waitlist_entry.status else None,
                    "joined_at": waitlist_entry.joined_at.isoformat() if waitlist_entry.joined_at else None,
                    "created_at": waitlist_entry.created_at.isoformat() if waitlist_entry.created_at else None
                }
            }
            
            await self.redis_manager.publish(channel, json.dumps(message))
            logger.info(f"Published WaitlistJoined for waitlist entry {waitlist_entry.id}")
            
        except Exception as e:
            logger.error(f"Failed to publish WaitlistJoined: {e}")
    
    async def publish_waitlist_cancelled(self, waitlist_entry):
        """
        Publish waitlist cancelled notification.
        
        Args:
            waitlist_entry: WaitlistEntry object to publish
        """
        try:
            channel = f"{self.channel_prefix}:waitlist_cancelled"
            message = {
                "type": "WaitlistCancelled",
                "waitlist_entry_id": waitlist_entry.id,
                "event_id": waitlist_entry.event_id,
                "user_id": waitlist_entry.user_id,
                "waitlist_data": {
                    "id": waitlist_entry.id,
                    "event_id": waitlist_entry.event_id,
                    "user_id": waitlist_entry.user_id,
                    "quantity": waitlist_entry.quantity,
                    "priority": waitlist_entry.priority,
                    "status": waitlist_entry.status.value if waitlist_entry.status else None,
                    "cancelled_at": waitlist_entry.cancelled_at.isoformat() if waitlist_entry.cancelled_at else None,
                    "updated_at": waitlist_entry.updated_at.isoformat() if waitlist_entry.updated_at else None
                }
            }
            
            await self.redis_manager.publish(channel, json.dumps(message))
            logger.info(f"Published WaitlistCancelled for waitlist entry {waitlist_entry.id}")
            
        except Exception as e:
            logger.error(f"Failed to publish WaitlistCancelled: {e}")
    
    async def publish_waitlist_notifications_sent(self, event_id: int, count: int):
        """
        Publish waitlist notifications sent notification.
        
        Args:
            event_id: ID of the event
            count: Number of notifications sent
        """
        try:
            channel = f"{self.channel_prefix}:waitlist_notifications_sent"
            message = {
                "type": "WaitlistNotificationsSent",
                "event_id": event_id,
                "notifications_sent": count,
                "timestamp": json.dumps({"timestamp": "now"})  # Will be replaced with actual timestamp
            }
            
            await self.redis_manager.publish(channel, json.dumps(message))
            logger.info(f"Published WaitlistNotificationsSent for event {event_id}, count: {count}")
            
        except Exception as e:
            logger.error(f"Failed to publish WaitlistNotificationsSent: {e}")
    
    async def publish_waitlist_availability_updated(self, event_id: int, available_capacity: int):
        """
        Publish waitlist availability updated notification.
        
        Args:
            event_id: ID of the event
            available_capacity: Available capacity for waitlist
        """
        try:
            channel = f"{self.channel_prefix}:waitlist_availability_updated"
            message = {
                "type": "WaitlistAvailabilityUpdated",
                "event_id": event_id,
                "available_capacity": available_capacity,
                "timestamp": json.dumps({"timestamp": "now"})  # Will be replaced with actual timestamp
            }
            
            await self.redis_manager.publish(channel, json.dumps(message))
            logger.info(f"Published WaitlistAvailabilityUpdated for event {event_id}, capacity: {available_capacity}")
            
        except Exception as e:
            logger.error(f"Failed to publish WaitlistAvailabilityUpdated: {e}")