"""
Tests for events listing functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.event import Event, EventStatus
from app.api.v1.events_public import list_events


class TestEventsListing:
    """Test cases for listing events."""
    
    @pytest.fixture
    def mock_user_token(self):
        """Mock JWT token for authenticated user."""
        return {
            "user_id": 1,
            "email": "test@example.com",
            "role": "user"
        }
    
    @pytest.fixture
    def mock_event_repo(self):
        """Mock event repository."""
        return MagicMock()
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager."""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_list_events_success(
        self,
        mock_event_repo,
        mock_cache_manager,
        mock_user_token
    ):
        """Test successful event listing."""
        mock_events = [
            Event(
                id=1,
                title="Event 1",
                description="Description 1",
                venue="Venue 1",
                event_date=datetime.now() + timedelta(days=1),
                capacity=100,
                price=Decimal("25.00"),
                status=EventStatus.PUBLISHED,
                created_by=1,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        mock_event_repo.get_all.return_value = mock_events
        mock_event_repo.count.return_value = 1
        mock_cache_manager.get_cached_events_list.return_value = None
        
        result = await list_events(
            page=1,
            size=10,
            status=None,
            current_user=mock_user_token,
            event_repo=mock_event_repo,
            cache_manager=mock_cache_manager
        )
        
        assert "events" in result
        assert result["total"] == 1
        assert result["page"] == 1
        assert result["size"] == 10
        assert len(result["events"]) == 1
        assert result["events"][0].title == "Event 1"
    
    @pytest.mark.asyncio
    async def test_list_events_with_pagination(
        self,
        mock_event_repo,
        mock_cache_manager,
        mock_user_token
    ):
        """Test event listing with pagination."""
        mock_events = []
        mock_event_repo.get_all.return_value = mock_events
        mock_event_repo.count.return_value = 0
        mock_cache_manager.get_cached_events_list.return_value = None
        
        result = await list_events(
            page=2,
            size=5,
            status=None,
            current_user=mock_user_token,
            event_repo=mock_event_repo,
            cache_manager=mock_cache_manager
        )
        
        assert result["page"] == 2
        assert result["size"] == 5
        mock_event_repo.get_all.assert_called_once_with(skip=5, limit=5)