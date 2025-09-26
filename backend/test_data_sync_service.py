"""
Test suite for Data Synchronization Service

Tests for real-time sync between AI agent conversations and support tickets,
background tasks for data consistency checks, and conversation-to-ticket utilities.

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os

from backend.database import Base
from backend.unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedChatHistory, UnifiedTicketComment,
    UnifiedTicketActivity, TicketStatus, TicketPriority, TicketCategory, UserRole
)
from backend.data_sync_service import (
    DataSyncService, SyncResult, ConsistencyCheckResult, SyncEvent, SyncEventType
)
from backend.conversation_to_ticket_utils import (
    ConversationAnalyzer, ConversationAnalysisResult, analyze_conversation_for_ticket
)
from backend.sync_events import EventDrivenSyncManager, SyncEventData

# Test database setup
@pytest.fixture
def test_db():
    """Create a test database"""
    # Create in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return TestSessionLocal

@pytest.fixture
def sample_user(test_db):
    """Create a sample user for testing"""
    with test_db() as db:
        user = UnifiedUser(
            user_id="test_user_123",
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User",
            role=UserRole.CUSTOMER,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

@pytest.fixture
def sample_conversation(test_db, sample_user):
    """Create a sample conversation for testing"""
    with test_db() as db:
        conversation = UnifiedChatHistory(
            session_id="test_session_123",
            user_id=sample_user.id,
            user_message="I'm having trouble with my internet connection. It keeps dropping out.",
            bot_response="I understand you're experiencing internet connectivity issues. Let me help you troubleshoot this problem.",
            tools_used=["bt_website_tool", "search_tool"],
            sources={"knowledge_base": "connectivity_troubleshooting"},
            created_at=datetime.now(timezone.utc)
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

@pytest.fixture
def sample_ticket(test_db, sample_user):
    """Create a sample ticket for testing"""
    with test_db() as db:
        ticket = UnifiedTicket(
            title="Internet Connection Issues",
            description="Customer experiencing intermittent internet connectivity problems",
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            category=TicketCategory.TECHNICAL,
            customer_id=sample_user.id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket

class TestDataSyncService:
    """Test cases for DataSyncService"""
    
    @pytest.fixture
    def sync_service(self):
        """Create a DataSyncService instance for testing"""
        return DataSyncService()
    
    def test_sync_conversation_to_existing_ticket(self, sync_service, test_db, sample_conversation, sample_ticket):
        """Test syncing conversation to existing ticket"""
        with patch('backend.data_sync_service.SessionLocal', test_db):
            result = sync_service.sync_ai_conversation_to_ticket(
                sample_conversation.id, sample_ticket.id
            )
            
            assert result.success is True
            assert result.entity_id == sample_ticket.id
            assert "conversation_linked" in result.actions_taken
            assert "comment_added" in result.actions_taken
            assert "activity_recorded" in result.actions_taken
    
    def test_sync_conversation_to_new_ticket(self, sync_service, test_db, sample_conversation):
        """Test creating new ticket from conversation"""
        with patch('backend.data_sync_service.SessionLocal', test_db):
            result = sync_service.create_ticket_from_conversation(sample_conversation.id)
            
            assert result.success is True
            assert result.entity_id is not None
            assert "ticket_created" in result.actions_taken
            assert "conversation_linked" in result.actions_taken
    
    def test_sync_nonexistent_conversation(self, sync_service, test_db):
        """Test syncing nonexistent conversation"""
        with patch('backend.data_sync_service.SessionLocal', test_db):
            result = sync_service.sync_ai_conversation_to_ticket(99999)
            
            assert result.success is False
            assert "not found" in result.message.lower()
    
    def test_sync_user_data(self, sync_service, test_db, sample_user):
        """Test user data synchronization"""
        with patch('backend.data_sync_service.SessionLocal', test_db):
            result = sync_service.sync_user_data(sample_user.id)
            
            assert result.success is True
            assert result.entity_id == sample_user.id
    
    def test_handle_ticket_status_change(self, sync_service, test_db, sample_ticket):
        """Test ticket status change handling"""
        with patch('backend.data_sync_service.SessionLocal', test_db):
            result = sync_service.handle_ticket_status_change(
                sample_ticket.id, TicketStatus.RESOLVED, sample_ticket.customer_id
            )
            
            assert result.success is True
            assert "status_updated" in result.actions_taken
            assert "activity_recorded" in result.actions_taken
    
    @pytest.mark.asyncio
    async def test_consistency_check(self, sync_service, test_db, sample_user):
        """Test data consistency check"""
        # Create some inconsistent data
        with test_db() as db:
            # Orphaned conversation (user_id points to non-existent user)
            orphaned_conv = UnifiedChatHistory(
                session_id="orphaned_session",
                user_id=99999,  # Non-existent user
                user_message="Test message",
                bot_response="Test response"
            )
            db.add(orphaned_conv)
            
            # Conversation with invalid ticket link
            invalid_ticket_conv = UnifiedChatHistory(
                session_id="invalid_ticket_session",
                user_id=sample_user.id,
                user_message="Test message",
                bot_response="Test response",
                ticket_id=99999  # Non-existent ticket
            )
            db.add(invalid_ticket_conv)
            
            db.commit()
        
        with patch('backend.data_sync_service.SessionLocal', test_db):
            result = await sync_service.perform_consistency_check()
            
            assert isinstance(result, ConsistencyCheckResult)
            assert result.total_checked > 0
            assert result.inconsistencies_found > 0
            assert result.resolved_count > 0
    
    @pytest.mark.asyncio
    async def test_service_lifecycle(self, sync_service):
        """Test starting and stopping the sync service"""
        # Start service
        await sync_service.start_service()
        assert sync_service.is_running is True
        assert len(sync_service.background_tasks) > 0
        
        # Stop service
        await sync_service.stop_service()
        assert sync_service.is_running is False
        assert len(sync_service.background_tasks) == 0

class TestConversationAnalyzer:
    """Test cases for ConversationAnalyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create a ConversationAnalyzer instance for testing"""
        return ConversationAnalyzer()
    
    def test_analyze_problem_conversation(self, analyzer, test_db, sample_user):
        """Test analyzing conversation that indicates a problem"""
        with test_db() as db:
            conversation = UnifiedChatHistory(
                session_id="problem_session",
                user_id=sample_user.id,
                user_message="I have a serious problem with my internet connection. It's not working at all and I need urgent help!",
                bot_response="I understand you're having connectivity issues. Let me help you troubleshoot this."
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        with patch('backend.conversation_to_ticket_utils.SessionLocal', test_db):
            analysis = analyzer.analyze_conversation(conversation.id)
            
            assert analysis.analysis_result == ConversationAnalysisResult.NEEDS_TICKET
            assert analysis.confidence_score > 0.5
            assert analysis.ticket_metadata is not None
            assert analysis.ticket_metadata.priority == TicketPriority.HIGH
            assert analysis.ticket_metadata.category == TicketCategory.TECHNICAL
    
    def test_analyze_resolved_conversation(self, analyzer, test_db, sample_user):
        """Test analyzing conversation that was resolved"""
        with test_db() as db:
            conversation = UnifiedChatHistory(
                session_id="resolved_session",
                user_id=sample_user.id,
                user_message="I was having trouble with my email setup",
                bot_response="Great! I've helped you configure your email settings. The issue should be resolved now. Please try sending a test email."
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        with patch('backend.conversation_to_ticket_utils.SessionLocal', test_db):
            analysis = analyzer.analyze_conversation(conversation.id)
            
            assert analysis.analysis_result == ConversationAnalysisResult.RESOLVED
            assert analysis.confidence_score > 0.3
    
    def test_analyze_informational_conversation(self, analyzer, test_db, sample_user):
        """Test analyzing informational conversation"""
        with test_db() as db:
            conversation = UnifiedChatHistory(
                session_id="info_session",
                user_id=sample_user.id,
                user_message="What are your internet plans and pricing?",
                bot_response="Here are our current internet plans and pricing options..."
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        with patch('backend.conversation_to_ticket_utils.SessionLocal', test_db):
            analysis = analyzer.analyze_conversation(conversation.id)
            
            assert analysis.analysis_result == ConversationAnalysisResult.INFORMATIONAL
    
    def test_analyze_escalation_conversation(self, analyzer, test_db, sample_user):
        """Test analyzing conversation that needs escalation"""
        with test_db() as db:
            conversation = UnifiedChatHistory(
                session_id="escalation_session",
                user_id=sample_user.id,
                user_message="This is not working! I need to speak to a human agent right now!",
                bot_response="I understand your frustration. Let me connect you with a human support agent."
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        with patch('backend.conversation_to_ticket_utils.SessionLocal', test_db):
            analysis = analyzer.analyze_conversation(conversation.id)
            
            assert analysis.analysis_result == ConversationAnalysisResult.ESCALATION_REQUIRED
            assert analysis.confidence_score > 0.6
    
    def test_entity_extraction(self, analyzer):
        """Test entity extraction from conversation"""
        user_message = "I'm getting ERROR_404 when trying to access my account at https://example.com. My email is test@example.com"
        bot_response = "I see you're having trouble with error 404. Let me help you with that."
        
        entities = analyzer._extract_entities(user_message, bot_response)
        
        assert "error_404" in entities["error_codes"]
        assert "https://example.com" in entities["urls"]
        assert "test@example.com" in entities["email_addresses"]
    
    def test_category_determination(self, analyzer):
        """Test ticket category determination"""
        # Technical issue
        tech_category = analyzer._determine_category("My internet is not working and I'm getting error messages")
        assert tech_category == TicketCategory.TECHNICAL
        
        # Billing issue
        billing_category = analyzer._determine_category("I have a question about my bill and payment")
        assert billing_category == TicketCategory.BILLING
        
        # Account issue
        account_category = analyzer._determine_category("I can't login to my account")
        assert account_category == TicketCategory.ACCOUNT
    
    def test_priority_determination(self, analyzer):
        """Test ticket priority determination"""
        # Critical priority
        critical_priority = analyzer._determine_priority("This is urgent! My business is down!")
        assert critical_priority == TicketPriority.CRITICAL
        
        # High priority
        high_priority = analyzer._determine_priority("This is important and affecting multiple users")
        assert high_priority == TicketPriority.HIGH
        
        # Low priority
        low_priority = analyzer._determine_priority("This is a minor cosmetic issue, no rush")
        assert low_priority == TicketPriority.LOW
    
    def test_sentiment_calculation(self, analyzer):
        """Test sentiment score calculation"""
        # Negative sentiment
        negative_score = analyzer._calculate_sentiment_score("I'm frustrated and angry with this terrible service")
        assert negative_score < 0
        
        # Positive sentiment
        positive_score = analyzer._calculate_sentiment_score("Thank you for the excellent and helpful service")
        assert positive_score > 0
        
        # Neutral sentiment
        neutral_score = analyzer._calculate_sentiment_score("I need information about your services")
        assert -0.2 <= neutral_score <= 0.2

class TestEventDrivenSync:
    """Test cases for EventDrivenSyncManager"""
    
    @pytest.fixture
    def event_manager(self):
        """Create an EventDrivenSyncManager instance for testing"""
        return EventDrivenSyncManager()
    
    def test_event_manager_initialization(self, event_manager):
        """Test event manager initialization"""
        # Mock database operations to avoid actual DB calls
        with patch('backend.sync_events.SessionLocal'):
            event_manager.initialize()
            assert event_manager.is_initialized is True
    
    def test_event_handler_registration(self, event_manager):
        """Test event handler registration"""
        handler_called = False
        
        def test_handler(event_data):
            nonlocal handler_called
            handler_called = True
        
        event_manager.register_event_handler("test_event", test_handler)
        assert "test_event" in event_manager.event_handlers
        assert test_handler in event_manager.event_handlers["test_event"]
    
    @pytest.mark.asyncio
    async def test_event_handler_triggering(self, event_manager):
        """Test event handler triggering"""
        handler_called = False
        received_data = None
        
        async def async_test_handler(event_data):
            nonlocal handler_called, received_data
            handler_called = True
            received_data = event_data
        
        event_manager.register_event_handler("test_event", async_test_handler)
        
        test_data = SyncEventData(
            table_name="test_table",
            operation="insert",
            entity_id=123
        )
        
        await event_manager._trigger_event_handlers("test_event", test_data)
        
        assert handler_called is True
        assert received_data == test_data
    
    @pytest.mark.asyncio
    async def test_conversation_analysis_for_ticket_creation(self, event_manager, test_db, sample_user):
        """Test automatic ticket creation analysis"""
        # Create conversation that should trigger ticket creation
        conversation = UnifiedChatHistory(
            session_id="auto_ticket_session",
            user_id=sample_user.id,
            user_message="I have a serious problem with my service that needs immediate attention. This is affecting my business operations.",
            bot_response="I understand this is urgent. Let me help you with this issue."
        )
        
        should_create = await event_manager._should_create_ticket_from_conversation(conversation)
        assert should_create is True
        
        # Create conversation that should NOT trigger ticket creation
        info_conversation = UnifiedChatHistory(
            session_id="info_session",
            user_id=sample_user.id,
            user_message="What are your service hours?",
            bot_response="Our service hours are 9 AM to 5 PM."
        )
        
        should_not_create = await event_manager._should_create_ticket_from_conversation(info_conversation)
        assert should_not_create is False

class TestIntegrationScenarios:
    """Integration test scenarios"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_conversation_to_ticket_flow(self, test_db):
        """Test complete flow from conversation to ticket creation"""
        # Setup
        sync_service = DataSyncService()
        
        with test_db() as db:
            # Create user
            user = UnifiedUser(
                user_id="integration_user",
                username="integrationuser",
                email="integration@example.com",
                password_hash="hashed_password",
                role=UserRole.CUSTOMER
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Create conversation with problem
            conversation = UnifiedChatHistory(
                session_id="integration_session",
                user_id=user.id,
                user_message="URGENT: My internet has been down for 2 hours and I work from home. This is critical for my business!",
                bot_response="I understand this is urgent. Let me help you troubleshoot your internet connection.",
                tools_used=["bt_website_tool"],
                created_at=datetime.now(timezone.utc)
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        # Test conversation analysis
        with patch('backend.conversation_to_ticket_utils.SessionLocal', test_db):
            analysis = analyze_conversation_for_ticket(conversation.id)
            
            assert analysis.analysis_result == ConversationAnalysisResult.NEEDS_TICKET
            assert analysis.ticket_metadata.priority == TicketPriority.CRITICAL
            assert analysis.ticket_metadata.category == TicketCategory.TECHNICAL
            assert "urgent" in analysis.ticket_metadata.tags
        
        # Test ticket creation
        with patch('backend.data_sync_service.SessionLocal', test_db):
            result = sync_service.create_ticket_from_conversation(conversation.id)
            
            assert result.success is True
            assert result.entity_id is not None
        
        # Verify ticket was created with correct data
        with test_db() as db:
            ticket = db.query(UnifiedTicket).filter(UnifiedTicket.id == result.entity_id).first()
            
            assert ticket is not None
            assert ticket.customer_id == user.id
            assert ticket.status == TicketStatus.OPEN
            assert ticket.priority == TicketPriority.CRITICAL
            assert ticket.category == TicketCategory.TECHNICAL
            
            # Verify conversation is linked to ticket
            updated_conversation = db.query(UnifiedChatHistory).filter(
                UnifiedChatHistory.id == conversation.id
            ).first()
            assert updated_conversation.ticket_id == ticket.id
    
    @pytest.mark.asyncio
    async def test_data_consistency_maintenance(self, test_db):
        """Test data consistency maintenance across systems"""
        sync_service = DataSyncService()
        
        with test_db() as db:
            # Create user
            user = UnifiedUser(
                user_id="consistency_user",
                username="consistencyuser",
                email="consistency@example.com",
                password_hash="hashed_password",
                role=UserRole.CUSTOMER
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Create ticket
            ticket = UnifiedTicket(
                title="Test Ticket",
                description="Test ticket for consistency check",
                status=TicketStatus.OPEN,
                customer_id=user.id
            )
            db.add(ticket)
            db.commit()
            db.refresh(ticket)
            
            # Create conversation linked to ticket
            conversation = UnifiedChatHistory(
                session_id="consistency_session",
                user_id=user.id,
                user_message="Following up on my ticket",
                bot_response="Let me check your ticket status",
                ticket_id=ticket.id
            )
            db.add(conversation)
            db.commit()
        
        # Test ticket status change synchronization
        with patch('backend.data_sync_service.SessionLocal', test_db):
            result = sync_service.handle_ticket_status_change(
                ticket.id, TicketStatus.RESOLVED, user.id
            )
            
            assert result.success is True
        
        # Verify consistency
        with test_db() as db:
            # Check ticket status was updated
            updated_ticket = db.query(UnifiedTicket).filter(UnifiedTicket.id == ticket.id).first()
            assert updated_ticket.status == TicketStatus.RESOLVED
            assert updated_ticket.resolved_at is not None
            
            # Check activity was recorded
            activities = db.query(UnifiedTicketActivity).filter(
                UnifiedTicketActivity.ticket_id == ticket.id
            ).all()
            assert len(activities) > 0
            
            status_change_activity = next(
                (a for a in activities if a.activity_type == "status_change"), None
            )
            assert status_change_activity is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])