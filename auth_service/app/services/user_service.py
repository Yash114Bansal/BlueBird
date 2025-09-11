"""
User management service.
Handles user registration, authentication, and profile management.
"""

from typing import Optional
import logging

from ..models.user import User, UserRole
from ..db.database import UserRepository
from ..schemas.auth import UserCreate, UserLogin, PasswordChange
from .password_manager import PasswordManager

logger = logging.getLogger(__name__)


class UserService:
    """
    User management service.
    Handles user registration, authentication, and profile management.
    """
    
    def __init__(self, password_manager: PasswordManager):
        self.password_manager = password_manager
    
    async def register_user(self, user_data: UserCreate, user_repo: UserRepository) -> Optional[User]:
        """
        Register a new user.
        
        Args:
            user_data: User creation data
            user_repo: User repository instance
            
        Returns:
            Created user or None if registration failed
        """
        try:
            # Check if user already exists
            existing_user = user_repo.get_by_email(user_data.email)
            if existing_user:
                logger.warning(f"User registration failed: email {user_data.email} already exists")
                return None
            
            existing_username = user_repo.get_by_username(user_data.username)
            if existing_username:
                logger.warning(f"User registration failed: username {user_data.username} already exists")
                return None
            
            # Hash password and create user
            hashed_password = self.password_manager.hash_password(user_data.password)
            
            user = user_repo.create(
                email=user_data.email,
                username=user_data.username,
                full_name=user_data.full_name,
                hashed_password=hashed_password,
                role=UserRole.USER
            )
            
            logger.info(f"User registered successfully: {user.email}")
            return user
            
        except Exception as e:
            logger.error(f"User registration failed: {e}")
            return None
    
    async def authenticate_user(self, login_data: UserLogin, user_repo: UserRepository) -> Optional[User]:
        """
        Authenticate a user with email and password.
        
        Args:
            login_data: Login credentials
            user_repo: User repository instance
            
        Returns:
            Authenticated user or None if authentication failed
        """
        try:
            # Find user by email
            user = user_repo.get_by_email(login_data.email)
            if not user:
                logger.warning(f"Authentication failed: user not found for email {login_data.email}")
                return None
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Authentication failed: user {user.email} is inactive")
                return None
            
            # Verify password
            if not self.password_manager.verify_password(login_data.password, user.hashed_password):
                logger.warning(f"Authentication failed: invalid password for user {user.email}")
                return None
            
            # Update last login
            user_repo.update_last_login(user.id)
            
            logger.info(f"User authenticated successfully: {user.email}")
            return user
            
        except Exception as e:
            logger.error(f"User authentication failed: {e}")
            return None
    
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
        try:
            user = user_repo.get_by_id(user_id)
            if not user:
                logger.warning(f"Password change failed: user {user_id} not found")
                return False
            
            # Verify current password
            if not self.password_manager.verify_password(password_data.current_password, user.hashed_password):
                logger.warning(f"Password change failed: invalid current password for user {user_id}")
                return False
            
            # Hash new password and update
            new_hashed_password = self.password_manager.hash_password(password_data.new_password)
            user_repo.update(user_id, hashed_password=new_hashed_password)
            
            logger.info(f"Password changed successfully for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Password change failed: {e}")
            return False
    
    async def update_user_profile(
        self, 
        user_id: int, 
        update_data: dict, 
        user_repo: UserRepository
    ) -> Optional[User]:
        """
        Update user profile information.
        
        Args:
            user_id: User ID
            update_data: Update data dictionary
            user_repo: User repository instance
            
        Returns:
            Updated user or None if update failed
        """
        try:
            # Check if email is being changed and if it's already taken
            if "email" in update_data:
                existing_user = user_repo.get_by_email(update_data["email"])
                if existing_user and existing_user.id != user_id:
                    logger.warning(f"Profile update failed: email {update_data['email']} already exists")
                    return None
            
            # Check if username is being changed and if it's already taken
            if "username" in update_data:
                existing_user = user_repo.get_by_username(update_data["username"])
                if existing_user and existing_user.id != user_id:
                    logger.warning(f"Profile update failed: username {update_data['username']} already exists")
                    return None
            
            # Update user
            updated_user = user_repo.update(user_id, **update_data)
            
            if updated_user:
                logger.info(f"User profile updated successfully for user {user_id}")
            
            return updated_user
            
        except Exception as e:
            logger.error(f"User profile update failed: {e}")
            return None
    
    async def deactivate_user(self, user_id: int, user_repo: UserRepository) -> bool:
        """
        Deactivate a user account.
        
        Args:
            user_id: User ID
            user_repo: User repository instance
            
        Returns:
            True if deactivation successful, False otherwise
        """
        try:
            updated_user = user_repo.update(user_id, is_active=False)
            if updated_user:
                logger.info(f"User {user_id} deactivated successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"User deactivation failed: {e}")
            return False
    
    async def get_user_by_id(self, user_id: int, user_repo: UserRepository) -> Optional[User]:
        """Get user by ID."""
        return user_repo.get_by_id(user_id)
    
    async def get_user_by_email(self, email: str, user_repo: UserRepository) -> Optional[User]:
        """Get user by email."""
        return user_repo.get_by_email(email)
    
    async def get_user_by_username(self, username: str, user_repo: UserRepository) -> Optional[User]:
        """Get user by username."""
        return user_repo.get_by_username(username)