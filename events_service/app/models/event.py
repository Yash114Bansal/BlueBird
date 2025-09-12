"""
Event model for Events Service.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Numeric
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class EventStatus(str, Enum):
    """Event status enumeration."""
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Event(Base):
    """
    Event model representing an event in the system.
    """
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    venue = Column(String(255), nullable=False)
    event_date = Column(DateTime, nullable=False, index=True)
    capacity = Column(Integer, nullable=False, default=0)
    price = Column(Numeric(10, 2), nullable=False, default=0.00)
    status = Column(String(20), nullable=False, default=EventStatus.DRAFT, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now(), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now(), nullable=False)
    created_by = Column(Integer, nullable=False)
        
    def __repr__(self):
        return f"<Event(id={self.id}, title='{self.title}', venue='{self.venue}')>"
    
    
    @property
    def is_upcoming(self) -> bool:
        """Check if the event is upcoming."""
        return self.event_date > datetime.now() and self.status == EventStatus.PUBLISHED

