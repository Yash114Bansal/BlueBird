"""
JWT service for Events Service.
Handles token validation for authentication.
"""

from typing import Optional, Dict, Any
from jose import JWTError, jwt
import logging

from ..core.config import config

logger = logging.getLogger(__name__)


class JWTService:
    """
    JWT service for token validation.
    """
    
    def __init__(self):
        self.secret_key: Optional[str] = None
        self.algorithm: Optional[str] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize JWT configuration from secrets."""
        self.secret_key = await config.get_jwt_secret()
        self.algorithm = await config.get_jwt_algorithm()
        self._initialized = True
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Token payload if valid, None otherwise
        """
        if not self._initialized:
            logger.error("JWT service not initialized")
            return None
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token has required fields
            if not all(key in payload for key in ["user_id", "email", "role"]):
                return None
            
            return payload
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during JWT verification: {e}")
            return None