"""
Tests for Bookings API endpoints.
Tests booking creation, retrieval, and management endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestBookingsAPI:
    """Test Bookings API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_api_client_creation(self, client):
        """Test that API client is created correctly."""
        assert client is not None
    
    def test_unauthorized_booking_creation(self, client):
        """Test booking creation without authentication returns 403."""
        booking_data = {
            "event_id": 1,
            "quantity": 2,
            "notes": "Test booking"
        }
        
        response = client.post("/api/v1/bookings/", json=booking_data)
        
        # Should return 403 Forbidden (not 401 Unauthorized)
        assert response.status_code == 403
    
    def test_unauthorized_booking_retrieval(self, client):
        """Test booking retrieval without authentication returns 403."""
        response = client.get("/api/v1/bookings/")
        
        # Should return 403 Forbidden
        assert response.status_code == 403
    
    def test_unauthorized_specific_booking_retrieval(self, client):
        """Test specific booking retrieval without authentication returns 403."""
        response = client.get("/api/v1/bookings/1")
        
        # Should return 403 Forbidden
        assert response.status_code == 403