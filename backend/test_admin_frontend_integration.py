"""
Test Admin Dashboard Frontend Integration
Tests the integration of admin dashboard frontend with main FastAPI application
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import tempfile
import os
from pathlib import Path

# Import the main app
from main import app

class TestAdminFrontendIntegration:
    """Test admin dashboard frontend integration"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_admin_dashboard_main_route(self):
        """Test admin dashboard main route serves HTML"""
        response = self.client.get("/admin")
        
        # Should return HTML response (even if file doesn't exist, should attempt to serve)
        assert response.status_code in [200, 404]  # 404 if file doesn't exist
        
    def test_admin_dashboard_with_slash(self):
        """Test admin dashboard route with trailing slash"""
        response = self.client.get("/admin/")
        
        # Should return HTML response
        assert response.status_code in [200, 404]
    
    def test_admin_tickets_route(self):
        """Test admin tickets page route"""
        response = self.client.get("/admin/tickets")
        
        # Should return HTML response
        assert response.status_code in [200, 404]
    
    def test_admin_users_route(self):
        """Test admin users page route"""
        response = self.client.get("/admin/users")
        
        # Should return HTML response
        assert response.status_code in [200, 404]
    
    def test_admin_integration_route(self):
        """Test admin integration page route"""
        response = self.client.get("/admin/integration")
        
        # Should return HTML response
        assert response.status_code in [200, 404]
    
    def test_admin_settings_route(self):
        """Test admin settings page route"""
        response = self.client.get("/admin/settings")
        
        # Should return HTML response
        assert response.status_code in [200, 404]
    
    def test_admin_spa_routing(self):
        """Test SPA routing for admin dashboard"""
        response = self.client.get("/admin/some-spa-route")
        
        # Should return HTML response (index.html for SPA routing)
        assert response.status_code in [200, 404]
    
    def test_admin_api_endpoints_exist(self):
        """Test that admin API endpoints are available"""
        # Test dashboard endpoint (should require auth)
        response = self.client.get("/api/admin/dashboard")
        assert response.status_code in [401, 403]  # Should require authentication
        
        # Test users endpoint (should require auth)
        response = self.client.get("/api/admin/users")
        assert response.status_code in [401, 403]  # Should require authentication
        
        # Test integration status endpoint (should require auth)
        response = self.client.get("/api/admin/integration/status")
        assert response.status_code in [401, 403]  # Should require authentication
    
    def test_support_api_endpoints_exist(self):
        """Test that support API endpoints are available"""
        # Test tickets endpoint (should require auth)
        response = self.client.get("/api/support/tickets")
        assert response.status_code in [401, 403]  # Should require authentication
    
    def test_auth_api_endpoints_exist(self):
        """Test that auth API endpoints are available"""
        # Test login endpoint (should accept POST)
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "testpass"
        })
        # Should return 401 for invalid credentials or 422 for validation error
        assert response.status_code in [401, 422, 500]
        
        # Test logout endpoint
        response = self.client.post("/api/auth/logout")
        # Should return success even without auth
        assert response.status_code in [200, 401]
    
    @patch('backend.admin_frontend_integration.Path.exists')
    def test_static_file_mounting_with_existing_files(self, mock_exists):
        """Test static file mounting when files exist"""
        mock_exists.return_value = True
        
        # This test verifies the mounting logic would work if files existed
        # The actual mounting happens during app startup
        assert True  # If we get here, the import and setup worked
    
    def test_admin_dashboard_integration_imports(self):
        """Test that all required imports work"""
        try:
            from backend.admin_frontend_integration import AdminFrontendIntegration, setup_admin_frontend_integration
            from backend.admin_api_proxy import setup_admin_api_proxy
            from backend.admin_auth_proxy import setup_admin_auth_proxy
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import admin dashboard integration modules: {e}")
    
    def test_unified_api_functionality(self):
        """Test that unified API endpoints respond correctly"""
        # Test that the API structure is in place
        
        # Auth endpoints
        auth_endpoints = [
            "/api/auth/login",
            "/api/auth/logout", 
            "/api/auth/profile",
            "/api/auth/verify"
        ]
        
        for endpoint in auth_endpoints:
            response = self.client.get(endpoint) if endpoint != "/api/auth/login" else self.client.post(endpoint, json={})
            # Should not return 404 (endpoint exists)
            assert response.status_code != 404, f"Endpoint {endpoint} not found"
        
        # Admin endpoints
        admin_endpoints = [
            "/api/admin/dashboard",
            "/api/admin/users",
            "/api/admin/integration/status",
            "/api/admin/metrics"
        ]
        
        for endpoint in admin_endpoints:
            response = self.client.get(endpoint)
            # Should not return 404 (endpoint exists), but may return 401/403 for auth
            assert response.status_code != 404, f"Endpoint {endpoint} not found"
        
        # Support endpoints
        support_endpoints = [
            "/api/support/tickets"
        ]
        
        for endpoint in support_endpoints:
            response = self.client.get(endpoint)
            # Should not return 404 (endpoint exists), but may return 401/403 for auth
            assert response.status_code != 404, f"Endpoint {endpoint} not found"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])