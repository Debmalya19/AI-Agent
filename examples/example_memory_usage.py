"""
Example usage of the Memory Layer Manager.
Demonstrates how to store conversations, retrieve context, and manage memory.
"""

import asyncio
from datetime import datetime, timezone
from memory_layer_manager import MemoryLayerManager
from memory_config import MemoryConfig
from memory_models import ConversationEntryDTO
from database import SessionLocal


async def main():
    """Demonstrate Memory Layer Manager usage"""
    
    # Create configuration
    config = MemoryConfig()
    config.log_level = "INFO"
    config.performance.max_context_entries = 5
    
    print("=== Memory Layer Manager Example ===\n")
    
    # Create memory manager
    print("1. Initializing Memory Layer Manager...")
    memory_manager = MemoryLayerManager(config=config)
    
    # Store some example conversations
    print("\n2. Storing example conversations...")
    
    conversations = [
        ConversationEntryDTO(
            session_id="demo_session_1",
            user_id="demo_user",
            user_message="What is Python?",
            bot_response="Python is a high-level programming language known for its simplicity and readability.",
            tools_used=["knowledge_search"],
            tool_performance={"knowledge_search": 0.9},
            response_quality_score=0.85
        ),
        ConversationEntryDTO(
            session_id="demo_session_1",
            user_id="demo_user",
            user_message="How do I create a list in Python?",
            bot_response="You can create a list in Python using square brackets: my_list = [1, 2, 3, 'hello']",
            tools_used=["code_examples"],
            tool_performance={"code_examples": 0.95},
            response_quality_score=0.92
        ),
        ConversationEntryDTO(
            session_id="demo_session_2",
            user_id="demo_user",
            user_message="What is machine learning?",
            bot_response="Machine learning is a subset of AI that enables computers to learn from data without explicit programming.",
            tools_used=["knowledge_search", "definition_lookup"],
            tool_performance={"knowledge_search": 0.8, "definition_lookup": 0.9},
            response_quality_score=0.88
        )
    ]
    
    for i, conv in enumerate(conversations, 1):
        success = memory_manager.store_conversation(conv)
        print(f"   Stored conversation {i}: {'✓' if success else '✗'}")
    
    # Retrieve context for a new query
    print("\n3. Retrieving context for new query...")
    query = "How to use Python for data science?"
    context_entries = memory_manager.retrieve_context(query, "demo_user", limit=3)
    
    print(f"   Found {len(context_entries)} relevant context entries:")
    for i, entry in enumerate(context_entries, 1):
        print(f"   {i}. [{entry.context_type}] (score: {entry.relevance_score:.2f})")
        print(f"      Content: {entry.content[:80]}...")
        print(f"      Source: {entry.source}")
        print()
    
    # Analyze tool usage
    print("4. Analyzing tool usage patterns...")
    tool_recommendation = memory_manager.analyze_tool_usage(
        "What is artificial intelligence?", 
        ["knowledge_search"]
    )
    
    if tool_recommendation:
        print(f"   Recommended tool: {tool_recommendation.tool_name}")
        print(f"   Confidence: {tool_recommendation.confidence_score:.1%}")
        print(f"   Reason: {tool_recommendation.reason}")
    else:
        print("   No tool recommendations available (insufficient historical data)")
    
    # Get conversation history
    print("\n5. Getting user conversation history...")
    history = memory_manager.get_user_conversation_history("demo_user", limit=5)
    
    print(f"   Found {len(history)} conversations in history:")
    for i, conv in enumerate(history, 1):
        print(f"   {i}. [{conv.session_id}] User: {conv.user_message[:50]}...")
        print(f"      Bot: {conv.bot_response[:50]}...")
        print(f"      Tools: {conv.tools_used}")
        print(f"      Quality: {conv.response_quality_score}")
        print()
    
    # Get memory statistics
    print("6. Getting memory statistics...")
    stats = memory_manager.get_memory_stats()
    
    print(f"   Total conversations: {stats.total_conversations}")
    print(f"   Total context entries: {stats.total_context_entries}")
    print(f"   Total tool usages: {stats.total_tool_usages}")
    print(f"   Average response time: {stats.average_response_time:.3f}s")
    print(f"   Health score: {stats.health_score:.2f}")
    print(f"   Error count: {stats.error_count}")
    
    # Record a health metric
    print("\n7. Recording health metrics...")
    success = memory_manager.record_health_metric(
        "demo_response_time", 0.125, "seconds", "performance"
    )
    print(f"   Health metric recorded: {'✓' if success else '✗'}")
    
    # Demonstrate cleanup (won't clean recent data)
    print("\n8. Running data cleanup...")
    cleanup_result = memory_manager.cleanup_expired_data()
    
    print(f"   Conversations cleaned: {cleanup_result.conversations_cleaned}")
    print(f"   Context entries cleaned: {cleanup_result.context_entries_cleaned}")
    print(f"   Tool metrics cleaned: {cleanup_result.tool_metrics_cleaned}")
    print(f"   Cleanup duration: {cleanup_result.cleanup_duration:.3f}s")
    if cleanup_result.errors:
        print(f"   Errors: {cleanup_result.errors}")
    
    print("\n=== Memory Layer Manager Demo Complete ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error running demo: {e}")
        print("Make sure the database is properly configured and accessible.")