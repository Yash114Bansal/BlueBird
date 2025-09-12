"""
Redis client for Bookings Service.
Handles caching, distributed locking, and high consistency operations.
"""

import asyncio
import json
import time
from typing import Optional, Dict, Any, Union
import redis.asyncio as redis
from redis.asyncio import Redis
import logging

from app.core.config import config

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Redis manager for high consistency operations.
    Handles caching, distributed locking, and session management.
    """
    
    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Redis connection."""
        if self._initialized:
            return
        
        try:
            redis_url = await config.get_redis_url()
            self.redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            self._initialized = True
            logger.info("Redis client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Redis connection closed")
    
    # Cache Operations
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self._initialized:
            await self.initialize()
        
        try:
            return await self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        if not self._initialized:
            await self.initialize()
        
        try:
            if ttl:
                return await self.redis_client.setex(key, ttl, value)
            else:
                return await self.redis_client.set(key, value)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._initialized:
            await self.initialize()
        
        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self._initialized:
            await self.initialize()
        
        try:
            result = await self.redis_client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False
    
    # JSON Operations
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value from cache."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for key {key}: {e}")
        return None
    
    async def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set JSON value in cache."""
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, ttl)
        except json.JSONEncodeError as e:
            logger.error(f"JSON encode error for key {key}: {e}")
            return False
    
    # Distributed Locking for High Consistency
    async def acquire_lock(self, lock_key: str, timeout: int = 30, blocking_timeout: int = 10) -> bool:
        """
        Acquire a distributed lock for high consistency operations.
        
        Args:
            lock_key: Unique key for the lock
            timeout: Lock timeout in seconds
            blocking_timeout: Maximum time to wait for lock acquisition
            
        Returns:
            True if lock acquired, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        lock_value = f"{time.time()}:{asyncio.current_task().get_name()}"
        end_time = time.time() + blocking_timeout
        
        while time.time() < end_time:
            try:
                # Try to acquire lock with SET NX EX
                result = await self.redis_client.set(
                    lock_key, 
                    lock_value, 
                    nx=True,  # Only set if not exists
                    ex=timeout  # Expire after timeout seconds
                )
                
                if result:
                    logger.debug(f"Distributed lock acquired: {lock_key}")
                    return True
                
                # Wait a bit before retrying
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error acquiring lock {lock_key}: {e}")
                return False
        
        logger.warning(f"Failed to acquire lock {lock_key} within {blocking_timeout}s")
        return False
    
    async def release_lock(self, lock_key: str) -> bool:
        """
        Release a distributed lock.
        
        Args:
            lock_key: Lock key to release
            
        Returns:
            True if lock released, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            result = await self.redis_client.delete(lock_key)
            if result > 0:
                logger.debug(f"Distributed lock released: {lock_key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error releasing lock {lock_key}: {e}")
            return False
    
    async def extend_lock(self, lock_key: str, additional_time: int) -> bool:
        """
        Extend the timeout of an existing lock.
        
        Args:
            lock_key: Lock key to extend
            additional_time: Additional time in seconds
            
        Returns:
            True if lock extended, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            result = await self.redis_client.expire(lock_key, additional_time)
            if result:
                logger.debug(f"Distributed lock extended: {lock_key} by {additional_time}s")
                return True
            return False
        except Exception as e:
            logger.error(f"Error extending lock {lock_key}: {e}")
            return False
    
    # Atomic Operations for High Consistency
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Atomically increment a counter."""
        if not self._initialized:
            await self.initialize()
        
        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis increment error for key {key}: {e}")
            return None
    
    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """Atomically decrement a counter."""
        if not self._initialized:
            await self.initialize()
        
        try:
            return await self.redis_client.decrby(key, amount)
        except Exception as e:
            logger.error(f"Redis decrement error for key {key}: {e}")
            return None
    
    async def set_if_not_exists(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value only if key doesn't exist (atomic operation)."""
        if not self._initialized:
            await self.initialize()
        
        try:
            if ttl:
                result = await self.redis_client.set(key, value, nx=True, ex=ttl)
            else:
                result = await self.redis_client.set(key, value, nx=True)
            return result is not None
        except Exception as e:
            logger.error(f"Redis set_if_not_exists error for key {key}: {e}")
            return False
    
    # Pattern Operations
    async def get_keys(self, pattern: str) -> list:
        """Get all keys matching pattern."""
        if not self._initialized:
            await self.initialize()
        
        try:
            return await self.redis_client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis keys error for pattern {pattern}: {e}")
            return []
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self._initialized:
            await self.initialize()
        
        try:
            keys = await self.get_keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis delete_pattern error for pattern {pattern}: {e}")
            return 0
    
    # Health Check
    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            if not self._initialized:
                await self.initialize()
            
            result = await self.redis_client.ping()
            return result is True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Global Redis manager instance
redis_manager = RedisManager()


# Context manager for distributed locks
class DistributedLock:
    """
    Context manager for distributed locks with automatic cleanup.
    """
    
    def __init__(self, redis_manager: RedisManager, lock_key: str, timeout: int = 30, blocking_timeout: int = 10):
        self.redis_manager = redis_manager
        self.lock_key = lock_key
        self.timeout = timeout
        self.blocking_timeout = blocking_timeout
        self.acquired = False
    
    async def __aenter__(self):
        self.acquired = await self.redis_manager.acquire_lock(
            self.lock_key, 
            self.timeout, 
            self.blocking_timeout
        )
        if not self.acquired:
            raise RuntimeError(f"Failed to acquire lock: {self.lock_key}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            await self.redis_manager.release_lock(self.lock_key)
            self.acquired = False


# Utility functions
def get_distributed_lock(lock_key: str, timeout: int = 30, blocking_timeout: int = 10) -> DistributedLock:
    """Get a distributed lock context manager."""
    return DistributedLock(redis_manager, lock_key, timeout, blocking_timeout)