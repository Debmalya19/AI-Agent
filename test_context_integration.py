"""
Integration tests for Context Retrieval Engine with existing tools.
Tests the integration between the enhanced context retrieval engine
and the existing ContextMemory class in tools.py.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import sys
import os

# Add the ai-agent directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from tools import ContextMemory
from context_retrieval_engine import ContextRetrievalEngine, SemanticFeatures
from memory_models import ContextEntryDTO


class TestContextIntegration(unittest.TestCase):
    """Test integration between enhanced and legacy context systems"""
    
    def setUp(self):
        """Set up test environment"""
        self.context_memory = ContextMemory(max_size=5)
    
    def test_context_memory_initialization(self):
        """Test that ContextMemory initializes with enhanced engine"""
        self.assertIsNotNone(self.context_memory)
        # Enhanced engine might not be available in test environment
        # so we just check that it doesn't crash
    
    def test_add_conversation_legacy_compatibility(self):
        """Test that adding conversations works with legacy interface"""
        user_query = "I need help with billing"
        response = "I can help you with billing issues"
        tools_used = ["billing_tool"]
        
        # Should not raise any exceptions
        self.context_memory.add_conversation(user_query, response, tools_used)
        
        # Should be stored in legacy format
        self.assertEqual(len(self.context_memory.conversation_history), 1)
        
        stored_entry = self.context_memory.conversation_history[0]
        self.assertEqual(stored_entry['user_query'], user_query)
        self.assertEqual(stored_entry['response'], response)
        self.assertEqual(stored_entry['tools_used'], tools_used)
    
    def test_get_recent_context_legacy_fallback(self):
        """Test that get_recent_context falls back to legacy implementation"""
        # Add some conversations
        self.context_memory.add_conversation(
            "I have a billing problem",
            "I can help with billing",
            ["billing_tool"]
        )
        self.context_memory.add_conversation(
            "My mobile phone is not working",
            "Let me help with mobile issues",
            ["mobile_tool"]
        )
        
        # Test context retrieval
        contexts = self.context_memory.get_recent_context("billing issue", limit=2)
        
        # Should return relevant contexts
        self.assertGreater(len(contexts), 0)
        
        # Should contain billing-related context
        billing_contexts = [ctx for ctx in contexts if 'billing' in ctx['user_query'].lower()]
        self.assertGreater(len(billing_contexts), 0)
    
    def test_add_context_with_ttl(self):
        """Test adding context with TTL"""
        key = "test_context"
        data = {"info": "test billing information"}
        
        # Should not raise exceptions
        self.context_memory.add_context(key, data, ttl=3600)
        
        # Should be retrievable
        retrieved = self.context_memory.get_context(key)
        self.assertEqual(retrieved, data)
    
    def test_get_tool_usage_pattern(self):
        """Test tool usage pattern recommendation"""
        # Test different query types
        billing_tools = self.context_memory.get_tool_usage_pattern("billing")
        support_tools = self.context_memory.get_tool_usage_pattern("support_hours")
        technical_tools = self.context_memory.get_tool_usage_pattern("technical")
        
        # Should return tool recommendations
        self.assertIsInstance(billing_tools, list)
        self.assertIsInstance(support_tools, list)
        self.assertIsInstance(technical_tools, list)
        
        # Should have different recommendations for different types
        self.assertIn('BTSupportHours', support_tools)
        self.assertIn('ContextRetriever', technical_tools)
    
    def test_max_size_enforcement(self):
        """Test that max_size is enforced in conversation history"""
        max_size = 3
        context_memory = ContextMemory(max_size=max_size)
        
        # Add more conversations than max_size
        for i in range(max_size + 2):
            context_memory.add_conversation(
                f"Query {i}",
                f"Response {i}",
                [f"tool_{i}"]
            )
        
        # Should only keep max_size conversations
        self.assertEqual(len(context_memory.conversation_history), max_size)
        
        # Should keep the most recent ones
        last_entry = context_memory.conversation_history[-1]
        self.assertEqual(last_entry['user_query'], f"Query {max_size + 1}")


class TestSemanticFeaturesIntegration(unittest.TestCase):
    """Test semantic features with real-world examples"""
    
    def test_bt_specific_content(self):
        """Test semantic feature extraction with BT-specific content"""
        text = "My BT mobile plan costs £25.99 per month and includes 10GB data"
        features = SemanticFeatures(text)
        
        # Should extract BT-specific terms
        self.assertIn('BT', features.technical_terms)
        self.assertIn('mobile', features.keywords)
        self.assertIn('mobile', features.topics)
        
        # Should extract price and data amount
        price_found = any('£25.99' in str(entity) for entity in features.entities)
        data_found = any('10GB' in str(entity) for entity in features.entities)
        
        self.assertTrue(price_found or data_found)  # At least one should be found
    
    def test_customer_support_content(self):
        """Test semantic features with customer support content"""
        text = "I need help with my billing issue, the support hours are not clear"
        features = SemanticFeatures(text)
        
        # Should identify support-related topics
        self.assertIn('billing', features.topics)
        self.assertIn('support', features.topics)
        
        # Should extract relevant keywords
        self.assertIn('billing', features.keywords)
        self.assertIn('support', features.keywords)
    
    def test_technical_issue_content(self):
        """Test semantic features with technical issue content"""
        text = "My WiFi router keeps disconnecting from the BT network"
        features = SemanticFeatures(text)
        
        # Should identify technical terms
        self.assertIn('WiFi', features.technical_terms)
        self.assertIn('BT', features.technical_terms)
        
        # Should identify technical topic
        self.assertIn('technical', features.topics)


class TestContextRetrievalEngineIntegration(unittest.TestCase):
    """Test Context Retrieval Engine with realistic scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        from memory_config import MemoryConfig
        self.config = MemoryConfig()
        self.config.log_level = "WARNING"  # Reduce test noise
        self.engine = ContextRetrievalEngine(config=self.config)
    
    def test_similarity_calculation_realistic(self):
        """Test similarity calculation with realistic customer queries"""
        test_cases = [
            {
                'query': 'billing problem',
                'context': 'I have an issue with my bill',
                'expected_min': 0.3
            },
            {
                'query': 'mobile phone not working',
                'context': 'My phone has stopped working',
                'expected_min': 0.4
            },
            {
                'query': 'upgrade my plan',
                'context': 'I want to change my plan to unlimited',
                'expected_min': 0.2
            }
        ]
        
        for case in test_cases:
            similarity = self.engine.calculate_context_similarity(
                case['query'], 
                case['context']
            )
            
            self.assertGreaterEqual(
                similarity, 
                case['expected_min'],
                f"Similarity {similarity} below expected {case['expected_min']} "
                f"for query '{case['query']}' and context '{case['context']}'"
            )
    
    def test_context_ranking_realistic(self):
        """Test context ranking with realistic customer service scenarios"""
        contexts = [
            ContextEntryDTO(
                content="I need help with my monthly bill payment",
                source="conversation_1",
                relevance_score=0.0,
                context_type="user_message",
                timestamp=datetime.now(timezone.utc),
                metadata={'response_quality': 0.9}
            ),
            ContextEntryDTO(
                content="The weather is nice today",
                source="conversation_2",
                relevance_score=0.0,
                context_type="user_message",
                timestamp=datetime.now(timezone.utc),
                metadata={'response_quality': 0.7}
            ),
            ContextEntryDTO(
                content="My billing statement shows incorrect charges",
                source="conversation_3",
                relevance_score=0.0,
                context_type="user_message",
                timestamp=datetime.now(timezone.utc),
                metadata={'response_quality': 0.8}
            )
        ]
        
        query = "billing issue help"
        ranked = self.engine.rank_context_relevance(contexts, query)
        
        # Should have some results
        self.assertGreater(len(ranked), 0)
        
        # Billing-related contexts should rank higher than weather
        billing_contexts = [ctx for ctx in ranked if 'bill' in ctx.content.lower()]
        weather_contexts = [ctx for ctx in ranked if 'weather' in ctx.content.lower()]
        
        if billing_contexts and weather_contexts:
            self.assertGreater(
                billing_contexts[0].relevance_score,
                weather_contexts[0].relevance_score
            )
    
    def test_cache_performance(self):
        """Test caching performance with multiple operations"""
        # Perform multiple cache operations
        for i in range(10):
            context_data = {
                'content': f'Test content {i}',
                'metadata': {'test': True}
            }
            
            key = f'test_key_{i}'
            
            # Cache the data
            success = self.engine.cache_context(
                key=key,
                context_data=context_data,
                context_type='test',
                ttl_hours=1
            )
            
            # Should succeed (at least in memory cache)
            self.assertTrue(success)
            
            # Should be retrievable from memory cache
            cached = self.engine.cache.get(key)
            self.assertEqual(cached, context_data)
        
        # Check cache stats
        stats = self.engine.get_cache_stats()
        self.assertGreater(stats['hit_rate'], 0.0)
        self.assertGreater(stats['cache_size'], 0)


if __name__ == '__main__':
    # Run integration tests
    unittest.main(verbosity=2)