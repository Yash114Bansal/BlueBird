"""
Celery configuration for workers.
Shared configuration used by all worker services.
Uses Zero Python SDK for secure configuration management.
"""

import os
import asyncio
import concurrent.futures
from urllib.parse import quote_plus
from typing import Dict, Any, Optional
import logging
from zero_python_sdk import zero

logger = logging.getLogger(__name__)


class WorkerSecretsManager:
    """
    Zero secrets client for workers using the official Zero Python SDK.
    Follows the same pattern as the booking service.
    """
    
    def __init__(self, zero_token: str, caller_name: str = "evently"):
        self.zero_token = zero_token
        self.caller_name = caller_name
        self._cache: Dict[str, Any] = {}
        self._secrets = None
    
    async def _fetch_secrets(self):
        """Fetch secrets from Zero if not already cached."""
        if self._secrets is None:
            try:
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    self._secrets = await loop.run_in_executor(
                        executor,
                        lambda: zero(
                            token=self.zero_token,
                            pick=["evently"],
                            caller_name=self.caller_name
                        ).fetch()
                    )
                logger.info("Successfully fetched secrets from Zero for workers")
            except Exception as e:
                logger.error(f"Failed to fetch secrets from Zero for workers: {e}")
                self._secrets = {}

    def _normalize_key(self, key: str) -> str:
        """Normalize a key to lowercase and replace underscores with hyphens."""
        return key.lower().replace("_", "-")
    
    async def get_secret(self, key: str) -> Optional[str]:
        """Get a secret value by key."""
        try:
            key = self._normalize_key(key)
            if key in self._cache:
                return self._cache[key]
            
            await self._fetch_secrets()
            evently_secrets = self._secrets.get("evently", {})
            secret_value = evently_secrets.get(key)
            
            if secret_value:
                self._cache[key] = secret_value
                
            return secret_value
            
        except Exception as e:
            logger.error(f"Failed to fetch secret {key} for workers: {e}")
            return None


class WorkersConfig:
    """
    Workers configuration manager using Zero secrets management.
    Handles all configuration for worker services.
    """
    
    def __init__(self):
        self.zero_token = os.getenv("ZERO_TOKEN")
        if not self.zero_token:
            raise ValueError("ZERO_TOKEN environment variable is required for workers")
        
        self.secrets_manager = WorkerSecretsManager(self.zero_token)
        self._config_cache: Dict[str, Any] = {}
    
    async def get_redis_url(self) -> str:
        """Get the Redis connection URL for Celery broker."""
        host = await self.secrets_manager.get_secret("REDIS_HOST") or "localhost"
        port = await self.secrets_manager.get_secret("REDIS_PORT") or "6379"
        password = await self.secrets_manager.get_secret("REDIS_PASSWORD")
        use_tls = await self.secrets_manager.get_secret("REDIS_USE_TLS")
        
        protocol = "rediss://" if use_tls else "redis://"
        
        # Build base URL
        if password:
            base_url = f"{protocol}:{password}@{host}:{port}"
        else:
            base_url = f"{protocol}{host}:{port}"
        
        # Add SSL certificate requirements for rediss:// URLs (for Upstash compatibility)
        if use_tls:
            # For Upstash Redis, we need to disable SSL certificate verification
            base_url += "?ssl_cert_reqs=CERT_NONE&ssl_check_hostname=False"
        
        return base_url
    
    async def get_celery_broker_url(self) -> str:
        """Get Celery broker URL."""
        return await self.get_redis_url()
    
    async def get_celery_result_backend(self) -> str:
        """Get Celery result backend URL."""
        return await self.get_redis_url()
    
    async def get_email_config(self) -> Dict[str, Any]:
        """Get email notification configuration."""
        return {
            "smtp_host": await self.secrets_manager.get_secret("SMTP_HOST") or "smtp.gmail.com",
            "smtp_port": int(await self.secrets_manager.get_secret("SMTP_PORT") or "587"),
            "smtp_username": await self.secrets_manager.get_secret("SMTP_USERNAME"),
            "smtp_password": await self.secrets_manager.get_secret("SMTP_PASSWORD"),
            "smtp_use_tls": await self.secrets_manager.get_secret("SMTP_USE_TLS") == "true",
            "from_email": await self.secrets_manager.get_secret("FROM_ADDRESS") or "noreply@evently.com",
            "from_name": await self.secrets_manager.get_secret("FROM_NAME") or "Evently",
            "max_retries": int(await self.secrets_manager.get_secret("MAX_RETRIES") or "3"),
            "retry_delay": int(await self.secrets_manager.get_secret("RETRY_DELAY") or "60")
        }
    
    async def get_db_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return {
            "host": await self.secrets_manager.get_secret("DB_HOST"),
            "port": await self.secrets_manager.get_secret("DB_PORT"),
            "name": await self.secrets_manager.get_secret("DB_NAME"),
            "user": await self.secrets_manager.get_secret("DB_USER"),
            "password": await self.secrets_manager.get_secret("DB_PASSWORD"),
        }
    
    async def close(self):
        """Close the secrets manager."""
        await self.secrets_manager.close()


