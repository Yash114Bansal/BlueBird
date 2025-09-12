"""
Tests for EventRepository CRUD operations.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.event import Event, EventStatus
from app.db.database import EventRepository


class TestEventRepositoryCRUD:
    """Test cases for EventRepository CRUD operations."""
    
    def test_create_event(self, db_session: Session):
        """Test creating a new event."""
        repo = EventRepository(db_session)
        
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
        
        event = repo.create(event_data)
        
        assert event.id is not None
        assert event.title == "Test Event"
        assert event.description == "A test event"
        assert event.venue == "Test Venue"
        assert event.capacity == 100
        assert event.price == Decimal("25.00")
        assert event.status == EventStatus.PUBLISHED
        assert event.created_by == 1
        assert event.created_at is not None
        assert event.updated_at is not None
    
    def test_get_event_by_id(self, db_session: Session):
        """Test getting an event by ID."""
        repo = EventRepository(db_session)
        
        # Create an event first
        event_data = {
            "title": "Test Event",
            "venue": "Test Venue",
            "event_date": datetime.now() + timedelta(days=30),
            "capacity": 100,
            "price": Decimal("25.00"),
            "status": EventStatus.PUBLISHED,
            "created_by": 1
        }
        
        created_event = repo.create(event_data)
        event_id = created_event.id
        
        # Retrieve the event
        retrieved_event = repo.get_by_id(event_id)
        
        assert retrieved_event is not None
        assert retrieved_event.id == event_id
        assert retrieved_event.title == "Test Event"
        assert retrieved_event.venue == "Test Venue"
    
    def test_get_event_by_nonexistent_id(self, db_session: Session):
        """Test getting an event by non-existent ID."""
        repo = EventRepository(db_session)
        
        retrieved_event = repo.get_by_id(999)
        
        assert retrieved_event is None
    
    def test_update_event(self, db_session: Session):
        """Test updating an event."""
        repo = EventRepository(db_session)
        
        # Create an event first
        event_data = {
            "title": "Original Event",
            "venue": "Original Venue",
            "event_date": datetime.now() + timedelta(days=30),
            "capacity": 100,
            "price": Decimal("25.00"),
            "status": EventStatus.DRAFT,
            "created_by": 1
        }
        
        created_event = repo.create(event_data)
        event_id = created_event.id
        
        # Update the event
        update_data = {
            "title": "Updated Event",
            "capacity": 150,
            "price": Decimal("30.00")
        }
        
        updated_event = repo.update(event_id, update_data)
        
        assert updated_event is not None
        assert updated_event.id == event_id
        assert updated_event.title == "Updated Event"
        assert updated_event.capacity == 150
        assert updated_event.price == Decimal("30.00")
        assert updated_event.venue == "Original Venue"  # Unchanged
    
    def test_update_nonexistent_event(self, db_session: Session):
        """Test updating a non-existent event."""
        repo = EventRepository(db_session)
        
        update_data = {"title": "Updated Event"}
        updated_event = repo.update(999, update_data)
        
        assert updated_event is None
    
    def test_delete_event(self, db_session: Session):
        """Test deleting an event."""
        repo = EventRepository(db_session)
        
        # Create an event first
        event_data = {
            "title": "Event to Delete",
            "venue": "Delete Venue",
            "event_date": datetime.now() + timedelta(days=30),
            "capacity": 100,
            "price": Decimal("25.00"),
            "status": EventStatus.PUBLISHED,
            "created_by": 1
        }
        
        created_event = repo.create(event_data)
        event_id = created_event.id
        
        # Delete the event
        result = repo.delete(event_id)
        
        assert result is True
        
        # Verify the event is deleted
        deleted_event = repo.get_by_id(event_id)
        assert deleted_event is None
    
    def test_delete_nonexistent_event(self, db_session: Session):
        """Test deleting a non-existent event."""
        repo = EventRepository(db_session)
        
        result = repo.delete(999)
        
        assert result is False