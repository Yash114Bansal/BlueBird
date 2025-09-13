"""
Tests for Notification Service.
Tests notification operations and service management.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from app.services.notification_service import NotificationService


class TestNotificationService:
    """Test cases for NotificationService."""
    
    @pytest.fixture
    def notification_service(self):
        """Create NotificationService instance for testing."""
        return NotificationService()
    
    @pytest.fixture
    def booking_data(self):
        """Create booking data for testing."""
        return {
            "id": 1,
            "user_id": 1,
            "event_id": 1,
            "booking_reference": "BK-20240101-ABC123",
            "quantity": 2,
            "total_amount": 100.0,
            "status": "confirmed"
        }
    
    @pytest.fixture
    def waitlist_data(self):
        """Create waitlist data for testing."""
        return {
            "id": 1,
            "user_id": 1,
            "event_id": 1,
            "quantity": 2,
            "priority": 1,
            "status": "pending"
        }
    
    @pytest.fixture
    def event_data(self):
        """Create event data for testing."""
        return {
            "id": 1,
            "name": "Test Event",
            "date": "2024-01-01T10:00:00Z",
            "capacity": 100
        }
    
    @pytest.mark.asyncio
    async def test_send_booking_confirmation_success(self, notification_service, booking_data, event_data):
        """Test successful booking confirmation notification."""
        # Test with enabled service
        notification_service.enable()
        
        with patch('app.services.notification_service.logger') as mock_logger:
            result = await notification_service.send_booking_confirmation(
                user_id=1,
                booking_data=booking_data,
                event_data=event_data
            )
            
            # Verify result
            assert result is True
            
            # Verify logging
            mock_logger.info.assert_called()
            mock_logger.debug.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_booking_confirmation_disabled(self, notification_service, booking_data):
        """Test booking confirmation notification when service is disabled."""
        # Test with disabled service
        notification_service.disable()
        
        with patch('app.services.notification_service.logger') as mock_logger:
            result = await notification_service.send_booking_confirmation(
                user_id=1,
                booking_data=booking_data
            )
            
            # Verify result
            assert result is True
            
            # Verify logging
            mock_logger.info.assert_called_with("Notification service disabled, skipping booking confirmation")
    
    @pytest.mark.asyncio
    async def test_send_booking_cancellation_success(self, notification_service, booking_data, event_data):
        """Test successful booking cancellation notification."""
        # Test with enabled service
        notification_service.enable()
        
        with patch('app.services.notification_service.logger') as mock_logger:
            result = await notification_service.send_booking_cancellation(
                user_id=1,
                booking_data=booking_data,
                event_data=event_data
            )
            
            # Verify result
            assert result is True
            
            # Verify logging
            mock_logger.info.assert_called()
            mock_logger.debug.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_waitlist_notification_success(self, notification_service, waitlist_data, event_data):
        """Test successful waitlist notification."""
        # Test with enabled service
        notification_service.enable()
        
        expires_at = datetime.now(timezone.utc)
        
        with patch('app.services.notification_service.logger') as mock_logger:
            result = await notification_service.send_waitlist_notification(
                user_id=1,
                waitlist_data=waitlist_data,
                event_data=event_data,
                expires_at=expires_at
            )
            
            # Verify result
            assert result is True
            
            # Verify logging
            mock_logger.info.assert_called()
            mock_logger.debug.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_waitlist_joined_success(self, notification_service, waitlist_data, event_data):
        """Test successful waitlist joined notification."""
        # Test with enabled service
        notification_service.enable()
        
        with patch('app.services.notification_service.logger') as mock_logger:
            result = await notification_service.send_waitlist_joined(
                user_id=1,
                waitlist_data=waitlist_data,
                event_data=event_data,
                position=1
            )
            
            # Verify result
            assert result is True
            
            # Verify logging
            mock_logger.info.assert_called()
            mock_logger.debug.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_waitlist_cancellation_success(self, notification_service, waitlist_data, event_data):
        """Test successful waitlist cancellation notification."""
        # Test with enabled service
        notification_service.enable()
        
        with patch('app.services.notification_service.logger') as mock_logger:
            result = await notification_service.send_waitlist_cancellation(
                user_id=1,
                waitlist_data=waitlist_data,
                event_data=event_data
            )
            
            # Verify result
            assert result is True
            
            # Verify logging
            mock_logger.info.assert_called()
            mock_logger.debug.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_bulk_notifications_success(self, notification_service):
        """Test successful bulk notifications."""
        # Test with enabled service
        notification_service.enable()
        
        notifications = [
            {"type": "booking_confirmation", "user_id": 1, "data": {"id": 1}},
            {"type": "waitlist_notification", "user_id": 2, "data": {"id": 2}}
        ]
        
        with patch('app.services.notification_service.logger') as mock_logger:
            result = await notification_service.send_bulk_notifications(notifications)
            
            # Verify result
            assert result["success"] == 2
            assert result["failed"] == 0
            
            # Verify logging
            mock_logger.info.assert_called()
            mock_logger.debug.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_bulk_notifications_disabled(self, notification_service):
        """Test bulk notifications when service is disabled."""
        # Test with disabled service
        notification_service.disable()
        
        notifications = [
            {"type": "booking_confirmation", "user_id": 1, "data": {"id": 1}}
        ]
        
        with patch('app.services.notification_service.logger') as mock_logger:
            result = await notification_service.send_bulk_notifications(notifications)
            
            # Verify result
            assert result["success"] == 1
            assert result["failed"] == 0
            
            # Verify logging
            mock_logger.info.assert_called_with("Notification service disabled, skipping bulk notifications")
    
    @pytest.mark.asyncio
    async def test_notification_service_management(self, notification_service):
        """Test notification service enable/disable functionality."""
        # Test initial state
        assert notification_service.is_enabled() is True
        
        # Test disable
        notification_service.disable()
        assert notification_service.is_enabled() is False
        
        # Test enable
        notification_service.enable()
        assert notification_service.is_enabled() is True
    
    @pytest.mark.asyncio
    async def test_get_notification_stats(self, notification_service):
        """Test getting notification service statistics."""
        # Test with enabled service
        notification_service.enable()
        
        with patch('app.services.notification_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            
            result = await notification_service.get_notification_stats()
            
            # Verify result
            assert result["enabled"] is True
            assert result["providers_count"] == 0
            assert "last_updated" in result
    
    @pytest.mark.asyncio
    async def test_notification_error_handling(self, notification_service, booking_data):
        """Test notification error handling."""
        # Test with enabled service
        notification_service.enable()
        
        # Mock an exception in the notification process
        with patch('app.services.notification_service.logger') as mock_logger:
            # Simulate an error by mocking logger to raise an exception
            mock_logger.info.side_effect = Exception("Test error")
            
            result = await notification_service.send_booking_confirmation(
                user_id=1,
                booking_data=booking_data
            )
            
            # Verify result - should return False on error
            assert result is False
            
            # Verify error logging
            mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_notification_without_event_data(self, notification_service, booking_data):
        """Test notification without optional event data."""
        # Test with enabled service
        notification_service.enable()
        
        with patch('app.services.notification_service.logger') as mock_logger:
            result = await notification_service.send_booking_confirmation(
                user_id=1,
                booking_data=booking_data
                # No event_data provided
            )
            
            # Verify result
            assert result is True
            
            # Verify logging
            mock_logger.info.assert_called()
            mock_logger.debug.assert_called()