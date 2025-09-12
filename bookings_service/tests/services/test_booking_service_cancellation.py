"""
Tests for BookingService cancellation operations.
Tests booking cancellation and status transitions.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.services.booking_service import BookingService
from app.models.booking import Booking, BookingStatus, PaymentStatus
from app.schemas.booking import BookingCancel


class TestBookingServiceCancellation:
    """Test BookingService booking cancellation functionality."""
    
    @pytest.fixture
    def booking_service(self, initialized_db_manager):
        """Create booking service instance for testing."""
        return BookingService()
    
    @pytest.fixture
    def sample_cancel_data(self):
        """Sample cancellation data for testing."""
        return BookingCancel(reason="User requested cancellation")
    
    def test_booking_service_has_cancel_method(self, booking_service):
        """Test that BookingService has cancel_booking method."""
        assert hasattr(booking_service, 'cancel_booking')
        assert callable(getattr(booking_service, 'cancel_booking'))
    
    def test_booking_service_has_release_methods(self, booking_service):
        """Test that BookingService has capacity release methods."""
        assert hasattr(booking_service, '_release_reserved_capacity')
        assert hasattr(booking_service, '_release_confirmed_capacity')
        assert callable(getattr(booking_service, '_release_reserved_capacity'))
        assert callable(getattr(booking_service, '_release_confirmed_capacity'))
    
    @pytest.mark.asyncio
    async def test_cancel_booking_method_signature(self, booking_service):
        """Test that cancel_booking method accepts correct parameters."""
        import inspect
        
        # Get the method signature
        sig = inspect.signature(booking_service.cancel_booking)
        params = list(sig.parameters.keys())
        
        # Should have booking_id, cancel_data, and user_id parameters
        assert 'booking_id' in params
        assert 'cancel_data' in params
        assert 'user_id' in params