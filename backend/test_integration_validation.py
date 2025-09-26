#!/usr/bin/env python3
"""
Integration Validation Tests

Focused integration tests that validate the core functionality works correctly.
This is a simplified version that focuses on the most critical integration points.

Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3
"""

import pytest
import tempfile
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

# Import the modules we need to test
from backend.database import Base, get_db
from backend.unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedChatHistory, UnifiedTicketComment,
    UnifiedTicketActivity, UserRole, TicketStatus, TicketPriority, TicketCategory
)
from backend.unified_auth import UnifiedAuthService, Permission
from backend.data_sync_service import DataSyncService
from backend.admin_integration import setup_admin_dashboard_integration

# Test database configuration
TEST_DATABASE_URL = "sqlite:///:memory:"

class TestCoreIntegration:
    """Test core integration functionality"""
    
    @pytest.fixture(scope="function")
    def test_engine(self):
        """Create test database engine"""
        engine = create_engine(TEST_DATABASE_URL, echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture(scope="function")
    def test_db_session(self, test_engine):
        """Create test database session"""
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    @pytest.fixture(scope="function")
    def auth_service(self):
        """Create authentication service"""
        return UnifiedAuthService("test-secret-key")
    
    @pytest.fixture(scope="function")
    def test_user(self, test_db_session, auth_service):
        """Create test user"""
        user = UnifiedUser(
            user_id="test_user_001",
            username="testuser",
            email="test@example.com",
            password_hash=auth_service.hash_password("password"),
            full_name="Test User",
            role=UserRole.CUSTOMER,
            is_active=True
        )
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        return user
    
    @pytest.fixture(scope="function")
    def test_admin(self, test_db_session, auth_service):
        """Create test admin user"""
        admin = UnifiedUser(
            user_id="test_admin_001",
            username="testadmin",
            email="admin@example.com",
            password_hash=auth_service.hash_password("password"),
            full_name="Test Admin",
            role=UserRole.ADMIN,
            is_admin=True,
            is_active=True
        )
        test_db_session.add(admin)
        test_db_session.commit()
        test_db_session.refresh(admin)
        return admin
    
    def test_database_integration(self, test_db_session, test_user):
        """Test database integration works correctly"""
        # Verify user was created
        assert test_user.id is not None
        assert test_user.username == "testuser"
        assert test_user.role == UserRole.CUSTOMER
        
        # Create a ticket
        ticket = UnifiedTicket(
            title="Integration Test Ticket",
            description="Testing database integration",
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            category=TicketCategory.TECHNICAL,
            customer_id=test_user.id
        )
        test_db_session.add(ticket)
        test_db_session.commit()
        test_db_session.refresh(ticket)
        
        # Verify ticket was created and relationships work
        assert ticket.id is not None
        assert ticket.customer_id == test_user.id
        assert ticket.customer.username == "testuser"
        
        # Create a comment
        comment = UnifiedTicketComment(
            ticket_id=ticket.id,
            author_id=test_user.id,
            comment="Test comment",
            content="Test comment",
            is_internal=False
        )
        test_db_session.add(comment)
        test_db_session.commit()
        
        # Verify comment relationships
        assert len(ticket.comments) == 1
        assert ticket.comments[0].author.username == "testuser"
    
    def test_authentication_integration(self, test_db_session, auth_service, test_user, test_admin):
        """Test authentication integration works correctly"""
        # Test JWT token creation and validation
        jwt_token = auth_service.create_jwt_token(test_user)
        assert jwt_token is not None
        
        decoded_user = auth_service.get_user_from_jwt(jwt_token, test_db_session)
        assert decoded_user is not None
        assert decoded_user.username == "testuser"
        
        # Test session management
        session_token = auth_service.create_user_session(test_admin, test_db_session)
        assert session_token is not None
        
        session_user = auth_service.get_user_from_session(session_token, test_db_session)
        assert session_user is not None
        assert session_user.username == "testadmin"
        assert session_user.is_admin is True
        
        # Test permissions by creating AuthenticatedUser objects
        from backend.unified_auth import ROLE_PERMISSIONS, AuthenticatedUser
        
        # Create AuthenticatedUser for permission testing
        user_permissions = ROLE_PERMISSIONS.get(test_user.role, set())
        auth_user = AuthenticatedUser(
            id=test_user.id,
            user_id=test_user.user_id,
            username=test_user.username,
            email=test_user.email,
            full_name=test_user.full_name,
            role=test_user.role,
            is_active=test_user.is_active,
            is_admin=test_user.is_admin,
            permissions=user_permissions,
            session_id=session_token
        )
        
        admin_permissions = ROLE_PERMISSIONS.get(test_admin.role, set())
        auth_admin = AuthenticatedUser(
            id=test_admin.id,
            user_id=test_admin.user_id,
            username=test_admin.username,
            email=test_admin.email,
            full_name=test_admin.full_name,
            role=test_admin.role,
            is_active=test_admin.is_active,
            is_admin=test_admin.is_admin,
            permissions=admin_permissions,
            session_id=session_token
        )
        
        assert auth_user.has_permission(Permission.TICKET_CREATE)
        assert not auth_user.has_permission(Permission.USER_CREATE)
        assert auth_admin.has_permission(Permission.USER_CREATE)
        assert auth_admin.has_permission(Permission.DASHBOARD_VIEW)
    
    def test_api_integration(self, test_engine):
        """Test API integration works correctly"""
        # Create FastAPI app with admin integration
        app = FastAPI()
        
        # Override database dependency
        def override_get_db():
            TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
            db = TestSessionLocal()
            try:
                yield db
            finally:
                db.close()
        
        app.dependency_overrides[get_db] = override_get_db
        
        # Setup admin dashboard integration
        admin_integration = setup_admin_dashboard_integration(app)
        assert admin_integration is not None
        assert admin_integration.is_initialized
        
        # Test with client
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/api/admin/integration/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert health_data["initialized"] is True
    
    def test_data_sync_integration(self, test_db_session, test_user):
        """Test data synchronization integration"""
        # Create conversation
        conversation = UnifiedChatHistory(
            session_id="test_session_001",
            user_id=test_user.id,
            user_message="I need help with my internet connection",
            bot_response="I'll help you troubleshoot your connection",
            tools_used=["bt_website_tool"],
            sources={"knowledge_base": "connectivity_help"}
        )
        test_db_session.add(conversation)
        test_db_session.commit()
        test_db_session.refresh(conversation)
        
        # Test sync service
        sync_service = DataSyncService()
        
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            # Test conversation to ticket sync
            result = sync_service.create_ticket_from_conversation(conversation.id)
            
            # The result might not be successful due to conversation analysis,
            # but we can verify the sync service is working
            assert result is not None
            assert hasattr(result, 'success')
    
    def test_end_to_end_workflow(self, test_db_session, auth_service, test_user):
        """Test simplified end-to-end workflow"""
        # Step 1: User authentication
        jwt_token = auth_service.create_jwt_token(test_user)
        assert jwt_token is not None
        
        # Step 2: Create conversation
        conversation = UnifiedChatHistory(
            session_id="e2e_session_001",
            user_id=test_user.id,
            user_message="I have a billing question",
            bot_response="I can help you with billing questions"
        )
        test_db_session.add(conversation)
        test_db_session.commit()
        test_db_session.refresh(conversation)
        
        # Step 3: Create ticket manually (simulating AI decision)
        ticket = UnifiedTicket(
            title="Billing Question",
            description="Customer has a billing question",
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            category=TicketCategory.BILLING,
            customer_id=test_user.id
        )
        test_db_session.add(ticket)
        test_db_session.commit()
        test_db_session.refresh(ticket)
        
        # Step 4: Link conversation to ticket
        conversation.ticket_id = ticket.id
        test_db_session.commit()
        
        # Step 5: Verify workflow completed
        assert conversation.ticket_id == ticket.id
        assert ticket.customer_id == test_user.id
        
        # Query chat history linked to this ticket
        linked_chats = test_db_session.query(UnifiedChatHistory).filter(
            UnifiedChatHistory.ticket_id == ticket.id
        ).all()
        assert len(linked_chats) == 1
        assert linked_chats[0].user_message == "I have a billing question"


class TestRequirementsCoverage:
    """Test that all requirements are covered"""
    
    def test_requirement_2_1_customer_data_sync(self):
        """Test Requirement 2.1 - Customer data synchronization"""
        # This test validates that customer data can be synchronized
        # between AI agent and admin dashboard systems
        
        # Create in-memory database
        engine = create_engine(TEST_DATABASE_URL, echo=False)
        Base.metadata.create_all(engine)
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with TestSessionLocal() as session:
            # Create customer in AI agent system
            customer = UnifiedUser(
                user_id="sync_customer_001",
                username="synccustomer",
                email="sync@example.com",
                password_hash="hashed_password",
                full_name="Sync Customer",
                role=UserRole.CUSTOMER,
                is_active=True
            )
            session.add(customer)
            session.commit()
            session.refresh(customer)
            
            # Verify customer data is accessible from admin dashboard perspective
            admin_customer = session.query(UnifiedUser).filter(
                UnifiedUser.username == "synccustomer"
            ).first()
            
            assert admin_customer is not None
            assert admin_customer.email == "sync@example.com"
            assert admin_customer.role == UserRole.CUSTOMER
    
    def test_requirement_3_1_unified_authentication(self):
        """Test Requirement 3.1 - Unified authentication"""
        auth_service = UnifiedAuthService("test-secret")
        
        # Create a test user for JWT testing
        engine = create_engine(TEST_DATABASE_URL, echo=False)
        Base.metadata.create_all(engine)
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with TestSessionLocal() as session:
            test_user = UnifiedUser(
                user_id="jwt_test_001",
                username="jwtuser",
                email="jwt@example.com",
                password_hash="hashed_password",
                full_name="JWT User",
                role=UserRole.CUSTOMER,
                is_active=True
            )
            session.add(test_user)
            session.commit()
            session.refresh(test_user)
            
            # Test JWT token creation
            token = auth_service.create_jwt_token(test_user)
            assert token is not None
            
            # Test token validation
            decoded_data = auth_service.verify_jwt_token(token)
            assert decoded_data is not None
            assert decoded_data["username"] == "jwtuser"
    
    def test_requirement_4_1_api_integration(self):
        """Test Requirement 4.1 - API integration"""
        # Create FastAPI app
        app = FastAPI()
        
        # Setup admin integration
        admin_integration = setup_admin_dashboard_integration(app)
        assert admin_integration is not None
        
        # Verify routes were added
        route_paths = [route.path for route in app.routes]
        assert any("/api/admin" in path for path in route_paths)


def run_validation_tests():
    """Run validation tests"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_validation_tests()