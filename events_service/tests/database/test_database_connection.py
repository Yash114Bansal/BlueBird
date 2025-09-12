"""
Tests for DatabaseConnection functionality.
"""

import pytest
from unittest.mock import MagicMock

from app.db.database import DatabaseConnection


class TestDatabaseConnection:
    """Test cases for DatabaseConnection."""
    
    def test_database_connection_initialization(self):
        """Test database connection initialization."""
        db_connection = DatabaseConnection()
        
        assert db_connection is not None
        assert hasattr(db_connection, 'engine')
        assert hasattr(db_connection, 'SessionLocal')
    
    def test_database_health_check(self):
        """Test database health check."""
        db_connection = DatabaseConnection()
        
        # This should not raise an exception
        result = db_connection.health_check()
        
        # The actual implementation might return different values
        assert result is not None
    
    def test_get_session_generator(self):
        """Test getting database session generator."""
        db_connection = DatabaseConnection()
        
        # Initialize the database first
        db_connection.initialize("sqlite:///:memory:")
        
        # Get the generator
        session_gen = db_connection.get_session()
        
        # This should be a generator
        assert session_gen is not None
        
        # Test that we can get a session from the generator
        session = next(session_gen)
        assert session is not None
        
        # Clean up
        try:
            next(session_gen)
        except StopIteration:
            pass  # Expected when generator is exhausted
    
    def test_get_session_without_initialization(self):
        """Test getting session without proper initialization."""
        db_connection = DatabaseConnection()
        
        # Don't initialize the database
        with pytest.raises(RuntimeError) as exc_info:
            session_gen = db_connection.get_session()
            next(session_gen)
        
        assert "Database not initialized" in str(exc_info.value)