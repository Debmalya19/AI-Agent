"""
Unit tests for ChatManager core functionality.
Tests the message processing pipeline, context retrieval integration,
and basic UI state management.
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from intelligent_chat import (
    ChatManager,
    ChatResponse,
    ContextEntry,
    UIState,
    ContentType,
    LoadingState,
    ErrorSeverity,
    ChatUIException,
    ToolExecutionError,
    ContextRetrievalError
)


class TestChatManagerCore:
    """Test suite for ChatManager core functionality."""
    
    @pytest.fixture
    def chat_manager(self):
        """Create a ChatManager instance for testing."""
        return ChatManager()
    
    @pytest.fixture
    def mock_tool_orchestrator(self):
        """Create a mock tool orchestrator."""
        mock = Mock()
        mock.select_tools = AsyncMock(return_value=[])
        mock.execute_tools = AsyncMock(return_value=[])
        return mock
    
    @pytest.fixture
    def mock_context_retriever(self):
        """Create a mock context retriever."""
        mock = Mock()
        mock.get_relevant_context = AsyncMock(return_value=[])
        return mock
    
    @pytest.fixture
    def mock_memory_manager(self):
        """Create a mock memory manager."""
        mock = Mock()
        mock.retrieve_context = Mock(return_value=[])
        mock.store_conversation = Mock(return_value=True)
        return mock
    
    @pytest.fixture
    def sample_context_entries(self):
        """Create sample context entries for testing."""
        return [
            ContextEntry(
                content="Previous user question about billing",
                source="conversation_123",
                relevance_score=0.8,
                timestamp=datetime.now(),
                context_type="user_message",
                metadata={"session_id": "test_session"}
            ),
            ContextEntry(
                content="Bot response about billing information",
                source="conversation_123",
                relevance_score=0.7,
                timestamp=datetime.now(),
                context_type="bot_response",
                metadata={"session_id": "test_session"}
            )
        ]
    
    def test_chat_manager_initialization(self):
        """Test ChatManager can be initialized with default parameters."""
        manager = ChatManager()
        
        assert manager is not None
        assert manager.tool_orchestrator is None
        assert manager.context_retriever is None
        assert manager.response_renderer is None
        assert isinstance(manager._active_sessions, dict)
        assert manager._conversation_count == 0
        assert manager._total_processing_time == 0.0
    
    def test_chat_manager_initialization_with_components(self, mock_tool_orchestrator, 
                                                        mock_context_retriever, mock_memory_manager):
        """Test ChatManager initialization with component dependencies."""
        manager = ChatManager(
            tool_orchestrator=mock_tool_orchestrator,
            context_retriever=mock_context_retriever,
            memory_manager=mock_memory_manager
        )
        
        assert manager.tool_orchestrator == mock_tool_orchestrator
        assert manager.context_retriever == mock_context_retriever
        assert manager.memory_manager == mock_memory_manager
    
    @pytest.mark.asyncio
    async def test_process_message_basic(self, chat_manager):
        """Test basic message processing without external components."""
        response = await chat_manager.process_message(
            message="Hello, how can I check my bill?",
            user_id="test_user_123",
            session_id="test_session_456"
        )
        
        assert isinstance(response, ChatResponse)
        assert "Hello, how can I check my bill?" in response.content
        assert response.content_type in [ContentType.PLAIN_TEXT, ContentType.MARKDOWN]
        assert response.execution_time > 0
        assert response.timestamp is not None
        assert response.ui_hints["session_id"] == "test_session_456"
        
        # Check session was created
        session_key = "test_user_123:test_session_456"
        assert session_key in chat_manager._active_sessions
        assert chat_manager._active_sessions[session_key]["message_count"] == 1
    
    @pytest.mark.asyncio
    async def test_process_message_with_context_retriever(self, mock_context_retriever, sample_context_entries):
        """Test message processing with context retriever integration."""
        mock_context_retriever.get_relevant_context.return_value = sample_context_entries
        
        manager = ChatManager(context_retriever=mock_context_retriever)
        
        response = await manager.process_message(
            message="What about my current bill?",
            user_id="test_user_123",
            session_id="test_session_456"
        )
        
        assert isinstance(response, ChatResponse)
        assert len(response.context_used) == 2
        assert "conversation_123" in response.context_used
        assert response.ui_hints["context_count"] == 2
        
        # Verify context retriever was called
        mock_context_retriever.get_relevant_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_with_tool_orchestrator(self, mock_tool_orchestrator):
        """Test message processing with tool orchestrator integration."""
        from intelligent_chat.models import ToolRecommendation, ToolResult
        
        # Mock tool recommendations
        tool_recommendations = [
            ToolRecommendation(
                tool_name="billing_tool",
                relevance_score=0.9,
                expected_execution_time=1.0,
                confidence_level=0.8
            )
        ]
        
        # Mock tool results
        tool_results = [
            ToolResult(
                tool_name="billing_tool",
                success=True,
                result={"bill_amount": "£45.99"},
                execution_time=0.5
            )
        ]
        
        mock_tool_orchestrator.select_tools.return_value = tool_recommendations
        mock_tool_orchestrator.execute_tools.return_value = tool_results
        
        manager = ChatManager(tool_orchestrator=mock_tool_orchestrator)
        
        response = await manager.process_message(
            message="Show me my bill",
            user_id="test_user_123",
            session_id="test_session_456"
        )
        
        assert isinstance(response, ChatResponse)
        assert "billing_tool" in response.tools_used
        assert response.ui_hints["tools_count"] == 1
        assert response.confidence_score > 0.5  # Should be boosted by successful tool usage
        
        # Verify tool orchestrator was called
        mock_tool_orchestrator.select_tools.assert_called_once()
        mock_tool_orchestrator.execute_tools.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_with_memory_integration(self, mock_memory_manager):
        """Test message processing with memory layer integration."""
        from memory_models import ContextEntryDTO
        
        # Mock memory contexts
        memory_contexts = [
            ContextEntryDTO(
                content="Previous billing question",
                source="memory_entry_1",
                relevance_score=0.8,
                context_type="user_message",
                timestamp=datetime.now(),
                metadata={}
            )
        ]
        
        mock_memory_manager.retrieve_context.return_value = memory_contexts
        
        manager = ChatManager(memory_manager=mock_memory_manager)
        
        response = await manager.process_message(
            message="What's my bill status?",
            user_id="test_user_123",
            session_id="test_session_456"
        )
        
        assert isinstance(response, ChatResponse)
        assert len(response.context_used) == 1
        assert "memory_entry_1" in response.context_used
        
        # Verify memory manager was called for retrieval and storage
        mock_memory_manager.retrieve_context.assert_called_once()
        mock_memory_manager.store_conversation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, mock_context_retriever):
        """Test error handling in message processing."""
        # Make context retriever raise an exception
        mock_context_retriever.get_relevant_context.side_effect = ContextRetrievalError(
            "Context retrieval failed", "test_user_123"
        )
        
        manager = ChatManager(context_retriever=mock_context_retriever)
        
        response = await manager.process_message(
            message="Test message",
            user_id="test_user_123",
            session_id="test_session_456"
        )
        
        # Should still return a response, not raise an exception
        assert isinstance(response, ChatResponse)
        assert response.content_type == ContentType.PLAIN_TEXT  # Should fallback gracefully
        assert response.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_get_conversation_context(self, mock_context_retriever, sample_context_entries):
        """Test conversation context retrieval."""
        mock_context_retriever.get_relevant_context.return_value = sample_context_entries
        
        manager = ChatManager(context_retriever=mock_context_retriever)
        
        context = await manager.get_conversation_context("test_user_123", limit=5)
        
        assert len(context) == 2
        assert all(isinstance(entry, ContextEntry) for entry in context)
        assert context[0].content == "Previous user question about billing"
        
        mock_context_retriever.get_relevant_context.assert_called_once_with("", "test_user_123", 5)
    
    @pytest.mark.asyncio
    async def test_get_conversation_context_with_memory_fallback(self, mock_memory_manager):
        """Test conversation context retrieval with memory layer fallback."""
        from memory_models import ContextEntryDTO
        
        memory_contexts = [
            ContextEntryDTO(
                content="Memory context entry",
                source="memory_1",
                relevance_score=0.7,
                context_type="user_message",
                timestamp=datetime.now(),
                metadata={}
            )
        ]
        
        mock_memory_manager.retrieve_context.return_value = memory_contexts
        
        manager = ChatManager(memory_manager=mock_memory_manager)
        
        context = await manager.get_conversation_context("test_user_123", limit=5)
        
        assert len(context) == 1
        assert context[0].content == "Memory context entry"
        assert context[0].source == "memory_1"
    
    def test_update_ui_state(self, chat_manager):
        """Test UI state generation based on chat response."""
        response = ChatResponse(
            content="Here's your billing information",
            content_type=ContentType.PLAIN_TEXT,
            tools_used=["billing_tool", "account_tool"],
            execution_time=1.5
        )
        
        ui_state = chat_manager.update_ui_state(response)
        
        assert isinstance(ui_state, UIState)
        assert len(ui_state.loading_indicators) == 2
        assert ui_state.loading_indicators[0].tool_name == "billing_tool"
        assert ui_state.loading_indicators[0].state == LoadingState.COMPLETED
        assert ui_state.loading_indicators[1].tool_name == "account_tool"
    
    def test_update_ui_state_with_error(self, chat_manager):
        """Test UI state generation for error responses."""
        error_response = ChatResponse(
            content="Error: Unable to process request",
            content_type=ContentType.ERROR_MESSAGE,
            execution_time=0.5
        )
        
        ui_state = chat_manager.update_ui_state(error_response)
        
        assert isinstance(ui_state, UIState)
        assert len(ui_state.error_states) == 1
        assert ui_state.error_states[0].error_type == "processing_error"
        assert ui_state.error_states[0].severity == ErrorSeverity.ERROR
        assert "retry" in ui_state.error_states[0].recovery_actions
    
    def test_session_management(self, chat_manager):
        """Test session creation and management."""
        # Test session creation
        chat_manager._ensure_session("user1", "session1")
        
        session_key = "user1:session1"
        assert session_key in chat_manager._active_sessions
        
        session = chat_manager._active_sessions[session_key]
        assert session["user_id"] == "user1"
        assert session["session_id"] == "session1"
        assert session["message_count"] == 0
        assert isinstance(session["created_at"], datetime)
    
    def test_session_stats(self, chat_manager):
        """Test session statistics tracking."""
        # Create a session with some activity
        chat_manager._ensure_session("user1", "session1")
        
        response = ChatResponse(
            content="Test response",
            content_type=ContentType.PLAIN_TEXT,
            tools_used=["tool1", "tool2"],
            execution_time=1.5
        )
        
        chat_manager._update_session_state("user1", "session1", "Test message", response)
        
        stats = chat_manager.get_session_stats("user1", "session1")
        
        assert stats["message_count"] == 1
        assert stats["total_processing_time"] == 1.5
        assert stats["tools_used_count"] == 2
        assert stats["avg_processing_time"] == 1.5
    
    def test_global_stats(self, chat_manager):
        """Test global statistics tracking."""
        # Simulate some activity
        chat_manager._conversation_count = 5
        chat_manager._total_processing_time = 10.0
        chat_manager._active_sessions["user1:session1"] = {}
        
        stats = chat_manager.get_global_stats()
        
        assert stats["total_conversations"] == 5
        assert stats["total_processing_time"] == 10.0
        assert stats["active_sessions"] == 1
        assert stats["avg_processing_time"] == 2.0
        assert "memory_integration_enabled" in stats
        assert "context_engine_enabled" in stats
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions(self, chat_manager):
        """Test cleanup of inactive sessions."""
        # Create some sessions with different ages
        now = datetime.now()
        old_time = now - timedelta(hours=25)  # Older than 24 hours
        recent_time = now - timedelta(hours=1)  # Recent
        
        chat_manager._active_sessions = {
            "user1:session1": {"created_at": old_time, "last_activity": old_time},
            "user2:session2": {"created_at": recent_time, "last_activity": recent_time},
            "user3:session3": {"created_at": old_time, "last_activity": recent_time}  # Old but recent activity
        }
        
        cleaned_count = await chat_manager.cleanup_inactive_sessions(max_age_hours=24)
        
        assert cleaned_count == 1  # Only user1:session1 should be cleaned
        assert "user1:session1" not in chat_manager._active_sessions
        assert "user2:session2" in chat_manager._active_sessions
        assert "user3:session3" in chat_manager._active_sessions
    
    def test_confidence_score_calculation(self, chat_manager):
        """Test confidence score calculation."""
        # Test with good context and successful tools
        context = [
            ContextEntry(
                content="Relevant context",
                source="test",
                relevance_score=0.9,
                timestamp=datetime.now(),
                context_type="test"
            )
        ]
        
        tool_performance = {
            "tool1": {"success": True},
            "tool2": {"success": True}
        }
        
        score = chat_manager._calculate_confidence_score(context, ["tool1", "tool2"], tool_performance)
        
        assert 0.5 < score <= 1.0  # Should be higher than base score
        
        # Test with no context and failed tools
        empty_score = chat_manager._calculate_confidence_score([], [], {})
        assert empty_score == 0.5  # Should be base score
    
    def test_content_type_determination(self, chat_manager):
        """Test content type determination."""
        # Test different content types
        assert chat_manager._determine_content_type("Hello world") == ContentType.PLAIN_TEXT
        assert chat_manager._determine_content_type("Error: Something failed") == ContentType.ERROR_MESSAGE
        assert chat_manager._determine_content_type("```python\nprint('hello')\n```") == ContentType.CODE_BLOCK
        assert chat_manager._determine_content_type('{"key": "value"}') == ContentType.JSON
        assert chat_manager._determine_content_type("# Header\n**bold text**") == ContentType.MARKDOWN


if __name__ == "__main__":
    pytest.main([__file__, "-v"])