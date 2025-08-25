#!/usr/bin/env python3
"""
Simple test for ContextRetriever functionality.
"""

import sys
import os
import asyncio
from datetime import datetime, timezone

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intelligent_chat.context_retriever import ContextRetriever
from intelligent_chat.models import ContextEntry


async def test_context_retriever():
    """Test basic ContextRetriever functionality."""
    print("Testing ContextRetriever...")
    
    # Create ContextRetriever without dependencies
    retriever = ContextRetriever()
    
    # Test 1: Empty context retrieval
    print("Test 1: Empty context retrieval")
    result = await retriever.get_relevant_context("test query", "test_user", 10)
    print(f"Result: {len(result)} contexts retrieved")
    assert len(result) == 0, "Should return empty list without dependencies"
    print("✓ Test 1 passed")
    
    # Test 2: Context summarization
    print("\nTest 2: Context summarization")
    contexts = [
        ContextEntry(
            content="This is test content 1",
            source="test_source_1",
            relevance_score=0.8,
            timestamp=datetime.now(timezone.utc),
            context_type="conversation",
            metadata={}
        ),
        ContextEntry(
            content="This is test content 2",
            source="test_source_2",
            relevance_score=0.7,
            timestamp=datetime.now(timezone.utc),
            context_type="knowledge_base",
            metadata={}
        )
    ]
    
    summary = retriever.summarize_context(contexts)
    print(f"Summary: {summary}")
    assert "test content 1" in summary, "Should contain first context"
    assert "test content 2" in summary, "Should contain second context"
    print("✓ Test 2 passed")
    
    # Test 3: Context usage tracking
    print("\nTest 3: Context usage tracking")
    retriever.track_context_usage(contexts, 0.9)
    stats = retriever.get_context_effectiveness_stats()
    print(f"Stats: {stats}")
    assert "test_source_1" in stats, "Should track first source"
    assert "test_source_2" in stats, "Should track second source"
    assert stats["test_source_1"]["average_effectiveness"] == 0.9, "Should track effectiveness"
    print("✓ Test 3 passed")
    
    # Test 4: Performance metrics
    print("\nTest 4: Performance metrics")
    metrics = retriever.get_performance_metrics()
    print(f"Metrics: {metrics}")
    assert "cache_hit_rate" in metrics, "Should have cache hit rate"
    assert "average_retrieval_time" in metrics, "Should have average retrieval time"
    print("✓ Test 4 passed")
    
    # Test 5: Cache functionality
    print("\nTest 5: Cache functionality")
    cache_key = retriever._generate_cache_key("test query", "test_user", 10)
    retriever._cache_context(cache_key, contexts)
    cached = retriever._get_cached_context(cache_key)
    print(f"Cached contexts: {len(cached) if cached else 0}")
    assert cached is not None, "Should retrieve cached contexts"
    assert len(cached) == 2, "Should have cached both contexts"
    print("✓ Test 5 passed")
    
    # Test 6: Intelligent ranking
    print("\nTest 6: Intelligent ranking")
    ranked = retriever._apply_intelligent_ranking(contexts, "test query", "test_user")
    print(f"Ranked contexts: {[c.relevance_score for c in ranked]}")
    assert len(ranked) == 2, "Should rank all contexts"
    assert ranked[0].relevance_score >= ranked[1].relevance_score, "Should be sorted by score"
    print("✓ Test 6 passed")
    
    # Test 7: Context window optimization
    print("\nTest 7: Context window optimization")
    optimized = retriever._optimize_context_window(contexts, 1)
    print(f"Optimized contexts: {len(optimized)}")
    assert len(optimized) == 1, "Should limit to requested size"
    print("✓ Test 7 passed")
    
    print("\n🎉 All tests passed! ContextRetriever is working correctly.")


if __name__ == "__main__":
    asyncio.run(test_context_retriever())