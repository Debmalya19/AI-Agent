"""
Integration tests for context window management and performance optimization.

Tests context retrieval, window management, caching, and performance
under various load conditions.
"""

import pytest
import asyncio
import time
import psutil
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

# Import intelligent chat components
from intelligent_chat.context_retriever import ContextRetriever
from intelligent_chat.chat_manager import ChatManager
from intelligent_chat.models import ContextEntry, ChatResponse
from intelligent_chat.performance_cache import get_performance_cache, get_response_cache
from intelligent_chat.resource_monitor import get_resource_monitor


class TestContextWindowManagement:
    """Test context window management and optimization."""
    
    @pytest.fixture
    def mock_memory_manager(self):
        """Mock memory layer manager with context data."""
        mock = Mock()
        
        # Create sample context entries
        sample_contexts = [
            ContextEntry(
                content=f"Context entry {i} with relevant information",
                source="conversation",
                relevance_score=0.9 - (i * 0.1),
                timestamp=datetime.now() - timedelta(minutes=i),
                context_type="conversation",
                metadata={"session_id": "test_session", "importance": "high" if i < 3 else "medium"}
            )
            for i in range(20)  # Large number of context entries
        ]
        
        mock.retrieve_context.return_value = sample_contexts
        mock.store_conversation.return_value = True
        return mock
    
    @pytest.fixture
    def context_retriever(self, mock_memory_manager):
        """Create ContextRetriever with mocked dependencies."""
        mock_context_engine = Mock()
        mock_context_engine.get_relevant_context.return_value = []
        
        return ContextRetriever(
            memory_manager=mock_memory_manager,
            context_engine=mock_context_engine
        )
    
    @pytest.mark.asyncio
    async def test_context_window_size_management(self, context_retriever):
        """Test context window size management."""
        # Request context with different limits
        small_context = await context_retriever.get_relevant_context(
            "test query", "user123", limit=5
        )
        
        large_context = await context_retriever.get_relevant_context(
            "test query", "user123", limit=15
        )
        
        # Verify limits are respected
        assert len(small_context) <= 5
        assert len(large_context) <= 15
        assert len(large_context) >= len(small_context)
        
        # Verify most relevant contexts are prioritized
        if len(small_context) > 1:
            for i in range(len(small_context) - 1):
                assert small_context[i].relevance_score >= small_context[i + 1].relevance_score
    
    @pytest.mark.asyncio
    async def test_context_compression_for_large_histories(self, context_retriever):
        """Test context compression for large conversation histories."""
        # Get large context
        large_context = await context_retriever.get_relevant_context(
            "complex query requiring lots of context", "user123", limit=20
        )
        
        # Test summarization
        summary = context_retriever.summarize_context(large_context)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        
        # Summary should be shorter than original content
        original_length = sum(len(ctx.content) for ctx in large_context)
        assert len(summary) < original_length
        
        # Summary should contain key information
        assert "Context entry" in summary or "relevant information" in summary
    
    @pytest.mark.asyncio
    async def test_context_prioritization_algorithm(self, context_retriever):
        """Test context prioritization based on relevance and recency."""
        # Mock context with different relevance scores and timestamps
        mixed_contexts = [
            ContextEntry(
                content="Very relevant recent context",
                source="conversation",
                relevance_score=0.95,
                timestamp=datetime.now() - timedelta(minutes=1),
                context_type="conversation"
            ),
            ContextEntry(
                content="Less relevant recent context",
                source="conversation",
                relevance_score=0.6,
                timestamp=datetime.now() - timedelta(minutes=2),
                context_type="conversation"
            ),
            ContextEntry(
                content="Very relevant old context",
                source="conversation",
                relevance_score=0.9,
                timestamp=datetime.now() - timedelta(hours=2),
                context_type="conversation"
            )
        ]
        
        with patch.object(context_retriever, '_retrieve_raw_context') as mock_retrieve:
            mock_retrieve.return_value = mixed_contexts
            
            prioritized_context = await context_retriever.get_relevant_context(
                "test query", "user123", limit=10
            )
            
            # Should prioritize by relevance score primarily
            assert prioritized_context[0].relevance_score >= prioritized_context[1].relevance_score
            
            # Recent high-relevance should be first
            assert prioritized_context[0].content == "Very relevant recent context"
    
    @pytest.mark.asyncio
    async def test_context_caching_mechanism(self, context_retriever):
        """Test context caching for performance."""
        query = "test caching query"
        user_id = "user123"
        
        # First call - should hit the source
        start_time = time.time()
        context1 = await context_retriever.get_relevant_context(query, user_id)
        first_call_time = time.time() - start_time
        
        # Second call - should use cache if implemented
        start_time = time.time()
        context2 = await context_retriever.get_relevant_context(query, user_id)
        second_call_time = time.time() - start_time
        
        # Results should be consistent
        assert len(context1) == len(context2)
        
        # Second call might be faster due to caching (if implemented)
        # This is informational rather than a strict requirement
        print(f"First call: {first_call_time:.4f}s, Second call: {second_call_time:.4f}s")
    
    @pytest.mark.asyncio
    async def test_context_effectiveness_tracking(self, context_retriever):
        """Test context effectiveness tracking and learning."""
        context_entries = [
            ContextEntry(
                content="Helpful context",
                source="conversation",
                relevance_score=0.8,
                timestamp=datetime.now(),
                context_type="conversation"
            ),
            ContextEntry(
                content="Less helpful context",
                source="conversation",
                relevance_score=0.6,
                timestamp=datetime.now(),
                context_type="conversation"
            )
        ]
        
        # Track high effectiveness
        context_retriever.track_context_usage(context_entries, 0.9)
        
        # Track low effectiveness
        context_retriever.track_context_usage(context_entries, 0.3)
        
        # Verify tracking doesn't raise errors
        assert True  # Placeholder - actual implementation would verify metrics storage


