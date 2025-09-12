"""
Tests for admin event deletion functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException

from app.models.event import Event, EventStatus
from app.api.v1.events_admin import delete_event


class TestAdminEventDeletion:
    """Test cases for admin event deletion."""
    
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
    async def test_delete_event_success(
        self,
        mock_event_repo,
        mock_cache_manager,
        mock_admin_token
    ):
        """Test successful event deletion."""
        existing_event = Event(
            id=1,
            title="Test Event",
            venue="Test Venue",
            event_date=datetime.now(),
            capacity=100,
            price=Decimal("25.00"),
            status=EventStatus.PUBLISHED,
            created_by=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_event_repo.get_by_id.return_value = existing_event
        mock_event_repo.delete.return_value = True
        mock_cache_manager.invalidate_event_cache.return_value = None
        
        result = await delete_event(
            event_id=1,
            current_user=mock_admin_token,
            event_repo=mock_event_repo,
            cache_manager=mock_cache_manager
        )
        
        assert result.message == "Event deleted successfully"
        assert result.success is True
        mock_event_repo.get_by_id.assert_called_once_with(1)
        mock_event_repo.delete.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_delete_event_not_found(
        self,
        mock_event_repo,
        mock_cache_manager,
        mock_admin_token
    ):
        """Test deleting non-existent event."""
        mock_event_repo.get_by_id.return_value = None
        mock_cache_manager.invalidate_event_cache.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await delete_event(
                event_id=999,
                current_user=mock_admin_token,
                event_repo=mock_event_repo,
                cache_manager=mock_cache_manager
            )
        
        assert exc_info.value.status_code == 404
        assert "Event not found" in str(exc_info.value.detail)