#!/usr/bin/env python3
"""
Demo script showing enhanced session memory and learning functionality.

This script demonstrates how the AI agent learns from previous conversations
and uses that knowledge to provide better responses over time.
"""

import sys
import os
import asyncio
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.memory_layer_manager import MemoryLayerManager
from backend.memory_models import ConversationEntryDTO
from backend.intelligent_chat.chat_manager import ChatManager
from backend.memory_config import load_config

async def demo_session_memory_learning():
    """Demonstrate session memory and learning functionality."""
    
    print("🧠 AI Agent Session Memory & Learning Demo")
    print("=" * 50)
    
    # Initialize components
    print("\n1. Initializing memory layer and chat manager...")
    
    try:
        memory_config = load_config()
        memory_manager = MemoryLayerManager(config=memory_config)
        chat_manager = ChatManager(memory_manager=memory_manager)
        
        print("✅ Components initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize components: {e}")
        return
    
    # Demo user and session
    user_id = "demo_user_123"
    session_id = "demo_session_456"
    
    print(f"\n2. Demo User: {user_id}")
    print(f"   Session: {session_id}")
    
    # Simulate a series of conversations to build learning data
    print("\n3. Simulating conversation history for learning...")
    
    conversation_scenarios = [
        {
            "user_message": "What are your support hours?",
            "bot_response": "Our support hours are Monday-Friday 8AM-8PM, Saturday-Sunday 9AM-6PM. You can reach us by phone at 0800 800 150 or through live chat.",
            "tools_used": ["BTSupportHours", "SupportKnowledgeBase"],
            "quality_score": 0.9
        },
        {
            "user_message": "I need help with my broadband connection",
            "bot_response": "I can help you troubleshoot your broadband connection. First, please check if all cables are securely connected and try restarting your router.",
            "tools_used": ["SupportKnowledgeBase", "ContextRetriever"],
            "quality_score": 0.8
        },
        {
            "user_message": "What mobile plans do you offer?",
            "bot_response": "We offer several mobile plans including Essential (£20/month), Plus (£30/month), and Premium (£45/month) with varying data allowances and features.",
            "tools_used": ["BTPlansInformation", "BTWebsiteSearch"],
            "quality_score": 0.95
        },
        {
            "user_message": "How do I upgrade my plan?",
            "bot_response": "You can upgrade your plan through your online account, by calling customer service, or I can guide you through the process. What type of upgrade are you looking for?",
            "tools_used": ["SupportKnowledgeBase", "BTPlansInformation"],
            "quality_score": 0.85
        },
        {
            "user_message": "I'm having billing issues",
            "bot_response": "I understand you're having billing concerns. Let me create a support ticket for you to get this resolved quickly by our billing team.",
            "tools_used": ["CreateSupportTicket", "SupportKnowledgeBase"],
            "quality_score": 0.9
        }
    ]
    
    # Store conversation history
    for i, scenario in enumerate(conversation_scenarios):
        conversation = ConversationEntryDTO(
            session_id=f"{session_id}_{i}",
            user_id=user_id,
            user_message=scenario["user_message"],
            bot_response=scenario["bot_response"],
            tools_used=scenario["tools_used"],
            tool_performance={tool: {"success": True, "execution_time": 0.5} for tool in scenario["tools_used"]},
            context_used=[f"context_{i}"],
            response_quality_score=scenario["quality_score"],
            timestamp=datetime.now()
        )
        
        success = memory_manager.store_conversation(conversation)
        if success:
            print(f"   ✅ Stored conversation {i+1}: {scenario['user_message'][:50]}...")
        else:
            print(f"   ❌ Failed to store conversation {i+1}")
    
    print(f"\n4. Stored {len(conversation_scenarios)} conversations for learning")
    
    # Demonstrate context retrieval with learning
    print("\n5. Testing context retrieval with learning...")
    
    test_queries = [
        "What are your hours?",  # Similar to stored query
        "I need help with internet",  # Similar to broadband query
        "Tell me about plans",  # Similar to mobile plans query
        "I have a billing problem"  # Similar to billing issues
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        
        # Get context using memory manager
        context_entries = memory_manager.retrieve_context(query, user_id, limit=5)
        
        if context_entries:
            print(f"   📚 Retrieved {len(context_entries)} relevant context entries:")
            for j, ctx in enumerate(context_entries[:2]):  # Show top 2
                print(f"      {j+1}. {ctx.context_type}: {ctx.content[:80]}... (relevance: {ctx.relevance_score:.2f})")
        else:
            print("   📚 No relevant context found")
        
        # Get tool recommendations based on learning
        tool_recommendation = memory_manager.analyze_tool_usage(query, [])
        if tool_recommendation:
            print(f"   🔧 Recommended tool: {tool_recommendation.tool_name} (confidence: {tool_recommendation.confidence_score:.2f})")
            print(f"      Reason: {tool_recommendation.reason}")
        else:
            print("   🔧 No tool recommendations available")
    
    # Demonstrate chat manager with learning
    print("\n6. Testing enhanced chat manager with learning...")
    
    test_message = "What are your support hours and how can I contact you?"
    print(f"\n   Processing: '{test_message}'")
    
    try:
        # Process message with learning-enhanced chat manager
        response = await chat_manager.process_message(test_message, user_id, session_id)
        
        print(f"   📝 Response: {response.content[:200]}...")
        print(f"   🔧 Tools used: {response.tools_used}")
        print(f"   📊 Confidence: {response.confidence_score:.2f}")
        print(f"   ⏱️  Execution time: {response.execution_time:.2f}s")
        print(f"   📚 Context sources: {response.context_used}")
        
        # Show learning insights
        insights = chat_manager.get_learning_insights(user_id)
        if "error" not in insights:
            print(f"\n   🧠 Learning Insights:")
            print(f"      Total conversations: {insights.get('total_conversations', 0)}")
            print(f"      Average quality: {insights.get('avg_quality_score', 0):.2f}")
            print(f"      Successful tools: {insights.get('most_successful_tools', [])}")
            
            if insights.get('improvement_suggestions'):
                print(f"      Suggestions: {insights['improvement_suggestions'][0]}")
        
    except Exception as e:
        print(f"   ❌ Error processing message: {e}")
    
    # Show memory statistics
    print("\n7. Memory Layer Statistics:")
    try:
        stats = memory_manager.get_memory_stats()
        print(f"   📊 Total conversations: {stats.total_conversations}")
        print(f"   📊 Total context entries: {stats.total_context_entries}")
        print(f"   📊 Health score: {stats.health_score:.2f}")
        print(f"   📊 Error count: {stats.error_count}")
        if stats.average_response_time > 0:
            print(f"   📊 Average response time: {stats.average_response_time:.3f}s")
    except Exception as e:
        print(f"   ❌ Error getting memory stats: {e}")
    
    print("\n8. Demo completed! 🎉")
    print("\nKey Learning Features Demonstrated:")
    print("   ✅ Persistent conversation storage")
    print("   ✅ Context-aware response generation")
    print("   ✅ Tool usage learning and recommendations")
    print("   ✅ Conversation pattern analysis")
    print("   ✅ Quality score tracking")
    print("   ✅ Performance optimization")
    print("   ✅ Learning insights and suggestions")

def main():
    """Run the demo."""
    try:
        asyncio.run(demo_session_memory_learning())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo failed: {e}")

if __name__ == "__main__":
    main()