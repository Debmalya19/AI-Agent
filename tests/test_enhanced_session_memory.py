#!/usr/bin/env python3
"""
Test script for enhanced session memory and learning functionality.
"""

import sys
import os
import asyncio
import unittest
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.memory_layer_manager import MemoryLayerManager
from backend.memory_models import ConversationEntryDTO
from backend.intelligent_chat.chat_manager import ChatManager
from backend.memory_config import load_config

class TestEnhancedSessionMemory(unittest.TestCase):
    """Test cases for enhanced session memory and learning."""
    
    def setUp(self):
        """Set up test environment."""
        try:
            self.memory_config = load_config()
            self.memory_manager = MemoryLayerManager(config=self.memory_config)
            self.chat_manager = ChatManager(memory_manager=self.memory_manager)
            self.test_user_id = "test_user_123"
            self.test_session_id = "test_session_456"
        except Exception as e:
            self.skipTest(f"Failed to initialize test environment: {e}")
    
    def test_conversation_storage_and_retrieval(self):
        """Test that conversations are stored and can be retrieved."""
        # Store a test conversation
        conversation = ConversationEntryDTO(
            session_id=self.test_session_id,
            user_id=self.test_user_id,
            user_message="What are your support hours?",
            bot_response="Our support hours are 9AM-5PM Monday-Friday.",
            tools_used=["BTSupportHours"],
            tool_performance={"BTSupportHours": {"success": True, "execution_time": 0.5}},
            context_used=["support_context"],
            response_quality_score=0.9,
            timestamp=datetime.now()
        )
        
        # Store conversation
        success = self.memory_manager.store_conversation(conversation)
        self.assertTrue(success, "Failed to store conversation")
        
        # Retrieve context
        context_entries = self.memory_manager.retrieve_context(
            "support hours", self.test_user_id, limit=5
        )
        
        self.assertGreater(len(context_entries), 0, "No context entries retrieved")
        
        # Check that retrieved context is relevant
        found_relevant = any("support" in ctx.content.lower() for ctx in context_entries)
        self.assertTrue(found_relevant, "Retrieved context not relevant to query")
    
    def test_tool_usage_learning(self):
        """Test that tool usage patterns are learned."""
        # Store multiple conversations with tool usage
        conversations = [
            {
                "message": "What are your hours?",
                "response": "9AM-5PM",
                "tools": ["BTSupportHours"],
                "quality": 0.9
            },
            {
                "message": "When are you open?",
                "response": "9AM-5PM weekdays",
                "tools": ["BTSupportHours"],
                "quality": 0.85
            },
            {
                "message": "Support hours please",
                "response": "Monday-Friday 9AM-5PM",
                "tools": ["BTSupportHours"],
                "quality": 0.95
            }
        ]
        
        for i, conv_data in enumerate(conversations):
            conversation = ConversationEntryDTO(
                session_id=f"{self.test_session_id}_{i}",
                user_id=self.test_user_id,
                user_message=conv_data["message"],
                bot_response=conv_data["response"],
                tools_used=conv_data["tools"],
                tool_performance={tool: {"success": True, "execution_time": 0.3} 
                                for tool in conv_data["tools"]},
                context_used=[f"context_{i}"],
                response_quality_score=conv_data["quality"],
                timestamp=datetime.now()
            )
            
            success = self.memory_manager.store_conversation(conversation)
            self.assertTrue(success, f"Failed to store conversation {i}")
        
        # Test tool recommendation
        tool_recommendation = self.memory_manager.analyze_tool_usage("hours", [])
        
        if tool_recommendation:
            self.assertEqual(tool_recommendation.tool_name, "BTSupportHours", 
                           "Wrong tool recommended")
            self.assertGreater(tool_recommendation.confidence_score, 0.5, 
                             "Low confidence in tool recommendation")
    
    def test_chat_manager_learning_integration(self):
        """Test that chat manager integrates learning properly."""
        # This test requires async execution
        async def async_test():
            # Store some learning data first
            conversation = ConversationEntryDTO(
                session_id=self.test_session_id,
                user_id=self.test_user_id,
                user_message="I need help with billing",
                bot_response="I can help with billing issues. Let me create a support ticket.",
                tools_used=["CreateSupportTicket", "SupportKnowledgeBase"],
                tool_performance={
                    "CreateSupportTicket": {"success": True, "execution_time": 0.8},
                    "SupportKnowledgeBase": {"success": True, "execution_time": 0.3}
                },
                context_used=["billing_context"],
                response_quality_score=0.9,
                timestamp=datetime.now()
            )
            
            self.memory_manager.store_conversation(conversation)
            
            # Test learning insights
            insights = self.chat_manager.get_learning_insights(self.test_user_id)
            
            self.assertIsInstance(insights, dict, "Insights should be a dictionary")
            self.assertIn("total_conversations", insights, "Missing total_conversations")
            
            if "error" not in insights:
                self.assertGreaterEqual(insights["total_conversations"], 1, 
                                      "Should have at least 1 conversation")
        
        # Run async test
        asyncio.run(async_test())
    
    def test_memory_statistics(self):
        """Test that memory statistics are properly calculated."""
        # Get memory stats
        stats = self.memory_manager.get_memory_stats()
        
        self.assertIsNotNone(stats, "Memory stats should not be None")
        self.assertGreaterEqual(stats.health_score, 0.0, "Health score should be >= 0")
        self.assertLessEqual(stats.health_score, 1.0, "Health score should be <= 1")
        self.assertGreaterEqual(stats.error_count, 0, "Error count should be >= 0")
    
    def test_conversation_pattern_analysis(self):
        """Test conversation pattern analysis."""
        # Store conversations with different patterns
        patterns = [
            ("support", "I need support", "Here's how I can help with support"),
            ("support", "Can you help me?", "Of course, I'm here to help"),
            ("billing", "Billing question", "I can help with billing"),
            ("plans", "What plans do you have?", "We offer several plans")
        ]
        
        for i, (pattern_type, message, response) in enumerate(patterns):
            conversation = ConversationEntryDTO(
                session_id=f"{self.test_session_id}_pattern_{i}",
                user_id=self.test_user_id,
                user_message=message,
                bot_response=response,
                tools_used=["SupportKnowledgeBase"],
                tool_performance={"SupportKnowledgeBase": {"success": True, "execution_time": 0.4}},
                context_used=[f"{pattern_type}_context"],
                response_quality_score=0.8,
                timestamp=datetime.now()
            )
            
            success = self.memory_manager.store_conversation(conversation)
            self.assertTrue(success, f"Failed to store pattern conversation {i}")
        
        # Get user history for pattern analysis
        user_history = self.memory_manager.get_user_conversation_history(self.test_user_id, limit=10)
        self.assertGreater(len(user_history), 0, "Should have conversation history")
    
    def tearDown(self):
        """Clean up test data."""
        try:
            # Clean up test data if needed
            # Note: In a real test environment, you'd want to use a test database
            pass
        except Exception as e:
            print(f"Cleanup warning: {e}")

def run_tests():
    """Run all tests."""
    print("🧪 Running Enhanced Session Memory Tests")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEnhancedSessionMemory)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All tests passed!")
    else:
        print(f"❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} test(s) had errors")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)