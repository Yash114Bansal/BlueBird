"""
Redis client for Events Service caching.
"""

import json
import logging
from typing import Any, Optional, Dict
import redis.asyncio as redis
from redis.asyncio import Redis

from ..core.config import config

class RedisConnection:
    """
    Redis connection manager for Events Service.
    Handles caching operations for read-heavy workloads.
    """
    
    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self._initialized = False
    
    def initialize(self, redis_url: str):
        """
        Initialize Redis connection.
        
        Args:
            redis_url: Redis connection URL
        """
        try:
            self.redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            self._initialized = True
            logger.info("Redis connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise
    
    def get_manager(self):
        """Get Redis manager instance."""
        if not self._initialized:
            raise RuntimeError("Redis not initialized")
        return self
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")


class CacheManager:
    """
    Cache manager for Events Service.
    Handles caching operations with TTL management.
    """
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.cache_config = {}
    
    async def initialize(self):
        """Initialize cache configuration."""
        self.cache_config = await config.get_cache_config()
    
    def _serialize(self, data: Any) -> str:
        """Serialize data for caching."""
        return json.dumps(data, default=str)
    
    def _deserialize(self, data: str) -> Any:
        """Deserialize cached data."""
        return json.loads(data)
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        try:
            value = await self.redis.get(key)
            if value:
                return self._deserialize(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        try:
            serialized_value = self._serialize(value)
            await self.redis.set(key, serialized_value, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful
        """
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete keys matching pattern.
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            Number of keys deleted
        """
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to delete cache pattern {pattern}: {e}")
            return 0
    
    async def get_events_cache_key(self, page: int, size: int, status: Optional[str] = None) -> str:
        """Generate cache key for events list."""
        if status:
            return f"events:list:{status}:{page}:{size}"
        return f"events:list:all:{page}:{size}"
    
    async def get_event_cache_key(self, event_id: int) -> str:
        """Generate cache key for single event."""
        return f"event:detail:{event_id}"
    
    
    async def cache_events_list(self, events: list, page: int, size: int, status: Optional[str] = None):
        """Cache events list."""
        cache_key = await self.get_events_cache_key(page, size, status)
        ttl = self.cache_config.get("events_ttl", 300)
        await self.set(cache_key, events, ttl)
    
    async def get_cached_events_list(self, page: int, size: int, status: Optional[str] = None) -> Optional[list]:
        """Get cached events list."""
        cache_key = await self.get_events_cache_key(page, size, status)
        return await self.get(cache_key)
    
    async def cache_event_detail(self, event: dict, event_id: int):
        """Cache event detail."""
        cache_key = await self.get_event_cache_key(event_id)
        ttl = self.cache_config.get("event_details_ttl", 600)
        await self.set(cache_key, event, ttl)
    
    async def get_cached_event_detail(self, event_id: int) -> Optional[dict]:
        """Get cached event detail."""
        cache_key = await self.get_event_cache_key(event_id)
        return await self.get(cache_key)
    
    async def invalidate_event_cache(self, event_id: int):
        """Invalidate event-related cache."""
        # Invalidate event detail cache
        await self.delete(await self.get_event_cache_key(event_id))
        
        # Invalidate events list cache (all pages and statuses)
        await self.delete_pattern("events:list:*")
    
