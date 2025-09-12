"""
Tests for optional authentication dependencies.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import Request

from app.api.dependencies import get_optional_current_user


class TestOptionalAuthentication:
    """Test cases for optional authentication dependencies."""
    
    @pytest.mark.asyncio
    async def test_get_optional_current_user_with_valid_token(self):
        """Test get_optional_current_user with valid token."""
        mock_jwt_service = MagicMock()
        mock_jwt_service.verify_token.return_value = {
            "user_id": 1,
            "email": "test@example.com",
            "role": "user"
        }
        
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer valid-token"}
        
        result = await get_optional_current_user(mock_request, mock_jwt_service)
        
        assert result is not None
        assert result["user_id"] == 1
        assert result["email"] == "test@example.com"
        assert result["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_get_optional_current_user_no_authorization_header(self):
        """Test get_optional_current_user with no authorization header."""
        mock_jwt_service = MagicMock()
        
        mock_request = MagicMock()
        mock_request.headers = {}
        
        result = await get_optional_current_user(mock_request, mock_jwt_service)
        
        assert result is None
        mock_jwt_service.verify_token.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_optional_current_user_invalid_authorization_format(self):
        """Test get_optional_current_user with invalid authorization format."""
        mock_jwt_service = MagicMock()
        
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Invalid token"}
        
        result = await get_optional_current_user(mock_request, mock_jwt_service)
        
        assert result is None
        mock_jwt_service.verify_token.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_optional_current_user_invalid_token(self):
        """Test get_optional_current_user with invalid token."""
        mock_jwt_service = MagicMock()
        mock_jwt_service.verify_token.return_value = None
        
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer invalid-token"}
        
        result = await get_optional_current_user(mock_request, mock_jwt_service)
        
        assert result is None
        mock_jwt_service.verify_token.assert_called_once_with("invalid-token")
    
    @pytest.mark.asyncio
    async def test_get_optional_current_user_jwt_exception(self):
        """Test get_optional_current_user with JWT service exception."""
        mock_jwt_service = MagicMock()
        mock_jwt_service.verify_token.side_effect = Exception("JWT error")
        
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}
        
        result = await get_optional_current_user(mock_request, mock_jwt_service)
        
        assert result is None
        mock_jwt_service.verify_token.assert_called_once_with("token")