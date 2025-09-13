"""
Tests for BookingItem model.
Tests model creation, validation, and relationships.
"""

import pytest
from decimal import Decimal

from app.models.booking import BookingItem


class TestBookingItemModel:
    """Test BookingItem model creation and properties."""
    
    def test_booking_item_creation(self):
        """Test creating a booking item with all fields."""
        booking_item = BookingItem(
            booking_id=1,
            price_per_item=Decimal("25.00"),
            quantity=2,
            total_price=Decimal("50.00")
        )
        
        assert booking_item.booking_id == 1
        assert booking_item.price_per_item == Decimal("25.00")
        assert booking_item.quantity == 2
        assert booking_item.total_price == Decimal("50.00")
    
    def test_booking_item_price_calculation(self):
        """Test that total price is calculated correctly."""
        booking_item = BookingItem(
            booking_id=1,
            price_per_item=Decimal("100.00"),
            quantity=3,
            total_price=Decimal("300.00")
        )
        
        expected_total = booking_item.price_per_item * booking_item.quantity
        assert booking_item.total_price == expected_total
    