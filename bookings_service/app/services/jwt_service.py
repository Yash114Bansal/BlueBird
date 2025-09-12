"""
JWT Service for Bookings Service.
Handles JWT token validation and user authentication.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from app.core.config import config

logger = logging.getLogger(__name__)


class JWTService:
    """
    JWT service for token validation and user authentication.
    Integrates with the auth service for user verification.
    """
    
    def __init__(self):
        self.jwt_secret = None
        self.jwt_algorithm = None
        self.jwt_expiry_minutes = None
    
    async def _get_config(self):
        """Get JWT configuration."""
        if not self.jwt_secret:
            self.jwt_secret = await config.get_jwt_secret()
            self.jwt_algorithm = await config.get_jwt_algorithm()
            self.jwt_expiry_minutes = await config.get_jwt_expiry_minutes()
    
    async def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate JWT token.
        
        Args:
            token: JWT token to decode
            
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            await self._get_config()
            
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"JWT decoding error: {e}")
            return None
    
    async def get_user_id(self, token: str) -> Optional[int]:
        """
        Extract user ID from JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            User ID if valid, None otherwise
        """
        payload = await self.decode_token(token)
        if payload:
            return payload.get("user_id")
        return None
    
    async def get_user_role(self, token: str) -> Optional[str]:
        """
        Extract user role from JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            User role if valid, None otherwise
        """
        payload = await self.decode_token(token)
        if payload:
            return payload.get("role")
        return None
    
    async def is_admin(self, token: str) -> bool:
        """
        Check if user is admin from JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            True if user is admin, False otherwise
        """
        role = await self.get_user_role(token)
        return role == "admin"
    
    async def validate_token(self, token: str) -> bool:
        """
        Validate JWT token.
        
        Args:
            token: JWT token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        payload = await self.decode_token(token)
        return payload is not None
    
    async def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive token information.
        
        Args:
            token: JWT token
            
        Returns:
            Dictionary with token information or None if invalid
        """
        payload = await self.decode_token(token)
        if not payload:
            return None
        
        return {
            "user_id": payload.get("user_id"),
            "role": payload.get("role"),
            "email": payload.get("email"),
            "username": payload.get("username"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
            "is_expired": datetime.now().timestamp() > payload.get("exp", 0)
        }


# Global service instance
jwt_service = JWTService()