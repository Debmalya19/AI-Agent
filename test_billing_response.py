#!/usr/bin/env python3
"""
Test script to verify that billing queries get the correct response.
"""

import sys
import os
import asyncio

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from intelligent_chat.chat_manager import ChatManager

async def test_billing_response():
    """Test that billing queries get the correct response."""
    
    # Initialize ChatManager
    chat_manager = ChatManager(auto_create_context_engine=False)
    
    # Test billing queries
    billing_queries = [
        "I need help with my bill",
        "How much does my plan cost?",
        "I have a question about my payment",
        "My invoice seems wrong",
        "What are the charges on my account?"
    ]
    
    print("Testing billing response improvements...")
    print("=" * 50)
    
    for i, query in enumerate(billing_queries, 1):
        print(f"\nTest {i}: '{query}'")
        print("-" * 30)
        
        try:
            response = await chat_manager.process_message(
                message=query,
                user_id=f"billing_test_user_{i}",
                session_id=f"billing_test_session_{i}"
            )
            
            print(f"Response: {response.content}")
            
            # Check if it's a billing-specific response
            billing_keywords = ['billing', 'bill', 'payment', 'account', 'charge']
            if any(keyword in response.content.lower() for keyword in billing_keywords):
                print("✅ PASS: Billing-specific response provided")
            else:
                print("⚠️  WARNING: Generic response, not billing-specific")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("Billing response test completed!")

if __name__ == "__main__":
    asyncio.run(test_billing_response())