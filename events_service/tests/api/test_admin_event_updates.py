"""
Tests for admin event update functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from decimal import Decimal

from app.models.event import Event, EventStatus
from app.schemas.event import EventUpdate
from app.api.v1.events_admin import update_event


class TestAdminEventUpdates:
    """Test cases for admin event updates."""
    
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
    async def test_update_event_success(
        self,
        mock_event_repo,
        mock_cache_manager,
        mock_admin_token
    ):
        """Test successful event update."""
        existing_event = Event(
            id=1,
            title="Original Event",
            description="Original description",
            venue="Original Venue",
            event_date=datetime(2024, 12, 31, 18, 0, 0),
            capacity=100,
            price=Decimal("25.00"),
            status=EventStatus.DRAFT,
            created_by=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        updated_event = Event(
            id=1,
            title="Updated Event",
            description="Updated description",
            venue="Updated Venue",
            event_date=datetime(2024, 12, 31, 18, 0, 0),
            capacity=150,
            price=Decimal("30.00"),
            status=EventStatus.PUBLISHED,
            created_by=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        mock_event_repo.get_by_id.return_value = existing_event
        mock_event_repo.update.return_value = updated_event
        mock_cache_manager.invalidate_event_cache.return_value = None
        
        update_data = EventUpdate(
            title="Updated Event",
            description="Updated description",
            venue="Updated Venue",
            capacity=150,
            price=Decimal("30.00"),
            status="published"
        )
        
        result = await update_event(
            event_id=1,
            event_data=update_data,
            current_user=mock_admin_token,
            event_repo=mock_event_repo,
            cache_manager=mock_cache_manager
        )
        
        assert result.title == "Updated Event"
        assert result.capacity == 150
        assert result.price == Decimal("30.00")
        mock_event_repo.get_by_id.assert_called_once_with(1)
        mock_event_repo.update.assert_called_once()
        mock_cache_manager.invalidate_event_cache.assert_called_once_with(1)