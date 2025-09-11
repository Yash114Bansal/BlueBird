"""
Tests for AuthenticationService - the main orchestrator service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.auth_service import AuthenticationService
from app.models.user import User, UserRole
from app.schemas.auth import UserCreate, UserLogin, PasswordChange, TokenData


class TestAuthenticationService:
    """Test cases for the AuthenticationService."""

    @pytest.mark.asyncio
    async def test_auth_service_initialization(self):
        """Test AuthenticationService initialization."""
        auth_service = AuthenticationService()
        
        assert auth_service.password_manager is not None
        assert auth_service.jwt_manager is not None
        assert auth_service.user_service is not None
        assert auth_service.session_manager is not None
        assert auth_service._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_service(self):
        """Test service initialization."""
        auth_service = AuthenticationService()
        
        with patch.object(auth_service.jwt_manager, 'initialize') as mock_init:
            await auth_service.initialize()
            
            assert auth_service._initialized is True
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_service_already_initialized(self):
        """Test service initialization when already initialized."""
        auth_service = AuthenticationService()
        auth_service._initialized = True
        
        with patch.object(auth_service.jwt_manager, 'initialize') as mock_init:
            await auth_service.initialize()
            
            mock_init.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, user_repo, test_user_data):
        """Test successful user registration."""
        user_create = UserCreate(**test_user_data)
        expected_user = User(
            id=1,
            email=test_user_data["email"],
            username=test_user_data["username"],
            full_name=test_user_data["full_name"],
            hashed_password="hashed_password",
            role=UserRole.USER
        )
        
        with patch.object(auth_service.user_service, 'register_user') as mock_register:
            mock_register.return_value = expected_user
            
            result = await auth_service.register_user(user_create, user_repo)
            
            assert result == expected_user
            mock_register.assert_called_once_with(user_create, user_repo)

    @pytest.mark.asyncio
    async def test_register_user_failure(self, auth_service, user_repo, test_user_data):
        """Test user registration failure."""
        user_create = UserCreate(**test_user_data)
        
        with patch.object(auth_service.user_service, 'register_user') as mock_register:
            mock_register.return_value = None
            
            result = await auth_service.register_user(user_create, user_repo)
            
            assert result is None
            mock_register.assert_called_once_with(user_create, user_repo)

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, user_repo, test_user_data):
        """Test successful user authentication."""
        user_login = UserLogin(email=test_user_data["email"], password=test_user_data["password"])
        expected_user = User(
            id=1,
            email=test_user_data["email"],
            username=test_user_data["username"],
            hashed_password="hashed_password",
            role=UserRole.USER
        )
        
        with patch.object(auth_service.user_service, 'authenticate_user') as mock_auth:
            mock_auth.return_value = expected_user
            
            result = await auth_service.authenticate_user(user_login, user_repo)
            
            assert result == expected_user
            mock_auth.assert_called_once_with(user_login, user_repo)

    @pytest.mark.asyncio
    async def test_authenticate_user_failure(self, auth_service, user_repo, test_user_data):
        """Test user authentication failure."""
        user_login = UserLogin(email=test_user_data["email"], password="wrong_password")
        
        with patch.object(auth_service.user_service, 'authenticate_user') as mock_auth:
            mock_auth.return_value = None
            
            result = await auth_service.authenticate_user(user_login, user_repo)
            
            assert result is None
            mock_auth.assert_called_once_with(user_login, user_repo)

    @pytest.mark.asyncio
    async def test_create_user_session_success(self, auth_service, session_repo, created_test_user):
        """Test successful session creation."""
        expected_session = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123",
            "expires_in": 1800
        }
        
        with patch.object(auth_service.session_manager, 'create_user_session') as mock_create:
            mock_create.return_value = expected_session
            
            result = await auth_service.create_user_session(
                created_test_user, session_repo, "192.168.1.1", "Mozilla/5.0"
            )
            
            assert result == expected_session
            mock_create.assert_called_once_with(
                created_test_user, session_repo, "192.168.1.1", "Mozilla/5.0"
            )

    @pytest.mark.asyncio
    async def test_create_user_session_failure(self, auth_service, session_repo, created_test_user):
        """Test session creation failure."""
        with patch.object(auth_service.session_manager, 'create_user_session') as mock_create:
            mock_create.return_value = None
            
            result = await auth_service.create_user_session(
                created_test_user, session_repo, "192.168.1.1", "Mozilla/5.0"
            )
            
            assert result is None
            mock_create.assert_called_once_with(
                created_test_user, session_repo, "192.168.1.1", "Mozilla/5.0"
            )

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, auth_service, session_repo):
        """Test successful token refresh."""
        refresh_token = "valid_refresh_token"
        expected_tokens = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 1800
        }
        
        with patch.object(auth_service.session_manager, 'refresh_access_token') as mock_refresh:
            mock_refresh.return_value = expected_tokens
            
            result = await auth_service.refresh_access_token(refresh_token, session_repo)
            
            assert result == expected_tokens
            mock_refresh.assert_called_once_with(refresh_token, session_repo)

    @pytest.mark.asyncio
    async def test_refresh_access_token_failure(self, auth_service, session_repo):
        """Test token refresh failure."""
        refresh_token = "invalid_refresh_token"
        
        with patch.object(auth_service.session_manager, 'refresh_access_token') as mock_refresh:
            mock_refresh.return_value = None
            
            result = await auth_service.refresh_access_token(refresh_token, session_repo)
            
            assert result is None
            mock_refresh.assert_called_once_with(refresh_token, session_repo)

    @pytest.mark.asyncio
    async def test_logout_user_success(self, auth_service, session_repo):
        """Test successful user logout."""
        access_token = "valid_access_token"
        
        with patch.object(auth_service.session_manager, 'logout_user') as mock_logout:
            mock_logout.return_value = True
            
            result = await auth_service.logout_user(access_token, session_repo)
            
            assert result is True
            mock_logout.assert_called_once_with(access_token, session_repo)

    @pytest.mark.asyncio
    async def test_logout_user_failure(self, auth_service, session_repo):
        """Test user logout failure."""
        access_token = "invalid_access_token"
        
        with patch.object(auth_service.session_manager, 'logout_user') as mock_logout:
            mock_logout.return_value = False
            
            result = await auth_service.logout_user(access_token, session_repo)
            
            assert result is False
            mock_logout.assert_called_once_with(access_token, session_repo)

    @pytest.mark.asyncio
    async def test_change_password_success(self, auth_service, user_repo, created_test_user):
        """Test successful password change."""
        password_data = PasswordChange(
            current_password="TestPassword123!",
            new_password="NewPassword123!"
        )
        
        with patch.object(auth_service.user_service, 'change_password') as mock_change:
            mock_change.return_value = True
            
            result = await auth_service.change_password(
                created_test_user.id, password_data, user_repo
            )
            
            assert result is True
            mock_change.assert_called_once_with(created_test_user.id, password_data, user_repo)

    @pytest.mark.asyncio
    async def test_change_password_failure(self, auth_service, user_repo, created_test_user):
        """Test password change failure."""
        password_data = PasswordChange(
            current_password="WrongPassword123!",
            new_password="NewPassword123!"
        )
        
        with patch.object(auth_service.user_service, 'change_password') as mock_change:
            mock_change.return_value = False
            
            result = await auth_service.change_password(
                created_test_user.id, password_data, user_repo
            )
            
            assert result is False
            mock_change.assert_called_once_with(created_test_user.id, password_data, user_repo)

    @pytest.mark.asyncio
    async def test_update_user_profile_regular_user(self, auth_service, user_repo, created_test_user):
        """Test profile update for regular user."""
        update_data = {
            "email": "newemail@example.com",
            "username": "newusername",
            "full_name": "New Full Name"
        }
        
        with patch.object(auth_service.user_service, 'update_user_profile') as mock_update:
            mock_update.return_value = created_test_user
            
            result = await auth_service.update_user_profile(
                created_test_user.id, update_data, user_repo, is_admin=False
            )
            
            assert result == created_test_user
            mock_update.assert_called_once_with(
                created_test_user.id, update_data, user_repo, False
            )

    @pytest.mark.asyncio
    async def test_update_user_profile_admin(self, auth_service, user_repo, created_test_user):
        """Test profile update for admin user."""
        update_data = {
            "email": "newemail@example.com",
            "username": "newusername",
            "full_name": "New Full Name",
            "is_active": True,
            "is_verified": True,
            "role": "admin"
        }
        
        with patch.object(auth_service.user_service, 'update_user_profile') as mock_update:
            mock_update.return_value = created_test_user
            
            result = await auth_service.update_user_profile(
                created_test_user.id, update_data, user_repo, is_admin=True
            )
            
            assert result == created_test_user
            mock_update.assert_called_once_with(
                created_test_user.id, update_data, user_repo, True
            )

    @pytest.mark.asyncio
    async def test_verify_token_success(self, auth_service):
        """Test successful token verification."""
        token = "valid_access_token"
        expected_token_data = TokenData(user_id=1, email="test@example.com", role="user")
        
        with patch.object(auth_service.jwt_manager, 'verify_token') as mock_verify:
            mock_verify.return_value = expected_token_data
            
            result = await auth_service.verify_token(token)
            
            assert result == expected_token_data
            mock_verify.assert_called_once_with(token, "access")

    @pytest.mark.asyncio
    async def test_verify_token_failure(self, auth_service):
        """Test token verification failure."""
        token = "invalid_access_token"
        
        with patch.object(auth_service.jwt_manager, 'verify_token') as mock_verify:
            mock_verify.return_value = None
            
            result = await auth_service.verify_token(token)
            
            assert result is None
            mock_verify.assert_called_once_with(token, "access")

    @pytest.mark.asyncio
    async def test_get_user_from_token_success(self, auth_service, user_repo, created_test_user):
        """Test getting user from valid token."""
        token = "valid_access_token"
        token_data = TokenData(user_id=created_test_user.id, email=created_test_user.email, role="user")
        
        with patch.object(auth_service, 'verify_token') as mock_verify:
            with patch.object(auth_service.user_service, 'get_user_by_id') as mock_get_user:
                mock_verify.return_value = token_data
                mock_get_user.return_value = created_test_user
                
                result = await auth_service.get_user_from_token(token, user_repo)
                
                assert result == created_test_user
                mock_verify.assert_called_once_with(token)
                mock_get_user.assert_called_once_with(created_test_user.id, user_repo)

    @pytest.mark.asyncio
    async def test_get_user_from_token_invalid_token(self, auth_service, user_repo):
        """Test getting user from invalid token."""
        token = "invalid_access_token"
        
        with patch.object(auth_service, 'verify_token') as mock_verify:
            with patch.object(auth_service.user_service, 'get_user_by_id') as mock_get_user:
                mock_verify.return_value = None
                
                result = await auth_service.get_user_from_token(token, user_repo)
                
                assert result is None
                mock_verify.assert_called_once_with(token)
                mock_get_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_from_token_user_not_found(self, auth_service, user_repo):
        """Test getting user from token when user doesn't exist."""
        token = "valid_access_token"
        token_data = TokenData(user_id=999, email="nonexistent@example.com", role="user")
        
        with patch.object(auth_service, 'verify_token') as mock_verify:
            with patch.object(auth_service.user_service, 'get_user_by_id') as mock_get_user:
                mock_verify.return_value = token_data
                mock_get_user.return_value = None
                
                result = await auth_service.get_user_from_token(token, user_repo)
                
                assert result is None
                mock_verify.assert_called_once_with(token)
                mock_get_user.assert_called_once_with(999, user_repo)

    @pytest.mark.asyncio
    async def test_get_token_expiry(self, auth_service):
        """Test getting token expiry time."""
        expected_expiry = 1800
        
        with patch.object(auth_service.jwt_manager, 'get_token_expiry') as mock_expiry:
            mock_expiry.return_value = expected_expiry
            
            result = await auth_service.get_token_expiry()
            
            assert result == expected_expiry
            mock_expiry.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, auth_service, session_repo):
        """Test cleanup of expired sessions."""
        expected_cleaned = 5
        
        with patch.object(auth_service.session_manager, 'cleanup_expired_sessions') as mock_cleanup:
            mock_cleanup.return_value = expected_cleaned
            
            result = await auth_service.cleanup_expired_sessions(session_repo)
            
            assert result == expected_cleaned
            mock_cleanup.assert_called_once_with(session_repo)

    @pytest.mark.asyncio
    async def test_deactivate_user_sessions(self, auth_service, session_repo, created_test_user):
        """Test deactivating all user sessions."""
        with patch.object(auth_service.session_manager, 'deactivate_user_sessions') as mock_deactivate:
            mock_deactivate.return_value = True
            
            result = await auth_service.deactivate_user_sessions(created_test_user.id, session_repo)
            
            assert result is True
            mock_deactivate.assert_called_once_with(created_test_user.id, session_repo)

    @pytest.mark.asyncio
    async def test_deactivate_user_sessions_failure(self, auth_service, session_repo):
        """Test deactivating user sessions failure."""
        with patch.object(auth_service.session_manager, 'deactivate_user_sessions') as mock_deactivate:
            mock_deactivate.return_value = False
            
            result = await auth_service.deactivate_user_sessions(999, session_repo)
            
            assert result is False
            mock_deactivate.assert_called_once_with(999, session_repo)

    @pytest.mark.asyncio
    async def test_full_authentication_flow(self, auth_service, user_repo, session_repo, test_user_data):
        """Test complete authentication flow: register -> login -> create session."""
        # Step 1: Register user
        user_create = UserCreate(**test_user_data)
        created_user = User(
            id=1,
            email=test_user_data["email"],
            username=test_user_data["username"],
            full_name=test_user_data["full_name"],
            hashed_password="hashed_password",
            role=UserRole.USER
        )
        
        with patch.object(auth_service.user_service, 'register_user') as mock_register:
            with patch.object(auth_service.user_service, 'authenticate_user') as mock_auth:
                with patch.object(auth_service.session_manager, 'create_user_session') as mock_session:
                    # Setup mocks
                    mock_register.return_value = created_user
                    mock_auth.return_value = created_user
                    mock_session.return_value = {
                        "access_token": "access_token_123",
                        "refresh_token": "refresh_token_123",
                        "expires_in": 1800
                    }
                    
                    # Register user
                    register_result = await auth_service.register_user(user_create, user_repo)
                    assert register_result == created_user
                    
                    # Login user
                    user_login = UserLogin(email=test_user_data["email"], password=test_user_data["password"])
                    auth_result = await auth_service.authenticate_user(user_login, user_repo)
                    assert auth_result == created_user
                    
                    # Create session
                    session_result = await auth_service.create_user_session(
                        created_user, session_repo, "192.168.1.1", "Mozilla/5.0"
                    )
                    assert session_result is not None
                    assert "access_token" in session_result
                    assert "refresh_token" in session_result