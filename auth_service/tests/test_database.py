"""
Tests for database repositories and connection management.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.database import (
    DatabaseManager, 
    BaseRepository, 
    UserRepository, 
    UserSessionRepository,
    DatabaseConnection
)
from app.models.user import User, UserSession, UserRole


class TestDatabaseManager:
    """Test cases for DatabaseManager."""

    def test_database_manager_initialization(self):
        """Test DatabaseManager initialization."""
        database_url = "sqlite:///:memory:"
        db_manager = DatabaseManager(database_url)
        
        assert db_manager.database_url == database_url
        assert db_manager.engine is not None
        assert db_manager.SessionLocal is not None

    def test_database_manager_with_custom_pool_size(self):
        """Test DatabaseManager with custom pool settings."""
        database_url = "sqlite:///:memory:"
        db_manager = DatabaseManager(database_url, pool_size=5, max_overflow=10)
        
        assert db_manager.database_url == database_url
        assert db_manager.engine is not None

    def test_get_session(self):
        """Test getting database session."""
        database_url = "sqlite:///:memory:"
        db_manager = DatabaseManager(database_url)
        
        session_gen = db_manager.get_session()
        session = next(session_gen)
        
        assert isinstance(session, Session)
        
        # Clean up
        try:
            next(session_gen)
        except StopIteration:
            pass

    def test_create_tables(self):
        """Test creating database tables."""
        database_url = "sqlite:///:memory:"
        db_manager = DatabaseManager(database_url)
        
        # Should not raise an exception
        db_manager.create_tables()

    def test_drop_tables(self):
        """Test dropping database tables."""
        database_url = "sqlite:///:memory:"
        db_manager = DatabaseManager(database_url)
        
        # Should not raise an exception
        db_manager.drop_tables()


class TestBaseRepository:
    """Test cases for BaseRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def base_repo(self, mock_session):
        """Create a BaseRepository instance."""
        return BaseRepository(mock_session, User)

    def test_base_repository_initialization(self, base_repo, mock_session):
        """Test BaseRepository initialization."""
        assert base_repo.session == mock_session
        assert base_repo.model_class == User

    def test_create_entity(self, base_repo, mock_session):
        """Test creating a new entity."""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "hashed_password": "hashed_password",
            "full_name": "Test User"
        }
        
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None
        
        result = base_repo.create(**user_data)
        
        # Verify the result is a User instance with correct data
        assert isinstance(result, User)
        assert result.email == user_data["email"]
        assert result.username == user_data["username"]
        assert result.hashed_password == user_data["hashed_password"]
        assert result.full_name == user_data["full_name"]
        
        # Verify session methods were called
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    def test_get_by_id(self, base_repo, mock_session):
        """Test getting entity by ID."""
        mock_user = User(id=1, email="test@example.com")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_session.query.return_value = mock_query
        
        result = base_repo.get_by_id(1)
        
        assert result == mock_user
        mock_session.query.assert_called_once_with(User)
        mock_query.filter.assert_called_once()

    def test_get_all_with_pagination(self, base_repo, mock_session):
        """Test getting all entities with pagination."""
        mock_users = [User(id=1), User(id=2)]
        mock_query = Mock()
        mock_offset = Mock()
        mock_limit = Mock()
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = mock_users
        mock_query.offset.return_value = mock_offset
        mock_session.query.return_value = mock_query
        
        result = base_repo.get_all(skip=10, limit=20)
        
        assert result == mock_users
        mock_session.query.assert_called_once_with(User)
        mock_query.offset.assert_called_once_with(10)
        mock_offset.limit.assert_called_once_with(20)

    def test_update_entity(self, base_repo, mock_session):
        """Test updating an entity."""
        mock_user = User(id=1, email="old@example.com")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_session.query.return_value = mock_query
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None
        
        result = base_repo.update(1, email="new@example.com", username="newuser")
        
        assert result == mock_user
        assert mock_user.email == "new@example.com"
        assert mock_user.username == "newuser"
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_user)

    def test_update_entity_not_found(self, base_repo, mock_session):
        """Test updating non-existent entity."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query
        
        result = base_repo.update(999, email="new@example.com")
        
        assert result is None
        mock_session.commit.assert_not_called()

    def test_delete_entity(self, base_repo, mock_session):
        """Test deleting an entity."""
        mock_user = User(id=1, email="test@example.com")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_session.query.return_value = mock_query
        mock_session.delete.return_value = None
        mock_session.commit.return_value = None
        
        result = base_repo.delete(1)
        
        assert result is True
        mock_session.delete.assert_called_once_with(mock_user)
        mock_session.commit.assert_called_once()

    def test_delete_entity_not_found(self, base_repo, mock_session):
        """Test deleting non-existent entity."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query
        
        result = base_repo.delete(999)
        
        assert result is False
        mock_session.delete.assert_not_called()

    def test_count_entities(self, base_repo, mock_session):
        """Test counting entities."""
        mock_query = Mock()
        mock_query.count.return_value = 5
        mock_session.query.return_value = mock_query
        
        result = base_repo.count()
        
        assert result == 5
        mock_session.query.assert_called_once_with(User)
        mock_query.count.assert_called_once()


