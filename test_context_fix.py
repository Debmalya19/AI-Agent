#!/usr/bin/env python3
"""
Test script to verify context understanding fix
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.intelligent_chat.chat_manager import ChatManager
from backend.memory_layer_manager import MemoryLayerManager
from backend.memory_config import load_config

async def test_context_understanding():
    """Test that the chat system maintains context between messages"""
    
    print("🧪 Testing Context Understanding Fix")
    print("=" * 50)
    
    # Initialize components
    memory_config = load_config()
    memory_manager = MemoryLayerManager(config=memory_config)
    
    chat_manager = ChatManager(
        memory_manager=memory_manager,
        auto_create_context_engine=True
    )
    
    # Test user and session
    user_id = "test_user_123"
    session_id = "test_session_456"
    
    print(f"👤 User ID: {user_id}")
    print(f"🔗 Session ID: {session_id}")
    print()
    
    # Test conversation sequence
    test_messages = [
        "I'm having trouble with my broadband router",
        "It's still not working after restarting",
        "What should I do next?"
    ]
    
    responses = []
    
    for i, message in enumerate(test_messages, 1):
        print(f"📝 Message {i}: {message}")
        
        try:
            response = await chat_manager.process_message(
                message=message,
                user_id=user_id,
                session_id=session_id
            )
            
            responses.append(response)
            
            print(f"🤖 Response {i}: {response.content[:100]}...")
            print(f"🔧 Tools used: {response.tools_used}")
            print(f"📊 Context used: {len(response.context_used)} entries")
            print(f"⭐ Confidence: {response.confidence_score:.2f}")
            print(f"⏱️  Time: {response.execution_time:.3f}s")
            print()
            
            # Check if context is being maintained
            if i > 1:
                # For subsequent messages, we should have context from previous messages
                if len(response.context_used) > 0:
                    print(f"✅ Context maintained: {len(response.context_used)} entries found")
                else:
                    print("❌ Context not maintained: No previous context found")
                print()
            
        except Exception as e:
            print(f"❌ Error processing message {i}: {e}")
            print()
    
    # Test session stats
    print("📈 Session Statistics:")
    session_stats = chat_manager.get_session_stats(user_id, session_id)
    for key, value in session_stats.items():
        print(f"  {key}: {value}")
    print()
    
    # Test global stats
    print("🌍 Global Statistics:")
    global_stats = chat_manager.get_global_stats()
    for key, value in global_stats.items():
        print(f"  {key}: {value}")
    print()
    
    print("✅ Context understanding test completed!")
    
    return responses

if __name__ == "__main__":
    asyncio.run(test_context_understanding())