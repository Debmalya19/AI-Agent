"""
Simplified integration tests for memory layer functionality.
Tests the core integration without complex database setup.
"""

import pytest
import json
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Mock the database dependencies before importing main
with patch('database.SessionLocal'), patch('database.get_db'):
    from main import app, memory_manager, memory_config

from memory_models import ConversationEntry, ContextEntry, ToolRecommendation
from memory_layer_manager import MemoryLayerManager, MemoryStats, CleanupResult
from datetime import datetime, timezone


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


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
    
    mock_manager.get_user_conversation_history.return_value = []
    mock_manager.record_health_metric.return_value = True
    
    return mock_manager


class TestMemoryIntegrationSimple:
    """Test memory layer integration with mocked dependencies"""
    
    def test_memory_health_endpoint(self, client, mock_memory_manager):
        """Test memory health endpoint"""
        with patch('main.memory_manager', mock_memory_manager):
            response = client.get("/memory/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "status" in data
            assert "health_score" in data
            assert "error_count" in data
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
    
    def test_memory_stats_unauthorized(self, client):
        """Test memory stats endpoint requires authentication"""
        response = client.get("/memory/stats")
        assert response.status_code == 401
    
    def test_memory_stats_endpoint_with_mock_session(self, client, mock_memory_manager):
        """Test memory statistics endpoint with mocked session validation"""
        
        # Mock the session validation to return a valid session
        def mock_session_query(*args, **kwargs):
            mock_session = Mock()
            mock_session.filter.return_value.first.return_value = Mock(user_id="test_user")
            return mock_session
        
        with patch('main.memory_manager', mock_memory_manager):
            with patch('main.SessionLocal') as mock_session_local:
                mock_db = Mock()
                mock_db.query = mock_session_query
                mock_session_local.return_value.__enter__.return_value = mock_db
                
                response = client.get(
                    "/memory/stats",
                    cookies={"session_token": "valid_token"}
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
    
    def test_user_history_endpoint_with_mock_session(self, client, mock_memory_manager):
        """Test user conversation history endpoint with mocked session"""
        
        # Mock conversation history
        mock_memory_manager.get_user_conversation_history.return_value = [
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
        
        def mock_session_query(*args, **kwargs):
            mock_session = Mock()
            mock_session.filter.return_value.first.return_value = Mock(user_id="test_user_123")
            return mock_session
        
        with patch('main.memory_manager', mock_memory_manager):
            with patch('main.SessionLocal') as mock_session_local:
                mock_db = Mock()
                mock_db.query = mock_session_query
                mock_session_local.return_value.__enter__.return_value = mock_db
                
                response = client.get(
                    "/memory/user-history?limit=10",
                    cookies={"session_token": "valid_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["status"] == "success"
                assert data["user_id"] == "test_user_123"
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
    
    def test_memory_cleanup_endpoint_with_mock_session(self, client, mock_memory_manager):
        """Test manual memory cleanup endpoint with mocked session"""
        
        def mock_session_query(*args, **kwargs):
            mock_session = Mock()
            mock_session.filter.return_value.first.return_value = Mock(user_id="test_user")
            return mock_session
        
        with patch('main.memory_manager', mock_memory_manager):
            with patch('main.SessionLocal') as mock_session_local:
                mock_db = Mock()
                mock_db.query = mock_session_query
                mock_session_local.return_value.__enter__.return_value = mock_db
                
                response = client.post(
                    "/memory/cleanup",
                    cookies={"session_token": "valid_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["status"] == "success"
                assert "cleanup task started" in data["message"].lower()
    
    def test_chat_endpoint_unauthorized(self, client):
        """Test chat endpoint without session token"""
        response = client.post("/chat", json={"query": "Test query"})
        assert response.status_code == 401
    
    def test_chat_endpoint_with_invalid_session(self, client):
        """Test chat endpoint with invalid session token"""
        
        def mock_session_query(*args, **kwargs):
            mock_session = Mock()
            mock_session.filter.return_value.first.return_value = None  # No session found
            return mock_session
        
        with patch('main.SessionLocal') as mock_session_local:
            mock_db = Mock()
            mock_db.query = mock_session_query
            mock_session_local.return_value.__enter__.return_value = mock_db
            
            response = client.post(
                "/chat",
                json={"query": "Test query"},
                cookies={"session_token": "invalid_token"}
            )
            assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])