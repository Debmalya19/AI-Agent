"""
Unit tests for memory layer data models and DTOs.
Tests data validation, serialization, and database model operations.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from memory_models import (
    EnhancedChatHistory,
    MemoryContextCache,
    ToolUsageMetrics,
    ConversationSummary,
    MemoryConfiguration,
    MemoryHealthMetrics,
    ConversationEntry,
    ContextEntry,
    ToolRecommendation,
    create_enhanced_chat_entry,
    create_context_cache_entry,
    create_tool_usage_metric
)

# Test database setup
@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

class TestConversationEntry:
    """Test ConversationEntry dataclass"""
    
    def test_valid_conversation_entry(self):
        """Test creating a valid conversation entry"""
        entry = ConversationEntry(
            session_id="test-session-123",
            user_id="user-456",
            user_message="Hello, how are you?",
            bot_response="I'm doing well, thank you!",
            tools_used=["greeting_tool"],
            tool_performance={"greeting_tool": 0.95},
            context_used=["previous_greeting"],
            response_quality_score=0.9
        )
        
        assert entry.session_id == "test-session-123"
        assert entry.user_id == "user-456"
        assert entry.user_message == "Hello, how are you?"
        assert entry.bot_response == "I'm doing well, thank you!"
        assert entry.tools_used == ["greeting_tool"]
        assert entry.tool_performance == {"greeting_tool": 0.95}
        assert entry.context_used == ["previous_greeting"]
        assert entry.response_quality_score == 0.9
        assert isinstance(entry.timestamp, datetime)
    
    def test_conversation_entry_validation_empty_session_id(self):
        """Test validation fails for empty session_id"""
        with pytest.raises(ValueError, match="session_id must be a non-empty string"):
            ConversationEntry(
                session_id="",
                user_id="user-456",
                user_message="Hello",
                bot_response="Hi"
            )
    
    def test_conversation_entry_validation_invalid_quality_score(self):
        """Test validation fails for invalid quality score"""
        with pytest.raises(ValueError, match="response_quality_score must be between 0.0 and 1.0"):
            ConversationEntry(
                session_id="test-session",
                user_id="user-456",
                user_message="Hello",
                bot_response="Hi",
                response_quality_score=1.5
            )
    
    def test_conversation_entry_to_dict(self):
        """Test converting conversation entry to dictionary"""
        entry = ConversationEntry(
            session_id="test-session",
            user_id="user-456",
            user_message="Hello",
            bot_response="Hi",
            response_quality_score=0.8
        )
        
        data = entry.to_dict()
        assert data['session_id'] == "test-session"
        assert data['user_id'] == "user-456"
        assert data['user_message'] == "Hello"
        assert data['bot_response'] == "Hi"
        assert data['response_quality_score'] == 0.8
        assert 'timestamp' in data
    
    def test_conversation_entry_from_dict(self):
        """Test creating conversation entry from dictionary"""
        data = {
            'session_id': 'test-session',
            'user_id': 'user-456',
            'user_message': 'Hello',
            'bot_response': 'Hi',
            'tools_used': ['test_tool'],
            'tool_performance': {'test_tool': 0.9},
            'context_used': ['context1'],
            'response_quality_score': 0.8,
            'timestamp': '2024-01-01T12:00:00+00:00'
        }
        
        entry = ConversationEntry.from_dict(data)
        assert entry.session_id == 'test-session'
        assert entry.user_id == 'user-456'
        assert entry.tools_used == ['test_tool']
        assert entry.tool_performance == {'test_tool': 0.9}
        assert entry.response_quality_score == 0.8

class TestContextEntry:
    """Test ContextEntry dataclass"""
    
    def test_valid_context_entry(self):
        """Test creating a valid context entry"""
        entry = ContextEntry(
            content="This is relevant context",
            source="conversation_history",
            relevance_score=0.85,
            context_type="conversation",
            metadata={"importance": "high"}
        )
        
        assert entry.content == "This is relevant context"
        assert entry.source == "conversation_history"
        assert entry.relevance_score == 0.85
        assert entry.context_type == "conversation"
        assert entry.metadata == {"importance": "high"}
        assert isinstance(entry.timestamp, datetime)
    
    def test_context_entry_validation_invalid_type(self):
        """Test validation fails for invalid context type"""
        with pytest.raises(ValueError, match="context_type must be one of"):
            ContextEntry(
                content="Test content",
                source="test_source",
                relevance_score=0.5,
                context_type="invalid_type"
            )
    
    def test_context_entry_validation_invalid_relevance_score(self):
        """Test validation fails for invalid relevance score"""
        with pytest.raises(ValueError, match="relevance_score must be between 0.0 and 1.0"):
            ContextEntry(
                content="Test content",
                source="test_source",
                relevance_score=2.0,
                context_type="conversation"
            )
    
    def test_context_entry_to_dict(self):
        """Test converting context entry to dictionary"""
        entry = ContextEntry(
            content="Test content",
            source="test_source",
            relevance_score=0.7,
            context_type="conversation"
        )
        
        data = entry.to_dict()
        assert data['content'] == "Test content"
        assert data['source'] == "test_source"
        assert data['relevance_score'] == 0.7
        assert data['context_type'] == "conversation"
        assert 'timestamp' in data
    
    def test_context_entry_from_dict(self):
        """Test creating context entry from dictionary"""
        data = {
            'content': 'Test content',
            'source': 'test_source',
            'relevance_score': 0.7,
            'context_type': 'conversation',
            'timestamp': '2024-01-01T12:00:00+00:00',
            'metadata': {'key': 'value'}
        }
        
        entry = ContextEntry.from_dict(data)
        assert entry.content == 'Test content'
        assert entry.source == 'test_source'
        assert entry.relevance_score == 0.7
        assert entry.context_type == 'conversation'
        assert entry.metadata == {'key': 'value'}

class TestToolRecommendation:
    """Test ToolRecommendation dataclass"""
    
    def test_valid_tool_recommendation(self):
        """Test creating a valid tool recommendation"""
        recommendation = ToolRecommendation(
            tool_name="search_tool",
            confidence_score=0.9,
            reason="High success rate in similar queries",
            expected_performance=0.85
        )
        
        assert recommendation.tool_name == "search_tool"
        assert recommendation.confidence_score == 0.9
        assert recommendation.reason == "High success rate in similar queries"
        assert recommendation.expected_performance == 0.85
    
    def test_tool_recommendation_validation_invalid_tool_name(self):
        """Test validation fails for invalid tool name"""
        with pytest.raises(ValueError, match="tool_name must contain only alphanumeric characters"):
            ToolRecommendation(
                tool_name="invalid tool name!",
                confidence_score=0.9,
                reason="Test reason",
                expected_performance=0.8
            )
    
    def test_tool_recommendation_validation_invalid_confidence(self):
        """Test validation fails for invalid confidence score"""
        with pytest.raises(ValueError, match="confidence_score must be between 0.0 and 1.0"):
            ToolRecommendation(
                tool_name="test_tool",
                confidence_score=1.5,
                reason="Test reason",
                expected_performance=0.8
            )
    
    def test_tool_recommendation_to_dict(self):
        """Test converting tool recommendation to dictionary"""
        recommendation = ToolRecommendation(
            tool_name="test_tool",
            confidence_score=0.8,
            reason="Test reason",
            expected_performance=0.7
        )
        
        data = recommendation.to_dict()
        assert data['tool_name'] == "test_tool"
        assert data['confidence_score'] == 0.8
        assert data['reason'] == "Test reason"
        assert data['expected_performance'] == 0.7
    
    def test_tool_recommendation_from_dict(self):
        """Test creating tool recommendation from dictionary"""
        data = {
            'tool_name': 'test_tool',
            'confidence_score': 0.8,
            'reason': 'Test reason',
            'expected_performance': 0.7
        }
        
        recommendation = ToolRecommendation.from_dict(data)
        assert recommendation.tool_name == 'test_tool'
        assert recommendation.confidence_score == 0.8
        assert recommendation.reason == 'Test reason'
        assert recommendation.expected_performance == 0.7

class TestEnhancedChatHistory:
    """Test EnhancedChatHistory database model"""
    
    def test_create_enhanced_chat_history(self, db_session):
        """Test creating enhanced chat history entry"""
        entry = EnhancedChatHistory(
            session_id="test-session",
            user_id="user-123",
            user_message="Hello",
            bot_response="Hi there!",
            tools_used=["greeting_tool"],
            tool_performance={"greeting_tool": 0.9},
            context_used=["previous_context"],
            response_quality_score=0.85
        )
        
        db_session.add(entry)
        db_session.commit()
        
        # Retrieve and verify
        retrieved = db_session.query(EnhancedChatHistory).first()
        assert retrieved.session_id == "test-session"
        assert retrieved.user_id == "user-123"
        assert retrieved.user_message == "Hello"
        assert retrieved.bot_response == "Hi there!"
        assert retrieved.tools_used == ["greeting_tool"]
        assert retrieved.response_quality_score == 0.85
    
    def test_enhanced_chat_history_to_conversation_entry(self, db_session):
        """Test converting database model to DTO"""
        entry = EnhancedChatHistory(
            session_id="test-session",
            user_id="user-123",
            user_message="Hello",
            bot_response="Hi there!",
            tools_used=["greeting_tool"],
            response_quality_score=0.85
        )
        
        db_session.add(entry)
        db_session.commit()
        
        conversation_entry = entry.to_conversation_entry()
        assert isinstance(conversation_entry, ConversationEntry)
        assert conversation_entry.session_id == "test-session"
        assert conversation_entry.user_id == "user-123"
        assert conversation_entry.tools_used == ["greeting_tool"]
        assert conversation_entry.response_quality_score == 0.85

class TestMemoryContextCache:
    """Test MemoryContextCache database model"""
    
    def test_create_memory_context_cache(self, db_session):
        """Test creating memory context cache entry"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        entry = MemoryContextCache(
            cache_key="test-key-123",
            user_id="user-123",
            context_data={"content": "Test context", "source": "test"},
            context_type="conversation",
            relevance_score=0.8,
            expires_at=expires_at
        )
        
        db_session.add(entry)
        db_session.commit()
        
        # Retrieve and verify
        retrieved = db_session.query(MemoryContextCache).first()
        assert retrieved.cache_key == "test-key-123"
        assert retrieved.user_id == "user-123"
        assert retrieved.context_data == {"content": "Test context", "source": "test"}
        assert retrieved.context_type == "conversation"
        assert retrieved.relevance_score == 0.8
    
    def test_memory_context_cache_to_context_entry(self, db_session):
        """Test converting cache model to DTO"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        entry = MemoryContextCache(
            cache_key="test-key",
            context_data={"content": "Test content", "source": "test_source", "metadata": {"key": "value"}},
            context_type="conversation",
            relevance_score=0.7,
            expires_at=expires_at
        )
        
        db_session.add(entry)
        db_session.commit()
        
        context_entry = entry.to_context_entry()
        assert isinstance(context_entry, ContextEntry)
        assert context_entry.content == "Test content"
        assert context_entry.source == "test_source"
        assert context_entry.relevance_score == 0.7
        assert context_entry.context_type == "conversation"
        assert context_entry.metadata == {"key": "value"}
    
    def test_memory_context_cache_is_expired(self, db_session):
        """Test cache expiration check"""
        # Create expired entry
        expired_entry = MemoryContextCache(
            cache_key="expired-key",
            context_data={"content": "Expired content"},
            context_type="conversation",
            relevance_score=0.5,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        # Create valid entry
        valid_entry = MemoryContextCache(
            cache_key="valid-key",
            context_data={"content": "Valid content"},
            context_type="conversation",
            relevance_score=0.5,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        assert expired_entry.is_expired() == True
        assert valid_entry.is_expired() == False

class TestToolUsageMetrics:
    """Test ToolUsageMetrics database model"""
    
    def test_create_tool_usage_metrics(self, db_session):
        """Test creating tool usage metrics entry"""
        entry = ToolUsageMetrics(
            tool_name="search_tool",
            query_type="search",
            query_hash="abc123",
            success_rate=0.85,
            average_response_time=1.2,
            response_quality_score=0.9,
            usage_count=10
        )
        
        db_session.add(entry)
        db_session.commit()
        
        # Retrieve and verify
        retrieved = db_session.query(ToolUsageMetrics).first()
        assert retrieved.tool_name == "search_tool"
        assert retrieved.query_type == "search"
        assert retrieved.success_rate == 0.85
        assert retrieved.average_response_time == 1.2
        assert retrieved.response_quality_score == 0.9
        assert retrieved.usage_count == 10
    
    def test_tool_usage_metrics_to_tool_recommendation(self, db_session):
        """Test converting metrics to tool recommendation"""
        entry = ToolUsageMetrics(
            tool_name="search_tool",
            success_rate=0.9,
            response_quality_score=0.85,
            usage_count=20
        )
        
        recommendation = entry.to_tool_recommendation("Test reason")
        assert isinstance(recommendation, ToolRecommendation)
        assert recommendation.tool_name == "search_tool"
        assert recommendation.reason == "Test reason"
        assert recommendation.expected_performance == 0.85
        assert 0.0 <= recommendation.confidence_score <= 1.0
    
    def test_tool_usage_metrics_update_metrics(self, db_session):
        """Test updating tool usage metrics"""
        entry = ToolUsageMetrics(
            tool_name="test_tool",
            success_rate=0.8,
            average_response_time=1.0,
            response_quality_score=0.7,
            usage_count=5
        )
        
        # Update with successful usage
        entry.update_metrics(success=True, response_time=0.8, quality_score=0.9)
        
        assert entry.usage_count == 6
        assert entry.success_rate > 0.8  # Should increase
        assert entry.average_response_time < 1.0  # Should decrease
        assert entry.response_quality_score > 0.7  # Should increase

class TestUtilityFunctions:
    """Test utility functions for model creation"""
    
    def test_create_enhanced_chat_entry(self):
        """Test utility function for creating enhanced chat entry"""
        entry = create_enhanced_chat_entry(
            session_id="test-session",
            user_id="user-123",
            user_message="Hello",
            bot_response="Hi",
            tools_used=["test_tool"],
            response_quality_score=0.8
        )
        
        assert isinstance(entry, EnhancedChatHistory)
        assert entry.session_id == "test-session"
        assert entry.user_id == "user-123"
        assert entry.tools_used == ["test_tool"]
        assert entry.response_quality_score == 0.8
    
    def test_create_context_cache_entry(self):
        """Test utility function for creating context cache entry"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        entry = create_context_cache_entry(
            cache_key="test-key",
            context_data={"content": "Test"},
            context_type="conversation",
            expires_at=expires_at,
            user_id="user-123",
            relevance_score=0.7
        )
        
        assert isinstance(entry, MemoryContextCache)
        assert entry.cache_key == "test-key"
        assert entry.user_id == "user-123"
        assert entry.context_type == "conversation"
        assert entry.relevance_score == 0.7
    
    def test_create_tool_usage_metric(self):
        """Test utility function for creating tool usage metric"""
        entry = create_tool_usage_metric(
            tool_name="test_tool",
            query_type="search",
            success_rate=0.9,
            usage_count=5
        )
        
        assert isinstance(entry, ToolUsageMetrics)
        assert entry.tool_name == "test_tool"
        assert entry.query_type == "search"
        assert entry.success_rate == 0.9
        assert entry.usage_count == 5

