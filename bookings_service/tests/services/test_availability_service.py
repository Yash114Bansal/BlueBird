"""
Tests for AvailabilityService.
Tests availability management and capacity operations.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.availability_service import AvailabilityService
from app.models.booking import EventAvailability


class TestAvailabilityService:
    """Test AvailabilityService functionality."""
    
    @pytest.fixture
    def availability_service(self, initialized_db_manager):
        """Create availability service instance for testing."""
        return AvailabilityService()
    
    def test_availability_service_initialization(self, availability_service):
        """Test that AvailabilityService initializes correctly."""
        assert availability_service is not None
    
    def test_availability_service_has_required_methods(self, availability_service):
        """Test that AvailabilityService has required methods."""
        required_methods = [
            'get_event_availability',
            'check_availability',
            'reserve_capacity',
            'confirm_capacity',
            'release_capacity',
            'create_event_availability',
            'update_event_capacity'
        ]
        
        for method_name in required_methods:
            assert hasattr(availability_service, method_name), f"Missing method: {method_name}"
            assert callable(getattr(availability_service, method_name)), f"Method not callable: {method_name}"
    
    @pytest.mark.asyncio
    async def test_get_configs(self, availability_service):
        """Test configuration loading."""
        with patch('app.core.config.config.get_consistency_config', return_value={"lock_timeout_seconds": 30}):
            with patch('app.core.config.config.get_cache_config', return_value={"cache_ttl_seconds": 300}):
                await availability_service._get_configs()
                
                assert availability_service.consistency_config is not None
                assert availability_service.cache_config is not None