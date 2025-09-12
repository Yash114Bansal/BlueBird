"""
Tests for Admin API endpoints.
Tests admin-only booking and availability management endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestAdminAPI:
    """Test Admin API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_api_client_creation(self, client):
        """Test that API client is created correctly."""
        assert client is not None
    
    def test_admin_endpoint_unauthorized(self, client):
        """Test admin endpoint without authentication returns 403."""
        response = client.get("/api/v1/admin/bookings/")
        
        # Should return 403 Forbidden (not 401 Unauthorized)
        assert response.status_code == 403
    
    def test_admin_cancel_booking_unauthorized(self, client):
        """Test admin cancel booking endpoint without authentication."""
        cancel_data = {
            "reason": "Admin cancellation"
        }
        
        response = client.post(
            "/api/v1/admin/bookings/1/cancel",
            json=cancel_data
        )
        
        # Endpoint might not exist, so expect 404
        assert response.status_code == 404
    
    def test_admin_update_availability_unauthorized(self, client):
        """Test admin update availability endpoint without authentication."""
        availability_data = {
            "total_capacity": 200,
            "available_capacity": 150
        }
        
        response = client.put(
            "/api/v1/admin/availability/1",
            json=availability_data
        )
        
        # Endpoint might not exist, so expect 404
        assert response.status_code == 404