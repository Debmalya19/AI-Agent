"""
Simple script to demonstrate using the Enhanced RAG System
"""

from enhanced_rag_orchestrator import search_with_priority
import json

def main():
    """Demonstrate the RAG system with various queries"""
    
    test_queries = [
        "How do I reset my BT router?",
        "What are the customer support hours?",
        "How to check my internet speed?",
        "Troubleshooting WiFi connection issues",
        "Contact BT customer service"
    ]
    
    print("🚀 Enhanced RAG System Demo")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        print("-" * 30)
        
        results = search_with_priority(query, max_results=3)
        
        if results:
            for i, result in enumerate(results, 1):
                method = result['search_method']
                confidence = result['confidence']
                source = result['source']
                content = result['content'][:150] + "..." if len(result['content']) > 150 else result['content']
                
                print(f"{i}. [{method.upper()}] Confidence: {confidence:.2f}")
                print(f"   Source: {source}")
                print(f"   Content: {content}")
                print()
        else:
            print("   No results found.")
    
    # Interactive mode
    print("\n" + "=" * 50)
    print("💬 Interactive Mode")
    print("Type 'quit' to exit")
    
    while True:
        user_query = input("\nEnter your query: ").strip()
        
        if user_query.lower() in ['quit', 'exit', 'q']:
            break
        
        if not user_query:
            continue
        
        results = search_with_priority(user_query, max_results=2)
        
        if results:
            print(f"\n✅ Found {len(results)} result(s):")
            for result in results:
                print(f"\n📄 {result['search_method'].upper()} (confidence: {result['confidence']:.2f})")
                print(f"   {result['content']}")
        else:
            print("\n❌ No relevant information found.")

if __name__ == "__main__":
    main()