class TestUserRepository:
    """Test cases for UserRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def user_repo(self, mock_session):
        """Create a UserRepository instance."""
        return UserRepository(mock_session)

    def test_user_repository_initialization(self, user_repo, mock_session):
        """Test UserRepository initialization."""
        assert user_repo.session == mock_session
        assert user_repo.model_class == User

    def test_get_by_email(self, user_repo, mock_session):
        """Test getting user by email."""
        mock_user = User(id=1, email="test@example.com")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_session.query.return_value = mock_query
        
        result = user_repo.get_by_email("test@example.com")
        
        assert result == mock_user
        mock_session.query.assert_called_once_with(User)
        mock_query.filter.assert_called_once()

    def test_get_by_username(self, user_repo, mock_session):
        """Test getting user by username."""
        mock_user = User(id=1, username="testuser")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_session.query.return_value = mock_query
        
        result = user_repo.get_by_username("testuser")
        
        assert result == mock_user
        mock_session.query.assert_called_once_with(User)
        mock_query.filter.assert_called_once()

    def test_get_active_users(self, user_repo, mock_session):
        """Test getting active users."""
        mock_users = [User(id=1, is_active=True), User(id=2, is_active=True)]
        mock_query = Mock()
        mock_filter = Mock()
        mock_offset = Mock()
        mock_limit = Mock()
        mock_filter.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = mock_users
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        result = user_repo.get_active_users(skip=0, limit=10)
        
        assert result == mock_users
        mock_session.query.assert_called_once_with(User)
        mock_query.filter.assert_called_once()
        mock_filter.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(10)

    def test_get_users_by_role(self, user_repo, mock_session):
        """Test getting users by role."""
        mock_users = [User(id=1, role=UserRole.ADMIN), User(id=2, role=UserRole.ADMIN)]
        mock_query = Mock()
        mock_filter = Mock()
        mock_offset = Mock()
        mock_limit = Mock()
        mock_filter.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = mock_users
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        result = user_repo.get_users_by_role("admin", skip=0, limit=10)
        
        assert result == mock_users
        mock_session.query.assert_called_once_with(User)
        mock_query.filter.assert_called_once()
        mock_filter.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(10)

    def test_update_last_login(self, user_repo, mock_session):
        """Test updating last login timestamp."""
        mock_user = User(id=1, email="test@example.com")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_session.query.return_value = mock_query
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None
        
        with patch('datetime.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            
            result = user_repo.update_last_login(1)
            
            assert result == mock_user
            assert mock_user.last_login == mock_now
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once_with(mock_user)


class TestUserSessionRepository:
    """Test cases for UserSessionRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def session_repo(self, mock_session):
        """Create a UserSessionRepository instance."""
        return UserSessionRepository(mock_session)

    def test_session_repository_initialization(self, session_repo, mock_session):
        """Test UserSessionRepository initialization."""
        assert session_repo.session == mock_session
        assert session_repo.model_class == UserSession

    def test_get_by_token(self, session_repo, mock_session):
        """Test getting session by token."""
        mock_session_obj = UserSession(id=1, session_token="token123")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_session_obj
        mock_session.query.return_value = mock_query
        
        result = session_repo.get_by_token("token123")
        
        assert result == mock_session_obj
        mock_session.query.assert_called_once_with(UserSession)
        mock_query.filter.assert_called_once()

    def test_get_by_refresh_token(self, session_repo, mock_session):
        """Test getting session by refresh token."""
        mock_session_obj = UserSession(id=1, refresh_token="refresh123")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_session_obj
        mock_session.query.return_value = mock_query
        
        result = session_repo.get_by_refresh_token("refresh123")
        
        assert result == mock_session_obj
        mock_session.query.assert_called_once_with(UserSession)
        mock_query.filter.assert_called_once()

    def test_get_user_sessions(self, session_repo, mock_session):
        """Test getting all sessions for a user."""
        mock_sessions = [
            UserSession(id=1, user_id=1, is_active=True),
            UserSession(id=2, user_id=1, is_active=True)
        ]
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = mock_sessions
        mock_session.query.return_value = mock_query
        
        result = session_repo.get_user_sessions(1)
        
        assert result == mock_sessions
        mock_session.query.assert_called_once_with(UserSession)
        mock_query.filter.assert_called_once()

    def test_deactivate_user_sessions(self, session_repo, mock_session):
        """Test deactivating all user sessions."""
        mock_sessions = [
            UserSession(id=1, user_id=1, is_active=True),
            UserSession(id=2, user_id=1, is_active=True)
        ]
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = mock_sessions
        mock_session.query.return_value = mock_query
        mock_session.commit.return_value = None
        
        session_repo.deactivate_user_sessions(1)
        
        assert mock_sessions[0].is_active is False
        assert mock_sessions[1].is_active is False
        mock_session.commit.assert_called_once()

    def test_cleanup_expired_sessions(self, session_repo, mock_session):
        """Test cleaning up expired sessions."""
        expired_time = datetime.utcnow() - timedelta(hours=1)
        mock_expired_sessions = [
            UserSession(id=1, expires_at=expired_time),
            UserSession(id=2, expires_at=expired_time)
        ]
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = mock_expired_sessions
        mock_session.query.return_value = mock_query
        mock_session.delete.return_value = None
        mock_session.commit.return_value = None
        
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.utcnow()
            
            result = session_repo.cleanup_expired_sessions()
            
            assert result == 2
            assert mock_session.delete.call_count == 2
            mock_session.commit.assert_called_once()


