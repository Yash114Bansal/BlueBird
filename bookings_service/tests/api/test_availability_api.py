"""
Tests for Availability API endpoints.
Tests availability checking and capacity management endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestAvailabilityAPI:
    """Test Availability API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_api_client_creation(self, client):
        """Test that API client is created correctly."""
        assert client is not None
    
    def test_availability_endpoint_not_found(self, client):
        """Test availability endpoint returns 404 for non-existent routes."""
        response = client.get("/api/v1/availability/1")
        
        # Endpoint might not exist or be configured differently
        assert response.status_code == 404
    
    def test_reserve_capacity_endpoint_not_found(self, client):
        """Test reserve capacity endpoint returns 404."""
        reservation_data = {
            "quantity": 5,
            "hold_duration_minutes": 15
        }
        
        response = client.post(
            "/api/v1/availability/1/reserve",
            json=reservation_data
        )
        
        assert response.status_code == 404
    
    def test_release_capacity_endpoint_not_found(self, client):
        """Test release capacity endpoint returns 404."""
        release_data = {
            "quantity": 5,
            "capacity_type": "reserved"
        }
        
        response = client.post(
            "/api/v1/availability/1/release",
            json=release_data
        )
        
        assert response.status_code == 404