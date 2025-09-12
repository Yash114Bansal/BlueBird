"""
Tests for JWT Service.
Tests JWT token generation, validation, and management.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta

from app.services.jwt_service import JWTService


class TestJWTService:
    """Test JWT Service functionality."""
    
    @pytest.fixture
    def jwt_service(self):
        """Create JWT service instance for testing."""
        return JWTService()
    
    def test_jwt_service_initialization(self, jwt_service):
        """Test that JWTService initializes correctly."""
        assert jwt_service is not None
    
    def test_jwt_service_has_required_methods(self, jwt_service):
        """Test that JWTService has required methods."""
        required_methods = [
            'decode_token',
            'get_user_id',
            'get_user_role',
            'is_admin',
            'validate_token',
            'get_token_info'
        ]
        
        for method_name in required_methods:
            assert hasattr(jwt_service, method_name), f"Missing method: {method_name}"
            assert callable(getattr(jwt_service, method_name)), f"Method not callable: {method_name}"
    
    @pytest.mark.asyncio
    async def test_get_config(self, jwt_service):
        """Test configuration loading."""
        with patch('app.core.config.config.get_jwt_secret', return_value="test-secret"):
            with patch('app.core.config.config.get_jwt_algorithm', return_value="HS256"):
                with patch('app.core.config.config.get_jwt_expiry_minutes', return_value=60):
                    await jwt_service._get_config()
                    
                    assert jwt_service.jwt_secret is not None
                    assert jwt_service.jwt_algorithm is not None
                    assert jwt_service.jwt_expiry_minutes is not None
                    assert jwt_service.jwt_secret == "test-secret"
                    assert jwt_service.jwt_algorithm == "HS256"
                    assert jwt_service.jwt_expiry_minutes == 60
    
    @pytest.mark.asyncio
    async def test_decode_token_method_signature(self, jwt_service):
        """Test that decode_token method accepts correct parameters."""
        import inspect
        
        # Get the method signature
        sig = inspect.signature(jwt_service.decode_token)
        params = list(sig.parameters.keys())
        
        # Should have token parameter
        assert 'token' in params