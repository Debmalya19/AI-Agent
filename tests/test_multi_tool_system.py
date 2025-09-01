#!/usr/bin/env python3
"""
Test script for the enhanced multi-tool system
Demonstrates how multiple tools work together to provide comprehensive answers
"""

import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import (
    bt_website_search, bt_support_hours_tool, bt_plan_information_tool,
    multi_tool_orchestrator, search_tool, wiki_tool
)

def test_bt_website_search():
    """Test BT website search functionality"""
    print("🔍 Testing BT Website Search Tool")
    print("=" * 50)
    
    test_queries = [
        "mobile plans",
        "customer support contact",
        "internet speed test",
        "WiFi troubleshooting"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 30)
        try:
            result = bt_website_search(query)
            print(f"Result: {result[:200]}...")
        except Exception as e:
            print(f"Error: {e}")

def test_bt_support_hours():
    """Test BT support hours tool"""
    print("\n\n🕒 Testing BT Support Hours Tool")
    print("=" * 50)
    
    try:
        # Note: bt_support_hours_tool is a function, not a LangChain tool, so direct call is correct
        result = bt_support_hours_tool("What are your support hours?")
        print(f"Support Hours Result: {result}")
    except Exception as e:
        print(f"Error: {e}")

def test_bt_plans():
    """Test BT plans information tool"""
    print("\n\n📱 Testing BT Plans Information Tool")
    print("=" * 50)
    
    test_queries = [
        "unlimited data plans",
        "family plans",
        "5G plans"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 30)
        try:
            # Note: bt_plan_information_tool is a function, not a LangChain tool, so direct call is correct
            result = bt_plan_information_tool(query)
            print(f"Result: {result[:200]}...")
        except Exception as e:
            print(f"Error: {e}")

def test_multi_tool_orchestrator():
    """Test the multi-tool orchestrator"""
    print("\n\n🚀 Testing Multi-Tool Orchestrator")
    print("=" * 50)
    
    test_queries = [
        "How do I check my data usage?",
        "What are your customer support hours?",
        "How can I upgrade my mobile plan?",
        "WiFi connection problems"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 30)
        try:
            result = multi_tool_orchestrator(query)
            print(f"Comprehensive Result: {result[:300]}...")
        except Exception as e:
            print(f"Error: {e}")

def test_individual_tools():
    """Test individual tools separately"""
    print("\n\n🔧 Testing Individual Tools")
    print("=" * 50)
    
    # Test web search
    print("\nTesting Web Search Tool:")
    try:
        result = search_tool.invoke({"query": "BT mobile plans 2024"})
        print(f"Web Search Result: {result[:200]}...")
    except Exception as e:
        print(f"Web Search Error: {e}")
    
    # Test Wikipedia tool
    print("\nTesting Wikipedia Tool:")
    try:
        result = wiki_tool.invoke({"query": "telecommunications"})
        print(f"Wikipedia Result: {result[:200]}...")
    except Exception as e:
        print(f"Wikipedia Error: {e}")

def interactive_test():
    """Interactive testing mode"""
    print("\n\n💬 Interactive Testing Mode")
    print("=" * 50)
    print("Type 'quit' to exit")
    
    while True:
        try:
            query = input("\nEnter your query: ").strip()
            if query.lower() == 'quit':
                break
            
            if not query:
                continue
            
            print(f"\nProcessing: {query}")
            print("-" * 40)
            
            # Use multi-tool orchestrator for comprehensive answer
            result = multi_tool_orchestrator(query)
            print(f"Answer: {result}")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    """Main test function"""
    print("🧪 Enhanced Multi-Tool System Test")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Test individual tools
        test_bt_website_search()
        test_bt_support_hours()
        test_bt_plans()
        test_individual_tools()
        
        # Test multi-tool orchestrator
        test_multi_tool_orchestrator()
        
        # Interactive mode
        interactive_test()
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
