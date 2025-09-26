#!/usr/bin/env python3
"""
End-to-End Workflow Integration Tests

Tests complete user workflows across both AI agent and admin dashboard systems
to verify seamless integration and data flow.

Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.database import Base, get_db
from backend.unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedChatHistory, UnifiedTicketComment,
    UnifiedTicketActivity, UnifiedUserSession, UserRole, TicketStatus,
    TicketPriority, TicketCategory
)
from backend.unified_auth import UnifiedAuthService, Permission
from backend.data_sync_service import DataSyncService
from backend.conversation_to_ticket_utils import ConversationAnalyzer, analyze_conversation_for_ticket
from backend.admin_integration import setup_admin_dashboard_integration

# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"

class EndToEndTestBase:
    """Base class for end-to-end tests"""
    
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
    def test_app(self, test_engine):
        """Create test FastAPI application"""
        app = FastAPI()
        
        def override_get_db():
            TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
            db = TestSessionLocal()
            try:
                yield db
            finally:
                db.close()
        
        app.dependency_overrides[get_db] = override_get_db
        setup_admin_dashboard_integration(app)
        return app
    
    @pytest.fixture(scope="function")
    def test_client(self, test_app):
        """Create test client"""
        return TestClient(test_app)
    
    @pytest.fixture(scope="function")
    def auth_service(self):
        """Create authentication service"""
        return UnifiedAuthService("test-secret-key-e2e")
    
    @pytest.fixture(scope="function")
    def sync_service(self):
        """Create data sync service"""
        return DataSyncService()
    
    @pytest.fixture(scope="function")
    def conversation_analyzer(self):
        """Create conversation analyzer"""
        return ConversationAnalyzer()


class TestCustomerSupportWorkflow(EndToEndTestBase):
    """Test complete customer support workflows"""
    
    def test_simple_inquiry_workflow(self, test_db_session, auth_service, sync_service):
        """Test workflow for simple customer inquiry that doesn't need escalation"""
        # Step 1: Create customer
        customer = UnifiedUser(
            user_id="simple_customer_001",
            username="simplecustomer",
            email="simple@example.com",
            password_hash=auth_service.hash_password("password"),
            full_name="Simple Customer",
            role=UserRole.CUSTOMER,
            is_active=True
        )
        test_db_session.add(customer)
        test_db_session.commit()
        test_db_session.refresh(customer)
        
        # Step 2: Customer has simple conversation with AI
        conversation = UnifiedChatHistory(
            session_id="simple_session_001",
            user_id=customer.id,
            user_message="What are your business hours?",
            bot_response="Our business hours are Monday to Friday, 9 AM to 6 PM, and Saturday 10 AM to 4 PM.",
            tools_used=["bt_support_hours_tool"],
            sources={"knowledge_base": "support_hours"},
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(conversation)
        test_db_session.commit()
        test_db_session.refresh(conversation)
        
        # Step 3: Analyze conversation - should NOT create ticket
        with patch('backend.conversation_to_ticket_utils.SessionLocal', return_value=test_db_session):
            analysis = analyze_conversation_for_ticket(conversation.id)
            
            # Simple informational query should not need a ticket
            assert analysis.analysis_result.value in ["informational", "resolved"]
            assert analysis.confidence_score < 0.5  # Low confidence for ticket creation
        
        # Step 4: Verify no ticket was created automatically
        tickets = test_db_session.query(UnifiedTicket).filter(
            UnifiedTicket.customer_id == customer.id
        ).all()
        assert len(tickets) == 0
        
        # Step 5: Customer should be satisfied with AI response
        # (In real system, this would be tracked through feedback mechanisms)
        assert conversation.bot_response is not None
        assert "business hours" in conversation.bot_response.lower()
    
    def test_technical_issue_escalation_workflow(self, test_db_session, auth_service, sync_service):
        """Test workflow for technical issue that needs escalation"""
        # Step 1: Create customer and agent
        customer = UnifiedUser(
            user_id="tech_customer_001",
            username="techcustomer",
            email="tech@example.com",
            password_hash=auth_service.hash_password("password"),
            full_name="Tech Customer",
            role=UserRole.CUSTOMER,
            is_active=True
        )
        
        agent = UnifiedUser(
            user_id="tech_agent_001",
            username="techagent",
            email="techagent@example.com",
            password_hash=auth_service.hash_password("password"),
            full_name="Tech Agent",
            role=UserRole.AGENT,
            is_admin=True,
            is_active=True
        )
        
        test_db_session.add_all([customer, agent])
        test_db_session.commit()
        test_db_session.refresh(customer)
        test_db_session.refresh(agent)
        
        # Step 2: Customer reports technical issue
        problem_conversation = UnifiedChatHistory(
            session_id="tech_session_001",
            user_id=customer.id,
            user_message="My internet has been completely down for 2 hours. I work from home and this is critical for my business. I've tried restarting my router but nothing works!",
            bot_response="I understand this is a critical issue affecting your business. I've tried some basic troubleshooting steps but this appears to need immediate technical support. I'm creating an urgent support ticket for you.",
            tools_used=["bt_website_tool", "create_ticket_tool"],
            sources={"knowledge_base": "connectivity_troubleshooting"},
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(problem_conversation)
        test_db_session.commit()
        test_db_session.refresh(problem_conversation)
        
        # Step 3: AI analyzes conversation and determines ticket needed
        with patch('backend.conversation_to_ticket_utils.SessionLocal', return_value=test_db_session):
            analysis = analyze_conversation_for_ticket(problem_conversation.id)
            
            assert analysis.analysis_result.value == "needs_ticket"
            assert analysis.confidence_score > 0.7
            assert analysis.ticket_metadata.priority == TicketPriority.CRITICAL
            assert analysis.ticket_metadata.category == TicketCategory.TECHNICAL
        
        # Step 4: AI creates support ticket automatically
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            ticket_result = sync_service.create_ticket_from_conversation(problem_conversation.id)
            
            assert ticket_result.success is True
            ticket_id = ticket_result.entity_id
        
        # Step 5: Verify ticket was created correctly
        ticket = test_db_session.query(UnifiedTicket).filter(UnifiedTicket.id == ticket_id).first()
        assert ticket is not None
        assert ticket.customer_id == customer.id
        assert ticket.status == TicketStatus.OPEN
        assert ticket.priority == TicketPriority.CRITICAL
        assert ticket.category == TicketCategory.TECHNICAL
        assert "internet" in ticket.title.lower() or "connectivity" in ticket.title.lower()
        
        # Step 6: Verify conversation is linked to ticket
        updated_conversation = test_db_session.query(UnifiedChatHistory).filter(
            UnifiedChatHistory.id == problem_conversation.id
        ).first()
        assert updated_conversation.ticket_id == ticket_id
        
        # Step 7: Agent receives and takes ownership of ticket
        ticket.assigned_agent_id = agent.id
        ticket.status = TicketStatus.IN_PROGRESS
        test_db_session.commit()
        
        # Step 8: Agent adds initial response
        agent_comment = UnifiedTicketComment(
            ticket_id=ticket.id,
            author_id=agent.id,
            comment="I'm investigating your connectivity issue. I can see from your conversation that you've already tried restarting your router. Let me check your line status and run some diagnostics.",
            content="I'm investigating your connectivity issue. I can see from your conversation that you've already tried restarting your router. Let me check your line status and run some diagnostics.",
            is_internal=False,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(agent_comment)
        
        # Step 9: Record assignment activity
        assignment_activity = UnifiedTicketActivity(
            ticket_id=ticket.id,
            activity_type="assigned",
            description=f"Ticket assigned to {agent.full_name}",
            performed_by_id=agent.id,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(assignment_activity)
        test_db_session.commit()
        
        # Step 10: Agent resolves the issue
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            resolution_result = sync_service.handle_ticket_status_change(
                ticket.id, TicketStatus.RESOLVED, agent.id
            )
            assert resolution_result.success is True
        
        # Step 11: Verify final state
        final_ticket = test_db_session.query(UnifiedTicket).filter(UnifiedTicket.id == ticket_id).first()
        assert final_ticket.status == TicketStatus.RESOLVED
        assert final_ticket.resolved_at is not None
        assert final_ticket.assigned_agent_id == agent.id
        
        # Verify all interactions are recorded
        comments = test_db_session.query(UnifiedTicketComment).filter(
            UnifiedTicketComment.ticket_id == ticket_id
        ).all()
        assert len(comments) >= 1
        
        activities = test_db_session.query(UnifiedTicketActivity).filter(
            UnifiedTicketActivity.ticket_id == ticket_id
        ).all()
        assert len(activities) >= 2  # Assignment + resolution
    
    def test_billing_inquiry_workflow(self, test_db_session, auth_service, sync_service):
        """Test workflow for billing inquiry that needs human review"""
        # Step 1: Create customer and billing agent
        customer = UnifiedUser(
            user_id="billing_customer_001",
            username="billingcustomer",
            email="billing@example.com",
            password_hash=auth_service.hash_password("password"),
            full_name="Billing Customer",
            role=UserRole.CUSTOMER,
            is_active=True
        )
        
        billing_agent = UnifiedUser(
            user_id="billing_agent_001",
            username="billingagent",
            email="billingagent@example.com",
            password_hash=auth_service.hash_password("password"),
            full_name="Billing Agent",
            role=UserRole.AGENT,
            is_admin=True,
            is_active=True
        )
        
        test_db_session.add_all([customer, billing_agent])
        test_db_session.commit()
        test_db_session.refresh(customer)
        test_db_session.refresh(billing_agent)
        
        # Step 2: Customer has billing question
        billing_conversation = UnifiedChatHistory(
            session_id="billing_session_001",
            user_id=customer.id,
            user_message="I have a question about my bill. I was charged £50 extra this month and I don't understand why. Can you help me understand these charges?",
            bot_response="I understand you have concerns about additional charges on your bill. Let me help you with this billing inquiry. I'm creating a support ticket so our billing team can review your account and explain the charges.",
            tools_used=["create_ticket_tool"],
            sources={"knowledge_base": "billing_support"},
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(billing_conversation)
        test_db_session.commit()
        test_db_session.refresh(billing_conversation)
        
        # Step 3: Create billing ticket
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            ticket_result = sync_service.create_ticket_from_conversation(billing_conversation.id)
            assert ticket_result.success is True
            ticket_id = ticket_result.entity_id
        
        # Step 4: Verify billing ticket properties
        ticket = test_db_session.query(UnifiedTicket).filter(UnifiedTicket.id == ticket_id).first()
        assert ticket.category == TicketCategory.BILLING
        assert ticket.priority in [TicketPriority.MEDIUM, TicketPriority.HIGH]
        
        # Step 5: Billing agent reviews and responds
        ticket.assigned_agent_id = billing_agent.id
        test_db_session.commit()
        
        billing_response = UnifiedTicketComment(
            ticket_id=ticket.id,
            author_id=billing_agent.id,
            comment="I've reviewed your account and can see the additional £50 charge. This was for international roaming charges during your trip last month. I'll send you a detailed breakdown via email.",
            content="I've reviewed your account and can see the additional £50 charge. This was for international roaming charges during your trip last month. I'll send you a detailed breakdown via email.",
            is_internal=False,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(billing_response)
        test_db_session.commit()
        
        # Step 6: Customer follow-up conversation
        followup_conversation = UnifiedChatHistory(
            session_id="billing_session_002",
            user_id=customer.id,
            user_message="Thank you for explaining the charges. That makes sense now. Can you help me set up roaming alerts for future trips?",
            bot_response="I'm glad that helped clarify the charges! I can definitely help you set up roaming alerts. Let me add this request to your existing ticket.",
            tools_used=["bt_website_tool"],
            ticket_id=ticket_id,  # Link to existing ticket
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(followup_conversation)
        test_db_session.commit()
        
        # Step 7: Resolve with additional service setup
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            resolution_result = sync_service.handle_ticket_status_change(
                ticket.id, TicketStatus.RESOLVED, billing_agent.id
            )
            assert resolution_result.success is True
        
        # Verify complete workflow
        final_ticket = test_db_session.query(UnifiedTicket).filter(UnifiedTicket.id == ticket_id).first()
        assert final_ticket.status == TicketStatus.RESOLVED
        
        # Verify both conversations are linked
        linked_conversations = test_db_session.query(UnifiedChatHistory).filter(
            UnifiedChatHistory.ticket_id == ticket_id
        ).all()
        assert len(linked_conversations) == 2


class TestAdminWorkflows(EndToEndTestBase):
    """Test admin dashboard workflows"""
    
    def test_admin_user_management_workflow(self, test_db_session, auth_service, test_client):
        """Test admin user management workflow"""
        # Step 1: Create admin user
        admin = UnifiedUser(
            user_id="admin_workflow_001",
            username="adminworkflow",
            email="adminworkflow@example.com",
            password_hash=auth_service.hash_password("admin_password"),
            full_name="Admin Workflow User",
            role=UserRole.ADMIN,
            is_admin=True,
            is_active=True
        )
        test_db_session.add(admin)
        test_db_session.commit()
        test_db_session.refresh(admin)
        
        # Step 2: Admin logs in
        session_token = auth_service.create_user_session(admin, test_db_session)
        jwt_token = auth_service.create_jwt_token(admin)
        
        # Verify admin session
        authenticated_admin = auth_service.get_user_from_session(session_token, test_db_session)
        assert authenticated_admin.username == "adminworkflow"
        assert authenticated_admin.has_permission(Permission.USER_CREATE)
        
        # Step 3: Admin creates new agent user
        new_agent = UnifiedUser(
            user_id="created_agent_001",
            username="createdagent",
            email="createdagent@example.com",
            password_hash=auth_service.hash_password("agent_password"),
            full_name="Created Agent",
            role=UserRole.AGENT,
            is_admin=True,
            is_active=True
        )
        test_db_session.add(new_agent)
        test_db_session.commit()
        test_db_session.refresh(new_agent)
        
        # Step 4: Admin updates user permissions
        assert admin.has_permission(Permission.USER_UPDATE)
        
        # Simulate permission update
        new_agent.role = UserRole.ADMIN
        test_db_session.commit()
        
        # Step 5: Admin views user activity
        # Create some activity for the new agent
        agent_session = auth_service.create_user_session(new_agent, test_db_session)
        
        # Verify admin can see user sessions
        user_sessions = test_db_session.query(UnifiedUserSession).filter(
            UnifiedUserSession.user_id == new_agent.id
        ).all()
        assert len(user_sessions) >= 1
        
        # Step 6: Admin deactivates user
        new_agent.is_active = False
        test_db_session.commit()
        
        # Verify user is deactivated
        updated_agent = test_db_session.query(UnifiedUser).filter(UnifiedUser.id == new_agent.id).first()
        assert updated_agent.is_active is False
    
    def test_admin_ticket_management_workflow(self, test_db_session, auth_service):
        """Test admin ticket management workflow"""
        # Step 1: Create admin, agent, and customer
        admin = UnifiedUser(
            user_id="ticket_admin_001",
            username="ticketadmin",
            email="ticketadmin@example.com",
            password_hash=auth_service.hash_password("password"),
            role=UserRole.ADMIN,
            is_admin=True,
            is_active=True
        )
        
        agent = UnifiedUser(
            user_id="ticket_agent_001",
            username="ticketagent",
            email="ticketagent@example.com",
            password_hash=auth_service.hash_password("password"),
            role=UserRole.AGENT,
            is_admin=True,
            is_active=True
        )
        
        customer = UnifiedUser(
            user_id="ticket_customer_001",
            username="ticketcustomer",
            email="ticketcustomer@example.com",
            password_hash=auth_service.hash_password("password"),
            role=UserRole.CUSTOMER,
            is_active=True
        )
        
        test_db_session.add_all([admin, agent, customer])
        test_db_session.commit()
        test_db_session.refresh(admin)
        test_db_session.refresh(agent)
        test_db_session.refresh(customer)
        
        # Step 2: Admin creates ticket on behalf of customer
        admin_ticket = UnifiedTicket(
            title="Admin Created Ticket",
            description="Ticket created by admin after phone call with customer",
            status=TicketStatus.OPEN,
            priority=TicketPriority.HIGH,
            category=TicketCategory.GENERAL,
            customer_id=customer.id,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(admin_ticket)
        test_db_session.commit()
        test_db_session.refresh(admin_ticket)
        
        # Step 3: Admin assigns ticket to agent
        admin_ticket.assigned_agent_id = agent.id
        
        assignment_activity = UnifiedTicketActivity(
            ticket_id=admin_ticket.id,
            activity_type="assigned",
            description=f"Ticket assigned to {agent.full_name} by admin",
            performed_by_id=admin.id,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(assignment_activity)
        test_db_session.commit()
        
        # Step 4: Admin adds internal note
        internal_note = UnifiedTicketComment(
            ticket_id=admin_ticket.id,
            author_id=admin.id,
            comment="Customer called about this issue. They mentioned it's been ongoing for several days. Priority escalation approved.",
            content="Customer called about this issue. They mentioned it's been ongoing for several days. Priority escalation approved.",
            is_internal=True,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(internal_note)
        test_db_session.commit()
        
        # Step 5: Admin escalates priority
        admin_ticket.priority = TicketPriority.CRITICAL
        
        priority_activity = UnifiedTicketActivity(
            ticket_id=admin_ticket.id,
            activity_type="priority_change",
            description="Priority escalated to Critical by admin",
            performed_by_id=admin.id,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(priority_activity)
        test_db_session.commit()
        
        # Step 6: Verify admin actions
        final_ticket = test_db_session.query(UnifiedTicket).filter(UnifiedTicket.id == admin_ticket.id).first()
        # Verify ticket was created by admin (would need additional tracking field)
        assert final_ticket.assigned_agent_id == agent.id
        assert final_ticket.priority == TicketPriority.CRITICAL
        
        # Verify activities were recorded
        activities = test_db_session.query(UnifiedTicketActivity).filter(
            UnifiedTicketActivity.ticket_id == admin_ticket.id
        ).all()
        assert len(activities) >= 2
        
        # Verify internal comment
        comments = test_db_session.query(UnifiedTicketComment).filter(
            UnifiedTicketComment.ticket_id == admin_ticket.id,
            UnifiedTicketComment.is_internal == True
        ).all()
        assert len(comments) == 1


class TestCrossSystemIntegration(EndToEndTestBase):
    """Test integration between AI agent and admin dashboard systems"""
    
    @pytest.mark.asyncio
    async def test_ai_to_admin_escalation_workflow(self, test_db_session, auth_service, sync_service):
        """Test escalation from AI agent to admin dashboard"""
        # Step 1: Create users
        customer = UnifiedUser(
            user_id="escalation_customer_001",
            username="escalationcustomer",
            email="escalation@example.com",
            password_hash=auth_service.hash_password("password"),
            role=UserRole.CUSTOMER,
            is_active=True
        )
        
        agent = UnifiedUser(
            user_id="escalation_agent_001",
            username="escalationagent",
            email="escalationagent@example.com",
            password_hash=auth_service.hash_password("password"),
            role=UserRole.AGENT,
            is_admin=True,
            is_active=True
        )
        
        test_db_session.add_all([customer, agent])
        test_db_session.commit()
        test_db_session.refresh(customer)
        test_db_session.refresh(agent)
        
        # Step 2: Customer starts with AI agent
        initial_conversation = UnifiedChatHistory(
            session_id="escalation_session_001",
            user_id=customer.id,
            user_message="I need help with my account but your suggestions aren't working. Can I speak to a human?",
            bot_response="I understand you'd like to speak with a human agent. Let me create a support ticket and connect you with our support team.",
            tools_used=["create_ticket_tool"],
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(initial_conversation)
        test_db_session.commit()
        test_db_session.refresh(initial_conversation)
        
        # Step 3: AI creates escalation ticket
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            ticket_result = sync_service.create_ticket_from_conversation(initial_conversation.id)
            assert ticket_result.success is True
            ticket_id = ticket_result.entity_id
        
        # Step 4: Ticket appears in admin dashboard
        ticket = test_db_session.query(UnifiedTicket).filter(UnifiedTicket.id == ticket_id).first()
        assert ticket is not None
        assert ticket.customer_id == customer.id
        
        # Step 5: Agent picks up ticket in admin dashboard
        ticket.assigned_agent_id = agent.id
        ticket.status = TicketStatus.IN_PROGRESS
        test_db_session.commit()
        
        # Step 6: Agent responds through admin dashboard
        agent_response = UnifiedTicketComment(
            ticket_id=ticket.id,
            author_id=agent.id,
            comment="Hi! I'm here to help you with your account. I can see you were working with our AI assistant. Let me take a look at your account and help resolve this issue.",
            content="Hi! I'm here to help you with your account. I can see you were working with our AI assistant. Let me take a look at your account and help resolve this issue.",
            is_internal=False,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(agent_response)
        test_db_session.commit()
        
        # Step 7: Customer continues conversation (could be through AI or direct)
        followup_conversation = UnifiedChatHistory(
            session_id="escalation_session_002",
            user_id=customer.id,
            user_message="Thank you! I'm having trouble accessing my online account. I keep getting an error message.",
            bot_response="I can see you're now connected with our support agent. They'll be able to help you with your account access issue.",
            ticket_id=ticket_id,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(followup_conversation)
        test_db_session.commit()
        
        # Step 8: Agent resolves issue
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            resolution_result = sync_service.handle_ticket_status_change(
                ticket.id, TicketStatus.RESOLVED, agent.id
            )
            assert resolution_result.success is True
        
        # Step 9: Verify complete integration
        final_ticket = test_db_session.query(UnifiedTicket).filter(UnifiedTicket.id == ticket_id).first()
        assert final_ticket.status == TicketStatus.RESOLVED
        
        # Verify all conversations are linked
        linked_conversations = test_db_session.query(UnifiedChatHistory).filter(
            UnifiedChatHistory.ticket_id == ticket_id
        ).all()
        assert len(linked_conversations) >= 2
        
        # Verify agent response exists
        agent_comments = test_db_session.query(UnifiedTicketComment).filter(
            UnifiedTicketComment.ticket_id == ticket_id,
            UnifiedTicketComment.author_id == agent.id
        ).all()
        assert len(agent_comments) >= 1
    
    def test_data_consistency_across_systems(self, test_db_session, auth_service, sync_service):
        """Test data consistency is maintained across AI agent and admin dashboard"""
        # Step 1: Create test data
        customer = UnifiedUser(
            user_id="consistency_customer_001",
            username="consistencycustomer",
            email="consistency@example.com",
            password_hash=auth_service.hash_password("password"),
            role=UserRole.CUSTOMER,
            is_active=True
        )
        test_db_session.add(customer)
        test_db_session.commit()
        test_db_session.refresh(customer)
        
        # Step 2: Create conversation in AI system
        ai_conversation = UnifiedChatHistory(
            session_id="consistency_session_001",
            user_id=customer.id,
            user_message="I have a problem that needs attention",
            bot_response="I'll help you with that problem",
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(ai_conversation)
        test_db_session.commit()
        test_db_session.refresh(ai_conversation)
        
        # Step 3: Create ticket in admin system
        admin_ticket = UnifiedTicket(
            title="Consistency Test Ticket",
            description="Testing data consistency",
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            category=TicketCategory.GENERAL,
            customer_id=customer.id,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(admin_ticket)
        test_db_session.commit()
        test_db_session.refresh(admin_ticket)
        
        # Step 4: Link conversation to ticket
        ai_conversation.ticket_id = admin_ticket.id
        test_db_session.commit()
        
        # Step 5: Update ticket status through sync service
        with patch('backend.data_sync_service.SessionLocal', return_value=test_db_session):
            sync_result = sync_service.handle_ticket_status_change(
                admin_ticket.id, TicketStatus.IN_PROGRESS, customer.id
            )
            assert sync_result.success is True
        
        # Step 6: Verify consistency
        # Check ticket status was updated
        updated_ticket = test_db_session.query(UnifiedTicket).filter(UnifiedTicket.id == admin_ticket.id).first()
        assert updated_ticket.status == TicketStatus.IN_PROGRESS
        
        # Check conversation is still linked
        updated_conversation = test_db_session.query(UnifiedChatHistory).filter(
            UnifiedChatHistory.id == ai_conversation.id
        ).first()
        assert updated_conversation.ticket_id == admin_ticket.id
        
        # Check activity was recorded
        activities = test_db_session.query(UnifiedTicketActivity).filter(
            UnifiedTicketActivity.ticket_id == admin_ticket.id
        ).all()
        assert len(activities) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])