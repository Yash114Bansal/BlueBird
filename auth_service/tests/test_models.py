"""
Tests for User and UserSession models.
"""

import pytest
from datetime import datetime
from app.models.user import User, UserSession, UserRole


class TestUserModel:
    """Test cases for the User model."""

    def test_user_creation(self):
        """Test creating a user with all required fields."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password_123",
            full_name="Test User"
        )
        
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.hashed_password == "hashed_password_123"
        assert user.full_name == "Test User"
        # Note: Default values are set by SQLAlchemy when saved to database

    def test_user_creation_with_custom_values(self):
        """Test creating a user with custom values."""
        user = User(
            email="admin@example.com",
            username="admin",
            hashed_password="hashed_password_123",
            full_name="Admin User",
            is_active=False,
            is_verified=True,
            role=UserRole.ADMIN
        )
        
        assert user.email == "admin@example.com"
        assert user.username == "admin"
        assert user.full_name == "Admin User"
        assert user.is_active is False
        assert user.is_verified is True
        assert user.role == UserRole.ADMIN

    def test_user_repr(self):
        """Test the string representation of a user."""
        user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password_123"
        )
        
        expected_repr = "<User(id=1, email='test@example.com', username='testuser')>"
        assert repr(user) == expected_repr

    def test_user_to_dict(self):
        """Test converting user to dictionary."""
        now = datetime.utcnow()
        user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password_123",
            full_name="Test User",
            is_active=True,
            is_verified=False,
            role=UserRole.USER,
            created_at=now,
            updated_at=now,
            last_login=None
        )
        
        user_dict = user.to_dict()
        
        assert user_dict["id"] == 1
        assert user_dict["email"] == "test@example.com"
        assert user_dict["username"] == "testuser"
        assert user_dict["full_name"] == "Test User"
        assert user_dict["is_active"] is True
        assert user_dict["is_verified"] is False
        assert user_dict["role"] == "user"
        assert user_dict["created_at"] == now.isoformat()
        assert user_dict["updated_at"] == now.isoformat()
        assert user_dict["last_login"] is None

    def test_user_to_dict_with_last_login(self):
        """Test converting user to dictionary with last_login."""
        now = datetime.utcnow()
        user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password_123",
            full_name="Test User",
            is_active=True,
            is_verified=False,
            role=UserRole.USER,
            last_login=now
        )
        
        user_dict = user.to_dict()
        assert user_dict["last_login"] == now.isoformat()


class TestUserSessionModel:
    """Test cases for the UserSession model."""

    def test_user_session_creation(self):
        """Test creating a user session."""
        session = UserSession(
            user_id=1,
            session_token="session_token_123",
            refresh_token="refresh_token_123",
            expires_at=datetime.utcnow(),
            is_active=True
        )
        
        assert session.user_id == 1
        assert session.session_token == "session_token_123"
        assert session.refresh_token == "refresh_token_123"
        assert session.is_active is True
        # Note: Default values are set by SQLAlchemy when saved to database

    def test_user_session_creation_with_custom_values(self):
        """Test creating a user session with custom values."""
        now = datetime.utcnow()
        session = UserSession(
            user_id=1,
            session_token="session_token_123",
            refresh_token="refresh_token_123",
            expires_at=now,
            is_active=False,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        assert session.user_id == 1
        assert session.session_token == "session_token_123"
        assert session.refresh_token == "refresh_token_123"
        assert session.expires_at == now
        assert session.is_active is False
        assert session.ip_address == "192.168.1.1"
        assert session.user_agent == "Mozilla/5.0"

    def test_user_session_to_dict(self):
        """Test converting user session to dictionary."""
        now = datetime.utcnow()
        session = UserSession(
            id=1,
            user_id=1,
            session_token="session_token_123",
            refresh_token="refresh_token_123",
            expires_at=now,
            is_active=True,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            created_at=now,
            last_accessed=now
        )
        
        session_dict = session.to_dict()
        
        assert session_dict["id"] == 1
        assert session_dict["user_id"] == 1
        assert session_dict["session_token"] == "session_token_123"
        assert session_dict["expires_at"] == now.isoformat()
        assert session_dict["is_active"] is True
        assert session_dict["ip_address"] == "192.168.1.1"
        assert session_dict["user_agent"] == "Mozilla/5.0"
        assert session_dict["created_at"] == now.isoformat()
        assert session_dict["last_accessed"] == now.isoformat()


class TestUserRoleEnum:
    """Test cases for the UserRole enum."""

    def test_user_role_values(self):
        """Test UserRole enum values."""
        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"

    def test_user_role_enumeration(self):
        """Test UserRole enum can be enumerated."""
        roles = list(UserRole)
        assert len(roles) == 2
        assert UserRole.USER in roles
        assert UserRole.ADMIN in roles