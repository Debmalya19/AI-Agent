# ConversationHistoryStore Usage Guide

## Overview

The `ConversationHistoryStore` provides comprehensive conversation management capabilities for the AI agent system. It offers persistent storage, intelligent search, filtering, archiving, and cleanup functionality while maintaining backward compatibility with the existing `ChatHistory` model.

## Key Features

- **Persistent Storage**: Save conversations with enhanced metadata including tool usage and quality scores
- **Intelligent Search**: Full-text search across conversation history with relevance ranking
- **Advanced Filtering**: Filter conversations by user, session, date range, quality score, and tools used
- **Data Archiving**: Automatic archiving of old conversations with summary generation
- **Cleanup Operations**: Configurable data retention and cleanup policies
- **Backward Compatibility**: Seamless integration with existing `ChatHistory` model
- **Statistics**: Comprehensive conversation analytics and reporting

## Basic Usage

### 1. Initialize the Store

```python
from sqlalchemy.orm import Session
from conversation_history_store import ConversationHistoryStore
from database import get_db

# Get database session
db = next(get_db())

# Create store instance
conversation_store = ConversationHistoryStore(db)
```

### 2. Save Conversations

```python
from memory_models import ConversationEntryDTO
from datetime import datetime, timezone

# Create conversation entry
conversation = ConversationEntryDTO(
    session_id="session_123",
    user_id="user_456",
    user_message="How do I reset my password?",
    bot_response="I'll help you reset your password. Let me guide you through the process.",
    tools_used=["auth_service", "email_service"],
    tool_performance={"auth_service": 0.95, "email_service": 0.88},
    context_used=["user_profile", "security_settings"],
    response_quality_score=0.92,
    timestamp=datetime.now(timezone.utc)
)

# Save to database
conversation_id = conversation_store.save_conversation(conversation)
print(f"Saved conversation with ID: {conversation_id}")
```

### 3. Retrieve User History

```python
# Get recent conversations for a user
user_history = conversation_store.get_user_history("user_456", limit=20)

for conv in user_history:
    print(f"Session: {conv.session_id}")
    print(f"User: {conv.user_message}")
    print(f"Bot: {conv.bot_response}")
    print(f"Quality: {conv.response_quality_score}")
    print("---")
```

### 4. Search Conversations

```python
# Search for conversations containing specific text
search_results = conversation_store.search_conversations(
    "password reset",
    user_id="user_456"  # Optional: limit to specific user
)

print(f"Found {len(search_results)} conversations about password reset")
```

## Advanced Usage

### 1. Using Filters

```python
from conversation_history_store import ConversationFilter
from datetime import datetime, timedelta, timezone

# Create advanced filter
filter_criteria = ConversationFilter(
    user_id="user_456",
    start_date=datetime.now(timezone.utc) - timedelta(days=7),
    end_date=datetime.now(timezone.utc),
    min_quality_score=0.8,
    tools_used=["auth_service"],
    limit=50,
    offset=0,
    order_by="response_quality_score",
    order_direction="desc"
)

# Apply filter to user history
filtered_conversations = conversation_store.get_user_history(
    "user_456",
    filters=filter_criteria
)

print(f"Found {len(filtered_conversations)} high-quality conversations using auth_service")
```

### 2. Conversation Statistics

```python
# Get conversation statistics
stats = conversation_store.get_conversation_stats(
    user_id="user_456",  # Optional: specific user
    days_back=30
)

print(f"Total conversations: {stats.total_conversations}")
print(f"Total users: {stats.total_users}")
print(f"Average quality score: {stats.average_quality_score:.2f}")
print(f"Most used tools: {stats.most_used_tools}")
```

### 3. Data Management

```python
# Archive old conversations (creates summaries before deletion)
archived_count = conversation_store.archive_old_conversations(retention_days=90)
print(f"Archived {archived_count} old conversations")

# Cleanup expired data
cleanup_stats = conversation_store.cleanup_expired_data(max_age_days=365)
print(f"Cleanup results: {cleanup_stats}")
```

## Filter Options

