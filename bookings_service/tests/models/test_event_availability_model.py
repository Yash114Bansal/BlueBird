"""
Tests for EventAvailability model.
Tests model creation, validation, and capacity management.
"""

import pytest

from app.models.booking import EventAvailability


class TestEventAvailabilityModel:
    """Test EventAvailability model creation and properties."""
    
    def test_availability_creation(self):
        """Test creating event availability with all fields."""
        availability = EventAvailability(
            event_id=1,
            total_capacity=100,
            available_capacity=80,
            reserved_capacity=15,
            confirmed_capacity=5,
            version=1
        )
        
        assert availability.event_id == 1
        assert availability.total_capacity == 100
        assert availability.available_capacity == 80
        assert availability.reserved_capacity == 15
        assert availability.confirmed_capacity == 5
        assert availability.version == 1
    
    def test_availability_capacity_consistency(self):
        """Test that capacity values are consistent."""
        availability = EventAvailability(
            event_id=1,
            total_capacity=100,
            available_capacity=80,
            reserved_capacity=15,
            confirmed_capacity=5,
            version=1
        )
        
        # Total should equal sum of all capacity types
        total_used = availability.reserved_capacity + availability.confirmed_capacity
        assert availability.available_capacity + total_used == availability.total_capacity
    
    def test_availability_properties(self):
        """Test computed properties of availability."""
        availability = EventAvailability(
            event_id=1,
            total_capacity=100,
            available_capacity=80,
            reserved_capacity=15,
            confirmed_capacity=5,
            version=1
        )
        
        # Test is_available property
        assert availability.is_available is True
        
        # Test utilization percentage
        expected_utilization = ((15 + 5) / 100) * 100  # 20%
        assert availability.utilization_percentage == expected_utilization
    
    def test_availability_full_capacity(self):
        """Test availability when at full capacity."""
        availability = EventAvailability(
            event_id=1,
            total_capacity=50,
            available_capacity=0,
            reserved_capacity=30,
            confirmed_capacity=20,
            version=1
        )
        
        assert availability.is_available is False
        assert availability.utilization_percentage == 100.0
        assert availability.available_capacity == 0