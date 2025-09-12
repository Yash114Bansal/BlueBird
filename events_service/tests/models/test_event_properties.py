"""
Tests for Event model properties and methods.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.event import Event, EventStatus


class TestEventProperties:
    """Test cases for Event model properties and methods."""
    
    def test_event_is_upcoming_property(self):
        """Test event is_upcoming property."""
        # Future event
        future_event_data = {
            "title": "Future Event",
            "venue": "Future Venue",
            "event_date": datetime.now() + timedelta(days=1),
            "capacity": 100,
            "price": Decimal("25.00"),
            "status": EventStatus.PUBLISHED,
            "created_by": 1
        }
        
        future_event = Event(**future_event_data)
        assert future_event.is_upcoming is True
        
        # Past event
        past_event_data = {
            "title": "Past Event",
            "venue": "Past Venue",
            "event_date": datetime.now() - timedelta(days=1),
            "capacity": 100,
            "price": Decimal("25.00"),
            "status": EventStatus.PUBLISHED,
            "created_by": 1
        }
        
        past_event = Event(**past_event_data)
        assert past_event.is_upcoming is False
    
    def test_event_repr(self):
        """Test event string representation."""
        event_data = {
            "title": "Test Event",
            "venue": "Test Venue",
            "event_date": datetime.now() + timedelta(days=1),
            "capacity": 100,
            "price": Decimal("25.00"),
            "status": EventStatus.PUBLISHED,
            "created_by": 1
        }
        
        event = Event(**event_data)
        repr_str = repr(event)
        
        assert "Test Event" in repr_str
        assert "Test Venue" in repr_str
    
    def test_event_status_enum(self):
        """Test EventStatus enum values."""
        assert EventStatus.DRAFT == "draft"
        assert EventStatus.PUBLISHED == "published"
        assert EventStatus.CANCELLED == "cancelled"