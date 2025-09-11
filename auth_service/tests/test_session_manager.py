"""
Tests for SessionManager service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from app.services.session_manager import SessionManager
from app.models.user import User, UserSession, UserRole


class TestSessionManager:
    """Test cases for the SessionManager service."""

    def test_session_manager_initialization(self, session_manager, jwt_manager):
        """Test SessionManager initialization."""
        assert session_manager.jwt_manager == jwt_manager

    @pytest.mark.asyncio
    async def test_create_user_session_success(self, session_manager, session_repo, created_test_user):
        """Test successful session creation."""
        # Mock JWT manager to return tokens
        mock_tokens = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123"
        }
        session_manager.jwt_manager.create_token_pair = Mock(return_value=mock_tokens)
        session_manager.jwt_manager.refresh_token_expire_days = 7
        
        # Mock session repository
        mock_session = UserSession(
            id=1,
            user_id=created_test_user.id,
            session_token=mock_tokens["access_token"],
            refresh_token=mock_tokens["refresh_token"],
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        session_repo.create = Mock(return_value=mock_session)
        
        result = await session_manager.create_user_session(
            created_test_user, session_repo, "192.168.1.1", "Mozilla/5.0"
        )
        
        assert result == mock_session
        session_repo.create.assert_called_once()
        session_manager.jwt_manager.create_token_pair.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_session_failure(self, session_manager, session_repo, created_test_user):
        """Test session creation failure."""
        # Mock JWT manager to raise exception
        session_manager.jwt_manager.create_token_pair = Mock(side_effect=Exception("JWT error"))
        session_repo.create = Mock()
        
        result = await session_manager.create_user_session(
            created_test_user, session_repo, "192.168.1.1", "Mozilla/5.0"
        )
        
        assert result is None
        session_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, session_manager, session_repo):
        """Test successful token refresh."""
        refresh_token = "valid_refresh_token"
        
        # Mock JWT manager
        token_data = Mock()
        token_data.user_id = 1
        token_data.email = "test@example.com"
        token_data.role = "user"
        session_manager.jwt_manager.verify_token = Mock(return_value=token_data)
        session_manager.jwt_manager.create_token_pair = Mock(return_value={
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token"
        })
        
        # Mock session repository
        mock_session = UserSession(
            id=1,
            user_id=1,
            session_token="old_access_token",
            refresh_token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=1),
            is_active=True
        )
        session_repo.get_by_refresh_token = Mock(return_value=mock_session)
        session_repo.session.commit = Mock()
        
        result = await session_manager.refresh_access_token(refresh_token, session_repo)
        
        assert result is not None
        assert "access_token" in result
        assert "refresh_token" in result
        session_repo.get_by_refresh_token.assert_called_once_with(refresh_token)
        session_repo.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid_token(self, session_manager, session_repo):
        """Test token refresh with invalid token."""
        refresh_token = "invalid_refresh_token"
        
        # Mock JWT manager to return None
        session_manager.jwt_manager.verify_token = Mock(return_value=None)
        session_repo.get_by_refresh_token = Mock()
        
        result = await session_manager.refresh_access_token(refresh_token, session_repo)
        
        assert result is None
        session_repo.get_by_refresh_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_access_token_session_not_found(self, session_manager, session_repo):
        """Test token refresh when session not found."""
        refresh_token = "valid_refresh_token"
        
        # Mock JWT manager
        token_data = Mock()
        token_data.user_id = 1
        token_data.email = "test@example.com"
        token_data.role = "user"
        session_manager.jwt_manager.verify_token = Mock(return_value=token_data)
        
        # Mock session repository to return None
        session_repo.get_by_refresh_token = Mock(return_value=None)
        
        result = await session_manager.refresh_access_token(refresh_token, session_repo)
        
        assert result is None
        session_repo.get_by_refresh_token.assert_called_once_with(refresh_token)

    @pytest.mark.asyncio
    async def test_refresh_access_token_expired_session(self, session_manager, session_repo):
        """Test token refresh with expired session."""
        refresh_token = "valid_refresh_token"
        
        # Mock JWT manager
        token_data = Mock()
        token_data.user_id = 1
        token_data.email = "test@example.com"
        token_data.role = "user"
        session_manager.jwt_manager.verify_token = Mock(return_value=token_data)
        
        # Mock expired session
        mock_session = UserSession(
            id=1,
            user_id=1,
            session_token="old_access_token",
            refresh_token=refresh_token,
            expires_at=datetime.utcnow() - timedelta(days=1),  # Expired
            is_active=True
        )
        session_repo.get_by_refresh_token = Mock(return_value=mock_session)
        session_repo.session.commit = Mock()
        
        result = await session_manager.refresh_access_token(refresh_token, session_repo)
        
        assert result is None
        assert mock_session.is_active is False
        session_repo.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_user_success(self, session_manager, session_repo):
        """Test successful user logout."""
        access_token = "valid_access_token"
        
        # Mock session repository
        mock_session = UserSession(
            id=1,
            user_id=1,
            session_token=access_token,
            is_active=True
        )
        session_repo.get_by_token = Mock(return_value=mock_session)
        session_repo.session.commit = Mock()
        
        result = await session_manager.logout_user(access_token, session_repo)
        
        assert result is True
        assert mock_session.is_active is False
        session_repo.get_by_token.assert_called_once_with(access_token)
        session_repo.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_user_session_not_found(self, session_manager, session_repo):
        """Test logout when session not found."""
        access_token = "invalid_access_token"
        
        # Mock session repository to return None
        session_repo.get_by_token = Mock(return_value=None)
        session_repo.session.commit = Mock()
        
        result = await session_manager.logout_user(access_token, session_repo)
        
        assert result is False
        session_repo.get_by_token.assert_called_once_with(access_token)
        session_repo.session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_logout_user_exception(self, session_manager, session_repo):
        """Test logout with exception."""
        access_token = "valid_access_token"
        
        # Mock session repository to raise exception
        session_repo.get_by_token = Mock(side_effect=Exception("Database error"))
        
        result = await session_manager.logout_user(access_token, session_repo)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_success(self, session_manager, session_repo):
        """Test successful session cleanup."""
        session_repo.cleanup_expired_sessions = Mock(return_value=5)
        
        result = await session_manager.cleanup_expired_sessions(session_repo)
        
        assert result == 5
        session_repo.cleanup_expired_sessions.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_exception(self, session_manager, session_repo):
        """Test session cleanup with exception."""
        session_repo.cleanup_expired_sessions = Mock(side_effect=Exception("Database error"))
        
        result = await session_manager.cleanup_expired_sessions(session_repo)
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_deactivate_user_sessions_success(self, session_manager, session_repo):
        """Test successful user session deactivation."""
        user_id = 1
        session_repo.deactivate_user_sessions = Mock()
        
        result = await session_manager.deactivate_user_sessions(user_id, session_repo)
        
        assert result is True
        session_repo.deactivate_user_sessions.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_deactivate_user_sessions_exception(self, session_manager, session_repo):
        """Test user session deactivation with exception."""
        user_id = 1
        session_repo.deactivate_user_sessions = Mock(side_effect=Exception("Database error"))
        
        result = await session_manager.deactivate_user_sessions(user_id, session_repo)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_create_user_session_with_optional_params(self, session_manager, session_repo, created_test_user):
        """Test session creation without optional parameters."""
        # Mock JWT manager to return tokens
        mock_tokens = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123"
        }
        session_manager.jwt_manager.create_token_pair = Mock(return_value=mock_tokens)
        session_manager.jwt_manager.refresh_token_expire_days = 7
        
        # Mock session repository
        mock_session = UserSession(
            id=1,
            user_id=created_test_user.id,
            session_token=mock_tokens["access_token"],
            refresh_token=mock_tokens["refresh_token"],
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        session_repo.create = Mock(return_value=mock_session)
        
        result = await session_manager.create_user_session(created_test_user, session_repo)
        
        assert result == mock_session
        session_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_access_token_inactive_session(self, session_manager, session_repo):
        """Test token refresh with inactive session."""
        refresh_token = "valid_refresh_token"
        
        # Mock JWT manager
        token_data = Mock()
        token_data.user_id = 1
        token_data.email = "test@example.com"
        token_data.role = "user"
        session_manager.jwt_manager.verify_token = Mock(return_value=token_data)
        
        # Mock inactive session
        mock_session = UserSession(
            id=1,
            user_id=1,
            session_token="old_access_token",
            refresh_token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=1),
            is_active=False  # Inactive
        )
        session_repo.get_by_refresh_token = Mock(return_value=mock_session)
        
        result = await session_manager.refresh_access_token(refresh_token, session_repo)
        
        assert result is None
        session_repo.get_by_refresh_token.assert_called_once_with(refresh_token)

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, session_manager, session_repo, created_test_user):
        """Test complete session lifecycle: create -> refresh -> logout."""
        # Step 1: Create session
        mock_tokens = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123"
        }
        session_manager.jwt_manager.create_token_pair = Mock(return_value=mock_tokens)
        session_manager.jwt_manager.refresh_token_expire_days = 7
        
        mock_session = UserSession(
            id=1,
            user_id=created_test_user.id,
            session_token=mock_tokens["access_token"],
            refresh_token=mock_tokens["refresh_token"],
            expires_at=datetime.utcnow() + timedelta(days=7),
            is_active=True
        )
        session_repo.create = Mock(return_value=mock_session)
        session_repo.get_by_refresh_token = Mock(return_value=mock_session)
        session_repo.get_by_token = Mock(return_value=mock_session)
        session_repo.session.commit = Mock()
        
        # Create session
        created_session = await session_manager.create_user_session(created_test_user, session_repo)
        assert created_session == mock_session
        
        # Step 2: Refresh token
        token_data = Mock()
        token_data.user_id = created_test_user.id
        token_data.email = created_test_user.email
        token_data.role = created_test_user.role.value
        session_manager.jwt_manager.verify_token = Mock(return_value=token_data)
        
        new_tokens = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token"
        }
        session_manager.jwt_manager.create_token_pair = Mock(return_value=new_tokens)
        
        refreshed_tokens = await session_manager.refresh_access_token(mock_tokens["refresh_token"], session_repo)
        assert refreshed_tokens == new_tokens
        
        # Step 3: Logout
        logout_result = await session_manager.logout_user(mock_tokens["access_token"], session_repo)
        assert logout_result is True
        assert mock_session.is_active is False