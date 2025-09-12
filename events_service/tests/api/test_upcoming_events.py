"""
Tests for upcoming events functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.api.v1.events_public import list_upcoming_events


class TestUpcomingEvents:
    """Test cases for upcoming events."""
    
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
    async def test_list_upcoming_events(
        self,
        mock_event_repo,
        mock_cache_manager,
        mock_user_token
    ):
        """Test listing upcoming events."""
        mock_events = []
        mock_event_repo.get_upcoming_events.return_value = mock_events
        mock_cache_manager.get_cached_events_list.return_value = None
        
        result = await list_upcoming_events(
            page=1,
            size=10,
            current_user=mock_user_token,
            event_repo=mock_event_repo,
            cache_manager=mock_cache_manager
        )
        
        assert result is not None
        mock_event_repo.get_upcoming_events.assert_called_once_with(skip=0, limit=10)