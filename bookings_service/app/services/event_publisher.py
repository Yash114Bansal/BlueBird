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