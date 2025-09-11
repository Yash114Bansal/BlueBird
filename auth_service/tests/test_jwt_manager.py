"""
Tests for JWTManager service.
"""

import pytest
from datetime import datetime, timedelta
from jose import JWTError
from app.services.jwt_manager import JWTManager


class TestJWTManager:
    """Test cases for the JWTManager service."""

    @pytest.mark.asyncio
    async def test_jwt_manager_initialization(self, jwt_manager):
        """Test JWTManager initialization."""
        assert jwt_manager.secret_key is not None
        assert jwt_manager.algorithm is not None
        assert jwt_manager.access_token_expire_minutes is not None
        assert jwt_manager.refresh_token_expire_days is not None

    def test_create_access_token(self, jwt_manager):
        """Test creating an access token."""
        token_data = {
            "user_id": 123,
            "email": "test@example.com",
            "role": "user"
        }
        
        token = jwt_manager.create_access_token(token_data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self, jwt_manager):
        """Test creating a refresh token."""
        token_data = {
            "user_id": 123,
            "email": "test@example.com",
            "role": "user"
        }
        
        token = jwt_manager.create_refresh_token(token_data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_valid_access_token(self, jwt_manager):
        """Test verifying a valid access token."""
        token_data = {
            "user_id": 123,
            "email": "test@example.com",
            "role": "user"
        }
        
        token = jwt_manager.create_access_token(token_data)
        verified_data = jwt_manager.verify_token(token, "access")
        
        assert verified_data is not None
        assert verified_data.user_id == 123
        assert verified_data.email == "test@example.com"
        assert verified_data.role == "user"

    def test_verify_token_valid_refresh_token(self, jwt_manager):
        """Test verifying a valid refresh token."""
        token_data = {
            "user_id": 123,
            "email": "test@example.com",
            "role": "user"
        }
        
        token = jwt_manager.create_refresh_token(token_data)
        verified_data = jwt_manager.verify_token(token, "refresh")
        
        assert verified_data is not None
        assert verified_data.user_id == 123
        assert verified_data.email == "test@example.com"
        assert verified_data.role == "user"

    def test_verify_token_invalid_token(self, jwt_manager):
        """Test verifying an invalid token."""
        invalid_token = "invalid.token.here"
        verified_data = jwt_manager.verify_token(invalid_token, "access")
        
        assert verified_data is None

    def test_verify_token_wrong_secret(self):
        """Test verifying a token with wrong secret key."""
        jwt_manager1 = JWTManager()
        jwt_manager2 = JWTManager()
        
        # Initialize with different secrets
        jwt_manager1.secret_key = "secret-key-1"
        jwt_manager1.algorithm = "HS256"
        jwt_manager1.access_token_expire_minutes = 30
        jwt_manager1.refresh_token_expire_days = 7
        
        jwt_manager2.secret_key = "secret-key-2"
        jwt_manager2.algorithm = "HS256"
        jwt_manager2.access_token_expire_minutes = 30
        jwt_manager2.refresh_token_expire_days = 7
        
        token_data = {
            "user_id": 123,
            "email": "test@example.com",
            "role": "user"
        }
        
        token = jwt_manager1.create_access_token(token_data)
        verified_data = jwt_manager2.verify_token(token, "access")
        
        assert verified_data is None

    def test_verify_token_expired_token(self):
        """Test verifying an expired token."""
        jwt_manager = JWTManager()
        jwt_manager.secret_key = "test-secret-key"
        jwt_manager.algorithm = "HS256"
        jwt_manager.access_token_expire_minutes = -1  # Expired immediately
        jwt_manager.refresh_token_expire_days = 7
        
        token_data = {
            "user_id": 123,
            "email": "test@example.com",
            "role": "user"
        }
        
        token = jwt_manager.create_access_token(token_data)
        verified_data = jwt_manager.verify_token(token, "access")
        
        assert verified_data is None

    def test_verify_token_wrong_token_type(self, jwt_manager):
        """Test verifying a token with wrong type."""
        token_data = {
            "user_id": 123,
            "email": "test@example.com",
            "role": "user"
        }
        
        access_token = jwt_manager.create_access_token(token_data)
        verified_data = jwt_manager.verify_token(access_token, "refresh")
        
        assert verified_data is None

    def test_verify_token_empty_token(self, jwt_manager):
        """Test verifying an empty token."""
        verified_data = jwt_manager.verify_token("", "access")
        
        assert verified_data is None

    def test_verify_token_none_token(self, jwt_manager):
        """Test verifying a None token."""
        with pytest.raises(AttributeError):
            jwt_manager.verify_token(None, "access")

    def test_token_expiration_times(self, jwt_manager):
        """Test that tokens have correct expiration times."""
        token_data = {
            "user_id": 123,
            "email": "test@example.com",
            "role": "user"
        }
        
        access_token = jwt_manager.create_access_token(token_data)
        refresh_token = jwt_manager.create_refresh_token(token_data)
        
        # Both tokens should be valid
        access_data = jwt_manager.verify_token(access_token, "access")
        refresh_data = jwt_manager.verify_token(refresh_token, "refresh")
        
        assert access_data is not None
        assert refresh_data is not None

    def test_token_with_different_roles(self, jwt_manager):
        """Test tokens with different user roles."""
        # Test user role
        user_token_data = {
            "user_id": 123,
            "email": "user@example.com",
            "role": "user"
        }
        
        # Test admin role
        admin_token_data = {
            "user_id": 456,
            "email": "admin@example.com",
            "role": "admin"
        }
        
        user_token = jwt_manager.create_access_token(user_token_data)
        admin_token = jwt_manager.create_access_token(admin_token_data)
        
        user_data = jwt_manager.verify_token(user_token, "access")
        admin_data = jwt_manager.verify_token(admin_token, "access")
        
        assert user_data.role == "user"
        assert admin_data.role == "admin"
        assert user_data.user_id == 123
        assert admin_data.user_id == 456

    def test_token_with_special_characters(self, jwt_manager):
        """Test tokens with special characters in data."""
        token_data = {
            "user_id": 123,
            "email": "test+special@example.com",
            "role": "user"
        }
        
        token = jwt_manager.create_access_token(token_data)
        verified_data = jwt_manager.verify_token(token, "access")
        
        assert verified_data is not None
        assert verified_data.email == "test+special@example.com"

    def test_token_consistency(self, jwt_manager):
        """Test that the same data produces consistent tokens."""
        token_data = {
            "user_id": 123,
            "email": "test@example.com",
            "role": "user"
        }
        
        token1 = jwt_manager.create_access_token(token_data)
        token2 = jwt_manager.create_access_token(token_data)
                
        data1 = jwt_manager.verify_token(token1, "access")
        data2 = jwt_manager.verify_token(token2, "access")
        
        assert data1.user_id == data2.user_id
        assert data1.email == data2.email
        assert data1.role == data2.role