"""
Integration tests for ContextRetriever with existing memory components.
Tests the integration with ContextRetrievalEngine and MemoryLayerManager.
"""

import pytest
import asyncio
import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from intelligent_chat.context_retriever import ContextRetriever
from intelligent_chat.models import ContextEntry
from intelligent_chat.exceptions import ContextRetrievalError
from memory_models import ContextEntryDTO
from context_retrieval_engine import ContextRetrievalEngine
from memory_layer_manager import MemoryLayerManager


class TestContextRetrieverIntegration(unittest.TestCase):
    """Test ContextRetriever integration with existing components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_context_engine = Mock(spec=ContextRetrievalEngine)
        self.mock_memory_manager = Mock(spec=MemoryLayerManager)
        
        self.context_retriever = ContextRetriever(
            context_engine=self.mock_context_engine,
            memory_manager=self.mock_memory_manager,
            max_context_length=1000,
            cache_ttl_seconds=300
        )
        
        # Sample context data
        self.sample_context_dto = ContextEntryDTO(
            content="Sample context content",
            source="test_source",
            relevance_score=0.8,
            context_type="conversation",
            timestamp=datetime.now(timezone.utc),
            metadata={"test": "data"}
        )
        
        self.sample_context_entry = ContextEntry(
            content="Sample context content",
            source="test_source",
            relevance_score=0.8,
            timestamp=datetime.now(timezone.utc),
            context_type="conversation",
            metadata={"test": "data"}
        )
    
    @pytest.mark.asyncio
    async def test_get_relevant_context_with_engine_integration(self):
        """Test context retrieval with context engine integration."""
        # Setup mock
        self.mock_context_engine.get_relevant_context.return_value = [self.sample_context_dto]
        self.mock_memory_manager.retrieve_context.return_value = []
        
        # Test
        result = await self.context_retriever.get_relevant_context(
            query="test query",
            user_id="test_user",
            limit=10
        )
        
        # Verify
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].content, "Sample context content")
        self.assertEqual(result[0].source, "test_source")
        self.mock_context_engine.get_relevant_context.assert_called_once_with(
            query="test query",
            user_id="test_user",
            limit=20  # Should request more for deduplication
        )
    
    @pytest.mark.asyncio
    async def test_get_relevant_context_with_memory_integration(self):
        """Test context retrieval with memory manager integration."""
        # Setup mock
        self.mock_memory_manager.retrieve_context.return_value = [self.sample_context_dto]
        self.mock_context_engine.get_relevant_context.return_value = []
        
        # Test
        result = await self.context_retriever.get_relevant_context(
            query="test query",
            user_id="test_user",
            limit=10
        )
        
        # Verify
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].content, "Sample context content")
        self.mock_memory_manager.retrieve_context.assert_called_once_with(
            "test query", "test_user", 10
        )
    
    @pytest.mark.asyncio
    async def test_get_relevant_context_with_both_sources(self):
        """Test context retrieval with both engine and memory sources."""
        # Setup mocks with different content
        engine_dto = ContextEntryDTO(
            content="Engine context",
            source="context_engine",
            relevance_score=0.9,
            context_type="knowledge_base",
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )
        
        memory_dto = ContextEntryDTO(
            content="Memory context",
            source="memory_layer",
            relevance_score=0.7,
            context_type="conversation",
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )
        
        self.mock_context_engine.get_relevant_context.return_value = [engine_dto]
        self.mock_memory_manager.retrieve_context.return_value = [memory_dto]
        
        # Test
        result = await self.context_retriever.get_relevant_context(
            query="test query",
            user_id="test_user",
            limit=10
        )
        
        # Verify
        self.assertEqual(len(result), 2)
        # Should be sorted by relevance score (engine first with 0.9)
        self.assertEqual(result[0].content, "Engine context")
        self.assertEqual(result[1].content, "Memory context")
    
    @pytest.mark.asyncio
    async def test_context_caching(self):
        """Test context caching functionality."""
        # Setup mock
        self.mock_context_engine.get_relevant_context.return_value = [self.sample_context_dto]
        self.mock_memory_manager.retrieve_context.return_value = []
        
        # First call
        result1 = await self.context_retriever.get_relevant_context(
            query="test query",
            user_id="test_user",
            limit=10
        )
        
        # Second call (should use cache)
        result2 = await self.context_retriever.get_relevant_context(
            query="test query",
            user_id="test_user",
            limit=10
        )
        
        # Verify
        self.assertEqual(len(result1), 1)
        self.assertEqual(len(result2), 1)
        self.assertEqual(result1[0].content, result2[0].content)
        
        # Engine should only be called once due to caching
        self.mock_context_engine.get_relevant_context.assert_called_once()
        
        # Check cache hit rate
        metrics = self.context_retriever.get_performance_metrics()
        self.assertEqual(metrics["cache_hits"], 1)
        self.assertEqual(metrics["cache_misses"], 1)
    
    @pytest.mark.asyncio
    async def test_context_deduplication(self):
        """Test context deduplication functionality."""
        # Setup mocks with duplicate content
        duplicate_dto1 = ContextEntryDTO(
            content="Duplicate content",
            source="source1",
            relevance_score=0.8,
            context_type="conversation",
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )
        
        duplicate_dto2 = ContextEntryDTO(
            content="Duplicate content",
            source="source2",
            relevance_score=0.7,
            context_type="conversation",
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )
        
        self.mock_context_engine.get_relevant_context.return_value = [duplicate_dto1]
        self.mock_memory_manager.retrieve_context.return_value = [duplicate_dto2]
        
        # Test
        result = await self.context_retriever.get_relevant_context(
            query="test query",
            user_id="test_user",
            limit=10
        )
        
        # Verify deduplication (should only have one entry)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].content, "Duplicate content")
        # Should keep the higher scoring one
        self.assertEqual(result[0].source, "source1")
    
    def test_summarize_context_full(self):
        """Test context summarization when within length limits."""
        contexts = [
            ContextEntry(
                content="Short context 1",
                source="source1",
                relevance_score=0.8,
                timestamp=datetime.now(),
                context_type="conversation",
                metadata={}
            ),
            ContextEntry(
                content="Short context 2",
                source="source2",
                relevance_score=0.7,
                timestamp=datetime.now(),
                context_type="knowledge_base",
                metadata={}
            )
        ]
        
        result = self.context_retriever.summarize_context(contexts)
        
        # Should contain full context since it's short
        self.assertIn("Short context 1", result)
        self.assertIn("Short context 2", result)
        self.assertIn("source1", result)
        self.assertIn("source2", result)
    
    def test_summarize_context_compressed(self):
        """Test context summarization with compression."""
        # Create long context that exceeds max_context_length
        long_content = "This is a very long context entry that should be compressed. " * 50
        
        contexts = [
            ContextEntry(
                content=long_content,
                source="source1",
                relevance_score=0.8,
                timestamp=datetime.now(),
                context_type="conversation",
                metadata={}
            )
        ]
        
        result = self.context_retriever.summarize_context(contexts)
        
        # Should be compressed
        self.assertLess(len(result), len(long_content))
        self.assertIn("source1", result)
    
    def test_track_context_usage(self):
        """Test context usage tracking."""
        contexts = [self.sample_context_entry]
        
        # Track usage
        self.context_retriever.track_context_usage(contexts, 0.9)
        
        # Verify tracking
        stats = self.context_retriever.get_context_effectiveness_stats()
        self.assertIn("test_source", stats)
        self.assertEqual(stats["test_source"]["total_uses"], 1)
        self.assertEqual(stats["test_source"]["average_effectiveness"], 0.9)
    
    def test_effectiveness_boosting(self):
        """Test effectiveness-based score boosting."""
        # Track some usage first
        self.context_retriever.track_context_usage([self.sample_context_entry], 0.9)
        
        # Create context with same source
        contexts = [
            ContextEntry(
                content="New content",
                source="test_source",  # Same source as tracked
                relevance_score=0.5,
                timestamp=datetime.now(),
                context_type="conversation",
                metadata={}
            ),
            ContextEntry(
                content="Other content",
                source="other_source",  # Different source
                relevance_score=0.5,
                timestamp=datetime.now(),
                context_type="conversation",
                metadata={}
            )
        ]
        
        # Apply intelligent ranking
        ranked = self.context_retriever._apply_intelligent_ranking(
            contexts, "test query", "test_user"
        )
        
        # The context from tracked source should have higher score due to effectiveness boost
        self.assertGreater(ranked[0].relevance_score, 0.5)
        self.assertEqual(ranked[0].source, "test_source")
    
    def test_recency_boosting(self):
        """Test recency-based score boosting."""
        recent_time = datetime.now(timezone.utc)
        old_time = datetime.now(timezone.utc) - timedelta(days=7)
        
        contexts = [
            ContextEntry(
                content="Old content",
                source="source1",
                relevance_score=0.5,
                timestamp=old_time,
                context_type="conversation",
                metadata={}
            ),
            ContextEntry(
                content="Recent content",
                source="source2",
                relevance_score=0.5,
                timestamp=recent_time,
                context_type="conversation",
                metadata={}
            )
        ]
        
        # Apply intelligent ranking
        ranked = self.context_retriever._apply_intelligent_ranking(
            contexts, "test query", "test_user"
        )
        
        # Recent context should have higher score
        self.assertEqual(ranked[0].content, "Recent content")
        self.assertGreater(ranked[0].relevance_score, ranked[1].relevance_score)
    
    def test_context_window_optimization(self):
        """Test context window optimization for performance."""
        # Create many contexts from same source
        contexts = []
        for i in range(20):
            contexts.append(ContextEntry(
                content=f"Content {i}",
                source="same_source",
                relevance_score=0.8 - (i * 0.01),  # Decreasing scores
                timestamp=datetime.now(),
                context_type="conversation",
                metadata={}
            ))
        
        # Optimize for limit of 5
        optimized = self.context_retriever._optimize_context_window(contexts, 5)
        
        # Should return exactly 5 contexts
        self.assertEqual(len(optimized), 5)
        
        # Should prefer higher scoring contexts
        self.assertEqual(optimized[0].content, "Content 0")
    
    @pytest.mark.asyncio
    async def test_error_handling_engine_failure(self):
        """Test error handling when context engine fails."""
        # Setup mock to raise exception
        self.mock_context_engine.get_relevant_context.side_effect = Exception("Engine error")
        self.mock_memory_manager.retrieve_context.return_value = [self.sample_context_dto]
        
        # Should not raise exception, should continue with memory results
        result = await self.context_retriever.get_relevant_context(
            query="test query",
            user_id="test_user",
            limit=10
        )
        
        # Should still get memory results
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].content, "Sample context content")
    
    @pytest.mark.asyncio
    async def test_error_handling_memory_failure(self):
        """Test error handling when memory manager fails."""
        # Setup mock to raise exception
        self.mock_memory_manager.retrieve_context.side_effect = Exception("Memory error")
        self.mock_context_engine.get_relevant_context.return_value = [self.sample_context_dto]
        
        # Should not raise exception, should continue with engine results
        result = await self.context_retriever.get_relevant_context(
            query="test query",
            user_id="test_user",
            limit=10
        )
        
        # Should still get engine results
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].content, "Sample context content")
    
    @pytest.mark.asyncio
    async def test_error_handling_both_fail(self):
        """Test error handling when both sources fail."""
        # Setup mocks to raise exceptions
        self.mock_context_engine.get_relevant_context.side_effect = Exception("Engine error")
        self.mock_memory_manager.retrieve_context.side_effect = Exception("Memory error")
        
        # Should raise ContextRetrievalError
        with self.assertRaises(ContextRetrievalError):
            await self.context_retriever.get_relevant_context(
                query="test query",
                user_id="test_user",
                limit=10
            )
    
    def test_performance_metrics(self):
        """Test performance metrics collection."""
        # Perform some operations to generate metrics
        self.context_retriever._cache_hits = 5
        self.context_retriever._cache_misses = 3
        self.context_retriever._retrieval_times = [0.1, 0.2, 0.15]
        
        metrics = self.context_retriever.get_performance_metrics()
        
        self.assertEqual(metrics["cache_hits"], 5)
        self.assertEqual(metrics["cache_misses"], 3)
        self.assertEqual(metrics["cache_hit_rate"], 5/8)
        self.assertEqual(metrics["average_retrieval_time"], 0.15)
    
    def test_cache_cleanup(self):
        """Test cache cleanup functionality."""
        # Fill cache beyond limit
        for i in range(150):
            cache_key = f"key_{i}"
            context = [self.sample_context_entry]
            self.context_retriever._cache_context(cache_key, context)
        
        # Should trigger cleanup
        self.assertLessEqual(len(self.context_retriever._context_cache), 100)
    
    def test_context_type_boosting(self):
        """Test context type boosting based on query characteristics."""
        contexts = [
            ContextEntry(
                content="Error troubleshooting guide",
                source="source1",
                relevance_score=0.5,
                timestamp=datetime.now(),
                context_type="troubleshooting",
                metadata={}
            ),
            ContextEntry(
                content="General information",
                source="source2",
                relevance_score=0.5,
                timestamp=datetime.now(),
                context_type="general",
                metadata={}
            )
        ]
        
        # Query with error-related content
        ranked = self.context_retriever._apply_intelligent_ranking(
            contexts, "I have an error with my connection", "test_user"
        )
        
        # Troubleshooting context should get boost
        self.assertEqual(ranked[0].context_type, "troubleshooting")
        self.assertGreater(ranked[0].relevance_score, ranked[1].relevance_score)


class TestContextRetrieverWithoutDependencies(unittest.TestCase):
    """Test ContextRetriever functionality without external dependencies."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.context_retriever = ContextRetriever(
            context_engine=None,
            memory_manager=None,
            max_context_length=1000
        )
    
    @pytest.mark.asyncio
    async def test_get_relevant_context_no_dependencies(self):
        """Test context retrieval without any dependencies."""
        result = await self.context_retriever.get_relevant_context(
            query="test query",
            user_id="test_user",
            limit=10
        )
        
        # Should return empty list when no dependencies available
        self.assertEqual(len(result), 0)
    
    def test_summarize_empty_context(self):
        """Test summarization with empty context."""
        result = self.context_retriever.summarize_context([])
        self.assertEqual(result, "No relevant context found.")
    
    def test_intelligent_content_truncation(self):
        """Test intelligent content truncation."""
        content = "This is the first sentence. This is the second sentence. This is the third sentence."
        
        truncated = self.context_retriever._truncate_content_intelligently(content, 50)
        
        # Should break at sentence boundary
        self.assertTrue(truncated.endswith("..."))
        self.assertIn("first sentence", truncated)
    
    def test_content_compression(self):
        """Test content compression functionality."""
        content = "This is very really quite a rather long sentence with basically many filler words actually."
        
        compressed = self.context_retriever._compress_content(content, 50)
        
        # Should remove filler words
        self.assertNotIn("very", compressed)
        self.assertNotIn("really", compressed)
        self.assertNotIn("basically", compressed)
        self.assertLess(len(compressed), len(content))


if __name__ == '__main__':
    unittest.main()