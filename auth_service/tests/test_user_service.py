"""
Tests for UserService with security fix validation.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.user_service import UserService
from app.models.user import User, UserRole
from app.schemas.auth import UserCreate, UserLogin, PasswordChange


class TestUserService:
    """Test cases for the UserService with security validation."""

    def test_user_service_initialization(self, password_manager):
        """Test UserService initialization."""
        user_service = UserService(password_manager)
        assert user_service.password_manager == password_manager

    @pytest.mark.asyncio
    async def test_register_user_success(self, user_service, user_repo, test_user_data):
        """Test successful user registration."""
        # Mock repository methods
        user_repo.get_by_email = Mock(return_value=None)
        user_repo.get_by_username = Mock(return_value=None)
        user_repo.create = Mock(return_value=User(
            id=1,
            email=test_user_data["email"],
            username=test_user_data["username"],
            full_name=test_user_data["full_name"],
            hashed_password="hashed_password",
            role=UserRole.USER
        ))
        
        user_create = UserCreate(**test_user_data)
        result = await user_service.register_user(user_create, user_repo)
        
        assert result is not None
        assert result.email == test_user_data["email"]
        assert result.username == test_user_data["username"]
        assert result.role == UserRole.USER
        user_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_email_exists(self, user_service, user_repo, test_user_data):
        """Test user registration with existing email."""
        # Mock repository to return existing user
        user_repo.get_by_email = Mock(return_value=User(id=1, email=test_user_data["email"]))
        user_repo.create = Mock()
        
        user_create = UserCreate(**test_user_data)
        result = await user_service.register_user(user_create, user_repo)
        
        assert result is None
        user_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_user_username_exists(self, user_service, user_repo, test_user_data):
        """Test user registration with existing username."""
        # Mock repository methods
        user_repo.get_by_email = Mock(return_value=None)
        user_repo.get_by_username = Mock(return_value=User(id=1, username=test_user_data["username"]))
        user_repo.create = Mock()
        
        user_create = UserCreate(**test_user_data)
        result = await user_service.register_user(user_create, user_repo)
        
        assert result is None
        user_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, user_service, user_repo, test_user_data):
        """Test successful user authentication."""
        # Create a mock user
        mock_user = User(
            id=1,
            email=test_user_data["email"],
            username=test_user_data["username"],
            hashed_password="hashed_password",
            is_active=True
        )
        
        user_repo.get_by_email = Mock(return_value=mock_user)
        user_repo.update_last_login = Mock(return_value=mock_user)
        
        # Mock password verification
        with patch.object(user_service.password_manager, 'verify_password') as mock_verify:
            mock_verify.return_value = True
            
            user_login = UserLogin(email=test_user_data["email"], password=test_user_data["password"])
            result = await user_service.authenticate_user(user_login, user_repo)
            
            assert result is not None
            assert result.email == test_user_data["email"]
            user_repo.update_last_login.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, user_service, user_repo, test_user_data):
        """Test authentication with non-existent user."""
        user_repo.get_by_email = Mock(return_value=None)
        
        user_login = UserLogin(email=test_user_data["email"], password=test_user_data["password"])
        result = await user_service.authenticate_user(user_login, user_repo)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, user_service, user_repo, test_user_data):
        """Test authentication with inactive user."""
        mock_user = User(
            id=1,
            email=test_user_data["email"],
            username=test_user_data["username"],
            hashed_password="hashed_password",
            is_active=False
        )
        
        user_repo.get_by_email = Mock(return_value=mock_user)
        
        user_login = UserLogin(email=test_user_data["email"], password=test_user_data["password"])
        result = await user_service.authenticate_user(user_login, user_repo)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, user_service, user_repo, test_user_data):
        """Test authentication with wrong password."""
        mock_user = User(
            id=1,
            email=test_user_data["email"],
            username=test_user_data["username"],
            hashed_password="hashed_password",
            is_active=True
        )
        
        user_repo.get_by_email = Mock(return_value=mock_user)
        
        # Mock password verification to return False
        with patch.object(user_service.password_manager, 'verify_password') as mock_verify:
            mock_verify.return_value = False
            
            user_login = UserLogin(email=test_user_data["email"], password="wrong_password")
            result = await user_service.authenticate_user(user_login, user_repo)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_change_password_success(self, user_service, user_repo, created_test_user):
        """Test successful password change."""
        password_data = PasswordChange(
            current_password="TestPassword123!",
            new_password="NewPassword123!"
        )
        
        # Mock password verification and hashing
        with patch.object(user_service.password_manager, 'verify_password') as mock_verify:
            with patch.object(user_service.password_manager, 'hash_password') as mock_hash:
                mock_verify.return_value = True
                mock_hash.return_value = "new_hashed_password"
                
                user_repo.update = Mock(return_value=created_test_user)
                
                result = await user_service.change_password(created_test_user.id, password_data, user_repo)
                
                assert result is True
                user_repo.update.assert_called_once_with(
                    created_test_user.id, 
                    hashed_password="new_hashed_password"
                )

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, user_service, user_repo, created_test_user):
        """Test password change with wrong current password."""
        password_data = PasswordChange(
            current_password="WrongPassword123!",
            new_password="NewPassword123!"
        )
        
        # Mock password verification to return False
        with patch.object(user_service.password_manager, 'verify_password') as mock_verify:
            mock_verify.return_value = False
            
            result = await user_service.change_password(created_test_user.id, password_data, user_repo)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_update_user_profile_regular_user_success(self, user_service, user_repo, created_test_user):
        """Test successful profile update for regular user."""
        update_data = {
            "email": "newemail@example.com",
            "username": "newusername",
            "full_name": "New Full Name"
        }
        
        # Mock repository methods
        user_repo.get_by_email = Mock(return_value=None)
        user_repo.get_by_username = Mock(return_value=None)
        user_repo.update = Mock(return_value=created_test_user)
        
        result = await user_service.update_user_profile(
            created_test_user.id, update_data, user_repo, is_admin=False
        )
        
        assert result is not None
        user_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_profile_regular_user_filters_sensitive_fields(self, user_service, user_repo, created_test_user):
        """Test that regular users cannot update sensitive fields."""
        update_data = {
            "email": "newemail@example.com",
            "username": "newusername",
            "full_name": "New Full Name",
            "is_active": True,      # Should be filtered out
            "is_verified": True,    # Should be filtered out
            "role": "admin"         # Should be filtered out
        }
        
        # Mock repository methods
        user_repo.get_by_email = Mock(return_value=None)
        user_repo.get_by_username = Mock(return_value=None)
        user_repo.update = Mock(return_value=created_test_user)
        
        result = await user_service.update_user_profile(
            created_test_user.id, update_data, user_repo, is_admin=False
        )
        
        assert result is not None
        
        # Verify that sensitive fields were filtered out
        call_args = user_repo.update.call_args[1]
        assert "is_active" not in call_args
        assert "is_verified" not in call_args
        assert "role" not in call_args
        assert "email" in call_args
        assert "username" in call_args
        assert "full_name" in call_args

    @pytest.mark.asyncio
    async def test_update_user_profile_admin_can_update_sensitive_fields(self, user_service, user_repo, created_test_user):
        """Test that admin users can update sensitive fields."""
        update_data = {
            "email": "newemail@example.com",
            "username": "newusername",
            "full_name": "New Full Name",
            "is_active": True,
            "is_verified": True,
            "role": "admin"
        }
        
        # Mock repository methods
        user_repo.get_by_email = Mock(return_value=None)
        user_repo.get_by_username = Mock(return_value=None)
        user_repo.update = Mock(return_value=created_test_user)
        
        result = await user_service.update_user_profile(
            created_test_user.id, update_data, user_repo, is_admin=True
        )
        
        assert result is not None
        
        # Verify that sensitive fields were NOT filtered out for admin
        call_args = user_repo.update.call_args[1]
        assert "is_active" in call_args
        assert "is_verified" in call_args
        assert "role" in call_args
        assert call_args["is_active"] is True
        assert call_args["is_verified"] is True
        assert call_args["role"] == "admin"

    @pytest.mark.asyncio
    async def test_update_user_profile_email_exists(self, user_service, user_repo, created_test_user):
        """Test profile update with existing email."""
        update_data = {
            "email": "existing@example.com"
        }
        
        # Mock repository to return existing user with different ID
        existing_user = User(id=999, email="existing@example.com")
        user_repo.get_by_email = Mock(return_value=existing_user)
        user_repo.update = Mock()
        
        result = await user_service.update_user_profile(
            created_test_user.id, update_data, user_repo, is_admin=False
        )
        
        assert result is None
        user_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_profile_username_exists(self, user_service, user_repo, created_test_user):
        """Test profile update with existing username."""
        update_data = {
            "username": "existinguser"
        }
        
        # Mock repository to return existing user with different ID
        existing_user = User(id=999, username="existinguser")
        user_repo.get_by_username = Mock(return_value=existing_user)
        user_repo.update = Mock()
        
        result = await user_service.update_user_profile(
            created_test_user.id, update_data, user_repo, is_admin=False
        )
        
        assert result is None
        user_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_profile_same_user_email(self, user_service, user_repo, created_test_user):
        """Test profile update with same user's email (should be allowed)."""
        update_data = {
            "email": created_test_user.email  # Same email
        }
        
        # Mock repository to return the same user
        user_repo.get_by_email = Mock(return_value=created_test_user)
        user_repo.update = Mock(return_value=created_test_user)
        
        result = await user_service.update_user_profile(
            created_test_user.id, update_data, user_repo, is_admin=False
        )
        
        assert result is not None
        user_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, user_service, user_repo, created_test_user):
        """Test successful user deactivation."""
        user_repo.update = Mock(return_value=created_test_user)
        
        result = await user_service.deactivate_user(created_test_user.id, user_repo)
        
        assert result is True
        user_repo.update.assert_called_once_with(created_test_user.id, is_active=False)

    @pytest.mark.asyncio
    async def test_deactivate_user_failure(self, user_service, user_repo):
        """Test user deactivation failure."""
        user_repo.update = Mock(return_value=None)
        
        result = await user_service.deactivate_user(999, user_repo)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_service, user_repo, created_test_user):
        """Test getting user by ID."""
        user_repo.get_by_id = Mock(return_value=created_test_user)
        
        result = await user_service.get_user_by_id(created_test_user.id, user_repo)
        
        assert result is not None
        assert result.id == created_test_user.id

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_service, user_repo, created_test_user):
        """Test getting user by email."""
        user_repo.get_by_email = Mock(return_value=created_test_user)
        
        result = await user_service.get_user_by_email(created_test_user.email, user_repo)
        
        assert result is not None
        assert result.email == created_test_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, user_service, user_repo, created_test_user):
        """Test getting user by username."""
        user_repo.get_by_username = Mock(return_value=created_test_user)
        
        result = await user_service.get_user_by_username(created_test_user.username, user_repo)
        
        assert result is not None
        assert result.username == created_test_user.username