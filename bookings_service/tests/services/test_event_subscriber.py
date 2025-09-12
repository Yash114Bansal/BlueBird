"""
Tests for Event Subscriber Service.
Tests event handling and message processing.
"""

import pytest
from unittest.mock import AsyncMock, patch
import json

from app.services.event_subscriber import EventSubscriber


class TestEventSubscriber:
    """Test Event Subscriber functionality."""
    
    @pytest.fixture
    def event_subscriber(self):
        """Create event subscriber instance for testing."""
        return EventSubscriber()
    
    def test_event_subscriber_initialization(self, event_subscriber):
        """Test that EventSubscriber initializes correctly."""
        assert event_subscriber is not None
    
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
    async def test_handle_message_method_signature(self, event_subscriber):
        """Test that _handle_message method accepts correct parameters."""
        import inspect
        
        # Get the method signature
        sig = inspect.signature(event_subscriber._handle_message)
        params = list(sig.parameters.keys())
        
        # Should have message parameter
        assert 'message' in params