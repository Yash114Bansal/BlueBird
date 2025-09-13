"""
Concise Analytics models optimized for fast queries.
Event-driven data aggregation for analytics dashboard.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, Index, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime, date
from typing import Dict, Any

Base = declarative_base()


class EventStats(Base):
    """
    Concise event statistics - one row per event.
    Optimized for quick event performance queries.
    """
    
    __tablename__ = "event_stats"
    
    event_id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(200), nullable=False, index=True)
    category = Column(String(50), nullable=True, index=True)
    
    # Key metrics
    total_capacity = Column(Integer, default=0, nullable=False)
    total_bookings = Column(Integer, default=0, nullable=False)
    confirmed_bookings = Column(Integer, default=0, nullable=False)
    cancelled_bookings = Column(Integer, default=0, nullable=False)
    capacity_utilization = Column(Float, default=0.0, nullable=False)
    total_revenue = Column(Float, default=0.0, nullable=False)
    
    # Performance metrics
    cancellation_rate = Column(Float, default=0.0, nullable=False)
    avg_booking_value = Column(Float, default=0.0, nullable=False)
    
    # Time tracking
    first_booking = Column(DateTime(timezone=True), nullable=True)
    last_booking = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "category": self.category,
            "total_capacity": self.total_capacity,
            "total_bookings": self.total_bookings,
            "confirmed_bookings": self.confirmed_bookings,
            "cancelled_bookings": self.cancelled_bookings,
            "capacity_utilization": round(self.capacity_utilization, 2),
            "total_revenue": round(self.total_revenue, 2),
            "cancellation_rate": round(self.cancellation_rate, 2),
            "avg_booking_value": round(self.avg_booking_value, 2),
            "first_booking": self.first_booking.isoformat() if self.first_booking else None,
            "last_booking": self.last_booking.isoformat() if self.last_booking else None,
            "updated_at": self.updated_at.isoformat()
        }


class DailyStats(Base):
    """
    Daily aggregated statistics - one row per day.
    Optimized for time-series analytics.
    """
    
    __tablename__ = "daily_stats"
    
    date = Column(Date, primary_key=True, index=True)
    
    # Daily metrics
    total_bookings = Column(Integer, default=0, nullable=False)
    new_bookings = Column(Integer, default=0, nullable=False)
    cancelled_bookings = Column(Integer, default=0, nullable=False)
    confirmed_bookings = Column(Integer, default=0, nullable=False)
    
    # Daily aggregates
    total_revenue = Column(Float, default=0.0, nullable=False)
    avg_booking_value = Column(Float, default=0.0, nullable=False)
    active_events = Column(Integer, default=0, nullable=False)
    new_users = Column(Integer, default=0, nullable=False)
    
    # Performance
    system_uptime = Column(Float, default=100.0, nullable=False)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "total_bookings": self.total_bookings,
            "new_bookings": self.new_bookings,
            "cancelled_bookings": self.cancelled_bookings,
            "confirmed_bookings": self.confirmed_bookings,
            "total_revenue": round(self.total_revenue, 2),
            "avg_booking_value": round(self.avg_booking_value, 2),
            "active_events": self.active_events,
            "new_users": self.new_users,
            "system_uptime": round(self.system_uptime, 2),
            "updated_at": self.updated_at.isoformat()
        }


class TopEvents(Base):
    """
    Pre-computed top events for quick dashboard display.
    Updated via events, optimized for leaderboard queries.
    """
    
    __tablename__ = "top_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=False, unique=True, index=True)
    event_name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=True)
    
    # Ranking metrics
    total_bookings = Column(Integer, default=0, nullable=False)
    total_revenue = Column(Float, default=0.0, nullable=False)
    capacity_utilization = Column(Float, default=0.0, nullable=False)
    
    # Rankings (computed)
    booking_rank = Column(Integer, nullable=True, index=True)
    revenue_rank = Column(Integer, nullable=True, index=True)
    utilization_rank = Column(Integer, nullable=True, index=True)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "category": self.category,
            "total_bookings": self.total_bookings,
            "total_revenue": round(self.total_revenue, 2),
            "capacity_utilization": round(self.capacity_utilization, 2),
            "booking_rank": self.booking_rank,
            "revenue_rank": self.revenue_rank,
            "utilization_rank": self.utilization_rank,
            "updated_at": self.updated_at.isoformat()
        }


class SystemMetrics(Base):
    """
    System-wide metrics for dashboard overview.
    Single row with current system state.
    """
    
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, default=1)
    
    # System totals
    total_events = Column(Integer, default=0, nullable=False)
    total_bookings = Column(Integer, default=0, nullable=False)
    total_users = Column(Integer, default=0, nullable=False)
    total_revenue = Column(Float, default=0.0, nullable=False)
    
    # Current period (last 30 days)
    recent_bookings = Column(Integer, default=0, nullable=False)
    recent_revenue = Column(Float, default=0.0, nullable=False)
    recent_events = Column(Integer, default=0, nullable=False)
    
    # Performance metrics
    avg_capacity_utilization = Column(Float, default=0.0, nullable=False)
    avg_cancellation_rate = Column(Float, default=0.0, nullable=False)
    system_uptime = Column(Float, default=100.0, nullable=False)
    
    # Growth metrics
    booking_growth_rate = Column(Float, default=0.0, nullable=False)
    revenue_growth_rate = Column(Float, default=0.0, nullable=False)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_events": self.total_events,
            "total_bookings": self.total_bookings,
            "total_users": self.total_users,
            "total_revenue": round(self.total_revenue, 2),
            "recent_bookings": self.recent_bookings,
            "recent_revenue": round(self.recent_revenue, 2),
            "recent_events": self.recent_events,
            "avg_capacity_utilization": round(self.avg_capacity_utilization, 2),
            "avg_cancellation_rate": round(self.avg_cancellation_rate, 2),
            "system_uptime": round(self.system_uptime, 2),
            "booking_growth_rate": round(self.booking_growth_rate, 2),
            "revenue_growth_rate": round(self.revenue_growth_rate, 2),
            "updated_at": self.updated_at.isoformat()
        }


class EventLog(Base):
    """
    Event log for debugging and audit trail.
    Stores all events received by analytics service.
    """
    
    __tablename__ = "event_log"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # BookingCreated, EventCreated, etc.
    event_id = Column(Integer, nullable=True, index=True)
    event_data = Column(Text, nullable=False)  # JSON payload
    processed = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "event_id": self.event_id,
            "event_data": self.event_data,
            "processed": self.processed,
            "created_at": self.created_at.isoformat()
        }