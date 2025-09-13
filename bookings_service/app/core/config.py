"""
Configuration management for Bookings Service.
Uses Zero Python SDK for secure configuration.
Optimized for high consistency and trade availability.
"""

import os
import asyncio
import concurrent.futures
from urllib.parse import quote_plus
from typing import Dict, Any, Optional
import logging
from zero_python_sdk import zero

logger = logging.getLogger(__name__)


class ZeroSecretsManager:
    """
    Zero secrets client using the official Zero Python SDK.
    Follows SOLID principles with single responsibility.
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
                logger.info("Successfully fetched secrets from Zero")
            except Exception as e:
                logger.error(f"Failed to fetch secrets from Zero: {e}")
                self._secrets = {}

    def _normalize_key(self, key: str) -> str:
        """Normalize a key to lowercase and replace underscores with hyphens."""
        return key.lower().replace("_", "-")
    
    async def get_secret(self, key: str) -> Optional[str]:
        """
        Get a secret value by key.
        
        Args:
            key: The secret key to retrieve
            
        Returns:
            Secret value or None if not found
        """
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
            logger.error(f"Failed to fetch secret {key}: {e}")
            return None
    
    async def get_config(self, service_name: str) -> Dict[str, Any]:
        """
        Get all configuration for a specific service.
        
        Args:
            service_name: Name of the service (e.g., 'bookings_service')
            
        Returns:
            Dictionary of configuration values
        """
        try:
            await self._fetch_secrets()
            config = self._secrets.get("evently", {})
            self._cache.update(config)
            return config
            
        except Exception as e:
            logger.error(f"Failed to fetch config for {service_name}: {e}")
            return {}
    
    async def close(self):
        """Close method for compatibility."""
        pass


class BookingsConfig:
    """
    Bookings Service configuration manager.
    Handles all configuration for the bookings service with high consistency focus.
    """
    
    def __init__(self):
        self.zero_token = os.getenv("ZERO_TOKEN")
        if not self.zero_token:
            raise ValueError("ZERO_TOKEN environment variable is required")
        
        self.secrets_manager = ZeroSecretsManager(self.zero_token)
        self._config_cache: Dict[str, Any] = {}
    
    async def get_database_url(self) -> str:
        """Get the database connection URL."""
        host = await self.secrets_manager.get_secret("DB_HOST") or "localhost"
        port = await self.secrets_manager.get_secret("DB_PORT") or "5432"
        name = await self.secrets_manager.get_secret("DB_NAME") or "evently"
        user = await self.secrets_manager.get_secret("DB_USER") or "evently"
        password = await self.secrets_manager.get_secret("DB_PASSWORD") or "evently123"

        return f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{name}"
    
    async def get_redis_url(self) -> str:
        """Get the Redis connection URL."""
        host = await self.secrets_manager.get_secret("REDIS_HOST") or "localhost"
        port = await self.secrets_manager.get_secret("REDIS_PORT") or "6379"
        password = await self.secrets_manager.get_secret("REDIS_PASSWORD")
        use_tls = await self.secrets_manager.get_secret("REDIS_USE_TLS")
        
        protocol = "rediss://" if use_tls else "redis://"
        
        if password:
            return f"{protocol}:{password}@{host}:{port}"
        return f"{protocol}{host}:{port}"
    
    async def get_jwt_secret(self) -> str:
        """Get JWT secret key."""
        return await self.secrets_manager.get_secret("JWT_SECRET") or "your-secret-key-change-in-production"
    
    async def get_jwt_algorithm(self) -> str:
        """Get JWT algorithm."""
        return await self.secrets_manager.get_secret("JWT_ALGORITHM") or "HS256"
    
    async def get_jwt_expiry_minutes(self) -> int:
        """Get JWT expiry time in minutes."""
        expiry = await self.secrets_manager.get_secret("JWT_EXPIRY_MINUTES")
        return int(expiry) if expiry else 30
    
    async def get_cors_origins(self) -> list:
        """Get CORS allowed origins."""
        origins = await self.secrets_manager.get_secret("CORS_ORIGINS")
        if origins:
            return origins.split(",")
        return ["http://localhost:3000", "http://localhost:8080"]
    
    async def get_cache_config(self) -> Dict[str, int]:
        """Get cache TTL configuration for bookings."""
        return {
            "bookings_ttl": int(await self.secrets_manager.get_secret("CACHE_TTL_BOOKINGS") or "60"),
            "availability_ttl": int(await self.secrets_manager.get_secret("CACHE_TTL_AVAILABILITY") or "30"),
            "user_bookings_ttl": int(await self.secrets_manager.get_secret("CACHE_TTL_USER_BOOKINGS") or "300"),
            "event_capacity_ttl": int(await self.secrets_manager.get_secret("CACHE_TTL_EVENT_CAPACITY") or "10")
        }
    
    async def get_consistency_config(self) -> Dict[str, Any]:
        """Get high consistency configuration settings."""
        return {
            "lock_timeout_seconds": int(await self.secrets_manager.get_secret("LOCK_TIMEOUT_SECONDS") or "30"),
            "max_retry_attempts": int(await self.secrets_manager.get_secret("MAX_RETRY_ATTEMPTS") or "3"),
            "retry_delay_ms": int(await self.secrets_manager.get_secret("RETRY_DELAY_MS") or "100"),
            "enable_distributed_locks": await self.secrets_manager.get_secret("ENABLE_DISTRIBUTED_LOCKS") == "true",
            "enable_optimistic_locking": await self.secrets_manager.get_secret("ENABLE_OPTIMISTIC_LOCKING") == "true",
            "transaction_timeout_seconds": int(await self.secrets_manager.get_secret("TRANSACTION_TIMEOUT_SECONDS") or "60")
        }
    
    async def get_booking_config(self) -> Dict[str, Any]:
        """Get booking-specific configuration."""
        return {
            "max_booking_quantity": int(await self.secrets_manager.get_secret("MAX_BOOKING_QUANTITY") or "10"),
            "booking_hold_duration_minutes": int(await self.secrets_manager.get_secret("BOOKING_HOLD_DURATION_MINUTES") or "15"),
            "enable_booking_validation": await self.secrets_manager.get_secret("ENABLE_BOOKING_VALIDATION") != "false",
            "enable_capacity_checks": await self.secrets_manager.get_secret("ENABLE_CAPACITY_CHECKS") != "false",
            "enable_duplicate_prevention": await self.secrets_manager.get_secret("ENABLE_DUPLICATE_PREVENTION") != "false"
        }
    
    async def get_waitlist_config(self) -> Dict[str, Any]:
        """Get waitlist-specific configuration."""
        return {
            "max_waitlist_quantity": int(await self.secrets_manager.get_secret("MAX_WAITLIST_QUANTITY") or "10"),
            "notification_expiry_minutes": int(await self.secrets_manager.get_secret("WAITLIST_NOTIFICATION_EXPIRY_MINUTES") or "30"),
            "enable_waitlist_validation": await self.secrets_manager.get_secret("ENABLE_WAITLIST_VALIDATION") != "false",
            "enable_waitlist_notifications": await self.secrets_manager.get_secret("ENABLE_WAITLIST_NOTIFICATIONS") != "false",
            "enable_duplicate_waitlist_prevention": await self.secrets_manager.get_secret("ENABLE_DUPLICATE_WAITLIST_PREVENTION") != "false",
            "max_waitlist_entries_per_user": int(await self.secrets_manager.get_secret("MAX_WAITLIST_ENTRIES_PER_USER") or "5")
        }
    
    async def get_database_config(self) -> Dict[str, Any]:
        """Get database-specific configuration for high consistency."""
        return {
            "pool_size": int(await self.secrets_manager.get_secret("DB_POOL_SIZE") or "20"),
            "max_overflow": int(await self.secrets_manager.get_secret("DB_MAX_OVERFLOW") or "30"),
            "pool_timeout": int(await self.secrets_manager.get_secret("DB_POOL_TIMEOUT") or "30"),
            "pool_recycle": int(await self.secrets_manager.get_secret("DB_POOL_RECYCLE") or "3600"),
            "isolation_level": await self.secrets_manager.get_secret("DB_ISOLATION_LEVEL") or "READ_COMMITTED",
            "enable_autocommit": await self.secrets_manager.get_secret("DB_ENABLE_AUTOCOMMIT") == "false"
        }
    
    async def close(self):
        """Close the secrets manager."""
        await self.secrets_manager.close()


# Global config instance
config = BookingsConfig()