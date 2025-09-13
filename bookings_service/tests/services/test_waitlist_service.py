"""
Tests for Waitlist Service.
Tests waitlist operations with high consistency and proper validations.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

from app.services.waitlist_service import WaitlistService
from app.models.booking import WaitlistEntry, WaitlistStatus, EventAvailability
from app.schemas.booking import WaitlistJoin, WaitlistCancel


class TestWaitlistService:
    """Test cases for WaitlistService."""
    
    @pytest.fixture
    def waitlist_service(self):
        """Create WaitlistService instance for testing."""
        return WaitlistService()
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock(spec=Session)
        session.query.return_value.filter.return_value.first.return_value = None
        session.query.return_value.filter.return_value.all.return_value = []
        session.query.return_value.filter.return_value.count.return_value = 0
        session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        return session
    
    @pytest.fixture
    def waitlist_join_data(self):
        """Create waitlist join data for testing."""
        return WaitlistJoin(
            event_id=1,
            quantity=2,
            notes="Test waitlist entry"
        )
    
    @pytest.fixture
    def waitlist_cancel_data(self):
        """Create waitlist cancel data for testing."""
        return WaitlistCancel(
            reason="Test cancellation"
        )
    
    @pytest.fixture
    def mock_waitlist_entry(self):
        """Create mock waitlist entry."""
        entry = MagicMock(spec=WaitlistEntry)
        entry.id = 1
        entry.user_id = 1
        entry.event_id = 1
        entry.quantity = 2
        entry.priority = 1
        entry.status = WaitlistStatus.PENDING
        entry.joined_at = datetime.now(timezone.utc)
        entry.created_at = datetime.now(timezone.utc)
        entry.updated_at = datetime.now(timezone.utc)
        entry.version = 1
        entry.notes = "Test waitlist entry"
        entry.to_dict.return_value = {
            "id": 1,
            "user_id": 1,
            "event_id": 1,
            "quantity": 2,
            "priority": 1,
            "status": "pending",
            "joined_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
            "notes": "Test waitlist entry"
        }
        return entry
    
    @pytest.fixture
    def mock_availability(self):
        """Create mock event availability."""
        availability = MagicMock(spec=EventAvailability)
        availability.event_id = 1
        availability.total_capacity = 100
        availability.available_capacity = 0  # Event is full
        availability.reserved_capacity = 50
        availability.confirmed_capacity = 50
        availability.version = 1
        return availability
    
    @pytest.mark.asyncio
    async def test_join_waitlist_success(self, waitlist_service, mock_session, waitlist_join_data, mock_availability):
        """Test successful waitlist join."""
        # Mock configuration
        waitlist_service.consistency_config = {"lock_timeout_seconds": 30}
        waitlist_service.waitlist_config = {"notification_expiry_minutes": 30}
        
        # Mock distributed lock
        mock_distributed_lock = AsyncMock()
        mock_distributed_lock.__aenter__ = AsyncMock(return_value=mock_distributed_lock)
        mock_distributed_lock.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.services.waitlist_service.get_distributed_lock', return_value=mock_distributed_lock):
            # Create a new mock session with proper query chain setup
            session = MagicMock(spec=Session)
            
            # Set up side effects for different queries
            def mock_query_side_effect(model):
                query_mock = MagicMock()
                filter_mock = MagicMock()
                query_mock.filter.return_value = filter_mock
                
                # Handle different types of model arguments
                if hasattr(model, '__name__'):
                    model_name = model.__name__
                elif hasattr(model, 'comparator'):
                    # This is likely a SQLAlchemy function like func.max()
                    model_name = 'func'
                else:
                    model_name = str(model)
                
                if model_name == 'WaitlistEntry':
                    # First call: check for existing entry (should return None)
                    # Second call: count for priority (should return 0)
                    filter_mock.first.return_value = None  # No existing entry
                    filter_mock.scalar.return_value = 0    # Priority calculation
                elif model_name == 'EventAvailability':
                    filter_mock.first.return_value = mock_availability
                elif model_name == 'func':
                    # This is for func.max() queries
                    filter_mock.scalar.return_value = 0    # Priority calculation
                
                return query_mock
            
            session.query.side_effect = mock_query_side_effect
            
            # Mock waitlist entry creation
            mock_waitlist_entry = MagicMock()
            mock_waitlist_entry.id = 1
            mock_waitlist_entry.to_dict.return_value = {"id": 1, "user_id": 1, "event_id": 1}
            session.add.return_value = None
            session.flush.return_value = None
            session.commit.return_value = None
            session.refresh.return_value = None
            
            with patch('app.services.waitlist_service.db_manager.get_transaction_session') as mock_get_session:
                mock_get_session.return_value.__enter__.return_value = session
                
                # Mock event publisher
                with patch.object(waitlist_service, '_get_event_publisher') as mock_get_publisher:
                    mock_publisher = AsyncMock()
                    mock_get_publisher.return_value = mock_publisher
                    
                    # Mock notification service
                    with patch('app.services.waitlist_service.notification_service.send_waitlist_joined') as mock_notify:
                        mock_notify.return_value = True
                        
                        # Test join waitlist
                        result = await waitlist_service.join_waitlist(
                            waitlist_data=waitlist_join_data,
                            user_id=1,
                            client_ip="127.0.0.1",
                            user_agent="test"
                        )
                        
                        # Verify result
                        assert result[1] is True  # Success
                        assert result[2] == 1  # Priority
                        
                        # Verify database operations
                        session.add.assert_called()
                        session.commit.assert_called()
                    
                    # Verify event publishing
                    mock_publisher.publish_waitlist_joined.assert_called_once()
                    
                    # Verify notification
                    mock_notify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_join_waitlist_event_not_found(self, waitlist_service, mock_session, waitlist_join_data):
        """Test waitlist join when event does not exist."""
        # Mock configuration
        waitlist_service.consistency_config = {"lock_timeout_seconds": 30}
        
        # Mock distributed lock
        mock_distributed_lock = AsyncMock()
        mock_distributed_lock.__aenter__ = AsyncMock(return_value=mock_distributed_lock)
        mock_distributed_lock.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.services.waitlist_service.get_distributed_lock', return_value=mock_distributed_lock):
            # Mock no availability record (event doesn't exist)
            mock_session.query.return_value.filter.return_value.first.return_value = None
            
            with patch('app.services.waitlist_service.db_manager.get_transaction_session') as mock_get_session:
                mock_get_session.return_value.__enter__.return_value = mock_session
                
                # Test join waitlist - should fail
                with pytest.raises(Exception, match="Event not found or not available for booking"):
                    await waitlist_service.join_waitlist(
                        waitlist_data=waitlist_join_data,
                        user_id=1,
                        client_ip="127.0.0.1",
                        user_agent="test"
                    )
    
    @pytest.mark.asyncio
    async def test_join_waitlist_event_has_availability(self, waitlist_service, mock_session, waitlist_join_data):
        """Test waitlist join when event has availability."""
        # Mock configuration
        waitlist_service.consistency_config = {"lock_timeout_seconds": 30}
        
        # Mock distributed lock
        mock_distributed_lock = AsyncMock()
        mock_distributed_lock.__aenter__ = AsyncMock(return_value=mock_distributed_lock)
        mock_distributed_lock.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.services.waitlist_service.get_distributed_lock', return_value=mock_distributed_lock):
            # Create a new mock session with proper query chain setup
            session = MagicMock(spec=Session)
            
            # Mock availability check - event has availability
            mock_availability = MagicMock()
            mock_availability.available_capacity = 10  # Event has availability
            
            # Set up side effects for different queries
            def mock_query_side_effect(model):
                query_mock = MagicMock()
                filter_mock = MagicMock()
                query_mock.filter.return_value = filter_mock
                
                if model.__name__ == 'WaitlistEntry':
                    # No existing entry
                    filter_mock.first.return_value = None
                elif model.__name__ == 'EventAvailability':
                    filter_mock.first.return_value = mock_availability
                
                return query_mock
            
            session.query.side_effect = mock_query_side_effect
            
            with patch('app.services.waitlist_service.db_manager.get_transaction_session') as mock_get_session:
                mock_get_session.return_value.__enter__.return_value = session
                
                # Test join waitlist - should fail
                with pytest.raises(Exception, match="Event has available capacity"):
                    await waitlist_service.join_waitlist(
                        waitlist_data=waitlist_join_data,
                        user_id=1,
                        client_ip="127.0.0.1",
                        user_agent="test"
                    )
    
    @pytest.mark.asyncio
    async def test_join_waitlist_duplicate_entry(self, waitlist_service, mock_session, waitlist_join_data, mock_waitlist_entry):
        """Test waitlist join with existing entry."""
        # Mock configuration
        waitlist_service.consistency_config = {"lock_timeout_seconds": 30}
        
        # Mock distributed lock
        mock_distributed_lock = AsyncMock()
        mock_distributed_lock.__aenter__ = AsyncMock(return_value=mock_distributed_lock)
        mock_distributed_lock.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.services.waitlist_service.get_distributed_lock', return_value=mock_distributed_lock):
            # Mock existing waitlist entry
            mock_session.query.return_value.filter.return_value.first.return_value = mock_waitlist_entry
            
            with patch('app.services.waitlist_service.db_manager.get_transaction_session') as mock_get_session:
                mock_get_session.return_value.__enter__.return_value = mock_session
                
                # Test join waitlist - should fail
                with pytest.raises(Exception, match="User already has an active waitlist entry"):
                    await waitlist_service.join_waitlist(
                        waitlist_data=waitlist_join_data,
                        user_id=1,
                        client_ip="127.0.0.1",
                        user_agent="test"
                    )
    
    @pytest.mark.asyncio
    async def test_cancel_waitlist_entry_success(self, waitlist_service, mock_session, waitlist_cancel_data, mock_waitlist_entry):
        """Test successful waitlist entry cancellation."""
        # Mock configuration
        waitlist_service.consistency_config = {"lock_timeout_seconds": 30}
        
        # Mock distributed lock
        mock_distributed_lock = AsyncMock()
        mock_distributed_lock.__aenter__ = AsyncMock(return_value=mock_distributed_lock)
        mock_distributed_lock.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.services.waitlist_service.get_distributed_lock', return_value=mock_distributed_lock):
            # Mock waitlist entry
            mock_waitlist_entry.status = WaitlistStatus.PENDING
            mock_session.query.return_value.filter.return_value.first.return_value = mock_waitlist_entry
            
            with patch('app.services.waitlist_service.db_manager.get_transaction_session') as mock_get_session:
                mock_get_session.return_value.__enter__.return_value = mock_session
                
                # Mock event publisher
                with patch.object(waitlist_service, '_get_event_publisher') as mock_get_publisher:
                    mock_publisher = AsyncMock()
                    mock_get_publisher.return_value = mock_publisher
                    
                    # Mock notification service
                    with patch('app.services.waitlist_service.notification_service.send_waitlist_cancellation') as mock_notify:
                        mock_notify.return_value = True
                        
                        # Test cancel waitlist entry
                        result = await waitlist_service.cancel_waitlist_entry(
                            waitlist_entry_id=1,
                            cancel_data=waitlist_cancel_data,
                            user_id=1
                        )
                        
                        # Verify result
                        assert result[1] is True  # Success
                        
                        # Verify database operations
                        mock_session.commit.assert_called()
                        
                        # Verify event publishing
                        mock_publisher.publish_waitlist_cancelled.assert_called_once()
                        
                        # Verify notification
                        mock_notify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_waitlist_entry_not_found(self, waitlist_service, mock_session, waitlist_cancel_data):
        """Test waitlist entry cancellation when entry not found."""
        # Mock configuration
        waitlist_service.consistency_config = {"lock_timeout_seconds": 30}
        
        # Mock distributed lock
        mock_distributed_lock = AsyncMock()
        mock_distributed_lock.__aenter__ = AsyncMock(return_value=mock_distributed_lock)
        mock_distributed_lock.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.services.waitlist_service.get_distributed_lock', return_value=mock_distributed_lock):
            # Mock no waitlist entry found
            mock_session.query.return_value.filter.return_value.first.return_value = None
            
            with patch('app.services.waitlist_service.db_manager.get_transaction_session') as mock_get_session:
                mock_get_session.return_value.__enter__.return_value = mock_session
                
                # Test cancel waitlist entry - should fail
                with pytest.raises(Exception, match="Waitlist entry not found"):
                    await waitlist_service.cancel_waitlist_entry(
                        waitlist_entry_id=1,
                        cancel_data=waitlist_cancel_data,
                        user_id=1
                    )
    
    @pytest.mark.asyncio
    async def test_notify_next_waitlist_entries(self, waitlist_service, mock_session, mock_waitlist_entry):
        """Test notifying next waitlist entries."""
        # Mock configuration
        waitlist_service.consistency_config = {"lock_timeout_seconds": 30}
        waitlist_service.waitlist_config = {"notification_expiry_minutes": 30}
        
        # Mock distributed lock
        mock_distributed_lock = AsyncMock()
        mock_distributed_lock.__aenter__ = AsyncMock(return_value=mock_distributed_lock)
        mock_distributed_lock.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.services.waitlist_service.get_distributed_lock', return_value=mock_distributed_lock):
            # Mock pending waitlist entries
            mock_waitlist_entry.status = WaitlistStatus.PENDING
            mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_waitlist_entry]
            
            with patch('app.services.waitlist_service.db_manager.get_transaction_session') as mock_get_session:
                mock_get_session.return_value.__enter__.return_value = mock_session
                
                # Mock event publisher
                with patch.object(waitlist_service, '_get_event_publisher') as mock_get_publisher:
                    mock_publisher = AsyncMock()
                    mock_get_publisher.return_value = mock_publisher
                    
                    # Mock notification service
                    with patch('app.services.waitlist_service.notification_service.send_waitlist_notification') as mock_notify:
                        mock_notify.return_value = True
                        
                        # Test notify waitlist entries
                        result = await waitlist_service.notify_next_waitlist_entries(
                            event_id=1,
                            available_quantity=2
                        )
                        
                        # Verify result
                        assert len(result) == 1
                    
                    # Verify database operations
                    mock_session.commit.assert_called()
                    
                    # Verify event publishing
                    mock_publisher.publish_waitlist_notifications_sent.assert_called_once()
                    
                    # Verify notification
                    mock_notify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_waitlist_position(self, waitlist_service, mock_session, mock_waitlist_entry):
        """Test getting waitlist position."""
        # Mock waitlist entry
        mock_waitlist_entry.priority = 3
        mock_session.query.return_value.filter.return_value.first.return_value = mock_waitlist_entry
        
        # Mock position calculation
        mock_session.query.return_value.filter.return_value.count.return_value = 2  # 2 entries with higher priority
        
        with patch('app.services.waitlist_service.db_manager.get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            # Test get position
            position = await waitlist_service.get_waitlist_position(waitlist_entry_id=1)
            
            # Verify result
            assert position == 3  # Position is count + 1
    
    @pytest.mark.asyncio
    async def test_get_waitlist_position_not_found(self, waitlist_service, mock_session):
        """Test getting waitlist position when entry not found."""
        # Mock no waitlist entry found
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch('app.services.waitlist_service.db_manager.get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            # Test get position
            position = await waitlist_service.get_waitlist_position(waitlist_entry_id=1)
            
            # Verify result
            assert position is None
    
    @pytest.mark.asyncio
    async def test_expire_notifications(self, waitlist_service, mock_session, mock_waitlist_entry):
        """Test expiring waitlist notifications."""
        # Mock configuration
        waitlist_service.consistency_config = {"lock_timeout_seconds": 30}
        
        # Mock expired notified entries
        mock_waitlist_entry.status = WaitlistStatus.NOTIFIED
        mock_waitlist_entry.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_waitlist_entry]
        
        with patch('app.services.waitlist_service.db_manager.get_transaction_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            # Test expire notifications
            expired_count = await waitlist_service.expire_notifications()
            
            # Verify result
            assert expired_count == 1
            
            # Verify database operations
            mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_check_waitlist_eligibility_can_join(self, waitlist_service, mock_session):
        """Test waitlist eligibility check when user can join."""
        # Create a new mock session with proper query chain setup
        session = MagicMock(spec=Session)
        
        # Mock availability query - event is full
        mock_availability = MagicMock()
        mock_availability.available_capacity = 0
        
        # Mock existing entry query - no existing entry
        mock_existing_entry = None
        
        # Mock total waitlist count query
        mock_count = 5
        
        # Set up side effects for different queries
        def mock_query_side_effect(model):
            query_mock = MagicMock()
            filter_mock = MagicMock()
            query_mock.filter.return_value = filter_mock
            
            if model.__name__ == 'EventAvailability':
                filter_mock.first.return_value = mock_availability
            elif model.__name__ == 'WaitlistEntry':
                filter_mock.first.return_value = mock_existing_entry
                filter_mock.count.return_value = mock_count
            
            return query_mock
        
        session.query.side_effect = mock_query_side_effect
        
        with patch('app.services.waitlist_service.db_manager.get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = session
            
            result = await waitlist_service.check_waitlist_eligibility(
                event_id=1,
                user_id=1,
                requested_quantity=2
            )
            
            # Verify result
            assert result["can_join"] is True
            assert result["event_id"] == 1
    
    @pytest.mark.asyncio
    async def test_check_waitlist_eligibility_event_available(self, waitlist_service, mock_session):
        """Test waitlist eligibility check when event has available capacity."""
        # Mock availability - event has capacity
        mock_availability = MagicMock()
        mock_availability.available_capacity = 10
        mock_session.query.return_value.filter.return_value.first.return_value = mock_availability
        
        with patch('app.services.waitlist_service.db_manager.get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            result = await waitlist_service.check_waitlist_eligibility(
                event_id=1,
                user_id=1,
                requested_quantity=2
            )
            
            # Verify result
            assert result["can_join"] is False
            assert result["event_id"] == 1
    
    @pytest.mark.asyncio
    async def test_check_waitlist_eligibility_existing_entry(self, waitlist_service, mock_session, mock_waitlist_entry):
        """Test waitlist eligibility check when user has existing entry."""
        # Mock availability - event is full
        mock_availability = MagicMock()
        mock_availability.available_capacity = 0
        mock_session.query.return_value.filter.return_value.first.return_value = mock_availability
        
        # Mock existing entry
        mock_waitlist_entry.status = WaitlistStatus.PENDING
        mock_session.query.return_value.filter.return_value.first.return_value = mock_waitlist_entry
        
        with patch('app.services.waitlist_service.db_manager.get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            result = await waitlist_service.check_waitlist_eligibility(
                event_id=1,
                user_id=1,
                requested_quantity=2
            )
            
            # Verify result
            assert result["can_join"] is False
            assert result["event_id"] == 1
    
    @pytest.mark.asyncio
    async def test_check_waitlist_eligibility_event_not_found(self, waitlist_service, mock_session):
        """Test waitlist eligibility check when event is not found."""
        # Mock no availability record
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch('app.services.waitlist_service.db_manager.get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            result = await waitlist_service.check_waitlist_eligibility(
                event_id=999,
                user_id=1,
                requested_quantity=2
            )
            
            # Verify result
            assert result["can_join"] is False
            assert result["event_id"] == 999