class TestDatabaseConnection:
    """Test cases for DatabaseConnection singleton."""

    def test_singleton_pattern(self):
        """Test that DatabaseConnection follows singleton pattern."""
        # Reset singleton state
        DatabaseConnection._instance = None
        DatabaseConnection._database_manager = None
        
        conn1 = DatabaseConnection()
        conn2 = DatabaseConnection()
        
        assert conn1 is conn2
        assert id(conn1) == id(conn2)

    def test_initialize_database(self):
        """Test database initialization."""
        # Reset singleton state
        DatabaseConnection._instance = None
        DatabaseConnection._database_manager = None
        
        conn = DatabaseConnection()
        database_url = "sqlite:///:memory:"
        
        with patch('app.db.database.DatabaseManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            conn.initialize(database_url)
            
            assert conn._database_manager == mock_manager
            mock_manager_class.assert_called_once_with(database_url)

    def test_get_manager_before_initialization(self):
        """Test getting manager before initialization raises error."""
        # Reset singleton state
        DatabaseConnection._instance = None
        DatabaseConnection._database_manager = None
        
        conn = DatabaseConnection()
        
        with pytest.raises(RuntimeError, match="Database not initialized"):
            conn.get_manager()

    def test_get_manager_after_initialization(self):
        """Test getting manager after initialization."""
        # Reset singleton state
        DatabaseConnection._instance = None
        DatabaseConnection._database_manager = None
        
        conn = DatabaseConnection()
        database_url = "sqlite:///:memory:"
        
        with patch('app.db.database.DatabaseManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            conn.initialize(database_url)
            result = conn.get_manager()
            
            assert result == mock_manager

    def test_get_session(self):
        """Test getting database session."""
        # Reset singleton state
        DatabaseConnection._instance = None
        DatabaseConnection._database_manager = None
        
        conn = DatabaseConnection()
        database_url = "sqlite:///:memory:"
        
        with patch('app.db.database.DatabaseManager') as mock_manager_class:
            mock_manager = Mock()
            mock_session_gen = iter([Mock()])
            mock_manager.get_session.return_value = mock_session_gen
            mock_manager_class.return_value = mock_manager
            
            conn.initialize(database_url)
            session_gen = conn.get_session()
            
            assert session_gen == mock_session_gen
            mock_manager.get_session.assert_called_once()