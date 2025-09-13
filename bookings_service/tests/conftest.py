"""
Test configuration and fixtures for Bookings Service.
Focuses on high consistency testing scenarios.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.main import app
from app.db.database import get_db, db_manager
from app.models.booking import Base, Booking, BookingItem, EventAvailability, BookingStatus, PaymentStatus
from app.services.booking_service import BookingService
from app.services.availability_service import AvailabilityService

# Test database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_bookings.db"

# Create test engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create test session
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def client():
    """Create test client."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Drop tables after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Create a database session for testing."""
    # Create tables before each test
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop tables after each test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_event_availability():
    """Sample event availability data for testing."""
    return {
        "event_id": 1,
        "total_capacity": 100,
        "available_capacity": 100,
        "reserved_capacity": 0,
        "confirmed_capacity": 0,
        "version": 1
    }


@pytest.fixture
def sample_booking_data():
    """Sample booking data for testing."""
    return {
        "event_id": 1,
        "quantity": 2,
        "notes": "Test booking"
    }


@pytest.fixture
def mock_redis_manager():
    """Mock Redis manager for testing."""
    mock_redis = AsyncMock()
    mock_redis.initialize = AsyncMock()
    mock_redis.get_json = AsyncMock(return_value=None)
    mock_redis.set_json = AsyncMock()
    mock_redis.delete = AsyncMock()
    mock_redis.delete_pattern = AsyncMock()
    return mock_redis


@pytest.fixture
def mock_distributed_lock():
    """Mock distributed lock for testing."""
    mock_lock = AsyncMock()
    mock_lock.__aenter__ = AsyncMock(return_value=mock_lock)
    mock_lock.__aexit__ = AsyncMock(return_value=None)
    return mock_lock


@pytest.fixture(scope="function")
def initialized_db_manager():
    """Mock the global database manager for testing."""
    from unittest.mock import patch, MagicMock
    from contextlib import contextmanager
    
    # Mock the database manager methods
    mock_db_manager = MagicMock()
    mock_db_manager._initialized = True
    
    # Create a proper context manager for transaction sessions
    @contextmanager
    def mock_get_transaction_session():
        session = TestingSessionLocal()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def mock_get_session():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    mock_db_manager.get_transaction_session = mock_get_transaction_session
    mock_db_manager.get_session = mock_get_session
    
    # Patch the global db_manager in both the database module and the booking service
    with patch('app.db.database.db_manager', mock_db_manager), \
         patch('app.services.booking_service.db_manager', mock_db_manager):
        yield mock_db_manager


@pytest.fixture
def booking_service(initialized_db_manager):
    """Create booking service instance for testing."""
    return BookingService()


@pytest.fixture
def availability_service(initialized_db_manager):
    """Create availability service instance for testing."""
    return AvailabilityService()


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token for testing."""
    return {
        "user_id": 1,
        "email": "test@example.com",
        "role": "user"
    }


@pytest.fixture
def mock_admin_token():
    """Mock admin JWT token for testing."""
    return {
        "user_id": 1,
        "email": "admin@example.com",
        "role": "admin"
    }


@pytest.fixture
def high_consistency_config():
    """High consistency configuration for testing."""
    return {
        "lock_timeout_seconds": 30,
        "max_retry_attempts": 3,
        "retry_delay_ms": 100,
        "enable_distributed_locks": True,
        "enable_optimistic_locking": True,
        "transaction_timeout_seconds": 60
    }


@pytest.fixture
def booking_config():
    """Booking configuration for testing."""
    return {
        "max_booking_quantity": 10,
        "booking_hold_duration_minutes": 15,
        "enable_booking_validation": True,
        "enable_capacity_checks": True,
        "enable_duplicate_prevention": True
    }