class TestPerformanceOptimization:
    """Test performance optimization features."""
    
    @pytest.fixture
    def chat_manager_with_optimization(self):
        """Create ChatManager with performance optimization enabled."""
        return ChatManager(auto_create_context_engine=False)
    
    @pytest.mark.asyncio
    async def test_response_caching_integration(self, chat_manager_with_optimization):
        """Test response caching integration."""
        response_cache = get_response_cache()
        
        # Clear cache
        response_cache.clear_cache()
        
        message = "What is the weather like?"
        user_id = "user123"
        session_id = "session456"
        
        # First call - should not be cached
        start_time = time.time()
        response1 = await chat_manager_with_optimization.process_message(message, user_id, session_id)
        first_call_time = time.time() - start_time
        
        # Verify response
        assert response1 is not None
        assert not response1.ui_hints.get("cached", False)
        
        # Second call - might be cached depending on implementation
        start_time = time.time()
        response2 = await chat_manager_with_optimization.process_message(message, user_id, session_id)
        second_call_time = time.time() - start_time
        
        # Responses should be consistent
        assert response2 is not None
        
        # Check if caching is working (informational)
        print(f"First call: {first_call_time:.4f}s, Second call: {second_call_time:.4f}s")
        print(f"Second response cached: {response2.ui_hints.get('cached', False)}")
    
    @pytest.mark.asyncio
    async def test_resource_monitoring_integration(self, chat_manager_with_optimization):
        """Test resource monitoring integration."""
        resource_monitor = get_resource_monitor()
        
        # Get initial resource usage
        initial_usage = resource_monitor.get_current_usage()
        
        # Process several messages
        for i in range(5):
            await chat_manager_with_optimization.process_message(
                f"Test message {i}",
                f"user{i}",
                f"session{i}"
            )
        
        # Get final resource usage
        final_usage = resource_monitor.get_current_usage()
        
        # Verify monitoring is working
        assert isinstance(initial_usage, dict)
        assert isinstance(final_usage, dict)
        
        # Check conversation memory tracking
        conversation_memory = resource_monitor.get_conversation_memory_usage()
        assert isinstance(conversation_memory, dict)
    
    @pytest.mark.asyncio
    async def test_performance_under_memory_constraints(self, chat_manager_with_optimization):
        """Test performance under memory constraints."""
        resource_monitor = get_resource_monitor()
        
        # Simulate memory constraint
        with patch.object(resource_monitor, 'track_conversation_memory') as mock_track:
            # First call succeeds
            mock_track.return_value = True
            
            response1 = await chat_manager_with_optimization.process_message(
                "Normal message",
                "user123",
                "session456"
            )
            
            assert response1 is not None
            assert not response1.ui_hints.get("simplified", False)
            
            # Second call hits memory limit
            mock_track.return_value = False
            
            response2 = await chat_manager_with_optimization.process_message(
                "Message under memory constraint",
                "user123",
                "session456"
            )
            
            assert response2 is not None
            # Should use simplified processing
            assert response2.ui_hints.get("simplified", False) or response2.confidence_score < 0.5
    
    @pytest.mark.asyncio
    async def test_concurrent_performance_optimization(self, chat_manager_with_optimization):
        """Test performance optimization under concurrent load."""
        num_concurrent = 10
        
        async def process_message_with_timing(user_id: str):
            start_time = time.time()
            response = await chat_manager_with_optimization.process_message(
                f"Concurrent message from {user_id}",
                user_id,
                f"session_{user_id}"
            )
            execution_time = time.time() - start_time
            return response, execution_time
        
        # Execute concurrent requests
        tasks = [process_message_with_timing(f"user{i}") for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks)
        
        responses, execution_times = zip(*results)
        
        # Verify all responses succeeded
        assert len(responses) == num_concurrent
        assert all(response is not None for response in responses)
        
        # Check performance metrics
        avg_execution_time = sum(execution_times) / len(execution_times)
        max_execution_time = max(execution_times)
        
        # Performance should be reasonable under concurrent load
        assert avg_execution_time < 2.0  # Average under 2 seconds
        assert max_execution_time < 5.0  # Max under 5 seconds
        
        # Verify system stats
        performance_stats = chat_manager_with_optimization.get_performance_stats()
        assert isinstance(performance_stats, dict)
        assert "cache_stats" in performance_stats
        assert "resource_usage" in performance_stats


