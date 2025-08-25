"""
Integration tests for memory layer functionality in the main application.
Tests the integration between FastAPI endpoints and memory layer components.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the main application
from database import Base, get_db
from models import User, UserSession
from memory_models import ConversationEntry, ContextEntry, ToolRecommendation
from memory_layer_manager import MemoryLayerManager, MemoryStats, CleanupResult


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_memory_integration.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Import after setting up database override
from main import app, memory_manager, memory_config

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def setup_test_db():
    """Set up test database"""
    # Import all models to ensure they're registered
    from models import User, UserSession, ChatHistory, KnowledgeEntry, SupportIntent, SupportResponse
    from memory_models import EnhancedChatHistory, MemoryContextCache, ToolUsageMetrics, ConversationSummary, MemoryHealthMetrics
    
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)

@pytest.fixture
def test_user_session(setup_test_db):
    """Create test user and session"""
    db = TestingSessionLocal()
    
    try:
        # Create test user
        test_user = User(
            user_id="test_user_123",
            username="testuser",
            email="test@example.com",
            password_hash="test_hash",
            full_name="Test User"
        )
        db.add(test_user)
        db.commit()
        
        # Create test session
        session_token = "test_session_token_123"
        test_session = UserSession(
            session_id=session_token,
            token_hash="test_token_hash",
            user_id="test_user_123",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            last_accessed=datetime.utcnow(),
            is_active=True
        )
        db.add(test_session)
        db.commit()
        
        yield {
            "user_id": "test_user_123",
            "session_token": session_token
        }
        
    finally:
        # Cleanup
        db.query(UserSession).filter(UserSession.session_id == session_token).delete()
        db.query(User).filter(User.user_id == "test_user_123").delete()
        db.commit()
        db.close()

@pytest.fixture
def mock_memory_manager():
    """Mock memory manager for testing"""
    mock_manager = Mock(spec=MemoryLayerManager)
    
    # Mock methods with realistic return values
    mock_manager.retrieve_context.return_value = [
        ContextEntry(
            content="Previous conversation about plans",
            source="conversation_1",
            relevance_score=0.8,
            context_type="conversation",
            timestamp=datetime.now(timezone.utc),
            metadata={"session_id": "test_session"}
        )
    ]
    
    mock_manager.analyze_tool_usage.return_value = ToolRecommendation(
        tool_name="search_tool",
        confidence_score=0.9,
        reason="High success rate for similar queries",
        expected_performance=0.85
    )
    
    mock_manager.store_conversation.return_value = True
    
    mock_stats = MemoryStats()
    mock_stats.total_conversations = 100
    mock_stats.total_context_entries = 250
    mock_stats.cache_hit_rate = 0.75
    mock_stats.health_score = 0.95
    mock_manager.get_memory_stats.return_value = mock_stats
    
    mock_cleanup = CleanupResult()
    mock_cleanup.conversations_cleaned = 10
    mock_cleanup.context_entries_cleaned = 25
    mock_cleanup.cleanup_duration = 2.5
    mock_manager.cleanup_expired_data.return_value = mock_cleanup
    
    mock_manager.get_user_conversation_history.return_value = [
        ConversationEntry(
            session_id="test_session",
            user_id="test_user_123",
            user_message="What are your plans?",
            bot_response="We offer various telecom plans...",
            tools_used=["bt_plans_tool"],
            tool_performance={"bt_plans_tool": 0.9},
            context_used=["previous_context"],
            response_quality_score=0.85,
            timestamp=datetime.now(timezone.utc)
        )
    ]
    
    mock_manager.record_health_metric.return_value = True
    
    return mock_manager


class TestMemoryIntegration:
    """Test memory layer integration with FastAPI application"""
    
    def test_chat_endpoint_with_memory_integration(self, client, test_user_session, mock_memory_manager):
        """Test chat endpoint integrates with memory layer"""
        with patch('main.memory_manager', mock_memory_manager):
            with patch('main.agent_executor') as mock_agent:
                # Mock agent response
                mock_agent.invoke.return_value = {
                    'output': 'Here are our available plans...',
                    'intermediate_steps': []
                }
                
                # Make chat request
                response = client.post(
                    "/chat",
                    json={"query": "What plans do you offer?"},
                    cookies={"session_token": test_user_session["session_token"]}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "summary" in data
                assert data["topic"] == "What plans do you offer?"
                
                # Verify memory manager methods were called
                mock_memory_manager.retrieve_context.assert_called_once()
                mock_memory_manager.store_conversation.assert_called_once()
                mock_memory_manager.record_health_metric.assert_called()
    
    def test_chat_endpoint_uses_context(self, client, test_user_session, mock_memory_manager):
        """Test that chat endpoint uses retrieved context"""
        with patch('main.memory_manager', mock_memory_manager):
            with patch('main.agent_executor') as mock_agent:
                mock_agent.invoke.return_value = {
                    'output': 'Based on our previous conversation about plans...',
                    'intermediate_steps': []
                }
                
                response = client.post(
                    "/chat",
                    json={"query": "Tell me more about those plans"},
                    cookies={"session_token": test_user_session["session_token"]}
                )
                
                assert response.status_code == 200
                
                # Verify context was retrieved for the user
                mock_memory_manager.retrieve_context.assert_called_with(
                    query="Tell me more about those plans",
                    user_id=test_user_session["user_id"],
                    limit=10
                )
    
    def test_chat_endpoint_stores_conversation(self, client, test_user_session, mock_memory_manager):
        """Test that chat endpoint stores conversation in memory"""
        with patch('main.memory_manager', mock_memory_manager):
            with patch('main.agent_executor') as mock_agent:
                mock_agent.invoke.return_value = {
                    'output': 'Here is the information you requested...',
                    'intermediate_steps': []
                }
                
                response = client.post(
                    "/chat",
                    json={"query": "I need help with my account"},
                    cookies={"session_token": test_user_session["session_token"]}
                )
                
                assert response.status_code == 200
                
                # Verify conversation was stored
                mock_memory_manager.store_conversation.assert_called_once()
                
                # Check the stored conversation details
                call_args = mock_memory_manager.store_conversation.call_args[0][0]
                assert isinstance(call_args, ConversationEntry)
                assert call_args.user_id == test_user_session["user_id"]
                assert call_args.user_message == "I need help with my account"
                assert "Here is the information you requested..." in call_args.bot_response
    
    def test_chat_endpoint_handles_agent_error(self, client, test_user_session, mock_memory_manager):
        """Test chat endpoint handles agent execution errors gracefully"""
        with patch('main.memory_manager', mock_memory_manager):
            with patch('main.agent_executor') as mock_agent:
                # Mock agent to raise an error
                mock_agent.invoke.side_effect = Exception("Agent execution failed")
                
                response = client.post(
                    "/chat",
                    json={"query": "This will cause an error"},
                    cookies={"session_token": test_user_session["session_token"]}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "error" in data["summary"].lower()
                
                # Verify failed conversation was still stored
                mock_memory_manager.store_conversation.assert_called_once()
                
                # Check that the stored conversation has quality score 0.0
                call_args = mock_memory_manager.store_conversation.call_args[0][0]
                assert call_args.response_quality_score == 0.0
    
    def test_memory_stats_endpoint(self, client, test_user_session, mock_memory_manager):
        """Test memory statistics endpoint"""
        with patch('main.memory_manager', mock_memory_manager):
            response = client.get(
                "/memory/stats",
                cookies={"session_token": test_user_session["session_token"]}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "success"
            assert "memory_stats" in data
            assert "config_summary" in data
            
            # Check memory stats structure
            stats = data["memory_stats"]
            assert "total_conversations" in stats
            assert "total_context_entries" in stats
            assert "cache_hit_rate" in stats
            assert "health_score" in stats
            
            # Check config summary
            config = data["config_summary"]
            assert "retention_days" in config
            assert "cache_enabled" in config
            assert "database_enabled" in config
    
    def test_memory_stats_unauthorized(self, client):
        """Test memory stats endpoint requires authentication"""
        response = client.get("/memory/stats")
        assert response.status_code == 401
    
    def test_user_history_endpoint(self, client, test_user_session, mock_memory_manager):
        """Test user conversation history endpoint"""
        with patch('main.memory_manager', mock_memory_manager):
            response = client.get(
                "/memory/user-history?limit=10",
                cookies={"session_token": test_user_session["session_token"]}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "success"
            assert data["user_id"] == test_user_session["user_id"]
            assert "conversations" in data
            assert "conversation_count" in data
            
            # Check conversation structure
            if data["conversations"]:
                conv = data["conversations"][0]
                assert "user_message" in conv
                assert "bot_response" in conv
                assert "tools_used" in conv
                assert "response_quality_score" in conv
                assert "timestamp" in conv
    
    def test_memory_cleanup_endpoint(self, client, test_user_session, mock_memory_manager):
        """Test manual memory cleanup endpoint"""
        with patch('main.memory_manager', mock_memory_manager):
            response = client.post(
                "/memory/cleanup",
                cookies={"session_token": test_user_session["session_token"]}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "success"
            assert "cleanup task started" in data["message"].lower()
    
    def test_memory_health_endpoint(self, client, mock_memory_manager):
        """Test memory health endpoint"""
        with patch('main.memory_manager', mock_memory_manager):
            response = client.get("/memory/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "status" in data
            assert "health_score" in data
            assert "error_count" in data
            assert "average_response_time" in data
            assert "timestamp" in data
            
            # Should be healthy with mock data
            assert data["status"] == "healthy"
            assert data["health_score"] == 0.95
    
    def test_memory_health_degraded_status(self, client):
        """Test memory health endpoint with degraded status"""
        mock_manager = Mock(spec=MemoryLayerManager)
        mock_stats = MemoryStats()
        mock_stats.error_count = 15  # High error count
        mock_stats.health_score = 0.7  # Low health score
        mock_stats.average_response_time = 6.0  # High response time
        mock_manager.get_memory_stats.return_value = mock_stats
        
        with patch('main.memory_manager', mock_manager):
            response = client.get("/memory/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "degraded"
            assert len(data["issues"]) > 0
            assert any("error count" in issue.lower() for issue in data["issues"])
    
    def test_memory_health_unhealthy_status(self, client):
        """Test memory health endpoint with unhealthy status"""
        mock_manager = Mock(spec=MemoryLayerManager)
        mock_stats = MemoryStats()
        mock_stats.error_count = 60  # Very high error count
        mock_stats.health_score = 0.3  # Very low health score
        mock_manager.get_memory_stats.return_value = mock_stats
        
        with patch('main.memory_manager', mock_manager):
            response = client.get("/memory/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "unhealthy"
    
    def test_memory_health_error_handling(self, client):
        """Test memory health endpoint error handling"""
        mock_manager = Mock(spec=MemoryLayerManager)
        mock_manager.get_memory_stats.side_effect = Exception("Memory system error")
        
        with patch('main.memory_manager', mock_manager):
            response = client.get("/memory/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "unhealthy"
            assert "error" in data
    
    def test_chat_endpoint_performance_tracking(self, client, test_user_session, mock_memory_manager):
        """Test that chat endpoint tracks performance metrics"""
        with patch('main.memory_manager', mock_memory_manager):
            with patch('main.agent_executor') as mock_agent:
                mock_agent.invoke.return_value = {
                    'output': 'Quick response',
                    'intermediate_steps': []
                }
                
                response = client.post(
                    "/chat",
                    json={"query": "Quick question"},
                    cookies={"session_token": test_user_session["session_token"]}
                )
                
                assert response.status_code == 200
                
                # Verify performance metric was recorded
                mock_memory_manager.record_health_metric.assert_called()
                
                # Check that response time metric was recorded
                calls = mock_memory_manager.record_health_metric.call_args_list
                response_time_call = None
                for call in calls:
                    if call[0][0] == "chat_response_time":
                        response_time_call = call
                        break
                
                assert response_time_call is not None
                assert response_time_call[0][1] > 0  # Response time should be positive
                assert response_time_call[0][2] == "seconds"
                assert response_time_call[0][3] == "performance"
    
    def test_chat_endpoint_quality_scoring(self, client, test_user_session, mock_memory_manager):
        """Test that chat endpoint calculates response quality scores"""
        with patch('main.memory_manager', mock_memory_manager):
            with patch('main.agent_executor') as mock_agent:
                mock_agent.invoke.return_value = {
                    'output': 'This is a comprehensive response with detailed information about your query.',
                    'intermediate_steps': [
                        (Mock(tool="search_tool"), "search result"),
                        (Mock(tool="wiki_tool"), "wiki result")
                    ]
                }
                
                response = client.post(
                    "/chat",
                    json={"query": "Detailed question requiring tools"},
                    cookies={"session_token": test_user_session["session_token"]}
                )
                
                assert response.status_code == 200
                
                # Check stored conversation quality score
                call_args = mock_memory_manager.store_conversation.call_args[0][0]
                assert call_args.response_quality_score > 0.0
                assert call_args.response_quality_score <= 1.0
                
                # Should have bonus for context and tools
                assert len(call_args.tools_used) > 0  # Tools were used
    
    @pytest.mark.asyncio
    async def test_background_cleanup_task(self, mock_memory_manager):
        """Test background cleanup task functionality"""
        with patch('main.memory_manager', mock_memory_manager):
            with patch('main.memory_config') as mock_config:
                mock_config.retention.cleanup_interval_hours = 0.001  # Very short interval for testing
                mock_config.retention.auto_cleanup_enabled = True
                
                # Import and run cleanup task
                from main import cleanup_memory_task
                
                # Run task once (it's an infinite loop, so we'll patch sleep)
                with patch('asyncio.sleep', side_effect=asyncio.CancelledError):
                    try:
                        await cleanup_memory_task()
                    except asyncio.CancelledError:
                        pass  # Expected when we cancel the sleep
                
                # Verify cleanup was called
                mock_memory_manager.cleanup_expired_data.assert_called_once()
                mock_memory_manager.record_health_metric.assert_called()


class TestMemoryIntegrationEdgeCases:
    """Test edge cases and error scenarios for memory integration"""
    
    def test_chat_without_session_token(self, client):
        """Test chat endpoint without session token"""
        response = client.post("/chat", json={"query": "Test query"})
        assert response.status_code == 401
    
    def test_chat_with_invalid_session(self, client):
        """Test chat endpoint with invalid session token"""
        response = client.post(
            "/chat",
            json={"query": "Test query"},
            cookies={"session_token": "invalid_token"}
        )
        assert response.status_code == 401
    
    def test_memory_stats_with_memory_error(self, client, test_user_session):
        """Test memory stats endpoint when memory manager fails"""
        mock_manager = Mock(spec=MemoryLayerManager)
        mock_manager.get_memory_stats.side_effect = Exception("Memory error")
        
        with patch('main.memory_manager', mock_manager):
            response = client.get(
                "/memory/stats",
                cookies={"session_token": test_user_session["session_token"]}
            )
            
            assert response.status_code == 500
    
    def test_user_history_with_memory_error(self, client, test_user_session):
        """Test user history endpoint when memory manager fails"""
        mock_manager = Mock(spec=MemoryLayerManager)
        mock_manager.get_user_conversation_history.side_effect = Exception("Memory error")
        
        with patch('main.memory_manager', mock_manager):
            response = client.get(
                "/memory/user-history",
                cookies={"session_token": test_user_session["session_token"]}
            )
            
            assert response.status_code == 500
    
    def test_chat_with_memory_storage_failure(self, client, test_user_session):
        """Test chat endpoint when memory storage fails"""
        mock_manager = Mock(spec=MemoryLayerManager)
        mock_manager.retrieve_context.return_value = []
        mock_manager.analyze_tool_usage.return_value = None
        mock_manager.store_conversation.return_value = False  # Storage fails
        mock_manager.record_health_metric.return_value = True
        
        with patch('main.memory_manager', mock_manager):
            with patch('main.agent_executor') as mock_agent:
                mock_agent.invoke.return_value = {
                    'output': 'Response despite storage failure',
                    'intermediate_steps': []
                }
                
                response = client.post(
                    "/chat",
                    json={"query": "Test query"},
                    cookies={"session_token": test_user_session["session_token"]}
                )
                
                # Should still return successful response
                assert response.status_code == 200
                
                # But should log warning about storage failure
                mock_manager.store_conversation.assert_called_once()
    
    def test_chat_with_context_retrieval_failure(self, client, test_user_session):
        """Test chat endpoint when context retrieval fails"""
        mock_manager = Mock(spec=MemoryLayerManager)
        mock_manager.retrieve_context.side_effect = Exception("Context retrieval error")
        mock_manager.analyze_tool_usage.return_value = None
        mock_manager.store_conversation.return_value = True
        mock_manager.record_health_metric.return_value = True
        
        with patch('main.memory_manager', mock_manager):
            with patch('main.agent_executor') as mock_agent:
                mock_agent.invoke.return_value = {
                    'output': 'Response without context',
                    'intermediate_steps': []
                }
                
                response = client.post(
                    "/chat",
                    json={"query": "Test query"},
                    cookies={"session_token": test_user_session["session_token"]}
                )
                
                # Should still work without context
                assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])