"""
Unit tests for the Memory Layer Manager.
Tests core memory operations, configuration management, and error handling.
"""

import pytest
import tempfile
import os
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from memory_layer_manager import MemoryLayerManager, MemoryStats, CleanupResult
from memory_config import MemoryConfig, RetentionPolicy, PerformanceConfig
from memory_models import (
    ConversationEntryDTO,
    ContextEntryDTO,
    ToolRecommendationDTO,
    EnhancedChatHistory,
    MemoryContextCache,
    ToolUsageMetrics,
    Base
)


class TestMemoryConfig:
    """Test memory configuration functionality"""
    
    def test_default_config_creation(self):
        """Test creating default configuration"""
        config = MemoryConfig()
        
        assert config.retention.conversation_retention_days == 90
        assert config.performance.max_context_entries == 50
        assert config.security.encrypt_sensitive_data is True
        assert config.enable_database_storage is True
    
    def test_config_from_dict(self):
        """Test creating configuration from dictionary"""
        config_dict = {
            'retention': {
                'conversation_retention_days': 30,
                'context_cache_retention_hours': 12
            },
            'performance': {
                'max_context_entries': 25,
                'enable_caching': False
            },
            'enable_database_storage': False
        }
        
        config = MemoryConfig.from_dict(config_dict)
        
        assert config.retention.conversation_retention_days == 30
        assert config.retention.context_cache_retention_hours == 12
        assert config.performance.max_context_entries == 25
        assert config.performance.enable_caching is False
        assert config.enable_database_storage is False
    
    def test_config_validation(self):
        """Test configuration validation"""
        config = MemoryConfig()
        
        # Valid configuration should have no errors
        errors = config.validate()
        assert len(errors) == 0
        assert config.is_valid() is True
        
        # Invalid configuration should have errors
        config.retention.conversation_retention_days = -1
        config.quality.min_relevance_score = 1.5
        
        errors = config.validate()
        assert len(errors) > 0
        assert config.is_valid() is False
    
    def test_config_file_operations(self):
        """Test saving and loading configuration from file"""
        config = MemoryConfig()
        config.retention.conversation_retention_days = 60
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            # Save configuration
            assert config.save_to_file(temp_path) is True
            
            # Load configuration
            loaded_config = MemoryConfig.from_file(temp_path)
            assert loaded_config.retention.conversation_retention_days == 60
            
        finally:
            os.unlink(temp_path)