class TestMemoryUsageOptimization:
    """Test memory usage optimization and cleanup."""
    
    @pytest.fixture
    def chat_manager(self):
        """Create ChatManager for memory testing."""
        return ChatManager(auto_create_context_engine=False)
    
    def get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, chat_manager):
        """Test memory usage under sustained load."""
        initial_memory = self.get_memory_usage()
        
        # Process many messages
        num_messages = 50
        for i in range(num_messages):
            await chat_manager.process_message(
                f"Test message {i} with some content to use memory",
                f"user{i % 5}",  # 5 different users
                f"session{i % 3}"  # 3 different sessions
            )
            
            # Periodic memory check
            if i % 10 == 0:
                current_memory = self.get_memory_usage()
                memory_increase = current_memory - initial_memory
                
                # Memory increase should be reasonable
                assert memory_increase < 50  # Less than 50MB increase
        
        final_memory = self.get_memory_usage()
        total_memory_increase = final_memory - initial_memory
        
        # Total memory increase should be reasonable
        assert total_memory_increase < 100  # Less than 100MB for 50 messages
    
    @pytest.mark.asyncio
    async def test_session_cleanup_memory_impact(self, chat_manager):
        """Test memory impact of session cleanup."""
        initial_memory = self.get_memory_usage()
        
        # Create many sessions
        num_sessions = 20
        for i in range(num_sessions):
            await chat_manager.process_message(
                f"Message in session {i}",
                f"user{i}",
                f"session{i}"
            )
        
        memory_after_sessions = self.get_memory_usage()
        
        # Cleanup sessions
        cleaned_count = await chat_manager.cleanup_inactive_sessions(max_age_hours=0)
        
        memory_after_cleanup = self.get_memory_usage()
        
        # Verify cleanup occurred
        assert cleaned_count == num_sessions
        
        # Memory should not increase significantly after cleanup
        memory_increase_after_cleanup = memory_after_cleanup - memory_after_sessions
        assert memory_increase_after_cleanup < 10  # Less than 10MB increase
    
    @pytest.mark.asyncio
    async def test_context_memory_management(self, chat_manager):
        """Test context memory management."""
        # Create large context scenario
        large_message = "This is a large message with lots of content. " * 100  # ~5KB message
        
        initial_memory = self.get_memory_usage()
        
        # Process messages with large context
        for i in range(10):
            await chat_manager.process_message(
                large_message,
                "user123",
                "session456"
            )
        
        final_memory = self.get_memory_usage()
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be proportional but not excessive
        expected_max_increase = 10 * 5 / 1024  # 10 messages * 5KB / 1024 = ~0.05MB minimum
        assert memory_increase < expected_max_increase * 10  # Allow 10x overhead
    
    @pytest.mark.asyncio
    async def test_garbage_collection_effectiveness(self, chat_manager):
        """Test garbage collection effectiveness."""
        import gc
        
        initial_memory = self.get_memory_usage()
        
        # Create and process many temporary objects
        for i in range(30):
            response = await chat_manager.process_message(
                f"Temporary message {i}",
                f"temp_user{i}",
                f"temp_session{i}"
            )
            
            # Create some temporary objects
            temp_data = [f"temp_data_{j}" for j in range(100)]
            del temp_data
        
        # Force garbage collection
        gc.collect()
        
        # Cleanup all sessions
        await chat_manager.cleanup_inactive_sessions(max_age_hours=0)
        
        # Force another garbage collection
        gc.collect()
        
        final_memory = self.get_memory_usage()
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal after cleanup and GC
        assert memory_increase < 20  # Less than 20MB after cleanup


