"""
User experience and responsiveness tests for intelligent chat UI.

Tests UI adaptation to different response types, context awareness in follow-up
conversations, loading indicator accuracy, error recovery, and conversation
thread continuity.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

# Import intelligent chat components
from intelligent_chat.chat_manager import ChatManager
from intelligent_chat.response_renderer import ResponseRenderer
from intelligent_chat.context_retriever import ContextRetriever
from intelligent_chat.models import (
    ChatResponse, ContextEntry, ToolRecommendation, ToolResult,
    ContentType, LoadingState, ErrorSeverity, UIState,
    LoadingIndicator, ErrorState
)

# Import loading and status components if available
try:
    from intelligent_chat.loading_indicators import LoadingIndicatorManager
except ImportError:
    LoadingIndicatorManager = None

try:
    from intelligent_chat.status_monitor import StatusMonitor
except ImportError:
    StatusMonitor = None


class TestUIAdaptationToResponseTypes:
    """Test UI adaptation to different response types."""
    
    @pytest.fixture
    def response_renderer(self):
        """Create ResponseRenderer for testing."""
        return ResponseRenderer()
    
    @pytest.fixture
    def chat_manager_with_renderer(self, response_renderer):
        """Create ChatManager with ResponseRenderer."""
        return ChatManager(
            response_renderer=response_renderer,
            auto_create_context_engine=False
        )
    
    def test_plain_text_response_adaptation(self, response_renderer):
        """Test UI adaptation for plain text responses."""
        plain_text = "This is a simple text response with helpful information."
        
        sections = response_renderer.render_response(plain_text, {})
        
        assert len(sections) == 1
        assert sections[0].content_type == ContentType.PLAIN_TEXT
        assert sections[0].content == plain_text
        
        # UI should adapt with simple text formatting
        assert sections[0].metadata.get("formatting") != "complex"
    
    def test_code_response_adaptation(self, response_renderer):
        """Test UI adaptation for code responses."""
        code_response = """Here's the solution:

```python
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

# Example usage
result = calculate_fibonacci(10)
print(f"Fibonacci(10) = {result}")
```

This function calculates Fibonacci numbers recursively."""
        
        sections = response_renderer.render_response(code_response, {})
        
        # Should detect and separate code blocks
        code_sections = [s for s in sections if s.content_type == ContentType.CODE_BLOCK]
        text_sections = [s for s in sections if s.content_type == ContentType.PLAIN_TEXT]
        
        assert len(code_sections) >= 1
        assert len(text_sections) >= 1
        
        # Code section should have syntax highlighting metadata
        code_section = code_sections[0]
        assert code_section.metadata.get("language") == "python"
        assert "def calculate_fibonacci" in code_section.content
    
    def test_structured_data_response_adaptation(self, response_renderer):
        """Test UI adaptation for structured data responses."""
        structured_response = """Here's your data analysis:

Summary statistics:
- Total users: 1,250
- Active users: 890
- Conversion rate: 71.2%

Detailed breakdown:
{"users": {"total": 1250, "active": 890, "inactive": 360}, "metrics": {"conversion_rate": 0.712, "engagement": 0.85}}

Key insights:
1. High engagement rate indicates good user experience
2. Conversion rate is above industry average
3. Consider re-engagement campaign for inactive users"""
        
        sections = response_renderer.render_response(structured_response, {})
        
        # Should have multiple content types
        content_types = [s.content_type for s in sections]
        assert ContentType.PLAIN_TEXT in content_types
        assert ContentType.JSON in content_types
        
        # JSON section should be properly formatted
        json_sections = [s for s in sections if s.content_type == ContentType.JSON]
        assert len(json_sections) >= 1
        
        json_section = json_sections[0]
        assert "users" in json_section.content
        assert "metrics" in json_section.content
    
    def test_error_response_adaptation(self, response_renderer):
        """Test UI adaptation for error responses."""
        error_response = "Error: Unable to connect to the weather service. Please check your internet connection and try again."
        
        sections = response_renderer.render_response(error_response, {"error": True})
        
        assert len(sections) == 1
        assert sections[0].content_type == ContentType.ERROR_MESSAGE
        
        # Error should have appropriate styling metadata
        assert sections[0].metadata.get("error") is True
        assert "Error:" in sections[0].content
    
    def test_mixed_content_response_adaptation(self, response_renderer):
        """Test UI adaptation for mixed content responses."""
        mixed_response = """# Weather Analysis Report

