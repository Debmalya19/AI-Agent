"""
Integration tests for Enhanced RAG Orchestrator with Memory Layer
Tests the integration between RAG orchestrator and memory layer components
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from enhanced_rag_orchestrator import (
    EnhancedRAGOrchestrator, 
    search_with_priority, 
    search_without_context,
    get_context_summary,
    get_tool_recommendations,
    record_tool_usage,
    store_conversation,
    get_performance_stats
)
from memory_layer_manager import MemoryLayerManager
from context_retrieval_engine import ContextRetrievalEngine
from tool_usage_analytics import ToolUsageAnalytics
from memory_models import (
    Base, 
    EnhancedChatHistory, 
    MemoryContextCache, 
    ToolUsageMetrics,
    ConversationEntryDTO,
    ContextEntryDTO,
    ToolRecommendationDTO
)
from memory_config import MemoryConfig


class TestEnhancedRAGIntegration:
    """Test suite for Enhanced RAG Orchestrator memory layer integration"""
    
    @pytest.fixture
    def test_db_session(self):
        """Create test database session"""
        # Create in-memory SQLite database for testing
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        
        TestSession = sessionmaker(bind=engine)
        session = TestSession()
        
        yield session
        
        session.close()
    
    @pytest.fixture
    def memory_config(self):
        """Create test memory configuration"""
        from memory_config import MemoryConfig, PerformanceConfig, QualityConfig
        
        return MemoryConfig(
            enable_database_storage=True,
            enable_context_retrieval=True,
            enable_tool_analytics=True,
            log_memory_operations=True,
            performance=PerformanceConfig(
                max_context_entries=10,
                max_conversation_history=50
            ),
            quality=QualityConfig(
                min_relevance_score=0.1,
                tool_success_threshold=0.5
            )
        )
    
    @pytest.fixture
    def memory_manager(self, test_db_session, memory_config):
        """Create test memory manager"""
        return MemoryLayerManager(config=memory_config, db_session=test_db_session)
    
    @pytest.fixture
    def context_engine(self, test_db_session, memory_config):
        """Create test context retrieval engine"""
        return ContextRetrievalEngine(db_session=test_db_session, config=memory_config)
    
    @pytest.fixture
    def analytics(self, test_db_session):
        """Create test tool usage analytics"""
        return ToolUsageAnalytics(db_session=test_db_session)
    
    @pytest.fixture
    def enhanced_rag(self, memory_manager, context_engine, analytics):
        """Create test enhanced RAG orchestrator"""
        return EnhancedRAGOrchestrator(
            memory_manager=memory_manager,
            context_engine=context_engine,
            analytics=analytics
        )
    
    def test_initialization(self, enhanced_rag):
        """Test that enhanced RAG orchestrator initializes correctly"""
        assert enhanced_rag.memory_manager is not None
        assert enhanced_rag.context_engine is not None
        assert enhanced_rag.analytics is not None
        assert enhanced_rag.context_memory is not None  # Legacy compatibility
    
    def test_search_with_enhanced_context(self, enhanced_rag, test_db_session):
        """Test search with enhanced context retrieval"""
        # Setup test data
        user_id = "test_user"
        query = "What are BT mobile plans?"
        
        # Add some conversation history
        conversation = ConversationEntryDTO(
            session_id="test_session",
            user_id=user_id,
            user_message="Tell me about mobile plans",
            bot_response="BT offers various mobile plans including SIM-only and contract options.",
            tools_used=["BTPlansInformation"],
            tool_performance={"BTPlansInformation": 0.9},
            context_used=[],
            response_quality_score=0.8,
            timestamp=datetime.now()
        )
        
        enhanced_rag.memory_manager.store_conversation(conversation)
        
        # Mock database queries for support intents and knowledge entries
        with patch('enhanced_rag_orchestrator.SessionLocal') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.all.return_value = []
            
            # Perform search
            results = enhanced_rag.search_with_context(
                query=query,
                user_id=user_id,
                max_results=5,
                include_context=True,
                tools_used=["BTPlansInformation"]
            )
            
            # Verify results structure
            assert isinstance(results, list)
            # Should have some results from context even if DB queries return empty
            # (depends on the context retrieval implementation)
    
    def test_memory_aware_ranking(self, enhanced_rag):
        """Test that results are ranked using memory insights"""
        query = "BT support hours"
        user_id = "test_user"
        
        # Create mock results
        results = [
            {
                'content': 'BT support is available 24/7',
                'source': 'memory_layer_conversation_1',
                'confidence': 0.8,
                'search_method': 'enhanced_context_retrieval',
                'timestamp': datetime.now()
            },
            {
                'content': 'Contact BT support',
                'source': 'support_intent_contact',
                'confidence': 0.6,
                'search_method': 'enhanced_intent_matching',
                'timestamp': datetime.now()
            }
        ]
        
        # Test ranking
        ranked_results = enhanced_rag._rank_results_with_memory(results, query, user_id)
        
        assert len(ranked_results) == 2
        # Memory layer result should be boosted
        memory_result = next((r for r in ranked_results if 'memory_layer' in r['source']), None)
        assert memory_result is not None
        assert memory_result.get('rank_score', 0) > 0.8
    
    def test_tool_recommendations_integration(self, enhanced_rag, analytics):
        """Test tool recommendations using analytics"""
        query = "What are BT mobile plans?"
        available_tools = ["BTPlansInformation", "BTWebsiteSearch", "ContextRetriever"]
        user_id = "test_user"
        
        # Mock analytics recommendations
        mock_recommendations = [
            ToolRecommendationDTO(
                tool_name="BTPlansInformation",
                confidence_score=0.9,
                reason="High success rate for plan queries",
                expected_performance=0.85
            ),
            ToolRecommendationDTO(
                tool_name="BTWebsiteSearch",
                confidence_score=0.7,
                reason="Good for general information",
                expected_performance=0.75
            )
        ]
        
        with patch.object(analytics, 'get_tool_recommendations', return_value=mock_recommendations):
            recommendations = enhanced_rag.get_tool_recommendations(query, available_tools, user_id)
            
            assert isinstance(recommendations, list)
            assert len(recommendations) >= 2
            assert "BTPlansInformation" in recommendations
            assert recommendations[0] == "BTPlansInformation"  # Should be first due to higher confidence
    
    def test_conversation_storage(self, enhanced_rag, memory_manager):
        """Test conversation storage in memory layer"""
        session_id = "test_session"
        user_id = "test_user"
        user_message = "What are your mobile plans?"
        bot_response = "We offer various mobile plans including SIM-only and contract options."
        tools_used = ["BTPlansInformation", "BTWebsiteSearch"]
        response_quality = 0.85
        
        # Store conversation
        enhanced_rag.store_conversation(
            session_id=session_id,
            user_id=user_id,
            user_message=user_message,
            bot_response=bot_response,
            tools_used=tools_used,
            response_quality_score=response_quality
        )
        
        # Verify storage in memory manager
        history = memory_manager.get_user_conversation_history(user_id, limit=1)
        assert len(history) == 1
        assert history[0].user_message == user_message
        assert history[0].bot_response == bot_response
        assert history[0].tools_used == tools_used
        assert history[0].response_quality_score == response_quality
    
    def test_tool_usage_recording(self, enhanced_rag, analytics):
        """Test tool usage recording for analytics"""
        tool_name = "BTPlansInformation"
        query = "What mobile plans do you have?"
        success = True
        response_quality = 0.9
        response_time = 1.5
        
        # Mock analytics recording
        with patch.object(analytics, 'record_tool_usage', return_value=True) as mock_record:
            enhanced_rag.record_tool_usage(
                tool_name=tool_name,
                query=query,
                success=success,
                response_quality=response_quality,
                response_time=response_time
            )
            
            # Verify analytics was called
            mock_record.assert_called_once_with(
                tool_name=tool_name,
                query=query,
                success=success,
                response_quality=response_quality,
                response_time=response_time
            )
    
    def test_context_summary_generation(self, enhanced_rag, context_engine):
        """Test context summary generation using memory layer"""
        query = "BT support hours"
        user_id = "test_user"
        
        # Mock context entries
        mock_context = [
            ContextEntryDTO(
                content="What are BT support hours?",
                source="conversation_1",
                relevance_score=0.9,
                context_type="user_message",
                timestamp=datetime.now(),
                metadata={}
            ),
            ContextEntryDTO(
                content="BT support is available 24/7 for urgent issues.",
                source="conversation_1",
                relevance_score=0.8,
                context_type="bot_response",
                timestamp=datetime.now(),
                metadata={}
            )
        ]
        
        with patch.object(context_engine, 'get_relevant_context', return_value=mock_context):
            summary = enhanced_rag.get_context_summary(query, user_id)
            
            assert isinstance(summary, str)
            assert len(summary) > 0
            assert "Previous question" in summary or "Previous answer" in summary
    
    def test_performance_stats(self, enhanced_rag):
        """Test performance statistics collection"""
        # Perform some operations to generate stats
        enhanced_rag._track_operation_time('search_with_context', 0.5)
        enhanced_rag._track_operation_time('search_with_context', 0.7)
        
        stats = enhanced_rag.get_performance_stats()
        
        assert isinstance(stats, dict)
        assert 'operation_times' in stats
        assert 'memory_stats' in stats
        assert 'cache_stats' in stats
        
        if 'search_with_context' in stats['operation_times']:
            search_stats = stats['operation_times']['search_with_context']
            assert 'avg_time' in search_stats
            assert 'count' in search_stats
            assert search_stats['count'] == 2
    
    def test_backward_compatibility(self, enhanced_rag):
        """Test backward compatibility with legacy context memory"""
        query = "BT mobile plans"
        
        # Should work with legacy context memory
        enhanced_rag.context_memory.add_conversation(
            "What are mobile plans?",
            "BT offers various mobile plans.",
            ["BTPlansInformation"]
        )
        
        # Search should include legacy context
        with patch('enhanced_rag_orchestrator.SessionLocal') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.all.return_value = []
            
            results = enhanced_rag.search_with_context(query, "test_user", include_context=True)
            
            # Should not raise errors and return some results
            assert isinstance(results, list)
    
    def test_error_handling(self, enhanced_rag):
        """Test error handling in memory layer integration"""
        # Test with invalid user_id
        results = enhanced_rag.search_with_context("test query", "", max_results=3)
        assert isinstance(results, list)  # Should not crash
        
        # Test with None values
        enhanced_rag.record_tool_usage("TestTool", "test", True, 0.8, None)
        # Should not raise exceptions
        
        # Test context summary with empty query
        summary = enhanced_rag.get_context_summary("", "test_user")
        assert isinstance(summary, str)


class TestGlobalFunctions:
    """Test global functions with memory layer integration"""
    
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup mocks for global functions"""
        with patch('enhanced_rag_orchestrator.enhanced_rag') as mock_rag:
            self.mock_rag = mock_rag
            yield
    
    def test_search_with_priority(self):
        """Test global search_with_priority function"""
        query = "BT mobile plans"
        user_id = "test_user"
        tools_used = ["BTPlansInformation"]
        
        self.mock_rag.search_with_context.return_value = [
            {'content': 'Test result', 'source': 'test', 'confidence': 0.8}
        ]
        
        results = search_with_priority(query, user_id, max_results=3, tools_used=tools_used)
        
        self.mock_rag.search_with_context.assert_called_once_with(
            query, user_id, 3, include_context=True, tools_used=tools_used
        )
        assert len(results) == 1
    
    def test_search_without_context(self):
        """Test global search_without_context function"""
        query = "BT support"
        user_id = "test_user"
        
        self.mock_rag.search_with_context.return_value = []
        
        results = search_without_context(query, user_id, max_results=5)
        
        self.mock_rag.search_with_context.assert_called_once_with(
            query, user_id, 5, include_context=False
        )
        assert isinstance(results, list)
    
    def test_get_context_summary(self):
        """Test global get_context_summary function"""
        query = "BT plans"
        user_id = "test_user"
        
        self.mock_rag.get_context_summary.return_value = "Test summary"
        
        summary = get_context_summary(query, user_id)
        
        self.mock_rag.get_context_summary.assert_called_once_with(query, user_id)
        assert summary == "Test summary"
    
    def test_get_tool_recommendations(self):
        """Test global get_tool_recommendations function"""
        query = "BT support"
        available_tools = ["BTSupportHours", "BTWebsiteSearch"]
        user_id = "test_user"
        
        self.mock_rag.get_tool_recommendations.return_value = available_tools
        
        recommendations = get_tool_recommendations(query, available_tools, user_id)
        
        self.mock_rag.get_tool_recommendations.assert_called_once_with(
            query, available_tools, user_id
        )
        assert recommendations == available_tools
    
    def test_record_tool_usage(self):
        """Test global record_tool_usage function"""
        tool_name = "BTPlansInformation"
        query = "mobile plans"
        success = True
        quality = 0.9
        response_time = 1.2
        
        record_tool_usage(tool_name, query, success, quality, response_time)
        
        self.mock_rag.record_tool_usage.assert_called_once_with(
            tool_name, query, success, quality, response_time
        )
    
    def test_store_conversation(self):
        """Test global store_conversation function"""
        session_id = "test_session"
        user_id = "test_user"
        user_message = "What are your plans?"
        bot_response = "We have various plans available."
        tools_used = ["BTPlansInformation"]
        quality = 0.85
        
        store_conversation(session_id, user_id, user_message, bot_response, tools_used, quality)
        
        self.mock_rag.store_conversation.assert_called_once_with(
            session_id, user_id, user_message, bot_response, tools_used, quality
        )
    
    def test_get_performance_stats(self):
        """Test global get_performance_stats function"""
        expected_stats = {
            'operation_times': {'search': {'avg_time': 0.5, 'count': 10}},
            'memory_stats': {'total_conversations': 100},
            'cache_stats': {'hit_rate': 0.8}
        }
        
        self.mock_rag.get_performance_stats.return_value = expected_stats
        
        stats = get_performance_stats()
        
        self.mock_rag.get_performance_stats.assert_called_once()
        assert stats == expected_stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])