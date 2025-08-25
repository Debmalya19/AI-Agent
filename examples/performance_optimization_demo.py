"""
Performance Optimization Demo

Demonstrates the performance optimization features of the intelligent chat UI system,
including caching, resource monitoring, and background metrics updates.
"""

import asyncio
import time
from datetime import datetime

from intelligent_chat.performance_cache import (
    get_performance_cache, get_response_cache, get_tool_performance_cache,
    start_background_updater, stop_background_updater
)
from intelligent_chat.resource_monitor import (
    get_resource_monitor, get_db_manager, start_resource_monitoring, stop_resource_monitoring
)
from intelligent_chat.models import ChatResponse, ContentType, ToolRecommendation


async def demo_performance_optimization():
    """Demonstrate performance optimization features."""
    print("🚀 Performance Optimization Demo")
    print("=" * 50)
    
    # Initialize components
    print("\n1. Initializing performance optimization components...")
    
    # Get cache instances
    perf_cache = get_performance_cache()
    response_cache = get_response_cache()
    tool_cache = get_tool_performance_cache()
    
    # Get monitoring instances
    resource_monitor = get_resource_monitor()
    db_manager = get_db_manager()
    
    print("✅ All components initialized")
    
    # Start monitoring services
    print("\n2. Starting monitoring services...")
    start_resource_monitoring()
    start_background_updater()
    print("✅ Monitoring services started")
    
    try:
        # Demo 1: Basic caching
        print("\n3. Demo: Basic Performance Caching")
        print("-" * 30)
        
        # Cache some data
        perf_cache.set("demo_key", "demo_value", "demo_category")
        cached_value = perf_cache.get("demo_key", "demo_category")
        print(f"Cached value: {cached_value}")
        
        # Show cache statistics
        cache_stats = perf_cache.get_stats()
        print(f"Cache hit rate: {cache_stats['hit_rate']:.2%}")
        print(f"Cache size: {cache_stats['cache_size']}")
        
        # Demo 2: Response caching
        print("\n4. Demo: Response Caching")
        print("-" * 25)
        
        # Create a sample response
        sample_response = ChatResponse(
            content="This is a sample response for caching demo",
            content_type=ContentType.PLAIN_TEXT,
            tools_used=["DemoTool"],
            execution_time=2.5,
            confidence_score=0.85
        )
        
        query = "What is the weather like?"
        context_hash = "demo_context_123"
        
        # Cache the response
        response_cache.cache_response(query, context_hash, sample_response)
        print("✅ Response cached")
        
        # Retrieve from cache
        start_time = time.time()
        cached_response = response_cache.get_response(query, context_hash)
        cache_retrieval_time = time.time() - start_time
        
        print(f"✅ Response retrieved from cache in {cache_retrieval_time*1000:.2f}ms")
        print(f"Cached response content: {cached_response.content[:50]}...")
        
        # Demo 3: Resource monitoring
        print("\n5. Demo: Resource Monitoring")
        print("-" * 25)
        
        # Get current resource usage
        resource_usage = resource_monitor.get_current_usage()
        for resource_type, usage in resource_usage.items():
            print(f"{resource_type.value}: {usage.current_value:.1f}% ({usage.limit.unit if usage.limit else 'N/A'})")
        
        # Demo tool execution monitoring
        print("\n6. Demo: Tool Execution Monitoring")
        print("-" * 30)
        
        with resource_monitor.monitor_tool_execution("DemoTool", timeout=5.0) as context:
            print(f"Monitoring tool: {context.tool_name}")
            
            # Simulate some work
            await asyncio.sleep(0.5)
            
            print(f"Execution time: {context.elapsed_time():.2f}s")
            print(f"Timeout check: {'❌ Timed out' if context.is_timeout() else '✅ Within limits'}")
        
        # Demo 4: Conversation memory tracking
        print("\n7. Demo: Conversation Memory Tracking")
        print("-" * 35)
        
        session_id = "demo_session_123"
        memory_usage = 25.5  # MB
        
        within_limits = resource_monitor.track_conversation_memory(session_id, memory_usage)
        print(f"Memory usage: {memory_usage}MB")
        print(f"Within limits: {'✅ Yes' if within_limits else '❌ No'}")
        
        # Get all conversation memory usage
        all_memory = resource_monitor.get_conversation_memory_usage()
        print(f"Total tracked conversations: {len(all_memory)}")
        
        # Demo 5: Database connection monitoring
        print("\n8. Demo: Database Connection Monitoring")
        print("-" * 35)
        
        db_stats = db_manager.get_connection_stats()
        print(f"Pool size: {db_stats['pool_size']}")
        print(f"Active connections: {db_stats['current_active']}")
        print(f"Peak connections: {db_stats['peak_active']}")
        print(f"Utilization: {db_stats['utilization_percent']:.1f}%")
        
        # Test database health
        health_ok = db_manager.health_check()
        print(f"Database health: {'✅ OK' if health_ok else '❌ Failed'}")
        
        # Demo 6: System statistics
        print("\n9. Demo: System Statistics")
        print("-" * 25)
        
        system_stats = resource_monitor.get_system_stats()
        print(f"Monitoring active: {system_stats['monitoring_active']}")
        print(f"Active executions: {system_stats['active_executions']}")
        print(f"Tracked conversations: {system_stats['tracked_conversations']}")
        print(f"Total conversation memory: {system_stats['total_conversation_memory']:.1f}MB")
        
        # Demo 7: Performance under load
        print("\n10. Demo: Performance Under Load")
        print("-" * 30)
        
        print("Generating cache load...")
        start_time = time.time()
        
        # Generate load
        for i in range(100):
            key = f"load_test_key_{i}"
            value = f"load_test_value_{i}" * 10  # Larger values
            perf_cache.set(key, value, "load_test")
            
            # Retrieve every other key
            if i % 2 == 0:
                perf_cache.get(key, "load_test")
        
        load_time = time.time() - start_time
        print(f"✅ Processed 100 cache operations in {load_time:.3f}s")
        
        # Show final cache statistics
        final_stats = perf_cache.get_stats()
        print(f"Final cache hit rate: {final_stats['hit_rate']:.2%}")
        print(f"Final cache size: {final_stats['cache_size']}")
        print(f"Average response time: {final_stats['average_response_time']*1000:.2f}ms")
        
        # Demo 8: Cache cleanup
        print("\n11. Demo: Cache Cleanup")
        print("-" * 20)
        
        # Clean up expired entries
        expired_count = perf_cache.cleanup_expired()
        print(f"Cleaned up {expired_count} expired entries")
        
        # Clear load test category
        cleared_count = perf_cache.clear_category("load_test")
        print(f"Cleared {cleared_count} load test entries")
        
        print("\n🎉 Performance optimization demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        print("\n12. Cleaning up...")
        stop_resource_monitoring()
        stop_background_updater()
        
        # Clean up conversation memory
        resource_monitor.cleanup_conversation_memory(session_id)
        
        print("✅ Cleanup completed")


def demo_tool_performance_caching():
    """Demonstrate tool performance caching."""
    print("\n🔧 Tool Performance Caching Demo")
    print("=" * 35)
    
    tool_cache = get_tool_performance_cache()
    
    # Simulate tool recommendations
    recommendations = [
        ToolRecommendation(
            tool_name="BTWebsiteSearch",
            relevance_score=0.9,
            expected_execution_time=2.5,
            confidence_level=0.85
        ),
        ToolRecommendation(
            tool_name="BTSupportHours",
            relevance_score=0.7,
            expected_execution_time=1.2,
            confidence_level=0.75
        )
    ]
    
    query_hash = "demo_query_hash_123"
    
    # Cache recommendations
    success = tool_cache.cache_tool_recommendations(query_hash, recommendations)
    print(f"Cached recommendations: {'✅ Success' if success else '❌ Failed'}")
    
    # Retrieve from cache
    cached_recs = tool_cache.get_tool_recommendations(query_hash)
    if cached_recs:
        print(f"Retrieved {len(cached_recs)} cached recommendations:")
        for rec in cached_recs:
            print(f"  - {rec.tool_name}: {rec.relevance_score:.2f} score")
    else:
        print("❌ No cached recommendations found")


if __name__ == "__main__":
    print("Starting Performance Optimization Demo...")
    
    # Run the main demo
    asyncio.run(demo_performance_optimization())
    
    # Run tool caching demo
    demo_tool_performance_caching()
    
    print("\n✨ All demos completed!")