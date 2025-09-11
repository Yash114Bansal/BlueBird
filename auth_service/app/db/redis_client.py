"""
Redis client for caching and distributed locking in Auth Service.
Provides caching operations and session management.
"""

import redis.asyncio as redis
import json
import logging
from typing import Any, Optional, Dict, List
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Redis connection manager following SOLID principles.
    Handles connection pooling and provides caching operations.
    """
    
    def __init__(self, redis_url: str, max_connections: int = 20):
        self.redis_url = redis_url
        self.pool = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=max_connections,
            retry_on_timeout=True
        )
        self.redis_client = redis.Redis(connection_pool=self.pool)
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        try:
            return await self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: str, expire: Optional[int] = None):
        """Set key-value pair with optional expiration."""
        try:
            await self.redis_client.set(key, value, ex=expire)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
    
    async def delete(self, key: str):
        """Delete key."""
        try:
            await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return await self.redis_client.exists(key)
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCREMENT error for key {key}: {e}")
            return 0
    
    async def expire(self, key: str, seconds: int):
        """Set expiration for a key."""
        try:
            await self.redis_client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
    
    async def close(self):
        """Close Redis connection."""
        await self.redis_client.aclose()


class CacheManager:
    """
    High-level cache manager with JSON serialization.
    Provides caching operations for the auth service.
    """
    
    def __init__(self, redis_manager: RedisManager, default_ttl: int = 3600):
        self.redis_manager = redis_manager
        self.default_ttl = default_ttl
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        value = await self.redis_manager.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set cached value."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.redis_manager.set(key, str(value), expire=ttl or self.default_ttl)
    
    async def delete(self, key: str):
        """Delete cached value."""
        await self.redis_manager.delete(key)
    
    async def get_or_set(self, key: str, factory_func, ttl: Optional[int] = None):
        """
        Get cached value or set it using factory function.
        
        Args:
            key: Cache key
            factory_func: Function to generate value if not cached
            ttl: Time to live in seconds
            
        Returns:
            Cached or generated value
        """
        value = await self.get(key)
        if value is None:
            value = await factory_func()
            await self.set(key, value, ttl)
        return value


class DistributedLock:
    """
    Distributed lock implementation using Redis.
    Prevents race conditions in concurrent operations.
    """
    
    def __init__(self, redis_manager: RedisManager, lock_key: str, timeout: int = 10):
        self.redis_manager = redis_manager
        self.lock_key = f"lock:{lock_key}"
        self.timeout = timeout
        self.identifier = None
    
    async def acquire(self) -> bool:
        """
        Acquire distributed lock.
        
        Returns:
            True if lock acquired, False otherwise
        """
        import uuid
        self.identifier = str(uuid.uuid4())
        
        # Try to acquire lock with timeout
        result = await self.redis_manager.redis_client.set(
            self.lock_key,
            self.identifier,
            nx=True,  # Only set if not exists
            ex=self.timeout
        )
        
        return result is not None
    
    async def release(self):
        """Release distributed lock."""
        if self.identifier:
            # Use Lua script to ensure atomic release
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            await self.redis_manager.redis_client.eval(
                lua_script, 1, self.lock_key, self.identifier
            )
    
    @asynccontextmanager
    async def __aenter__(self):
        """Async context manager entry."""
        acquired = await self.acquire()
        if not acquired:
            raise RuntimeError(f"Failed to acquire lock: {self.lock_key}")
        try:
            yield self
        finally:
            await self.release()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.release()


class RateLimiter:
    """
    Rate limiting implementation using Redis.
    Prevents abuse of authentication endpoints.
    """
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
    
    async def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            key: Rate limit key (e.g., user IP or user ID)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            True if request is allowed, False otherwise
        """
        current_count = await self.redis_manager.increment(key)
        
        if current_count == 1:
            # First request in window, set expiration
            await self.redis_manager.expire(key, window_seconds)
        
        return current_count <= limit
    
    async def get_remaining_attempts(self, key: str, limit: int) -> int:
        """Get remaining attempts for a rate limit key."""
        current_count = await self.redis_manager.redis_client.get(key)
        if current_count is None:
            return limit
        
        current_count = int(current_count)
        return max(0, limit - current_count)


class SessionCache:
    """
    Session cache manager for storing active sessions.
    Provides fast session validation and management.
    """
    
    def __init__(self, redis_manager: RedisManager, session_ttl: int = 1800):
        self.redis_manager = redis_manager
        self.session_ttl = session_ttl
    
    async def store_session(self, session_id: str, user_data: Dict[str, Any]):
        """Store session data in cache."""
        key = f"session:{session_id}"
        await self.redis_manager.set(key, json.dumps(user_data), expire=self.session_ttl)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from cache."""
        key = f"session:{session_id}"
        data = await self.redis_manager.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None
    
    async def delete_session(self, session_id: str):
        """Delete session from cache."""
        key = f"session:{session_id}"
        await self.redis_manager.delete(key)
    
    async def extend_session(self, session_id: str):
        """Extend session expiration."""
        key = f"session:{session_id}"
        await self.redis_manager.expire(key, self.session_ttl)


class RedisConnection:
    """
    Singleton Redis connection manager.
    Ensures single connection per service instance.
    """
    
    _instance: Optional['RedisConnection'] = None
    _redis_manager: Optional[RedisManager] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, redis_url: str):
        """Initialize Redis connection."""
        if self._redis_manager is None:
            self._redis_manager = RedisManager(redis_url)
            logger.info("Redis connection initialized")
    
    def get_manager(self) -> RedisManager:
        """Get Redis manager instance."""
        if self._redis_manager is None:
            raise RuntimeError("Redis not initialized. Call initialize() first.")
        return self._redis_manager
    
    def get_cache_manager(self, default_ttl: int = 3600) -> CacheManager:
        """Get cache manager instance."""
        return CacheManager(self.get_manager(), default_ttl)
    
    def get_distributed_lock(self, lock_key: str, timeout: int = 10) -> DistributedLock:
        """Get distributed lock instance."""
        return DistributedLock(self.get_manager(), lock_key, timeout)
    
    def get_rate_limiter(self) -> RateLimiter:
        """Get rate limiter instance."""
        return RateLimiter(self.get_manager())
    
    def get_session_cache(self, session_ttl: int = 1800) -> SessionCache:
        """Get session cache instance."""
        return SessionCache(self.get_manager(), session_ttl)