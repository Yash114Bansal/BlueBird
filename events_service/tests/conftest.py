"""
Test configuration and fixtures for Events Service.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api.dependencies import get_database_session
from app.models.event import Base

# Test database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

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
app.dependency_overrides[get_database_session] = override_get_db


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
def sample_event_data():
    """Sample event data for testing."""
    return {
        "title": "Test Event",
        "description": "A test event for unit testing",
        "venue": "Test Venue",
        "event_date": "2024-12-31T18:00:00",
        "capacity": 100,
        "price": 25.00,
        "status": "published"
    }
