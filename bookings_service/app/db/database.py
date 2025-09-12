"""
Database connection and session management for Bookings Service.
Optimized for high consistency and transaction management.
"""

import asyncio
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator
import logging

from app.core.config import config
from app.models.booking import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database manager for high consistency operations.
    Handles connection pooling and transaction management.
    """
    
    def __init__(self):
        self.engine = None
        self.async_engine = None
        self.session_factory = None
        self.async_session_factory = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connections with high consistency settings."""
        if self._initialized:
            return
        
        try:
            # Get database configuration
            db_url = await config.get_database_url()
            db_config = await config.get_database_config()
            
            # Create sync engine with connection pooling
            self.engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=db_config["pool_size"],
                max_overflow=db_config["max_overflow"],
                pool_timeout=db_config["pool_timeout"],
                pool_recycle=db_config["pool_recycle"],
                echo=False,
                future=True
            )
            
            # Create async engine
            async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            self.async_engine = create_async_engine(
                async_db_url,
                pool_size=db_config["pool_size"],
                max_overflow=db_config["max_overflow"],
                pool_timeout=db_config["pool_timeout"],
                pool_recycle=db_config["pool_recycle"],
                echo=False,
                future=True,
                connect_args={
                    "statement_cache_size": 0, 
                    "prepared_statement_cache_size": 0  
                }
            )
            
            # Create session factories
            self.session_factory = sessionmaker(
                bind=self.engine,
                class_=Session,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            self.async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            # Set up event listeners for consistency
            self._setup_event_listeners()
            
            self._initialized = True
            logger.info("Database manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise
    
    def _setup_event_listeners(self):
        """Set up database event listeners for consistency monitoring."""
        
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set database connection parameters for consistency."""
            if "postgresql" in str(dbapi_connection):
                # Set isolation level for consistency
                with dbapi_connection.cursor() as cursor:
                    cursor.execute("SET default_transaction_isolation TO 'read committed'")
                    cursor.execute("SET lock_timeout TO '30s'")
                    cursor.execute("SET statement_timeout TO '60s'")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log connection checkout for monitoring."""
            logger.debug("Database connection checked out")
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log connection checkin for monitoring."""
            logger.debug("Database connection checked in")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic transaction management.
        Ensures proper rollback on exceptions.
        """
        if not self._initialized:
            raise RuntimeError("Database manager not initialized")
        
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session with automatic transaction management.
        Ensures proper rollback on exceptions.
        """
        if not self._initialized:
            raise RuntimeError("Database manager not initialized")
        
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async database session error: {e}")
            raise
        finally:
            await session.close()
    
    @contextmanager
    def get_transaction_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with explicit transaction control.
        For high consistency operations that need manual transaction management.
        """
        if not self._initialized:
            raise RuntimeError("Database manager not initialized")
        
        session = self.session_factory()
        try:
            # Begin transaction
            session.begin()
            yield session
            # Transaction will be committed by caller
        except Exception as e:
            session.rollback()
            logger.error(f"Transaction session error: {e}")
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_transaction_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session with explicit transaction control.
        For high consistency operations that need manual transaction management.
        """
        if not self._initialized:
            raise RuntimeError("Database manager not initialized")
        
        session = self.async_session_factory()
        try:
            # Begin transaction
            await session.begin()
            yield session
            # Transaction will be committed by caller
        except Exception as e:
            await session.rollback()
            logger.error(f"Async transaction session error: {e}")
            raise
        finally:
            await session.close()
    
    async def create_tables(self):
        """Create all database tables."""
        if not self._initialized:
            await self.initialize()
        
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    
    async def drop_tables(self):
        """Drop all database tables (use with caution)."""
        if not self._initialized:
            await self.initialize()
        
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")
    
    async def close(self):
        """Close all database connections."""
        if self.async_engine:
            await self.async_engine.dispose()
        if self.engine:
            self.engine.dispose()
        logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


# Dependency functions for FastAPI
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for getting database session."""
    with db_manager.get_session() as session:
        yield session


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting async database session."""
    async with db_manager.get_async_session() as session:
        yield session


def get_transaction_db() -> Generator[Session, None, None]:
    """FastAPI dependency for getting transaction database session."""
    with db_manager.get_transaction_session() as session:
        yield session


async def get_async_transaction_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting async transaction database session."""
    async with db_manager.get_async_transaction_session() as session:
        yield session