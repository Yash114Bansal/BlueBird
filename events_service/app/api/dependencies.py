"""
Dependency injection for Events Service.
Provides database sessions, caching, and authentication dependencies.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Generator, Optional, Dict, Any

from ..db.database import DatabaseConnection, EventRepository
from ..db.redis_client import RedisConnection, CacheManager
from ..services.jwt_service import JWTService

# Security scheme
security = HTTPBearer()

# Global instances
db_connection = DatabaseConnection()
redis_connection = RedisConnection()
jwt_service = JWTService()


def get_database_session() -> Generator[Session, None, None]:
    """
    Get database session dependency.
    
    Yields:
        SQLAlchemy database session
    """
    yield from db_connection.get_session()


def get_event_repository(session: Session = Depends(get_database_session)) -> EventRepository:
    """
    Get event repository dependency.
    
    Args:
        session: Database session
        
    Returns:
        Event repository instance
    """
    return EventRepository(session)


async def get_cache_manager() -> CacheManager:
    """
    Get cache manager dependency.
    
    Returns:
        Cache manager instance
    """
    redis_manager = redis_connection.get_manager()
    cache_manager = CacheManager(redis_manager.redis_client)
    if not hasattr(cache_manager, '_initialized'):
        await cache_manager.initialize()
    return cache_manager


async def get_jwt_service() -> JWTService:
    """
    Get JWT service dependency.
    
    Returns:
        JWT service instance
    """
    if not jwt_service._initialized:
        await jwt_service.initialize()
    return jwt_service


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_svc: JWTService = Depends(get_jwt_service)
) -> Dict[str, Any]:
    """
    Get current authenticated user dependency.
    
    Args:
        credentials: HTTP authorization credentials
        jwt_svc: JWT service
        
    Returns:
        Current authenticated user data
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        user_data = jwt_svc.verify_token(token)
        
        if user_data is None:
            raise credentials_exception
        
        return user_data
        
    except Exception:
        raise credentials_exception


async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current admin user dependency.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Current admin user data
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_optional_current_user(
    request: Request,
    jwt_svc: JWTService = Depends(get_jwt_service)
) -> Optional[Dict[str, Any]]:
    """
    Get current user dependency that doesn't raise exception if not authenticated.
    
    Args:
        request: FastAPI request object
        jwt_svc: JWT service
        
    Returns:
        Current user if authenticated, None otherwise
    """
    authorization = request.headers.get("Authorization")
    
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    try:
        token = authorization.split(" ")[1]
        user_data = jwt_svc.verify_token(token)
        return user_data
        
    except Exception:
        return None


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
    
    # Fallback to direct connection
    if request.client:
        return request.client.host
    
    return "unknown"