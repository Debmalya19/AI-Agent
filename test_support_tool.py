from main import support_knowledge_tool_func

print("Testing support knowledge tool...")

queries = [
    "How do I upgrade my plan?",
    "What are your support hours?",
    "How do I change my plan?"
]

for query in queries:
    print(f"\n🔍 Query: {query}")
    print("-" * 40)
    result = support_knowledge_tool_func(query)
    print(f"Result: {result[:200]}...")
    print("=" * 50)
