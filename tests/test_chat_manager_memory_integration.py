"""
Integration tests for ChatManager with existing memory layer.
Tests the integration with MemoryLayerManager, ContextRetrievalEngine,
and conversation history tracking and management.
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from intelligent_chat import (
    ChatManager,
    ChatResponse,
    ContextEntry,
    ContentType
)

# Import memory layer components
try:
    from memory_layer_manager import MemoryLayerManager, MemoryStats
    from context_retrieval_engine import ContextRetrievalEngine
    from memory_models import ConversationEntryDTO, ContextEntryDTO
    from memory_config import MemoryConfig
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False


@pytest.mark.skipif(not MEMORY_AVAILABLE, reason="Memory layer components not available")
class TestChatManagerMemoryIntegration:
    """Test suite for ChatManager memory layer integration."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock(spec=Session)
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.close = Mock()
        session.query = Mock()
        return session
    
    @pytest.fixture
    def memory_config(self):
        """Create a test memory configuration."""
        config = MemoryConfig()
        config.enable_database_storage = True
        config.enable_context_retrieval = True
        config.enable_tool_analytics = True
        config.log_memory_operations = True
        return config
    
    @pytest.fixture
    def mock_memory_manager(self, mock_db_session, memory_config):
        """Create a mock memory layer manager."""
        manager = Mock(spec=MemoryLayerManager)
        manager.config = memory_config
        manager.db_session = mock_db_session
        
        # Mock methods
        manager.store_conversation = Mock(return_value=True)
        manager.retrieve_context = Mock(return_value=[])
        manager.get_memory_stats = Mock(return_value=MemoryStats())
        manager.cleanup_expired_data = Mock()
        
        return manager
    
    @pytest.fixture
    def mock_context_engine(self, mock_db_session, memory_config):
        """Create a mock context retrieval engine."""
        engine = Mock(spec=ContextRetrievalEngine)
        engine.config = memory_config
        engine.db_session = mock_db_session
        
        # Mock methods
        engine.get_relevant_context = Mock(return_value=[])
        engine.rank_context_relevance = Mock(return_value=[])
        engine.calculate_context_similarity = Mock(return_value=0.8)
        engine.cache_context = Mock(return_value=True)
        
        return engine
    
    @pytest.fixture
    def sample_memory_contexts(self):
        """Create sample memory context entries."""
        return [
            ContextEntryDTO(
                content="User asked about billing last week",
                source="memory_conversation_1",
                relevance_score=0.9,
                context_type="conversation",
                timestamp=datetime.now() - timedelta(days=1),
                metadata={"session_id": "old_session", "topic": "billing", "message_type": "user_message"}
            ),
            ContextEntryDTO(
                content="Bot provided billing information",
                source="memory_conversation_1",
                relevance_score=0.8,
                context_type="conversation",
                timestamp=datetime.now() - timedelta(days=1),
                metadata={"session_id": "old_session", "topic": "billing", "message_type": "bot_response"}
            )
        ]
    
    def test_chat_manager_memory_integration_initialization(self, mock_memory_manager, mock_context_engine):
        """Test ChatManager initialization with memory components."""
        manager = ChatManager(
            memory_manager=mock_memory_manager,
            context_engine=mock_context_engine
        )
        
        assert manager.memory_manager == mock_memory_manager
        assert manager.context_engine == mock_context_engine
        assert manager._conversation_count == 0
        assert manager._total_processing_time == 0.0
    
    @pytest.mark.asyncio
    async def test_process_message_with_memory_storage(self, mock_memory_manager):
        """Test message processing stores conversation in memory layer."""
        manager = ChatManager(memory_manager=mock_memory_manager)
        
        response = await manager.process_message(
            message="What's my current bill?",
            user_id="test_user_123",
            session_id="test_session_456"
        )
        
        # Verify response was generated
        assert isinstance(response, ChatResponse)
        assert response.execution_time > 0
        
        # Verify conversation was stored in memory
        mock_memory_manager.store_conversation.assert_called_once()
        
        # Check the stored conversation data
        call_args = mock_memory_manager.store_conversation.call_args[0][0]
        assert isinstance(call_args, ConversationEntryDTO)
        assert call_args.user_id == "test_user_123"
        assert call_args.session_id == "test_session_456"
        assert call_args.user_message == "What's my current bill?"
        assert call_args.bot_response == response.content
    
    @pytest.mark.asyncio
    async def test_context_retrieval_from_memory(self, mock_memory_manager, sample_memory_contexts):
        """Test context retrieval from memory layer."""
        mock_memory_manager.retrieve_context.return_value = sample_memory_contexts
        
        # Create manager with memory manager but no context engine to force memory fallback
        manager = ChatManager(
            memory_manager=mock_memory_manager,
            context_engine=None,
            auto_create_context_engine=False  # Disable auto-creation
        )
        
        response = await manager.process_message(
            message="Tell me more about my bill",
            user_id="test_user_123",
            session_id="test_session_456"
        )
        
        # Verify context was retrieved from memory
        mock_memory_manager.retrieve_context.assert_called_once_with(
            "Tell me more about my bill", "test_user_123", 10
        )
        
        # Verify context was used in response
        assert len(response.context_used) == 2
        assert "memory_conversation_1" in response.context_used
        assert response.ui_hints["context_count"] == 2
    
    @pytest.mark.asyncio
    async def test_context_retrieval_from_engine(self, mock_context_engine, sample_memory_contexts):
        """Test context retrieval from context engine."""
        mock_context_engine.get_relevant_context.return_value = sample_memory_contexts
        
        manager = ChatManager(context_engine=mock_context_engine)
        
        response = await manager.process_message(
            message="Show me billing details",
            user_id="test_user_123",
            session_id="test_session_456"
        )
        
        # Verify context was retrieved from engine
        mock_context_engine.get_relevant_context.assert_called_once_with(
            "Show me billing details", "test_user_123", limit=10
        )
        
        # Verify context was used
        assert len(response.context_used) == 2
        assert response.ui_hints["context_count"] == 2
    
    @pytest.mark.asyncio
    async def test_get_conversation_context_memory_fallback(self, mock_memory_manager, sample_memory_contexts):
        """Test conversation context retrieval with memory fallback."""
        mock_memory_manager.retrieve_context.return_value = sample_memory_contexts
        
        manager = ChatManager(memory_manager=mock_memory_manager)
        
        context = await manager.get_conversation_context("test_user_123", limit=5)
        
        # Verify memory manager was called
        mock_memory_manager.retrieve_context.assert_called_once_with("", "test_user_123", 5)
        
        # Verify context entries were converted properly
        assert len(context) == 2
        assert all(isinstance(entry, ContextEntry) for entry in context)
        assert context[0].content == "User asked about billing last week"
        assert context[0].source == "memory_conversation_1"
        assert context[0].relevance_score == 0.9
    
    @pytest.mark.asyncio
    async def test_get_conversation_context_engine_fallback(self, mock_context_engine, sample_memory_contexts):
        """Test conversation context retrieval with context engine fallback."""
        mock_context_engine.get_relevant_context.return_value = sample_memory_contexts
        
        manager = ChatManager(context_engine=mock_context_engine)
        
        context = await manager.get_conversation_context("test_user_123", limit=5)
        
        # Verify context engine was called
        mock_context_engine.get_relevant_context.assert_called_once_with("", "test_user_123", limit=5)
        
        # Verify context entries were converted properly
        assert len(context) == 2
        assert context[1].content == "Bot provided billing information"
        assert context[1].context_type == "bot_response"
    
    @pytest.mark.asyncio
    async def test_memory_storage_error_handling(self, mock_memory_manager):
        """Test error handling when memory storage fails."""
        # Make memory storage fail
        mock_memory_manager.store_conversation.return_value = False
        
        manager = ChatManager(memory_manager=mock_memory_manager)
        
        # Should still process message successfully
        response = await manager.process_message(
            message="Test message",
            user_id="test_user_123",
            session_id="test_session_456"
        )
        
        assert isinstance(response, ChatResponse)
        assert response.content_type != ContentType.ERROR_MESSAGE  # Should not be an error response
        
        # Verify storage was attempted
        mock_memory_manager.store_conversation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_retrieval_error_handling(self, mock_memory_manager):
        """Test error handling when context retrieval fails."""
        # Make context retrieval raise an exception
        mock_memory_manager.retrieve_context.side_effect = Exception("Database connection failed")
        
        manager = ChatManager(memory_manager=mock_memory_manager)
        
        # Should still process message successfully
        response = await manager.process_message(
            message="Test message",
            user_id="test_user_123",
            session_id="test_session_456"
        )
        
        assert isinstance(response, ChatResponse)
        assert len(response.context_used) == 0  # No context due to error
        assert response.ui_hints["context_count"] == 0
    
    @pytest.mark.asyncio
    async def test_conversation_history_tracking(self, mock_memory_manager):
        """Test conversation history tracking across multiple messages."""
        manager = ChatManager(memory_manager=mock_memory_manager)
        
        # Process multiple messages
        messages = [
            "What's my bill?",
            "Can you break down the charges?",
            "When is the payment due?"
        ]
        
        for i, message in enumerate(messages):
            response = await manager.process_message(
                message=message,
                user_id="test_user_123",
                session_id="test_session_456"
            )
            
            assert isinstance(response, ChatResponse)
        
        # Verify all conversations were stored
        assert mock_memory_manager.store_conversation.call_count == 3
        
        # Verify session tracking
        session_stats = manager.get_session_stats("test_user_123", "test_session_456")
        assert session_stats["message_count"] == 3
        assert session_stats["total_processing_time"] > 0
    
    def test_context_conversion_from_memory(self, sample_memory_contexts):
        """Test conversion of memory contexts to ContextEntry objects."""
        manager = ChatManager()
        
        context_entries = manager._convert_memory_contexts_to_context_entries(sample_memory_contexts)
        
        assert len(context_entries) == 2
        assert all(isinstance(entry, ContextEntry) for entry in context_entries)
        
        # Check first entry
        entry1 = context_entries[0]
        assert entry1.content == "User asked about billing last week"
        assert entry1.source == "memory_conversation_1"
        assert entry1.relevance_score == 0.9
        assert entry1.context_type == "conversation"
        assert entry1.metadata["topic"] == "billing"
        assert entry1.metadata["message_type"] == "user_message"
    
    def test_context_conversion_from_engine(self, sample_memory_contexts):
        """Test conversion of engine contexts to ContextEntry objects."""
        manager = ChatManager()
        
        context_entries = manager._convert_engine_contexts_to_context_entries(sample_memory_contexts)
        
        assert len(context_entries) == 2
        assert all(isinstance(entry, ContextEntry) for entry in context_entries)
        
        # Check second entry
        entry2 = context_entries[1]
        assert entry2.content == "Bot provided billing information"
        assert entry2.source == "memory_conversation_1"
        assert entry2.relevance_score == 0.8
        assert entry2.context_type == "conversation"
        assert entry2.metadata["message_type"] == "bot_response"
    
    @pytest.mark.asyncio
    async def test_confidence_score_with_memory_context(self, mock_memory_manager, sample_memory_contexts):
        """Test confidence score calculation with memory-provided context."""
        mock_memory_manager.retrieve_context.return_value = sample_memory_contexts
        
        manager = ChatManager(memory_manager=mock_memory_manager)
        
        response = await manager.process_message(
            message="What about my billing?",
            user_id="test_user_123",
            session_id="test_session_456"
        )
        
        # Confidence should be boosted by relevant context
        assert response.confidence_score > 0.5  # Base score
        assert response.confidence_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_memory_integration_performance_tracking(self, mock_memory_manager):
        """Test performance tracking with memory integration."""
        manager = ChatManager(memory_manager=mock_memory_manager)
        
        # Process several messages
        for i in range(3):
            await manager.process_message(
                message=f"Test message {i}",
                user_id="test_user_123",
                session_id="test_session_456"
            )
        
        # Check global stats
        stats = manager.get_global_stats()
        assert stats["total_conversations"] == 3
        assert stats["total_processing_time"] > 0
        assert stats["avg_processing_time"] > 0
        assert stats["memory_integration_enabled"] is True
        assert stats["active_sessions"] == 1
    
    @pytest.mark.asyncio
    async def test_error_conversation_storage(self, mock_memory_manager):
        """Test that error conversations are also stored in memory."""
        manager = ChatManager(memory_manager=mock_memory_manager)
        
        # Simulate an error by making the message processing fail internally
        with patch.object(manager, '_generate_response_content', side_effect=Exception("Test error")):
            response = await manager.process_message(
                message="This will cause an error",
                user_id="test_user_123",
                session_id="test_session_456"
            )
        
        # Should return error response
        assert response.content_type == ContentType.ERROR_MESSAGE
        assert "error" in response.content.lower()
        
        # Should still attempt to store the conversation
        mock_memory_manager.store_conversation.assert_called_once()
    
    def test_memory_integration_without_components(self):
        """Test ChatManager works without memory components."""
        manager = ChatManager()  # No memory components
        
        # Should initialize successfully
        assert manager.memory_manager is None
        assert manager.context_engine is None
        
        # Global stats should reflect no memory integration
        stats = manager.get_global_stats()
        assert stats["memory_integration_enabled"] is False
        assert stats["context_engine_enabled"] is False


@pytest.mark.skipif(MEMORY_AVAILABLE, reason="Testing import fallback behavior")
class TestChatManagerWithoutMemoryLayer:
    """Test ChatManager behavior when memory layer is not available."""
    
    def test_initialization_without_memory_imports(self):
        """Test ChatManager initializes gracefully without memory layer imports."""
        manager = ChatManager()
        
        assert manager is not None
        assert manager.memory_manager is None
        assert manager.context_engine is None
    
    @pytest.mark.asyncio
    async def test_process_message_without_memory(self):
        """Test message processing works without memory layer."""
        manager = ChatManager()
        
        response = await manager.process_message(
            message="Test message",
            user_id="test_user",
            session_id="test_session"
        )
        
        assert isinstance(response, ChatResponse)
        assert response.execution_time > 0
        assert len(response.context_used) == 0  # No context without memory layer


if __name__ == "__main__":
    pytest.main([__file__, "-v"])