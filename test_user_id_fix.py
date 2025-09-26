#!/usr/bin/env python3
"""
Test script to verify the user_id fix for the chat endpoint.
This script tests that the ConversationEntry is created correctly with string user_id.
"""

import sys
import os
sys.path.append('.')

from backend.memory_models import ConversationEntry
from backend.unified_auth import AuthenticatedUser, UserRole, Permission
from datetime import datetime

def test_conversation_entry_creation():
    """Test that ConversationEntry can be created with proper string user_id"""
    print("Testing ConversationEntry creation...")
    
    # Test with string user_id (should work)
    try:
        conversation = ConversationEntry(
            session_id='test_session_123',
            user_id='user_abc123',  # String user_id
            user_message='Hello, I need help with my account',
            bot_response='I can help you with your account. What specific issue are you experiencing?',
            tools_used=['SupportKnowledgeBase'],
            tool_performance={'SupportKnowledgeBase': 0.9},
            context_used=['session_context'],
            response_quality_score=0.8
        )
        print("✅ ConversationEntry created successfully with string user_id")
        print(f"   user_id: '{conversation.user_id}' (type: {type(conversation.user_id).__name__})")
        return True
    except Exception as e:
        print(f"❌ Error creating ConversationEntry with string user_id: {e}")
        return False

def test_authenticated_user_structure():
    """Test that AuthenticatedUser has both id and user_id fields"""
    print("\nTesting AuthenticatedUser structure...")
    
    try:
        # Create a mock AuthenticatedUser
        user = AuthenticatedUser(
            id=123,  # Integer ID
            user_id='user_abc123',  # String user_id
            username='testuser',
            email='test@example.com',
            full_name='Test User',
            role=UserRole.CUSTOMER,
            is_active=True,
            is_admin=False,
            permissions=set(),
            session_id='session_123'
        )
        
        print("✅ AuthenticatedUser created successfully")
        print(f"   id: {user.id} (type: {type(user.id).__name__})")
        print(f"   user_id: '{user.user_id}' (type: {type(user.user_id).__name__})")
        
        # Test that we should use user_id for ConversationEntry
        conversation = ConversationEntry(
            session_id=user.session_id,
            user_id=user.user_id,  # Use user_id (string), not id (int)
            user_message='Test message',
            bot_response='Test response'
        )
        print("✅ ConversationEntry created successfully using user.user_id")
        return True
        
    except Exception as e:
        print(f"❌ Error in AuthenticatedUser test: {e}")
        return False

def test_integer_user_id_rejection():
    """Test that ConversationEntry rejects integer user_id"""
    print("\nTesting integer user_id rejection...")
    
    try:
        conversation = ConversationEntry(
            session_id='test_session',
            user_id=123,  # Integer user_id (should fail)
            user_message='Test message',
            bot_response='Test response'
        )
        print("❌ ConversationEntry incorrectly accepted integer user_id")
        return False
    except ValueError as e:
        if "user_id must be a non-empty string" in str(e):
            print("✅ ConversationEntry correctly rejected integer user_id")
            return True
        else:
            print(f"❌ Unexpected error: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error type: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing user_id fix for chat endpoint memory storage")
    print("=" * 60)
    
    tests = [
        test_conversation_entry_creation,
        test_authenticated_user_structure,
        test_integer_user_id_rejection
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! The user_id fix should resolve the memory storage error.")
        print("\nThe issue was:")
        print("- Chat endpoint was using current_user.id (integer)")
        print("- ConversationEntry validation requires user_id to be a non-empty string")
        print("- Fixed by using current_user.user_id (string) instead")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    print("=" * 60)
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)