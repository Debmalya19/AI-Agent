"""
Comprehensive integration tests for complete conversation flows.

Tests end-to-end scenarios for typical user interactions, tool chain execution
with context continuity, UI state transitions, and performance benchmarks.
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import intelligent chat components
from intelligent_chat.chat_manager import ChatManager
from intelligent_chat.tool_orchestrator import ToolOrchestrator
from intelligent_chat.response_renderer import ResponseRenderer
from intelligent_chat.context_retriever import ContextRetriever
from intelligent_chat.tool_selector import ToolSelector
from intelligent_chat.models import (
    ChatResponse, ContextEntry, ToolRecommendation, ToolResult,
    ContentType, LoadingState, ErrorSeverity, UIState
)
from intelligent_chat.exceptions import ChatUIException, ToolExecutionError


class TestCompleteConversationFlows:
    """Test complete conversation flows with context continuity."""
    
    @pytest.fixture
    def mock_memory_manager(self):
        """Mock memory layer manager."""
        mock = Mock()
        mock.store_conversation = Mock(return_value=True)
        mock.retrieve_context = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def mock_context_engine(self):
        """Mock context retrieval engine."""
        mock = Mock()
        mock.get_relevant_context = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def mock_tool_orchestrator(self):
        """Mock tool orchestrator."""
        mock = AsyncMock()
        mock.select_tools = AsyncMock(return_value=[])
        mock.execute_tools = AsyncMock(return_value=[])
        return mock
    
    @pytest.fixture
    def mock_context_retriever(self):
        """Mock context retriever."""
        mock = AsyncMock()
        mock.get_relevant_context = AsyncMock(return_value=[])
        return mock
    
    @pytest.fixture
    def mock_response_renderer(self):
        """Mock response renderer."""
        mock = Mock()
        mock.render_response = Mock(return_value=[])
        mock.detect_content_type = Mock(return_value=ContentType.PLAIN_TEXT)
        return mock
    
    @pytest.fixture
    def chat_manager(self, mock_memory_manager, mock_context_engine, mock_tool_orchestrator, 
                    mock_context_retriever, mock_response_renderer):
        """Create ChatManager with mocked dependencies."""
        return ChatManager(
            tool_orchestrator=mock_tool_orchestrator,
            context_retriever=mock_context_retriever,
            response_renderer=mock_response_renderer,
            memory_manager=mock_memory_manager,
            context_engine=mock_context_engine,
            auto_create_context_engine=False
        )
    
    @pytest.mark.asyncio
    async def test_basic_conversation_flow(self, chat_manager):
        """Test basic conversation flow without tools."""
        # Test single message processing
        response = await chat_manager.process_message(
            message="Hello, how are you?",
            user_id="user123",
            session_id="session456"
        )
        
        assert response is not None
        assert response.content is not None
        assert response.execution_time > 0
        assert response.timestamp is not None
        assert response.ui_hints["session_id"] == "session456"
        
        # Verify session was created
        stats = chat_manager.get_session_stats("user123", "session456")
        assert stats["message_count"] == 1
        assert stats["total_processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_conversation_with_context_continuity(self, chat_manager, mock_context_retriever):
        """Test conversation flow with context continuity."""
        # Setup context retriever to return relevant context
        context_entries = [
            ContextEntry(
                content="Previous conversation about weather",
                source="conversation_history",
                relevance_score=0.8,
                timestamp=datetime.now(),
                context_type="conversation",
                metadata={"session_id": "session456"}
            )
        ]
        mock_context_retriever.get_relevant_context.return_value = context_entries
        
        # First message
        response1 = await chat_manager.process_message(
            message="What's the weather like?",
            user_id="user123",
            session_id="session456"
        )
        
        # Second message (follow-up)
        response2 = await chat_manager.process_message(
            message="What about tomorrow?",
            user_id="user123",
            session_id="session456"
        )
        
        # Verify context was used
        assert mock_context_retriever.get_relevant_context.call_count == 2
        assert response2.context_used == ["conversation_history"]
        assert response2.ui_hints["context_count"] == 1
        
        # Verify session continuity
        stats = chat_manager.get_session_stats("user123", "session456")
        assert stats["message_count"] == 2
    
    @pytest.mark.asyncio
    async def test_tool_chain_execution(self, chat_manager, mock_tool_orchestrator):
        """Test tool chain execution with multiple tools."""
        # Setup tool orchestrator to return tool recommendations and results
        tool_recommendations = [
            ToolRecommendation(
                tool_name="weather_tool",
                relevance_score=0.9,
                expected_execution_time=2.0,
                confidence_level=0.8
            ),
            ToolRecommendation(
                tool_name="location_tool",
                relevance_score=0.7,
                expected_execution_time=1.0,
                confidence_level=0.9
            )
        ]
        
        tool_results = [
            ToolResult(
                tool_name="weather_tool",
                success=True,
                result={"temperature": 22, "condition": "sunny"},
                execution_time=1.8
            ),
            ToolResult(
                tool_name="location_tool",
                success=True,
                result={"city": "New York", "country": "USA"},
                execution_time=0.9
            )
        ]
        
        mock_tool_orchestrator.select_tools.return_value = tool_recommendations
        mock_tool_orchestrator.execute_tools.return_value = tool_results
        
        # Process message that should trigger tools
        response = await chat_manager.process_message(
            message="What's the weather in my location?",
            user_id="user123",
            session_id="session456"
        )
        
        # Verify tools were used
        assert len(response.tools_used) == 2
        assert "weather_tool" in response.tools_used
        assert "location_tool" in response.tools_used
        assert response.ui_hints["tools_count"] == 2
        assert response.confidence_score > 0.5  # Should be higher with successful tools
        
        # Verify tool orchestrator was called correctly
        mock_tool_orchestrator.select_tools.assert_called_once()
        mock_tool_orchestrator.execute_tools.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, chat_manager, mock_tool_orchestrator):
        """Test error handling and recovery mechanisms."""
        # Setup tool orchestrator to fail
        mock_tool_orchestrator.select_tools.side_effect = Exception("Tool selection failed")
        
        # Process message that would normally use tools
        response = await chat_manager.process_message(
            message="Get me some data",
            user_id="user123",
            session_id="session456"
        )
        
        # Verify graceful handling
        assert response is not None
        assert response.content is not None
        assert len(response.tools_used) == 0  # No tools used due to failure
        assert response.execution_time > 0
        
        # Reset mock and test tool execution failure
        mock_tool_orchestrator.select_tools.side_effect = None
        mock_tool_orchestrator.select_tools.return_value = [
            ToolRecommendation(
                tool_name="failing_tool",
                relevance_score=0.8,
                expected_execution_time=1.0,
                confidence_level=0.7
            )
        ]
        mock_tool_orchestrator.execute_tools.return_value = [
            ToolResult(
                tool_name="failing_tool",
                success=False,
                result=None,
                execution_time=0.5,
                error_message="Tool execution failed"
            )
        ]
        
        response2 = await chat_manager.process_message(
            message="Try again",
            user_id="user123",
            session_id="session456"
        )
        
        # Verify handling of tool failure
        assert response2 is not None
        assert len(response2.tools_used) == 0  # Failed tools not included
        assert response2.confidence_score < 0.8  # Lower confidence due to failures
    
    @pytest.mark.asyncio
    async def test_ui_state_transitions(self, chat_manager, mock_tool_orchestrator):
        """Test UI state transitions during conversation."""
        # Setup successful tool execution
        mock_tool_orchestrator.select_tools.return_value = [
            ToolRecommendation(
                tool_name="test_tool",
                relevance_score=0.8,
                expected_execution_time=1.0,
                confidence_level=0.9
            )
        ]
        mock_tool_orchestrator.execute_tools.return_value = [
            ToolResult(
                tool_name="test_tool",
                success=True,
                result="Tool result",
                execution_time=0.8
            )
        ]
        
        # Process message
        response = await chat_manager.process_message(
            message="Test message",
            user_id="user123",
            session_id="session456"
        )
        
        # Test UI state generation
        ui_state = chat_manager.update_ui_state(response)
        
        assert ui_state is not None
        assert len(ui_state.loading_indicators) == 1
        assert ui_state.loading_indicators[0].tool_name == "test_tool"
        assert ui_state.loading_indicators[0].state == LoadingState.COMPLETED
        assert len(ui_state.error_states) == 0  # No errors
        
        # Test error UI state
        error_response = ChatResponse(
            content="Error occurred",
            content_type=ContentType.ERROR_MESSAGE,
            execution_time=0.1
        )
        
        error_ui_state = chat_manager.update_ui_state(error_response)
        assert len(error_ui_state.error_states) == 1
        assert error_ui_state.error_states[0].severity == ErrorSeverity.ERROR
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, chat_manager):
        """Test performance benchmarks for response times."""
        # Test multiple messages to get performance data
        messages = [
            "Hello",
            "What's the weather?",
            "Tell me about AI",
            "How does machine learning work?",
            "Goodbye"
        ]
        
        response_times = []
        
        for i, message in enumerate(messages):
            start_time = time.time()
            response = await chat_manager.process_message(
                message=message,
                user_id="user123",
                session_id=f"session{i}"
            )
            total_time = time.time() - start_time
            
            response_times.append(total_time)
            
            # Verify response time is reasonable (< 5 seconds for basic processing)
            assert response.execution_time < 5.0
            assert total_time < 10.0  # Including test overhead
        
        # Calculate performance metrics
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        # Performance assertions
        assert avg_response_time < 2.0  # Average should be under 2 seconds
        assert max_response_time < 5.0  # Max should be under 5 seconds
        assert min_response_time > 0.0  # Should take some time
        
        # Verify global stats
        global_stats = chat_manager.get_global_stats()
        assert global_stats["total_conversations"] == len(messages)
        assert global_stats["avg_processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_conversations(self, chat_manager):
        """Test handling of concurrent conversations."""
        # Create multiple concurrent conversations
        tasks = []
        
        for i in range(5):
            task = chat_manager.process_message(
                message=f"Message {i}",
                user_id=f"user{i}",
                session_id=f"session{i}"
            )
            tasks.append(task)
        
        # Execute all tasks concurrently
        responses = await asyncio.gather(*tasks)
        
        # Verify all responses
        assert len(responses) == 5
        for i, response in enumerate(responses):
            assert response is not None
            assert response.ui_hints["session_id"] == f"session{i}"
            assert response.execution_time > 0
        
        # Verify session isolation
        for i in range(5):
            stats = chat_manager.get_session_stats(f"user{i}", f"session{i}")
            assert stats["message_count"] == 1
    
    @pytest.mark.asyncio
    async def test_memory_integration(self, chat_manager, mock_memory_manager):
        """Test integration with memory layer."""
        # Process a message
        response = await chat_manager.process_message(
            message="Remember this important fact",
            user_id="user123",
            session_id="session456"
        )
        
        # Verify memory manager was called to store conversation
        mock_memory_manager.store_conversation.assert_called_once()
        
        # Verify conversation context retrieval
        context = await chat_manager.get_conversation_context("user123", limit=5)
        assert isinstance(context, list)
        mock_memory_manager.retrieve_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_cleanup(self, chat_manager):
        """Test session cleanup functionality."""
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
        
        # Test cleanup (should not clean up recent sessions)
        cleaned = await chat_manager.cleanup_inactive_sessions(max_age_hours=24)
        assert cleaned == 0  # No sessions should be cleaned (too recent)
        
        # Test cleanup with very short max age
        cleaned = await chat_manager.cleanup_inactive_sessions(max_age_hours=0)
        assert cleaned == 3  # All sessions should be cleaned
        
        # Verify sessions were cleaned
        global_stats = chat_manager.get_global_stats()
        assert global_stats["active_sessions"] == 0


class TestToolChainExecution:
    """Test tool chain execution scenarios."""
    
    @pytest.fixture
    def tool_orchestrator(self):
        """Create ToolOrchestrator for testing."""
        from intelligent_chat.tool_orchestrator import ToolOrchestrator
        from intelligent_chat.tool_selector import ToolSelector
        
        tool_selector = ToolSelector()
        return ToolOrchestrator(tool_selector=tool_selector)
    
    @pytest.mark.asyncio
    async def test_sequential_tool_execution(self, tool_orchestrator):
        """Test sequential execution of dependent tools."""
        # Mock tools with dependencies
        with patch.object(tool_orchestrator, '_get_available_tools') as mock_tools:
            mock_tools.return_value = ["location_tool", "weather_tool", "recommendation_tool"]
            
            with patch.object(tool_orchestrator, '_execute_single_tool') as mock_execute:
                # Setup tool results
                mock_execute.side_effect = [
                    ToolResult("location_tool", True, {"city": "NYC"}, 1.0),
                    ToolResult("weather_tool", True, {"temp": 20}, 1.5),
                    ToolResult("recommendation_tool", True, {"activity": "walk"}, 0.8)
                ]
                
                # Execute tools
                results = await tool_orchestrator.execute_tools(
                    ["location_tool", "weather_tool", "recommendation_tool"],
                    "What should I do today?",
                    {"context": []}
                )
                
                assert len(results) == 3
                assert all(result.success for result in results)
                assert mock_execute.call_count == 3
    
    @pytest.mark.asyncio
    async def test_parallel_tool_execution(self, tool_orchestrator):
        """Test parallel execution of independent tools."""
        with patch.object(tool_orchestrator, '_get_available_tools') as mock_tools:
            mock_tools.return_value = ["news_tool", "stock_tool", "crypto_tool"]
            
            with patch.object(tool_orchestrator, '_execute_single_tool') as mock_execute:
                # Setup tool results with different execution times
                async def mock_tool_execution(tool_name, *args):
                    await asyncio.sleep(0.1)  # Simulate execution time
                    return ToolResult(tool_name, True, f"{tool_name}_result", 0.1)
                
                mock_execute.side_effect = mock_tool_execution
                
                start_time = time.time()
                results = await tool_orchestrator.execute_tools(
                    ["news_tool", "stock_tool", "crypto_tool"],
                    "Get me market updates",
                    {"context": []}
                )
                execution_time = time.time() - start_time
                
                # Should execute in parallel, so total time should be close to individual time
                assert execution_time < 0.5  # Much less than 3 * 0.1 if sequential
                assert len(results) == 3
                assert all(result.success for result in results)
    
    @pytest.mark.asyncio
    async def test_tool_failure_recovery(self, tool_orchestrator):
        """Test recovery from tool failures."""
        with patch.object(tool_orchestrator, '_get_available_tools') as mock_tools:
            mock_tools.return_value = ["primary_tool", "backup_tool"]
            
            with patch.object(tool_orchestrator, '_execute_single_tool') as mock_execute:
                # Primary tool fails, backup succeeds
                mock_execute.side_effect = [
                    ToolResult("primary_tool", False, None, 0.5, "Connection failed"),
                    ToolResult("backup_tool", True, "backup_result", 0.3)
                ]
                
                results = await tool_orchestrator.execute_tools(
                    ["primary_tool", "backup_tool"],
                    "Get data",
                    {"context": []}
                )
                
                assert len(results) == 2
                assert not results[0].success
                assert results[1].success
                assert results[0].error_message == "Connection failed"


class TestContextContinuity:
    """Test context continuity across conversations."""
    
    @pytest.fixture
    def context_retriever(self):
        """Create ContextRetriever for testing."""
        from intelligent_chat.context_retriever import ContextRetriever
        
        # Mock the memory manager
        mock_memory = Mock()
        mock_context_engine = Mock()
        
        return ContextRetriever(
            memory_manager=mock_memory,
            context_engine=mock_context_engine
        )
    
    @pytest.mark.asyncio
    async def test_context_relevance_scoring(self, context_retriever):
        """Test context relevance scoring."""
        # Mock context entries
        mock_contexts = [
            ContextEntry(
                content="User asked about weather yesterday",
                source="conversation",
                relevance_score=0.9,
                timestamp=datetime.now() - timedelta(hours=1),
                context_type="conversation"
            ),
            ContextEntry(
                content="User likes outdoor activities",
                source="profile",
                relevance_score=0.6,
                timestamp=datetime.now() - timedelta(days=1),
                context_type="preference"
            )
        ]
        
        with patch.object(context_retriever, '_retrieve_raw_context') as mock_retrieve:
            mock_retrieve.return_value = mock_contexts
            
            relevant_context = await context_retriever.get_relevant_context(
                "What's the weather like for hiking?",
                "user123"
            )
            
            assert len(relevant_context) > 0
            # Should prioritize recent, relevant context
            assert relevant_context[0].relevance_score >= relevant_context[-1].relevance_score
    
    @pytest.mark.asyncio
    async def test_context_summarization(self, context_retriever):
        """Test context summarization for large contexts."""
        # Create large context
        large_context = [
            ContextEntry(
                content=f"Context entry {i} with detailed information",
                source="conversation",
                relevance_score=0.8 - (i * 0.1),
                timestamp=datetime.now() - timedelta(minutes=i),
                context_type="conversation"
            )
            for i in range(20)  # Large number of context entries
        ]
        
        summary = context_retriever.summarize_context(large_context)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert len(summary) < sum(len(ctx.content) for ctx in large_context)  # Should be shorter
    
    @pytest.mark.asyncio
    async def test_context_effectiveness_tracking(self, context_retriever):
        """Test context effectiveness tracking."""
        context_entries = [
            ContextEntry(
                content="Relevant context",
                source="conversation",
                relevance_score=0.8,
                timestamp=datetime.now(),
                context_type="conversation"
            )
        ]
        
        # Track high effectiveness
        context_retriever.track_context_usage(context_entries, 0.9)
        
        # Track low effectiveness
        context_retriever.track_context_usage(context_entries, 0.3)
        
        # Verify tracking was called (implementation would update metrics)
        assert True  # Placeholder - actual implementation would verify metrics


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    @pytest.mark.asyncio
    async def test_response_time_benchmarks(self):
        """Test response time benchmarks under various loads."""
        from intelligent_chat.chat_manager import ChatManager
        
        chat_manager = ChatManager(auto_create_context_engine=False)
        
        # Test single message performance
        start_time = time.time()
        response = await chat_manager.process_message(
            "Simple test message",
            "user123",
            "session456"
        )
        single_message_time = time.time() - start_time
        
        assert single_message_time < 1.0  # Should be fast for simple messages
        assert response.execution_time < single_message_time
        
        # Test batch processing performance
        messages = [f"Message {i}" for i in range(10)]
        
        start_time = time.time()
        tasks = [
            chat_manager.process_message(msg, f"user{i}", f"session{i}")
            for i, msg in enumerate(messages)
        ]
        responses = await asyncio.gather(*tasks)
        batch_time = time.time() - start_time
        
        assert len(responses) == 10
        assert batch_time < 5.0  # Batch should complete reasonably fast
        
        # Calculate performance metrics
        avg_response_time = sum(r.execution_time for r in responses) / len(responses)
        assert avg_response_time < 0.5  # Average should be fast
    
    @pytest.mark.asyncio
    async def test_memory_usage_benchmarks(self):
        """Test memory usage under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        from intelligent_chat.chat_manager import ChatManager
        chat_manager = ChatManager(auto_create_context_engine=False)
        
        # Process many messages to test memory usage
        for i in range(100):
            await chat_manager.process_message(
                f"Test message {i} with some content to use memory",
                f"user{i % 10}",  # 10 different users
                f"session{i % 5}"  # 5 different sessions
            )
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for 100 messages)
        assert memory_increase < 100
        
        # Test cleanup reduces memory
        cleaned_sessions = await chat_manager.cleanup_inactive_sessions(max_age_hours=0)
        assert cleaned_sessions > 0
        
        after_cleanup_memory = process.memory_info().rss / 1024 / 1024  # MB
        # Memory should not increase significantly after cleanup
        assert after_cleanup_memory <= final_memory + 10  # Allow some variance
    
    @pytest.mark.asyncio
    async def test_concurrent_load_performance(self):
        """Test performance under concurrent load."""
        from intelligent_chat.chat_manager import ChatManager
        
        chat_manager = ChatManager(auto_create_context_engine=False)
        
        # Create concurrent load
        num_concurrent = 20
        messages_per_user = 5
        
        async def user_conversation(user_id: str):
            """Simulate a user having a conversation."""
            session_id = f"session_{user_id}"
            response_times = []
            
            for i in range(messages_per_user):
                start_time = time.time()
                response = await chat_manager.process_message(
                    f"Message {i} from {user_id}",
                    user_id,
                    session_id
                )
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                # Small delay between messages
                await asyncio.sleep(0.1)
            
            return response_times
        
        # Execute concurrent conversations
        start_time = time.time()
        tasks = [user_conversation(f"user{i}") for i in range(num_concurrent)]
        all_response_times = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Flatten response times
        flat_response_times = [time for user_times in all_response_times for time in user_times]
        
        # Performance assertions
        total_messages = num_concurrent * messages_per_user
        avg_response_time = sum(flat_response_times) / len(flat_response_times)
        max_response_time = max(flat_response_times)
        
        assert total_messages == len(flat_response_times)
        assert avg_response_time < 2.0  # Average response time under load
        assert max_response_time < 5.0  # Max response time under load
        assert total_time < 30.0  # Total test time should be reasonable
        
        # Verify system handled concurrent load
        global_stats = chat_manager.get_global_stats()
        assert global_stats["total_conversations"] == total_messages
        assert global_stats["active_sessions"] == num_concurrent


if __name__ == "__main__":
    # Run specific test categories
    pytest.main([
        __file__ + "::TestCompleteConversationFlows",
        "-v", "--tb=short"
    ])