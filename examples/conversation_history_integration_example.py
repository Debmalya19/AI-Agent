"""
Integration example demonstrating how ConversationHistoryStore works
with the existing ChatHistory model and database infrastructure.
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from database import get_db, init_db
from conversation_history_store import ConversationHistoryStore, ConversationFilter
from memory_models import ConversationEntryDTO
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demonstrate_conversation_history_store():
    """
    Demonstrate the ConversationHistoryStore functionality with real database operations.
    This example shows how the store integrates with existing models and provides
    enhanced conversation management capabilities.
    """
    
    # Initialize database (create tables if they don't exist)
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Create ConversationHistoryStore instance
        conversation_store = ConversationHistoryStore(db)
        logger.info("ConversationHistoryStore initialized")
        
        # Example 1: Save a new conversation
        logger.info("\n=== Example 1: Saving Conversations ===")
        
        conversation1 = ConversationEntryDTO(
            session_id="demo_session_001",
            user_id="user_123",
            user_message="Hello, I'm having trouble logging into my account",
            bot_response="I'd be happy to help you with your login issue. Let me check your account status and guide you through the troubleshooting steps.",
            tools_used=["customer_db_tool", "auth_validator"],
            tool_performance={"customer_db_tool": 0.95, "auth_validator": 0.88},
            context_used=["user_profile", "recent_login_attempts"],
            response_quality_score=0.92,
            timestamp=datetime.now(timezone.utc)
        )
        
        conversation2 = ConversationEntryDTO(
            session_id="demo_session_001",
            user_id="user_123",
            user_message="I tried resetting my password but didn't receive the email",
            bot_response="Let me check your email settings and resend the password reset email. I can also verify if there are any delivery issues.",
            tools_used=["email_service", "customer_db_tool"],
            tool_performance={"email_service": 0.87, "customer_db_tool": 0.93},
            context_used=["previous_conversation", "email_preferences"],
            response_quality_score=0.89,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Save conversations
        conv1_id = conversation_store.save_conversation(conversation1)
        conv2_id = conversation_store.save_conversation(conversation2)
        logger.info(f"Saved conversations with IDs: {conv1_id}, {conv2_id}")
        
        # Example 2: Retrieve user history
        logger.info("\n=== Example 2: Retrieving User History ===")
        
        user_history = conversation_store.get_user_history("user_123", limit=10)
        logger.info(f"Retrieved {len(user_history)} conversations for user_123")
        
        for i, conv in enumerate(user_history, 1):
            logger.info(f"  Conversation {i}:")
            logger.info(f"    Session: {conv.session_id}")
            logger.info(f"    User: {conv.user_message[:50]}...")
            logger.info(f"    Bot: {conv.bot_response[:50]}...")
            logger.info(f"    Tools: {conv.tools_used}")
            logger.info(f"    Quality: {conv.response_quality_score}")
        
        # Example 3: Search conversations
        logger.info("\n=== Example 3: Searching Conversations ===")
        
        search_results = conversation_store.search_conversations(
            "login trouble", 
            user_id="user_123"
        )
        logger.info(f"Found {len(search_results)} conversations matching 'login trouble'")
        
        for result in search_results:
            logger.info(f"  Match: {result.user_message[:100]}...")
        
        # Example 4: Using filters
        logger.info("\n=== Example 4: Using Conversation Filters ===")
        
        # Create filter for high-quality conversations
        quality_filter = ConversationFilter(
            min_quality_score=0.9,
            tools_used=["customer_db_tool"],
            limit=5,
            order_by="response_quality_score",
            order_direction="desc"
        )
        
        filtered_conversations = conversation_store.get_user_history(
            "user_123", 
            filters=quality_filter
        )
        logger.info(f"Found {len(filtered_conversations)} high-quality conversations using customer_db_tool")
        
        # Example 5: Get conversation statistics
        logger.info("\n=== Example 5: Conversation Statistics ===")
        
        stats = conversation_store.get_conversation_stats(user_id="user_123", days_back=7)
        logger.info(f"Conversation stats for user_123 (last 7 days):")
        logger.info(f"  Total conversations: {stats.total_conversations}")
        logger.info(f"  Average quality score: {stats.average_quality_score:.2f}")
        
        # Example 6: Demonstrate backward compatibility with ChatHistory
        logger.info("\n=== Example 6: Backward Compatibility ===")
        
        # Query legacy ChatHistory table to show both entries exist
        from models import ChatHistory
        legacy_entries = db.query(ChatHistory).filter(
            ChatHistory.session_id == "demo_session_001"
        ).all()
        
        logger.info(f"Found {len(legacy_entries)} entries in legacy ChatHistory table")
        for entry in legacy_entries:
            logger.info(f"  Legacy entry: {entry.user_message[:50]}...")
        
        # Example 7: Cleanup demonstration (commented out to avoid deleting demo data)
        logger.info("\n=== Example 7: Cleanup Operations ===")
        logger.info("Cleanup operations available:")
        logger.info("  - archive_old_conversations(retention_days=90)")
        logger.info("  - cleanup_expired_data(max_age_days=365)")
        logger.info("  (Not executed in demo to preserve data)")
        
        logger.info("\n=== Integration Demo Complete ===")
        logger.info("ConversationHistoryStore successfully integrates with:")
        logger.info("  ✓ Enhanced memory models")
        logger.info("  ✓ Legacy ChatHistory model")
        logger.info("  ✓ Existing database infrastructure")
        logger.info("  ✓ Comprehensive search and filtering")
        logger.info("  ✓ Data archiving and cleanup")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        db.rollback()
    
    finally:
        # Close database session
        db.close()

if __name__ == "__main__":
    demonstrate_conversation_history_store()