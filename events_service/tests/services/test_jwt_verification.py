"""
Tests for JWT token verification.
"""

import pytest
import time
from unittest.mock import AsyncMock, patch
from jose import jwt

from app.services.jwt_service import JWTService


class TestJWTVerification:
    """Test cases for JWT token verification."""
    
    def test_verify_token_not_initialized(self):
        """Test token verification when service is not initialized."""
        jwt_service = JWTService()
        
        result = jwt_service.verify_token("invalid-token")
        
        assert result is None
    
    def test_verify_token_valid(self):
        """Test verification of a valid token."""
        jwt_service = JWTService()
        jwt_service.secret_key = "test-secret-key"
        jwt_service.algorithm = "HS256"
        jwt_service._initialized = True
        
        # Create a valid token
        payload = {
            "user_id": 1,
            "email": "test@example.com",
            "role": "user",
            "exp": int(time.time()) + 3600
        }
        
        token = jwt.encode(payload, jwt_service.secret_key, algorithm=jwt_service.algorithm)
        
        result = jwt_service.verify_token(token)
        
        assert result is not None
        assert result["user_id"] == 1
        assert result["email"] == "test@example.com"
        assert result["role"] == "user"
    
    def test_verify_token_invalid_signature(self):
        """Test verification of token with invalid signature."""
        jwt_service = JWTService()
        jwt_service.secret_key = "test-secret-key"
        jwt_service.algorithm = "HS256"
        jwt_service._initialized = True
        
        # Create token with different secret
        payload = {"user_id": 1, "email": "test@example.com"}
        invalid_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        
        result = jwt_service.verify_token(invalid_token)
        
        assert result is None
    
    def test_verify_token_missing_fields(self):
        """Test verification of token with missing required fields."""
        jwt_service = JWTService()
        jwt_service.secret_key = "test-secret-key"
        jwt_service.algorithm = "HS256"
        jwt_service._initialized = True
        
        # Create token with missing fields
        payload = {"user_id": 1}  # Missing email and role
        token = jwt.encode(payload, jwt_service.secret_key, algorithm=jwt_service.algorithm)
        
        result = jwt_service.verify_token(token)
        
        assert result is None
    
    def test_verify_token_expired(self):
        """Test verification of expired token."""
        jwt_service = JWTService()
        jwt_service.secret_key = "test-secret-key"
        jwt_service.algorithm = "HS256"
        jwt_service._initialized = True
        
        # Create expired token
        payload = {
            "user_id": 1,
            "email": "test@example.com",
            "role": "user",
            "exp": int(time.time()) - 3600  # Expired 1 hour ago
        }
        
        token = jwt.encode(payload, jwt_service.secret_key, algorithm=jwt_service.algorithm)
        
        result = jwt_service.verify_token(token)
        
        assert result is None
    
    def test_verify_token_invalid_format(self):
        """Test verification of malformed token."""
        jwt_service = JWTService()
        jwt_service.secret_key = "test-secret-key"
        jwt_service.algorithm = "HS256"
        jwt_service._initialized = True
        
        result = jwt_service.verify_token("invalid.token.format")
        
        assert result is None
    
    def test_verify_token_wrong_algorithm(self):
        """Test verification of token with wrong algorithm."""
        jwt_service = JWTService()
        jwt_service.secret_key = "test-secret-key"
        jwt_service.algorithm = "HS256"
        jwt_service._initialized = True
        
        # Create token with different algorithm
        payload = {"user_id": 1, "email": "test@example.com", "role": "user"}
        token = jwt.encode(payload, jwt_service.secret_key, algorithm="HS512")
        
        result = jwt_service.verify_token(token)
        
        assert result is None
    
    def test_verify_token_with_admin_role(self):
        """Test verification of token with admin role."""
        jwt_service = JWTService()
        jwt_service.secret_key = "test-secret-key"
        jwt_service.algorithm = "HS256"
        jwt_service._initialized = True
        
        # Create admin token
        payload = {
            "user_id": 1,
            "email": "admin@example.com",
            "role": "admin",
            "exp": int(time.time()) + 3600
        }
        
        token = jwt.encode(payload, jwt_service.secret_key, algorithm=jwt_service.algorithm)
        
        result = jwt_service.verify_token(token)
        
        assert result is not None
        assert result["role"] == "admin"
    
    def test_verify_token_with_extra_fields(self):
        """Test verification of token with extra fields."""
        jwt_service = JWTService()
        jwt_service.secret_key = "test-secret-key"
        jwt_service.algorithm = "HS256"
        jwt_service._initialized = True
        
        # Create token with extra fields
        payload = {
            "user_id": 1,
            "email": "test@example.com",
            "role": "user",
            "extra_field": "extra_value",
            "exp": int(time.time()) + 3600
        }
        
        token = jwt.encode(payload, jwt_service.secret_key, algorithm=jwt_service.algorithm)
        
        result = jwt_service.verify_token(token)
        
        assert result is not None
        assert result["user_id"] == 1
        assert result["email"] == "test@example.com"
        assert result["role"] == "user"
        assert result["extra_field"] == "extra_value"
    
    @pytest.mark.asyncio
    async def test_jwt_service_with_config_error(self):
        """Test JWT service initialization with config error."""
        jwt_service = JWTService()
        
        with patch('app.services.jwt_service.config') as mock_config:
            mock_config.get_jwt_secret = AsyncMock(side_effect=Exception("Config error"))
            
            with pytest.raises(Exception) as exc_info:
                await jwt_service.initialize()
            
            assert "Config error" in str(exc_info.value)