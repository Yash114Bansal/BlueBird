"""
Dependency injection for Analytics Service.
Provides database sessions, authentication, and service dependencies.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Generator, Optional
import jwt
import logging
from datetime import datetime

from ..db.database import DatabaseConnection, DatabaseManager
from ..db.redis_client import RedisConnection, RedisManager
from ..services.analytics_service import AnalyticsService
from ..services.event_subscriber import EventSubscriber
from ..core.config import config

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Global instances
db_connection = DatabaseConnection()
redis_connection = RedisConnection()


def get_database_session() -> Generator[Session, None, None]:
    """
    Get database session dependency.
    
    Yields:
        SQLAlchemy database session
    """
    yield from db_connection.get_session()


def get_database_manager() -> DatabaseManager:
    """
    Get database manager dependency.
    
    Returns:
        Database manager instance
    """
    # Force re-check of database initialization
    if not hasattr(db_connection, '_manager') or db_connection._manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized. Service is starting up."
        )
    
    try:
        return db_connection.get_manager()
    except RuntimeError as e:
        if "not initialized" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not initialized. Service is starting up."
            )
        raise


def get_redis_manager() -> RedisManager:
    """
    Get Redis manager dependency.
    
    Returns:
        Redis manager instance
    """
    try:
        return redis_connection.get_manager()
    except RuntimeError as e:
        if "not initialized" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis not initialized. Service is starting up."
            )
        raise


def get_analytics_service(
    db_manager: DatabaseManager = Depends(get_database_manager),
    redis_manager: RedisManager = Depends(get_redis_manager)
) -> AnalyticsService:
    """
    Get analytics service dependency.
    
    Args:
        db_manager: Database manager
        redis_manager: Redis manager
        
    Returns:
        Analytics service instance
    """
    return AnalyticsService(db_manager, redis_manager)


def get_event_subscriber(
    db_manager: DatabaseManager = Depends(get_database_manager),
    redis_manager: RedisManager = Depends(get_redis_manager)
) -> EventSubscriber:
    """
    Get event subscriber dependency.
    
    Args:
        db_manager: Database manager
        redis_manager: Redis manager
        
    Returns:
        Event subscriber instance
    """
    return EventSubscriber(db_manager, redis_manager)


async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify admin JWT token using PyJWT and secrets.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        Token payload if valid
        
    Raises:
        HTTPException: If token is invalid or user is not admin
    """
    try:
        # Get JWT secret and algorithm from config
        jwt_secret = await config.get_jwt_secret()
        jwt_algorithm = await config.get_jwt_algorithm()
        
        # Decode and verify JWT token
        try:
            payload = jwt.decode(
                credentials.credentials,
                jwt_secret,
                algorithms=[jwt_algorithm]
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Check if user is admin
        if payload.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Check if token is not expired (additional check)
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        
        return payload
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )


async def get_current_admin(
    token_data: dict = Depends(verify_admin_token)
) -> dict:
    """
    Get current admin user from verified token.
    
    Args:
        token_data: Verified token data
        
    Returns:
        Admin user data
    """
    return {
        "user_id": token_data.get("user_id"),
        "email": token_data.get("email"),
        "username": token_data.get("username"),
        "role": token_data.get("role")
    }


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    # Check for forwarded headers first (for load balancers/proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"


async def rate_limit_check(
    request: Request,
    redis_manager: RedisManager = Depends(get_redis_manager)
) -> bool:
    """
    Check rate limiting for analytics requests.
    
    Args:
        request: FastAPI request object
        redis_manager: Redis manager
        
    Returns:
        True if request is allowed, False if rate limited
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    try:
        # Get rate limit config
        rate_config = await config.get_rate_limit_config()
        limit = rate_config.get("analytics_requests", 100)
        window = rate_config.get("window_minutes", 15)
        
        # Get client IP
        client_ip = get_client_ip(request)
        
        # Create rate limit key
        rate_key = f"rate_limit:analytics:{client_ip}"
        
        # Check current count
        current_count = await redis_manager.get(rate_key)
        
        if current_count is None:
            # First request in window
            await redis_manager.set(rate_key, "1", window * 60)
            return True
        
        count = int(current_count)
        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {limit} requests per {window} minutes."
            )
        
        # Increment counter
        await redis_manager.set(rate_key, str(count + 1), window * 60)
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return True