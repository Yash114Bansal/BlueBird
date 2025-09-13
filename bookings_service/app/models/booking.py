"""
Booking models for Bookings Service.
Implements high consistency booking management with availability tracking.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum, Numeric, 
    ForeignKey, Index, CheckConstraint, UniqueConstraint, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

Base = declarative_base()


class BookingStatus(PyEnum):
    """Booking status enumeration."""
    PENDING = "pending"           # Booking created, payment pending
    CONFIRMED = "confirmed"       # Payment successful, booking confirmed
    CANCELLED = "cancelled"       # Booking cancelled by user
    EXPIRED = "expired"           # Booking expired due to timeout
    REFUNDED = "refunded"         # Booking refunded
    COMPLETED = "completed"       # Event completed


class PaymentStatus(PyEnum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Booking(Base):
    """
    Booking model for managing event bookings with high consistency.
    Includes optimistic locking and audit trail.
    """
    
    __tablename__ = "bookings"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id = Column(Integer, nullable=False, index=True)  # References auth service
    event_id = Column(Integer, nullable=False, index=True)  # References events service
    
    # Booking details
    booking_reference = Column(String(50), unique=True, index=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    
    # Status tracking
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False, index=True)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    
    # Timing
    booking_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # For pending bookings
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Payment information
    payment_method = Column(String(50), nullable=True)
    payment_reference = Column(String(100), nullable=True, index=True)
    payment_processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    version = Column(Integer, default=1, nullable=False)  # For optimistic locking
    
    # Additional fields
    notes = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Relationships
    booking_items = relationship("BookingItem", back_populates="booking", cascade="all, delete-orphan")
    booking_audit_logs = relationship("BookingAuditLog", back_populates="booking", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint('total_amount >= 0', name='check_total_amount_positive'),
        CheckConstraint('version > 0', name='check_version_positive'),
        Index('idx_booking_user_event', 'user_id', 'event_id'),
        Index('idx_booking_status_date', 'status', 'booking_date'),
        Index('idx_booking_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<Booking(id={self.id}, reference='{self.booking_reference}', status='{self.status.value}')>"
    
    def to_dict(self) -> dict:
        """Convert booking to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_id": self.event_id,
            "booking_reference": self.booking_reference,
            "quantity": self.quantity,
            "total_amount": float(self.total_amount),
            "currency": self.currency,
            "status": self.status.value,
            "payment_status": self.payment_status.value,
            "booking_date": self.booking_date.isoformat() if self.booking_date else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "payment_method": self.payment_method,
            "payment_reference": self.payment_reference,
            "payment_processed_at": self.payment_processed_at.isoformat() if self.payment_processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
            "notes": self.notes
        }
    
    @property
    def is_active(self) -> bool:
        """Check if booking is active (confirmed or pending)."""
        return self.status in [BookingStatus.PENDING, BookingStatus.CONFIRMED]
    
    @property
    def is_expired(self) -> bool:
        """Check if booking has expired."""
        if not self.expires_at:
            return False
        from datetime import timezone
        now = datetime.now(timezone.utc)
        return now > self.expires_at and self.status == BookingStatus.PENDING


class BookingItem(Base):
    """
    Individual booking items for detailed tracking.
    """
    
    __tablename__ = "booking_items"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Item details
    price_per_item = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    booking = relationship("Booking", back_populates="booking_items")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_item_quantity_positive'),
        CheckConstraint('price_per_item >= 0', name='check_item_price_positive'),
        CheckConstraint('total_price >= 0', name='check_item_total_positive'),
        Index('idx_booking_item_booking', 'booking_id'),
    )
    
    def __repr__(self):
        return f"<BookingItem(id={self.id}, booking_id={self.booking_id}, quantity={self.quantity})>"


