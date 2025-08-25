"""
Unit tests for ConversationHistoryStore class.
Tests cover all functionality including storage, retrieval, search, filtering,
archiving, and cleanup operations.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from conversation_history_store import (
    ConversationHistoryStore,
    ConversationFilter,
    ConversationStats
)
from memory_models import (
    EnhancedChatHistory,
    ConversationSummary,
    ConversationEntryDTO
)
from models import ChatHistory

class TestConversationHistoryStore:
    """Test suite for ConversationHistoryStore"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def conversation_store(self, mock_db_session):
        """Create ConversationHistoryStore instance with mock session"""
        return ConversationHistoryStore(mock_db_session)
    
    @pytest.fixture
    def sample_conversation_dto(self):
        """Create a sample ConversationEntryDTO for testing"""
        return ConversationEntryDTO(
            session_id="test_session_123",
            user_id="user_456",
            user_message="Hello, I need help with my account",
            bot_response="I'd be happy to help you with your account. What specific issue are you experiencing?",
            tools_used=["customer_db_tool", "support_knowledge_tool"],
            tool_performance={"customer_db_tool": 0.95, "support_knowledge_tool": 0.87},
            context_used=["previous_conversation", "user_profile"],
            response_quality_score=0.92,
            timestamp=datetime.now(timezone.utc)
        )
    
    @pytest.fixture
    def sample_enhanced_chat_history(self):
        """Create a sample EnhancedChatHistory database entry"""
        return EnhancedChatHistory(
            id=1,
            session_id="test_session_123",
            user_id="user_456",
            user_message="Hello, I need help with my account",
            bot_response="I'd be happy to help you with your account.",
            tools_used=["customer_db_tool"],
            tool_performance={"customer_db_tool": 0.95},
            context_used=["previous_conversation"],
            response_quality_score=0.92,
            created_at=datetime.now(timezone.utc)
        )

class TestSaveConversation(TestConversationHistoryStore):
    """Tests for save_conversation method"""
    
    def test_save_conversation_success(self, conversation_store, mock_db_session, sample_conversation_dto):
        """Test successful conversation saving"""
        # Setup
        mock_enhanced_entry = Mock()
        mock_enhanced_entry.id = 123
        
        with patch('conversation_history_store.create_enhanced_chat_entry', return_value=mock_enhanced_entry):
            with patch('conversation_history_store.ChatHistory') as mock_chat_history:
                # Execute
                result = conversation_store.save_conversation(sample_conversation_dto)
                
                # Verify
                assert result == "123"
                mock_db_session.add.assert_called()
                mock_db_session.commit.assert_called_once()
                assert mock_db_session.add.call_count == 2  # Enhanced + Legacy entries
    
    def test_save_conversation_database_error(self, conversation_store, mock_db_session, sample_conversation_dto):
        """Test handling of database errors during save"""
        # Setup
        mock_db_session.commit.side_effect = SQLAlchemyError("Database error")
        
        with patch('conversation_history_store.create_enhanced_chat_entry'):
            with patch('conversation_history_store.ChatHistory'):
                # Execute & Verify
                with pytest.raises(SQLAlchemyError):
                    conversation_store.save_conversation(sample_conversation_dto)
                
                mock_db_session.rollback.assert_called_once()
    
    def test_save_conversation_creates_both_entries(self, conversation_store, mock_db_session, sample_conversation_dto):
        """Test that both enhanced and legacy entries are created"""
        # Setup
        mock_enhanced_entry = Mock()
        mock_enhanced_entry.id = 123
        
        with patch('conversation_history_store.create_enhanced_chat_entry', return_value=mock_enhanced_entry) as mock_create_enhanced:
            with patch('conversation_history_store.ChatHistory') as mock_chat_history_class:
                mock_legacy_entry = Mock()
                mock_chat_history_class.return_value = mock_legacy_entry
                
                # Execute
                conversation_store.save_conversation(sample_conversation_dto)
                
                # Verify enhanced entry creation
                mock_create_enhanced.assert_called_once_with(
                    session_id=sample_conversation_dto.session_id,
                    user_id=sample_conversation_dto.user_id,
                    user_message=sample_conversation_dto.user_message,
                    bot_response=sample_conversation_dto.bot_response,
                    tools_used=sample_conversation_dto.tools_used,
                    tool_performance=sample_conversation_dto.tool_performance,
                    context_used=sample_conversation_dto.context_used,
                    response_quality_score=sample_conversation_dto.response_quality_score
                )
                
                # Verify legacy entry creation
                mock_chat_history_class.assert_called_once_with(
                    session_id=sample_conversation_dto.session_id,
                    user_message=sample_conversation_dto.user_message,
                    bot_response=sample_conversation_dto.bot_response,
                    tools_used=sample_conversation_dto.tools_used,
                    sources=sample_conversation_dto.context_used
                )

