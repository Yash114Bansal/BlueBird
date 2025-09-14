"""
Celery service for Auth Service.
Handles task dispatch to workers for email notifications.
"""

import ssl
import logging
from typing import Optional, Dict, Any
from celery import Celery
from ..core.config import config

logger = logging.getLogger(__name__)


class CeleryService:
    """
    Celery service for dispatching tasks to workers.
    Handles email verification tasks.
    """
    
    def __init__(self):
        self._celery_app = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Celery app for task dispatch."""
        try:
            if self._initialized:
                return
                
            # Create Celery app
            self._celery_app = Celery('auth_service')
            
            # Get Redis URL
            redis_url = await config.get_redis_url()
            
            # Configure Celery
            self._celery_app.conf.update(
                broker_url=redis_url,
                result_backend=redis_url,
                task_serializer='json',
                result_serializer='json',
                accept_content=['json'],
                task_routes={
                    'email_workers.tasks.send_otp_verification_email': {'queue': 'email_notifications'},
                    'email_workers.tasks.send_welcome_email': {'queue': 'email_notifications'},
                },
                broker_use_ssl={
                    'ssl_cert_reqs': ssl.CERT_NONE,
                    'ssl_check_hostname': False,
                },
                redis_backend_use_ssl={
                    'ssl_cert_reqs': ssl.CERT_NONE, 
                    'ssl_check_hostname': False,
                },
                task_track_started=True,
                timezone='UTC',
                enable_utc=True,
                broker_connection_retry_on_startup=True,
                broker_connection_max_retries=10,
                broker_connection_timeout=30,
                result_expires=3600,  # Results expire after 1 hour
                task_acks_late=True,
                worker_prefetch_multiplier=1,
                task_time_limit=300,  # 5 minutes
                task_soft_time_limit=240,  # 4 minutes
            )
            
            self._initialized = True
            logger.info("Celery service initialized for auth service")
            
        except Exception as e:
            logger.error(f"Failed to initialize Celery service: {e}")
            self._celery_app = None
            self._initialized = False
    
    async def send_otp_email(self, email: str, otp: str, user_data: Dict[str, Any]) -> bool:
        """
        Send OTP verification email via Celery workers.
        
        Args:
            email: User email address
            otp: Generated OTP code
            user_data: User information for email template
            
        Returns:
            True if task sent successfully, False otherwise
        """
        try:
            # Ensure Celery is initialized
            if not self._initialized:
                await self.initialize()
            
            if not self._celery_app:
                logger.error("Celery app not initialized, cannot send OTP email")
                return False
            
            # Prepare task data
            task_data = {
                'email': email,
                'otp': otp,
                'user_data': user_data,
                'timestamp': logger.info(f"Sending OTP email task for {email}")
            }
            
            # Send task to Celery workers
            task = self._celery_app.send_task(
                'email_workers.tasks.send_otp_verification_email',
                args=[task_data],
                queue='email_notifications'
            )
            
            logger.info(f"OTP email task sent for {email} with task ID: {task.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send OTP email task for {email}: {e}")
            return False
    
    async def send_welcome_email(self, email: str, user_data: Dict[str, Any]) -> bool:
        """
        Send welcome email via Celery workers.
        
        Args:
            email: User email address
            user_data: User information for email template
            
        Returns:
            True if task sent successfully, False otherwise
        """
        try:
            # Ensure Celery is initialized
            if not self._initialized:
                await self.initialize()
            
            if not self._celery_app:
                logger.error("Celery app not initialized, cannot send welcome email")
                return False
            
            # Prepare task data
            task_data = {
                'email': email,
                'user_data': user_data,
                'timestamp': logger.info(f"Sending welcome email task for {email}")
            }
            
            # Send task to Celery workers
            task = self._celery_app.send_task(
                'email_workers.tasks.send_welcome_email',
                args=[task_data],
                queue='email_notifications'
            )
            
            logger.info(f"Welcome email task sent for {email} with task ID: {task.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email task for {email}: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """Check if Celery service is initialized."""
        return self._initialized and self._celery_app is not None


# Global Celery service instance
celery_service = CeleryService()