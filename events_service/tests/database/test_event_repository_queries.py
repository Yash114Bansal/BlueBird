"""
Tests for EventRepository query operations.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.event import Event, EventStatus
from app.db.database import EventRepository


class TestEventRepositoryQueries:
    """Test cases for EventRepository query operations."""
    
    def test_get_all_events(self, db_session: Session):
        """Test getting all events."""
        repo = EventRepository(db_session)
        
        # Create multiple events
        for i in range(3):
            event_data = {
                "title": f"Event {i+1}",
                "venue": f"Venue {i+1}",
                "event_date": datetime.now() + timedelta(days=30+i),
                "capacity": 100,
                "price": Decimal("25.00"),
                "status": EventStatus.PUBLISHED,
                "created_by": 1
            }
            repo.create(event_data)
        
        events = repo.get_all()
        
        assert len(events) == 3
        assert events[0].title == "Event 1"
        assert events[1].title == "Event 2"
        assert events[2].title == "Event 3"
    
    def test_get_events_with_pagination(self, db_session: Session):
        """Test getting events with pagination."""
        repo = EventRepository(db_session)
        
        # Create multiple events
        for i in range(5):
            event_data = {
                "title": f"Event {i+1}",
                "venue": f"Venue {i+1}",
                "event_date": datetime.now() + timedelta(days=30+i),
                "capacity": 100,
                "price": Decimal("25.00"),
                "status": EventStatus.PUBLISHED,
                "created_by": 1
            }
            repo.create(event_data)
        
        # Test pagination
        events_page1 = repo.get_all(skip=0, limit=2)
        events_page2 = repo.get_all(skip=2, limit=2)
        
        assert len(events_page1) == 2
        assert len(events_page2) == 2
        assert events_page1[0].title == "Event 1"
        assert events_page1[1].title == "Event 2"
        assert events_page2[0].title == "Event 3"
        assert events_page2[1].title == "Event 4"
    
    def test_get_events_by_status(self, db_session: Session):
        """Test getting events by status."""
        repo = EventRepository(db_session)
        
        # Create events with different statuses
        for status in [EventStatus.DRAFT, EventStatus.PUBLISHED, EventStatus.CANCELLED]:
            event_data = {
                "title": f"Event {status.value}",
                "venue": f"Venue {status.value}",
                "event_date": datetime.now() + timedelta(days=30),
                "capacity": 100,
                "price": Decimal("25.00"),
                "status": status,
                "created_by": 1
            }
            repo.create(event_data)
        
        # Test filtering by status
        published_events = repo.get_all(status=EventStatus.PUBLISHED)
        draft_events = repo.get_all(status=EventStatus.DRAFT)
        
        assert len(published_events) == 1
        assert len(draft_events) == 1
        assert published_events[0].status == EventStatus.PUBLISHED
        assert draft_events[0].status == EventStatus.DRAFT
    
    def test_get_upcoming_events(self, db_session: Session):
        """Test getting upcoming events."""
        repo = EventRepository(db_session)
        
        # Create events with different dates
        past_date = datetime.now() - timedelta(days=1)
        future_date1 = datetime.now() + timedelta(days=1)
        future_date2 = datetime.now() + timedelta(days=2)
        
        event_data_past = {
            "title": "Past Event",
            "venue": "Past Venue",
            "event_date": past_date,
            "capacity": 100,
            "price": Decimal("25.00"),
            "status": EventStatus.PUBLISHED,
            "created_by": 1
        }
        
        event_data_future1 = {
            "title": "Future Event 1",
            "venue": "Future Venue 1",
            "event_date": future_date1,
            "capacity": 100,
            "price": Decimal("25.00"),
            "status": EventStatus.PUBLISHED,
            "created_by": 1
        }
        
        event_data_future2 = {
            "title": "Future Event 2",
            "venue": "Future Venue 2",
            "event_date": future_date2,
            "capacity": 100,
            "price": Decimal("25.00"),
            "status": EventStatus.PUBLISHED,
            "created_by": 1
        }
        
        repo.create(event_data_past)
        repo.create(event_data_future1)
        repo.create(event_data_future2)
        
        upcoming_events = repo.get_upcoming_events()
        
        assert len(upcoming_events) == 2
        assert upcoming_events[0].title == "Future Event 1"
        assert upcoming_events[1].title == "Future Event 2"
    
    def test_count_events(self, db_session: Session):
        """Test counting events."""
        repo = EventRepository(db_session)
        
        # Create multiple events
        for i in range(3):
            event_data = {
                "title": f"Event {i+1}",
                "venue": f"Venue {i+1}",
                "event_date": datetime.now() + timedelta(days=30+i),
                "capacity": 100,
                "price": Decimal("25.00"),
                "status": EventStatus.PUBLISHED,
                "created_by": 1
            }
            repo.create(event_data)
        
        total_count = repo.count()
        
        assert total_count == 3