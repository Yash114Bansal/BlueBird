"""
Notification Service for Bookings Service.
Handles sending notifications for booking and waitlist events using Celery workers.
"""
import ssl
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

# Import Celery for task dispatch
from celery import Celery

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Notification service for sending various types of notifications using Celery workers.
    Decoupled from the main service to handle notifications asynchronously.
    """
    
    def __init__(self):
        """Initialize the notification service."""
        self.enabled = True
        self.providers = []
        self._celery_app = None
        self._initialized = False
    
    async def _initialize_celery(self):
        """Initialize Celery app for task dispatch."""
        try:
            if self._initialized:
                return
                
            # Create a simple Celery app for sending tasks to workers
            self._celery_app = Celery('bookings_service')
            
            from app.core.config import config
            logger.info("Initializing Celery app for notification dispatch")
            # Get Redis URL asynchronously
            redis_url = await config.get_redis_url()
            
            self._celery_app.conf.update(
                broker_url=redis_url,
                result_backend=redis_url,
                task_serializer='json',
                result_serializer='json',
                accept_content=['json'],
                task_routes={
                    'email_workers.tasks.*': {'queue': 'email_notifications'},
                },
                broker_use_ssl={
                    'ssl_cert_reqs': ssl.CERT_NONE,
                    'ssl_check_hostname': False,
                },
                redis_backend_use_ssl={
                    'ssl_cert_reqs': ssl.CERT_NONE, 
                    'ssl_check_hostname': False,
                },
            )
            
            self._initialized = True
            logger.info("Celery app initialized for notification dispatch")
            
        except Exception as e:
            logger.error(f"Failed to initialize Celery app: {e}")
            self._celery_app = None
            self._initialized = False
    
    async def _send_email_task(self, task_name: str, user_id: int, data: Dict[str, Any]) -> bool:
        """
        Send email task to Celery workers.
        
        Args:
            task_name: Name of the Celery task
            user_id: User ID (workers will fetch email address)
            data: Task data
            
        Returns:
            True if task sent successfully, False otherwise
        """
        try:
            # Ensure Celery is initialized
            if not self._initialized:
                await self._initialize_celery()
            
            if not self._celery_app:
                logger.error("Celery app not initialized, cannot send email task")
                return False
            
            # Send task to Celery workers with user_id
            task = self._celery_app.send_task(
                task_name,
                args=[user_id, data],
                queue='email_notifications'
            )
            
            logger.info(f"Email task {task_name} sent for user {user_id} with ID: {task.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email task {task_name}: {e}")
            return False
    
    
    async def send_booking_confirmation(
        self, 
        user_id: int, 
        booking_data: Dict[str, Any],
        event_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send booking confirmation notification via email worker.
        
        Args:
            user_id: ID of the user
            booking_data: Booking information
            event_data: Event information (optional)
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            if not self.enabled:
                logger.info("Notification service disabled, skipping booking confirmation")
                return True
            
            logger.info(f"Sending booking confirmation to user {user_id}")
            
            # Prepare task data
            task_data = {
                'booking_id': booking_data.get('id'),
                'event_name': booking_data.get('event_name', 'Your Event'),  # Use actual event name or fallback
                'quantity': booking_data.get('quantity', 1),
                'total_price': booking_data.get('total_amount', 0),
                'booking_date': booking_data.get('created_at', datetime.now().strftime('%Y-%m-%d'))
            }
            
            # Send task to email worker with user_id
            return await self._send_email_task(
                'email_workers.tasks.send_booking_confirmation',
                user_id,
                task_data
            )
            
        except Exception as e:
            logger.error(f"Failed to send booking confirmation: {e}")
            return False
    
    async def send_booking_cancellation(
        self, 
        user_id: int, 
        booking_data: Dict[str, Any],
        event_data: Optional[Dict[str, Any]] = None,
        cancellation_reason: Optional[str] = None
    ) -> bool:
        """
        Send booking cancellation notification via email worker.
        
        Args:
            user_id: ID of the user
            booking_data: Booking information
            event_data: Event information (optional)
            cancellation_reason: Reason for cancellation (optional)
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            if not self.enabled:
                logger.info("Notification service disabled, skipping booking cancellation")
                return True
            
            logger.info(f"Sending booking cancellation to user {user_id}")
            
            # Prepare task data
            task_data = {
                'booking_id': booking_data.get('id'),
                'event_name': 'Your Event',  # Generic event name
                'refund_amount': booking_data.get('total_amount', 0),
                'reason': cancellation_reason or 'User request',
                'cancellation_date': datetime.now().strftime('%Y-%m-%d')
            }
            
            # Send task to email worker with user_id
            return await self._send_email_task(
                'email_workers.tasks.send_booking_cancellation',
                user_id,
                task_data
            )
            
        except Exception as e:
            logger.error(f"Failed to send booking cancellation: {e}")
            return False
    
    async def send_waitlist_notification(
        self, 
        user_id: int, 
        waitlist_data: Dict[str, Any],
        event_data: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Send waitlist availability notification via email worker.
        
        Args:
            user_id: ID of the user
            waitlist_data: Waitlist entry information
            event_data: Event information (optional)
            expires_at: When the notification expires (optional)
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            if not self.enabled:
                logger.info("Notification service disabled, skipping waitlist notification")
                return True
            
            logger.info(f"Sending waitlist notification to user {user_id}")
            
            # Calculate expiry minutes
            expiry_minutes = 30  # Default
            if expires_at:
                time_diff = expires_at - datetime.now(timezone.utc)
                expiry_minutes = max(1, int(time_diff.total_seconds() / 60))
            
            # Prepare task data
            task_data = {
                'event_name': event_data.get('name') if event_data else 'Event',
                'position': waitlist_data.get('position', 1),
                'expiry_minutes': expiry_minutes,
                'waitlist_id': waitlist_data.get('id')
            }
            
            # Send task to email worker with user_id
            return await self._send_email_task(
                'email_workers.tasks.send_waitlist_notification',
                user_id,
                task_data
            )
            
        except Exception as e:
            logger.error(f"Failed to send waitlist notification: {e}")
            return False
    
    async def send_waitlist_joined(
        self, 
        user_id: int, 
        waitlist_data: Dict[str, Any],
        event_data: Optional[Dict[str, Any]] = None,
        position: Optional[int] = None
    ) -> bool:
        """
        Send waitlist joined confirmation notification via email worker.
        
        Args:
            user_id: ID of the user
            waitlist_data: Waitlist entry information
            event_data: Event information (optional)
            position: Position in waitlist (optional)
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            if not self.enabled:
                logger.info("Notification service disabled, skipping waitlist joined notification")
                return True
            
            logger.info(f"Sending waitlist joined notification to user {user_id}")
            
            # Prepare task data
            task_data = {
                'event_name': event_data.get('name') if event_data else 'Event',
                'position': position or waitlist_data.get('position', 1),
                'waitlist_id': waitlist_data.get('id'),
                'joined_date': datetime.now().strftime('%Y-%m-%d')
            }
            
            # Send task to email worker with user_id
            return await self._send_email_task(
                'email_workers.tasks.send_waitlist_joined',
                user_id,
                task_data
            )
            
        except Exception as e:
            logger.error(f"Failed to send waitlist joined notification: {e}")
            return False
    
    async def send_waitlist_cancellation(
        self, 
        user_id: int, 
        waitlist_data: Dict[str, Any],
        event_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send waitlist cancellation notification via email worker.
        
        Args:
            user_id: ID of the user
            waitlist_data: Waitlist entry information
            event_data: Event information (optional)
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            if not self.enabled:
                logger.info("Notification service disabled, skipping waitlist cancellation")
                return True
            
            logger.info(f"Sending waitlist cancellation to user {user_id}")
            
            # Prepare task data
            task_data = {
                'event_name': event_data.get('name') if event_data else 'Event',
                'waitlist_id': waitlist_data.get('id'),
                'cancellation_date': datetime.now().strftime('%Y-%m-%d')
            }
            
            # Send task to email worker with user_id
            return await self._send_email_task(
                'email_workers.tasks.send_waitlist_cancellation',
                user_id,
                task_data
            )
            
        except Exception as e:
            logger.error(f"Failed to send waitlist cancellation: {e}")
            return False
    
    async def send_bulk_notifications(
        self, 
        notifications: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Send multiple notifications in bulk.
        
        Args:
            notifications: List of notification data
            
        Returns:
            Dictionary with success and failure counts
        """
        try:
            if not self.enabled:
                logger.info("Notification service disabled, skipping bulk notifications")
                return {"success": len(notifications), "failed": 0}
            
            logger.info(f"Sending {len(notifications)} bulk notifications")
            
            # For now, just log each notification
            for notification in notifications:
                logger.debug(f"Bulk notification: {notification}")
            
            return {"success": len(notifications), "failed": 0}
            
        except Exception as e:
            logger.error(f"Failed to send bulk notifications: {e}")
            return {"success": 0, "failed": len(notifications)}
    
    def enable(self):
        """Enable the notification service."""
        self.enabled = True
        logger.info("Notification service enabled")
    
    def disable(self):
        """Disable the notification service."""
        self.enabled = False
        logger.info("Notification service disabled")
    
    def is_enabled(self) -> bool:
        """Check if the notification service is enabled."""
        return self.enabled
    
    async def get_notification_stats(self) -> Dict[str, Any]:
        """
        Get notification service statistics.
        
        Returns:
            Dictionary with notification statistics
        """
        try:
            return {
                "enabled": self.enabled,
                "providers_count": len(self.providers),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get notification stats: {e}")
            return {
                "enabled": self.enabled,
                "error": str(e)
            }


# Global notification service instance
notification_service = NotificationService()