class TestAdditionalUtilities:
    """Test additional utility functions"""
    
    def test_generate_query_hash(self):
        """Test query hash generation"""
        from memory_models import generate_query_hash
        
        hash1 = generate_query_hash("Hello world")
        hash2 = generate_query_hash("hello   world")  # Different spacing
        hash3 = generate_query_hash("HELLO WORLD")    # Different case
        hash4 = generate_query_hash("Goodbye world")  # Different content
        
        # Same content should produce same hash
        assert hash1 == hash2 == hash3
        # Different content should produce different hash
        assert hash1 != hash4
        # Hash should be 16 characters
        assert len(hash1) == 16
    
    def test_validate_json_serializable(self):
        """Test JSON serialization validation"""
        from memory_models import validate_json_serializable
        
        # Valid JSON data
        assert validate_json_serializable({"key": "value"}) == True
        assert validate_json_serializable([1, 2, 3]) == True
        assert validate_json_serializable("string") == True
        assert validate_json_serializable(123) == True
        
        # Invalid JSON data
        assert validate_json_serializable(datetime.now()) == False
        assert validate_json_serializable(set([1, 2, 3])) == False
    
    def test_sanitize_for_storage(self):
        """Test data sanitization for storage"""
        from memory_models import sanitize_for_storage
        
        data = {
            "valid_string": "test",
            "valid_number": 123,
            "valid_list": [1, 2, 3],
            "invalid_datetime": datetime.now(),
            "invalid_set": set([1, 2, 3])
        }
        
        sanitized = sanitize_for_storage(data)
        
        # Valid data should remain unchanged
        assert sanitized["valid_string"] == "test"
        assert sanitized["valid_number"] == 123
        assert sanitized["valid_list"] == [1, 2, 3]
        
        # Invalid data should be converted to string
        assert isinstance(sanitized["invalid_datetime"], str)
        assert isinstance(sanitized["invalid_set"], str)
    
    def test_create_conversation_summary(self):
        """Test conversation summary creation"""
        from memory_models import create_conversation_summary
        
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=1)
        
        summary = create_conversation_summary(
            user_id="user-123",
            session_id="session-456",
            summary_text="User asked about weather",
            key_topics=["weather", "forecast"],
            important_context={"location": "New York"},
            date_range_start=start_time,
            date_range_end=end_time
        )
        
        assert isinstance(summary, ConversationSummary)
        assert summary.user_id == "user-123"
        assert summary.session_id == "session-456"
        assert summary.summary_text == "User asked about weather"
        assert summary.key_topics == ["weather", "forecast"]
        assert summary.important_context == {"location": "New York"}