class TestMemoryLayerManager:
    """Test Memory Layer Manager functionality"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        session = Mock()
        session.query.return_value = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.close = Mock()
        return session
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration"""
        config = MemoryConfig()
        config.retention.conversation_retention_days = 30
        config.performance.max_context_entries = 10
        config.log_level = "DEBUG"
        return config
    
    @pytest.fixture
    def memory_manager(self, test_config, mock_db_session):
        """Create Memory Layer Manager with test configuration"""
        return MemoryLayerManager(config=test_config, db_session=mock_db_session)
    
    def test_manager_initialization(self, test_config):
        """Test Memory Layer Manager initialization"""
        manager = MemoryLayerManager(config=test_config)
        
        assert manager.config == test_config
        assert manager._error_count == 0
        assert manager._last_cleanup is None
    
    def test_store_conversation_success(self, memory_manager, mock_db_session):
        """Test successful conversation storage"""
        conversation = ConversationEntryDTO(
            session_id="test_session",
            user_id="test_user",
            user_message="Hello",
            bot_response="Hi there!",
            tools_used=["greeting_tool"],
            response_quality_score=0.9
        )
        
        result = memory_manager.store_conversation(conversation)
        
        assert result is True
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    def test_store_conversation_database_disabled(self, test_config, mock_db_session):
        """Test conversation storage when database is disabled"""
        test_config.enable_database_storage = False
        manager = MemoryLayerManager(config=test_config, db_session=mock_db_session)
        
        conversation = ConversationEntryDTO(
            session_id="test_session",
            user_id="test_user",
            user_message="Hello",
            bot_response="Hi there!"
        )
        
        result = manager.store_conversation(conversation)
        
        assert result is True
        mock_db_session.add.assert_not_called()
    
    def test_store_conversation_error_handling(self, memory_manager, mock_db_session):
        """Test conversation storage error handling"""
        mock_db_session.add.side_effect = Exception("Database error")
        
        conversation = ConversationEntryDTO(
            session_id="test_session",
            user_id="test_user",
            user_message="Hello",
            bot_response="Hi there!"
        )
        
        result = memory_manager.store_conversation(conversation)
        
        assert result is False
        assert memory_manager._error_count == 1
        mock_db_session.rollback.assert_called_once()
    
    def test_retrieve_context_success(self, memory_manager, mock_db_session):
        """Test successful context retrieval"""
        # Mock database query results
        mock_conversation = Mock()
        mock_conversation.id = 1
        mock_conversation.user_message = "What is Python?"
        mock_conversation.bot_response = "Python is a programming language"
        mock_conversation.session_id = "test_session"
        mock_conversation.tools_used = ["search_tool"]
        mock_conversation.response_quality_score = 0.8
        mock_conversation.created_at = datetime.now(timezone.utc)
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_conversation]
        
        mock_db_session.query.return_value = mock_query
        
        result = memory_manager.retrieve_context("Python programming", "test_user", limit=5)
        
        # Should return at least 1 entry (may filter out low relevance scores)
        assert len(result) >= 1
        assert all(isinstance(entry, ContextEntryDTO) for entry in result)
        assert any(entry.content in ["What is Python?", "Python is a programming language"] for entry in result)
    
    def test_retrieve_context_disabled(self, test_config, mock_db_session):
        """Test context retrieval when disabled"""
        test_config.enable_context_retrieval = False
        manager = MemoryLayerManager(config=test_config, db_session=mock_db_session)
        
        result = manager.retrieve_context("test query", "test_user")
        
        assert result == []
        mock_db_session.query.assert_not_called()
    
    def test_retrieve_context_error_handling(self, memory_manager, mock_db_session):
        """Test context retrieval error handling"""
        mock_db_session.query.side_effect = Exception("Database error")
        
        result = memory_manager.retrieve_context("test query", "test_user")
        
        assert result == []
        assert memory_manager._error_count == 1
    
    def test_calculate_relevance_score(self, memory_manager):
        """Test relevance score calculation"""
        # Test exact match
        score = memory_manager._calculate_relevance_score("hello world", "hello world")
        assert score == 1.0
        
        # Test partial match
        score = memory_manager._calculate_relevance_score("hello", "hello world")
        assert 0.0 < score < 1.0
        
        # Test no match
        score = memory_manager._calculate_relevance_score("hello", "goodbye")
        assert score == 0.0
        
        # Test empty strings
        score = memory_manager._calculate_relevance_score("", "hello")
        assert score == 0.0
    
    def test_analyze_tool_usage_success(self, memory_manager, mock_db_session):
        """Test successful tool usage analysis"""
        # Mock tool metrics query
        mock_metric = Mock()
        mock_metric.tool_name = "search_tool"
        mock_metric.success_rate = 0.9
        mock_metric.response_quality_score = 0.8
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_metric]
        
        mock_db_session.query.return_value = mock_query
        
        result = memory_manager.analyze_tool_usage("search query", ["search_tool"])
        
        assert result is not None
        assert isinstance(result, ToolRecommendationDTO)
        assert result.tool_name == "search_tool"
        assert result.confidence_score == 0.9
    
    def test_analyze_tool_usage_no_data(self, memory_manager, mock_db_session):
        """Test tool usage analysis with no historical data"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db_session.query.return_value = mock_query
        
        result = memory_manager.analyze_tool_usage("new query", ["new_tool"])
        
        assert result is None
    
    def test_analyze_tool_usage_disabled(self, test_config, mock_db_session):
        """Test tool usage analysis when disabled"""
        test_config.enable_tool_analytics = False
        manager = MemoryLayerManager(config=test_config, db_session=mock_db_session)
        
        result = manager.analyze_tool_usage("test query", ["test_tool"])
        
        assert result is None
        mock_db_session.query.assert_not_called()
    
    def test_cleanup_expired_data_success(self, memory_manager, mock_db_session):
        """Test successful data cleanup"""
        # Mock query results for cleanup with proper chaining
        mock_conversations_query = Mock()
        mock_conversations_query.filter.return_value = mock_conversations_query
        mock_conversations_query.count.return_value = 5
        mock_conversations_query.delete.return_value = None
        
        mock_cache_query = Mock()
        mock_cache_query.filter.return_value = mock_cache_query
        mock_cache_query.count.return_value = 3
        mock_cache_query.delete.return_value = None
        
        mock_metrics_query = Mock()
        mock_metrics_query.filter.return_value = mock_metrics_query
        mock_metrics_query.count.return_value = 2
        mock_metrics_query.delete.return_value = None
        
        def mock_query_side_effect(model):
            if model == EnhancedChatHistory:
                return mock_conversations_query
            elif model == MemoryContextCache:
                return mock_cache_query
            elif model == ToolUsageMetrics:
                return mock_metrics_query
            return Mock()
        
        mock_db_session.query.side_effect = mock_query_side_effect
        
        result = memory_manager.cleanup_expired_data()
        
        assert isinstance(result, CleanupResult)
        assert result.conversations_cleaned == 5
        assert result.context_entries_cleaned == 3
        assert result.tool_metrics_cleaned == 2
        assert len(result.errors) == 0
        mock_db_session.commit.assert_called_once()
    
    def test_cleanup_expired_data_error_handling(self, memory_manager, mock_db_session):
        """Test cleanup error handling"""
        mock_db_session.query.side_effect = Exception("Database error")
        
        result = memory_manager.cleanup_expired_data()
        
        assert isinstance(result, CleanupResult)
        assert len(result.errors) > 0
        assert memory_manager._error_count == 1
        mock_db_session.rollback.assert_called_once()
    
    def test_get_memory_stats_success(self, memory_manager, mock_db_session):
        """Test successful memory statistics retrieval"""
        # Mock count queries
        def mock_query_side_effect(model):
            mock_query = Mock()
            if model == EnhancedChatHistory:
                mock_query.count.return_value = 100
            elif model == MemoryContextCache:
                mock_query.count.return_value = 50
            elif model == ToolUsageMetrics:
                mock_query.count.return_value = 25
            return mock_query
        
        mock_db_session.query.side_effect = mock_query_side_effect
        
        result = memory_manager.get_memory_stats()
        
        assert isinstance(result, MemoryStats)
        assert result.total_conversations == 100
        assert result.total_context_entries == 50
        assert result.total_tool_usages == 25
        assert result.error_count == 0
    
    def test_get_memory_stats_error_handling(self, memory_manager, mock_db_session):
        """Test memory statistics error handling"""
        mock_db_session.query.side_effect = Exception("Database error")
        
        result = memory_manager.get_memory_stats()
        
        assert isinstance(result, MemoryStats)
        assert memory_manager._error_count == 1
    
    def test_record_health_metric_success(self, memory_manager, mock_db_session):
        """Test successful health metric recording"""
        result = memory_manager.record_health_metric(
            "response_time", 0.5, "seconds", "performance"
        )
        
        assert result is True
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    def test_record_health_metric_disabled(self, test_config, mock_db_session):
        """Test health metric recording when disabled"""
        test_config.enable_health_monitoring = False
        manager = MemoryLayerManager(config=test_config, db_session=mock_db_session)
        
        result = manager.record_health_metric("test_metric", 1.0)
        
        assert result is True
        mock_db_session.add.assert_not_called()
    
    def test_get_user_conversation_history_success(self, memory_manager, mock_db_session):
        """Test successful user conversation history retrieval"""
        # Mock conversation data
        mock_conversation = Mock()
        mock_conversation.session_id = "test_session"
        mock_conversation.user_id = "test_user"
        mock_conversation.user_message = "Hello"
        mock_conversation.bot_response = "Hi there!"
        mock_conversation.tools_used = ["greeting_tool"]
        mock_conversation.tool_performance = {"greeting_tool": 0.9}
        mock_conversation.context_used = []
        mock_conversation.response_quality_score = 0.8
        mock_conversation.created_at = datetime.now(timezone.utc)
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_conversation]
        
        mock_db_session.query.return_value = mock_query
        
        result = memory_manager.get_user_conversation_history("test_user", limit=10)
        
        assert len(result) == 1
        assert isinstance(result[0], ConversationEntryDTO)
        assert result[0].user_id == "test_user"
        assert result[0].user_message == "Hello"
    
    def test_get_user_conversation_history_error_handling(self, memory_manager, mock_db_session):
        """Test user conversation history error handling"""
        mock_db_session.query.side_effect = Exception("Database error")
        
        result = memory_manager.get_user_conversation_history("test_user")
        
        assert result == []
        assert memory_manager._error_count == 1
    
    def test_operation_time_tracking(self, memory_manager):
        """Test operation time tracking"""
        # Track some operation times
        memory_manager._track_operation_time("test_operation", 0.1)
        memory_manager._track_operation_time("test_operation", 0.2)
        memory_manager._track_operation_time("test_operation", 0.3)
        
        assert "test_operation" in memory_manager._operation_times
        assert len(memory_manager._operation_times["test_operation"]) == 3
        
        # Test that only last 100 measurements are kept
        for i in range(150):
            memory_manager._track_operation_time("test_operation", i * 0.001)
        
        assert len(memory_manager._operation_times["test_operation"]) == 100
    
    def test_error_logging(self, memory_manager):
        """Test error logging functionality"""
        initial_count = memory_manager._error_count
        
        test_error = Exception("Test error")
        memory_manager._log_error("test_operation", test_error)
        
        assert memory_manager._error_count == initial_count + 1


# Integration tests (require actual database)
class TestMemoryLayerManagerIntegration:
    """Integration tests for Memory Layer Manager with real database"""
    
    @pytest.fixture
    def test_db_engine(self):
        """Create test database engine"""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def test_db_session(self, test_db_engine):
        """Create test database session"""
        Session = sessionmaker(bind=test_db_engine)
        session = Session()
        yield session
        session.close()
    
    @pytest.fixture
    def integration_manager(self, test_db_session):
        """Create Memory Layer Manager with real database session"""
        config = MemoryConfig()
        config.log_level = "DEBUG"
        return MemoryLayerManager(config=config, db_session=test_db_session)
    
    def test_full_conversation_workflow(self, integration_manager):
        """Test complete conversation storage and retrieval workflow"""
        # Store a conversation
        conversation = ConversationEntryDTO(
            session_id="integration_test",
            user_id="test_user",
            user_message="What is machine learning?",
            bot_response="Machine learning is a subset of AI...",
            tools_used=["search_tool", "knowledge_tool"],
            tool_performance={"search_tool": 0.9, "knowledge_tool": 0.8},
            response_quality_score=0.85
        )
        
        # Store conversation
        result = integration_manager.store_conversation(conversation)
        assert result is True
        
        # Retrieve context
        context_entries = integration_manager.retrieve_context(
            "machine learning", "test_user", limit=5
        )
        
        assert len(context_entries) > 0
        assert any("machine learning" in entry.content.lower() for entry in context_entries)
        
        # Get conversation history
        history = integration_manager.get_user_conversation_history("test_user")
        assert len(history) == 1
        assert history[0].user_message == "What is machine learning?"
        
        # Get memory stats
        stats = integration_manager.get_memory_stats()
        assert stats.total_conversations >= 1
    
    def test_cleanup_workflow(self, integration_manager):
        """Test data cleanup workflow"""
        # Store some test data
        conversation = ConversationEntryDTO(
            session_id="cleanup_test",
            user_id="cleanup_user",
            user_message="Test message",
            bot_response="Test response"
        )
        
        integration_manager.store_conversation(conversation)
        
        # Perform cleanup (should not clean recent data)
        result = integration_manager.cleanup_expired_data()
        assert isinstance(result, CleanupResult)
        assert result.conversations_cleaned == 0  # Recent data should not be cleaned
        
        # Verify data still exists
        history = integration_manager.get_user_conversation_history("cleanup_user")
        assert len(history) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])