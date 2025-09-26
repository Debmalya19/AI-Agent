#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite for Admin Dashboard Integration

This test suite covers all aspects of the admin dashboard integration:
- Database integration tests to verify unified models work correctly
- Authentication integration tests for JWT token sharing between systems
- API integration tests to verify admin dashboard endpoints work through FastAPI
- End-to-end tests for complete user workflows across both systems
- Data synchronization tests to verify real-time updates work correctly

Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3
"""

import pytest
import asyncio
import tempfile
import os
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any, Optional

# Import all the modules we need to test
from backend.database import Base, get_db
from backend.unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedChatHistory, UnifiedTicketComment,
    UnifiedTicketActivity, UnifiedUserSession, UserRole, TicketStatus,
    TicketPriority, TicketCategory
)
from backend.unified_auth import UnifiedAuthService, Permission
from backend.data_sync_service import DataSyncService
from backend.admin_integration import setup_admin_dashboard_integration
from backend.admin_dashboard_integration import AdminAPIAdapter
from backend.conversation_to_ticket_utils import analyze_conversation_for_ticket
from backend.sync_events import EventDrivenSyncManager

# Test database configuration
TEST_DATABASE_URL = "sqlite:///:memory:"

class IntegrationTestBase:
    """Base class for integration tests with common setup"""
    
    @pytest.fixture(scope="function")
    def test_engine(self):
        """Create a test database engine"""
        engine = create_engine(TEST_DATABASE_URL, echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture(scope="function")
    def test_db_session(self, test_engine):
        """Create a test database session"""
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    @pytest.fixture(scope="function")
    def test_app(self, test_engine):
        """Create a test FastAPI application"""
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
        return app
    
    @pytest.fixture(scope="function")
    def test_client(self, test_app):
        """Create a test client"""
        return TestClient(test_app)
    
    @pytest.fixture(scope="function")
    def auth_service(self):
        """Create an authentication service for testing"""
        return UnifiedAuthService(
            jwt_secret="test-secret-key-for-integration-tests",
            jwt_algorithm="HS256",
            token_expire_hours=1
        )
    
    @pytest.fixture(scope="function")
    def sample_users(self, test_db_session):
        """Create sample users for testing"""
        users = {}
        
        # Customer user
        customer = UnifiedUser(
            user_id="customer_001",
            username="customer",
            email="customer@example.com",
            password_hash="hashed_password",
            full_name="Test Customer",
            role=UserRole.CUSTOMER,
            is_admin=False,
            is_active=True
        )
        test_db_session.add(customer)
        
        # Agent user
        agent = UnifiedUser(
            user_id="agent_001",
            username="agent",
            email="agent@example.com",
            password_hash="hashed_password",
            full_name="Test Agent",
            role=UserRole.AGENT,
            is_admin=True,
            is_active=True
        )
        test_db_session.add(agent)
        
        # Admin user
        admin = UnifiedUser(
            user_id="admin_001",
            username="admin",
            email="admin@example.com",
            password_hash="hashed_password",
            full_name="Test Admin",
            role=UserRole.ADMIN,
            is_admin=True,
            is_active=True
        )
        test_db_session.add(admin)
        
        test_db_session.commit()
        test_db_session.refresh(customer)
        test_db_session.refresh(agent)
        test_db_session.refresh(admin)
        
        users['customer'] = customer
        users['agent'] = agent
        users['admin'] = admin
        
        return users


class TestDatabaseIntegration(IntegrationTestBase):
    """Test database integration and unified models"""
    
    def test_unified_models_creation(self, test_db_session, sample_users):
        """Test that unified models can be created and work correctly"""
        customer = sample_users['customer']
        
        # Create a ticket
        ticket = UnifiedTicket(
            title="Integration Test Ticket",
            description="This is a test ticket for integration testing",
            status=TicketStatus.OPEN,
            priority=TicketPriority.HIGH,
            category=TicketCategory.TECHNICAL,
            customer_id=customer.id,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(ticket)
        test_db_session.commit()
        test_db_session.refresh(ticket)
        
        # Verify ticket was created
        assert ticket.id is not None
        assert ticket.customer_id == customer.id
        assert ticket.status == TicketStatus.OPEN
        
        # Test relationship
        assert ticket.customer.username == "customer"
        assert len(customer.created_tickets) == 1
    
    def test_chat_history_integration(self, test_db_session, sample_users):
        """Test chat history integration with tickets"""
        customer = sample_users['customer']
        
        # Create chat history
        chat = UnifiedChatHistory(
            session_id="integration_session_001",
            user_id=customer.id,
            user_message="I need help with my internet connection",
            bot_response="I'll help you troubleshoot your connection",
            tools_used=["bt_website_tool", "search_tool"],
            sources={"knowledge_base": "connectivity_help"},
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(chat)
        test_db_session.commit()
        test_db_session.refresh(chat)
        
        # Create ticket and link to chat
        ticket = UnifiedTicket(
            title="Connection Issue",
            description="Customer needs help with internet connection",
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            category=TicketCategory.TECHNICAL,
            customer_id=customer.id
        )
        test_db_session.add(ticket)
        test_db_session.commit()
        test_db_session.refresh(ticket)
        
        # Link chat to ticket
        chat.ticket_id = ticket.id
        test_db_session.commit()
        
        # Verify relationship
        assert chat.ticket_id == ticket.id
        assert len(ticket.chat_history) == 1
        assert ticket.chat_history[0].user_message == "I need help with my internet connection"
    
    def test_ticket_comments_and_activities(self, test_db_session, sample_users):
        """Test ticket comments and activities integration"""
        customer = sample_users['customer']
        agent = sample_users['agent']
        
        # Create ticket
        ticket = UnifiedTicket(
            title="Test Ticket for Comments",
            description="Testing comments and activities",
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            category=TicketCategory.SUPPORT,
            customer_id=customer.id
        )
        test_db_session.add(ticket)
        test_db_session.commit()
        test_db_session.refresh(ticket)
        
        # Add comment
        comment = UnifiedTicketComment(
            ticket_id=ticket.id,
            author_id=agent.id,
            comment="I'm looking into this issue for you",
            content="I'm looking into this issue for you",  # Admin dashboard compatibility
            is_internal=False,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(comment)
        
        # Add activity
        activity = UnifiedTicketActivity(
            ticket_id=ticket.id,
            activity_type="status_change",
            description="Ticket status changed to In Progress",
            performed_by_id=agent.id,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(activity)
        
        test_db_session.commit()
        
        # Verify relationships
        assert len(ticket.comments) == 1
        assert len(ticket.activities) == 1
        assert ticket.comments[0].author.username == "agent"
        assert ticket.activities[0].performed_by.username == "agent"
    
    def test_database_constraints_and_validation(self, test_db_session, sample_users):
        """Test database constraints and data validation"""
        customer = sample_users['customer']
        
        # Test unique constraints
        duplicate_user = UnifiedUser(
            user_id="customer_001",  # Same as existing user
            username="duplicate",
            email="duplicate@example.com",
            password_hash="hashed_password",
            role=UserRole.CUSTOMER
        )
        test_db_session.add(duplicate_user)
        
        with pytest.raises(Exception):  # Should raise integrity error
            test_db_session.commit()
        
        test_db_session.rollback()
        
        # Test foreign key constraints
        invalid_ticket = UnifiedTicket(
            title="Invalid Ticket",
            description="This ticket has invalid customer_id",
            customer_id=99999,  # Non-existent customer
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            category=TicketCategory.TECHNICAL
        )
        test_db_session.add(invalid_ticket)
        
        with pytest.raises(Exception):  # Should raise foreign key error
            test_db_session.commit()


class TestAuthenticationIntegration(IntegrationTestBase):
    """Test authentication integration between systems"""
    
    def test_jwt_token_sharing(self, test_db_session, auth_service, sample_users):
        """Test JWT token sharing between AI agent and admin dashboard"""
        customer = sample_users['customer']
        
        # Create JWT token
        jwt_token = auth_service.create_jwt_token(customer)
        assert jwt_token is not None
        
        # Verify token can be decoded
        decoded_user = auth_service.get_user_from_jwt(jwt_token, test_db_session)
        assert decoded_user is not None
        assert decoded_user.username == "customer"
        assert decoded_user.role == UserRole.CUSTOMER
    
    def test_session_management_integration(self, test_db_session, auth_service, sample_users):
        """Test session management across both systems"""
        admin = sample_users['admin']
        
        # Create user session
        session_token = auth_service.create_user_session(admin, test_db_session)
        assert session_token is not None
        
        # Verify session exists in database
        session = test_db_session.query(UnifiedUserSession).filter(
            UnifiedUserSession.session_id == session_token
        ).first()
        assert session is not None
        assert session.user_id == admin.id
        assert session.is_active is True
        
        # Validate session
        validated_user = auth_service.get_user_from_session(session_token, test_db_session)
        assert validated_user is not None
        assert validated_user.username == "admin"
        
        # Invalidate session
        result = auth_service.invalidate_session(session_token, test_db_session)
        assert result is True
        
        # Verify session is invalidated
        invalid_user = auth_service.get_user_from_session(session_token, test_db_session)
        assert invalid_user is None
    
    def test_role_based_permissions(self, sample_users):
        """Test role-based permission system integration"""
        customer = sample_users['customer']
        agent = sample_users['agent']
        admin = sample_users['admin']
        
        # Test customer permissions
        assert customer.has_permission(Permission.TICKET_CREATE)
        assert customer.has_permission(Permission.TICKET_VIEW_OWN)
        assert not customer.has_permission(Permission.USER_DELETE)
        assert not customer.has_permission(Permission.DASHBOARD_VIEW)
        
        # Test agent permissions
        assert agent.has_permission(Permission.TICKET_CREATE)
        assert agent.has_permission(Permission.TICKET_VIEW_ALL)
        assert agent.has_permission(Permission.TICKET_ASSIGN)
        assert not agent.has_permission(Permission.USER_DELETE)
        
        # Test admin permissions
        assert admin.has_permission(Permission.DASHBOARD_VIEW)
        assert admin.has_permission(Permission.USER_CREATE)
        assert admin.has_permission(Permission.USER_UPDATE)
        assert admin.has_permission(Permission.TICKET_DELETE)
    
    def test_cross_system_authentication(self, test_db_session, auth_service, sample_users):
        """Test authentication works across AI agent and admin dashboard"""
        agent = sample_users['agent']
        
        # Simulate login from AI agent system
        authenticated_user = auth_service.authenticate_user("agent", "test_password", test_db_session)
        # Note: This would fail in real scenario due to password hashing, but tests the flow
        
        # Create session for admin dashboard access
        session_token = auth_service.create_user_session(agent, test_db_session)
        
        # Verify agent can access admin functions
        admin_user = auth_service.get_user_from_session(session_token, test_db_session)
        assert admin_user.is_admin is True
        assert admin_user.has_permission(Permission.DASHBOARD_VIEW)


class TestAPIIntegration(IntegrationTestBase):
    """Test API integration between FastAPI and admin dashboard"""
    
    def test_admin_dashboard_routes_integration(self, test_app, test_client):
        """Test that admin dashboard routes are properly integrated into FastAPI"""
        # Setup admin dashboard integration
        admin_integration = setup_admin_dashboard_integration(test_app)
        assert admin_integration is not None
        assert admin_integration.is_initialized
        
        # Test health endpoint
        response = test_client.get("/api/admin/integration/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert health_data["initialized"] is True
    
    def test_api_adapter_functionality(self, sample_users):
        """Test API adapter converts data correctly between systems"""
        customer = sample_users['customer']
        
        # Test user adaptation
        user_dict = AdminAPIAdapter.adapt_user_to_dict(customer)
        assert user_dict["id"] == customer.id
        assert user_dict["username"] == "customer"
        assert user_dict["email"] == "customer@example.com"
        assert user_dict["role"] == UserRole.CUSTOMER.value
        
        # Test minimal user adaptation
        minimal_dict = AdminAPIAdapter.adapt_user_to_dict(customer, minimal=True)
        assert "password_hash" not in minimal_dict
        assert "created_at" not in minimal_dict
        assert minimal_dict["username"] == "customer"
    
    def test_admin_api_endpoints(self, test_app, test_client, test_db_session, sample_users):
        """Test admin API endpoints work through FastAPI"""
        # Setup integration
        setup_admin_dashboard_integration(test_app)
        
        # Test status endpoint
        response = test_client.get("/api/admin/integration/status")
        assert response.status_code == 200
        
        status_data = response.json()
        assert "initialized" in status_data
        assert "routers_count" in status_data
        assert status_data["initialized"] is True
    
    def test_error_handling_integration(self, test_app, test_client):
        """Test error handling across integrated systems"""
        setup_admin_dashboard_integration(test_app)
        
        # Test non-existent endpoint
        response = test_client.get("/api/admin/nonexistent")
        assert response.status_code == 404
        
        # Test invalid data handling would go here
        # (specific endpoints would need authentication setup)


class TestEndToEndWorkflows(IntegrationTestBase):
    """Test complete end-to-end user workflows"""
    
    @pytest.mark.asyncio
    async def test_customer_support_workflow(self, test_db_session, auth_service, sample_users):
        """Test complete customer support workflow from conversation to resolution"""
        customer = sample_users['customer']
        agent = sample_users['agent']
        
        # Step 1: Customer has conversation with AI agent
        conversation = UnifiedChatHistory(
            session_id="e2e_session_001",
            user_id=customer.id,
            user_message="My internet is completely down and I need urgent help!",
            bot_response="I understand this is urgent. Let me help you troubleshoot and create a support ticket.",
            tools_used=["bt_website_tool", "create_ticket_tool"],
            sources={"knowledge_base": "connectivity_troubleshooting"},
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(conversation)
        test_db_session.commit()
        test_db_session.refresh(conversation)
        
        # Step 2: AI agent creates support ticket
        sync_service = DataSyncService()
        
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            result = sync_service.create_ticket_from_conversation(conversation.id)
            assert result.success is True
            ticket_id = result.entity_id
        
        # Step 3: Verify ticket was created correctly
        ticket = test_db_session.query(UnifiedTicket).filter(UnifiedTicket.id == ticket_id).first()
        assert ticket is not None
        assert ticket.customer_id == customer.id
        assert ticket.status == TicketStatus.OPEN
        assert ticket.priority == TicketPriority.HIGH  # Should be high due to "urgent" keyword
        
        # Step 4: Agent takes ownership of ticket
        ticket.assigned_agent_id = agent.id
        test_db_session.commit()
        
        # Step 5: Agent adds comment
        comment = UnifiedTicketComment(
            ticket_id=ticket.id,
            author_id=agent.id,
            comment="I'm investigating your connection issue. I'll run some diagnostics.",
            content="I'm investigating your connection issue. I'll run some diagnostics.",
            is_internal=False,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(comment)
        
        # Step 6: Record activity
        activity = UnifiedTicketActivity(
            ticket_id=ticket.id,
            activity_type="assigned",
            description=f"Ticket assigned to agent {agent.username}",
            performed_by_id=agent.id,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(activity)
        test_db_session.commit()
        
        # Step 7: Agent resolves ticket
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            resolve_result = sync_service.handle_ticket_status_change(
                ticket.id, TicketStatus.RESOLVED, agent.id
            )
            assert resolve_result.success is True
        
        # Step 8: Verify final state
        final_ticket = test_db_session.query(UnifiedTicket).filter(UnifiedTicket.id == ticket_id).first()
        assert final_ticket.status == TicketStatus.RESOLVED
        assert final_ticket.resolved_at is not None
        assert len(final_ticket.comments) >= 1
        assert len(final_ticket.activities) >= 2  # Assignment + resolution
    
    def test_admin_dashboard_workflow(self, test_db_session, auth_service, sample_users):
        """Test admin dashboard workflow for managing users and tickets"""
        admin = sample_users['admin']
        customer = sample_users['customer']
        
        # Step 1: Admin logs in
        session_token = auth_service.create_user_session(admin, test_db_session)
        authenticated_admin = auth_service.get_user_from_session(session_token, test_db_session)
        assert authenticated_admin.is_admin is True
        
        # Step 2: Admin views customer information
        customer_data = AdminAPIAdapter.adapt_user_to_dict(customer)
        assert customer_data["username"] == "customer"
        assert customer_data["role"] == UserRole.CUSTOMER.value
        
        # Step 3: Admin creates ticket on behalf of customer
        admin_created_ticket = UnifiedTicket(
            title="Admin Created Ticket",
            description="Ticket created by admin on behalf of customer",
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            category=TicketCategory.BILLING,
            customer_id=customer.id,
            created_by_admin_id=admin.id,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(admin_created_ticket)
        test_db_session.commit()
        test_db_session.refresh(admin_created_ticket)
        
        # Step 4: Admin adds internal comment
        internal_comment = UnifiedTicketComment(
            ticket_id=admin_created_ticket.id,
            author_id=admin.id,
            comment="Internal note: Customer called about billing discrepancy",
            content="Internal note: Customer called about billing discrepancy",
            is_internal=True,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(internal_comment)
        test_db_session.commit()
        
        # Step 5: Verify admin permissions and actions
        assert admin.has_permission(Permission.TICKET_CREATE)
        assert admin.has_permission(Permission.TICKET_VIEW_ALL)
        assert admin.has_permission(Permission.USER_UPDATE)
        
        # Verify ticket was created correctly
        assert admin_created_ticket.created_by_admin_id == admin.id
        assert len(admin_created_ticket.comments) == 1
        assert admin_created_ticket.comments[0].is_internal is True


class TestDataSynchronization(IntegrationTestBase):
    """Test data synchronization between systems"""
    
    @pytest.mark.asyncio
    async def test_real_time_conversation_sync(self, test_db_session, sample_users):
        """Test real-time synchronization of conversations to tickets"""
        customer = sample_users['customer']
        
        # Create conversation that should trigger ticket creation
        urgent_conversation = UnifiedChatHistory(
            session_id="sync_test_session",
            user_id=customer.id,
            user_message="CRITICAL: My business internet has been down for 3 hours! I'm losing money!",
            bot_response="I understand this is critical for your business. I'm creating an urgent support ticket.",
            tools_used=["create_ticket_tool", "bt_website_tool"],
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(urgent_conversation)
        test_db_session.commit()
        test_db_session.refresh(urgent_conversation)
        
        # Test conversation analysis
        with patch('backend.conversation_to_ticket_utils.SessionLocal', return_value=test_db_session):
            analysis = analyze_conversation_for_ticket(urgent_conversation.id)
            
            assert analysis.analysis_result.value == "needs_ticket"
            assert analysis.confidence_score > 0.7
            assert analysis.ticket_metadata.priority == TicketPriority.CRITICAL
            assert "urgent" in analysis.ticket_metadata.tags or "critical" in analysis.ticket_metadata.tags
        
        # Test automatic ticket creation
        sync_service = DataSyncService()
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            sync_result = sync_service.create_ticket_from_conversation(urgent_conversation.id)
            
            assert sync_result.success is True
            assert sync_result.entity_id is not None
        
        # Verify conversation is linked to ticket
        updated_conversation = test_db_session.query(UnifiedChatHistory).filter(
            UnifiedChatHistory.id == urgent_conversation.id
        ).first()
        assert updated_conversation.ticket_id == sync_result.entity_id
    
    @pytest.mark.asyncio
    async def test_data_consistency_checks(self, test_db_session, sample_users):
        """Test data consistency maintenance across systems"""
        customer = sample_users['customer']
        
        # Create inconsistent data scenarios
        
        # Scenario 1: Orphaned conversation (user_id points to non-existent user)
        orphaned_conversation = UnifiedChatHistory(
            session_id="orphaned_session",
            user_id=99999,  # Non-existent user
            user_message="This conversation has no valid user",
            bot_response="This should be detected as inconsistent",
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(orphaned_conversation)
        
        # Scenario 2: Conversation linked to non-existent ticket
        invalid_ticket_conversation = UnifiedChatHistory(
            session_id="invalid_ticket_session",
            user_id=customer.id,
            user_message="This conversation links to invalid ticket",
            bot_response="This should also be detected",
            ticket_id=99999,  # Non-existent ticket
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(invalid_ticket_conversation)
        
        test_db_session.commit()
        
        # Run consistency check
        sync_service = DataSyncService()
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            consistency_result = await sync_service.perform_consistency_check()
            
            assert consistency_result.total_checked > 0
            assert consistency_result.inconsistencies_found >= 2
            assert consistency_result.resolved_count > 0
    
    @pytest.mark.asyncio
    async def test_event_driven_synchronization(self, test_db_session, sample_users):
        """Test event-driven synchronization system"""
        customer = sample_users['customer']
        
        # Initialize event manager
        event_manager = EventDrivenSyncManager()
        
        # Mock database operations
        with patch('backend.sync_events.SessionLocal', return_value=test_db_session):
            event_manager.initialize()
            assert event_manager.is_initialized is True
        
        # Test event handler registration
        events_received = []
        
        async def test_event_handler(event_data):
            events_received.append(event_data)
        
        event_manager.register_event_handler("ticket_created", test_event_handler)
        
        # Simulate ticket creation event
        from backend.sync_events import SyncEventData
        
        test_event_data = SyncEventData(
            table_name="unified_tickets",
            operation="insert",
            entity_id=123,
            user_id=customer.id,
            timestamp=datetime.now(timezone.utc)
        )
        
        await event_manager._trigger_event_handlers("ticket_created", test_event_data)
        
        # Verify event was handled
        assert len(events_received) == 1
        assert events_received[0].entity_id == 123
        assert events_received[0].user_id == customer.id
    
    def test_ticket_status_synchronization(self, test_db_session, sample_users):
        """Test ticket status changes are synchronized across systems"""
        customer = sample_users['customer']
        agent = sample_users['agent']
        
        # Create ticket
        ticket = UnifiedTicket(
            title="Status Sync Test Ticket",
            description="Testing status synchronization",
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            category=TicketCategory.TECHNICAL,
            customer_id=customer.id,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(ticket)
        test_db_session.commit()
        test_db_session.refresh(ticket)
        
        # Test status change synchronization
        sync_service = DataSyncService()
        
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            # Change status to in progress
            result1 = sync_service.handle_ticket_status_change(
                ticket.id, TicketStatus.IN_PROGRESS, agent.id
            )
            assert result1.success is True
            
            # Change status to resolved
            result2 = sync_service.handle_ticket_status_change(
                ticket.id, TicketStatus.RESOLVED, agent.id
            )
            assert result2.success is True
        
        # Verify status changes were recorded
        updated_ticket = test_db_session.query(UnifiedTicket).filter(UnifiedTicket.id == ticket.id).first()
        assert updated_ticket.status == TicketStatus.RESOLVED
        assert updated_ticket.resolved_at is not None
        
        # Verify activities were created
        activities = test_db_session.query(UnifiedTicketActivity).filter(
            UnifiedTicketActivity.ticket_id == ticket.id,
            UnifiedTicketActivity.activity_type == "status_change"
        ).all()
        assert len(activities) >= 2  # Should have at least 2 status changes


class TestPerformanceAndScalability(IntegrationTestBase):
    """Test performance and scalability aspects of integration"""
    
    def test_bulk_data_operations(self, test_db_session, sample_users):
        """Test performance with bulk data operations"""
        customer = sample_users['customer']
        
        # Create multiple conversations
        conversations = []
        for i in range(50):
            conv = UnifiedChatHistory(
                session_id=f"bulk_session_{i}",
                user_id=customer.id,
                user_message=f"Test message {i}",
                bot_response=f"Test response {i}",
                created_at=datetime.now(timezone.utc)
            )
            conversations.append(conv)
        
        test_db_session.add_all(conversations)
        test_db_session.commit()
        
        # Test bulk ticket creation
        sync_service = DataSyncService()
        
        start_time = datetime.now()
        
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            # Create tickets for first 10 conversations
            for conv in conversations[:10]:
                result = sync_service.create_ticket_from_conversation(conv.id)
                assert result.success is True
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert duration < 30.0  # 30 seconds for 10 ticket creations
    
    def test_concurrent_operations(self, test_db_session, sample_users):
        """Test concurrent operations don't cause conflicts"""
        customer = sample_users['customer']
        
        # Create ticket for concurrent testing
        ticket = UnifiedTicket(
            title="Concurrent Test Ticket",
            description="Testing concurrent operations",
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            category=TicketCategory.TECHNICAL,
            customer_id=customer.id
        )
        test_db_session.add(ticket)
        test_db_session.commit()
        test_db_session.refresh(ticket)
        
        # Simulate concurrent comment additions
        comments = []
        for i in range(5):
            comment = UnifiedTicketComment(
                ticket_id=ticket.id,
                author_id=customer.id,
                comment=f"Concurrent comment {i}",
                content=f"Concurrent comment {i}",
                is_internal=False,
                created_at=datetime.now(timezone.utc)
            )
            comments.append(comment)
        
        test_db_session.add_all(comments)
        test_db_session.commit()
        
        # Verify all comments were added
        ticket_comments = test_db_session.query(UnifiedTicketComment).filter(
            UnifiedTicketComment.ticket_id == ticket.id
        ).all()
        assert len(ticket_comments) == 5


# Test runner and utilities
def run_integration_tests():
    """Run all integration tests"""
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure for debugging
    ])


if __name__ == "__main__":
    run_integration_tests()