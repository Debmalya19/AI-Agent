"""
Unit tests for the Context Retrieval Engine.
Tests semantic similarity calculation, context ranking, caching mechanisms,
and database integration functionality.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import tempfile
import os

from context_retrieval_engine import (
    ContextRetrievalEngine,
    SemanticFeatures,
    MemoryCache
)
from memory_models import (
    ContextEntryDTO,
    EnhancedChatHistory,
    MemoryContextCache
)
from memory_config import MemoryConfig


class TestSemanticFeatures(unittest.TestCase):
    """Test semantic feature extraction"""
    
    def test_keyword_extraction(self):
        """Test keyword extraction from text"""
        text = "I need help with my mobile phone billing issue"
        features = SemanticFeatures(text)
        
        self.assertIn('mobile', features.keywords)
        self.assertIn('phone', features.keywords)
        self.assertIn('billing', features.keywords)
        self.assertNotIn('the', features.keywords)  # Stop word should be filtered
    
    def test_topic_extraction(self):
        """Test topic extraction from text"""
        text = "I have a billing problem with my mobile plan"
        features = SemanticFeatures(text)
        
        self.assertIn('billing', features.topics)
        self.assertIn('mobile', features.topics)
        self.assertIn('plans', features.topics)
    
    def test_entity_extraction(self):
        """Test entity extraction from text"""
        text = "My plan costs £25.99 and includes 10GB data"
        features = SemanticFeatures(text)
        
        # Should extract price and data amount
        self.assertTrue(any('£25.99' in str(entity) for entity in features.entities))
        self.assertTrue(any('10GB' in str(entity) for entity in features.entities))
    
    def test_sentiment_indicators(self):
        """Test sentiment indicator extraction"""
        positive_text = "This is great and amazing service"
        negative_text = "This is terrible and awful service"
        
        positive_features = SemanticFeatures(positive_text)
        negative_features = SemanticFeatures(negative_text)
        
        self.assertGreater(positive_features.sentiment_indicators['positive'], 0)
        self.assertGreater(negative_features.sentiment_indicators['negative'], 0)
    
    def test_technical_terms(self):
        """Test technical term extraction"""
        text = "My WiFi router has SIM card issues with BT network"
        features = SemanticFeatures(text)
        
        self.assertIn('WiFi', features.technical_terms)
        self.assertIn('SIM', features.technical_terms)
        self.assertIn('BT', features.technical_terms)
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        text = "Test text for conversion"
        features = SemanticFeatures(text)
        feature_dict = features.to_dict()
        
        self.assertIsInstance(feature_dict, dict)
        self.assertIn('keywords', feature_dict)
        self.assertIn('topics', feature_dict)
        self.assertIn('entities', feature_dict)
        self.assertIn('sentiment_indicators', feature_dict)


class TestMemoryCache(unittest.TestCase):
    """Test memory cache functionality"""
    
    def setUp(self):
        """Set up test cache"""
        self.cache = MemoryCache(max_size=3, ttl_seconds=60)
    
    def test_put_and_get(self):
        """Test basic put and get operations"""
        test_data = {"key": "value"}
        self.cache.put("test_key", test_data)
        
        retrieved = self.cache.get("test_key")
        self.assertEqual(retrieved, test_data)
    
    def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = MemoryCache(max_size=10, ttl_seconds=0)  # Immediate expiration
        cache.put("test_key", "test_value")
        
        # Should be expired immediately
        retrieved = cache.get("test_key")
        self.assertIsNone(retrieved)
    
    def test_max_size_eviction(self):
        """Test eviction when max size is reached"""
        # Fill cache to capacity
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")
        self.cache.put("key3", "value3")
        
        # Add one more - should evict oldest
        self.cache.put("key4", "value4")
        
        # key1 should be evicted
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNotNone(self.cache.get("key4"))
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation"""
        self.cache.put("key1", "value1")
        
        # One hit
        self.cache.get("key1")
        # One miss
        self.cache.get("nonexistent")
        
        hit_rate = self.cache.get_hit_rate()
        self.assertEqual(hit_rate, 0.5)  # 1 hit out of 2 attempts
    
    def test_clear(self):
        """Test cache clearing"""
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")
        
        self.cache.clear()
        
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))
        self.assertEqual(self.cache.get_hit_rate(), 0.0)


