"""
Pydantic schemas for Event-related operations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..models.event import EventStatus


class EventStatusEnum(str, Enum):
    """Event status enumeration for API."""
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class EventBase(BaseModel):
    """Base event schema."""
    title: str = Field(..., min_length=1, max_length=255, description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    venue: str = Field(..., min_length=1, max_length=255, description="Event venue")
    event_date: datetime = Field(..., description="Event date and time")
    capacity: int = Field(..., gt=0, description="Event capacity")
    price: Decimal = Field(..., ge=0, description="Event price per ticket")
    status: EventStatusEnum = Field(EventStatusEnum.DRAFT, description="Event status")


class EventCreate(EventBase):
    """Schema for creating a new event."""
    pass


class EventUpdate(BaseModel):
    """Schema for updating an event."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    venue: Optional[str] = Field(None, min_length=1, max_length=255)
    event_date: Optional[datetime] = None
    capacity: Optional[int] = Field(None, gt=0)
    price: Optional[Decimal] = Field(None, ge=0)
    status: Optional[EventStatusEnum] = None


class EventResponse(EventBase):
    """Schema for event response."""
    id: int
    is_upcoming: bool
    created_at: datetime
    updated_at: datetime
    created_by: int

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """Schema for event list response."""
    events: List[EventResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool
    

class MessageResponse(BaseModel):
    """Generic message response schema."""
    message: str
    success: bool = True


class EventStatsResponse(BaseModel):
    """Schema for event statistics response."""
    total_events: int
    published_events: int
    total_bookings: int
    total_revenue: Decimal
    most_popular_event: Optional[EventResponse] = None