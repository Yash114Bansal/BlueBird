"""
Comprehensive Tests for Event Subscriber Service.
Tests event handling and message processing.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json
from datetime import datetime, timezone

from app.services.event_subscriber import EventSubscriber
from app.models.booking import EventAvailability


class TestEventSubscriberComprehensive:
    """Comprehensive test for Event Subscriber functionality."""
    
    @pytest.fixture
    def event_subscriber(self):
        """Create event subscriber instance for testing."""
        return EventSubscriber()
    
    @pytest.fixture
    def mock_redis_manager(self):
        """Mock Redis manager for testing."""
        mock_redis = AsyncMock()
        mock_redis.initialize = AsyncMock()
        mock_redis.redis_client = MagicMock()
        return mock_redis
    
    @pytest.fixture
    def mock_pubsub(self):
        """Mock Redis pubsub for testing."""
        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_pubsub.get_message = AsyncMock()
        return mock_pubsub
    
    def test_event_subscriber_initialization(self, event_subscriber):
        """Test that EventSubscriber initializes correctly."""
        assert event_subscriber is not None
        assert event_subscriber.channel_prefix == "evently:events"
        assert event_subscriber.running is False
        assert event_subscriber.pubsub is None
    
    def test_event_subscriber_has_required_methods(self, event_subscriber):
        """Test that EventSubscriber has required methods."""
        required_methods = [
            'start',
            'stop',
            '_listen_for_messages',
            '_handle_message',
            '_handle_event_created',
            '_handle_event_updated',
            '_handle_event_deleted'
        ]
        
        for method_name in required_methods:
            assert hasattr(event_subscriber, method_name), f"Missing method: {method_name}"
            assert callable(getattr(event_subscriber, method_name)), f"Method not callable: {method_name}"
    
    @pytest.mark.asyncio
    @patch('app.services.event_subscriber.redis_manager')
    async def test_start_success(self, mock_redis_manager, event_subscriber, mock_pubsub):
        """Test successful subscriber start."""
        # Setup mocks
        mock_redis_manager.initialize = AsyncMock()
        mock_redis_manager.redis_client.pubsub.return_value = mock_pubsub
        
        # Call start
        await event_subscriber.start()
        
        # Verify initialization
        assert event_subscriber.running is True
        assert event_subscriber.pubsub == mock_pubsub
        
        # Verify Redis initialization
        mock_redis_manager.initialize.assert_called_once()
        
        # Verify pubsub setup
        mock_redis_manager.redis_client.pubsub.assert_called_once()
        mock_pubsub.subscribe.assert_called_once()
        
        # Verify channels subscribed
        call_args = mock_pubsub.subscribe.call_args[0]
        expected_channels = [
            "evently:events:created",
            "evently:events:updated", 
            "evently:events:deleted"
        ]
        assert all(channel in call_args for channel in expected_channels)
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, event_subscriber):
        """Test starting subscriber when already running."""
        # Set running to True
        event_subscriber.running = True
        
        # Call start - should return early
        await event_subscriber.start()
        
        # Should still be running
        assert event_subscriber.running is True
    
    @pytest.mark.asyncio
    async def test_stop_success(self, event_subscriber, mock_pubsub):
        """Test successful subscriber stop."""
        # Setup running state
        event_subscriber.running = True
        event_subscriber.pubsub = mock_pubsub
        
        # Call stop
        await event_subscriber.stop()
        
        # Verify state changes
        assert event_subscriber.running is False
        
        # Verify pubsub cleanup
        mock_pubsub.unsubscribe.assert_called_once()
        mock_pubsub.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_not_running(self, event_subscriber):
        """Test stopping subscriber when not running."""
        # Ensure not running
        event_subscriber.running = False
        
        # Call stop - should return early
        await event_subscriber.stop()
        
        # Should still not be running
        assert event_subscriber.running is False
    
    @pytest.mark.asyncio
    async def test_handle_message_event_created(self, event_subscriber):
        """Test handling EventCreated message."""
        # Create test message
        message_data = {
            "type": "EventCreated",
            "event_id": 100,
            "event_data": {
                "id": 100,
                "capacity": 50
            }
        }
        message = {
            "type": "message",
            "data": json.dumps(message_data)
        }
        
        # Mock the event handler
        with patch.object(event_subscriber, '_handle_event_created') as mock_handler:
            await event_subscriber._handle_message(message)
            mock_handler.assert_called_once_with(message_data)
    
    @pytest.mark.asyncio
    async def test_handle_message_event_updated(self, event_subscriber):
        """Test handling EventUpdated message."""
        # Create test message
        message_data = {
            "type": "EventUpdated",
            "event_id": 100,
            "event_data": {
                "id": 100,
                "capacity": 75
            }
        }
        message = {
            "type": "message",
            "data": json.dumps(message_data)
        }
        
        # Mock the event handler
        with patch.object(event_subscriber, '_handle_event_updated') as mock_handler:
            await event_subscriber._handle_message(message)
            mock_handler.assert_called_once_with(message_data)
    
    @pytest.mark.asyncio
    async def test_handle_message_event_deleted(self, event_subscriber):
        """Test handling EventDeleted message."""
        # Create test message
        message_data = {
            "type": "EventDeleted",
            "event_id": 100
        }
        message = {
            "type": "message",
            "data": json.dumps(message_data)
        }
        
        # Mock the event handler
        with patch.object(event_subscriber, '_handle_event_deleted') as mock_handler:
            await event_subscriber._handle_message(message)
            mock_handler.assert_called_once_with(100)
    
    @pytest.mark.asyncio
    async def test_handle_message_unknown_type(self, event_subscriber):
        """Test handling unknown event type."""
        # Create test message with unknown type
        message_data = {
            "type": "UnknownEvent",
            "event_id": 100
        }
        message = {
            "type": "message",
            "data": json.dumps(message_data)
        }
        
        # Should not raise exception
        await event_subscriber._handle_message(message)
    
    @pytest.mark.asyncio
    async def test_handle_message_invalid_json(self, event_subscriber):
        """Test handling message with invalid JSON."""
        # Create test message with invalid JSON
        message = {
            "type": "message",
            "data": "invalid json"
        }
        
        # Should not raise exception
        await event_subscriber._handle_message(message)
    
    @pytest.mark.asyncio
    @patch('app.services.event_subscriber.db_manager')
    async def test_handle_event_created_success(self, mock_db_manager, event_subscriber):
        """Test successful event created handling."""
        # Setup mocks
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_db_manager.get_session.return_value.__exit__.return_value = None
        
        # Mock query result (no existing availability)
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Test data
        data = {
            "event_data": {
                "id": 100,
                "capacity": 50
            }
        }
        
        # Call handler
        await event_subscriber._handle_event_created(data)
        
        # Verify database operations
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Verify EventAvailability was created
        added_availability = mock_session.add.call_args[0][0]
        assert isinstance(added_availability, EventAvailability)
        assert added_availability.event_id == 100
        assert added_availability.total_capacity == 50
        assert added_availability.available_capacity == 50
        assert added_availability.reserved_capacity == 0
        assert added_availability.confirmed_capacity == 0
    
    @pytest.mark.asyncio
    @patch('app.services.event_subscriber.db_manager')
    async def test_handle_event_created_already_exists(self, mock_db_manager, event_subscriber):
        """Test event created handling when availability already exists."""
        # Setup mocks
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_db_manager.get_session.return_value.__exit__.return_value = None
        
        # Mock existing availability
        existing_availability = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = existing_availability
        
        # Test data
        data = {
            "event_data": {
                "id": 100,
                "capacity": 50
            }
        }
        
        # Call handler
        await event_subscriber._handle_event_created(data)
        
        # Verify no new availability was added
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('app.services.event_subscriber.db_manager')
    async def test_handle_event_updated_success(self, mock_db_manager, event_subscriber):
        """Test successful event updated handling."""
        # Setup mocks
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_db_manager.get_session.return_value.__exit__.return_value = None
        
        # Mock existing availability
        existing_availability = MagicMock()
        existing_availability.total_capacity = 50
        existing_availability.available_capacity = 30
        existing_availability.version = 1
        mock_session.query.return_value.filter.return_value.first.return_value = existing_availability
        
        # Test data
        data = {
            "event_data": {
                "id": 100,
                "capacity": 75
            }
        }
        
        # Call handler
        await event_subscriber._handle_event_updated(data)
        
        # Verify availability was updated
        assert existing_availability.total_capacity == 75
        assert existing_availability.available_capacity == 55  # 30 + (75-50)
        assert existing_availability.version == 2
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.event_subscriber.db_manager')
    async def test_handle_event_updated_not_found(self, mock_db_manager, event_subscriber):
        """Test event updated handling when availability not found."""
        # Setup mocks
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_db_manager.get_session.return_value.__exit__.return_value = None
        
        # Mock no existing availability
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Test data
        data = {
            "event_data": {
                "id": 100,
                "capacity": 75
            }
        }
        
        # Call handler
        await event_subscriber._handle_event_updated(data)
        
        # Verify new availability was created
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Verify EventAvailability was created
        added_availability = mock_session.add.call_args[0][0]
        assert isinstance(added_availability, EventAvailability)
        assert added_availability.event_id == 100
        assert added_availability.total_capacity == 75
    
    @pytest.mark.asyncio
    @patch('app.services.event_subscriber.db_manager')
    async def test_handle_event_deleted_success(self, mock_db_manager, event_subscriber):
        """Test successful event deleted handling."""
        # Setup mocks
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_db_manager.get_session.return_value.__exit__.return_value = None
        
        # Mock existing availability
        existing_availability = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = existing_availability
        
        # Call handler
        await event_subscriber._handle_event_deleted(100)
        
        # Verify availability was deleted
        mock_session.delete.assert_called_once_with(existing_availability)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.event_subscriber.db_manager')
    async def test_handle_event_deleted_not_found(self, mock_db_manager, event_subscriber):
        """Test event deleted handling when availability not found."""
        # Setup mocks
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_db_manager.get_session.return_value.__exit__.return_value = None
        
        # Mock no existing availability
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Call handler
        await event_subscriber._handle_event_deleted(100)
        
        # Verify no deletion occurred
        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_event_created_missing_event_id(self, event_subscriber):
        """Test event created handling with missing event ID."""
        # Test data without event ID
        data = {
            "event_data": {
                "capacity": 50
            }
        }
        
        # Should not raise exception
        await event_subscriber._handle_event_created(data)
    
    @pytest.mark.asyncio
    async def test_handle_event_updated_missing_capacity(self, event_subscriber):
        """Test event updated handling with missing capacity."""
        # Test data without capacity
        data = {
            "event_data": {
                "id": 100
            }
        }
        
        # Should not raise exception
        await event_subscriber._handle_event_updated(data)
    
    @pytest.mark.asyncio
    @patch('app.services.event_subscriber.db_manager')
    async def test_handle_event_updated_negative_available_capacity(self, mock_db_manager, event_subscriber):
        """Test event updated handling that results in negative available capacity."""
        # Setup mocks
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_db_manager.get_session.return_value.__exit__.return_value = None
        
        # Mock existing availability with high used capacity
        existing_availability = MagicMock()
        existing_availability.total_capacity = 100
        existing_availability.available_capacity = 20  # 80 used
        existing_availability.version = 1
        mock_session.query.return_value.filter.return_value.first.return_value = existing_availability
        
        # Test data - reduce capacity significantly
        data = {
            "event_data": {
                "id": 100,
                "capacity": 50  # Reduce from 100 to 50
            }
        }
        
        # Call handler
        await event_subscriber._handle_event_updated(data)
        
        # Verify availability was updated with available_capacity clamped to 0
        assert existing_availability.total_capacity == 50
        assert existing_availability.available_capacity == 0  # max(0, 20 + (50-100)) = max(0, -30) = 0
        assert existing_availability.version == 2
        mock_session.commit.assert_called_once()