"""
Main authentication service.
Orchestrates user authentication, registration, and session management.
"""

from typing import Optional, Dict, Any
import logging

from ..models.user import User
from ..db.database import UserRepository, UserSessionRepository
from ..schemas.auth import TokenData, UserCreate, UserLogin, PasswordChange
from .user_service import UserService
from .session_manager import SessionManager
from .jwt_manager import JWTManager
from .password_manager import PasswordManager

logger = logging.getLogger(__name__)


class AuthenticationService:
    """
    Main authentication service.
    Orchestrates user authentication, registration, and session management.
    """
    
    def __init__(self):
        self.password_manager = PasswordManager()
        self.jwt_manager = JWTManager()
        self.user_service = UserService(self.password_manager)
        self.session_manager = SessionManager(self.jwt_manager)
        self._initialized = False
    
    async def initialize(self):
        """Initialize the authentication service."""
        if not self._initialized:
            await self.jwt_manager.initialize()
            self._initialized = True
    
    async def register_user(self, user_data: UserCreate, user_repo: UserRepository) -> Optional[User]:
        """
        Register a new user.
        
        Args:
            user_data: User creation data
            user_repo: User repository instance
            
        Returns:
            Created user or None if registration failed
        """
        return await self.user_service.register_user(user_data, user_repo)
    
    async def authenticate_user(self, login_data: UserLogin, user_repo: UserRepository) -> Optional[User]:
        """
        Authenticate a user with email and password.
        
        Args:
            login_data: Login credentials
            user_repo: User repository instance
            
        Returns:
            Authenticated user or None if authentication failed
        """
        return await self.user_service.authenticate_user(login_data, user_repo)
    
    async def create_user_session(
        self, 
        user: User, 
        session_repo: UserSessionRepository,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Any]:
        """
        Create a new user session.
        
        Args:
            user: Authenticated user
            session_repo: Session repository instance
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created session or None if creation failed
        """
        return await self.session_manager.create_user_session(
            user, session_repo, ip_address, user_agent
        )
    
    async def refresh_access_token(self, refresh_token: str, session_repo: UserSessionRepository) -> Optional[Dict[str, str]]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            session_repo: Session repository instance
            
        Returns:
            New token pair or None if refresh failed
        """
        return await self.session_manager.refresh_access_token(refresh_token, session_repo)
    
    async def logout_user(self, access_token: str, session_repo: UserSessionRepository) -> bool:
        """
        Logout user by deactivating session.
        
        Args:
            access_token: User's access token
            session_repo: Session repository instance
            
        Returns:
            True if logout successful, False otherwise
        """
        return await self.session_manager.logout_user(access_token, session_repo)
    
    async def change_password(
        self, 
        user_id: int, 
        password_data: PasswordChange, 
        user_repo: UserRepository
    ) -> bool:
        """
        Change user password.
        
        Args:
            user_id: User ID
            password_data: Password change data
            user_repo: User repository instance
            
        Returns:
            True if password changed successfully, False otherwise
        """
        return await self.user_service.change_password(user_id, password_data, user_repo)
    
    async def update_user_profile(
        self, 
        user_id: int, 
        update_data: dict, 
        user_repo: UserRepository,
        is_admin: bool = False
    ) -> Optional[User]:
        """
        Update user profile information.
        
        Args:
            user_id: User ID
            update_data: Update data dictionary
            user_repo: User repository instance
            is_admin: Whether the requesting user is an admin
            
        Returns:
            Updated user or None if update failed
        """
        return await self.user_service.update_user_profile(user_id, update_data, user_repo, is_admin)
    
    async def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify access token and return token data."""
        return self.jwt_manager.verify_token(token, "access")
    
    async def get_user_from_token(self, token: str, user_repo: UserRepository) -> Optional[User]:
        """Get user from access token."""
        token_data = await self.verify_token(token)
        if token_data:
            return await self.user_service.get_user_by_id(token_data.user_id, user_repo)
        return None
    
    async def get_token_expiry(self) -> int:
        """Get access token expiry time in seconds."""
        return self.jwt_manager.get_token_expiry()
    
    async def cleanup_expired_sessions(self, session_repo: UserSessionRepository) -> int:
        """
        Clean up expired sessions.
        
        Args:
            session_repo: Session repository instance
            
        Returns:
            Number of sessions cleaned up
        """
        return await self.session_manager.cleanup_expired_sessions(session_repo)
    
    async def deactivate_user_sessions(self, user_id: int, session_repo: UserSessionRepository) -> bool:
        """
        Deactivate all sessions for a user.
        
        Args:
            user_id: User ID
            session_repo: Session repository instance
            
        Returns:
            True if successful, False otherwise
        """
        return await self.session_manager.deactivate_user_sessions(user_id, session_repo)