class TestContextRetrievalEngine(unittest.TestCase):
    """Test context retrieval engine functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_session = Mock()
        
        # Create proper mock config with nested structure
        self.mock_config = Mock(spec=MemoryConfig)
        self.mock_config.log_level = "INFO"
        self.mock_config.log_memory_operations = False
        self.mock_config.enable_database_storage = True
        
        # Mock nested performance config
        mock_performance = Mock()
        mock_performance.max_context_entries = 10
        self.mock_config.performance = mock_performance
        
        # Mock nested retention config
        mock_retention = Mock()
        mock_retention.conversation_retention_days = 30
        self.mock_config.retention = mock_retention
        
        # Mock nested quality config
        mock_quality = Mock()
        mock_quality.min_relevance_score = 0.1
        self.mock_config.quality = mock_quality
        
        self.engine = ContextRetrievalEngine(
            db_session=self.mock_session,
            config=self.mock_config
        )
    
    def test_initialization(self):
        """Test engine initialization"""
        self.assertIsNotNone(self.engine.cache)
        # legacy_memory is initialized lazily, so it starts as None
        self.assertIsNone(self.engine.legacy_memory)
        self.assertEqual(self.engine.db_session, self.mock_session)
    
    def test_extract_semantic_features(self):
        """Test semantic feature extraction"""
        text = "I need help with billing"
        features = self.engine.extract_semantic_features(text)
        
        self.assertIsInstance(features, SemanticFeatures)
        self.assertIn('billing', features.keywords)
        self.assertIn('billing', features.topics)
    
    def test_calculate_context_similarity_basic(self):
        """Test basic context similarity calculation"""
        query = "mobile phone billing"
        context = "I have a billing issue with my mobile phone"
        
        similarity = self.engine.calculate_context_similarity(query, context)
        
        self.assertGreater(similarity, 0.0)
        self.assertLessEqual(similarity, 1.0)
    
    def test_calculate_context_similarity_identical(self):
        """Test similarity calculation with identical text"""
        text = "mobile phone billing issue"
        
        similarity = self.engine.calculate_context_similarity(text, text)
        
        self.assertGreaterEqual(similarity, 0.8)  # Should be very high
    
    def test_calculate_context_similarity_unrelated(self):
        """Test similarity calculation with unrelated text"""
        query = "mobile phone billing"
        context = "weather forecast sunny day"
        
        similarity = self.engine.calculate_context_similarity(query, context)
        
        self.assertLess(similarity, 0.2)  # Should be very low
    
    def test_calculate_context_similarity_empty(self):
        """Test similarity calculation with empty strings"""
        similarity1 = self.engine.calculate_context_similarity("", "test")
        similarity2 = self.engine.calculate_context_similarity("test", "")
        similarity3 = self.engine.calculate_context_similarity("", "")
        
        self.assertEqual(similarity1, 0.0)
        self.assertEqual(similarity2, 0.0)
        self.assertEqual(similarity3, 0.0)
    
    def test_rank_context_relevance(self):
        """Test context relevance ranking"""
        contexts = [
            ContextEntryDTO(
                content="mobile phone billing issue",
                source="test1",
                relevance_score=0.0,  # Will be recalculated
                context_type="test",
                timestamp=datetime.now(timezone.utc)
            ),
            ContextEntryDTO(
                content="weather forecast",
                source="test2",
                relevance_score=0.0,  # Will be recalculated
                context_type="test",
                timestamp=datetime.now(timezone.utc)
            ),
            ContextEntryDTO(
                content="billing problem with mobile",
                source="test3",
                relevance_score=0.0,  # Will be recalculated
                context_type="test",
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        query = "mobile billing"
        ranked = self.engine.rank_context_relevance(contexts, query)
        
        # Should be sorted by relevance (highest first)
        self.assertGreater(len(ranked), 0)
        if len(ranked) > 1:
            self.assertGreaterEqual(ranked[0].relevance_score, ranked[1].relevance_score)
        if len(ranked) > 2:
            self.assertGreaterEqual(ranked[1].relevance_score, ranked[2].relevance_score)
        
        # Mobile billing related contexts should rank higher than weather
        mobile_contexts = [ctx for ctx in ranked if 'mobile' in ctx.content.lower()]
        weather_contexts = [ctx for ctx in ranked if 'weather' in ctx.content.lower()]
        
        if mobile_contexts and weather_contexts:
            self.assertGreater(mobile_contexts[0].relevance_score, weather_contexts[0].relevance_score)
    
    def test_rank_context_relevance_with_boosting(self):
        """Test context ranking with relevance boosting"""
        recent_time = datetime.now(timezone.utc)
        old_time = datetime.now(timezone.utc) - timedelta(days=7)
        
        contexts = [
            ContextEntryDTO(
                content="mobile billing issue",
                source="old",
                relevance_score=0.0,
                context_type="test",
                timestamp=old_time,
                metadata={'response_quality': 0.5}
            ),
            ContextEntryDTO(
                content="mobile billing issue",
                source="recent",
                relevance_score=0.0,
                context_type="test",
                timestamp=recent_time,
                metadata={'response_quality': 0.9, 'tools_used': ['tool1']}
            )
        ]
        
        query = "mobile billing"
        ranked = self.engine.rank_context_relevance(contexts, query)
        
        # Recent, high-quality context with tools should rank higher
        recent_context = next(ctx for ctx in ranked if ctx.source == "recent")
        old_context = next(ctx for ctx in ranked if ctx.source == "old")
        
        self.assertGreater(recent_context.relevance_score, old_context.relevance_score)
    
    def test_cache_context(self):
        """Test context caching functionality"""
        context_data = {"content": "test content", "type": "test"}
        
        # Mock database operations
        self.mock_session.add = Mock()
        self.mock_session.commit = Mock()
        
        result = self.engine.cache_context(
            key="test_key",
            context_data=context_data,
            context_type="test",
            ttl_hours=24,
            user_id="user123",
            relevance_score=0.8
        )
        
        self.assertTrue(result)
        
        # Should be cached in memory
        cached = self.engine.cache.get("test_key")
        self.assertEqual(cached, context_data)
        
        # Should attempt database storage
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
    
    def test_get_cache_stats(self):
        """Test cache statistics retrieval"""
        # Add some cache operations
        self.engine.cache.put("key1", "value1")
        self.engine.cache.get("key1")  # Hit
        self.engine.cache.get("nonexistent")  # Miss
        
        stats = self.engine.get_cache_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('hit_rate', stats)
        self.assertIn('cache_size', stats)
        self.assertIn('max_size', stats)
        self.assertIn('operation_times', stats)
        
        self.assertEqual(stats['hit_rate'], 0.5)  # 1 hit out of 2 attempts
        self.assertEqual(stats['cache_size'], 1)  # One item cached
    
    def test_clear_cache(self):
        """Test cache clearing"""
        self.engine.cache.put("key1", "value1")
        self.engine.clear_cache()
        
        self.assertIsNone(self.engine.cache.get("key1"))
    
    @patch('context_retrieval_engine.SessionLocal')
    def test_get_relevant_context_with_database(self, mock_session_factory):
        """Test getting relevant context from database"""
        # Setup mock database session
        mock_session = Mock()
        mock_session_factory.return_value = mock_session
        
        # Create engine without pre-configured session
        engine = ContextRetrievalEngine(config=self.mock_config)
        
        # Mock database query results
        mock_conversation = Mock(spec=EnhancedChatHistory)
        mock_conversation.id = 1
        mock_conversation.user_message = "I have a billing issue"
        mock_conversation.bot_response = "I can help with billing"
        mock_conversation.session_id = "session123"
        mock_conversation.tools_used = ["billing_tool"]
        mock_conversation.response_quality_score = 0.8
        mock_conversation.created_at = datetime.now(timezone.utc)
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_conversation]
        
        mock_session.query.return_value = mock_query
        
        # Mock cached context query
        mock_cache_query = Mock()
        mock_cache_query.filter.return_value = mock_cache_query
        mock_cache_query.order_by.return_value = mock_cache_query
        mock_cache_query.limit.return_value = mock_cache_query
        mock_cache_query.all.return_value = []
        
        # Setup query method to return different mocks for different models
        def query_side_effect(model):
            if model == EnhancedChatHistory:
                return mock_query
            elif model == MemoryContextCache:
                return mock_cache_query
            return Mock()
        
        mock_session.query.side_effect = query_side_effect
        
        # Test context retrieval
        contexts = engine.get_relevant_context("billing issue", "user123", limit=5)
        
        # Should return contexts from database
        self.assertGreater(len(contexts), 0)
        
        # Check that contexts contain expected data
        billing_contexts = [ctx for ctx in contexts if 'billing' in ctx.content.lower()]
        self.assertGreater(len(billing_contexts), 0)
        
        # Verify database was queried
        mock_session.query.assert_called()
        mock_session.close.assert_called()
    
    def test_generate_cache_key(self):
        """Test cache key generation"""
        key1 = self.engine._generate_cache_key("query", "user1", ["type1"], 10)
        key2 = self.engine._generate_cache_key("query", "user1", ["type1"], 10)
        key3 = self.engine._generate_cache_key("different", "user1", ["type1"], 10)
        
        # Same parameters should generate same key
        self.assertEqual(key1, key2)
        
        # Different parameters should generate different key
        self.assertNotEqual(key1, key3)
        
        # Key should be a string starting with "context_"
        self.assertIsInstance(key1, str)
        self.assertTrue(key1.startswith("context_"))


class TestContextRetrievalEngineIntegration(unittest.TestCase):
    """Integration tests for context retrieval engine"""
    
    def setUp(self):
        """Set up integration test environment"""
        # Create a real config for integration testing
        self.config = MemoryConfig()
        self.config.log_level = "WARNING"  # Reduce log noise in tests
        
        # Create engine with real cache but mock database
        self.engine = ContextRetrievalEngine(config=self.config)
    
    def test_end_to_end_context_retrieval(self):
        """Test end-to-end context retrieval workflow"""
        # Test retrieval without legacy memory (since it's not initialized)
        contexts = self.engine.get_relevant_context("billing issue", "user123", limit=5)
        
        # Should return empty list since no data is available
        self.assertIsInstance(contexts, list)
        
        # Test that the method doesn't crash
        self.assertGreaterEqual(len(contexts), 0)
    
    def test_caching_workflow(self):
        """Test complete caching workflow"""
        # Cache some context
        context_data = {
            "content": "Test billing information",
            "metadata": {"source": "test"}
        }
        
        # Use unique key to avoid conflicts
        import time
        unique_key = f"test_billing_{int(time.time() * 1000)}"
        
        # Cache context (will use memory cache since no DB session)
        success = self.engine.cache_context(
            key=unique_key,
            context_data=context_data,
            context_type="billing",
            ttl_hours=1
        )
        
        self.assertTrue(success)
        
        # Retrieve from cache
        cached = self.engine.cache.get(unique_key)
        self.assertEqual(cached, context_data)
        
        # Check cache stats
        stats = self.engine.get_cache_stats()
        self.assertGreater(stats['hit_rate'], 0.0)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)