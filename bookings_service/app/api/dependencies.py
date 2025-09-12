"""
API dependencies for Bookings Service.
Handles authentication, authorization, and common dependencies.
"""

import asyncio
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
import logging

from app.core.config import config
from app.db.database import get_db, get_async_db
from app.db.redis_client import redis_manager
from app.schemas.booking import BookingErrorResponse

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


class AuthorizationError(Exception):
    """Custom exception for authorization errors."""
    pass


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    Extract and validate user ID from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        User ID from the token
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Get JWT configuration
        jwt_secret = await config.get_jwt_secret()
        jwt_algorithm = await config.get_jwt_algorithm()
        
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            jwt_secret,
            algorithms=[jwt_algorithm]
        )
        
        # Extract user ID
        user_id = payload.get("user_id")
        if not user_id:
            raise AuthenticationError("Invalid token: missing user_id")
        
        # Check if user is active (optional - depends on your auth service)
        
        return int(user_id)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_role(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Extract and validate user role from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        User role from the token
        
    Raises:
        HTTPException: If token is invalid or user is not authorized
    """
    try:
        # Get JWT configuration
        jwt_secret = await config.get_jwt_secret()
        jwt_algorithm = await config.get_jwt_algorithm()
        
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            jwt_secret,
            algorithms=[jwt_algorithm]
        )
        
        # Extract user role
        user_role = payload.get("role")
        if not user_role:
            raise AuthenticationError("Invalid token: missing role")
        
        return user_role
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Role extraction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin_role(user_role: str = Depends(get_current_user_role)) -> str:
    """
    Require admin role for access.
    
    Args:
        user_role: User role from JWT token
        
    Returns:
        User role if admin
        
    Raises:
        HTTPException: If user is not admin
    """
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user_role


async def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    
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


async def get_user_agent(request: Request) -> str:
    """
    Extract user agent from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User agent string
    """
    return request.headers.get("User-Agent", "unknown")


async def check_booking_permissions(
    booking_id: int,
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role),
    db: Session = Depends(get_db)
) -> int:
    """
    Check if user has permission to access a specific booking.
    
    Args:
        booking_id: ID of the booking to check
        user_id: Current user ID
        user_role: Current user role
        db: Database session
        
    Returns:
        Booking ID if access is allowed
        
    Raises:
        HTTPException: If access is denied or booking not found
    """
    from app.models.booking import Booking
    
    # Admins can access any booking
    if user_role == "admin":
        return booking_id
    
    # Regular users can only access their own bookings
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.user_id == user_id
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found or access denied"
        )
    
    return booking_id


async def validate_booking_ownership(
    booking_id: int,
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role),
    db: Session = Depends(get_db)
) -> int:
    """
    Validate that user owns the booking (for operations like cancel).
    
    Args:
        booking_id: ID of the booking to validate
        user_id: Current user ID
        user_role: Current user role
        db: Database session
        
    Returns:
        Booking ID if ownership is validated
        
    Raises:
        HTTPException: If ownership validation fails
    """
    from app.models.booking import Booking
    
    # Admins can operate on any booking
    if user_role == "admin":
        return booking_id
    
    # Regular users can only operate on their own bookings
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.user_id == user_id
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found or you don't have permission to access it"
        )
    
    return booking_id


async def get_redis_client():
    """
    Get Redis client instance.
    
    Returns:
        Redis client instance
    """
    if not redis_manager._initialized:
        await redis_manager.initialize()
    return redis_manager


async def check_service_health() -> Dict[str, Any]:
    """
    Check the health of all service dependencies.
    
    Returns:
        Dictionary with health status of all components
    """
    health_status = {
        "database": "unknown",
        "redis": "unknown",
        "overall": "unknown"
    }
    
    try:
        # Check database connection
        db = next(get_db())
        db.execute("SELECT 1")
        health_status["database"] = "healthy"
        db.close()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = "unhealthy"
    
    try:
        # Check Redis connection
        redis_healthy = await redis_manager.health_check()
        health_status["redis"] = "healthy" if redis_healthy else "unhealthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["redis"] = "unhealthy"
    
    # Overall health
    if health_status["database"] == "healthy" and health_status["redis"] == "healthy":
        health_status["overall"] = "healthy"
    else:
        health_status["overall"] = "unhealthy"
    
    return health_status


# Common dependency combinations
async def get_authenticated_user(
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role),
    client_ip: str = Depends(get_client_ip),
    user_agent: str = Depends(get_user_agent)
) -> Dict[str, Any]:
    """
    Get complete authenticated user information.
    
    Returns:
        Dictionary with user information and request metadata
    """
    return {
        "user_id": user_id,
        "user_role": user_role,
        "client_ip": client_ip,
        "user_agent": user_agent
    }


async def get_admin_user(
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(require_admin_role),
    client_ip: str = Depends(get_client_ip),
    user_agent: str = Depends(get_user_agent)
) -> Dict[str, Any]:
    """
    Get authenticated admin user information.
    
    Returns:
        Dictionary with admin user information and request metadata
    """
    return {
        "user_id": user_id,
        "user_role": user_role,
        "client_ip": client_ip,
        "user_agent": user_agent
    }