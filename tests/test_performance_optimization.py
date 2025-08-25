"""
Performance Optimization Tests

Tests for caching system, resource monitoring, and performance optimization
components of the intelligent chat UI system.

Requirements covered:
- 6.1: Performance optimization through caching
- 6.2: Response time optimization
- 6.4: Resource usage optimization
- 6.5: Background performance metric updates
"""

import asyncio
import pytest
import time
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
import psutil

from intelligent_chat.performance_cache import (
    PerformanceCache, ResponseCache, ToolPerformanceCache,
    BackgroundMetricsUpdater, CacheEntry
)
from intelligent_chat.resource_monitor import (
    ResourceMonitor, DatabaseConnectionManager, ResourceType,
    AlertLevel, ResourceLimit, ExecutionContext
)
from intelligent_chat.models import ChatResponse, ToolRecommendation, ContentType


class TestPerformanceCache:
    """Test performance caching system."""
    
    def setup_method(self):
        """Setup test environment."""
        self.cache = PerformanceCache(max_size=100, default_ttl=300)
    
    def test_cache_basic_operations(self):
        """Test basic cache operations."""
        # Test set and get
        assert self.cache.set("test_key", "test_value")
        assert self.cache.get("test_key") == "test_value"
        
        # Test cache miss
        assert self.cache.get("nonexistent_key") is None
        
        # Test delete
        assert self.cache.delete("test_key")
        assert self.cache.get("test_key") is None
    
    def test_cache_ttl_expiration(self):
        """Test TTL-based cache expiration."""
        # Set with short TTL
        self.cache.set("expire_key", "expire_value", ttl=1)
        assert self.cache.get("expire_key") == "expire_value"
        
        # Wait for expiration
        time.sleep(1.1)
        assert self.cache.get("expire_key") is None
    
    def test_cache_categories(self):
        """Test cache categories with different TTLs."""
        # Test different categories
        self.cache.set("tool_key", "tool_value", category="tool_performance")
        self.cache.set("response_key", "response_value", category="response_cache")
        
        assert self.cache.get("tool_key", "tool_performance") == "tool_value"
        assert self.cache.get("response_key", "response_cache") == "response_value"
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        small_cache = PerformanceCache(max_size=3)
        
        # Fill cache
        small_cache.set("key1", "value1")
        small_cache.set("key2", "value2")
        small_cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        small_cache.get("key1")
        
        # Add new key, should evict key2 (least recently used)
        small_cache.set("key4", "value4")
        
        assert small_cache.get("key1") == "value1"  # Still there
        assert small_cache.get("key2") is None      # Evicted
        assert small_cache.get("key3") == "value3"  # Still there
        assert small_cache.get("key4") == "value4"  # New entry
    
    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        # Generate some cache activity
        self.cache.set("key1", "value1")
        self.cache.get("key1")  # Hit
        self.cache.get("key2")  # Miss
        
        stats = self.cache.get_stats()
        
        assert stats['cache_hits'] >= 1
        assert stats['cache_misses'] >= 1
        assert stats['total_requests'] >= 2
        assert 0 <= stats['hit_rate'] <= 1
        assert stats['cache_size'] >= 1
    
    def test_cache_cleanup_expired(self):
        """Test cleanup of expired entries."""
        # Add entries with different TTLs
        self.cache.set("short_key", "short_value", ttl=1)
        self.cache.set("long_key", "long_value", ttl=300)
        
        # Wait for short TTL to expire
        time.sleep(1.1)
        
        # Cleanup expired entries
        expired_count = self.cache.cleanup_expired()
        
        assert expired_count >= 1
        assert self.cache.get("short_key") is None
        assert self.cache.get("long_key") == "long_value"
    
    def test_cache_clear_category(self):
        """Test clearing cache by category."""
        # Add entries in different categories
        self.cache.set("tool:key1", "value1", "tool_performance")
        self.cache.set("tool:key2", "value2", "tool_performance")
        self.cache.set("response:key1", "value1", "response_cache")
        
        # Clear tool performance category
        cleared = self.cache.clear_category("tool_performance")
        
        assert cleared >= 2
        assert self.cache.get("tool:key1", "tool_performance") is None
        assert self.cache.get("response:key1", "response_cache") == "value1"


class TestResponseCache:
    """Test response caching system."""
    
    def setup_method(self):
        """Setup test environment."""
        self.perf_cache = PerformanceCache()
        self.response_cache = ResponseCache(self.perf_cache)
    
    def test_response_caching(self):
        """Test response caching and retrieval."""
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
        assert self.response_cache.cache_response(query, context_hash, response)
        
        # Retrieve cached response
        cached_response = self.response_cache.get_response(query, context_hash)
        
        assert cached_response is not None
        assert cached_response.content == response.content
        assert cached_response.content_type == response.content_type
        assert cached_response.tools_used == response.tools_used
    
    def test_response_cache_miss(self):
        """Test response cache miss."""
        cached_response = self.response_cache.get_response(
            "nonexistent query", "nonexistent_hash"
        )
        assert cached_response is None