class TestDataValidation:
    """Test data validation functions"""
    
    def test_validate_conversation_data_valid(self):
        """Test validation of valid conversation data"""
        from memory_models import validate_conversation_data
        
        valid_data = {
            "session_id": "test-session",
            "user_id": "user-123",
            "user_message": "Hello",
            "bot_response": "Hi there!",
            "response_quality_score": 0.8
        }
        
        # Should not raise exception
        validate_conversation_data(valid_data)
    
    def test_validate_conversation_data_missing_field(self):
        """Test validation fails for missing required field"""
        from memory_models import validate_conversation_data, ValidationError
        
        invalid_data = {
            "session_id": "test-session",
            "user_id": "user-123",
            "user_message": "Hello"
            # Missing bot_response
        }
        
        with pytest.raises(ValidationError, match="Missing required field: bot_response"):
            validate_conversation_data(invalid_data)
    
    def test_validate_conversation_data_invalid_score(self):
        """Test validation fails for invalid quality score"""
        from memory_models import validate_conversation_data, ValidationError
        
        invalid_data = {
            "session_id": "test-session",
            "user_id": "user-123",
            "user_message": "Hello",
            "bot_response": "Hi",
            "response_quality_score": 1.5  # Invalid score
        }
        
        with pytest.raises(ValidationError, match="response_quality_score must be between 0.0 and 1.0"):
            validate_conversation_data(invalid_data)
    
    def test_validate_context_data_valid(self):
        """Test validation of valid context data"""
        from memory_models import validate_context_data
        
        valid_data = {
            "content": "Test content",
            "source": "test_source",
            "relevance_score": 0.7,
            "context_type": "conversation"
        }
        
        # Should not raise exception
        validate_context_data(valid_data)
    
    def test_validate_context_data_invalid_type(self):
        """Test validation fails for invalid context type"""
        from memory_models import validate_context_data, ValidationError
        
        invalid_data = {
            "content": "Test content",
            "source": "test_source",
            "relevance_score": 0.7,
            "context_type": "invalid_type"
        }
        
        with pytest.raises(ValidationError, match="context_type must be one of"):
            validate_context_data(invalid_data)
    
    def test_validate_tool_recommendation_data_valid(self):
        """Test validation of valid tool recommendation data"""
        from memory_models import validate_tool_recommendation_data
        
        valid_data = {
            "tool_name": "search_tool",
            "confidence_score": 0.9,
            "reason": "High success rate",
            "expected_performance": 0.8
        }
        
        # Should not raise exception
        validate_tool_recommendation_data(valid_data)
    
    def test_validate_tool_recommendation_data_invalid_name(self):
        """Test validation fails for invalid tool name"""
        from memory_models import validate_tool_recommendation_data, ValidationError
        
        invalid_data = {
            "tool_name": "invalid tool name!",
            "confidence_score": 0.9,
            "reason": "Test reason",
            "expected_performance": 0.8
        }
        
        with pytest.raises(ValidationError, match="tool_name must contain only alphanumeric characters"):
            validate_tool_recommendation_data(invalid_data)

if __name__ == "__main__":
    pytest.main([__file__])