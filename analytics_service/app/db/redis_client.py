"""
Redis client for Analytics Service.
Handles caching and event processing.
"""

import redis.asyncio as redis
from typing import Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Redis connection manager for analytics caching.
    Handles async Redis operations.
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        if not self.redis_client:
            return None
        try:
            return await self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set value in Redis with TTL."""
        if not self.redis_client:
            return False
        try:
            await self.redis_client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value from Redis."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in Redis key {key}")
        return None
    
    async def set_json(self, key: str, data: Dict[str, Any], ttl: int = 300) -> bool:
        """Set JSON value in Redis."""
        try:
            json_str = json.dumps(data)
            return await self.set(key, json_str, ttl)
        except Exception as e:
            logger.error(f"Redis set_json error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self.redis_client:
            return False
        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.redis_client:
            return False
        try:
            result = await self.redis_client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")


class RedisConnection:
    """
    Redis connection wrapper for dependency injection.
    Provides singleton access to Redis manager.
    """
    
    def __init__(self):
        self._manager: Optional[RedisManager] = None
    
    def initialize(self, redis_url: str):
        """Initialize Redis connection."""
        if self._manager is None:
            self._manager = RedisManager(redis_url)
            logger.info("Redis connection wrapper initialized")
    
    def get_manager(self) -> RedisManager:
        """Get Redis manager instance."""
        if self._manager is None:
            raise RuntimeError("Redis not initialized. Call initialize() first.")
        return self._manager
    
    async def close(self):
        """Close Redis connection."""
        if self._manager:
            await self._manager.close()
            self._manager = None