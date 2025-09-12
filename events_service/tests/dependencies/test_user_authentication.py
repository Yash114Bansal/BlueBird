"""
Tests for user authentication dependencies.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import get_current_user


class TestUserAuthentication:
    """Test cases for user authentication dependencies."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test get_current_user with valid token."""
        mock_jwt_service = MagicMock()
        mock_jwt_service.verify_token.return_value = {
            "user_id": 1,
            "email": "test@example.com",
            "role": "user"
        }
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid-token"
        )
        
        result = await get_current_user(mock_credentials, mock_jwt_service)
        
        assert result["user_id"] == 1
        assert result["email"] == "test@example.com"
        assert result["role"] == "user"
        mock_jwt_service.verify_token.assert_called_once_with("valid-token")
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token."""
        mock_jwt_service = MagicMock()
        mock_jwt_service.verify_token.return_value = None
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid-token"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_jwt_service)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_current_user_jwt_exception(self):
        """Test get_current_user with JWT service exception."""
        mock_jwt_service = MagicMock()
        mock_jwt_service.verify_token.side_effect = Exception("JWT error")
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="token"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_jwt_service)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)