The `ConversationFilter` class supports the following criteria:

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | str | Filter by specific user ID |
| `session_id` | str | Filter by specific session ID |
| `start_date` | datetime | Filter conversations after this date |
| `end_date` | datetime | Filter conversations before this date |
| `tools_used` | List[str] | Filter by tools that were used |
| `min_quality_score` | float | Filter by minimum quality score |
| `search_text` | str | Text search within conversations |
| `limit` | int | Maximum number of results (default: 100) |
| `offset` | int | Number of results to skip (default: 0) |
| `order_by` | str | Field to order by (default: "created_at") |
| `order_direction` | str | "asc" or "desc" (default: "desc") |

## Integration with Existing Systems

### ChatHistory Compatibility

The store automatically creates entries in both the new `EnhancedChatHistory` table and the legacy `ChatHistory` table, ensuring backward compatibility:

```python
# When you save a conversation, both tables are updated:
# 1. EnhancedChatHistory - with full metadata and analytics
# 2. ChatHistory - for backward compatibility with existing code
```

### Memory Layer Integration

The store integrates seamlessly with other memory layer components:

```python
from memory_layer_manager import MemoryLayerManager

# The MemoryLayerManager uses ConversationHistoryStore internally
memory_manager = MemoryLayerManager(config)
memory_manager.conversation_store  # Access to the store
```

## Error Handling

The store includes comprehensive error handling:

```python
try:
    conversation_id = conversation_store.save_conversation(conversation)
except SQLAlchemyError as e:
    print(f"Database error: {e}")
    # Store handles rollback automatically
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance Considerations

### Database Indexes

The store relies on several database indexes for optimal performance:

- `idx_enhanced_chat_user_session` - User and session queries
- `idx_enhanced_chat_created` - Date-based queries
- `idx_enhanced_chat_quality` - Quality score filtering

### Caching

For high-performance scenarios, consider implementing caching:

```python
# Example with Redis caching (implementation depends on your setup)
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_user_history(user_id: str, limit: int = 50):
    return conversation_store.get_user_history(user_id, limit)
```

### Pagination

Use pagination for large result sets:

```python
# Get conversations in pages
page_size = 50
page_number = 1

filter_with_pagination = ConversationFilter(
    limit=page_size,
    offset=(page_number - 1) * page_size
)

conversations = conversation_store.get_user_history("user_456", filters=filter_with_pagination)
```

## Monitoring and Maintenance

### Regular Maintenance Tasks

```python
# Schedule these operations regularly:

# 1. Archive old conversations (weekly)
archived = conversation_store.archive_old_conversations(retention_days=90)

# 2. Cleanup expired data (monthly)
cleanup_stats = conversation_store.cleanup_expired_data(max_age_days=365)

# 3. Monitor conversation statistics (daily)
stats = conversation_store.get_conversation_stats(days_back=1)
```

### Health Checks

```python
def health_check():
    try:
        # Test basic functionality
        stats = conversation_store.get_conversation_stats(days_back=1)
        return {"status": "healthy", "conversations_today": stats.total_conversations}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Best Practices

1. **Always use database sessions properly**: Ensure sessions are closed after use
2. **Handle errors gracefully**: The store includes error handling, but wrap calls in try-catch blocks
3. **Use filters for large datasets**: Don't retrieve all conversations at once
4. **Regular maintenance**: Schedule archiving and cleanup operations
5. **Monitor performance**: Track query performance and optimize as needed
6. **Quality scores**: Implement meaningful quality scoring for better analytics

## Requirements Satisfied

This implementation satisfies the following requirements from the specification:

- **Requirement 1.1**: Persistent storage of chat history with metadata
- **Requirement 1.2**: Context-aware conversation retrieval
- **Requirement 4.3**: Configurable data retention and cleanup
- **Requirement 5.3**: Secure data handling and privacy protection

## Testing

Run the comprehensive test suite:

```bash
python -m pytest ai-agent/test_conversation_history_store.py -v
```

For integration testing, run the example:

```bash
python ai-agent/conversation_history_integration_example.py
```