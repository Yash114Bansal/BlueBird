"""
Tests for Event Publisher Service.
Tests event publishing functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime, timezone
from decimal import Decimal

from app.services.event_publisher import EventPublisher
from app.models.event import Event, EventStatus


class TestEventPublisher:
    """Test EventPublisher functionality."""
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager for testing."""
        mock_cache = MagicMock()
        mock_cache.redis = AsyncMock()
        mock_cache.redis.publish = AsyncMock()
        return mock_cache
    
    @pytest.fixture
    def publisher(self, mock_cache_manager):
        """Create publisher instance for testing."""
        return EventPublisher(mock_cache_manager)
    
    def _create_mock_event(self, **kwargs):
        """Helper to create mock event objects with real values."""
        class MockEvent:
            def __init__(self, **attrs):
                # Default values
                self.id = 1
                self.title = "Test Event"
                self.capacity = 100
                self.price = Decimal("25.50")
                self.event_date = datetime(2024, 6, 15, 18, 0, 0, tzinfo=timezone.utc)
                self.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                self.updated_at = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
                self.category = "Technology"
                self.status = "published"
                
                # Override with provided values
                for key, value in attrs.items():
                    setattr(self, key, value)
        
        return MockEvent(**kwargs)

    @pytest.fixture
    def mock_event(self):
        """Mock event object for testing."""
        return self._create_mock_event()
    
    def test_publisher_initialization(self, publisher):
        """Test that EventPublisher initializes correctly."""
        assert publisher is not None
        assert publisher.channel_prefix == "evently:events"
        assert publisher.cache_manager is not None
    
    def test_publisher_has_required_methods(self, publisher):
        """Test that EventPublisher has required methods."""
        required_methods = [
            'publish_event_created',
            'publish_event_updated',
            'publish_event_deleted'
        ]
        
        for method_name in required_methods:
            assert hasattr(publisher, method_name), f"Missing method: {method_name}"
            assert callable(getattr(publisher, method_name)), f"Method not callable: {method_name}"
    
    @pytest.mark.asyncio
    async def test_publish_event_created_success(self, publisher, mock_event, mock_cache_manager):
        """Test successful event created publishing."""
        # Call the method
        await publisher.publish_event_created(mock_event)
        
        # Verify Redis publish was called
        mock_cache_manager.redis.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_cache_manager.redis.publish.call_args
        channel = call_args[0][0]
        message_str = call_args[0][1]
        
        # Verify channel
        assert channel == "evently:events:created"
        
        # Verify message content
        message = json.loads(message_str)
        assert message["type"] == "EventCreated"
        assert message["event_id"] == 1
        
        # Verify event data
        event_data = message["event_data"]
        assert event_data["id"] == 1
        assert event_data["name"] == "Test Event"  # Analytics service expects 'name' field
        assert event_data["title"] == "Test Event"
        assert event_data["category"] == "Technology"
        assert event_data["capacity"] == 100
        assert event_data["price"] == 25.5
        assert event_data["event_date"] == "2024-06-15T18:00:00+00:00"
        assert event_data["created_at"] == "2024-01-01T12:00:00+00:00"
    
    @pytest.mark.asyncio
    async def test_publish_event_updated_success(self, publisher, mock_event, mock_cache_manager):
        """Test successful event updated publishing."""
        # Call the method
        await publisher.publish_event_updated(mock_event)
        
        # Verify Redis publish was called
        mock_cache_manager.redis.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_cache_manager.redis.publish.call_args
        channel = call_args[0][0]
        message_str = call_args[0][1]
        
        # Verify channel
        assert channel == "evently:events:updated"
        
        # Verify message content
        message = json.loads(message_str)
        assert message["type"] == "EventUpdated"
        assert message["event_id"] == 1
        
        # Verify event data
        event_data = message["event_data"]
        assert event_data["id"] == 1
        assert event_data["name"] == "Test Event"
        assert event_data["title"] == "Test Event"
        assert event_data["category"] == "Technology"
        assert event_data["capacity"] == 100
        assert event_data["price"] == 25.5
        assert event_data["event_date"] == "2024-06-15T18:00:00+00:00"
        assert event_data["updated_at"] == "2024-01-01T12:30:00+00:00"
    
    @pytest.mark.asyncio
    async def test_publish_event_deleted_success(self, publisher, mock_cache_manager):
        """Test successful event deleted publishing."""
        # Call the method
        await publisher.publish_event_deleted(123)
        
        # Verify Redis publish was called
        mock_cache_manager.redis.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_cache_manager.redis.publish.call_args
        channel = call_args[0][0]
        message_str = call_args[0][1]
        
        # Verify channel
        assert channel == "evently:events:deleted"
        
        # Verify message content
        message = json.loads(message_str)
        assert message["type"] == "EventDeleted"
        assert message["event_id"] == 123
    
    @pytest.mark.asyncio
    async def test_publish_event_created_with_none_values(self, publisher, mock_cache_manager):
        """Test publishing event created with None values."""
        # Create event with None values
        event = self._create_mock_event(
            price=None,
            event_date=None,
            created_at=None,
            category=None
        )
        
        # Call the method
        await publisher.publish_event_created(event)
        
        # Verify Redis publish was called
        mock_cache_manager.redis.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_cache_manager.redis.publish.call_args
        message_str = call_args[0][1]
        
        # Verify message content handles None values
        message = json.loads(message_str)
        event_data = message["event_data"]
        assert event_data["price"] == 0.0
        assert event_data["event_date"] is None
        assert event_data["created_at"] is None
        assert event_data["category"] is None
    
    @pytest.mark.asyncio
    async def test_publish_event_updated_with_none_values(self, publisher, mock_cache_manager):
        """Test publishing event updated with None values."""
        # Create event with None values
        event = self._create_mock_event(
            price=None,
            event_date=None,
            updated_at=None,
            category=None
        )
        
        # Call the method
        await publisher.publish_event_updated(event)
        
        # Verify Redis publish was called
        mock_cache_manager.redis.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_cache_manager.redis.publish.call_args
        message_str = call_args[0][1]
        
        # Verify message content handles None values
        message = json.loads(message_str)
        event_data = message["event_data"]
        assert event_data["price"] == 0.0
        assert event_data["event_date"] is None
        assert event_data["updated_at"] is None
        assert event_data["category"] is None
    
    @pytest.mark.asyncio
    async def test_publish_event_created_redis_error(self, publisher, mock_event, mock_cache_manager):
        """Test handling of Redis publish errors."""
        # Make Redis publish raise an exception
        mock_cache_manager.redis.publish.side_effect = Exception("Redis connection failed")
        
        # Call the method - should not raise exception
        await publisher.publish_event_created(mock_event)
        
        # Verify Redis publish was called
        mock_cache_manager.redis.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_event_updated_redis_error(self, publisher, mock_event, mock_cache_manager):
        """Test handling of Redis publish errors."""
        # Make Redis publish raise an exception
        mock_cache_manager.redis.publish.side_effect = Exception("Redis connection failed")
        
        # Call the method - should not raise exception
        await publisher.publish_event_updated(mock_event)
        
        # Verify Redis publish was called
        mock_cache_manager.redis.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_event_deleted_redis_error(self, publisher, mock_cache_manager):
        """Test handling of Redis publish errors."""
        # Make Redis publish raise an exception
        mock_cache_manager.redis.publish.side_effect = Exception("Redis connection failed")
        
        # Call the method - should not raise exception
        await publisher.publish_event_deleted(123)
        
        # Verify Redis publish was called
        mock_cache_manager.redis.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_event_created_without_category(self, publisher, mock_cache_manager):
        """Test publishing event created without category attribute."""
        # Create event without category attribute
        event = self._create_mock_event()
        
        # Remove category attribute
        if hasattr(event, 'category'):
            delattr(event, 'category')
        
        # Call the method
        await publisher.publish_event_created(event)
        
        # Verify Redis publish was called
        mock_cache_manager.redis.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_cache_manager.redis.publish.call_args
        message_str = call_args[0][1]
        
        # Verify message content
        message = json.loads(message_str)
        event_data = message["event_data"]
        assert event_data["category"] is None
    
    @pytest.mark.asyncio
    async def test_publish_event_updated_without_category(self, publisher, mock_cache_manager):
        """Test publishing event updated without category attribute."""
        # Create event without category attribute
        event = self._create_mock_event()
        
        # Remove category attribute
        if hasattr(event, 'category'):
            delattr(event, 'category')
        
        # Call the method
        await publisher.publish_event_updated(event)
        
        # Verify Redis publish was called
        mock_cache_manager.redis.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_cache_manager.redis.publish.call_args
        message_str = call_args[0][1]
        
        # Verify message content
        message = json.loads(message_str)
        event_data = message["event_data"]
        assert event_data["category"] is None
    
    @pytest.mark.asyncio
    async def test_publish_methods_json_serialization(self, publisher, mock_cache_manager):
        """Test that all publish methods produce valid JSON."""
        # Create a properly configured mock event for each method
        def create_mock_event():
            return self._create_mock_event()
        
        # Test event created and updated methods
        for method in [publisher.publish_event_created, publisher.publish_event_updated]:
            # Reset mock for each method
            mock_cache_manager.redis.reset_mock()
            
            # Create a fresh mock event for each method
            mock_event = create_mock_event()
            
            # Call the method
            await method(mock_event)
            
            # Verify Redis publish was called
            mock_cache_manager.redis.publish.assert_called_once()
            
            # Get the message and verify it's valid JSON
            call_args = mock_cache_manager.redis.publish.call_args
            message_str = call_args[0][1]
            
            # Should not raise exception
            message = json.loads(message_str)
            assert isinstance(message, dict)
            assert "type" in message
            assert "event_id" in message
            assert "event_data" in message
        
        # Test event deleted method
        mock_cache_manager.redis.reset_mock()
        await publisher.publish_event_deleted(123)
        
        # Verify Redis publish was called
        mock_cache_manager.redis.publish.assert_called_once()
        
        # Get the message and verify it's valid JSON
        call_args = mock_cache_manager.redis.publish.call_args
        message_str = call_args[0][1]
        
        # Should not raise exception
        message = json.loads(message_str)
        assert isinstance(message, dict)
        assert "type" in message
        assert "event_id" in message
        assert message["type"] == "EventDeleted"
        assert message["event_id"] == 123
    
    @pytest.mark.asyncio
    async def test_publish_event_created_analytics_compatibility(self, publisher, mock_event, mock_cache_manager):
        """Test that event created message is compatible with analytics service."""
        # Call the method
        await publisher.publish_event_created(mock_event)
        
        # Get the message
        call_args = mock_cache_manager.redis.publish.call_args
        message_str = call_args[0][1]
        message = json.loads(message_str)
        
        # Verify analytics service compatibility
        event_data = message["event_data"]
        assert "name" in event_data  # Analytics service expects 'name' field
        assert event_data["name"] == event_data["title"]  # Should be the same as title
    
    @pytest.mark.asyncio
    async def test_publish_event_updated_analytics_compatibility(self, publisher, mock_event, mock_cache_manager):
        """Test that event updated message is compatible with analytics service."""
        # Call the method
        await publisher.publish_event_updated(mock_event)
        
        # Get the message
        call_args = mock_cache_manager.redis.publish.call_args
        message_str = call_args[0][1]
        message = json.loads(message_str)
        
        # Verify analytics service compatibility
        event_data = message["event_data"]
        assert "name" in event_data  # Analytics service expects 'name' field
        assert event_data["name"] == event_data["title"]  # Should be the same as title