class EventAvailability(Base):
    """
    Real-time event availability tracking for high consistency.
    This table maintains the current available capacity for each event.
    """
    
    __tablename__ = "event_availability"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, unique=True, nullable=False, index=True)
    
    # Capacity tracking
    total_capacity = Column(Integer, nullable=False)
    available_capacity = Column(Integer, nullable=False)
    reserved_capacity = Column(Integer, default=0, nullable=False)  # Pending bookings
    confirmed_capacity = Column(Integer, default=0, nullable=False)  # Confirmed bookings
    
    # Event pricing
    price = Column(Numeric(10, 2), nullable=False, default=0.00)  # Event price per ticket
    
    # Locking mechanism
    version = Column(Integer, default=1, nullable=False)  # For optimistic locking
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('total_capacity >= 0', name='check_total_capacity_positive'),
        CheckConstraint('available_capacity >= 0', name='check_available_capacity_positive'),
        CheckConstraint('reserved_capacity >= 0', name='check_reserved_capacity_positive'),
        CheckConstraint('confirmed_capacity >= 0', name='check_confirmed_capacity_positive'),
        CheckConstraint('available_capacity + reserved_capacity + confirmed_capacity = total_capacity', 
                       name='check_capacity_consistency'),
        CheckConstraint('version > 0', name='check_availability_version_positive'),
        Index('idx_availability_event', 'event_id'),
    )
    
    def __repr__(self):
        return f"<EventAvailability(event_id={self.event_id}, available={self.available_capacity}/{self.total_capacity})>"
    
    def to_dict(self) -> dict:
        """Convert availability to dictionary representation."""
        return {
            "event_id": self.event_id,
            "total_capacity": self.total_capacity,
            "available_capacity": self.available_capacity,
            "reserved_capacity": self.reserved_capacity,
            "confirmed_capacity": self.confirmed_capacity,
            "price": float(self.price),
            "version": self.version,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }
    
    @property
    def is_available(self) -> bool:
        """Check if event has available capacity."""
        return self.available_capacity > 0
    
    @property
    def utilization_percentage(self) -> float:
        """Calculate capacity utilization percentage."""
        if self.total_capacity == 0:
            return 0.0
        return ((self.reserved_capacity + self.confirmed_capacity) / self.total_capacity) * 100


class BookingAuditLog(Base):
    """
    Audit trail for booking changes to maintain data integrity.
    Tracks all modifications to bookings for compliance and debugging.
    """
    
    __tablename__ = "booking_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Change details
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, CANCEL, CONFIRM, etc.
    field_name = Column(String(100), nullable=True)  # Which field was changed
    old_value = Column(Text, nullable=True)  # Previous value
    new_value = Column(Text, nullable=True)  # New value
    
    # Metadata
    changed_by = Column(Integer, nullable=True)  # User ID who made the change
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    reason = Column(Text, nullable=True)  # Reason for the change
    
    # Relationships
    booking = relationship("Booking", back_populates="booking_audit_logs")
    
    # Constraints
    __table_args__ = (
        Index('idx_audit_booking', 'booking_id'),
        Index('idx_audit_action_date', 'action', 'changed_at'),
    )
    
    def __repr__(self):
        return f"<BookingAuditLog(id={self.id}, booking_id={self.booking_id}, action='{self.action}')>"
    
    def to_dict(self) -> dict:
        """Convert audit log to dictionary representation."""
        return {
            "id": self.id,
            "booking_id": self.booking_id,
            "action": self.action,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "reason": self.reason
        }


class WaitlistStatus(PyEnum):
    """Waitlist status enumeration."""
    PENDING = "pending"           # User joined waitlist, waiting for availability
    NOTIFIED = "notified"         # User notified of availability
    BOOKED = "booked"             # User successfully booked from waitlist
    EXPIRED = "expired"           # Waitlist entry expired
    CANCELLED = "cancelled"       # User cancelled waitlist entry


