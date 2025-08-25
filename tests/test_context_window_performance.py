#!/usr/bin/env python3
"""
Performance tests for ContextRetriever context window management.
"""

import sys
import os
import asyncio
import time
from datetime import datetime, timezone, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intelligent_chat.context_retriever import ContextRetriever
from intelligent_chat.models import ContextEntry


def create_test_contexts(count: int) -> list[ContextEntry]:
    """Create test context entries."""
    contexts = []
    for i in range(count):
        content_length = 100 + (i % 5) * 200  # Varying lengths
        content = f"Test context content {i}. " * (content_length // 20)
        
        contexts.append(ContextEntry(
            content=content,
            source=f"test_source_{i % 10}",  # 10 different sources
            relevance_score=0.9 - (i * 0.01),  # Decreasing relevance
            timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
            context_type=["conversation", "knowledge_base", "documentation"][i % 3],
            metadata={"test_id": i, "category": f"cat_{i % 5}"}
        ))
    
    return contexts


async def test_context_window_performance():
    """Test context window management performance."""
    print("Testing Context Window Management Performance...")
    
    retriever = ContextRetriever(
        max_context_length=2000,
        cache_ttl_seconds=300,
        compression_threshold=5000
    )
    
    # Test 1: Context Window Compression
    print("\nTest 1: Context Window Compression")
    large_contexts = create_test_contexts(50)
    
    start_time = time.time()
    compressed = retriever.compress_context_window(large_contexts, 10)
    compression_time = time.time() - start_time
    
    print(f"Compressed {len(large_contexts)} contexts to {len(compressed)} in {compression_time:.3f}s")
    assert len(compressed) == 10, "Should compress to target size"
    assert compressed[0].relevance_score >= compressed[-1].relevance_score, "Should maintain relevance order"
    print("✓ Test 1 passed")
    
    # Test 2: Performance Optimization
    print("\nTest 2: Performance Optimization")
    test_contexts = create_test_contexts(30)
    
    # Test speed optimization
    speed_optimized = retriever.optimize_context_for_performance(test_contexts, "speed")
    print(f"Speed optimized: {len(speed_optimized)} contexts")
    assert len(speed_optimized) <= 5, "Speed optimization should limit contexts"
    
    # Test accuracy optimization
    accuracy_optimized = retriever.optimize_context_for_performance(test_contexts, "accuracy")
    print(f"Accuracy optimized: {len(accuracy_optimized)} contexts")
    assert len(accuracy_optimized) <= 15, "Accuracy optimization should allow more contexts"
    
    # Test balanced optimization
    balanced_optimized = retriever.optimize_context_for_performance(test_contexts, "balanced")
    print(f"Balanced optimized: {len(balanced_optimized)} contexts")
    assert 5 <= len(balanced_optimized) <= 15, "Balanced should be between speed and accuracy"
    print("✓ Test 2 passed")
    
    # Test 3: Context Caching Performance
    print("\nTest 3: Context Caching Performance")
    test_contexts = create_test_contexts(20)
    
    # Create cache entry
    start_time = time.time()
    cache_key = retriever.create_context_cache_entry(test_contexts, "test query", "test_user", 24)
    cache_creation_time = time.time() - start_time
    
    # Retrieve from cache
    start_time = time.time()
    cached_contexts = retriever.get_cached_context_entry(cache_key)
    cache_retrieval_time = time.time() - start_time
    
    print(f"Cache creation: {cache_creation_time:.3f}s, retrieval: {cache_retrieval_time:.3f}s")
    assert cached_contexts is not None, "Should retrieve cached contexts"
    assert len(cached_contexts) == len(test_contexts), "Should retrieve all cached contexts"
    print("✓ Test 3 passed")
    
    # Test 4: Large Scale Context Processing
    print("\nTest 4: Large Scale Context Processing")
    large_contexts = create_test_contexts(200)
    
    start_time = time.time()
    # Simulate processing large context set
    for i in range(0, len(large_contexts), 20):
        batch = large_contexts[i:i+20]
        compressed_batch = retriever.compress_context_window(batch, 5)
        retriever.track_context_usage(compressed_batch, 0.8)
    
    processing_time = time.time() - start_time
    print(f"Processed {len(large_contexts)} contexts in {processing_time:.3f}s")
    print(f"Average time per context: {processing_time/len(large_contexts)*1000:.2f}ms")
    
    # Should process reasonably fast
    assert processing_time < 5.0, "Should process large context set in reasonable time"
    print("✓ Test 4 passed")
    
    # Test 5: Context Window Analytics
    print("\nTest 5: Context Window Analytics")
    analytics = retriever.get_context_window_analytics()
    print(f"Analytics: {analytics}")
    
    assert "total_contexts_processed" in analytics, "Should have total contexts processed"
    assert "cache_efficiency" in analytics, "Should have cache efficiency metrics"
    assert "performance_metrics" in analytics, "Should have performance metrics"
    print("✓ Test 5 passed")
    
    # Test 6: Cache Cleanup Performance
    print("\nTest 6: Cache Cleanup Performance")
    # Create many cache entries
    for i in range(50):
        contexts = create_test_contexts(5)
        retriever.create_context_cache_entry(contexts, f"query_{i}", "test_user", 1)  # 1 hour TTL
    
    # Wait a moment and cleanup
    start_time = time.time()
    cleaned_count = retriever.cleanup_expired_cache_entries()
    cleanup_time = time.time() - start_time
    
    print(f"Cleaned up {cleaned_count} entries in {cleanup_time:.3f}s")
    assert cleanup_time < 1.0, "Cleanup should be fast"
    print("✓ Test 6 passed")
    
    # Test 7: Context Compression Statistics
    print("\nTest 7: Context Compression Statistics")
    compression_stats = retriever.get_context_compression_stats()
    print(f"Compression stats: {compression_stats}")
    
    assert "compression_ratio" in compression_stats, "Should have compression ratio"
    assert "total_compressed_contexts" in compression_stats, "Should have total compressed contexts"
    print("✓ Test 7 passed")
    
    # Test 8: Memory Usage Optimization
    print("\nTest 8: Memory Usage Optimization")
    initial_cache_size = len(retriever._context_cache)
    
    # Fill cache with many entries
    for i in range(150):
        contexts = create_test_contexts(3)
        cache_key = f"test_key_{i}"
        retriever._cache_context(cache_key, contexts)
    
    final_cache_size = len(retriever._context_cache)
    print(f"Cache size: {initial_cache_size} -> {final_cache_size}")
    
    # Should trigger automatic cleanup
    assert final_cache_size <= 100, "Should limit cache size through cleanup"
    print("✓ Test 8 passed")
    
    # Performance Summary
    print("\n📊 Performance Summary:")
    final_analytics = retriever.get_context_window_analytics()
    print(f"Total contexts processed: {final_analytics['total_contexts_processed']}")
    print(f"Cache hit rate: {final_analytics['cache_efficiency']['hit_rate']:.2%}")
    print(f"Average retrieval time: {final_analytics['performance_metrics']['avg_retrieval_time']:.3f}s")
    print(f"Compressed cache entries: {final_analytics['compressed_cache_entries']}")
    
    print("\n🎉 All performance tests passed! Context window management is optimized.")


async def benchmark_context_operations():
    """Benchmark different context operations."""
    print("\n🔬 Benchmarking Context Operations...")
    
    retriever = ContextRetriever()
    contexts = create_test_contexts(100)
    
    # Benchmark compression
    start_time = time.time()
    for _ in range(10):
        retriever.compress_context_window(contexts, 10)
    compression_time = (time.time() - start_time) / 10
    print(f"Average compression time: {compression_time:.3f}s")
    
    # Benchmark optimization
    start_time = time.time()
    for _ in range(10):
        retriever.optimize_context_for_performance(contexts, "balanced")
    optimization_time = (time.time() - start_time) / 10
    print(f"Average optimization time: {optimization_time:.3f}s")
    
    # Benchmark caching
    start_time = time.time()
    for i in range(10):
        retriever.create_context_cache_entry(contexts[:10], f"query_{i}", "user", 1)
    caching_time = (time.time() - start_time) / 10
    print(f"Average caching time: {caching_time:.3f}s")
    
    print("📈 Benchmark complete!")


if __name__ == "__main__":
    asyncio.run(test_context_window_performance())
    asyncio.run(benchmark_context_operations())