"""
Database connection and session management for Events Service.
"""

import logging
from typing import Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from ..core.config import config
from ..models.event import Base

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Database connection manager for Events Service.
    Handles connection pooling and session management.
    """
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def initialize(self, database_url: str):
        """
        Initialize database connection.
        
        Args:
            database_url: Database connection URL
        """
        try:
            # Create engine with connection pooling
            self.engine = create_engine(
                database_url,
                poolclass=StaticPool,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            self._initialized = True
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get database session.
        
        Yields:
            SQLAlchemy database session
        """
        if not self._initialized:
            raise RuntimeError("Database not initialized")
        
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def get_manager(self):
        """Get database manager instance."""
        if not self._initialized:
            raise RuntimeError("Database not initialized")
        return self
    
    def create_tables(self):
        """Create all database tables."""
        if not self._initialized:
            raise RuntimeError("Database not initialized")
        
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def health_check(self) -> bool:
        """
        Check database health.
        
        Returns:
            True if database is healthy
        """
        if not self._initialized:
            return False
        
        try:
            session = self.SessionLocal()
            try:
                session.execute(text("SELECT 1"))
                return True
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


class EventRepository:
    """
    Repository for Event model operations.
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, event_data: dict) -> "Event":
        """Create a new event."""
        from ..models.event import Event
        event = Event(**event_data)
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event
    
    def get_by_id(self, event_id: int) -> Optional["Event"]:
        """Get event by ID."""
        from ..models.event import Event
        return self.session.query(Event).filter(Event.id == event_id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100, status: Optional[str] = None) -> list:
        """Get all events with pagination and optional status filter."""
        from ..models.event import Event
        query = self.session.query(Event)
        
        if status:
            query = query.filter(Event.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    def get_upcoming_events(self, skip: int = 0, limit: int = 100) -> list:
        """Get upcoming published events."""
        from ..models.event import Event, EventStatus
        from datetime import datetime
        
        return self.session.query(Event).filter(
            Event.status == EventStatus.PUBLISHED,
            Event.event_date > datetime.utcnow()
        ).order_by(Event.event_date).offset(skip).limit(limit).all()
    
    def update(self, event_id: int, event_data: dict) -> Optional["Event"]:
        """Update an event."""
        from ..models.event import Event
        event = self.get_by_id(event_id)
        if event:
            for key, value in event_data.items():
                if hasattr(event, key):
                    setattr(event, key, value)
            self.session.commit()
            self.session.refresh(event)
        return event
    
    def delete(self, event_id: int) -> bool:
        """Delete an event."""
        from ..models.event import Event
        event = self.get_by_id(event_id)
        if event:
            self.session.delete(event)
            self.session.commit()
            return True
        return False
    
    def count(self, status: Optional[str] = None) -> int:
        """Count events with optional status filter."""
        from ..models.event import Event
        query = self.session.query(Event)
        
        if status:
            query = query.filter(Event.status == status)
        
        return query.count()

