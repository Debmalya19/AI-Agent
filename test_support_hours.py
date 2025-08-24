from enhanced_rag_orchestrator import search_with_priority

print("Testing support hours query...")
results = search_with_priority("What are your support hours?")
print(f"Found {len(results)} results")

for i, result in enumerate(results):
    print(f"\nResult {i+1}:")
    print(f"Source: {result['source']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Content: {result['content'][:300]}...")