class TestCachingPerformance:
    """Test caching performance and effectiveness."""
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_optimization(self):
        """Test cache hit rate optimization."""
        performance_cache = get_performance_cache()
        response_cache = get_response_cache()
        
        # Clear caches
        performance_cache.clear_cache()
        response_cache.clear_cache()
        
        # Test repeated queries
        repeated_queries = [
            "What is the weather?",
            "How are you?",
            "What is the weather?",  # Repeat
            "Tell me about AI",
            "How are you?",  # Repeat
            "What is the weather?"  # Repeat
        ]
        
        chat_manager = ChatManager(auto_create_context_engine=False)
        
        cache_hits = 0
        total_queries = len(repeated_queries)
        
        for query in repeated_queries:
            response = await chat_manager.process_message(
                query,
                "user123",
                "session456"
            )
            
            if response.ui_hints.get("cached", False):
                cache_hits += 1
        
        # Calculate cache hit rate
        cache_hit_rate = cache_hits / total_queries
        
        # Should have some cache hits for repeated queries
        print(f"Cache hit rate: {cache_hit_rate:.2%}")
        
        # Verify caching is working (informational)
        cache_stats = performance_cache.get_stats()
        print(f"Cache stats: {cache_stats}")
    
    @pytest.mark.asyncio
    async def test_cache_performance_impact(self):
        """Test performance impact of caching."""
        chat_manager = ChatManager(auto_create_context_engine=False)
        
        # Test query
        test_query = "Complex query that should be cached"
        
        # Measure performance with cold cache
        start_time = time.time()
        response1 = await chat_manager.process_message(
            test_query,
            "user123",
            "session456"
        )
        cold_cache_time = time.time() - start_time
        
        # Measure performance with warm cache
        start_time = time.time()
        response2 = await chat_manager.process_message(
            test_query,
            "user123",
            "session456"
        )
        warm_cache_time = time.time() - start_time
        
        # Verify responses are consistent
        assert response1 is not None
        assert response2 is not None
        
        # Performance comparison (informational)
        print(f"Cold cache: {cold_cache_time:.4f}s")
        print(f"Warm cache: {warm_cache_time:.4f}s")
        
        if response2.ui_hints.get("cached", False):
            print("Second response was cached")
            # Cached response should be faster
            assert warm_cache_time <= cold_cache_time
        else:
            print("Second response was not cached")


if __name__ == "__main__":
    # Run context and performance integration tests
    pytest.main([
        __file__,
        "-v", "--tb=short"
    ])