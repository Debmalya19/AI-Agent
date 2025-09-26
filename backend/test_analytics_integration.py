"""
Tests for Analytics and Monitoring Integration

Tests the analytics service, routes, and database queries to ensure
unified analytics work correctly across AI agent and admin dashboard systems.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base, get_db
from backend.unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedChatHistory, UnifiedVoiceAnalytics,
    UnifiedCustomerSatisfaction, TicketStatus, TicketPriority, TicketCategory, UserRole
)
from backend.analytics_service import analytics_service
from backend.analytics_queries import analytics_queries
import json
import logging

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_analytics.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger = logging.getLogger(__name__)

class TestAnalyticsService:
    """Test the analytics service functionality"""
    
    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a test database session"""
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            Base.metadata.drop_all(bind=engine)
    
    @pytest.fixture
    def sample_data(self, db_session):
        """Create sample data for testing"""
        # Create test users
        admin_user = UnifiedUser(
            user_id="admin_001",
            username="admin_test",
            email="admin@test.com",
            password_hash="test_hash",
            full_name="Admin Test User",
            role=UserRole.ADMIN,
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
            last_login=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        customer_user = UnifiedUser(
            user_id="customer_001",
            username="customer_test",
            email="customer@test.com",
            password_hash="test_hash",
            full_name="Customer Test User",
            role=UserRole.CUSTOMER,
            created_at=datetime.now(timezone.utc) - timedelta(days=15),
            last_login=datetime.now(timezone.utc) - timedelta(minutes=30)
        )
        
        db_session.add(admin_user)
        db_session.add(customer_user)
        db_session.commit()
        
        # Create test chat history
        chat1 = UnifiedChatHistory(
            user_id=customer_user.id,
            session_id="session_001",
            user_message="I need help with my account",
            bot_response="I can help you with that. What specific issue are you having?",
            tools_used='["account_lookup", "user_verification"]',
            created_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        
        chat2 = UnifiedChatHistory(
            user_id=customer_user.id,
            session_id="session_002", 
            user_message="How do I reset my password?",
            bot_response="I'll guide you through the password reset process.",
            tools_used='["password_reset"]',
            created_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        db_session.add(chat1)
        db_session.add(chat2)
        
        # Create test tickets
        ticket1 = UnifiedTicket(
            customer_id=customer_user.id,
            title="Account Access Issue",
            description="Cannot access my account after password change",
            status=TicketStatus.RESOLVED,
            priority=TicketPriority.HIGH,
            category=TicketCategory.TECHNICAL,
            created_at=datetime.now(timezone.utc) - timedelta(hours=3),
            resolved_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        db_session.add(ticket1)
        
        # Create test voice analytics
        voice1 = UnifiedVoiceAnalytics(
            user_id=customer_user.id,
            action_type="password_reset",
            duration_ms=5000,
            accuracy_score=0.95,
            created_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        db_session.add(voice1)
        
        # Create test satisfaction rating
        satisfaction1 = UnifiedCustomerSatisfaction(
            customer_id=customer_user.id,
            ticket_id=ticket1.id,
            rating=4,
            feedback="Good support, resolved quickly",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=30)
        )
        
        db_session.add(satisfaction1)
        db_session.commit()
        
        return {
            'admin_user': admin_user,
            'customer_user': customer_user,
            'chat1': chat1,
            'chat2': chat2,
            'ticket1': ticket1,
            'voice1': voice1,
            'satisfaction1': satisfaction1
        }
    
    def test_unified_analytics_generation(self, db_session, sample_data):
        """Test unified analytics generation"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=1)
        
        # Override the database session for testing
        original_session = analytics_service.get_unified_analytics.__globals__.get('SessionLocal')
        analytics_service.get_unified_analytics.__globals__['SessionLocal'] = lambda: db_session
        
        try:
            analytics = analytics_service.get_unified_analytics(start_date, end_date)
            
            # Verify analytics structure
            assert analytics.conversation_metrics is not None
            assert analytics.ticket_metrics is not None
            assert analytics.user_engagement is not None
            assert analytics.system_performance is not None
            
            # Verify conversation metrics
            assert analytics.conversation_metrics.total_conversations >= 2
            assert analytics.conversation_metrics.unique_users >= 1
            assert analytics.conversation_metrics.tools_used_count is not None
            
            # Verify ticket metrics
            assert analytics.ticket_metrics.total_tickets >= 1
            assert analytics.ticket_metrics.resolved_tickets >= 1
            
        finally:
            # Restore original session
            if original_session:
                analytics_service.get_unified_analytics.__globals__['SessionLocal'] = original_session
    
    def test_customer_interaction_history(self, db_session, sample_data):
        """Test customer interaction history retrieval"""
        customer_id = sample_data['customer_user'].id
        
        # Override the database session for testing
        original_session = analytics_service.get_customer_interaction_history.__globals__.get('SessionLocal')
        analytics_service.get_customer_interaction_history.__globals__['SessionLocal'] = lambda: db_session
        
        try:
            profile = analytics_service.get_customer_interaction_history(customer_id, limit=10)
            
            # Verify profile structure
            assert 'customer' in profile
            assert 'summary' in profile
            assert 'conversations' in profile
            assert 'tickets' in profile
            assert 'timeline' in profile
            
            # Verify customer data
            assert profile['customer']['id'] == customer_id
            assert profile['customer']['username'] == 'customer_test'
            
            # Verify summary data
            assert profile['summary']['total_conversations'] >= 2
            assert profile['summary']['total_tickets'] >= 1
            
            # Verify conversations
            assert len(profile['conversations']) >= 2
            
            # Verify timeline
            assert len(profile['timeline']) > 0
            
        finally:
            # Restore original session
            if original_session:
                analytics_service.get_customer_interaction_history.__globals__['SessionLocal'] = original_session
    
    def test_ai_conversation_statistics(self, db_session, sample_data):
        """Test AI conversation statistics generation"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=1)
        
        # Override the database session for testing
        original_session = analytics_service.get_ai_agent_conversation_statistics.__globals__.get('SessionLocal')
        analytics_service.get_ai_agent_conversation_statistics.__globals__['SessionLocal'] = lambda: db_session
        
        try:
            stats = analytics_service.get_ai_agent_conversation_statistics(
                start_date, end_date, group_by='day'
            )
            
            # Verify statistics structure
            assert 'period' in stats
            assert 'volume_over_time' in stats
            assert 'tool_usage' in stats
            assert 'success_metrics' in stats
            
            # Verify period data
            assert stats['period']['group_by'] == 'day'
            
            # Verify success metrics
            assert 'total_conversations' in stats['success_metrics']
            assert 'success_rate' in stats['success_metrics']
            
        finally:
            # Restore original session
            if original_session:
                analytics_service.get_ai_agent_conversation_statistics.__globals__['SessionLocal'] = original_session


class TestAnalyticsQueries:
    """Test the analytics database queries"""
    
    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a test database session"""
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            Base.metadata.drop_all(bind=engine)
    
    def test_conversation_volume_query(self, db_session):
        """Test conversation volume query"""
        # Create test data
        user = UnifiedUser(
            user_id="test_user",
            username="test",
            email="test@test.com",
            password_hash="test_hash",
            role=UserRole.CUSTOMER
        )
        db_session.add(user)
        db_session.commit()
        
        chat = UnifiedChatHistory(
            user_id=user.id,
            session_id="test_session",
            user_message="Test message",
            bot_response="Test response",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(chat)
        db_session.commit()
        
        # Test query
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=1)
        
        results = analytics_queries.get_conversation_volume_by_period(
            db_session, start_date, end_date, 'day'
        )
        
        assert len(results) >= 1
        assert 'total_conversations' in results[0]
        assert 'unique_users' in results[0]
    
    def test_ticket_performance_query(self, db_session):
        """Test ticket performance metrics query"""
        # Create test data
        user = UnifiedUser(
            user_id="test_user",
            username="test",
            email="test@test.com",
            password_hash="test_hash",
            role=UserRole.CUSTOMER
        )
        db_session.add(user)
        db_session.commit()
        
        ticket = UnifiedTicket(
            customer_id=user.id,
            title="Test Ticket",
            description="Test description",
            status=TicketStatus.RESOLVED,
            priority=TicketPriority.MEDIUM,
            category=TicketCategory.GENERAL,
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            resolved_at=datetime.now(timezone.utc)
        )
        db_session.add(ticket)
        db_session.commit()
        
        # Test query
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=1)
        
        results = analytics_queries.get_ticket_performance_metrics(
            db_session, start_date, end_date
        )
        
        assert 'total_tickets' in results
        assert 'resolved_tickets' in results
        assert 'resolution_metrics' in results


class TestAnalyticsRoutes:
    """Test the analytics API routes"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi import FastAPI
        from backend.analytics_routes import analytics_router
        
        app = FastAPI()
        app.include_router(analytics_router)
        
        # Override database dependency
        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()
        
        app.dependency_overrides[get_db] = override_get_db
        
        from fastapi.testclient import TestClient
        return TestClient(app)
    
    def test_unified_dashboard_endpoint_unauthorized(self, client):
        """Test unified dashboard endpoint without authentication"""
        response = client.get("/api/analytics/unified-dashboard")
        # Should require authentication - could be 401 (no auth) or 403 (insufficient permissions)
        assert response.status_code in [401, 403]
    
    def test_ai_conversations_endpoint_unauthorized(self, client):
        """Test AI conversations endpoint without authentication"""
        response = client.get("/api/analytics/ai-conversations")
        # Should require authentication - could be 401 (no auth) or 403 (insufficient permissions)
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])