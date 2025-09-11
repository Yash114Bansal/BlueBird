"""
Dependency injection for Auth Service.
Provides database sessions and authentication dependencies.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Generator, Optional

from ..db.database import DatabaseConnection, UserRepository, UserSessionRepository
from ..services.auth_service import AuthenticationService
from ..models.user import User
from ..schemas.auth import TokenData

# Security scheme
security = HTTPBearer()

# Global instances
db_connection = DatabaseConnection()
auth_service = AuthenticationService()


def get_database_session() -> Generator[Session, None, None]:
    """
    Get database session dependency.
    
    Yields:
        SQLAlchemy database session
    """
    yield from db_connection.get_session()


def get_user_repository(session: Session = Depends(get_database_session)) -> UserRepository:
    """
    Get user repository dependency.
    
    Args:
        session: Database session
        
    Returns:
        User repository instance
    """
    return UserRepository(session)


def get_session_repository(session: Session = Depends(get_database_session)) -> UserSessionRepository:
    """
    Get session repository dependency.
    
    Args:
        session: Database session
        
    Returns:
        Session repository instance
    """
    return UserSessionRepository(session)


async def get_auth_service() -> AuthenticationService:
    """
    Get authentication service dependency.
    
    Returns:
        Authentication service instance
    """
    if not auth_service._initialized:
        await auth_service.initialize()
    return auth_service


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    """
    Get current authenticated user dependency.
    
    Args:
        credentials: HTTP authorization credentials
        auth_service: Authentication service
        user_repo: User repository
        
    Returns:
        Current authenticated user
        
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
        user = await auth_service.get_user_from_token(token, user_repo)
        
        if user is None:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user"
            )
        
        return user
        
    except Exception:
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user dependency.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current admin user dependency.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Current admin user
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_optional_current_user(
    request: Request,
    auth_service: AuthenticationService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
) -> Optional[User]:
    """
    Get current user dependency that doesn't raise exception if not authenticated.
    
    Args:
        request: FastAPI request object
        auth_service: Authentication service
        user_repo: User repository
        
    Returns:
        Current user if authenticated, None otherwise
    """
    authorization = request.headers.get("Authorization")
    
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    try:
        token = authorization.split(" ")[1]
        user = await auth_service.get_user_from_token(token, user_repo)
        
        if user and user.is_active:
            return user
        
        return None
        
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


def get_user_agent(request: Request) -> str:
    """
    Get user agent from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User agent string
    """
    return request.headers.get("User-Agent", "unknown")


class RateLimitDependency:
    """
    Rate limiting dependency for authentication endpoints.
    """
    
    def __init__(self, limit: int, window_seconds: int = 900):
        self.limit = limit
        self.window_seconds = window_seconds
    
    async def __call__(self, request: Request) -> bool:
        """
        Check rate limit for the request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if request is allowed
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # TODO: Implement rate limiting
        
        return True


# Rate limiting dependencies
login_rate_limit = RateLimitDependency(limit=5, window_seconds=900)
register_rate_limit = RateLimitDependency(limit=3, window_seconds=900)
password_reset_rate_limit = RateLimitDependency(limit=3, window_seconds=3600)