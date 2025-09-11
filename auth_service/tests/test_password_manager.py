"""
Tests for PasswordManager service.
"""

import pytest
from app.services.password_manager import PasswordManager


class TestPasswordManager:
    """Test cases for the PasswordManager service."""

    def test_password_manager_initialization(self):
        """Test PasswordManager initialization."""
        password_manager = PasswordManager()
        assert password_manager is not None
        assert password_manager.pwd_context is not None

    def test_hash_password(self):
        """Test password hashing."""
        password_manager = PasswordManager()
        password = "TestPassword123!"
        
        hashed = password_manager.hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash format

    def test_hash_password_different_hashes(self):
        """Test that the same password produces different hashes."""
        password_manager = PasswordManager()
        password = "TestPassword123!"
        
        hash1 = password_manager.hash_password(password)
        hash2 = password_manager.hash_password(password)
        
        # bcrypt should produce different hashes due to salt
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password_manager = PasswordManager()
        password = "TestPassword123!"
        hashed = password_manager.hash_password(password)
        
        result = password_manager.verify_password(password, hashed)
        
        assert result is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password_manager = PasswordManager()
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = password_manager.hash_password(password)
        
        result = password_manager.verify_password(wrong_password, hashed)
        
        assert result is False

    def test_verify_password_empty_password(self):
        """Test password verification with empty password."""
        password_manager = PasswordManager()
        password = "TestPassword123!"
        hashed = password_manager.hash_password(password)
        
        result = password_manager.verify_password("", hashed)
        
        assert result is False

    def test_verify_password_none_password(self):
        """Test password verification with None password."""
        password_manager = PasswordManager()
        password = "TestPassword123!"
        hashed = password_manager.hash_password(password)
        
        with pytest.raises(TypeError):
            password_manager.verify_password(None, hashed)

    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash."""
        password_manager = PasswordManager()
        password = "TestPassword123!"
        invalid_hash = "invalid_hash"
        
        with pytest.raises(Exception):  # passlib.exc.UnknownHashError
            password_manager.verify_password(password, invalid_hash)

    def test_hash_password_empty_string(self):
        """Test hashing empty password."""
        password_manager = PasswordManager()
        password = ""
        
        hashed = password_manager.hash_password(password)
        
        assert hashed is not None
        assert hashed != password

    def test_hash_password_none(self):
        """Test hashing None password."""
        password_manager = PasswordManager()
        
        with pytest.raises((TypeError, AttributeError)):
            password_manager.hash_password(None)

    def test_verify_password_special_characters(self):
        """Test password verification with special characters."""
        password_manager = PasswordManager()
        password = "Test@Password#123$%^&*()"
        hashed = password_manager.hash_password(password)
        
        result = password_manager.verify_password(password, hashed)
        
        assert result is True

    def test_verify_password_unicode(self):
        """Test password verification with unicode characters."""
        password_manager = PasswordManager()
        password = "TestPassword123!🚀"
        hashed = password_manager.hash_password(password)
        
        result = password_manager.verify_password(password, hashed)
        
        assert result is True

    def test_verify_password_very_long_password(self):
        """Test password verification with very long password."""
        password_manager = PasswordManager()
        password = "A" * 1000  # Very long password
        hashed = password_manager.hash_password(password)
        
        result = password_manager.verify_password(password, hashed)
        
        assert result is True

    def test_hash_password_consistency(self):
        """Test that hash_password always returns a string."""
        password_manager = PasswordManager()
        passwords = [
            "TestPassword123!",
            "simple",
            "123456",
            "!@#$%^&*()",
            "password with spaces",
            "PASSWORD",
            "password"
        ]
        
        for password in passwords:
            hashed = password_manager.hash_password(password)
            assert isinstance(hashed, str)
            assert len(hashed) > 0
            assert hashed != password