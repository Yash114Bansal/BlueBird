"""
Tests for admin authentication dependencies.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import get_current_admin_user


class TestAdminAuthentication:
    """Test cases for admin authentication dependencies."""
    
    @pytest.mark.asyncio
    async def test_get_current_admin_user_valid_admin(self):
        """Test get_current_admin_user with valid admin token."""
        admin_user = {
            "user_id": 1,
            "email": "admin@example.com",
            "role": "admin"
        }
        
        result = await get_current_admin_user(current_user=admin_user)
        
        assert result["user_id"] == 1
        assert result["email"] == "admin@example.com"
        assert result["role"] == "admin"
    
    @pytest.mark.asyncio
    async def test_get_current_admin_user_non_admin(self):
        """Test get_current_admin_user with non-admin token."""
        regular_user = {
            "user_id": 1,
            "email": "user@example.com",
            "role": "user"  # Not admin
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(current_user=regular_user)
        
        assert exc_info.value.status_code == 403
        assert "Not enough permissions" in str(exc_info.value.detail)