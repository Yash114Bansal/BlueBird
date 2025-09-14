"""
OTP Service for email verification.
Handles OTP generation, caching, and validation using Redis.
"""

import secrets
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from ..db.redis_client import RedisConnection
from ..core.config import config

logger = logging.getLogger(__name__)


class OTPService:
    """
    OTP service for email verification.
    Handles OTP generation, caching, and validation.
    """
    
    def __init__(self):
        self.redis_connection = RedisConnection()
        self.otp_length = 6
        self.otp_expiry_minutes = 10
        self.max_attempts = 3
        self._initialized = False
    
    async def initialize(self):
        """Initialize the OTP service."""
        if not self._initialized:
            redis_url = await config.get_redis_url()
            self.redis_connection.initialize(redis_url)
            self._initialized = True
            logger.info("OTP service initialized")
    
    def generate_otp(self) -> str:
        """
        Generate a secure 6-digit OTP.
        
        Returns:
            6-digit OTP string
        """
        otp = secrets.randbelow(10**self.otp_length)
        return f"{otp:0{self.otp_length}d}"
    
    async def store_otp(self, email: str, otp: str) -> bool:
        """
        Store OTP in Redis with expiry and attempt tracking.
        
        Args:
            email: User email address
            otp: Generated OTP
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            await self.initialize()
            redis_manager = self.redis_connection.get_manager()
            
            # Create keys for OTP and attempts
            otp_key = f"otp:verification:{email}"
            attempts_key = f"otp:attempts:{email}"
            
            # Store OTP with expiry
            await redis_manager.set(otp_key, otp, expire=self.otp_expiry_minutes * 60)
            
            # Initialize attempts counter
            await redis_manager.set(attempts_key, "0", expire=self.otp_expiry_minutes * 60)
            
            logger.info(f"OTP stored for email {email}, expires in {self.otp_expiry_minutes} minutes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store OTP for {email}: {e}")
            return False
    
    async def validate_otp(self, email: str, provided_otp: str) -> Dict[str, Any]:
        """
        Validate provided OTP against stored OTP.
        
        Args:
            email: User email address
            provided_otp: OTP provided by user
            
        Returns:
            Dictionary with validation result and details
        """
        try:
            await self.initialize()
            redis_manager = self.redis_connection.get_manager()
            
            # Get keys
            otp_key = f"otp:verification:{email}"
            attempts_key = f"otp:attempts:{email}"
            
            # Check if OTP exists
            stored_otp = await redis_manager.get(otp_key)
            if not stored_otp:
                return {
                    "valid": False,
                    "reason": "OTP_NOT_FOUND",
                    "message": "OTP not found or expired"
                }
            
            # Check attempts
            attempts = await redis_manager.get(attempts_key)
            current_attempts = int(attempts) if attempts else 0
            
            if current_attempts >= self.max_attempts:
                # Clear OTP after max attempts
                await redis_manager.delete(otp_key)
                await redis_manager.delete(attempts_key)
                return {
                    "valid": False,
                    "reason": "MAX_ATTEMPTS_EXCEEDED",
                    "message": "Maximum verification attempts exceeded"
                }
            
            # Increment attempts
            await redis_manager.increment(attempts_key, 1)
            try:
                stored_otp = int(stored_otp)
                provided_otp = int(provided_otp)
            except ValueError:
                return {
                    "valid": False,
                    "reason": "INVALID_OTP",
                    "message": "Invalid OTP code"
                }

            # Validate OTP
            if stored_otp == provided_otp:
                # Clear OTP after successful validation
                await redis_manager.delete(otp_key)
                await redis_manager.delete(attempts_key)
                
                logger.info(f"OTP validated successfully for {email}")
                return {
                    "valid": True,
                    "reason": "SUCCESS",
                    "message": "OTP verified successfully"
                }
            else:
                logger.warning(f"Invalid OTP attempt for {email}")
                return {
                    "valid": False,
                    "reason": "INVALID_OTP",
                    "message": "Invalid OTP code"
                }
                
        except Exception as e:
            logger.error(f"Failed to validate OTP for {email}: {e}")
            return {
                "valid": False,
                "reason": "VALIDATION_ERROR",
                "message": "OTP validation failed"
            }
    
    async def get_otp_attempts(self, email: str) -> int:
        """
        Get remaining OTP attempts for an email.
        
        Args:
            email: User email address
            
        Returns:
            Number of attempts made
        """
        try:
            await self.initialize()
            redis_manager = self.redis_connection.get_manager()
            
            attempts_key = f"otp:attempts:{email}"
            attempts = await redis_manager.get(attempts_key)
            
            return int(attempts) if attempts else 0
            
        except Exception as e:
            logger.error(f"Failed to get OTP attempts for {email}: {e}")
            return 0
    
    async def clear_otp(self, email: str) -> bool:
        """
        Clear OTP and attempts for an email.
        
        Args:
            email: User email address
            
        Returns:
            True if cleared successfully, False otherwise
        """
        try:
            await self.initialize()
            redis_manager = self.redis_connection.get_manager()
            
            otp_key = f"otp:verification:{email}"
            attempts_key = f"otp:attempts:{email}"
            
            await redis_manager.delete(otp_key)
            await redis_manager.delete(attempts_key)
            
            logger.info(f"OTP cleared for {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear OTP for {email}: {e}")
            return False
    
    async def is_otp_expired(self, email: str) -> bool:
        """
        Check if OTP is expired for an email.
        
        Args:
            email: User email address
            
        Returns:
            True if expired, False otherwise
        """
        try:
            await self.initialize()
            redis_manager = self.redis_connection.get_manager()
            
            otp_key = f"otp:verification:{email}"
            exists = await redis_manager.exists(otp_key)
            
            return not exists
            
        except Exception as e:
            logger.error(f"Failed to check OTP expiry for {email}: {e}")
            return True
    
    async def get_otp_info(self, email: str) -> Dict[str, Any]:
        """
        Get OTP information for an email.
        
        Args:
            email: User email address
            
        Returns:
            Dictionary with OTP information
        """
        try:
            await self.initialize()
            
            attempts = await self.get_otp_attempts(email)
            is_expired = await self.is_otp_expired(email)
            
            return {
                "email": email,
                "attempts_made": attempts,
                "max_attempts": self.max_attempts,
                "remaining_attempts": self.max_attempts - attempts,
                "is_expired": is_expired,
                "expiry_minutes": self.otp_expiry_minutes
            }
            
        except Exception as e:
            logger.error(f"Failed to get OTP info for {email}: {e}")
            return {
                "email": email,
                "attempts_made": 0,
                "max_attempts": self.max_attempts,
                "remaining_attempts": self.max_attempts,
                "is_expired": True,
                "expiry_minutes": self.otp_expiry_minutes
            }


# Global OTP service instance
otp_service = OTPService()