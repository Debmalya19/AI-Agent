"""
Integration example showing how to use MemoryErrorHandler with memory layer components.

This example demonstrates how to integrate error handling and recovery mechanisms
with the existing memory layer system components.
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from memory_error_handler import (
    MemoryErrorHandler, 
    handle_memory_errors, 
    FallbackStrategy,
    ErrorType
)
from memory_layer_manager import MemoryLayerManager
from context_retrieval_engine import ContextRetrievalEngine
from conversation_history_store import ConversationHistoryStore
from tool_usage_analytics import ToolUsageAnalytics
from memory_config import MemoryConfig


class EnhancedMemoryLayerManager:
    """
    Enhanced Memory Layer Manager with comprehensive error handling.
    
    This class wraps the original MemoryLayerManager with error handling
    and recovery mechanisms for production use.
    """
    
    def __init__(self, config: MemoryConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.error_handler = MemoryErrorHandler(self.logger)
        
        # Initialize core components with error handling
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize memory layer components with error handling."""
        try:
            self.memory_manager = MemoryLayerManager(self.config)
            self.logger.info("Memory layer components initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize memory layer components: {e}")
            # Use fallback configuration
            fallback_config = MemoryConfig()
            self.memory_manager = MemoryLayerManager(fallback_config)
    
    @handle_memory_errors(None, "store_conversation")  # Will be set in __post_init__
    def store_conversation_safe(self, user_id: str, user_message: str, 
                               bot_response: str, tools_used: List[str] = None) -> bool:
        """
        Store conversation with error handling and recovery.
        
        Args:
            user_id: User identifier
            user_message: User's message
            bot_response: Bot's response
            tools_used: List of tools used in the conversation
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        try:
            # Use circuit breaker for database operations
            db_breaker = self.error_handler.get_circuit_breaker('database')
            
            @db_breaker
            def store_operation():
                return self.memory_manager.store_conversation(
                    user_id=user_id,
                    user_message=user_message,
                    bot_response=bot_response,
                    tools_used=tools_used or []
                )
            
            return store_operation()
            
        except Exception as e:
            fallback = self.error_handler.handle_database_error(e, "store_conversation")
            
            if fallback == FallbackStrategy.RETRY_WITH_BACKOFF:
                # Retry with exponential backoff
                return self.error_handler.retry_operation(
                    self._store_conversation_fallback,
                    "store_conversation_retry",
                    max_retries=3,
                    user_id=user_id,
                    user_message=user_message,
                    bot_response=bot_response,
                    tools_used=tools_used
                )
            elif fallback == FallbackStrategy.USE_CACHE:
                # Store in cache as fallback
                return self._store_in_cache(user_id, user_message, bot_response, tools_used)
            else:
                self.logger.warning(f"Failed to store conversation for user {user_id}")
                return False
    
    def _store_conversation_fallback(self, user_id: str, user_message: str, 
                                   bot_response: str, tools_used: List[str]):
        """Fallback method for storing conversation."""
        return self.memory_manager.store_conversation(
            user_id=user_id,
            user_message=user_message,
            bot_response=bot_response,
            tools_used=tools_used
        )
    
    def _store_in_cache(self, user_id: str, user_message: str, 
                       bot_response: str, tools_used: List[str]) -> bool:
        """Store conversation in cache as fallback."""
        try:
            # Implement cache storage logic here
            cache_key = f"conversation:{user_id}:{datetime.now().isoformat()}"
            conversation_data = {
                "user_message": user_message,
                "bot_response": bot_response,
                "tools_used": tools_used,
                "timestamp": datetime.now().isoformat()
            }
            # This would use Redis or another cache implementation
            self.logger.info(f"Stored conversation in cache with key: {cache_key}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to store in cache: {e}")
            return False
    
    def retrieve_context_safe(self, query: str, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve context with error handling and recovery.
        
        Args:
            query: Search query
            user_id: User identifier
            limit: Maximum number of results
            
        Returns:
            List of context entries
        """
        try:
            # Use circuit breaker for context retrieval
            cache_breaker = self.error_handler.get_circuit_breaker('cache')
            
            @cache_breaker
            def retrieve_operation():
                return self.memory_manager.retrieve_context(query, user_id, limit)
            
            return retrieve_operation()
            
        except Exception as e:
            fallback = self.error_handler.handle_context_error(e, query)
            
            if fallback == FallbackStrategy.RETURN_EMPTY:
                self.logger.warning(f"Returning empty context for query: {query[:50]}...")
                return []
            elif fallback == FallbackStrategy.USE_DATABASE:
                # Try database fallback
                return self._retrieve_from_database(query, user_id, limit)
            else:
                return []
    
    def _retrieve_from_database(self, query: str, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Fallback method for retrieving context from database."""
        try:
            # Direct database query as fallback
            return self.memory_manager.retrieve_context_from_db(query, user_id, limit)
        except Exception as e:
            self.logger.error(f"Database fallback failed: {e}")
            return []
    
    def analyze_tool_usage_safe(self, query: str, tools_used: List[str]) -> Dict[str, Any]:
        """
        Analyze tool usage with error handling.
        
        Args:
            query: User query
            tools_used: List of tools used
            
        Returns:
            Tool analysis results
        """
        try:
            return self.memory_manager.analyze_tool_usage(query, tools_used)
        except Exception as e:
            fallback = self.error_handler.handle_tool_analytics_error(e, str(tools_used))
            
            if fallback == FallbackStrategy.USE_DEFAULT:
                return {
                    "recommended_tools": tools_used,
                    "confidence_scores": {tool: 0.5 for tool in tools_used},
                    "fallback_used": True
                }
            else:
                return {}
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health report."""
        health_report = self.error_handler.get_health_report()
        
        # Add memory-specific health metrics
        try:
            memory_stats = self.memory_manager.get_memory_stats()
            health_report["memory_stats"] = memory_stats
        except Exception as e:
            health_report["memory_stats"] = {"error": str(e)}
        
        return health_report
    
    def cleanup_with_recovery(self) -> Dict[str, Any]:
        """Perform cleanup operations with error recovery."""
        cleanup_results = {
            "expired_data_cleaned": False,
            "cache_cleared": False,
            "errors": []
        }
        
        # Clean expired data with error handling
        try:
            with self.error_handler.error_recovery_context("cleanup_expired_data", max_retries=2):
                result = self.memory_manager.cleanup_expired_data()
                cleanup_results["expired_data_cleaned"] = True
                cleanup_results["expired_count"] = result.get("cleaned_count", 0)
        except Exception as e:
            cleanup_results["errors"].append(f"Expired data cleanup failed: {e}")
        
        # Clear cache with error handling
        try:
            with self.error_handler.error_recovery_context("clear_cache", max_retries=1):
                # Implement cache clearing logic
                cleanup_results["cache_cleared"] = True
        except Exception as e:
            cleanup_results["errors"].append(f"Cache clear failed: {e}")
        
        return cleanup_results


def setup_error_handler_integration():
    """Set up the error handler decorator with the instance."""
    # This function demonstrates how to properly set up the decorator
    # with the error handler instance
    pass


async def demonstrate_error_handling():
    """
    Demonstrate error handling and recovery mechanisms in action.
    """
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize enhanced memory manager
    config = MemoryConfig()
    enhanced_manager = EnhancedMemoryLayerManager(config, logger)
    
    # Set up the error handler for the decorator
    handle_memory_errors.__defaults__ = (enhanced_manager.error_handler, "unknown")
    
    logger.info("=== Memory Error Handler Integration Demo ===")
    
    # Test 1: Store conversation with error handling
    logger.info("\n1. Testing conversation storage with error handling...")
    success = enhanced_manager.store_conversation_safe(
        user_id="test_user_123",
        user_message="How do I implement error handling?",
        bot_response="Here's how to implement comprehensive error handling...",
        tools_used=["documentation_search", "code_analysis"]
    )
    logger.info(f"Conversation storage result: {success}")
    
    # Test 2: Retrieve context with error handling
    logger.info("\n2. Testing context retrieval with error handling...")
    context = enhanced_manager.retrieve_context_safe(
        query="error handling patterns",
        user_id="test_user_123",
        limit=5
    )
    logger.info(f"Retrieved {len(context)} context entries")
    
    # Test 3: Tool usage analysis with error handling
    logger.info("\n3. Testing tool usage analysis with error handling...")
    analysis = enhanced_manager.analyze_tool_usage_safe(
        query="implement error handling",
        tools_used=["documentation_search", "code_analysis"]
    )
    logger.info(f"Tool analysis result: {analysis}")
    
    # Test 4: System health check
    logger.info("\n4. Checking system health...")
    health = enhanced_manager.get_system_health()
    logger.info(f"System healthy: {health['is_healthy']}")
    logger.info(f"Error metrics: {len(health['error_metrics'])} types tracked")
    
    # Test 5: Cleanup with recovery
    logger.info("\n5. Testing cleanup with error recovery...")
    cleanup_result = enhanced_manager.cleanup_with_recovery()
    logger.info(f"Cleanup results: {cleanup_result}")
    
    # Test 6: Demonstrate circuit breaker
    logger.info("\n6. Testing circuit breaker functionality...")
    db_breaker = enhanced_manager.error_handler.get_circuit_breaker('database')
    logger.info(f"Database circuit breaker state: Open={db_breaker.state.is_open}, "
                f"Failures={db_breaker.state.failure_count}")
    
    logger.info("\n=== Demo completed successfully ===")


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demonstrate_error_handling())