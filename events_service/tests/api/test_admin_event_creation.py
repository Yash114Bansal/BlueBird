"""
Tests for admin event creation functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from decimal import Decimal

from app.models.event import Event, EventStatus
from app.schemas.event import EventCreate
from app.api.v1.events_admin import create_event


class TestAdminEventCreation:
    """Test cases for admin event creation."""
    
    @pytest.fixture
    def mock_event_repo(self):
        """Mock event repository."""
        return MagicMock()
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_admin_token(self):
        """Mock JWT token for admin user."""
        return {
            "user_id": 1,
            "email": "admin@example.com",
            "role": "admin"
        }
    
    @pytest.mark.asyncio
    async def test_create_event_success(
        self,
        mock_event_repo,
        mock_cache_manager,
        mock_admin_token
    ):
        """Test successful event creation."""
        created_event = Event(
            id=1,
            title="New Event",
            description="A new event",
            venue="New Venue",
            event_date=datetime(2024, 12, 31, 18, 0, 0),
            capacity=100,
            price=Decimal("25.00"),
            status=EventStatus.DRAFT,
            created_by=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_event_repo.create.return_value = created_event
        mock_cache_manager.delete_pattern.return_value = None
        
        event_data = EventCreate(
            title="New Event",
            description="A new event",
            venue="New Venue",
            event_date=datetime(2024, 12, 31, 18, 0, 0),
            capacity=100,
            price=Decimal("25.00"),
            status="draft"
        )
        
        result = await create_event(
            event_data=event_data,
            current_user=mock_admin_token,
            event_repo=mock_event_repo,
            cache_manager=mock_cache_manager
        )
        
        assert result.title == "New Event"
        assert result.id == 1
        mock_event_repo.create.assert_called_once()
        mock_cache_manager.delete_pattern.assert_called_once_with("events:list:*")