class TestToolPerformanceCache:
    """Test tool performance caching system."""
    
    def setup_method(self):
        """Setup test environment."""
        self.perf_cache = PerformanceCache()
        self.mock_session = Mock()
        self.tool_cache = ToolPerformanceCache(self.perf_cache, self.mock_session)
    
    def test_tool_performance_caching(self):
        """Test tool performance metrics caching."""
        # Mock database response
        mock_metrics = [Mock()]
        mock_metrics[0].usage_count = 10
        mock_metrics[0].success_rate = 0.8
        mock_metrics[0].response_quality_score = 0.9
        mock_metrics[0].average_response_time = 2.5
        
        self.mock_session.query.return_value.filter.return_value.all.return_value = mock_metrics
        
        # Get performance (should fetch from DB and cache)
        performance = self.tool_cache.get_tool_performance("TestTool", "support")
        
        assert performance is not None
        assert performance['success_rate'] == 0.8
        assert performance['quality_score'] == 0.9
        assert performance['response_time'] == 2.5
        assert performance['usage_count'] == 10
        
        # Second call should use cache
        performance2 = self.tool_cache.get_tool_performance("TestTool", "support")
        assert performance2 == performance
    
    def test_tool_recommendations_caching(self):
        """Test tool recommendations caching."""
        recommendations = [
            ToolRecommendation(
                tool_name="Tool1",
                relevance_score=0.9,
                expected_execution_time=2.0,
                confidence_level=0.8
            ),
            ToolRecommendation(
                tool_name="Tool2",
                relevance_score=0.7,
                expected_execution_time=1.5,
                confidence_level=0.6
            )
        ]
        
        query_hash = "test_query_hash"
        
        # Cache recommendations
        assert self.tool_cache.cache_tool_recommendations(query_hash, recommendations)
        
        # Retrieve cached recommendations
        cached_recs = self.tool_cache.get_tool_recommendations(query_hash)
        
        assert cached_recs is not None
        assert len(cached_recs) == 2
        assert cached_recs[0].tool_name == "Tool1"
        assert cached_recs[1].tool_name == "Tool2"


class TestResourceMonitor:
    """Test resource monitoring system."""
    
    def setup_method(self):
        """Setup test environment."""
        self.monitor = ResourceMonitor()
    
    def test_resource_limits_configuration(self):
        """Test resource limits configuration."""
        # Check default limits
        assert ResourceType.MEMORY in self.monitor.limits
        assert ResourceType.CPU in self.monitor.limits
        
        memory_limit = self.monitor.limits[ResourceType.MEMORY]
        assert memory_limit.soft_limit == 80.0
        assert memory_limit.hard_limit == 90.0
        assert memory_limit.unit == "percentage"
    
    def test_current_usage_monitoring(self):
        """Test current resource usage monitoring."""
        usage = self.monitor.get_current_usage()
        
        # Should have memory and CPU usage
        assert ResourceType.MEMORY in usage
        assert ResourceType.CPU in usage
        
        memory_usage = usage[ResourceType.MEMORY]
        assert 0 <= memory_usage.current_value <= 100
        assert 0 <= memory_usage.percentage_used <= 100
    
    def test_tool_execution_monitoring(self):
        """Test tool execution monitoring context."""
        with self.monitor.monitor_tool_execution("TestTool", timeout=5.0) as context:
            assert context.tool_name == "TestTool"
            assert context.timeout == 5.0
            assert not context.is_timeout()
            
            # Simulate some work
            time.sleep(0.1)
            
            assert context.elapsed_time() > 0
    
    def test_conversation_memory_tracking(self):
        """Test conversation memory tracking."""
        session_id = "test_session_123"
        
        # Track memory usage within limits
        assert self.monitor.track_conversation_memory(session_id, 30.0)
        
        # Track memory usage exceeding limits
        assert not self.monitor.track_conversation_memory(session_id, 150.0)
        
        # Check memory usage retrieval
        memory_usage = self.monitor.get_conversation_memory_usage()
        assert session_id in memory_usage
        assert memory_usage[session_id] == 150.0
        
        # Cleanup
        self.monitor.cleanup_conversation_memory(session_id)
        memory_usage = self.monitor.get_conversation_memory_usage()
        assert session_id not in memory_usage
    
    def test_alert_system(self):
        """Test resource alert system."""
        alerts_received = []
        
        def alert_callback(alert):
            alerts_received.append(alert)
        
        self.monitor.add_alert_callback(alert_callback)
        
        # Force a high memory usage scenario (mock)
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 95.0  # Above hard limit
            
            alerts = self.monitor.check_resource_limits()
            
            assert len(alerts) > 0
            memory_alert = next((a for a in alerts if a.resource_type == ResourceType.MEMORY), None)
            assert memory_alert is not None
            assert memory_alert.level == AlertLevel.CRITICAL
    
    def test_system_stats(self):
        """Test system statistics collection."""
        stats = self.monitor.get_system_stats()
        
        assert 'timestamp' in stats
        assert 'resource_usage' in stats
        assert 'active_executions' in stats
        assert 'tracked_conversations' in stats
        assert 'monitoring_active' in stats
        
        # Check resource usage structure
        resource_usage = stats['resource_usage']
        assert 'memory' in resource_usage
        assert 'cpu' in resource_usage
    
    def test_monitoring_lifecycle(self):
        """Test monitoring start/stop lifecycle."""
        assert not self.monitor._monitoring
        
        # Start monitoring
        self.monitor.start_monitoring()
        assert self.monitor._monitoring
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        assert not self.monitor._monitoring


