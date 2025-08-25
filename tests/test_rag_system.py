#!/usr/bin/env python3
"""
Test script to verify the RAG system is working properly
"""

from enhanced_rag_orchestrator import search_with_priority
from main import support_knowledge_tool_func

def test_rag_system():
    """Test the RAG system with the problematic queries"""
    
    print("Testing RAG System...")
    print("=" * 50)
    
    # Test queries that were failing
    test_queries = [
        "How do I upgrade my plan?",
        "What are your support hours?",
        "How do I change my plan?"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        print("-" * 30)
        
        # Test RAG search
        print("📚 RAG Search Results:")
        rag_results = search_with_priority(query, max_results=3)
        
        if rag_results:
            for i, result in enumerate(rag_results, 1):
                print(f"  {i}. Confidence: {result['confidence']:.2f}")
                print(f"     Source: {result['source']}")
                print(f"     Content: {result['content'][:100]}...")
                print()
        else:
            print("  No results found")
        
        # Test support knowledge tool
        print("🛠️ Support Knowledge Tool:")
        support_result = support_knowledge_tool_func(query)
        print(f"  Result: {support_result[:100]}...")
        
        print("\n" + "=" * 50)

if __name__ == "__main__":
    test_rag_system()