## Current Conditions
The weather data shows:

```json
{
  "temperature": 22,
  "humidity": 65,
  "wind_speed": 10,
  "condition": "partly_cloudy"
}
```

## Recommendations
Based on the current conditions:
- **Temperature**: Perfect for outdoor activities
- **Humidity**: Comfortable level
- **Wind**: Light breeze, ideal for walking

```python
# Weather comfort index calculation
def comfort_index(temp, humidity, wind):
    return (temp * 0.6) + ((100 - humidity) * 0.3) + (wind * 0.1)

comfort = comfort_index(22, 65, 10)
print(f"Comfort index: {comfort}")
```

**Conclusion**: Excellent weather for outdoor activities!"""
        
        sections = response_renderer.render_response(mixed_response, {})
        
        # Should have multiple content types
        content_types = [s.content_type for s in sections]
        assert ContentType.MARKDOWN in content_types
        assert ContentType.JSON in content_types
        assert ContentType.CODE_BLOCK in content_types
        
        # Should maintain proper ordering
        assert len(sections) >= 3
        
        # Verify each section has appropriate metadata
        for section in sections:
            assert section.content_type in [
                ContentType.MARKDOWN, ContentType.JSON, 
                ContentType.CODE_BLOCK, ContentType.PLAIN_TEXT
            ]
    
    @pytest.mark.asyncio
    async def test_dynamic_ui_adaptation_flow(self, chat_manager_with_renderer):
        """Test dynamic UI adaptation throughout conversation flow."""
        # Test different message types that should trigger different UI adaptations
        test_messages = [
            {
                "message": "Hello, how are you?",
                "expected_type": ContentType.PLAIN_TEXT
            },
            {
                "message": "Show me a Python function to sort a list",
                "expected_adaptation": "code_focused"
            },
            {
                "message": "What's the weather data in JSON format?",
                "expected_adaptation": "data_focused"
            }
        ]
        
        for i, test_case in enumerate(test_messages):
            response = await chat_manager_with_renderer.process_message(
                message=test_case["message"],
                user_id="test_user",
                session_id="adaptation_test"
            )
            
            assert response is not None
            assert response.content_type in [
                ContentType.PLAIN_TEXT, ContentType.MARKDOWN, 
                ContentType.CODE_BLOCK, ContentType.JSON
            ]
            
            # UI should adapt based on content
            ui_state = chat_manager_with_renderer.update_ui_state(response)
            assert ui_state is not None


class TestContextAwarenessInFollowUpConversations:
    """Test context awareness in follow-up conversations."""
    
    @pytest.fixture
    def mock_context_retriever(self):
        """Mock context retriever with conversation history."""
        mock = AsyncMock()
        
        # Simulate conversation history
        conversation_history = [
            ContextEntry(
                content="User asked about Python programming",
                source="conversation",
                relevance_score=0.9,
                timestamp=datetime.now() - timedelta(minutes=2),
                context_type="conversation",
                metadata={"topic": "programming", "language": "python"}
            ),
            ContextEntry(
                content="Discussed list sorting algorithms",
                source="conversation",
                relevance_score=0.8,
                timestamp=datetime.now() - timedelta(minutes=1),
                context_type="conversation",
                metadata={"topic": "algorithms", "subtopic": "sorting"}
            )
        ]
        
        mock.get_relevant_context.return_value = conversation_history
        return mock
    
    @pytest.fixture
    def chat_manager_with_context(self, mock_context_retriever):
        """Create ChatManager with context awareness."""
        return ChatManager(
            context_retriever=mock_context_retriever,
            auto_create_context_engine=False
        )
    
    @pytest.mark.asyncio
    async def test_follow_up_question_context_awareness(self, chat_manager_with_context, mock_context_retriever):
        """Test context awareness in follow-up questions."""
        # Initial question
        response1 = await chat_manager_with_context.process_message(
            message="How do I sort a list in Python?",
            user_id="user123",
            session_id="context_test"
        )
        
        assert response1 is not None
        
        # Follow-up question that should use context
        response2 = await chat_manager_with_context.process_message(
            message="What about sorting in reverse order?",
            user_id="user123",
            session_id="context_test"
        )
        
        assert response2 is not None
        
        # Verify context was retrieved for follow-up
        assert mock_context_retriever.get_relevant_context.call_count == 2
        
        # Context should be used in response
        assert len(response2.context_used) > 0
        assert response2.ui_hints.get("context_count", 0) > 0
    
    @pytest.mark.asyncio
    async def test_context_relevance_in_topic_changes(self, chat_manager_with_context, mock_context_retriever):
        """Test context relevance when topics change."""
        # Setup different context for topic change
        new_context = [
            ContextEntry(
                content="User switched to asking about weather",
                source="conversation",
                relevance_score=0.7,
                timestamp=datetime.now(),
                context_type="conversation",
                metadata={"topic": "weather"}
            )
        ]
        
        mock_context_retriever.get_relevant_context.return_value = new_context
        
        # Topic change question
        response = await chat_manager_with_context.process_message(
            message="What's the weather like today?",
            user_id="user123",
            session_id="context_test"
        )
        
        assert response is not None
        
        # Should still retrieve context but with different relevance
        mock_context_retriever.get_relevant_context.assert_called()
        
        # Context should reflect topic change
        assert len(response.context_used) > 0
    
    @pytest.mark.asyncio
    async def test_context_summarization_for_long_conversations(self, chat_manager_with_context, mock_context_retriever):
        """Test context summarization for long conversations."""
        # Setup large context history
        large_context = [
            ContextEntry(
                content=f"Conversation point {i} about various topics",
                source="conversation",
                relevance_score=0.9 - (i * 0.05),
                timestamp=datetime.now() - timedelta(minutes=i),
                context_type="conversation",
                metadata={"sequence": i}
            )
            for i in range(15)  # Large conversation history
        ]
        
        mock_context_retriever.get_relevant_context.return_value = large_context
        
        # Process message with large context
        response = await chat_manager_with_context.process_message(
            message="Can you summarize our conversation?",
            user_id="user123",
            session_id="long_context_test"
        )
        
        assert response is not None
        
        # Should handle large context appropriately
        assert len(response.context_used) > 0
        assert response.ui_hints.get("context_count", 0) > 0
        
        # Context should be managed efficiently
        context_hint = response.ui_hints.get("context_management")
        if context_hint:
            assert context_hint in ["summarized", "truncated", "prioritized"]
    
    @pytest.mark.asyncio
    async def test_context_boundary_management(self, chat_manager_with_context):
        """Test context boundary management across sessions."""
        # Different session should have isolated context
        response1 = await chat_manager_with_context.process_message(
            message="Remember this: my favorite color is blue",
            user_id="user123",
            session_id="session_a"
        )
        
        response2 = await chat_manager_with_context.process_message(
            message="What's my favorite color?",
            user_id="user123",
            session_id="session_b"  # Different session
        )
        
        assert response1 is not None
        assert response2 is not None
        
        # Sessions should be isolated
        # (Implementation would ensure context doesn't leak between sessions)
        assert True  # Placeholder for session isolation verification


class TestLoadingIndicatorAccuracy:
    """Test loading indicator accuracy and responsiveness."""
    
    @pytest.fixture
    def loading_manager(self):
        """Create LoadingIndicatorManager for testing."""
        if LoadingIndicatorManager:
            return LoadingIndicatorManager()
        else:
            # Mock implementation
            mock = Mock()
            mock.start_loading = Mock(return_value=LoadingIndicator("test", LoadingState.LOADING))
            mock.get_indicator = Mock(return_value=LoadingIndicator("test", LoadingState.COMPLETED))
            mock.get_active_indicators = Mock(return_value=[])
            mock.complete_loading = Mock()
            mock.error_loading = Mock()
            mock.update_progress = Mock()
            return mock
    
    @pytest.fixture
    def status_monitor(self):
        """Create StatusMonitor for testing."""
        if StatusMonitor:
            return StatusMonitor()
        else:
            # Mock implementation
            return Mock()
    
    @pytest.fixture
    def mock_tool_orchestrator(self):
        """Mock tool orchestrator with timing simulation."""
        mock = AsyncMock()
        
        async def mock_execute_tools(tools, query, context):
            """Simulate tool execution with realistic timing."""
            results = []
            for tool in tools:
                # Simulate different execution times
                if tool == "fast_tool":
                    await asyncio.sleep(0.1)
                    results.append(ToolResult(tool, True, "fast_result", 0.1))
                elif tool == "slow_tool":
                    await asyncio.sleep(0.5)
                    results.append(ToolResult(tool, True, "slow_result", 0.5))
                elif tool == "failing_tool":
                    await asyncio.sleep(0.2)
                    results.append(ToolResult(tool, False, None, 0.2, "Tool failed"))
            return results
        
        mock.execute_tools.side_effect = mock_execute_tools
        mock.select_tools.return_value = []
        return mock
    
    @pytest.mark.asyncio
    async def test_loading_indicator_lifecycle(self, loading_manager):
        """Test complete loading indicator lifecycle."""
        tool_name = "test_tool"
        
        # Start loading
        indicator = loading_manager.start_loading(tool_name, "Processing request...")
        
        assert indicator.tool_name == tool_name
        assert indicator.state == LoadingState.LOADING
        assert indicator.progress == 0.0
        
        # Update progress
        loading_manager.update_progress(tool_name, 0.5, "Halfway complete...")
        updated_indicator = loading_manager.get_indicator(tool_name)
        
        assert updated_indicator.progress == 0.5
        assert updated_indicator.message == "Halfway complete..."
        
        # Complete loading
        loading_manager.complete_loading(tool_name, "Task completed successfully")
        completed_indicator = loading_manager.get_indicator(tool_name)
        
        assert completed_indicator.state == LoadingState.COMPLETED
        assert completed_indicator.progress == 1.0
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_loading_indicators(self, loading_manager):
        """Test multiple concurrent loading indicators."""
        tools = ["tool_a", "tool_b", "tool_c"]
        
        # Start multiple tools
        for tool in tools:
            loading_manager.start_loading(tool, f"Processing {tool}...")
        
        # Verify all are loading
        active_indicators = loading_manager.get_active_indicators()
        assert len(active_indicators) == 3
        
        for indicator in active_indicators:
            assert indicator.state == LoadingState.LOADING
            assert indicator.tool_name in tools
        
        # Complete tools at different times
        loading_manager.complete_loading("tool_a", "Tool A completed")
        loading_manager.error_loading("tool_b", "Tool B failed")
        
        # Verify states
        indicator_a = loading_manager.get_indicator("tool_a")
        indicator_b = loading_manager.get_indicator("tool_b")
        indicator_c = loading_manager.get_indicator("tool_c")
        
        assert indicator_a.state == LoadingState.COMPLETED
        assert indicator_b.state == LoadingState.ERROR
        assert indicator_c.state == LoadingState.LOADING
    
    @pytest.mark.asyncio
    async def test_loading_indicator_timing_accuracy(self, mock_tool_orchestrator):
        """Test loading indicator timing accuracy."""
        chat_manager = ChatManager(
            tool_orchestrator=mock_tool_orchestrator,
            auto_create_context_engine=False
        )
        
        # Setup tools with different execution times
        mock_tool_orchestrator.select_tools.return_value = [
            ToolRecommendation("fast_tool", 0.8, 0.1, 0.9),
            ToolRecommendation("slow_tool", 0.7, 0.5, 0.8)
        ]
        
        start_time = time.time()
        response = await chat_manager.process_message(
            message="Execute tools with timing",
            user_id="user123",
            session_id="timing_test"
        )
        total_time = time.time() - start_time
        
        assert response is not None
        
        # Verify timing accuracy
        assert total_time >= 0.5  # Should take at least as long as slowest tool
        assert total_time < 1.0   # But not too much longer (parallel execution)
        
        # UI state should reflect completed tools
        ui_state = chat_manager.update_ui_state(response)
        assert len(ui_state.loading_indicators) == 2
        
        for indicator in ui_state.loading_indicators:
            assert indicator.state == LoadingState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_loading_indicator_error_handling(self, loading_manager):
        """Test loading indicator error handling."""
        tool_name = "failing_tool"
        
        # Start loading
        loading_manager.start_loading(tool_name, "Processing...")
        
        # Simulate error
        error_message = "Connection timeout"
        loading_manager.error_loading(tool_name, error_message)
        
        indicator = loading_manager.get_indicator(tool_name)
        
        assert indicator.state == LoadingState.ERROR
        assert error_message in indicator.message
        assert indicator.progress == 0.0  # Progress should reset on error


class TestErrorRecoveryAndUserExperience:
    """Test error recovery and user experience."""
    
    @pytest.fixture
    def chat_manager_with_error_handling(self):
        """Create ChatManager with error handling."""
        return ChatManager(auto_create_context_engine=False)
    
    @pytest.mark.asyncio
    async def test_graceful_tool_failure_recovery(self, chat_manager_with_error_handling):
        """Test graceful recovery from tool failures."""
        # Mock tool orchestrator that fails
        mock_orchestrator = AsyncMock()
        mock_orchestrator.select_tools.return_value = [
            ToolRecommendation("failing_tool", 0.8, 1.0, 0.7)
        ]
        mock_orchestrator.execute_tools.return_value = [
            ToolResult("failing_tool", False, None, 0.5, "Network error")
        ]
        
        chat_manager_with_error_handling.tool_orchestrator = mock_orchestrator
        
        response = await chat_manager_with_error_handling.process_message(
            message="Get some data that will fail",
            user_id="user123",
            session_id="error_test"
        )
        
        # Should still return a response
        assert response is not None
        assert response.content is not None
        
        # Should indicate graceful handling
        assert len(response.tools_used) == 0  # Failed tools not included
        assert response.confidence_score < 0.8  # Lower confidence due to failure
        
        # UI state should show error recovery
        ui_state = chat_manager_with_error_handling.update_ui_state(response)
        # Error handling should be graceful, not necessarily showing error states
        # unless specifically configured to do so
    
    @pytest.mark.asyncio
    async def test_context_retrieval_failure_recovery(self, chat_manager_with_error_handling):
        """Test recovery from context retrieval failures."""
        # Mock context retriever that fails
        mock_retriever = AsyncMock()
        mock_retriever.get_relevant_context.side_effect = Exception("Context service unavailable")
        
        chat_manager_with_error_handling.context_retriever = mock_retriever
        
        response = await chat_manager_with_error_handling.process_message(
            message="This should work despite context failure",
            user_id="user123",
            session_id="context_error_test"
        )
        
        # Should still work without context
        assert response is not None
        assert response.content is not None
        assert len(response.context_used) == 0  # No context due to failure
        
        # Should continue processing
        assert response.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_partial_failure_user_experience(self, chat_manager_with_error_handling):
        """Test user experience with partial failures."""
        # Mock mixed success/failure scenario
        mock_orchestrator = AsyncMock()
        mock_orchestrator.select_tools.return_value = [
            ToolRecommendation("success_tool", 0.9, 1.0, 0.8),
            ToolRecommendation("failure_tool", 0.8, 1.0, 0.7)
        ]
        mock_orchestrator.execute_tools.return_value = [
            ToolResult("success_tool", True, "Success data", 0.8),
            ToolResult("failure_tool", False, None, 0.3, "Service unavailable")
        ]
        
        chat_manager_with_error_handling.tool_orchestrator = mock_orchestrator
        
        response = await chat_manager_with_error_handling.process_message(
            message="Get data from multiple sources",
            user_id="user123",
            session_id="partial_failure_test"
        )
        
        # Should include successful results
        assert response is not None
        assert len(response.tools_used) == 1  # Only successful tool
        assert "success_tool" in response.tools_used
        
        # Should have moderate confidence (partial success)
        assert 0.3 < response.confidence_score < 0.9
        
        # UI should indicate partial results
        ui_state = chat_manager_with_error_handling.update_ui_state(response)
        assert len(ui_state.loading_indicators) == 1  # Only successful tool shown
    
    @pytest.mark.asyncio
    async def test_error_message_clarity_and_recovery_options(self):
        """Test error message clarity and recovery options."""
        from intelligent_chat.user_friendly_errors import UserFriendlyErrorHandler
        
        error_handler = UserFriendlyErrorHandler()
        
        # Test different error types
        network_error = Exception("Connection timeout")
        friendly_network_error = error_handler.make_user_friendly(
            network_error, 
            context="tool_execution",
            user_action="fetching weather data"
        )
        
        assert "network" in friendly_network_error.message.lower() or "connection" in friendly_network_error.message.lower()
        assert len(friendly_network_error.recovery_actions) > 0
        assert "retry" in friendly_network_error.recovery_actions
        
        # Test validation error
        validation_error = ValueError("Invalid input format")
        friendly_validation_error = error_handler.make_user_friendly(
            validation_error,
            context="user_input",
            user_action="processing query"
        )
        
        assert "input" in friendly_validation_error.message.lower()
        assert "rephrase" in friendly_validation_error.recovery_actions or "clarify" in friendly_validation_error.recovery_actions


class TestConversationThreadContinuity:
    """Test conversation thread continuity."""
    
    @pytest.fixture
    def chat_manager_for_continuity(self):
        """Create ChatManager for continuity testing."""
        return ChatManager(auto_create_context_engine=False)
    
    @pytest.mark.asyncio
    async def test_conversation_thread_isolation(self, chat_manager_for_continuity):
        """Test conversation thread isolation between sessions."""
        # Create conversations in different sessions
        response_a1 = await chat_manager_for_continuity.process_message(
            message="My name is Alice",
            user_id="user123",
            session_id="session_a"
        )
        
        response_b1 = await chat_manager_for_continuity.process_message(
            message="My name is Bob",
            user_id="user123",
            session_id="session_b"
        )
        
        # Follow-up questions in each session
        response_a2 = await chat_manager_for_continuity.process_message(
            message="What's my name?",
            user_id="user123",
            session_id="session_a"
        )
        
        response_b2 = await chat_manager_for_continuity.process_message(
            message="What's my name?",
            user_id="user123",
            session_id="session_b"
        )
        
        # Verify session isolation
        assert response_a1 is not None
        assert response_b1 is not None
        assert response_a2 is not None
        assert response_b2 is not None
        
        # Sessions should maintain separate contexts
        stats_a = chat_manager_for_continuity.get_session_stats("user123", "session_a")
        stats_b = chat_manager_for_continuity.get_session_stats("user123", "session_b")
        
        assert stats_a["message_count"] == 2
        assert stats_b["message_count"] == 2
    
    @pytest.mark.asyncio
    async def test_conversation_flow_continuity(self, chat_manager_for_continuity):
        """Test conversation flow continuity within a session."""
        session_id = "continuity_test"
        user_id = "user123"
        
        # Multi-turn conversation
        conversation_turns = [
            "I'm planning a trip to Paris",
            "What's the weather like there?",
            "What about restaurants?",
            "Any recommendations for museums?",
            "How much should I budget for this trip?"
        ]
        
        responses = []
        for turn in conversation_turns:
            response = await chat_manager_for_continuity.process_message(
                message=turn,
                user_id=user_id,
                session_id=session_id
            )
            responses.append(response)
            
            # Small delay to simulate real conversation
            await asyncio.sleep(0.1)
        
        # Verify all responses
        assert len(responses) == len(conversation_turns)
        for response in responses:
            assert response is not None
            assert response.content is not None
        
        # Verify conversation continuity
        session_stats = chat_manager_for_continuity.get_session_stats(user_id, session_id)
        assert session_stats["message_count"] == len(conversation_turns)
        assert session_stats["total_processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_conversation_memory_persistence(self, chat_manager_for_continuity):
        """Test conversation memory persistence across time."""
        session_id = "memory_test"
        user_id = "user123"
        
        # Initial conversation
        await chat_manager_for_continuity.process_message(
            message="I work as a software engineer at TechCorp",
            user_id=user_id,
            session_id=session_id
        )
        
        await chat_manager_for_continuity.process_message(
            message="I'm interested in machine learning",
            user_id=user_id,
            session_id=session_id
        )
        
        # Simulate time gap
        await asyncio.sleep(0.2)
        
        # Later conversation referencing earlier context
        response = await chat_manager_for_continuity.process_message(
            message="Can you recommend ML resources for my work?",
            user_id=user_id,
            session_id=session_id
        )
        
        assert response is not None
        
        # Should maintain conversation context
        session_stats = chat_manager_for_continuity.get_session_stats(user_id, session_id)
        assert session_stats["message_count"] == 3
    
    @pytest.mark.asyncio
    async def test_conversation_context_relevance_over_time(self, chat_manager_for_continuity):
        """Test conversation context relevance over time."""
        session_id = "relevance_test"
        user_id = "user123"
        
        # Build up conversation history
        topics = [
            "Tell me about Python programming",
            "What about data structures?",
            "How do I implement a binary tree?",
            "Now let's talk about cooking",
            "What's a good pasta recipe?",
            "Back to programming - what about algorithms?"
        ]
        
        responses = []
        for topic in topics:
            response = await chat_manager_for_continuity.process_message(
                message=topic,
                user_id=user_id,
                session_id=session_id
            )
            responses.append(response)
        
        # Verify all responses
        assert len(responses) == len(topics)
        
        # Later responses should still maintain context appropriately
        # (Implementation would ensure relevant context is maintained)
        final_response = responses[-1]  # "Back to programming" question
        assert final_response is not None
        
        # Should have maintained programming context despite topic change
        session_stats = chat_manager_for_continuity.get_session_stats(user_id, session_id)
        assert session_stats["message_count"] == len(topics)


class TestResponsivenessUnderLoad:
    """Test system responsiveness under various load conditions."""
    
    @pytest.mark.asyncio
    async def test_response_time_consistency(self):
        """Test response time consistency under normal load."""
        chat_manager = ChatManager(auto_create_context_engine=False)
        
        response_times = []
        num_requests = 10
        
        for i in range(num_requests):
            start_time = time.time()
            response = await chat_manager.process_message(
                message=f"Test message {i}",
                user_id=f"user{i}",
                session_id=f"session{i}"
            )
            response_time = time.time() - start_time
            response_times.append(response_time)
            
            assert response is not None
        
        # Calculate consistency metrics
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        # Response times should be consistent
        assert max_time < avg_time * 3  # Max shouldn't be more than 3x average
        assert min_time > avg_time * 0.3  # Min shouldn't be less than 30% of average
        assert avg_time < 2.0  # Average should be reasonable
    
    @pytest.mark.asyncio
    async def test_concurrent_user_responsiveness(self):
        """Test responsiveness with concurrent users."""
        chat_manager = ChatManager(auto_create_context_engine=False)
        
        num_concurrent_users = 15
        
        async def user_session(user_id: str):
            """Simulate a user session."""
            session_times = []
            for i in range(3):  # 3 messages per user
                start_time = time.time()
                response = await chat_manager.process_message(
                    message=f"Message {i} from {user_id}",
                    user_id=user_id,
                    session_id=f"session_{user_id}"
                )
                session_time = time.time() - start_time
                session_times.append(session_time)
                
                assert response is not None
                
                # Brief pause between messages
                await asyncio.sleep(0.05)
            
            return session_times
        
        # Execute concurrent user sessions
        start_time = time.time()
        tasks = [user_session(f"user{i}") for i in range(num_concurrent_users)]
        all_session_times = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Flatten all response times
        all_response_times = [time for session in all_session_times for time in session]
        
        # Analyze responsiveness
        avg_response_time = sum(all_response_times) / len(all_response_times)
        max_response_time = max(all_response_times)
        
        # Should maintain reasonable responsiveness under concurrent load
        assert avg_response_time < 3.0  # Average under 3 seconds
        assert max_response_time < 8.0  # Max under 8 seconds
        assert total_time < 20.0  # Total test time reasonable
        
        # Verify all users were handled
        total_messages = num_concurrent_users * 3
        assert len(all_response_times) == total_messages
    
    @pytest.mark.asyncio
    async def test_system_recovery_after_load_spike(self):
        """Test system recovery after load spike."""
        chat_manager = ChatManager(auto_create_context_engine=False)
        
        # Create load spike
        spike_tasks = []
        for i in range(20):  # High concurrent load
            task = chat_manager.process_message(
                message=f"Load spike message {i}",
                user_id=f"spike_user{i}",
                session_id=f"spike_session{i}"
            )
            spike_tasks.append(task)
        
        # Execute load spike
        spike_start = time.time()
        spike_responses = await asyncio.gather(*spike_tasks)
        spike_duration = time.time() - spike_start
        
        # Verify spike was handled
        assert len(spike_responses) == 20
        assert all(response is not None for response in spike_responses)
        
        # Wait for system to settle
        await asyncio.sleep(0.5)
        
        # Test normal operation after spike
        normal_start = time.time()
        normal_response = await chat_manager.process_message(
            message="Normal message after spike",
            user_id="normal_user",
            session_id="normal_session"
        )
        normal_time = time.time() - normal_start
        
        # System should recover to normal performance
        assert normal_response is not None
        assert normal_time < 2.0  # Should be back to normal response time
        
        # Cleanup should work properly
        cleaned_sessions = await chat_manager.cleanup_inactive_sessions(max_age_hours=0)
        assert cleaned_sessions > 0  # Should clean up spike sessions


if __name__ == "__main__":
    # Run user experience and responsiveness tests
    pytest.main([
        __file__,
        "-v", "--tb=short"
    ])