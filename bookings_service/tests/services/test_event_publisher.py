"""
Tests for Event Publisher Service.
Tests booking event publishing functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime, timezone
from decimal import Decimal

from app.services.event_publisher import BookingEventPublisher
from app.models.booking import Booking, BookingStatus, PaymentStatus


class TestBookingEventPublisher:
    """Test BookingEventPublisher functionality."""
    
    @pytest.fixture
    def mock_redis_manager(self):
        """Mock Redis manager for testing."""
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock()
        return mock_redis
    
    @pytest.fixture
    def publisher(self, mock_redis_manager):
        """Create publisher instance for testing."""
        return BookingEventPublisher(mock_redis_manager)
    
    @pytest.fixture
    def mock_booking(self):
        """Mock booking object for testing."""
        booking = MagicMock()
        booking.id = 1
        booking.event_id = 100
        booking.user_id = 50
        booking.booking_reference = "BK-12345"
        booking.quantity = 2
        booking.total_amount = Decimal("50.00")
        booking.currency = "USD"
        booking.status = BookingStatus.PENDING
        booking.payment_status = PaymentStatus.PENDING
        booking.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        booking.expires_at = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        booking.updated_at = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        return booking
    
    def test_publisher_initialization(self, publisher):
        """Test that BookingEventPublisher initializes correctly."""
        assert publisher is not None
        assert publisher.channel_prefix == "evently:bookings"
        assert publisher.redis_manager is not None
    
    def test_publisher_has_required_methods(self, publisher):
        """Test that BookingEventPublisher has required methods."""
        required_methods = [
            'publish_booking_created',
            'publish_booking_confirmed',
            'publish_booking_cancelled',
            'publish_booking_expired',
            'publish_booking_payment_completed'
        ]
        
        for method_name in required_methods:
            assert hasattr(publisher, method_name), f"Missing method: {method_name}"
            assert callable(getattr(publisher, method_name)), f"Method not callable: {method_name}"
    
    @pytest.mark.asyncio
    async def test_publish_booking_created_success(self, publisher, mock_booking, mock_redis_manager):
        """Test successful booking created event publishing."""
        # Call the method
        await publisher.publish_booking_created(mock_booking)
        
        # Verify Redis publish was called
        mock_redis_manager.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_redis_manager.publish.call_args
        channel = call_args[0][0]
        message_str = call_args[0][1]
        
        # Verify channel
        assert channel == "evently:bookings:created"
        
        # Verify message content
        message = json.loads(message_str)
        assert message["type"] == "BookingCreated"
        assert message["booking_id"] == 1
        assert message["event_id"] == 100
        assert message["user_id"] == 50
        
        # Verify booking data
        booking_data = message["booking_data"]
        assert booking_data["id"] == 1
        assert booking_data["event_id"] == 100
        assert booking_data["user_id"] == 50
        assert booking_data["booking_reference"] == "BK-12345"
        assert booking_data["quantity"] == 2
        assert booking_data["total_amount"] == 50.0
        assert booking_data["currency"] == "USD"
        assert booking_data["status"] == "pending"
        assert booking_data["payment_status"] == "pending"
        assert booking_data["created_at"] == "2024-01-01T12:00:00+00:00"
        assert booking_data["expires_at"] == "2024-01-01T13:00:00+00:00"
    
    @pytest.mark.asyncio
    async def test_publish_booking_confirmed_success(self, publisher, mock_booking, mock_redis_manager):
        """Test successful booking confirmed event publishing."""
        # Call the method
        await publisher.publish_booking_confirmed(mock_booking)
        
        # Verify Redis publish was called
        mock_redis_manager.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_redis_manager.publish.call_args
        channel = call_args[0][0]
        message_str = call_args[0][1]
        
        # Verify channel
        assert channel == "evently:bookings:confirmed"
        
        # Verify message content
        message = json.loads(message_str)
        assert message["type"] == "BookingConfirmed"
        assert message["booking_id"] == 1
        assert message["event_id"] == 100
        assert message["user_id"] == 50
        
        # Verify booking data
        booking_data = message["booking_data"]
        assert booking_data["id"] == 1
        assert booking_data["confirmed_at"] == "2024-01-01T12:30:00+00:00"
    
    @pytest.mark.asyncio
    async def test_publish_booking_cancelled_success(self, publisher, mock_booking, mock_redis_manager):
        """Test successful booking cancelled event publishing."""
        # Add cancellation reason to mock booking
        mock_booking.cancellation_reason = "User requested cancellation"
        
        # Call the method
        await publisher.publish_booking_cancelled(mock_booking)
        
        # Verify Redis publish was called
        mock_redis_manager.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_redis_manager.publish.call_args
        channel = call_args[0][0]
        message_str = call_args[0][1]
        
        # Verify channel
        assert channel == "evently:bookings:cancelled"
        
        # Verify message content
        message = json.loads(message_str)
        assert message["type"] == "BookingCancelled"
        assert message["booking_id"] == 1
        
        # Verify booking data
        booking_data = message["booking_data"]
        assert booking_data["cancelled_at"] == "2024-01-01T12:30:00+00:00"
        assert booking_data["cancellation_reason"] == "User requested cancellation"
    
    @pytest.mark.asyncio
    async def test_publish_booking_expired_success(self, publisher, mock_booking, mock_redis_manager):
        """Test successful booking expired event publishing."""
        # Call the method
        await publisher.publish_booking_expired(mock_booking)
        
        # Verify Redis publish was called
        mock_redis_manager.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_redis_manager.publish.call_args
        channel = call_args[0][0]
        message_str = call_args[0][1]
        
        # Verify channel
        assert channel == "evently:bookings:expired"
        
        # Verify message content
        message = json.loads(message_str)
        assert message["type"] == "BookingExpired"
        assert message["booking_id"] == 1
        
        # Verify booking data
        booking_data = message["booking_data"]
        assert booking_data["expired_at"] == "2024-01-01T12:30:00+00:00"
    
    @pytest.mark.asyncio
    async def test_publish_booking_payment_completed_success(self, publisher, mock_booking, mock_redis_manager):
        """Test successful booking payment completed event publishing."""
        # Call the method
        await publisher.publish_booking_payment_completed(mock_booking)
        
        # Verify Redis publish was called
        mock_redis_manager.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_redis_manager.publish.call_args
        channel = call_args[0][0]
        message_str = call_args[0][1]
        
        # Verify channel
        assert channel == "evently:bookings:payment_completed"
        
        # Verify message content
        message = json.loads(message_str)
        assert message["type"] == "BookingPaymentCompleted"
        assert message["booking_id"] == 1
        
        # Verify booking data
        booking_data = message["booking_data"]
        assert booking_data["payment_completed_at"] == "2024-01-01T12:30:00+00:00"
    
    @pytest.mark.asyncio
    async def test_publish_booking_created_with_none_values(self, publisher, mock_redis_manager):
        """Test publishing booking created with None values."""
        # Create booking with None values
        booking = MagicMock()
        booking.id = 1
        booking.event_id = 100
        booking.user_id = 50
        booking.booking_reference = "BK-12345"
        booking.quantity = 2
        booking.total_amount = None
        booking.currency = "USD"
        booking.status = None
        booking.payment_status = None
        booking.created_at = None
        booking.expires_at = None
        booking.updated_at = None
        
        # Call the method
        await publisher.publish_booking_created(booking)
        
        # Verify Redis publish was called
        mock_redis_manager.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_redis_manager.publish.call_args
        message_str = call_args[0][1]
        
        # Verify message content handles None values
        message = json.loads(message_str)
        booking_data = message["booking_data"]
        assert booking_data["total_amount"] == 0.0
        assert booking_data["status"] is None
        assert booking_data["payment_status"] is None
        assert booking_data["created_at"] is None
        assert booking_data["expires_at"] is None
    
    @pytest.mark.asyncio
    async def test_publish_booking_created_redis_error(self, publisher, mock_booking, mock_redis_manager):
        """Test handling of Redis publish errors."""
        # Make Redis publish raise an exception
        mock_redis_manager.publish.side_effect = Exception("Redis connection failed")
        
        # Call the method - should not raise exception
        await publisher.publish_booking_created(mock_booking)
        
        # Verify Redis publish was called
        mock_redis_manager.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_booking_cancelled_without_reason(self, publisher, mock_booking, mock_redis_manager):
        """Test publishing booking cancelled without cancellation reason."""
        # Remove cancellation_reason attribute
        if hasattr(mock_booking, 'cancellation_reason'):
            delattr(mock_booking, 'cancellation_reason')
        
        # Call the method
        await publisher.publish_booking_cancelled(mock_booking)
        
        # Verify Redis publish was called
        mock_redis_manager.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_redis_manager.publish.call_args
        message_str = call_args[0][1]
        
        # Verify message content
        message = json.loads(message_str)
        booking_data = message["booking_data"]
        assert booking_data["cancellation_reason"] is None
    
    @pytest.mark.asyncio
    async def test_publish_methods_json_serialization(self, publisher, mock_redis_manager):
        """Test that all publish methods produce valid JSON."""
        # Create a properly configured mock booking for each method
        def create_mock_booking():
            booking = MagicMock()
            booking.id = 1
            booking.event_id = 100
            booking.user_id = 50
            booking.booking_reference = "BK-12345"
            booking.quantity = 2
            booking.total_amount = Decimal("50.00")
            booking.currency = "USD"
            booking.status = BookingStatus.PENDING
            booking.payment_status = PaymentStatus.PENDING
            booking.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            booking.expires_at = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
            booking.updated_at = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
            return booking
        
        methods = [
            publisher.publish_booking_created,
            publisher.publish_booking_confirmed,
            publisher.publish_booking_cancelled,
            publisher.publish_booking_expired,
            publisher.publish_booking_payment_completed
        ]
        
        for method in methods:
            # Reset mock for each method
            mock_redis_manager.reset_mock()
            
            # Create a fresh mock booking for each method
            mock_booking = create_mock_booking()
            
            # For cancelled method, add a proper cancellation reason
            if method == publisher.publish_booking_cancelled:
                mock_booking.cancellation_reason = "User requested cancellation"
            
            # Call the method
            await method(mock_booking)
            
            # Verify Redis publish was called
            mock_redis_manager.publish.assert_called_once()
            
            # Get the message and verify it's valid JSON
            call_args = mock_redis_manager.publish.call_args
            message_str = call_args[0][1]
            
            # Should not raise exception
            message = json.loads(message_str)
            assert isinstance(message, dict)
            assert "type" in message
            assert "booking_id" in message
            assert "booking_data" in message