class TestGetUserHistory(TestConversationHistoryStore):
    """Tests for get_user_history method"""
    
    def test_get_user_history_success(self, conversation_store, mock_db_session, sample_enhanced_chat_history):
        """Test successful retrieval of user history"""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_enhanced_chat_history]
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = conversation_store.get_user_history("user_456", limit=10)
        
        # Verify
        assert len(result) == 1
        assert isinstance(result[0], ConversationEntryDTO)
        assert result[0].user_id == "user_456"
        assert result[0].session_id == "test_session_123"
        mock_db_session.query.assert_called_once_with(EnhancedChatHistory)
    
    def test_get_user_history_with_filters(self, conversation_store, mock_db_session):
        """Test user history retrieval with filters"""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query
        
        filters = ConversationFilter(
            session_id="specific_session",
            min_quality_score=0.8,
            limit=20,
            offset=10
        )
        
        with patch.object(conversation_store, '_apply_filters', return_value=mock_query) as mock_apply_filters:
            # Execute
            result = conversation_store.get_user_history("user_456", filters=filters)
            
            # Verify
            mock_apply_filters.assert_called_once_with(mock_query, filters)
    
    def test_get_user_history_database_error(self, conversation_store, mock_db_session):
        """Test handling of database errors during history retrieval"""
        # Setup
        mock_db_session.query.side_effect = SQLAlchemyError("Database error")
        
        # Execute
        result = conversation_store.get_user_history("user_456")
        
        # Verify
        assert result == []

class TestSearchConversations(TestConversationHistoryStore):
    """Tests for search_conversations method"""
    
    def test_search_conversations_success(self, conversation_store, mock_db_session, sample_enhanced_chat_history):
        """Test successful conversation search"""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_enhanced_chat_history]
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = conversation_store.search_conversations("help with account")
        
        # Verify
        assert len(result) == 1
        assert isinstance(result[0], ConversationEntryDTO)
        mock_db_session.query.assert_called_once_with(EnhancedChatHistory)
    
    def test_search_conversations_with_user_filter(self, conversation_store, mock_db_session):
        """Test conversation search with user ID filter"""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = conversation_store.search_conversations("test query", user_id="user_456")
        
        # Verify
        # Should have two filter calls: one for text search, one for user_id
        assert mock_query.filter.call_count >= 2
    
    def test_search_conversations_with_additional_filters(self, conversation_store, mock_db_session):
        """Test conversation search with additional filters"""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query
        
        filters = ConversationFilter(min_quality_score=0.8, limit=10)
        
        with patch.object(conversation_store, '_apply_filters', return_value=mock_query) as mock_apply_filters:
            # Execute
            result = conversation_store.search_conversations("test query", filters=filters)
            
            # Verify
            mock_apply_filters.assert_called_once_with(mock_query, filters)

class TestArchiveOldConversations(TestConversationHistoryStore):
    """Tests for archive_old_conversations method"""
    
    def test_archive_old_conversations_success(self, conversation_store, mock_db_session, sample_enhanced_chat_history):
        """Test successful archiving of old conversations"""
        # Setup
        old_conversation = sample_enhanced_chat_history
        old_conversation.created_at = datetime.now(timezone.utc) - timedelta(days=100)
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [old_conversation]
        mock_query.delete.return_value = 1
        mock_db_session.query.return_value = mock_query
        
        with patch.object(conversation_store, '_create_conversation_summary') as mock_create_summary:
            mock_summary = Mock()
            mock_create_summary.return_value = mock_summary
            
            # Execute
            result = conversation_store.archive_old_conversations(retention_days=90)
            
            # Verify
            assert result == 1
            mock_create_summary.assert_called_once_with(old_conversation)
            mock_db_session.add.assert_called_once_with(mock_summary)
            mock_db_session.commit.assert_called_once()
    
    def test_archive_old_conversations_no_conversations_to_archive(self, conversation_store, mock_db_session):
        """Test archiving when no old conversations exist"""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = conversation_store.archive_old_conversations(retention_days=90)
        
        # Verify
        assert result == 0
        mock_db_session.commit.assert_not_called()
    
    def test_archive_old_conversations_database_error(self, conversation_store, mock_db_session):
        """Test handling of database errors during archiving"""
        # Setup
        mock_db_session.query.side_effect = SQLAlchemyError("Database error")
        
        # Execute
        result = conversation_store.archive_old_conversations(retention_days=90)
        
        # Verify
        assert result == 0
        mock_db_session.rollback.assert_called_once()

