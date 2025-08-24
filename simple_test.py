from enhanced_rag_orchestrator import search_with_priority

print("Testing RAG system...")
results = search_with_priority("How do I upgrade my plan?")
print(f"Found {len(results)} results")

for i, result in enumerate(results):
    print(f"\nResult {i+1}:")
    print(f"Source: {result['source']}")
    print(f"Content: {result['content'][:200]}...")
