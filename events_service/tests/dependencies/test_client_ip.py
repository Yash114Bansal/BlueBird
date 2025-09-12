"""
Tests for client IP extraction dependencies.
"""

import pytest
from fastapi import Request

from app.api.dependencies import get_client_ip


class TestClientIP:
    """Test cases for client IP extraction."""
    
    def test_get_client_ip_x_forwarded_for(self):
        """Test getting client IP from X-Forwarded-For header."""
        mock_request = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/test",
                "headers": [(b"x-forwarded-for", b"192.168.1.1")]
            }
        )
        
        ip = get_client_ip(mock_request)
        
        assert ip == "192.168.1.1"
    
    def test_get_client_ip_x_real_ip(self):
        """Test getting client IP from X-Real-IP header."""
        mock_request = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/test",
                "headers": [(b"x-real-ip", b"10.0.0.1")]
            }
        )
        
        ip = get_client_ip(mock_request)
        
        assert ip == "10.0.0.1"
    
    def test_get_client_ip_direct_connection(self):
        """Test getting client IP from direct connection."""
        mock_request = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/test",
                "headers": [],
                "client": ("127.0.0.1", 12345)
            }
        )
        
        ip = get_client_ip(mock_request)
        
        assert ip == "127.0.0.1"
    
    def test_get_client_ip_no_client_info(self):
        """Test getting client IP when no client info is available."""
        mock_request = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/test",
                "headers": []
            }
        )
        
        ip = get_client_ip(mock_request)
        
        assert ip == "unknown"
    
    def test_get_client_ip_priority_order(self):
        """Test that X-Forwarded-For takes priority over X-Real-IP."""
        mock_request = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/test",
                "headers": [
                    (b"x-forwarded-for", b"192.168.1.1"),
                    (b"x-real-ip", b"10.0.0.1")
                ]
            }
        )
        
        ip = get_client_ip(mock_request)
        
        assert ip == "192.168.1.1"
    
    def test_get_client_ip_x_forwarded_for_multiple_ips(self):
        """Test getting client IP from X-Forwarded-For with multiple IPs."""
        mock_request = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/test",
                "headers": [(b"x-forwarded-for", b"192.168.1.1, 10.0.0.1, 172.16.0.1")]
            }
        )
        
        ip = get_client_ip(mock_request)
        
        assert ip == "192.168.1.1"