class TestCleanupExpiredData(TestConversationHistoryStore):
    """Tests for cleanup_expired_data method"""
    
    def test_cleanup_expired_data_success(self, conversation_store, mock_db_session):
        """Test successful cleanup of expired data"""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5
        mock_query.delete.return_value = 5
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = conversation_store.cleanup_expired_data(max_age_days=365)
        
        # Verify
        expected_result = {
            'conversations_deleted': 5,
            'summaries_deleted': 5,
            'legacy_entries_deleted': 5,
            'total_deleted': 15
        }
        assert result == expected_result
        mock_db_session.commit.assert_called_once()
    
    def test_cleanup_expired_data_database_error(self, conversation_store, mock_db_session):
        """Test handling of database errors during cleanup"""
        # Setup
        mock_db_session.query.side_effect = SQLAlchemyError("Database error")
        
        # Execute
        result = conversation_store.cleanup_expired_data(max_age_days=365)
        
        # Verify
        assert 'error' in result
        mock_db_session.rollback.assert_called_once()

class TestGetConversationStats(TestConversationHistoryStore):
    """Tests for get_conversation_stats method"""
    
    def test_get_conversation_stats_success(self, conversation_store, mock_db_session):
        """Test successful retrieval of conversation statistics"""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 100
        mock_db_session.query.return_value = mock_query
        
        # Mock scalar queries for aggregations
        mock_db_session.query.return_value.scalar.return_value = 50  # unique users
        
        # Execute
        result = conversation_store.get_conversation_stats(days_back=30)
        
        # Verify
        assert isinstance(result, ConversationStats)
        assert result.total_conversations == 100
    
    def test_get_conversation_stats_with_user_filter(self, conversation_store, mock_db_session):
        """Test conversation stats with user filter"""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 25
        mock_db_session.query.return_value = mock_query
        mock_db_session.query.return_value.scalar.return_value = 1
        
        # Execute
        result = conversation_store.get_conversation_stats(user_id="user_456", days_back=7)
        
        # Verify
        assert isinstance(result, ConversationStats)
        assert result.total_conversations == 25

class TestApplyFilters(TestConversationHistoryStore):
    """Tests for _apply_filters method"""
    
    def test_apply_filters_all_criteria(self, conversation_store):
        """Test applying all filter criteria"""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        filters = ConversationFilter(
            session_id="test_session",
            start_date=datetime.now(timezone.utc) - timedelta(days=7),
            end_date=datetime.now(timezone.utc),
            min_quality_score=0.8,
            tools_used=["tool1", "tool2"],
            limit=50,
            offset=10,
            order_by="created_at",
            order_direction="desc"
        )
        
        # Execute
        result = conversation_store._apply_filters(mock_query, filters)
        
        # Verify
        assert result == mock_query
        # Should have multiple filter calls for different criteria
        assert mock_query.filter.call_count >= 4
        mock_query.order_by.assert_called_once()
        mock_query.offset.assert_called_once_with(10)
        mock_query.limit.assert_called_once_with(50)
    
    def test_apply_filters_minimal_criteria(self, conversation_store):
        """Test applying minimal filter criteria"""
        # Setup
        mock_query = Mock()
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        filters = ConversationFilter(limit=10, offset=0)
        
        # Execute
        result = conversation_store._apply_filters(mock_query, filters)
        
        # Verify
        assert result == mock_query
        mock_query.order_by.assert_called_once()
        mock_query.offset.assert_called_once_with(0)
        mock_query.limit.assert_called_once_with(10)

class TestToConversationDto(TestConversationHistoryStore):
    """Tests for _to_conversation_dto method"""
    
    def test_to_conversation_dto_complete_data(self, conversation_store, sample_enhanced_chat_history):
        """Test conversion of complete database entry to DTO"""
        # Execute
        result = conversation_store._to_conversation_dto(sample_enhanced_chat_history)
        
        # Verify
        assert isinstance(result, ConversationEntryDTO)
        assert result.session_id == sample_enhanced_chat_history.session_id
        assert result.user_id == sample_enhanced_chat_history.user_id
        assert result.user_message == sample_enhanced_chat_history.user_message
        assert result.bot_response == sample_enhanced_chat_history.bot_response
        assert result.tools_used == sample_enhanced_chat_history.tools_used
        assert result.tool_performance == sample_enhanced_chat_history.tool_performance
        assert result.context_used == sample_enhanced_chat_history.context_used
        assert result.response_quality_score == sample_enhanced_chat_history.response_quality_score
        assert result.timestamp == sample_enhanced_chat_history.created_at
    
    def test_to_conversation_dto_minimal_data(self, conversation_store):
        """Test conversion with minimal database entry data"""
        # Setup
        minimal_entry = EnhancedChatHistory(
            session_id="test_session",
            user_id="test_user",
            user_message="Test message",
            bot_response="Test response",
            created_at=datetime.now(timezone.utc)
        )
        
        # Execute
        result = conversation_store._to_conversation_dto(minimal_entry)
        
        # Verify
        assert isinstance(result, ConversationEntryDTO)
        assert result.tools_used == []
        assert result.tool_performance == {}
        assert result.context_used == []

