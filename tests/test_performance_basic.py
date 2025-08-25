"""
Basic Performance Optimization Tests

Simple tests to verify the performance optimization components work correctly.
"""

import pytest
import time
from datetime import datetime, timezone

from intelligent_chat.performance_cache import PerformanceCache, CacheEntry
from intelligent_chat.models import ChatResponse, ContentType


def test_performance_cache_basic():
    """Test basic performance cache operations."""
    cache = PerformanceCache(max_size=10, default_ttl=300)
    
    # Test set and get
    assert cache.set("test_key", "test_value")
    assert cache.get("test_key") == "test_value"
    
    # Test cache miss
    assert cache.get("nonexistent_key") is None
    
    # Test delete
    assert cache.delete("test_key")
    assert cache.get("test_key") is None


def test_cache_entry_expiration():
    """Test cache entry expiration logic."""
    entry = CacheEntry(
        data="test_data",
        timestamp=datetime.now(timezone.utc),
        ttl=1  # 1 second TTL
    )
    
    # Should not be expired initially
    assert not entry.is_expired()
    
    # Wait for expiration
    time.sleep(1.1)
    assert entry.is_expired()


def test_cache_statistics():
    """Test cache statistics tracking."""
    cache = PerformanceCache(max_size=10)
    
    # Generate some activity
    cache.set("key1", "value1")
    cache.get("key1")  # Hit
    cache.get("key2")  # Miss
    
    stats = cache.get_stats()
    
    assert stats['cache_hits'] >= 1
    assert stats['cache_misses'] >= 1
    assert stats['total_requests'] >= 2
    assert 0 <= stats['hit_rate'] <= 1


def test_response_caching():
    """Test response caching functionality."""
    from intelligent_chat.performance_cache import ResponseCache
    
    perf_cache = PerformanceCache()
    response_cache = ResponseCache(perf_cache)
    
    # Create test response
    response = ChatResponse(
        content="Test response",
        content_type=ContentType.PLAIN_TEXT,
        tools_used=["TestTool"],
        execution_time=1.5
    )
    
    query = "test query"
    context_hash = "test_context_hash"
    
    # Cache response
    assert response_cache.cache_response(query, context_hash, response)
    
    # Retrieve cached response
    cached_response = response_cache.get_response(query, context_hash)
    
    assert cached_response is not None
    assert cached_response.content == response.content
    assert cached_response.content_type == response.content_type


if __name__ == "__main__":
    pytest.main([__file__, "-v"])