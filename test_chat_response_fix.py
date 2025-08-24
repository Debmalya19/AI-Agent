#!/usr/bin/env python3
"""
Test script to verify that the chat response fix is working correctly.
"""

import sys
import os
import asyncio
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from intelligent_chat.chat_manager import ChatManager
from intelligent_chat.models import ContextEntry

async def test_chat_response():
    """Test that chat responses are clean and helpful, not debug information."""
    
    # Initialize ChatManager
    chat_manager = ChatManager(auto_create_context_engine=False)
    
    # Test cases
    test_cases = [
        {
            "message": "my broadband is not working",
            "expected_keywords": ["broadband", "connection", "router", "troubleshoot"],
            "avoid_keywords": ["I received your message", "I found", "context entries"]
        },
        {
            "message": "How do I upgrade my plan?",
            "expected_keywords": ["upgrade", "plan", "package", "account"],
            "avoid_keywords": ["I received your message", "I found", "context entries"]
        }
    ]
    
    print("Testing chat response generation...")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['message']}")
        print("-" * 30)
        
        try:
            # Process the message
            response = await chat_manager.process_message(
                message=test_case['message'],
                user_id="test_user",
                session_id="test_session"
            )
            
            print(f"Response: {response.content}")
            print(f"Content Type: {response.content_type}")
            print(f"Confidence Score: {response.confidence_score}")
            print(f"Tools Used: {response.tools_used}")
            
            # Check for debug information
            debug_found = any(keyword.lower() in response.content.lower() 
                            for keyword in test_case['avoid_keywords'])
            
            if debug_found:
                print("❌ FAIL: Debug information found in response!")
                for keyword in test_case['avoid_keywords']:
                    if keyword.lower() in response.content.lower():
                        print(f"   Found debug keyword: '{keyword}'")
            else:
                print("✅ PASS: No debug information found")
            
            # Check for helpful content
            helpful_found = any(keyword.lower() in response.content.lower() 
                              for keyword in test_case['expected_keywords'])
            
            if helpful_found:
                print("✅ PASS: Helpful content found")
            else:
                print("⚠️  WARNING: Expected helpful keywords not found")
                print(f"   Expected one of: {test_case['expected_keywords']}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_chat_response())