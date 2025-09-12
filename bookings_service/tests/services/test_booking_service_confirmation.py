"""
Tests for BookingService confirmation operations.
Tests booking confirmation and status transitions.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.services.booking_service import BookingService
from app.models.booking import Booking, BookingStatus, PaymentStatus


class TestBookingServiceConfirmation:
    """Test BookingService booking confirmation functionality."""
    
    @pytest.fixture
    def booking_service(self, initialized_db_manager):
        """Create booking service instance for testing."""
        return BookingService()
    
    def test_booking_service_has_confirm_method(self, booking_service):
        """Test that BookingService has confirm_booking method."""
        assert hasattr(booking_service, 'confirm_booking')
        assert callable(getattr(booking_service, 'confirm_booking'))
    
    def test_booking_service_has_get_booking_method(self, booking_service):
        """Test that BookingService has get_booking_by_id method."""
        assert hasattr(booking_service, 'get_booking_by_id')
        assert callable(getattr(booking_service, 'get_booking_by_id'))
    
    def test_booking_service_has_confirm_availability_method(self, booking_service):
        """Test that BookingService has _confirm_availability_reservation method."""
        assert hasattr(booking_service, '_confirm_availability_reservation')
        assert callable(getattr(booking_service, '_confirm_availability_reservation'))
    
    @pytest.mark.asyncio
    async def test_confirm_booking_method_signature(self, booking_service):
        """Test that confirm_booking method accepts correct parameters."""
        import inspect
        
        # Get the method signature
        sig = inspect.signature(booking_service.confirm_booking)
        params = list(sig.parameters.keys())
        
        # Should have booking_id and user_id parameters
        assert 'booking_id' in params
        assert 'user_id' in params