class WaitlistEntry(Base):
    """
    Waitlist model for managing event waitlist entries with high consistency.
    Tracks users waiting for event availability with priority ordering.
    """
    
    __tablename__ = "waitlist_entries"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id = Column(Integer, nullable=False, index=True)  # References auth service
    event_id = Column(Integer, nullable=False, index=True)  # References events service
    
    # Waitlist details
    quantity = Column(Integer, nullable=False)
    priority = Column(Integer, nullable=False, index=True)  # Lower number = higher priority
    status = Column(Enum(WaitlistStatus), default=WaitlistStatus.PENDING, nullable=False, index=True)
    
    # Timing
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notified_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # For notification expiry
    booked_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    version = Column(Integer, default=1, nullable=False)  # For optimistic locking
    
    # Additional fields
    notes = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Relationships
    waitlist_audit_logs = relationship("WaitlistAuditLog", back_populates="waitlist_entry", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_waitlist_quantity_positive'),
        CheckConstraint('priority > 0', name='check_waitlist_priority_positive'),
        CheckConstraint('version > 0', name='check_waitlist_version_positive'),
        UniqueConstraint('user_id', 'event_id', name='unique_user_event_waitlist'),
        Index('idx_waitlist_user_event', 'user_id', 'event_id'),
        Index('idx_waitlist_status_priority', 'status', 'priority'),
        Index('idx_waitlist_event_priority', 'event_id', 'priority'),
        Index('idx_waitlist_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<WaitlistEntry(id={self.id}, user_id={self.user_id}, event_id={self.event_id}, priority={self.priority})>"
    
    def to_dict(self) -> dict:
        """Convert waitlist entry to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_id": self.event_id,
            "quantity": self.quantity,
            "priority": self.priority,
            "status": self.status.value,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "notified_at": self.notified_at.isoformat() if self.notified_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "booked_at": self.booked_at.isoformat() if self.booked_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
            "notes": self.notes
        }
    
    @property
    def is_active(self) -> bool:
        """Check if waitlist entry is active (pending or notified)."""
        return self.status in [WaitlistStatus.PENDING, WaitlistStatus.NOTIFIED]
    
    @property
    def is_notification_expired(self) -> bool:
        """Check if notification has expired."""
        if not self.expires_at or self.status != WaitlistStatus.NOTIFIED:
            return False
        from datetime import timezone
        now = datetime.now(timezone.utc)
        return now > self.expires_at


class WaitlistAuditLog(Base):
    """
    Audit trail for waitlist changes to maintain data integrity.
    Tracks all modifications to waitlist entries for compliance and debugging.
    """
    
    __tablename__ = "waitlist_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    waitlist_entry_id = Column(Integer, ForeignKey("waitlist_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Change details
    action = Column(String(50), nullable=False)  # JOIN, NOTIFY, BOOK, CANCEL, EXPIRE, etc.
    field_name = Column(String(100), nullable=True)  # Which field was changed
    old_value = Column(Text, nullable=True)  # Previous value
    new_value = Column(Text, nullable=True)  # New value
    
    # Metadata
    changed_by = Column(Integer, nullable=True)  # User ID who made the change
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    reason = Column(Text, nullable=True)  # Reason for the change
    
    # Relationships
    waitlist_entry = relationship("WaitlistEntry", back_populates="waitlist_audit_logs")
    
    # Constraints
    __table_args__ = (
        Index('idx_waitlist_audit_entry', 'waitlist_entry_id'),
        Index('idx_waitlist_audit_action_date', 'action', 'changed_at'),
    )
    
    def __repr__(self):
        return f"<WaitlistAuditLog(id={self.id}, waitlist_entry_id={self.waitlist_entry_id}, action='{self.action}')>"
    
    def to_dict(self) -> dict:
        """Convert waitlist audit log to dictionary representation."""
        return {
            "id": self.id,
            "waitlist_entry_id": self.waitlist_entry_id,
            "action": self.action,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "reason": self.reason
        }