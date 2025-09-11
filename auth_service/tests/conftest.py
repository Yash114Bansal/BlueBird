"""
Test configuration and fixtures for the auth service.
"""

import os
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from httpx import AsyncClient
import redis
from unittest.mock import Mock, AsyncMock

# Set test environment variables before importing app
os.environ["ZERO_TOKEN"] = "test_zero_token"
os.environ["JWT_SECRET"] = "test-super-secret-jwt-key-for-testing-only"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRY_MINUTES"] = "30"
os.environ["REFRESH_TOKEN_EXPIRY_DAYS"] = "7"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "test_auth"
os.environ["DB_USER"] = "test_user"
os.environ["DB_PASSWORD"] = "test_password"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["REDIS_PASSWORD"] = ""
os.environ["REDIS_USE_TLS"] = "false"

from app.main import app
from app.db.database import DatabaseManager, UserRepository, UserSessionRepository
from app.models.user import User, UserSession, UserRole, Base
from app.services.password_manager import PasswordManager
from app.services.jwt_manager import JWTManager
from app.services.session_manager import SessionManager
from app.services.user_service import UserService
from app.services.auth_service import AuthenticationService
from app.core.config import AuthConfig


# Test database URL (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Test Redis URL (mock Redis for tests)
TEST_REDIS_URL = "redis://localhost:6379/15"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def mock_redis():
    """Create a mock Redis client."""
    mock_redis = Mock(spec=redis.Redis)
    mock_redis.get = Mock(return_value=None)
    mock_redis.set = Mock(return_value=True)
    mock_redis.delete = Mock(return_value=True)
    mock_redis.exists = Mock(return_value=False)
    mock_redis.expire = Mock(return_value=True)
    return mock_redis


@pytest.fixture(scope="function")
def user_repo(test_db_session) -> UserRepository:
    """Create a user repository for testing."""
    return UserRepository(test_db_session)


@pytest.fixture(scope="function")
def session_repo(test_db_session) -> UserSessionRepository:
    """Create a session repository for testing."""
    return UserSessionRepository(test_db_session)


@pytest.fixture(scope="function")
def password_manager() -> PasswordManager:
    """Create a password manager for testing."""
    return PasswordManager()


@pytest.fixture(scope="function")
def jwt_manager() -> JWTManager:
    """Create a JWT manager for testing."""
    manager = JWTManager()
    manager.secret_key = "test-secret-key-for-testing-only"
    manager.algorithm = "HS256"
    manager.access_token_expire_minutes = 30
    manager.refresh_token_expire_days = 7
    return manager


@pytest.fixture(scope="function")
def session_manager(jwt_manager) -> SessionManager:
    """Create a session manager for testing."""
    return SessionManager(jwt_manager)


@pytest.fixture(scope="function")
def user_service(password_manager) -> UserService:
    """Create a user service for testing."""
    return UserService(password_manager)


@pytest.fixture(scope="function")
def auth_service() -> AuthenticationService:
    """Create an authentication service for testing."""
    return AuthenticationService()


@pytest.fixture(scope="function")
def test_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }


@pytest.fixture(scope="function")
def test_admin_data():
    """Sample admin user data for testing."""
    return {
        "email": "admin@example.com",
        "username": "admin",
        "password": "AdminPassword123!",
        "full_name": "Admin User"
    }


@pytest.fixture(scope="function")
def created_test_user(user_repo, password_manager, test_user_data) -> User:
    """Create a test user in the database."""
    hashed_password = password_manager.hash_password(test_user_data["password"])
    user = user_repo.create(
        email=test_user_data["email"],
        username=test_user_data["username"],
        full_name=test_user_data["full_name"],
        hashed_password=hashed_password,
        role=UserRole.USER
    )
    return user


@pytest.fixture(scope="function")
def created_admin_user(user_repo, password_manager, test_admin_data) -> User:
    """Create a test admin user in the database."""
    hashed_password = password_manager.hash_password(test_admin_data["password"])
    user = user_repo.create(
        email=test_admin_data["email"],
        username=test_admin_data["username"],
        full_name=test_admin_data["full_name"],
        hashed_password=hashed_password,
        role=UserRole.ADMIN,
        is_verified=True
    )
    return user


@pytest.fixture(scope="function")
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
def auth_headers(jwt_manager, created_test_user) -> dict:
    """Create authentication headers for testing."""
    token_data = {
        "sub": str(created_test_user.id),
        "email": created_test_user.email,
        "role": created_test_user.role.value
    }
    access_token = jwt_manager.create_access_token(token_data)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def admin_headers(jwt_manager, created_admin_user) -> dict:
    """Create admin authentication headers for testing."""
    token_data = {
        "sub": str(created_admin_user.id),
        "email": created_admin_user.email,
        "role": created_admin_user.role.value
    }
    access_token = jwt_manager.create_access_token(token_data)
    return {"Authorization": f"Bearer {access_token}"}


# Test settings
@pytest.fixture(scope="function")
def test_settings():
    """Create test settings."""
    return AuthConfig()
