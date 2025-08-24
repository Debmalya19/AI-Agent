"""
Tests for new intelligent chat UI endpoints.
Tests /chat/status, /chat/context, /chat/tools, and /chat/ui-state endpoints.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from fastapi.testclient import TestClient

# Import the main app
from main import app, intelligent_chat_manager, memory_manager, tools

# Import intelligent chat models
from intelligent_chat.models import (
    ContextEntry,
    UIState,
    LoadingIndicator,
    LoadingState,
    ErrorState,
    ErrorSeverity,
    ContentSection,
    ContentType,
    InteractiveElement
)


class TestIntelligentChatNewEndpoints:
    """Test new intelligent chat UI endpoints."""
    
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
    def sample_context_entries(self):
        """Sample context entries."""
        return [
            ContextEntry(
                content="Previous user question about BT plans",
                source="conversation_history",
                relevance_score=0.9,
                timestamp=datetime.now(),
                context_type="user_message",
                metadata={"session_id": "test_session_token_123"}
            ),
            ContextEntry(
                content="Bot response about BT broadband options",
                source="conversation_history",
                relevance_score=0.8,
                timestamp=datetime.now(),
                context_type="bot_response",
                metadata={"tools_used": ["BTPlansInformation"]}
            )
        ]
    
    def test_chat_status_endpoint_success(self, client, mock_session_token, mock_user_session):
        """Test /chat/status endpoint returns system status successfully."""
        
        # Mock database session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
            
            # Mock intelligent chat manager stats
            if intelligent_chat_manager:
                with patch.object(intelligent_chat_manager, 'get_session_stats') as mock_session_stats:
                    mock_session_stats.return_value = {
                        "message_count": 5,
                        "total_processing_time": 12.5,
                        "tools_used_count": 8,
                        "avg_processing_time": 2.5
                    }
                    
                    with patch.object(intelligent_chat_manager, 'get_global_stats') as mock_global_stats:
                        mock_global_stats.return_value = {
                            "total_conversations": 150,
                            "active_sessions": 12,
                            "avg_processing_time": 2.1
                        }
                        
                        # Make request
                        response = client.get(
                            "/chat/status",
                            cookies={"session_token": mock_session_token}
                        )
            else:
                # Make request without intelligent chat manager
                response = client.get(
                    "/chat/status",
                    cookies={"session_token": mock_session_token}
                )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "data" in data
        assert data["data"]["system_status"] == "operational"
        assert "intelligent_chat_enabled" in data["data"]
        assert "legacy_agent_enabled" in data["data"]
        assert "memory_layer_enabled" in data["data"]
        assert "timestamp" in data["data"]
        
        # If intelligent chat manager is available, check additional stats
        if intelligent_chat_manager:
            assert "session_stats" in data["data"]
            assert "global_stats" in data["data"]
    
    def test_chat_status_endpoint_unauthorized(self, client):
        """Test /chat/status endpoint returns 401 when unauthorized."""
        response = client.get("/chat/status")
        
        assert response.status_code == 401
        assert "Unauthorized" in response.json()["detail"]
    
    def test_chat_context_endpoint_success(
        self, client, mock_session_token, mock_user_session, sample_context_entries
    ):
        """Test /chat/context endpoint returns conversation context successfully."""
        
        # Mock database session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
            
            # Mock intelligent chat manager context retrieval
            if intelligent_chat_manager:
                with patch.object(intelligent_chat_manager, 'get_conversation_context', new_callable=AsyncMock) as mock_context:
                    mock_context.return_value = sample_context_entries
                    
                    # Make request
                    response = client.get(
                        "/chat/context?limit=5&include_metadata=true",
                        cookies={"session_token": mock_session_token}
                    )
            else:
                # Mock memory manager fallback
                with patch('main.memory_manager') as mock_memory:
                    mock_memory.retrieve_context.return_value = [
                        Mock(
                            content="Mock context content",
                            source="memory_layer",
                            relevance_score=0.7,
                            timestamp=datetime.now(),
                            context_type="user_message",
                            metadata={}
                        )
                    ]
                    
                    # Make request
                    response = client.get(
                        "/chat/context?limit=5&include_metadata=true",
                        cookies={"session_token": mock_session_token}
                    )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["user_id"] == "test_user_123"
        assert "context_count" in data
        assert "context_entries" in data
        assert data["limit"] == 5
        assert data["include_metadata"] == True
        
        # Verify context entry structure
        if data["context_entries"]:
            entry = data["context_entries"][0]
            assert "content" in entry
            assert "source" in entry
            assert "relevance_score" in entry
            assert "timestamp" in entry
            assert "context_type" in entry
            assert "metadata" in entry
    
    def test_chat_context_endpoint_without_metadata(
        self, client, mock_session_token, mock_user_session
    ):
        """Test /chat/context endpoint excludes metadata when requested."""
        
        # Mock database session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
            
            # Mock memory manager
            with patch('main.memory_manager') as mock_memory:
                mock_memory.retrieve_context.return_value = [
                    Mock(
                        content="Test content",
                        source="test_source",
                        relevance_score=0.8,
                        timestamp=datetime.now(),
                        context_type="user_message",
                        metadata={"sensitive": "data"}
                    )
                ]
                
                # Make request without metadata
                response = client.get(
                    "/chat/context?include_metadata=false",
                    cookies={"session_token": mock_session_token}
                )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["include_metadata"] == False
        if data["context_entries"]:
            entry = data["context_entries"][0]
            assert entry["metadata"] == {}  # Should be empty when not included
    
    def test_chat_tools_endpoint_success(self, client, mock_session_token, mock_user_session):
        """Test /chat/tools endpoint returns available tools information."""
        
        # Mock database session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
            
            # Make request
            response = client.get(
                "/chat/tools",
                cookies={"session_token": mock_session_token}
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "tools" in data
        assert "tool_performance" in data
        assert "orchestrator_status" in data
        assert "categories" in data
        assert "timestamp" in data
        
        # Verify tools structure
        if data["tools"]:
            tool = data["tools"][0]
            assert "name" in tool
            assert "description" in tool
            assert "status" in tool
            assert "category" in tool
        
        # Verify categories
        categories = data["categories"]
        expected_categories = ["bt_specific", "support", "context", "search", "general"]
        for category in expected_categories:
            assert category in categories
            assert isinstance(categories[category], int)
        
        # Verify orchestrator status
        orchestrator = data["orchestrator_status"]
        assert "enabled" in orchestrator
    
    def test_chat_ui_state_endpoint_success(self, client, mock_session_token, mock_user_session):
        """Test /chat/ui-state endpoint returns UI state information."""
        
        # Mock database session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
            
            # Mock intelligent chat manager UI state
            if intelligent_chat_manager:
                mock_ui_state = UIState()
                mock_ui_state.loading_indicators = [
                    LoadingIndicator(
                        tool_name="TestTool",
                        state=LoadingState.LOADING,
                        progress=0.5,
                        message="Processing...",
                        estimated_time=5.0
                    )
                ]
                mock_ui_state.error_states = [
                    ErrorState(
                        error_type="test_error",
                        message="Test error message",
                        severity=ErrorSeverity.WARNING,
                        recovery_actions=["retry"],
                        context={"test": "data"}
                    )
                ]
                mock_ui_state.content_sections = [
                    ContentSection(
                        content="Test content",
                        content_type=ContentType.PLAIN_TEXT,
                        metadata={"test": "metadata"},
                        order=1
                    )
                ]
                mock_ui_state.interactive_elements = [
                    InteractiveElement(
                        element_type="button",
                        element_id="test_button",
                        properties={"label": "Test Button"},
                        actions=["click"]
                    )
                ]
                
                with patch.object(intelligent_chat_manager, 'update_ui_state') as mock_update:
                    mock_update.return_value = mock_ui_state
                    
                    # Make request
                    response = client.get(
                        f"/chat/ui-state/{mock_session_token}",
                        cookies={"session_token": mock_session_token}
                    )
            else:
                # Make request without intelligent chat manager
                response = client.get(
                    f"/chat/ui-state/{mock_session_token}",
                    cookies={"session_token": mock_session_token}
                )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "ui_state" in data
        
        ui_state = data["ui_state"]
        assert ui_state["session_id"] == mock_session_token
        assert "loading_indicators" in ui_state
        assert "error_states" in ui_state
        assert "content_sections" in ui_state
        assert "interactive_elements" in ui_state
        assert "last_updated" in ui_state
        
        # If intelligent chat manager is available, verify detailed structure
        if intelligent_chat_manager:
            if ui_state["loading_indicators"]:
                indicator = ui_state["loading_indicators"][0]
                assert "tool_name" in indicator
                assert "state" in indicator
                assert "progress" in indicator
                assert "message" in indicator
                assert "estimated_time" in indicator
            
            if ui_state["error_states"]:
                error = ui_state["error_states"][0]
                assert "error_type" in error
                assert "message" in error
                assert "severity" in error
                assert "recovery_actions" in error
                assert "context" in error
    
    def test_endpoints_invalid_session(self, client, mock_session_token):
        """Test all new endpoints return 401 for invalid sessions."""
        
        # Mock database to return no session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
            
            endpoints = [
                "/chat/status",
                "/chat/context",
                "/chat/tools",
                f"/chat/ui-state/{mock_session_token}"
            ]
            
            for endpoint in endpoints:
                response = client.get(
                    endpoint,
                    cookies={"session_token": mock_session_token}
                )
                
                assert response.status_code == 401, f"Endpoint {endpoint} should return 401"
                assert "Invalid session" in response.json()["detail"]
    
    def test_chat_context_endpoint_fallback_to_memory_manager(
        self, client, mock_session_token, mock_user_session
    ):
        """Test /chat/context endpoint falls back to memory manager when intelligent chat fails."""
        
        # Mock database session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
            
            # Mock intelligent chat manager to fail
            if intelligent_chat_manager:
                with patch.object(intelligent_chat_manager, 'get_conversation_context', new_callable=AsyncMock) as mock_context:
                    mock_context.side_effect = Exception("Intelligent context failed")
                    
                    # Mock memory manager fallback
                    with patch('main.memory_manager') as mock_memory:
                        mock_memory.retrieve_context.return_value = [
                            Mock(
                                content="Fallback context",
                                source="memory_fallback",
                                relevance_score=0.6,
                                timestamp=datetime.now(),
                                context_type="fallback",
                                metadata={}
                            )
                        ]
                        
                        # Make request
                        response = client.get(
                            "/chat/context",
                            cookies={"session_token": mock_session_token}
                        )
            else:
                # Direct memory manager test
                with patch('main.memory_manager') as mock_memory:
                    mock_memory.retrieve_context.return_value = [
                        Mock(
                            content="Direct memory context",
                            source="memory_direct",
                            relevance_score=0.7,
                            timestamp=datetime.now(),
                            context_type="direct",
                            metadata={}
                        )
                    ]
                    
                    # Make request
                    response = client.get(
                        "/chat/context",
                        cookies={"session_token": mock_session_token}
                    )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["context_count"] >= 0
        
        # Verify fallback worked
        if data["context_entries"]:
            entry = data["context_entries"][0]
            assert "content" in entry
            assert entry["source"] in ["memory_fallback", "memory_direct"]
    
    def test_chat_tools_endpoint_categorization(self, client, mock_session_token, mock_user_session):
        """Test /chat/tools endpoint correctly categorizes tools."""
        
        # Mock database session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
            
            # Make request
            response = client.get(
                "/chat/tools",
                cookies={"session_token": mock_session_token}
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check that tools are properly categorized
        tools_list = data["tools"]
        categories = data["categories"]
        
        # Count tools by category
        bt_tools = [t for t in tools_list if t["category"] == "bt_specific"]
        support_tools = [t for t in tools_list if t["category"] == "support"]
        context_tools = [t for t in tools_list if t["category"] == "context"]
        search_tools = [t for t in tools_list if t["category"] == "search"]
        general_tools = [t for t in tools_list if t["category"] == "general"]
        
        # Verify category counts match
        assert len(bt_tools) == categories["bt_specific"]
        assert len(support_tools) == categories["support"]
        assert len(context_tools) == categories["context"]
        assert len(search_tools) == categories["search"]
        assert len(general_tools) == categories["general"]
        
        # Verify total count
        total_categorized = sum(categories.values())
        assert total_categorized == len(tools_list)
    
    def test_error_handling_in_endpoints(self, client, mock_session_token, mock_user_session):
        """Test error handling in all new endpoints."""
        
        # Mock database session
        with patch('main.SessionLocal') as mock_db:
            mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
            
            # Test each endpoint with various error conditions
            endpoints_to_test = [
                ("/chat/status", {}),
                ("/chat/context", {}),
                ("/chat/tools", {}),
                (f"/chat/ui-state/{mock_session_token}", {})
            ]
            
            for endpoint, params in endpoints_to_test:
                # Test with database error
                with patch('main.SessionLocal') as mock_db_error:
                    mock_db_error.side_effect = Exception("Database connection failed")
                    
                    response = client.get(
                        endpoint,
                        cookies={"session_token": mock_session_token},
                        params=params
                    )
                    
                    # Should return 500 for internal errors
                    assert response.status_code == 500
                    assert "Failed to" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])