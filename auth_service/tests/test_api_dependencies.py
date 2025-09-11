"""
Unit tests for API dependencies.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_database_session,
    get_user_repository,
    get_session_repository,
    get_auth_service,
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    get_optional_current_user,
    get_client_ip,
    get_user_agent,
    RateLimitDependency,
    security
)
from app.db.database import UserRepository, UserSessionRepository
from app.services.auth_service import AuthenticationService
from app.models.user import User, UserRole


class TestDatabaseDependencies:
    """Test database-related dependencies."""

    def test_get_database_session(self):
        """Test getting database session dependency."""
        with patch('app.api.dependencies.db_connection') as mock_connection:
            mock_session = Mock(spec=Session)
            mock_connection.get_session.return_value = iter([mock_session])
            
            session_gen = get_database_session()
            session = next(session_gen)
            
            assert session == mock_session
            mock_connection.get_session.assert_called_once()

    def test_get_user_repository(self):
        """Test getting user repository dependency."""
        mock_session = Mock(spec=Session)
        
        with patch('app.api.dependencies.get_database_session', return_value=iter([mock_session])):
            repo = get_user_repository(session=mock_session)
            
            assert isinstance(repo, UserRepository)
            assert repo.session == mock_session

    def test_get_session_repository(self):
        """Test getting session repository dependency."""
        mock_session = Mock(spec=Session)
        
        with patch('app.api.dependencies.get_database_session', return_value=iter([mock_session])):
            repo = get_session_repository(session=mock_session)
            
            assert isinstance(repo, UserSessionRepository)
            assert repo.session == mock_session


class TestAuthServiceDependency:
    """Test authentication service dependency."""

    @pytest.mark.asyncio
    async def test_get_auth_service_initialized(self):
        """Test getting initialized auth service."""
        mock_service = Mock(spec=AuthenticationService)
        mock_service._initialized = True
        
        with patch('app.api.dependencies.auth_service', mock_service):
            service = await get_auth_service()
            
            assert service == mock_service

    @pytest.mark.asyncio
    async def test_get_auth_service_not_initialized(self):
        """Test getting uninitialized auth service."""
        mock_service = Mock(spec=AuthenticationService)
        mock_service._initialized = False
        mock_service.initialize = AsyncMock()
        
        with patch('app.api.dependencies.auth_service', mock_service):
            service = await get_auth_service()
            
            assert service == mock_service
            mock_service.initialize.assert_called_once()


class TestUserDependencies:
    """Test user-related dependencies."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """Test getting current user with valid token."""
        mock_user = Mock(spec=User)
        mock_user.is_active = True
        
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "valid_token"
        
        mock_auth_service = Mock(spec=AuthenticationService)
        mock_auth_service.get_user_from_token = AsyncMock(return_value=mock_user)
        
        mock_user_repo = Mock(spec=UserRepository)
        
        user = await get_current_user(
            credentials=mock_credentials,
            auth_service=mock_auth_service,
            user_repo=mock_user_repo
        )
        
        assert user == mock_user
        mock_auth_service.get_user_from_token.assert_called_once_with("valid_token", mock_user_repo)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "invalid_token"
        
        mock_auth_service = Mock(spec=AuthenticationService)
        mock_auth_service.get_user_from_token = AsyncMock(return_value=None)
        
        mock_user_repo = Mock(spec=UserRepository)
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                credentials=mock_credentials,
                auth_service=mock_auth_service,
                user_repo=mock_user_repo
            )
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_inactive(self):
        """Test getting current user with inactive user."""
        mock_user = Mock(spec=User)
        mock_user.is_active = False
        
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "valid_token"
        
        mock_auth_service = Mock(spec=AuthenticationService)
        mock_auth_service.get_user_from_token = AsyncMock(return_value=mock_user)
        
        mock_user_repo = Mock(spec=UserRepository)
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                credentials=mock_credentials,
                auth_service=mock_auth_service,
                user_repo=mock_user_repo
            )
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_exception(self):
        """Test getting current user with exception."""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "token"
        
        mock_auth_service = Mock(spec=AuthenticationService)
        mock_auth_service.get_user_from_token = AsyncMock(side_effect=Exception("Token error"))
        
        mock_user_repo = Mock(spec=UserRepository)
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                credentials=mock_credentials,
                auth_service=mock_auth_service,
                user_repo=mock_user_repo
            )
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_active_user_success(self):
        """Test getting current active user."""
        mock_user = Mock(spec=User)
        mock_user.is_active = True
        
        user = await get_current_active_user(current_user=mock_user)
        assert user == mock_user

    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(self):
        """Test getting current active user with inactive user."""
        mock_user = Mock(spec=User)
        mock_user.is_active = False
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(current_user=mock_user)
        
        assert exc_info.value.status_code == 400
        assert "Inactive user" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_admin_user_success(self):
        """Test getting current admin user."""
        mock_user = Mock(spec=User)
        mock_user.role = Mock()
        mock_user.role.value = "admin"
        
        user = await get_current_admin_user(current_user=mock_user)
        assert user == mock_user

    @pytest.mark.asyncio
    async def test_get_current_admin_user_not_admin(self):
        """Test getting current admin user with non-admin user."""
        mock_user = Mock(spec=User)
        mock_user.role = Mock()
        mock_user.role.value = "user"
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(current_user=mock_user)
        
        assert exc_info.value.status_code == 403
        assert "Not enough permissions" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_optional_current_user_with_token(self):
        """Test getting optional current user with valid token."""
        mock_user = Mock(spec=User)
        mock_user.is_active = True
        
        mock_request = Mock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer valid_token"}
        
        mock_auth_service = Mock(spec=AuthenticationService)
        mock_auth_service.get_user_from_token = AsyncMock(return_value=mock_user)
        
        mock_user_repo = Mock(spec=UserRepository)
        
        user = await get_optional_current_user(
            request=mock_request,
            auth_service=mock_auth_service,
            user_repo=mock_user_repo
        )
        
        assert user == mock_user

    @pytest.mark.asyncio
    async def test_get_optional_current_user_no_token(self):
        """Test getting optional current user without token."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        
        mock_auth_service = Mock(spec=AuthenticationService)
        mock_user_repo = Mock(spec=UserRepository)
        
        user = await get_optional_current_user(
            request=mock_request,
            auth_service=mock_auth_service,
            user_repo=mock_user_repo
        )
        
        assert user is None

    @pytest.mark.asyncio
    async def test_get_optional_current_user_invalid_token(self):
        """Test getting optional current user with invalid token."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer invalid_token"}
        
        mock_auth_service = Mock(spec=AuthenticationService)
        mock_auth_service.get_user_from_token = AsyncMock(side_effect=Exception("Invalid token"))
        
        mock_user_repo = Mock(spec=UserRepository)
        
        user = await get_optional_current_user(
            request=mock_request,
            auth_service=mock_auth_service,
            user_repo=mock_user_repo
        )
        
        assert user is None

    @pytest.mark.asyncio
    async def test_get_optional_current_user_inactive(self):
        """Test getting optional current user with inactive user."""
        mock_user = Mock(spec=User)
        mock_user.is_active = False
        
        mock_request = Mock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer valid_token"}
        
        mock_auth_service = Mock(spec=AuthenticationService)
        mock_auth_service.get_user_from_token = AsyncMock(return_value=mock_user)
        
        mock_user_repo = Mock(spec=UserRepository)
        
        user = await get_optional_current_user(
            request=mock_request,
            auth_service=mock_auth_service,
            user_repo=mock_user_repo
        )
        
        assert user is None


class TestRequestDependencies:
    """Test request-related dependencies."""

    def test_get_client_ip_direct_connection(self):
        """Test getting client IP from direct connection."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.1"
        
        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_x_forwarded_for(self):
        """Test getting client IP from X-Forwarded-For header."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-Forwarded-For": "203.0.113.1, 70.41.3.18, 150.172.238.178"}
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.1"
        
        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.1"

    def test_get_client_ip_x_real_ip(self):
        """Test getting client IP from X-Real-IP header."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-Real-IP": "203.0.113.1"}
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.1"
        
        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.1"

    def test_get_client_ip_no_client(self):
        """Test getting client IP when no client info available."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        mock_request.client = None
        
        ip = get_client_ip(mock_request)
        assert ip == "unknown"

    def test_get_user_agent(self):
        """Test getting user agent from request."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        user_agent = get_user_agent(mock_request)
        assert user_agent == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def test_get_user_agent_missing(self):
        """Test getting user agent when header is missing."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        
        user_agent = get_user_agent(mock_request)
        assert user_agent == "unknown"


class TestRateLimitDependency:
    """Test rate limiting dependency."""

    @pytest.mark.asyncio
    async def test_rate_limit_allowed(self):
        """Test rate limit allowing request."""
        rate_limit = RateLimitDependency(limit=5, window_seconds=900)
        mock_request = Mock(spec=Request)
        
        result = await rate_limit(mock_request)
        assert result is True

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test rate limit exceeding (placeholder implementation)."""
        # Note: Current implementation always returns True
        # This test documents the expected behavior when rate limiting is implemented
        rate_limit = RateLimitDependency(limit=1, window_seconds=60)
        mock_request = Mock(spec=Request)
        
        result = await rate_limit(mock_request)
        assert result is True  # Current implementation always allows


class TestSecurityScheme:
    """Test security scheme."""

    def test_security_scheme_creation(self):
        """Test HTTPBearer security scheme creation."""
        assert security is not None
        assert hasattr(security, 'scheme_name')
        assert security.scheme_name == "HTTPBearer"