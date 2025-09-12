"""
Tests for event validation functionality.
"""

import pytest
from decimal import Decimal

from app.schemas.event import EventCreate, EventUpdate


class TestEventValidation:
    """Test cases for event validation."""
    
    def test_event_create_schema_validation(self):
        """Test EventCreate schema validation."""
        valid_data = {
            "title": "Valid Event",
            "description": "A valid event",
            "venue": "Valid Venue",
            "event_date": "2024-12-31T18:00:00",
            "capacity": 100,
            "price": 25.00,
            "status": "draft"
        }
        
        event = EventCreate(**valid_data)
        assert event.title == "Valid Event"
        assert event.capacity == 100
        assert event.price == Decimal("25.00")
    
    def test_event_create_schema_invalid_capacity(self):
        """Test EventCreate schema with invalid capacity."""
        invalid_data = {
            "title": "Invalid Event",
            "venue": "Invalid Venue",
            "event_date": "2024-12-31T18:00:00",
            "capacity": 0,  # Invalid: capacity must be > 0
            "price": 25.00,
            "status": "draft"
        }
        
        with pytest.raises(ValueError):
            EventCreate(**invalid_data)
    
    def test_event_create_schema_invalid_price(self):
        """Test EventCreate schema with invalid price."""
        invalid_data = {
            "title": "Invalid Event",
            "venue": "Invalid Venue",
            "event_date": "2024-12-31T18:00:00",
            "capacity": 100,
            "price": -10.00,  # Invalid: price must be >= 0
            "status": "draft"
        }
        
        with pytest.raises(ValueError):
            EventCreate(**invalid_data)
    
    def test_event_update_schema_partial(self):
        """Test EventUpdate schema with partial data."""
        update_data = {
            "title": "Updated Title",
            "capacity": 150
        }
        
        event_update = EventUpdate(**update_data)
        assert event_update.title == "Updated Title"
        assert event_update.capacity == 150
        assert event_update.description is None  # Not provided
        assert event_update.venue is None  # Not provided