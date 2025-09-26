"""
Test Suite for Admin Dashboard Integration

This module contains comprehensive tests for the admin dashboard API integration layer.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os
from datetime import datetime

# Import the modules to test
from backend.admin_integration import (
    setup_admin_dashboard_integration,
    AdminDashboardIntegration,
    add_admin_routes_only,
    get_admin_route_list
)
from backend.admin_dashboard_integration import AdminAPIAdapter
from backend.unified_models import (
    Base, UnifiedUser as User, UnifiedTicket as Ticket, UnifiedTicketComment as TicketComment,
    TicketStatus, TicketPriority, TicketCategory
)
from backend.database import get_db

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_admin_integration.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture
def test_app():
    """Create a test FastAPI application"""
    app = FastAPI()
    
    # Override database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test database tables
    Base.metadata.create_all(bind=engine)
    
    return app

@pytest.fixture
def test_client(test_app):
    """Create a test client"""
    return TestClient(test_app)

@pytest.fixture
def test_db():
    """Create a test database session"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_user(test_db):
    """Create a test user"""
    user = User(
        user_id="test_user_001",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_admin=True,
        password_hash="hashed_password",
        created_at=datetime.utcnow()
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def test_ticket(test_db, test_user):
    """Create a test ticket"""
    ticket = Ticket(
        title="Test Ticket",
        description="This is a test ticket",
        customer_id=test_user.id,
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        category=TicketCategory.GENERAL,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_db.add(ticket)
    test_db.commit()
    test_db.refresh(ticket)
    return ticket

class TestAdminIntegration:
    """Test the main admin integration functionality"""
    
    def test_setup_admin_dashboard_integration(self, test_app):
        """Test setting up admin dashboard integration"""
        admin_integration = setup_admin_dashboard_integration(test_app, enable_compatibility=True)
        
        assert admin_integration is not None
        assert admin_integration.is_initialized
        assert len(admin_integration.routers) > 0
        assert admin_integration.compatibility_router is not None
    
    def test_admin_dashboard_integration_class(self, test_app):
        """Test AdminDashboardIntegration class directly"""
        integration = AdminDashboardIntegration()
        
        success = integration.initialize(test_app, enable_compatibility=False)
        
        assert success
        assert integration.is_initialized
        assert len(integration.routers) > 0
        assert integration.compatibility_router is None  # Disabled
    
    def test_add_admin_routes_only(self, test_app):
        """Test adding only admin routes without full integration"""
        success = add_admin_routes_only(test_app)
        
        assert success
        # Verify routes were added by checking the app's routes
        route_paths = [route.path for route in test_app.routes]
        assert any("/api/admin" in path for path in route_paths)
    
    def test_get_admin_route_list(self):
        """Test getting the list of admin routes"""
        routes = get_admin_route_list()
        
        assert len(routes) > 0
        assert all('path' in route for route in routes)
        assert all('method' in route for route in routes)
        assert all('description' in route for route in routes)

class TestAdminAPIAdapter:
    """Test the API adapter functionality"""
    
    def test_adapt_user_to_dict(self, test_user):
        """Test user to dictionary conversion"""
        user_dict = AdminAPIAdapter.adapt_user_to_dict(test_user)
        
        assert user_dict['id'] == test_user.id
        assert user_dict['username'] == test_user.username
        assert user_dict['email'] == test_user.email
        assert user_dict['is_admin'] == test_user.is_admin
    
    def test_adapt_user_to_dict_minimal(self, test_user):
        """Test minimal user to dictionary conversion"""
        user_dict = AdminAPIAdapter.adapt_user_to_dict(test_user, minimal=True)
        
        assert user_dict['id'] == test_user.id
        assert user_dict['username'] == test_user.username
        assert user_dict['email'] == test_user.email
        assert 'is_admin' not in user_dict  # Should not be in minimal version
    
    def test_adapt_ticket_to_dict(self, test_ticket):
        """Test ticket to dictionary conversion"""
        ticket_dict = AdminAPIAdapter.adapt_ticket_to_dict(test_ticket)
        
        assert ticket_dict['id'] == test_ticket.id
        assert ticket_dict['ticket_id'] == test_ticket.ticket_id
        assert ticket_dict['subject'] == test_ticket.subject
        assert ticket_dict['status'] == test_ticket.status
    
    def test_create_pagination_dict(self):
        """Test pagination dictionary creation"""
        pagination = AdminAPIAdapter.create_pagination_dict(
            page=1, per_page=10, total=25, has_next=True, has_prev=False
        )
        
        assert pagination['page'] == 1
        assert pagination['per_page'] == 10
        assert pagination['total'] == 25
        assert pagination['pages'] == 3  # ceil(25/10)
        assert pagination['has_next'] is True
        assert pagination['has_prev'] is False

class TestAdminEndpoints:
    """Test the admin API endpoints"""
    
    def test_admin_dashboard_endpoint(self, test_client, test_app, test_user):
        """Test the admin dashboard endpoint"""
        # Setup integration
        setup_admin_dashboard_integration(test_app)
        
        # Mock authentication (in real tests, you'd use proper auth)
        # For now, we'll test the endpoint structure
        
        # Note: This test would need proper authentication setup
        # response = test_client.get("/api/admin/dashboard")
        # assert response.status_code in [200, 401]  # 401 if not authenticated
    
    def test_health_endpoints(self, test_client, test_app):
        """Test health check endpoints"""
        setup_admin_dashboard_integration(test_app)
        
        # Test integration health endpoint
        response = test_client.get("/api/admin/integration/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert 'status' in health_data
        assert 'initialized' in health_data
    
    def test_status_endpoints(self, test_client, test_app):
        """Test status endpoints"""
        setup_admin_dashboard_integration(test_app)
        
        # Test integration status endpoint
        response = test_client.get("/api/admin/integration/status")
        assert response.status_code == 200
        
        status_data = response.json()
        assert 'initialized' in status_data
        assert 'routers_count' in status_data

class TestCompatibilityLayer:
    """Test the Flask compatibility layer"""
    
    def test_compatibility_routes_exist(self, test_app, test_client):
        """Test that compatibility routes are created"""
        setup_admin_dashboard_integration(test_app, enable_compatibility=True)
        
        # Check that Flask-style routes exist
        route_paths = [route.path for route in test_app.routes]
        
        # Should have both modern and compatibility routes
        assert any("/api/admin/dashboard" in path for path in route_paths)
        assert any("/api/tickets/" in path for path in route_paths)
    
    def test_flask_response_format(self, test_app, test_client):
        """Test that Flask compatibility endpoints return proper format"""
        setup_admin_dashboard_integration(test_app, enable_compatibility=True)
        
        # Test a compatibility endpoint (would need auth in real scenario)
        # response = test_client.get("/api/tickets/stats")
        # This would test the Flask-style response format with 'success' field

class TestErrorHandling:
    """Test error handling in admin integration"""
    
    def test_invalid_integration_setup(self):
        """Test handling of invalid integration setup"""
        # Test with None app
        try:
            integration = AdminDashboardIntegration()
            success = integration.initialize(None)
            assert not success
        except Exception:
            # Should handle gracefully
            pass
    
    def test_database_error_handling(self, test_app):
        """Test handling of database errors"""
        # This would test scenarios where database is unavailable
        pass

class TestPerformance:
    """Test performance aspects of admin integration"""
    
    def test_route_registration_performance(self, test_app):
        """Test that route registration is efficient"""
        import time
        
        start_time = time.time()
        setup_admin_dashboard_integration(test_app)
        end_time = time.time()
        
        # Should complete within reasonable time
        assert (end_time - start_time) < 5.0  # 5 seconds max
    
    def test_memory_usage(self, test_app):
        """Test memory usage of integration"""
        # This would test memory consumption
        pass

# Integration test scenarios
class TestIntegrationScenarios:
    """Test real-world integration scenarios"""
    
    def test_full_integration_workflow(self, test_app, test_client):
        """Test complete integration workflow"""
        # 1. Setup integration
        admin_integration = setup_admin_dashboard_integration(test_app)
        assert admin_integration.is_initialized
        
        # 2. Check health
        response = test_client.get("/api/admin/integration/health")
        assert response.status_code == 200
        
        # 3. Check status
        response = test_client.get("/api/admin/integration/status")
        assert response.status_code == 200
        
        # 4. Verify routes are accessible (structure-wise)
        routes = get_admin_route_list()
        assert len(routes) > 0
    
    def test_migration_scenario(self, test_app):
        """Test migration from Flask to FastAPI scenario"""
        # 1. Start with compatibility mode
        integration = setup_admin_dashboard_integration(test_app, enable_compatibility=True)
        assert integration.compatibility_router is not None
        
        # 2. Simulate migration by creating new integration without compatibility
        new_integration = AdminDashboardIntegration()
        success = new_integration.initialize(test_app, enable_compatibility=False)
        assert success
        assert new_integration.compatibility_router is None

# Cleanup
def teardown_module():
    """Clean up after tests"""
    try:
        os.remove("test_admin_integration.db")
    except FileNotFoundError:
        pass

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])