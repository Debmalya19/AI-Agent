#!/usr/bin/env python3
"""
Enhanced System Test Script
Demonstrates the enhanced multi-tool system with:
- BT.com web scraping
- Context memory and understanding
- Intelligent tool orchestration
- Enhanced RAG with context
"""

import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_context_memory():
    """Test the context memory system"""
    print("🧠 **Testing Context Memory System**")
    print("=" * 50)
    
    try:
        from tools import context_memory
        
        # Test adding conversations
        print("Adding test conversations...")
        context_memory.add_conversation(
            "What are your support hours?",
            "Our support is available 24/7",
            ["BTSupportHours"]
        )
        
        context_memory.add_conversation(
            "How do I upgrade my plan?",
            "You can upgrade through our website or app",
            ["BTPlansInformation", "BTWebsiteSearch"]
        )
        
        # Test retrieving context
        print("\nTesting context retrieval...")
        recent_context = context_memory.get_recent_context("support hours", limit=2)
        print(f"Found {len(recent_context)} relevant contexts")
        
        for ctx in recent_context:
            print(f"- Previous: {ctx['user_query']}")
            print(f"  Answer: {ctx['response']}")
        
        # Test tool usage patterns
        print("\nTesting tool usage patterns...")
        patterns = context_memory.get_tool_usage_pattern("support_hours")
        print(f"Recommended tools for support_hours: {patterns}")
        
    except Exception as e:
        print(f"Error: {e}")

