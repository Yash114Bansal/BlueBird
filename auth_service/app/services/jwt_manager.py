"""
JWT token management service.
Handles token creation, validation, and refresh.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import logging

from ..core.config import config
from ..schemas.auth import TokenData

logger = logging.getLogger(__name__)


class JWTManager:
    """
    JWT token management service.
    Handles token creation, validation, and refresh.
    """
    
    def __init__(self):
        self.secret_key: Optional[str] = None
        self.algorithm: Optional[str] = None
        self.access_token_expire_minutes: Optional[int] = None
        self.refresh_token_expire_days: Optional[int] = None
    
    async def initialize(self):
        """Initialize JWT configuration from secrets."""
        self.secret_key = await config.get_jwt_secret()
        self.algorithm = await config.get_jwt_algorithm()
        self.access_token_expire_minutes = await config.get_jwt_expiry_minutes()
        self.refresh_token_expire_days = await config.get_refresh_token_expiry_days()
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[TokenData]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != token_type:
                return None
            
            user_id: int = payload.get("user_id")
            email: str = payload.get("email")
            role: str = payload.get("role")
            
            if user_id is None or email is None:
                return None
            
            return TokenData(user_id=user_id, email=email, role=role)
            
        except JWTError:
            return None
    
    def create_token_pair(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """Create both access and refresh tokens for a user."""
        access_token = self.create_access_token(user_data)
        refresh_token = self.create_refresh_token(user_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    
    def get_token_expiry(self) -> int:
        """Get access token expiry time in seconds."""
        return self.access_token_expire_minutes * 60