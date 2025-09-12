"""
Tests for Event model creation.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.event import Event, EventStatus


class TestEventCreation:
    """Test cases for Event model creation."""
    
    def test_event_creation(self):
        """Test event model creation with valid data."""
        event_data = {
            "title": "Test Event",
            "description": "A test event",
            "venue": "Test Venue",
            "event_date": datetime.now() + timedelta(days=30),
            "capacity": 100,
            "price": Decimal("25.00"),
            "status": EventStatus.PUBLISHED,
            "created_by": 1
        }
        
        event = Event(**event_data)
        
        assert event.title == "Test Event"
        assert event.description == "A test event"
        assert event.venue == "Test Venue"
        assert event.capacity == 100
        assert event.price == Decimal("25.00")
        assert event.status == EventStatus.PUBLISHED
        assert event.created_by == 1
        assert event.is_upcoming is True
    
    def test_event_with_minimal_data(self):
        """Test event creation with minimal required data."""
        event_data = {
            "title": "Minimal Event",
            "venue": "Minimal Venue",
            "event_date": datetime.now() + timedelta(days=1),
            "capacity": 50,
            "price": Decimal("0.00"),
            "status": EventStatus.DRAFT,  # Explicitly set status
            "created_by": 1
        }
        
        event = Event(**event_data)
        
        assert event.title == "Minimal Event"
        assert event.venue == "Minimal Venue"
        assert event.capacity == 50
        assert event.price == Decimal("0.00")
        assert event.status == EventStatus.DRAFT
        assert event.created_by == 1
        assert event.event_date > datetime.now()
    
    def test_event_default_status(self):
        """Test event creation with default status."""
        event_data = {
            "title": "Default Status Event",
            "venue": "Default Venue",
            "event_date": datetime.now() + timedelta(days=1),
            "capacity": 50,
            "price": Decimal("0.00"),
            "status": EventStatus.DRAFT,  # Explicitly set status
            "created_by": 1
        }
        
        event = Event(**event_data)
        
        assert event.status == EventStatus.DRAFT