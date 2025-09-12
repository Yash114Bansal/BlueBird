"""
Configuration management for Events Service.
Uses Zero Python SDK for secure configuration.
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
            service_name: Name of the service (e.g., 'events_service')
            
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


class EventsConfig:
    """
    Events Service configuration manager.
    Handles all configuration for the events service.
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
        """Get cache TTL configuration."""
        return {
            "events_ttl": int(await self.secrets_manager.get_secret("CACHE_TTL_EVENTS") or "300"),
            "event_details_ttl": int(await self.secrets_manager.get_secret("CACHE_TTL_EVENT_DETAILS") or "600"),
            "bookings_ttl": int(await self.secrets_manager.get_secret("CACHE_TTL_BOOKINGS") or "60")
        }
    
    async def close(self):
        """Close the secrets manager."""
        await self.secrets_manager.close()


# Global config instance
config = EventsConfig()