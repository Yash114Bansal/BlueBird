"""
Tests for Event model validation.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.event import Event, EventStatus


class TestEventValidation:
    """Test cases for Event model validation."""
    
    def test_event_with_zero_capacity(self):
        """Test event with zero capacity."""
        event_data = {
            "title": "Zero Capacity Event",
            "venue": "Zero Venue",
            "event_date": datetime.now() + timedelta(days=1),
            "capacity": 0,
            "price": Decimal("25.00"),
            "status": EventStatus.DRAFT,
            "created_by": 1
        }
        
        event = Event(**event_data)
        
        assert event.capacity == 0
        assert event.title == "Zero Capacity Event"
    
    def test_event_with_negative_price(self):
        """Test event with negative price."""
        event_data = {
            "title": "Negative Price Event",
            "venue": "Negative Venue",
            "event_date": datetime.now() + timedelta(days=1),
            "capacity": 100,
            "price": Decimal("-10.00"),
            "status": EventStatus.DRAFT,
            "created_by": 1
        }
        
        event = Event(**event_data)
        
        assert event.price == Decimal("-10.00")
        assert event.title == "Negative Price Event"
    
    def test_event_with_high_capacity(self):
        """Test event with high capacity."""
        event_data = {
            "title": "High Capacity Event",
            "venue": "High Capacity Venue",
            "event_date": datetime.now() + timedelta(days=1),
            "capacity": 10000,
            "price": Decimal("25.00"),
            "status": EventStatus.DRAFT,
            "created_by": 1
        }
        
        event = Event(**event_data)
        
        assert event.capacity == 10000
        assert event.title == "High Capacity Event"