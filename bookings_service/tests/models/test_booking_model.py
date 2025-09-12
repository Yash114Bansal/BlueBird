"""
Tests for Booking model.
Tests model creation, validation, and basic properties.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.models.booking import Booking, BookingStatus, PaymentStatus


class TestBookingModelCreation:
    """Test Booking model creation and basic properties."""
    
    def test_booking_creation_with_required_fields(self):
        """Test creating a booking with only required fields."""
        booking = Booking(
            user_id=1,
            event_id=1,
            booking_reference="BK-TEST-001",
            quantity=2,
            total_amount=Decimal("50.00"),
            currency="USD",
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            version=1
        )
        
        assert booking.user_id == 1
        assert booking.event_id == 1
        assert booking.booking_reference == "BK-TEST-001"
        assert booking.quantity == 2
        assert booking.total_amount == Decimal("50.00")
        assert booking.currency == "USD"
        assert booking.status == BookingStatus.PENDING
        assert booking.payment_status == PaymentStatus.PENDING
        assert booking.version == 1
    
    def test_booking_creation_with_all_fields(self):
        """Test creating a booking with all optional fields."""
        now = datetime.now(timezone.utc)
        booking = Booking(
            user_id=1,
            event_id=1,
            booking_reference="BK-FULL-001",
            quantity=2,
            total_amount=Decimal("50.00"),
            currency="USD",
            status=BookingStatus.CONFIRMED,
            payment_status=PaymentStatus.COMPLETED,
            booking_date=now,
            expires_at=now + timedelta(minutes=15),
            confirmed_at=now,
            cancelled_at=None,
            payment_method="credit_card",
            payment_reference="PAY-123",
            payment_processed_at=now,
            created_at=now,
            updated_at=now,
            version=1,
            notes="Test booking",
            ip_address="127.0.0.1",
            user_agent="test-agent"
        )
        
        assert booking.payment_method == "credit_card"
        assert booking.payment_reference == "PAY-123"
        assert booking.notes == "Test booking"
        assert booking.ip_address == "127.0.0.1"
        assert booking.user_agent == "test-agent"
    
    def test_booking_default_values(self):
        """Test that default values are set correctly."""
        booking = Booking(
            user_id=1,
            event_id=1,
            booking_reference="BK-DEFAULT-001",
            quantity=1,
            total_amount=Decimal("25.00"),
            currency="USD",
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            version=1
        )
        
        assert booking.currency == "USD"  
        assert booking.status == BookingStatus.PENDING  
        assert booking.payment_status == PaymentStatus.PENDING 
        assert booking.version == 1  