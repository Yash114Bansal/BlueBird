"""
Tests for BookingService creation operations.
Tests booking creation, validation, and basic functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.services.booking_service import BookingService
from app.schemas.booking import BookingCreate


class TestBookingServiceCreation:
    """Test BookingService booking creation functionality."""
    
    @pytest.fixture
    def booking_service(self, initialized_db_manager):
        """Create booking service instance for testing."""
        return BookingService()
    
    @pytest.fixture
    def sample_booking_data(self):
        """Sample booking data for testing."""
        return {
            "event_id": 1,
            "quantity": 2,
            "ticket_type": "General",
            "notes": "Test booking"
        }
    
    def test_booking_service_initialization(self, booking_service):
        """Test that BookingService initializes correctly."""
        assert booking_service is not None
        assert booking_service.consistency_config is None
        assert booking_service.booking_config is None
    
    def test_generate_booking_reference(self, booking_service):
        """Test booking reference generation."""
        import asyncio
        reference = asyncio.run(booking_service._generate_booking_reference())
        
        assert reference is not None
        assert reference.startswith("BK-")
        assert len(reference) > 10  # Should have date and UUID
    
    @pytest.mark.asyncio
    async def test_get_configs(self, booking_service):
        """Test configuration loading."""
        with patch('app.core.config.config.get_consistency_config', return_value={"lock_timeout_seconds": 30}):
            with patch('app.core.config.config.get_booking_config', return_value={"booking_hold_duration_minutes": 15}):
                await booking_service._get_configs()
                
                assert booking_service.consistency_config is not None
                assert booking_service.booking_config is not None
                assert booking_service.consistency_config["lock_timeout_seconds"] == 30
                assert booking_service.booking_config["booking_hold_duration_minutes"] == 15