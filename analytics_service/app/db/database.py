"""
Database connection and session management for Analytics Service.
Provides database operations for analytics data.
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
        """Create all database tables."""
        from ..models.analytics import Base
        Base.metadata.create_all(bind=self.engine)
        logger.info("Analytics database tables created successfully")
    
    def close(self):
        """Close database connections."""
        self.engine.dispose()
        logger.info("Database connections closed")


class DatabaseConnection:
    """
    Database connection wrapper for dependency injection.
    Provides singleton access to database manager.
    """
    
    def __init__(self):
        self._manager: Optional[DatabaseManager] = None
    
    def initialize(self, database_url: str):
        """Initialize database connection."""
        if self._manager is None:
            self._manager = DatabaseManager(database_url)
            logger.info("Database connection initialized")
    
    def get_manager(self) -> DatabaseManager:
        """Get database manager instance."""
        if self._manager is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._manager
    
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session."""
        yield from self.get_manager().get_session()
    
    def close(self):
        """Close database connection."""
        if self._manager:
            self._manager.close()
            self._manager = None