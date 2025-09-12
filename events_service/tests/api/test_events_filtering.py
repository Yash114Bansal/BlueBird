"""
Tests for events filtering functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.api.v1.events_public import list_events


class TestEventsFiltering:
    """Test cases for event filtering."""
    
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
    async def test_list_events_with_status_filter(
        self,
        mock_event_repo,
        mock_cache_manager,
        mock_user_token
    ):
        """Test event listing with status filter."""
        mock_events = []
        mock_event_repo.get_all.return_value = mock_events
        mock_event_repo.count.return_value = 0
        mock_cache_manager.get_cached_events_list.return_value = None
        
        result = await list_events(
            page=1,
            size=10,
            status="published",
            current_user=mock_user_token,
            event_repo=mock_event_repo,
            cache_manager=mock_cache_manager
        )
        
        assert result is not None
        mock_event_repo.get_all.assert_called_once_with(skip=0, limit=10, status="published")
        mock_event_repo.count.assert_called_once_with(status="published")
    
    @pytest.mark.asyncio
    async def test_list_events_from_cache(
        self,
        mock_event_repo,
        mock_cache_manager,
        mock_user_token
    ):
        """Test event listing returns cached data."""
        cached_data = {
            "events": [],
            "total": 0,
            "page": 1,
            "size": 10,
            "has_next": False,
            "has_prev": False
        }
        mock_cache_manager.get_cached_events_list.return_value = cached_data
        
        result = await list_events(
            page=1,
            size=10,
            status=None,
            current_user=mock_user_token,
            event_repo=mock_event_repo,
            cache_manager=mock_cache_manager
        )
        
        assert result == cached_data
        mock_event_repo.get_all.assert_not_called()
        mock_event_repo.count.assert_not_called()