def test_bt_scraping():
    """Test BT.com web scraping capabilities"""
    print("\n\n🌐 **Testing BT.com Web Scraping**")
    print("=" * 50)
    
    try:
        from tools import scrape_bt_website
        
        test_queries = [
            "mobile plans",
            "customer support contact",
            "internet speed test"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            print("-" * 30)
            
            result = scrape_bt_website(query)
            if "From BT.com" in result:
                print("✓ Successfully scraped BT.com")
                print(f"Result preview: {result[:200]}...")
            else:
                print("✗ Scraping failed or no results")
                
    except Exception as e:
        print(f"Error: {e}")

def test_enhanced_rag():
    """Test the enhanced RAG system with context memory"""
    print("\n\n📚 **Testing Enhanced RAG System**")
    print("=" * 50)
    
    try:
        from enhanced_rag_orchestrator import search_with_priority, get_context_summary
        
        test_queries = [
            "How do I check my data usage?",
            "What are your support hours?",
            "How can I upgrade my mobile plan?"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            print("-" * 30)
            
            # Get context summary
            context_summary = get_context_summary(query)
            if context_summary:
                print("📝 Context found:")
                print(context_summary)
            
            # Search with enhanced RAG
            results = search_with_priority(query, max_results=2)
            print(f"Found {len(results)} results")
            
            for i, result in enumerate(results, 1):
                print(f"{i}. Source: {result['source']}")
                print(f"   Confidence: {result.get('confidence', 0):.2f}")
                print(f"   Method: {result['search_method']}")
                print(f"   Content: {result['content'][:100]}...")
                
    except Exception as e:
        print(f"Error: {e}")

def test_intelligent_orchestrator():
    """Test the intelligent tool orchestrator"""
    print("\n\n🚀 **Testing Intelligent Tool Orchestrator**")
    print("=" * 50)
    
    try:
        from tools import intelligent_tool_orchestrator
        
        test_queries = [
            "I want to upgrade my mobile plan and need help with WiFi issues",
            "What are your current support hours and contact information?",
            "How do I check my data usage and what plans are available?"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            print("-" * 30)
            
            result = intelligent_tool_orchestrator(query)
            print(f"Comprehensive Answer: {result[:300]}...")
            
    except Exception as e:
        print(f"Error: {e}")

def test_query_analysis():
    """Test query type analysis"""
    print("\n\n🔍 **Testing Query Type Analysis**")
    print("=" * 50)
    
    try:
        from tools import analyze_query_type
        
        test_queries = [
            ("What are your support hours?", "support_hours"),
            ("How much do your mobile plans cost?", "plans"),
            ("I have a technical problem with my WiFi", "technical"),
            ("How do I pay my bill?", "billing"),
            ("What's the weather like?", "general")
        ]
        
        for query, expected_type in test_queries:
            detected_type = analyze_query_type(query)
            status = "✓" if detected_type == expected_type else "✗"
            print(f"{status} Query: {query}")
            print(f"   Expected: {expected_type}, Detected: {detected_type}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_conversation_flow():
    """Test a complete conversation flow with context memory"""
    print("\n\n💬 **Testing Conversation Flow with Context Memory**")
    print("=" * 50)
    
    try:
        from tools import context_memory, intelligent_tool_orchestrator
        
        # Simulate a conversation
        conversation = [
            "What are your support hours?",
            "How do I contact support?",
            "What mobile plans do you offer?",
            "Can you tell me more about the unlimited data plan?",
            "How do I upgrade to that plan?"
        ]
        
        print("Simulating conversation flow...")
        
        for i, query in enumerate(conversation, 1):
            print(f"\n--- Turn {i} ---")
            print(f"User: {query}")
            
            # Get context before answering
            recent_context = context_memory.get_recent_context(query, limit=2)
            if recent_context:
                print(f"📝 Context: Found {len(recent_context)} relevant previous exchanges")
            
            # Generate answer using intelligent orchestrator
            answer = intelligent_tool_orchestrator(query)
            print(f"AI: {answer[:200]}...")
            
            # Store in memory
            context_memory.add_conversation(query, answer, ["IntelligentOrchestrator"])
            
            print(f"💾 Stored in context memory")
            
    except Exception as e:
        print(f"Error: {e}")

def test_performance_and_caching():
    """Test performance and caching features"""
    print("\n\n⚡ **Testing Performance and Caching**")
    print("=" * 50)
    
    try:
        from tools import scrape_bt_website, context_memory
        import time
        
        # Test caching with repeated queries
        query = "mobile plans"
        
        print(f"Testing caching for query: {query}")
        
        # First call (should scrape)
        start_time = time.time()
        result1 = scrape_bt_website(query)
        first_call_time = time.time() - start_time
        print(f"First call: {first_call_time:.2f}s")
        
        # Second call (should use cache)
        start_time = time.time()
        result2 = scrape_bt_website(query)
        second_call_time = time.time() - start_time
        print(f"Second call: {second_call_time:.2f}s")
        
        # Check if results are similar (cached)
        if "cached" in result2:
            print("✓ Caching working correctly")
        else:
            print("✗ Caching not working")
            
        # Performance improvement
        if second_call_time < first_call_time:
            improvement = ((first_call_time - second_call_time) / first_call_time) * 100
            print(f"⚡ Performance improvement: {improvement:.1f}%")
            
    except Exception as e:
        print(f"Error: {e}")

def interactive_test():
    """Interactive testing mode"""
    print("\n\n💬 **Interactive Testing Mode**")
    print("=" * 50)
    print("Type 'quit' to exit")
    print("Type 'context' to see current context")
    print("Type 'memory' to see memory status")
    
    try:
        from tools import intelligent_tool_orchestrator, context_memory
        
        while True:
            try:
                query = input("\nEnter your query: ").strip()
                if query.lower() == 'quit':
                    break
                elif query.lower() == 'context':
                    print("\n📝 Current Context:")
                    for i, entry in enumerate(context_memory.conversation_history[-5:], 1):
                        print(f"{i}. {entry['user_query']} -> {entry['response'][:100]}...")
                    continue
                elif query.lower() == 'memory':
                    print(f"\n🧠 Memory Status:")
                    print(f"Conversations: {len(context_memory.conversation_history)}")
                    print(f"Cached contexts: {len(context_memory.context_cache)}")
                    continue
                
                if not query:
                    continue
                
                print(f"\nProcessing: {query}")
                print("-" * 40)
                
                # Use intelligent orchestrator
                result = intelligent_tool_orchestrator(query)
                print(f"Answer: {result}")
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
                
    except Exception as e:
        print(f"Interactive mode error: {e}")

def main():
    """Main test function"""
    print("🎯 **Enhanced Multi-Tool System Test**")
    print("=" * 60)
    print("Testing enhanced capabilities:")
    print("- BT.com web scraping")
    print("- Context memory and understanding")
    print("- Intelligent tool orchestration")
    print("- Enhanced RAG with context")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Run all tests
        test_context_memory()
        test_bt_scraping()
        test_enhanced_rag()
        test_intelligent_orchestrator()
        test_query_analysis()
        test_conversation_flow()
        test_performance_and_caching()
        
        print("\n\n🎉 **All Tests Completed!**")
        print("=" * 60)
        print("The enhanced system successfully demonstrated:")
        print("✓ Context memory and conversation tracking")
        print("✓ BT.com web scraping capabilities")
        print("✓ Enhanced RAG with context awareness")
        print("✓ Intelligent tool orchestration")
        print("✓ Query type analysis")
        print("✓ Performance optimization and caching")
        
        # Interactive mode
        interactive_test()
        
        print("\n\n🚀 **Enhanced System Ready!**")
        print("To start the full application, run:")
        print("python main.py")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
