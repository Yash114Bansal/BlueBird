"""
Tests for JWT service initialization.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.jwt_service import JWTService


class TestJWTInitialization:
    """Test cases for JWT service initialization."""
    
    def test_jwt_service_initialization(self):
        """Test JWT service initialization."""
        jwt_service = JWTService()
        
        assert jwt_service.secret_key is None
        assert jwt_service.algorithm is None
        assert jwt_service._initialized is False
    
    @pytest.mark.asyncio
    async def test_jwt_service_initialize(self):
        """Test JWT service initialization with config."""
        jwt_service = JWTService()
        
        # Mock the config methods as async
        with patch('app.services.jwt_service.config') as mock_config:
            mock_config.get_jwt_secret = AsyncMock(return_value="test-secret-key")
            mock_config.get_jwt_algorithm = AsyncMock(return_value="HS256")
            
            await jwt_service.initialize()
            
            assert jwt_service.secret_key == "test-secret-key"
            assert jwt_service.algorithm == "HS256"
            assert jwt_service._initialized is True