"""
Integration tests for intelligent chat UI API endpoints.
Tests backward compatibility and enhanced functionality.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from fastapi.testclient import TestClient

# Import the main app
from main import app, intelligent_chat_manager, memory_manager

# Import intelligent chat models
from intelligent_chat.models import (
    ChatResponse as IntelligentChatResponse,
    ContentType,
    UIState,
    LoadingIndicator,
    LoadingState,
    ErrorState,
    ErrorSeverity
)


class TestIntelligentChatAPIIntegration:
    """Test intelligent chat UI integration with FastAPI endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_session_token(self):
        """Mock session token for authentication."""
        return "test_session_token_123"
    
    @pytest.fixture
    def mock_user_session(self):
        """Mock user session data."""
        return Mock(
            session_id="test_session_token_123",
            user_id="test_user_123",
            is_active=True
        )
    
    @pytest.fixture
    def sample_intelligent_response(self):
        """Sample intelligent chat response."""
        return IntelligentChatResponse(
            content="This is a test response from intelligent chat manager.",
            content_type=ContentType.PLAIN_TEXT,
            tools_used=["ContextRetriever", "SupportKnowledgeBase"],
            context_used=["conversation_history", "user_preferences"],
            confidence_score=0.85,
            execution_time=1.23,
            ui_hints={
                "session_id": "test_session_token_123",
                "context_count": 2,
                "tools_count": 2
            },
            timestamp=datetime.now()
        )
    
    def test_chat_endpoint_with_intelligent_manager_success(
        self, client, mock_session_token, mock_user_session, sample_intelligent_response
    ):
        """Test chat endpoint using intelligent chat manager successfully."""
        
        # Mock database session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
            
            # Mock intelligent chat manager
            with patch.object(intelligent_chat_manager, 'process_message', new_callable=AsyncMock) as mock_process:
                mock_process.return_value = sample_intelligent_response
                
                # Mock UI state update
                mock_ui_state = UIState()
                mock_ui_state.loading_indicators = [
                    LoadingIndicator(
                        tool_name="ContextRetriever",
                        state=LoadingState.COMPLETED,
                        progress=1.0,
                        message="Context retrieval completed"
                    )
                ]
                
                with patch.object(intelligent_chat_manager, 'update_ui_state') as mock_ui_update:
                    mock_ui_update.return_value = mock_ui_state
                    
                    # Make request
                    response = client.post(
                        "/chat",
                        json={"query": "What are BT's support hours?"},
                        cookies={"session_token": mock_session_token}
                    )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check backward compatibility fields
        assert data["topic"] == "What are BT's support hours?"
        assert data["summary"] == sample_intelligent_response.content
        assert data["tools_used"] == sample_intelligent_response.tools_used
        assert data["sources"] == sample_intelligent_response.context_used
        
        # Check enhanced fields
        assert data["confidence_score"] == sample_intelligent_response.confidence_score
        assert data["execution_time"] == sample_intelligent_response.execution_time
        assert data["content_type"] == sample_intelligent_response.content_type.value
        assert data["ui_state"] is not None
        assert len(data["ui_state"]["loading_indicators"]) == 1
        assert data["ui_state"]["loading_indicators"][0]["tool_name"] == "ContextRetriever"
        
        # Verify intelligent chat manager was called
        mock_process.assert_called_once_with(
            message="What are BT's support hours?",
            user_id="test_user_123",
            session_id=mock_session_token
        )
    
    def test_chat_endpoint_fallback_to_legacy(
        self, client, mock_session_token, mock_user_session
    ):
        """Test chat endpoint falls back to legacy agent executor when intelligent manager fails."""
        
        # Mock database session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
            
            # Mock intelligent chat manager to fail
            with patch.object(intelligent_chat_manager, 'process_message', new_callable=AsyncMock) as mock_process:
                mock_process.side_effect = Exception("Intelligent manager failed")
                
                # Mock legacy components
                with patch('main.agent_executor') as mock_agent:
                    mock_agent.invoke.return_value = {
                        'output': 'Legacy response from agent executor'
                    }
                    
                    with patch('main.memory_manager') as mock_memory:
                        mock_memory.retrieve_context.return_value = []
                        mock_memory.analyze_tool_usage.return_value = None
                        mock_memory.store_conversation.return_value = True
                        mock_memory.record_health_metric.return_value = None
                        
                        # Make request
                        response = client.post(
                            "/chat",
                            json={"query": "Test fallback query"},
                            cookies={"session_token": mock_session_token}
                        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check that legacy response is returned
        assert data["topic"] == "Test fallback query"
        assert data["summary"] == "Legacy response from agent executor"
        
        # Verify intelligent manager was attempted first
        mock_process.assert_called_once()
    
    def test_chat_endpoint_unauthorized_no_token(self, client):
        """Test chat endpoint returns 401 when no session token provided."""
        response = client.post(
            "/chat",
            json={"query": "Test query"}
        )
        
        assert response.status_code == 401
        assert "Unauthorized" in response.json()["detail"]
    
    def test_chat_endpoint_invalid_session(self, client, mock_session_token):
        """Test chat endpoint returns 401 when session is invalid."""
        
        # Mock database to return no session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
            
            response = client.post(
                "/chat",
                json={"query": "Test query"},
                cookies={"session_token": mock_session_token}
            )
        
        assert response.status_code == 401
        assert "Invalid session" in response.json()["detail"]
    
    def test_chat_endpoint_with_error_ui_state(
        self, client, mock_session_token, mock_user_session
    ):
        """Test chat endpoint includes error UI state when processing fails."""
        
        # Create error response
        error_response = IntelligentChatResponse(
            content="I encountered an error processing your request.",
            content_type=ContentType.ERROR_MESSAGE,
            tools_used=[],
            context_used=[],
            confidence_score=0.0,
            execution_time=0.5,
            ui_hints={"error": True},
            timestamp=datetime.now()
        )
        
        # Mock database session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
            
            # Mock intelligent chat manager to return error response
            with patch.object(intelligent_chat_manager, 'process_message', new_callable=AsyncMock) as mock_process:
                mock_process.return_value = error_response
                
                # Mock UI state with error
                mock_ui_state = UIState()
                mock_ui_state.error_states = [
                    ErrorState(
                        error_type="processing_error",
                        message="Failed to process message",
                        severity=ErrorSeverity.ERROR,
                        recovery_actions=["retry", "simplify_query"]
                    )
                ]
                
                with patch.object(intelligent_chat_manager, 'update_ui_state') as mock_ui_update:
                    mock_ui_update.return_value = mock_ui_state
                    
                    # Make request
                    response = client.post(
                        "/chat",
                        json={"query": "Problematic query"},
                        cookies={"session_token": mock_session_token}
                    )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check error handling
        assert data["content_type"] == "error_message"
        assert data["confidence_score"] == 0.0
        assert data["ui_state"] is not None
        assert len(data["ui_state"]["error_states"]) == 1
        assert data["ui_state"]["error_states"][0]["error_type"] == "processing_error"
        assert "retry" in data["ui_state"]["error_states"][0]["recovery_actions"]
    
    def test_chat_endpoint_performance_tracking(
        self, client, mock_session_token, mock_user_session, sample_intelligent_response
    ):
        """Test that chat endpoint properly tracks performance metrics."""
        
        # Mock database session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
            
            # Mock intelligent chat manager
            with patch.object(intelligent_chat_manager, 'process_message', new_callable=AsyncMock) as mock_process:
                mock_process.return_value = sample_intelligent_response
                
                with patch.object(intelligent_chat_manager, 'update_ui_state') as mock_ui_update:
                    mock_ui_update.return_value = UIState()
                    
                    # Make request
                    response = client.post(
                        "/chat",
                        json={"query": "Performance test query"},
                        cookies={"session_token": mock_session_token}
                    )
        
        # Verify response includes performance data
        assert response.status_code == 200
        data = response.json()
        
        # Check that execution time is tracked
        assert "execution_time" in data
        assert isinstance(data["execution_time"], (int, float))
        assert data["execution_time"] >= 0
    
    @pytest.mark.asyncio
    async def test_intelligent_chat_manager_integration(self):
        """Test that intelligent chat manager integrates properly with existing components."""
        
        if not intelligent_chat_manager:
            pytest.skip("Intelligent chat manager not available")
        
        # Test basic functionality
        response = await intelligent_chat_manager.process_message(
            message="Test integration message",
            user_id="test_user",
            session_id="test_session"
        )
        
        # Verify response structure
        assert isinstance(response, IntelligentChatResponse)
        assert response.content is not None
        assert isinstance(response.tools_used, list)
        assert isinstance(response.context_used, list)
        assert isinstance(response.confidence_score, (int, float))
        assert isinstance(response.execution_time, (int, float))
    
    def test_backward_compatibility_response_format(
        self, client, mock_session_token, mock_user_session, sample_intelligent_response
    ):
        """Test that response format maintains backward compatibility."""
        
        # Mock database session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
            
            # Mock intelligent chat manager
            with patch.object(intelligent_chat_manager, 'process_message', new_callable=AsyncMock) as mock_process:
                mock_process.return_value = sample_intelligent_response
                
                with patch.object(intelligent_chat_manager, 'update_ui_state') as mock_ui_update:
                    mock_ui_update.return_value = UIState()
                    
                    # Make request
                    response = client.post(
                        "/chat",
                        json={"query": "Backward compatibility test"},
                        cookies={"session_token": mock_session_token}
                    )
        
        # Verify response has all required legacy fields
        assert response.status_code == 200
        data = response.json()
        
        required_legacy_fields = ["topic", "summary", "sources", "tools_used"]
        for field in required_legacy_fields:
            assert field in data, f"Missing required legacy field: {field}"
        
        # Verify enhanced fields are also present
        enhanced_fields = ["confidence_score", "execution_time", "ui_state", "content_type"]
        for field in enhanced_fields:
            assert field in data, f"Missing enhanced field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])