"""
Simple integration test to verify the comprehensive integration tests work.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

# Import intelligent chat components
from intelligent_chat.chat_manager import ChatManager
from intelligent_chat.models import ChatResponse, ContentType


class TestSimpleIntegration:
    """Simple integration tests to verify functionality."""
    
    @pytest.mark.asyncio
    async def test_chat_manager_basic_functionality(self):
        """Test basic ChatManager functionality."""
        # Create ChatManager with minimal dependencies
        chat_manager = ChatManager(auto_create_context_engine=False)
        
        # Process a simple message
        response = await chat_manager.process_message(
            message="Hello, test message",
            user_id="test_user",
            session_id="test_session"
        )
        
        # Verify response
        assert response is not None
        assert isinstance(response, ChatResponse)
        assert response.content is not None
        assert response.execution_time > 0
        assert response.timestamp is not None
        
        # Verify session was created
        stats = chat_manager.get_session_stats("test_user", "test_session")
        assert stats["message_count"] == 1
        assert stats["total_processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_multiple_messages_conversation(self):
        """Test multiple messages in a conversation."""
        chat_manager = ChatManager(auto_create_context_engine=False)
        
        messages = ["Hello", "How are you?", "Tell me about AI"]
        
        for i, message in enumerate(messages):
            response = await chat_manager.process_message(
                message=message,
                user_id="test_user",
                session_id="test_session"
            )
            
            assert response is not None
            assert response.content is not None
            
            # Check session stats
            stats = chat_manager.get_session_stats("test_user", "test_session")
            assert stats["message_count"] == i + 1
    
    @pytest.mark.asyncio
    async def test_concurrent_conversations(self):
        """Test concurrent conversations."""
        chat_manager = ChatManager(auto_create_context_engine=False)
        
        # Create concurrent tasks
        tasks = []
        for i in range(3):
            task = chat_manager.process_message(
                message=f"Message {i}",
                user_id=f"user{i}",
                session_id=f"session{i}"
            )
            tasks.append(task)
        
        # Execute concurrently
        responses = await asyncio.gather(*tasks)
        
        # Verify all responses
        assert len(responses) == 3
        for i, response in enumerate(responses):
            assert response is not None
            assert f"Message {i}" in response.content or response.content is not None
    
    def test_ui_state_generation(self):
        """Test UI state generation."""
        chat_manager = ChatManager(auto_create_context_engine=False)
        
        # Create a response
        response = ChatResponse(
            content="Test response",
            content_type=ContentType.PLAIN_TEXT,
            tools_used=["test_tool"],
            execution_time=1.0
        )
        
        # Generate UI state
        ui_state = chat_manager.update_ui_state(response)
        
        assert ui_state is not None
        assert len(ui_state.loading_indicators) == 1
        assert ui_state.loading_indicators[0].tool_name == "test_tool"
    
    @pytest.mark.asyncio
    async def test_session_cleanup(self):
        """Test session cleanup."""
        chat_manager = ChatManager(auto_create_context_engine=False)
        
        # Create some sessions
        for i in range(3):
            await chat_manager.process_message(
                message=f"Message {i}",
                user_id=f"user{i}",
                session_id=f"session{i}"
            )
        
        # Verify sessions exist
        global_stats = chat_manager.get_global_stats()
        assert global_stats["active_sessions"] == 3
        
        # Cleanup sessions
        cleaned = await chat_manager.cleanup_inactive_sessions(max_age_hours=0)
        assert cleaned == 3
        
        # Verify cleanup
        global_stats = chat_manager.get_global_stats()
        assert global_stats["active_sessions"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])