class TestDatabaseConnectionManager:
    """Test database connection manager."""
    
    def setup_method(self):
        """Setup test environment."""
        # Use in-memory SQLite for testing
        self.db_manager = DatabaseConnectionManager("sqlite:///:memory:")
    
    def test_connection_manager_initialization(self):
        """Test connection manager initialization."""
        assert self.db_manager.engine is not None
        assert self.db_manager.SessionLocal is not None
        assert self.db_manager.pool_size == 10
        assert self.db_manager.max_overflow == 20
    
    def test_session_context_manager(self):
        """Test database session context manager."""
        with self.db_manager.get_session() as session:
            # Test basic query
            result = session.execute("SELECT 1").fetchone()
            assert result[0] == 1
    
    def test_connection_statistics(self):
        """Test connection pool statistics."""
        stats = self.db_manager.get_connection_stats()
        
        assert 'pool_size' in stats
        assert 'checked_in' in stats
        assert 'checked_out' in stats
        assert 'total_created' in stats
        assert 'utilization_percent' in stats
    
    def test_health_check(self):
        """Test database health check."""
        assert self.db_manager.health_check()


class TestBackgroundMetricsUpdater:
    """Test background metrics updater."""
    
    def setup_method(self):
        """Setup test environment."""
        self.cache = PerformanceCache()
        self.tool_cache = ToolPerformanceCache(self.cache)
        self.updater = BackgroundMetricsUpdater(self.cache, self.tool_cache)
    
    def test_updater_lifecycle(self):
        """Test updater start/stop lifecycle."""
        assert not self.updater._running
        
        # Start updater
        self.updater.start()
        assert self.updater._running
        
        # Give it a moment to start
        time.sleep(0.1)
        
        # Stop updater
        self.updater.stop()
        assert not self.updater._running


class TestPerformanceIntegration:
    """Integration tests for performance optimization components."""
    
    def setup_method(self):
        """Setup test environment."""
        self.cache = PerformanceCache()
        self.response_cache = ResponseCache(self.cache)
        self.monitor = ResourceMonitor()
    
    def test_cache_performance_under_load(self):
        """Test cache performance under concurrent load."""
        def cache_worker(worker_id):
            for i in range(100):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                
                # Set and get
                self.cache.set(key, value)
                retrieved = self.cache.get(key)
                assert retrieved == value
        
        # Run multiple workers concurrently
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=cache_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all workers to complete
        for thread in threads:
            thread.join()
        
        # Check cache statistics
        stats = self.cache.get_stats()
        assert stats['total_requests'] >= 500  # 5 workers * 100 operations
        assert stats['cache_hits'] >= 500
    
    def test_resource_monitoring_during_cache_operations(self):
        """Test resource monitoring during intensive cache operations."""
        self.monitor.start_monitoring()
        
        try:
            # Perform intensive cache operations
            for i in range(1000):
                key = f"intensive_key_{i}"
                value = f"intensive_value_{i}" * 100  # Larger values
                self.cache.set(key, value)
                self.cache.get(key)
            
            # Check that monitoring captured the activity
            stats = self.monitor.get_system_stats()
            assert stats['monitoring_active']
            
            # Memory usage should be tracked
            usage = self.monitor.get_current_usage()
            assert ResourceType.MEMORY in usage
            
        finally:
            self.monitor.stop_monitoring()
    
    def test_end_to_end_performance_optimization(self):
        """Test end-to-end performance optimization scenario."""
        # Simulate a complete chat interaction with caching and monitoring
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        try:
            # Simulate tool execution with monitoring
            with self.monitor.monitor_tool_execution("TestTool", timeout=10.0) as context:
                # Simulate response generation and caching
                response = ChatResponse(
                    content="This is a test response with performance optimization",
                    content_type=ContentType.PLAIN_TEXT,
                    tools_used=["TestTool"],
                    execution_time=context.elapsed_time()
                )
                
                # Cache the response
                query = "test performance query"
                context_hash = "performance_context_hash"
                assert self.response_cache.cache_response(query, context_hash, response)
                
                # Retrieve from cache (should be faster)
                start_time = time.time()
                cached_response = self.response_cache.get_response(query, context_hash)
                cache_time = time.time() - start_time
                
                assert cached_response is not None
                assert cache_time < 0.01  # Should be very fast from cache
            
            # Check final statistics
            cache_stats = self.cache.get_stats()
            monitor_stats = self.monitor.get_system_stats()
            
            assert cache_stats['hit_rate'] > 0
            assert monitor_stats['monitoring_active']
            
        finally:
            self.monitor.stop_monitoring()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])