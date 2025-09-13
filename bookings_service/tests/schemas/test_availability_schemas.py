"""
Tests for Availability API schemas.
Tests schema validation and response format.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.schemas.booking import EventAvailabilityResponse


class TestEventAvailabilityResponseSchema:
    """Test EventAvailabilityResponse schema validation."""
    
    def test_valid_event_availability_response(self):
        """Test valid event availability response creation."""
        response_data = {
            "event_id": 1,
            "total_capacity": 100,
            "available_capacity": 75,
            "utilization_percentage": 25.0,
            "last_updated": datetime.now(timezone.utc)
        }
        
        response = EventAvailabilityResponse(**response_data)
        
        assert response.event_id == 1
        assert response.total_capacity == 100
        assert response.available_capacity == 75
        assert response.utilization_percentage == 25.0
        assert isinstance(response.last_updated, datetime)
    
    def test_event_availability_response_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        # Test missing event_id
        with pytest.raises(ValidationError) as exc_info:
            EventAvailabilityResponse(
                total_capacity=100,
                available_capacity=75,
                utilization_percentage=25.0,
                last_updated=datetime.now(timezone.utc)
            )
        assert "event_id" in str(exc_info.value)
        
        # Test missing total_capacity
        with pytest.raises(ValidationError) as exc_info:
            EventAvailabilityResponse(
                event_id=1,
                available_capacity=75,
                utilization_percentage=25.0,
                last_updated=datetime.now(timezone.utc)
            )
        assert "total_capacity" in str(exc_info.value)
        
        # Test missing available_capacity
        with pytest.raises(ValidationError) as exc_info:
            EventAvailabilityResponse(
                event_id=1,
                total_capacity=100,
                utilization_percentage=25.0,
                last_updated=datetime.now(timezone.utc)
            )
        assert "available_capacity" in str(exc_info.value)
        
        # Test missing utilization_percentage
        with pytest.raises(ValidationError) as exc_info:
            EventAvailabilityResponse(
                event_id=1,
                total_capacity=100,
                available_capacity=75,
                last_updated=datetime.now(timezone.utc)
            )
        assert "utilization_percentage" in str(exc_info.value)
        
        # Test missing last_updated
        with pytest.raises(ValidationError) as exc_info:
            EventAvailabilityResponse(
                event_id=1,
                total_capacity=100,
                available_capacity=75,
                utilization_percentage=25.0
            )
        assert "last_updated" in str(exc_info.value)
    
    def test_event_availability_response_invalid_types(self):
        """Test that invalid field types raise validation error."""
        # Test invalid event_id type
        with pytest.raises(ValidationError) as exc_info:
            EventAvailabilityResponse(
                event_id="invalid",
                total_capacity=100,
                available_capacity=75,
                utilization_percentage=25.0,
                last_updated=datetime.now(timezone.utc)
            )
        assert "event_id" in str(exc_info.value)
        
        # Test invalid total_capacity type
        with pytest.raises(ValidationError) as exc_info:
            EventAvailabilityResponse(
                event_id=1,
                total_capacity="invalid",
                available_capacity=75,
                utilization_percentage=25.0,
                last_updated=datetime.now(timezone.utc)
            )
        assert "total_capacity" in str(exc_info.value)
        
        # Test invalid available_capacity type
        with pytest.raises(ValidationError) as exc_info:
            EventAvailabilityResponse(
                event_id=1,
                total_capacity=100,
                available_capacity="invalid",
                utilization_percentage=25.0,
                last_updated=datetime.now(timezone.utc)
            )
        assert "available_capacity" in str(exc_info.value)
        
        # Test invalid utilization_percentage type
        with pytest.raises(ValidationError) as exc_info:
            EventAvailabilityResponse(
                event_id=1,
                total_capacity=100,
                available_capacity=75,
                utilization_percentage="invalid",
                last_updated=datetime.now(timezone.utc)
            )
        assert "utilization_percentage" in str(exc_info.value)
        
        # Test invalid last_updated type
        with pytest.raises(ValidationError) as exc_info:
            EventAvailabilityResponse(
                event_id=1,
                total_capacity=100,
                available_capacity=75,
                utilization_percentage=25.0,
                last_updated="invalid"
            )
        assert "last_updated" in str(exc_info.value)
    
    def test_event_availability_response_negative_values(self):
        """Test that negative values are handled correctly."""
        # Test negative total_capacity
        with pytest.raises(ValidationError) as exc_info:
            EventAvailabilityResponse(
                event_id=1,
                total_capacity=-1,
                available_capacity=75,
                utilization_percentage=25.0,
                last_updated=datetime.now(timezone.utc)
            )
        assert "total_capacity" in str(exc_info.value)
        
        # Test negative available_capacity
        with pytest.raises(ValidationError) as exc_info:
            EventAvailabilityResponse(
                event_id=1,
                total_capacity=100,
                available_capacity=-1,
                utilization_percentage=25.0,
                last_updated=datetime.now(timezone.utc)
            )
        assert "available_capacity" in str(exc_info.value)
    
    def test_event_availability_response_from_orm(self):
        """Test creating response from ORM object."""
        # Mock ORM object
        class MockAvailability:
            def __init__(self):
                self.event_id = 1
                self.total_capacity = 100
                self.available_capacity = 75
                self.utilization_percentage = 25.0
                self.last_updated = datetime.now(timezone.utc)
        
        mock_availability = MockAvailability()
        response = EventAvailabilityResponse.from_orm(mock_availability)
        
        assert response.event_id == 1
        assert response.total_capacity == 100
        assert response.available_capacity == 75
        assert response.utilization_percentage == 25.0
        assert isinstance(response.last_updated, datetime)
    
    def test_event_availability_response_json_serialization(self):
        """Test that response can be serialized to JSON."""
        response_data = {
            "event_id": 1,
            "total_capacity": 100,
            "available_capacity": 75,
            "utilization_percentage": 25.0,
            "last_updated": datetime.now(timezone.utc)
        }
        
        response = EventAvailabilityResponse(**response_data)
        json_data = response.json()
        
        # Verify JSON contains expected fields
        assert '"event_id":1' in json_data
        assert '"total_capacity":100' in json_data
        assert '"available_capacity":75' in json_data
        assert '"utilization_percentage":25.0' in json_data
        
        # Verify internal fields are not in JSON
        assert '"reserved_capacity"' not in json_data
        assert '"confirmed_capacity"' not in json_data
    
    def test_event_availability_response_dict_conversion(self):
        """Test that response can be converted to dictionary."""
        response_data = {
            "event_id": 1,
            "total_capacity": 100,
            "available_capacity": 75,
            "utilization_percentage": 25.0,
            "last_updated": datetime.now(timezone.utc)
        }
        
        response = EventAvailabilityResponse(**response_data)
        dict_data = response.dict()
        
        # Verify dictionary contains expected fields
        assert "event_id" in dict_data
        assert "total_capacity" in dict_data
        assert "available_capacity" in dict_data
        assert "utilization_percentage" in dict_data
        assert "last_updated" in dict_data
        
        # Verify internal fields are not in dictionary
        assert "reserved_capacity" not in dict_data
        assert "confirmed_capacity" not in dict_data
        
        # Verify values
        assert dict_data["event_id"] == 1
        assert dict_data["total_capacity"] == 100
        assert dict_data["available_capacity"] == 75
        assert dict_data["utilization_percentage"] == 25.0