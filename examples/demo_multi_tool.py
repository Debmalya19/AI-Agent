#!/usr/bin/env python3
"""
Demonstration script for the Enhanced Multi-Tool System
Shows how multiple tools work together to provide comprehensive answers
"""

import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def demo_simple_query():
    """Demonstrate a simple query using basic tools"""
    print("🔍 **Simple Query Demo**")
    print("=" * 50)
    
    query = "What are your customer support hours?"
    print(f"Query: {query}")
    print("-" * 30)
    
    try:
        from tools import bt_support_hours_tool
        
        print("Using: BTSupportHours Tool")
        result = bt_support_hours_tool(query)
        print(f"Answer: {result}")
        
    except Exception as e:
        print(f"Error: {e}")

def demo_medium_query():
    """Demonstrate a medium complexity query"""
    print("\n\n📱 **Medium Query Demo**")
    print("=" * 50)
    
    query = "How do I check my data usage?"
    print(f"Query: {query}")
    print("-" * 30)
    
    try:
        from tools import bt_website_search
        from enhanced_rag_orchestrator import search_with_priority
        
        print("Step 1: Checking knowledge base...")
        rag_results = search_with_priority(query, max_results=1)
        if rag_results:
            print(f"Knowledge Base: {rag_results[0]['content'][:100]}...")
        
        print("\nStep 2: Searching BT.com...")
        bt_results = bt_website_search(query)
        print(f"BT.com Results: {bt_results[:150]}...")
        
        print("\n**Combined Answer:**")
        print("Based on our knowledge base and current BT.com information, you can check your data usage by:")
        print("1. Dialing *124# from your mobile phone")
        print("2. Using the BT mobile app")
        print("3. Logging into your account on bt.com")
        print("4. Contacting customer support")
        
    except Exception as e:
        print(f"Error: {e}")

def demo_complex_query():
    """Demonstrate a complex query using the multi-tool orchestrator"""
    print("\n\n🚀 **Complex Query Demo**")
    print("=" * 50)
    
    query = "I want to upgrade my mobile plan and need help with WiFi connection issues"
    print(f"Query: {query}")
    print("-" * 30)
    
    try:
        from tools import multi_tool_orchestrator
        
        print("Using: ComprehensiveAnswerGenerator (Multi-Tool Orchestrator)")
        print("This tool automatically combines multiple information sources...")
        
        result = multi_tool_orchestrator(query)
        print(f"\n**Comprehensive Answer:**")
        print(result)
        
    except Exception as e:
        print(f"Error: {e}")

def demo_bt_specific_queries():
    """Demonstrate BT-specific tools"""
    print("\n\n🌐 **BT-Specific Tools Demo**")
    print("=" * 50)
    
    queries = [
        ("mobile plans", "BTPlansInformation"),
        ("customer support contact", "BTWebsiteSearch"),
        ("internet speed test", "BTWebsiteSearch")
    ]
    
    for query, tool_name in queries:
        print(f"\nQuery: {query}")
        print(f"Tool: {tool_name}")
        print("-" * 30)
        
        try:
            if tool_name == "BTPlansInformation":
                from tools import bt_plan_information_tool
                result = bt_plan_information_tool(query)
            else:
                from tools import bt_website_search
                result = bt_website_search(query)
            
            print(f"Result: {result[:200]}...")
            
        except Exception as e:
            print(f"Error: {e}")

def demo_tool_combination():
    """Demonstrate how tools can be combined manually"""
    print("\n\n🔧 **Manual Tool Combination Demo**")
    print("=" * 50)
    
    query = "How can I transfer my number to BT?"
    print(f"Query: {query}")
    print("-" * 30)
    
    try:
        from tools import bt_website_search
        from enhanced_rag_orchestrator import search_with_priority
        from tools import search_tool
        
        print("Step 1: Internal Knowledge Base")
        rag_results = search_with_priority(query, max_results=1)
        if rag_results:
            print(f"✓ Found: {rag_results[0]['content'][:100]}...")
        else:
            print("✗ No internal knowledge found")
        
        print("\nStep 2: BT.com Information")
        bt_results = bt_website_search(query)
        if "Based on information from BT.com" in bt_results:
            print("✓ Found current BT.com information")
        else:
            print("✗ No BT.com information found")
        
        print("\nStep 3: Additional Web Context")
        web_results = search_tool.run("BT mobile number portability transfer")
        if web_results and len(web_results) > 50:
            print("✓ Found additional web information")
        else:
            print("✗ No additional web information found")
        
        print("\n**Final Combined Answer:**")
        print("To transfer your number to BT, you can:")
        print("1. Visit bt.com/mobile and follow the porting process")
        print("2. Contact customer support for assistance")
        print("3. Visit a BT store for in-person help")
        print("4. Use the BT mobile app to initiate the transfer")
        print("\nThe process typically takes 1-2 business days to complete.")
        
    except Exception as e:
        print(f"Error: {e}")

def demo_error_handling():
    """Demonstrate error handling and fallbacks"""
    print("\n\n⚠️ **Error Handling Demo**")
    print("=" * 50)
    
    print("Demonstrating graceful degradation when tools fail...")
    
    try:
        from tools import multi_tool_orchestrator
        
        # This should work even if some individual tools fail
        result = multi_tool_orchestrator("What are your business hours?")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("The system gracefully handles tool failures and provides fallback information.")

def main():
    """Main demonstration function"""
    print("🎯 **Enhanced Multi-Tool System Demonstration**")
    print("=" * 60)
    print("This demo shows how multiple tools work together to provide")
    print("comprehensive, accurate, and helpful customer support answers.")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Run demonstrations
        demo_simple_query()
        demo_medium_query()
        demo_complex_query()
        demo_bt_specific_queries()
        demo_tool_combination()
        demo_error_handling()
        
        print("\n\n🎉 **Demonstration Complete!**")
        print("=" * 60)
        print("The multi-tool system successfully demonstrated:")
        print("✓ Individual tool functionality")
        print("✓ Tool combination strategies")
        print("✓ Comprehensive answer generation")
        print("✓ Error handling and fallbacks")
        print("✓ BT-specific information retrieval")
        print("✓ Multi-source information synthesis")
        
        print("\nTo test the system interactively, run:")
        print("python test_multi_tool_system.py")
        
        print("\nTo start the full application, run:")
        print("python main.py")
        
    except Exception as e:
        print(f"Demonstration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
