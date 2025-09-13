"""
Tests for Waitlist API endpoints.
Tests waitlist API operations with proper authentication and validation.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.main import app
from app.schemas.booking import WaitlistJoin, WaitlistCancel
from app.models.booking import WaitlistStatus
from app.api.dependencies import (
    get_current_user_id, 
    get_current_user_role,
    get_authenticated_user,
    get_admin_user
)


class TestWaitlistAPI:
    """Test cases for Waitlist API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client with dependency overrides."""
        # Override authentication dependencies
        app.dependency_overrides[get_current_user_id] = lambda: 1
        app.dependency_overrides[get_current_user_role] = lambda: "user"
        app.dependency_overrides[get_authenticated_user] = lambda: {
            "user_id": 1,
            "client_ip": "127.0.0.1",
            "user_agent": "test"
        }
        app.dependency_overrides[get_admin_user] = lambda: {"user_id": 1, "role": "admin"}
        
        yield TestClient(app)
        
        # Clean up overrides
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def admin_client(self):
        """Create test client with admin dependency overrides."""
        # Override authentication dependencies for admin
        app.dependency_overrides[get_current_user_id] = lambda: 1
        app.dependency_overrides[get_current_user_role] = lambda: "admin"
        app.dependency_overrides[get_authenticated_user] = lambda: {
            "user_id": 1,
            "client_ip": "127.0.0.1",
            "user_agent": "test"
        }
        app.dependency_overrides[get_admin_user] = lambda: {"user_id": 1, "role": "admin"}
        
        yield TestClient(app)
        
        # Clean up overrides
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def unauth_client(self):
        """Create test client without authentication overrides."""
        yield TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        return {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture
    def admin_headers(self):
        """Create admin authentication headers."""
        return {
            "Authorization": "Bearer admin-token",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture
    def waitlist_join_data(self):
        """Create waitlist join data."""
        return {
            "event_id": 1,
            "quantity": 2,
            "notes": "Test waitlist entry"
        }
    
    @pytest.fixture
    def waitlist_cancel_data(self):
        """Create waitlist cancel data."""
        return {
            "reason": "Test cancellation"
        }
    
    @pytest.fixture
    def mock_waitlist_entry(self):
        """Create mock waitlist entry."""
        entry = MagicMock()
        entry.id = 1
        entry.user_id = 1
        entry.event_id = 1
        entry.quantity = 2
        entry.priority = 1
        entry.status = WaitlistStatus.PENDING
        entry.joined_at = datetime.now(timezone.utc)
        entry.created_at = datetime.now(timezone.utc)
        entry.updated_at = datetime.now(timezone.utc)
        entry.version = 1
        entry.notes = "Test waitlist entry"
        return entry
    
    def test_join_waitlist_success(self, client, auth_headers, waitlist_join_data, mock_waitlist_entry):
        """Test successful waitlist join."""
        with patch('app.api.v1.waitlist.waitlist_service.join_waitlist') as mock_join:
            mock_join.return_value = (mock_waitlist_entry, True, 1)
            
            response = client.post(
                "/api/v1/waitlist/join",
                json=waitlist_join_data,
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Successfully joined waitlist"
            assert data["estimated_position"] == 1
            assert "waitlist_entry" in data
    
    def test_join_waitlist_unauthorized(self, waitlist_join_data):
        """Test waitlist join without authentication."""
        # Create client without dependency overrides
        unauth_client = TestClient(app)
        response = unauth_client.post(
            "/api/v1/waitlist/join",
            json=waitlist_join_data
        )
        
        assert response.status_code == 403
    
    def test_join_waitlist_validation_error(self, client, auth_headers):
        """Test waitlist join with validation error."""
        invalid_data = {
            "event_id": -1,  # Invalid event ID
            "quantity": 0,   # Invalid quantity
            "notes": "Test"
        }
        
        response = client.post(
            "/api/v1/waitlist/join",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_user_waitlist_entries_success(self, client, auth_headers, mock_waitlist_entry):
        """Test getting user waitlist entries."""
        with patch('app.api.v1.waitlist.waitlist_service.get_user_waitlist_entries') as mock_get:
            mock_get.return_value = ([mock_waitlist_entry], 1)
            
            response = client.get(
                "/api/v1/waitlist/",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "page_size" in data
    
    def test_get_waitlist_entry_success(self, client, auth_headers, mock_waitlist_entry):
        """Test getting specific waitlist entry."""
        with patch('app.api.v1.waitlist.waitlist_service.get_waitlist_entry_by_id') as mock_get:
            mock_get.return_value = mock_waitlist_entry
            
            response = client.get(
                "/api/v1/waitlist/1",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["user_id"] == 1
            assert data["event_id"] == 1
    
    def test_get_waitlist_entry_not_found(self, client, auth_headers):
        """Test getting non-existent waitlist entry."""
        with patch('app.api.v1.waitlist.waitlist_service.get_waitlist_entry_by_id') as mock_get:
            mock_get.return_value = None
            
            response = client.get(
                "/api/v1/waitlist/999",
                headers=auth_headers
            )
            
            assert response.status_code == 404
    
    def test_cancel_waitlist_entry_success(self, client, auth_headers, waitlist_cancel_data, mock_waitlist_entry):
        """Test successful waitlist entry cancellation."""
        with patch('app.api.v1.waitlist.get_current_user_id') as mock_user_id:
            mock_user_id.return_value = 1
            
            with patch('app.api.v1.waitlist.get_current_user_role') as mock_role:
                mock_role.return_value = "user"
                
                with patch('app.api.v1.waitlist.waitlist_service.get_waitlist_entry_by_id') as mock_get:
                    mock_get.return_value = mock_waitlist_entry
                    
                    with patch('app.api.v1.waitlist.waitlist_service.cancel_waitlist_entry') as mock_cancel:
                        mock_cancel.return_value = (mock_waitlist_entry, True)
                        
                        response = client.put(
                            "/api/v1/waitlist/1/cancel",
                            json=waitlist_cancel_data,
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["message"] == "Waitlist entry cancelled successfully"
    
    def test_get_waitlist_position_success(self, client, auth_headers, mock_waitlist_entry):
        """Test getting waitlist position."""
        with patch('app.api.v1.waitlist.get_current_user_id') as mock_user_id:
            mock_user_id.return_value = 1
            
            with patch('app.api.v1.waitlist.get_current_user_role') as mock_role:
                mock_role.return_value = "user"
                
                with patch('app.api.v1.waitlist.waitlist_service.get_waitlist_entry_by_id') as mock_get:
                    mock_get.return_value = mock_waitlist_entry
                    
                    with patch('app.api.v1.waitlist.waitlist_service.get_waitlist_position') as mock_position:
                        mock_position.return_value = 3
                        
                        response = client.get(
                            "/api/v1/waitlist/1/position",
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["waitlist_entry_id"] == 1
                        assert data["position"] == 3
                        assert data["status"] == "active"
    
    def test_get_waitlist_audit_log_success(self, client, auth_headers, mock_waitlist_entry):
        """Test getting waitlist audit log."""
        with patch('app.api.v1.waitlist.get_current_user_id') as mock_user_id:
            mock_user_id.return_value = 1
            
            with patch('app.api.v1.waitlist.get_current_user_role') as mock_role:
                mock_role.return_value = "user"
                
                with patch('app.api.v1.waitlist.waitlist_service.get_waitlist_entry_by_id') as mock_get:
                    mock_get.return_value = mock_waitlist_entry
                    
                    with patch('app.api.v1.waitlist.get_db') as mock_db:
                        mock_session = MagicMock()
                        mock_audit_log = MagicMock()
                        mock_audit_log.id = 1
                        mock_audit_log.action = "JOIN"
                        mock_audit_log.changed_at = datetime.now(timezone.utc)
                        mock_audit_log.waitlist_entry_id = 1
                        mock_audit_log.changed_by = 1
                        mock_audit_log.field_name = None
                        mock_audit_log.old_value = None
                        mock_audit_log.new_value = None
                        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_audit_log]
                        mock_db.return_value = mock_session
                        
                        response = client.get(
                            "/api/v1/waitlist/1/audit",
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert isinstance(data, list)
                        # The test should expect the actual number of audit logs returned
                        assert len(data) >= 1
                        # Check that at least one entry has the expected action
                        actions = [entry["action"] for entry in data]
                        assert "JOIN" in actions
    
    def test_get_event_waitlist_admin_success(self, client, admin_headers, mock_waitlist_entry):
        """Test getting event waitlist as admin."""
        with patch('app.api.v1.waitlist.get_admin_user') as mock_admin:
            mock_admin.return_value = {"user_id": 1, "role": "admin"}
            
            with patch('app.api.v1.waitlist.waitlist_service.get_event_waitlist') as mock_get:
                mock_get.return_value = ([mock_waitlist_entry], 1)
                
                response = client.get(
                    "/api/v1/waitlist/admin/event/1",
                    headers=admin_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "items" in data
                assert "total" in data
        
    def test_notify_waitlist_entries_admin_success(self, client, admin_headers):
        """Test manually notifying waitlist entries as admin."""
        with patch('app.api.v1.waitlist.get_admin_user') as mock_admin:
            mock_admin.return_value = {"user_id": 1, "role": "admin"}
            
            with patch('app.api.v1.waitlist.waitlist_service.notify_next_waitlist_entries') as mock_notify:
                mock_notify.return_value = [MagicMock(), MagicMock()]  # 2 entries notified
                
                response = client.post(
                    "/api/v1/waitlist/admin/notify/1?available_quantity=4",
                    headers=admin_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["message"] == "Notified 2 waitlist entries"
                assert data["data"]["notifications_sent"] == 2
    
    
    def test_check_waitlist_eligibility_success(self, client, auth_headers):
        """Test successful waitlist eligibility check."""
        with patch('app.api.v1.waitlist.get_current_user_id') as mock_user_id:
            mock_user_id.return_value = 1
            
            with patch('app.api.v1.waitlist.waitlist_service.check_waitlist_eligibility') as mock_check:
                mock_check.return_value = {
                    "can_join": True,
                    "event_id": 1
                }
                
                response = client.get(
                    "/api/v1/waitlist/check/1?quantity=2",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["can_join"] is True
                assert data["event_id"] == 1
    
    def test_check_waitlist_eligibility_event_available(self, client, auth_headers):
        """Test waitlist eligibility check when event has available capacity."""
        with patch('app.api.v1.waitlist.get_current_user_id') as mock_user_id:
            mock_user_id.return_value = 1
            
            with patch('app.api.v1.waitlist.waitlist_service.check_waitlist_eligibility') as mock_check:
                mock_check.return_value = {
                    "can_join": False,
                    "event_id": 1
                }
                
                response = client.get(
                    "/api/v1/waitlist/check/1",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["can_join"] is False
                assert data["event_id"] == 1
    
    def test_check_waitlist_eligibility_existing_entry(self, client, auth_headers):
        """Test waitlist eligibility check when user has existing entry."""
        with patch('app.api.v1.waitlist.get_current_user_id') as mock_user_id:
            mock_user_id.return_value = 1
            
            with patch('app.api.v1.waitlist.waitlist_service.check_waitlist_eligibility') as mock_check:
                mock_check.return_value = {
                    "can_join": False,
                    "event_id": 1
                }
                
                response = client.get(
                    "/api/v1/waitlist/check/1",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["can_join"] is False
                assert data["event_id"] == 1
    
    
    def test_check_waitlist_eligibility_invalid_quantity(self, client, auth_headers):
        """Test waitlist eligibility check with invalid quantity."""
        with patch('app.api.v1.waitlist.get_current_user_id') as mock_user_id:
            mock_user_id.return_value = 1
            
            response = client.get(
                "/api/v1/waitlist/check/1?quantity=0",  # Invalid quantity
                headers=auth_headers
            )
            
            assert response.status_code == 422  # Validation error
    
    def test_join_waitlist_event_not_found(self, client, auth_headers, waitlist_join_data):
        """Test joining waitlist for non-existent event."""
        with patch('app.api.v1.waitlist.get_authenticated_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": 1,
                "client_ip": "127.0.0.1",
                "user_agent": "test"
            }
            
            with patch('app.api.v1.waitlist.waitlist_service.join_waitlist') as mock_join:
                mock_join.side_effect = Exception("Event not found or not available for booking")
                
                response = client.post(
                    "/api/v1/waitlist/join",
                    json=waitlist_join_data,
                    headers=auth_headers
                )
                
                assert response.status_code == 400
                response_data = response.json()
                # Check if the error message is in the response (could be in different keys)
                response_text = str(response_data)
                assert "Event not found" in response_text