# Global config instance
workers_config = WorkersConfig()

# Task routing for different worker types
CELERY_ROUTES = {
    'email_workers.tasks.*': {'queue': 'email_notifications'},
    'email_workers.tasks.send_otp_verification_email': {'queue': 'email_notifications'},
    'email_workers.tasks.send_welcome_email': {'queue': 'email_notifications'},
}

# Task serialization
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

# Task time limits
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes

# Worker configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_DISABLE_RATE_LIMITS = False

# Result backend configuration
CELERY_RESULT_BACKEND_MAX_RETRIES = 10
CELERY_RESULT_BACKEND_RETRY_DELAY = 1.0

# Task routing configuration
CELERY_TASK_ROUTES = CELERY_ROUTES

# Celery app configuration
def create_celery_app():
    """Create and configure Celery app for email workers."""
    from celery import Celery
    
    # Initialize workers config
    config = WorkersConfig()
    
    # Get broker and result backend URLs
    broker_url = asyncio.run(config.get_celery_broker_url())
    result_backend = asyncio.run(config.get_celery_result_backend())
    
    celery_app = Celery(
        'evently_workers',
        broker=broker_url,
        backend=result_backend,
        include=[
            'email_workers.tasks',
        ]
    )
    
    celery_app.conf.update(
        task_track_started=True,
        task_serializer=CELERY_TASK_SERIALIZER,
        result_serializer=CELERY_RESULT_SERIALIZER,
        accept_content=CELERY_ACCEPT_CONTENT,
        timezone='UTC',
        enable_utc=True,
        worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
        worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(task_name)s[%(task_id)s]: %(message)s",
        broker_connection_retry_on_startup=True,
        broker_connection_max_retries=10,
        broker_connection_timeout=30,
        result_expires=3600,  # Results expire after 1 hour
        task_acks_late=CELERY_TASK_ACKS_LATE,
        worker_prefetch_multiplier=CELERY_WORKER_PREFETCH_MULTIPLIER,
        task_time_limit=CELERY_TASK_TIME_LIMIT,
        task_soft_time_limit=CELERY_TASK_SOFT_TIME_LIMIT,
        task_routes=CELERY_TASK_ROUTES,
        result_backend_max_retries=CELERY_RESULT_BACKEND_MAX_RETRIES,
        result_backend_retry_delay=CELERY_RESULT_BACKEND_RETRY_DELAY,
        # Fix for macOS fork() issues - use solo pool instead of prefork
        worker_pool='solo',  # Use solo pool to avoid fork() issues on macOS
        # Redis SSL configuration for Upstash compatibility
        broker_use_ssl={
            'ssl_cert_reqs': 'CERT_NONE',
            'ssl_check_hostname': False,
        },
        redis_backend_use_ssl={
            'ssl_cert_reqs': 'CERT_NONE', 
            'ssl_check_hostname': False,
        },
    )
    
    return celery_app