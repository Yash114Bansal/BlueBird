"""
Database connection and session management for Auth Service.
Provides database operations for user authentication.
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator, Optional
import logging

logger = logging.getLogger(__name__)

# Metadata for schema management
metadata = MetaData()


class DatabaseManager:
    """
    Database connection manager following SOLID principles.
    Handles connection pooling and session management.
    """
    
    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 20):
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
            echo=False
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session.
        
        Yields:
            SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_tables(self):
        """Create all tables in the database."""
        from ..models.user import Base
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all tables in the database."""
        from ..models.user import Base
        Base.metadata.drop_all(bind=self.engine)


class BaseRepository:
    """
    Base repository class following Repository pattern.
    Provides common CRUD operations for all entities.
    """
    
    def __init__(self, session: Session, model_class):
        self.session = session
        self.model_class = model_class
    
    def create(self, **kwargs):
        """Create a new entity."""
        entity = self.model_class(**kwargs)
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity
    
    def get_by_id(self, entity_id: int):
        """Get entity by ID."""
        return self.session.query(self.model_class).filter(
            self.model_class.id == entity_id
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100):
        """Get all entities with pagination."""
        return self.session.query(self.model_class).offset(skip).limit(limit).all()
    
    def update(self, entity_id: int, **kwargs):
        """Update entity by ID."""
        entity = self.get_by_id(entity_id)
        if entity:
            for key, value in kwargs.items():
                setattr(entity, key, value)
            self.session.commit()
            self.session.refresh(entity)
        return entity
    
    def delete(self, entity_id: int):
        """Delete entity by ID."""
        entity = self.get_by_id(entity_id)
        if entity:
            self.session.delete(entity)
            self.session.commit()
            return True
        return False
    
    def count(self):
        """Count total entities."""
        return self.session.query(self.model_class).count()


class UserRepository(BaseRepository):
    """
    User repository for user-related database operations.
    Extends base repository with user-specific methods.
    """
    
    def __init__(self, session: Session):
        from ..models.user import User
        super().__init__(session, User)
    
    def get_by_email(self, email: str):
        """Get user by email address."""
        return self.session.query(self.model_class).filter(
            self.model_class.email == email
        ).first()
    
    def get_by_username(self, username: str):
        """Get user by username."""
        return self.session.query(self.model_class).filter(
            self.model_class.username == username
        ).first()
    
    def get_active_users(self, skip: int = 0, limit: int = 100):
        """Get all active users."""
        return self.session.query(self.model_class).filter(
            self.model_class.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_users_by_role(self, role: str, skip: int = 0, limit: int = 100):
        """Get users by role."""
        return self.session.query(self.model_class).filter(
            self.model_class.role == role
        ).offset(skip).limit(limit).all()
    
    def update_last_login(self, user_id: int):
        """Update user's last login timestamp."""
        from datetime import datetime
        return self.update(user_id, last_login=datetime.utcnow())


class UserSessionRepository(BaseRepository):
    """
    User session repository for session-related database operations.
    Handles session management and tracking.
    """
    
    def __init__(self, session: Session):
        from ..models.user import UserSession
        super().__init__(session, UserSession)
    
    def get_by_token(self, token: str):
        """Get session by token."""
        return self.session.query(self.model_class).filter(
            self.model_class.session_token == token
        ).first()
    
    def get_by_refresh_token(self, refresh_token: str):
        """Get session by refresh token."""
        return self.session.query(self.model_class).filter(
            self.model_class.refresh_token == refresh_token
        ).first()
    
    def get_user_sessions(self, user_id: int):
        """Get all sessions for a user."""
        return self.session.query(self.model_class).filter(
            self.model_class.user_id == user_id,
            self.model_class.is_active == True
        ).all()
    
    def deactivate_user_sessions(self, user_id: int):
        """Deactivate all sessions for a user."""
        sessions = self.get_user_sessions(user_id)
        for session in sessions:
            session.is_active = False
        self.session.commit()
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        from datetime import datetime
        expired_sessions = self.session.query(self.model_class).filter(
            self.model_class.expires_at < datetime.utcnow()
        ).all()
        
        for session in expired_sessions:
            self.session.delete(session)
        
        self.session.commit()
        return len(expired_sessions)


class DatabaseConnection:
    """
    Singleton database connection manager.
    Ensures single connection per service instance.
    """
    
    _instance: Optional['DatabaseConnection'] = None
    _database_manager: Optional[DatabaseManager] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, database_url: str):
        """Initialize database connection."""
        if self._database_manager is None:
            self._database_manager = DatabaseManager(database_url)
            logger.info("Database connection initialized")
    
    def get_manager(self) -> DatabaseManager:
        """Get database manager instance."""
        if self._database_manager is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._database_manager
    
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session."""
        return self.get_manager().get_session()