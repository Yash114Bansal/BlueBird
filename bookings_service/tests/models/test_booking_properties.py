"""
Tests for Booking model properties and computed fields.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.models.booking import Booking, BookingStatus, PaymentStatus


class TestBookingProperties:
    """Test Booking model properties and computed fields."""
    
    def test_is_active_property(self):
        """Test the is_active property."""
        # Active booking
        active_booking = Booking(
            user_id=1,
            event_id=1,
            booking_reference="BK-ACTIVE-001",
            quantity=2,
            total_amount=Decimal("50.00"),
            currency="USD",
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            version=1
        )
        assert active_booking.is_active is True
        
        # Cancelled booking
        cancelled_booking = Booking(
            user_id=1,
            event_id=1,
            booking_reference="BK-CANCELLED-001",
            quantity=2,
            total_amount=Decimal("50.00"),
            currency="USD",
            status=BookingStatus.CANCELLED,
            payment_status=PaymentStatus.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            version=1
        )
        assert cancelled_booking.is_active is False
    
    def test_is_expired_property(self):
        """Test the is_expired property."""
        now = datetime.now(timezone.utc)
        
        # Non-expired booking
        active_booking = Booking(
            user_id=1,
            event_id=1,
            booking_reference="BK-ACTIVE-001",
            quantity=2,
            total_amount=Decimal("50.00"),
            currency="USD",
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            expires_at=now + timedelta(minutes=15),
            version=1
        )
        assert active_booking.is_expired is False
        
        # Expired booking
        expired_booking = Booking(
            user_id=1,
            event_id=1,
            booking_reference="BK-EXPIRED-001",
            quantity=2,
            total_amount=Decimal("50.00"),
            currency="USD",
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            expires_at=now - timedelta(minutes=15),
            version=1
        )
        assert expired_booking.is_expired is True
        
        # Booking without expiry
        no_expiry_booking = Booking(
            user_id=1,
            event_id=1,
            booking_reference="BK-NO-EXPIRY-001",
            quantity=2,
            total_amount=Decimal("50.00"),
            currency="USD",
            status=BookingStatus.CONFIRMED,
            payment_status=PaymentStatus.COMPLETED,
            expires_at=None,
            version=1
        )
        assert no_expiry_booking.is_expired is False
    
    def test_status_properties(self):
        """Test status-related properties."""
        # Confirmed booking
        confirmed_booking = Booking(
            user_id=1,
            event_id=1,
            booking_reference="BK-CONFIRMED-001",
            quantity=2,
            total_amount=Decimal("50.00"),
            currency="USD",
            status=BookingStatus.CONFIRMED,
            payment_status=PaymentStatus.COMPLETED,
            expires_at=None,
            version=1
        )
        assert confirmed_booking.status == BookingStatus.CONFIRMED
        assert confirmed_booking.payment_status == PaymentStatus.COMPLETED
        
        # Pending booking
        pending_booking = Booking(
            user_id=1,
            event_id=1,
            booking_reference="BK-PENDING-001",
            quantity=2,
            total_amount=Decimal("50.00"),
            currency="USD",
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            version=1
        )
        assert pending_booking.status == BookingStatus.PENDING
        assert pending_booking.payment_status == PaymentStatus.PENDING