class TestCreateConversationSummary(TestConversationHistoryStore):
    """Tests for _create_conversation_summary method"""
    
    def test_create_conversation_summary_success(self, conversation_store, sample_enhanced_chat_history):
        """Test successful creation of conversation summary"""
        # Execute
        result = conversation_store._create_conversation_summary(sample_enhanced_chat_history)
        
        # Verify
        assert isinstance(result, ConversationSummary)
        assert result.user_id == sample_enhanced_chat_history.user_id
        assert result.session_id == sample_enhanced_chat_history.session_id
        assert len(result.summary_text) > 0
        assert isinstance(result.key_topics, list)
        assert isinstance(result.important_context, dict)
    
    def test_create_conversation_summary_with_tools(self, conversation_store):
        """Test summary creation with tool usage data"""
        # Setup
        conversation_with_tools = EnhancedChatHistory(
            session_id="test_session",
            user_id="test_user",
            user_message="I have an error with my account",
            bot_response="Let me help you with that error",
            tools_used=["customer_db_tool", "error_handler"],
            response_quality_score=0.95,
            created_at=datetime.now(timezone.utc)
        )
        
        # Execute
        result = conversation_store._create_conversation_summary(conversation_with_tools)
        
        # Verify
        assert result is not None
        assert 'error' in result.key_topics
        assert 'tools_used' in result.important_context
        assert result.important_context['tools_used'] == ["customer_db_tool", "error_handler"]
        assert result.important_context['quality_score'] == 0.95

class TestConversationFilter:
    """Tests for ConversationFilter class"""
    
    def test_conversation_filter_defaults(self):
        """Test ConversationFilter with default values"""
        filter_obj = ConversationFilter()
        
        assert filter_obj.user_id is None
        assert filter_obj.session_id is None
        assert filter_obj.start_date is None
        assert filter_obj.end_date is None
        assert filter_obj.tools_used == []
        assert filter_obj.min_quality_score is None
        assert filter_obj.search_text is None
        assert filter_obj.limit == 100
        assert filter_obj.offset == 0
        assert filter_obj.order_by == "created_at"
        assert filter_obj.order_direction == "desc"
    
    def test_conversation_filter_custom_values(self):
        """Test ConversationFilter with custom values"""
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        filter_obj = ConversationFilter(
            user_id="test_user",
            session_id="test_session",
            start_date=start_date,
            end_date=end_date,
            tools_used=["tool1", "tool2"],
            min_quality_score=0.8,
            search_text="test query",
            limit=50,
            offset=25,
            order_by="response_quality_score",
            order_direction="asc"
        )
        
        assert filter_obj.user_id == "test_user"
        assert filter_obj.session_id == "test_session"
        assert filter_obj.start_date == start_date
        assert filter_obj.end_date == end_date
        assert filter_obj.tools_used == ["tool1", "tool2"]
        assert filter_obj.min_quality_score == 0.8
        assert filter_obj.search_text == "test query"
        assert filter_obj.limit == 50
        assert filter_obj.offset == 25
        assert filter_obj.order_by == "response_quality_score"
        assert filter_obj.order_direction == "asc"

class TestConversationStats:
    """Tests for ConversationStats class"""
    
    def test_conversation_stats_defaults(self):
        """Test ConversationStats with default values"""
        stats = ConversationStats()
        
        assert stats.total_conversations == 0
        assert stats.total_users == 0
        assert stats.average_quality_score == 0.0
        assert stats.most_used_tools == []
        assert stats.conversations_by_date == {}
    
    def test_conversation_stats_custom_values(self):
        """Test ConversationStats with custom values"""
        most_used_tools = [("tool1", 50), ("tool2", 30)]
        conversations_by_date = {"2024-01-01": 10, "2024-01-02": 15}
        
        stats = ConversationStats(
            total_conversations=100,
            total_users=25,
            average_quality_score=0.85,
            most_used_tools=most_used_tools,
            conversations_by_date=conversations_by_date
        )
        
        assert stats.total_conversations == 100
        assert stats.total_users == 25
        assert stats.average_quality_score == 0.85
        assert stats.most_used_tools == most_used_tools
        assert stats.conversations_by_date == conversations_by_date

if __name__ == "__main__":
    pytest.main([__file__])