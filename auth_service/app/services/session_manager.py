"""
Session management service.
Handles user session creation, validation, and cleanup.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from ..models.user import User, UserSession
from ..db.database import UserSessionRepository
from .jwt_manager import JWTManager

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Session management service.
    Handles user session lifecycle and validation.
    """
    
    def __init__(self, jwt_manager: JWTManager):
        self.jwt_manager = jwt_manager
    
    async def create_user_session(
        self, 
        user: User, 
        session_repo: UserSessionRepository,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[UserSession]:
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
        try:
            # Generate tokens
            user_data = {
                "user_id": user.id,
                "email": user.email,
                "role": user.role.value
            }
            tokens = self.jwt_manager.create_token_pair(user_data)
            
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(days=self.jwt_manager.refresh_token_expire_days)
            
            # Create session
            session = session_repo.create(
                user_id=user.id,
                session_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(f"Session created for user {user.email}")
            return session
            
        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            return None
    
    async def refresh_access_token(self, refresh_token: str, session_repo: UserSessionRepository) -> Optional[Dict[str, str]]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            session_repo: Session repository instance
            
        Returns:
            New token pair or None if refresh failed
        """
        try:
            # Verify refresh token
            token_data = self.jwt_manager.verify_token(refresh_token, "refresh")
            if not token_data:
                logger.warning("Token refresh failed: invalid refresh token")
                return None
            
            # Find session
            session = session_repo.get_by_refresh_token(refresh_token)
            if not session or not session.is_active:
                logger.warning("Token refresh failed: session not found or inactive")
                return None
            
            # Check if session is expired
            if session.expires_at < datetime.utcnow():
                logger.warning("Token refresh failed: session expired")
                session.is_active = False
                session_repo.session.commit()
                return None
            
            # Create new token pair
            user_data = {
                "user_id": token_data.user_id,
                "email": token_data.email,
                "role": token_data.role
            }
            new_tokens = self.jwt_manager.create_token_pair(user_data)
            
            # Update session with new tokens
            session.session_token = new_tokens["access_token"]
            session.refresh_token = new_tokens["refresh_token"]
            session.last_accessed = datetime.utcnow()
            session_repo.session.commit()
            
            logger.info(f"Tokens refreshed for user {token_data.user_id}")
            return new_tokens
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return None
    
    async def logout_user(self, access_token: str, session_repo: UserSessionRepository) -> bool:
        """
        Logout user by deactivating session.
        
        Args:
            access_token: User's access token
            session_repo: Session repository instance
            
        Returns:
            True if logout successful, False otherwise
        """
        try:
            session = session_repo.get_by_token(access_token)
            if session:
                session.is_active = False
                session_repo.session.commit()
                logger.info(f"User logged out: session {session.id}")
                return True
            
            logger.warning("Logout failed: session not found")
            return False
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    async def cleanup_expired_sessions(self, session_repo: UserSessionRepository) -> int:
        """
        Clean up expired sessions.
        
        Args:
            session_repo: Session repository instance
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            return session_repo.cleanup_expired_sessions()
        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")
            return 0
    
    async def deactivate_user_sessions(self, user_id: int, session_repo: UserSessionRepository) -> bool:
        """
        Deactivate all sessions for a user.
        
        Args:
            user_id: User ID
            session_repo: Session repository instance
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session_repo.deactivate_user_sessions(user_id)
            logger.info(f"Deactivated all sessions for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate user sessions: {e}")
            return False