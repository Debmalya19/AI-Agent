"""
Core Memory Layer Manager for the AI agent system.
Provides centralized management of conversation storage, context retrieval,
and memory statistics with configurable policies and monitoring.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import hashlib
import json
import time

from backend.database import get_db, SessionLocal
from backend.memory_config import MemoryConfig, load_config
from backend.memory_models import (
    EnhancedChatHistory,
    MemoryContextCache,
    ToolUsageMetrics,
    ConversationSummary,
    MemoryHealthMetrics,
    ConversationEntryDTO,
    ContextEntryDTO,
    ToolRecommendationDTO,
    create_enhanced_chat_entry,
    create_context_cache_entry,
    create_tool_usage_metric
)


class MemoryStats:
    """Statistics about memory system performance and usage"""
    
    def __init__(self):
        self.total_conversations: int = 0
        self.total_context_entries: int = 0
        self.total_tool_usages: int = 0
        self.cache_hit_rate: float = 0.0
        self.average_response_time: float = 0.0
        self.storage_usage_mb: float = 0.0
        self.last_cleanup: Optional[datetime] = None
        self.health_score: float = 1.0
        self.error_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary"""
        return {
            'total_conversations': self.total_conversations,
            'total_context_entries': self.total_context_entries,
            'total_tool_usages': self.total_tool_usages,
            'cache_hit_rate': self.cache_hit_rate,
            'average_response_time': self.average_response_time,
            'storage_usage_mb': self.storage_usage_mb,
            'last_cleanup': self.last_cleanup.isoformat() if self.last_cleanup else None,
            'health_score': self.health_score,
            'error_count': self.error_count
        }


class CleanupResult:
    """Result of memory cleanup operations"""
    
    def __init__(self):
        self.conversations_cleaned: int = 0
        self.context_entries_cleaned: int = 0
        self.tool_metrics_cleaned: int = 0
        self.space_freed_mb: float = 0.0
        self.cleanup_duration: float = 0.0
        self.errors: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cleanup result to dictionary"""
        return {
            'conversations_cleaned': self.conversations_cleaned,
            'context_entries_cleaned': self.context_entries_cleaned,
            'tool_metrics_cleaned': self.tool_metrics_cleaned,
            'space_freed_mb': self.space_freed_mb,
            'cleanup_duration': self.cleanup_duration,
            'errors': self.errors
        }


class MemoryLayerManager:
    """
    Central manager for the memory layer functionality.
    Handles conversation storage, context retrieval, and memory statistics.
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None, db_session: Optional[Session] = None):
        """
        Initialize the Memory Layer Manager.
        
        Args:
            config: Memory configuration settings
            db_session: Database session (optional, will create if not provided)
        """
        self.config = config or load_config()
        self.db_session = db_session
        self._session_factory = SessionLocal if not db_session else None
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, self.config.log_level))
        
        # Performance tracking
        self._operation_times: Dict[str, List[float]] = {}
        self._error_count = 0
        self._last_cleanup = None
        
        # Validate configuration
        config_errors = self.config.validate()
        if config_errors:
            self.logger.warning(f"Configuration validation errors: {config_errors}")
        
        self.logger.info(f"Memory Layer Manager initialized with config: storage={self.config.enable_database_storage}, "
                        f"context_retrieval={self.config.enable_context_retrieval}, "
                        f"tool_analytics={self.config.enable_tool_analytics}")
    
    def _get_session(self) -> Session:
        """Get database session"""
        if self.db_session:
            return self.db_session
        return self._session_factory()
    
    def _close_session(self, session: Session) -> None:
        """Close database session if we created it"""
        if not self.db_session:
            session.close()
    
    def _track_operation_time(self, operation: str, duration: float) -> None:
        """Track operation execution time for performance monitoring"""
        if operation not in self._operation_times:
            self._operation_times[operation] = []
        
        self._operation_times[operation].append(duration)
        
        # Keep only last 100 measurements
        if len(self._operation_times[operation]) > 100:
            self._operation_times[operation] = self._operation_times[operation][-100:]
    
    def _log_error(self, operation: str, error: Exception) -> None:
        """Log error and increment error counter"""
        self._error_count += 1
        self.logger.error(f"Error in {operation}: {str(error)}")
        
        if self.config.log_memory_operations:
            self.logger.debug(f"Error details: {error}", exc_info=True)
    
    def store_conversation(self, conversation: ConversationEntryDTO) -> bool:
        """
        Store a conversation entry in the memory system.
        
        Args:
            conversation: Conversation entry to store
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        start_time = time.time()
        session = None
        
        try:
            if not self.config.enable_database_storage:
                self.logger.debug("Database storage disabled, skipping conversation storage")
                return True
            
            session = self._get_session()
            
            # Create enhanced chat history entry
            chat_entry = create_enhanced_chat_entry(
                session_id=conversation.session_id,
                user_id=conversation.user_id,
                user_message=conversation.user_message,
                bot_response=conversation.bot_response,
                tools_used=conversation.tools_used,
                tool_performance=conversation.tool_performance,
                context_used=conversation.context_used,
                response_quality_score=conversation.response_quality_score
            )
            
            session.add(chat_entry)
            session.commit()
            
            duration = time.time() - start_time
            self._track_operation_time('store_conversation', duration)
            
            if self.config.log_memory_operations:
                self.logger.info(f"Stored conversation for user {conversation.user_id} in {duration:.3f}s")
            
            return True
            
        except Exception as e:
            if session:
                session.rollback()
            self._log_error('store_conversation', e)
            return False
        
        finally:
            if session:
                self._close_session(session)
    
    def retrieve_context(self, query: str, user_id: str, limit: int = 10) -> List[ContextEntryDTO]:
        """
        Retrieve relevant context entries for a query.
        
        Args:
            query: Query string to find relevant context for
            user_id: User ID to filter context by
            limit: Maximum number of context entries to return
            
        Returns:
            List of relevant context entries
        """
        start_time = time.time()
        session = None
        
        try:
            if not self.config.enable_context_retrieval:
                self.logger.debug("Context retrieval disabled")
                return []
            
            session = self._get_session()
            context_entries = []
            
            # Limit by configuration
            actual_limit = min(limit, self.config.performance.max_context_entries)
            
            # Query recent conversations for context
            recent_conversations = session.query(EnhancedChatHistory).filter(
                and_(
                    EnhancedChatHistory.user_id == user_id,
                    EnhancedChatHistory.created_at >= datetime.now(timezone.utc) - timedelta(
                        days=self.config.retention.conversation_retention_days
                    )
                )
            ).order_by(desc(EnhancedChatHistory.created_at)).limit(actual_limit).all()
            
            # Convert to context entries
            for conv in recent_conversations:
                # Add user message as context
                context_entries.append(ContextEntryDTO(
                    content=conv.user_message,
                    source=f"conversation_{conv.id}",
                    relevance_score=self._calculate_relevance_score(query, conv.user_message),
                    context_type="conversation",  # Use valid context type
                    timestamp=conv.created_at,
                    metadata={
                        'session_id': conv.session_id,
                        'tools_used': conv.tools_used or [],
                        'response_quality': conv.response_quality_score,
                        'message_type': 'user_message'
                    }
                ))
                
                # Add bot response as context
                context_entries.append(ContextEntryDTO(
                    content=conv.bot_response,
                    source=f"conversation_{conv.id}",
                    relevance_score=self._calculate_relevance_score(query, conv.bot_response),
                    context_type="conversation",  # Use valid context type
                    timestamp=conv.created_at,
                    metadata={
                        'session_id': conv.session_id,
                        'tools_used': conv.tools_used or [],
                        'response_quality': conv.response_quality_score,
                        'message_type': 'bot_response'
                    }
                ))
            
            # Filter by minimum relevance score (but allow at least some entries)
            filtered_entries = [
                entry for entry in context_entries 
                if entry.relevance_score >= self.config.quality.min_relevance_score
            ]
            
            # If no entries meet the threshold, return the best ones anyway (up to 3)
            if not filtered_entries and context_entries:
                context_entries.sort(key=lambda x: x.relevance_score, reverse=True)
                filtered_entries = context_entries[:3]
            else:
                context_entries = filtered_entries
            
            # Sort by relevance score
            filtered_entries.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Return top entries
            result = filtered_entries[:actual_limit]
            
            duration = time.time() - start_time
            self._track_operation_time('retrieve_context', duration)
            
            if self.config.log_memory_operations:
                self.logger.info(f"Retrieved {len(result)} context entries for user {user_id} in {duration:.3f}s")
            
            return result
            
        except Exception as e:
            self._log_error('retrieve_context', e)
            return []
        
        finally:
            if session:
                self._close_session(session)
    
    def _calculate_relevance_score(self, query: str, content: str) -> float:
        """
        Calculate relevance score between query and content.
        Simple implementation using word overlap - can be enhanced with embeddings.
        
        Args:
            query: Query string
            content: Content to compare against
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not query or not content:
            return 0.0
        
        # Simple word-based similarity
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words or not content_words:
            return 0.0
        
        intersection = query_words.intersection(content_words)
        union = query_words.union(content_words)
        
        return len(intersection) / len(union) if union else 0.0
    
    def analyze_tool_usage(self, query: str, tools_used: List[str]) -> Optional[ToolRecommendationDTO]:
        """
        Analyze tool usage patterns and provide recommendations.
        
        Args:
            query: Query that triggered tool usage
            tools_used: List of tools that were used
            
        Returns:
            Tool recommendation based on historical data
        """
        start_time = time.time()
        session = None
        
        try:
            if not self.config.enable_tool_analytics:
                self.logger.debug("Tool analytics disabled")
                return None
            
            session = self._get_session()
            
            # Get query hash for grouping similar queries
            query_hash = hashlib.md5(query.lower().encode()).hexdigest()[:16]
            
            # Find similar queries and their successful tools
            similar_metrics = session.query(ToolUsageMetrics).filter(
                and_(
                    ToolUsageMetrics.query_hash == query_hash,
                    ToolUsageMetrics.success_rate >= self.config.quality.tool_success_threshold
                )
            ).order_by(desc(ToolUsageMetrics.success_rate)).all()
            
            if not similar_metrics:
                # No historical data, return None
                return None
            
            # Find the best performing tool
            best_tool = similar_metrics[0]
            
            recommendation = ToolRecommendationDTO(
                tool_name=best_tool.tool_name,
                confidence_score=best_tool.success_rate,
                reason=f"Tool has {best_tool.success_rate:.1%} success rate for similar queries",
                expected_performance=best_tool.response_quality_score or 0.0
            )
            
            duration = time.time() - start_time
            self._track_operation_time('analyze_tool_usage', duration)
            
            if self.config.log_memory_operations:
                self.logger.info(f"Generated tool recommendation in {duration:.3f}s")
            
            return recommendation
            
        except Exception as e:
            self._log_error('analyze_tool_usage', e)
            return None
        
        finally:
            if session:
                self._close_session(session)
    
    def cleanup_expired_data(self) -> CleanupResult:
        """
        Clean up expired data according to retention policies.
        
        Returns:
            CleanupResult with details of cleanup operation
        """
        start_time = time.time()
        session = None
        result = CleanupResult()
        
        try:
            session = self._get_session()
            
            # Clean up old conversations
            conversation_cutoff = datetime.now(timezone.utc) - timedelta(
                days=self.config.retention.conversation_retention_days
            )
            
            old_conversations = session.query(EnhancedChatHistory).filter(
                EnhancedChatHistory.created_at < conversation_cutoff
            )
            result.conversations_cleaned = old_conversations.count()
            old_conversations.delete()
            
            # Clean up expired context cache
            cache_cutoff = datetime.now(timezone.utc) - timedelta(
                hours=self.config.retention.context_cache_retention_hours
            )
            
            expired_cache = session.query(MemoryContextCache).filter(
                MemoryContextCache.expires_at < cache_cutoff
            )
            result.context_entries_cleaned = expired_cache.count()
            expired_cache.delete()
            
            # Clean up old tool metrics
            metrics_cutoff = datetime.now(timezone.utc) - timedelta(
                days=self.config.retention.tool_metrics_retention_days
            )
            
            old_metrics = session.query(ToolUsageMetrics).filter(
                ToolUsageMetrics.created_at < metrics_cutoff
            )
            result.tool_metrics_cleaned = old_metrics.count()
            old_metrics.delete()
            
            session.commit()
            
            result.cleanup_duration = time.time() - start_time
            self._last_cleanup = datetime.now(timezone.utc)
            
            if self.config.log_memory_operations:
                self.logger.info(f"Cleanup completed in {result.cleanup_duration:.3f}s: "
                               f"{result.conversations_cleaned} conversations, "
                               f"{result.context_entries_cleaned} cache entries, "
                               f"{result.tool_metrics_cleaned} tool metrics")
            
            return result
            
        except Exception as e:
            if session:
                session.rollback()
            self._log_error('cleanup_expired_data', e)
            result.errors.append(str(e))
            return result
        
        finally:
            if session:
                self._close_session(session)
    
    def get_memory_stats(self) -> MemoryStats:
        """
        Get comprehensive memory system statistics.
        
        Returns:
            MemoryStats object with current system statistics
        """
        start_time = time.time()
        session = None
        stats = MemoryStats()
        
        try:
            session = self._get_session()
            
            # Count total conversations
            stats.total_conversations = session.query(EnhancedChatHistory).count()
            
            # Count total context entries
            stats.total_context_entries = session.query(MemoryContextCache).count()
            
            # Count total tool usages
            stats.total_tool_usages = session.query(ToolUsageMetrics).count()
            
            # Calculate average response time
            if 'retrieve_context' in self._operation_times:
                stats.average_response_time = sum(self._operation_times['retrieve_context']) / len(self._operation_times['retrieve_context'])
            
            # Set error count
            stats.error_count = self._error_count
            
            # Set last cleanup time
            stats.last_cleanup = self._last_cleanup
            
            # Calculate health score (simple implementation)
            stats.health_score = max(0.0, 1.0 - (self._error_count * 0.1))
            
            duration = time.time() - start_time
            self._track_operation_time('get_memory_stats', duration)
            
            if self.config.log_performance_metrics:
                self.logger.info(f"Generated memory stats in {duration:.3f}s")
            
            return stats
            
        except Exception as e:
            self._log_error('get_memory_stats', e)
            return stats
        
        finally:
            if session:
                self._close_session(session)
    
    def record_health_metric(self, metric_name: str, metric_value: float, 
                           metric_unit: str = "", metric_category: str = "general") -> bool:
        """
        Record a health metric for monitoring.
        
        Args:
            metric_name: Name of the metric
            metric_value: Value of the metric
            metric_unit: Unit of measurement
            metric_category: Category of the metric
            
        Returns:
            bool: True if recorded successfully
        """
        if not self.config.enable_health_monitoring:
            return True
        
        session = None
        
        try:
            session = self._get_session()
            
            health_metric = MemoryHealthMetrics(
                metric_name=metric_name,
                metric_value=metric_value,
                metric_unit=metric_unit,
                metric_category=metric_category
            )
            
            session.add(health_metric)
            session.commit()
            
            return True
            
        except Exception as e:
            if session:
                session.rollback()
            self._log_error('record_health_metric', e)
            return False
        
        finally:
            if session:
                self._close_session(session)
    
    def get_user_conversation_history(self, user_id: str, limit: int = 50) -> List[ConversationEntryDTO]:
        """
        Get conversation history for a specific user.
        
        Args:
            user_id: User ID to get history for
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation entries
        """
        session = None
        
        try:
            session = self._get_session()
            
            # Limit by configuration
            actual_limit = min(limit, self.config.performance.max_conversation_history)
            
            conversations = session.query(EnhancedChatHistory).filter(
                EnhancedChatHistory.user_id == user_id
            ).order_by(desc(EnhancedChatHistory.created_at)).limit(actual_limit).all()
            
            result = []
            for conv in conversations:
                result.append(ConversationEntryDTO(
                    session_id=conv.session_id,
                    user_id=conv.user_id,
                    user_message=conv.user_message,
                    bot_response=conv.bot_response,
                    tools_used=conv.tools_used or [],
                    tool_performance=conv.tool_performance or {},
                    context_used=conv.context_used or [],
                    response_quality_score=conv.response_quality_score,
                    timestamp=conv.created_at
                ))
            
            return result
            
        except Exception as e:
            self._log_error('get_user_conversation_history', e)
            return []
        
        finally:
            if session:
                self._close_session(session)
    
    def cleanup_user_session_data(self, user_id: str, session_id: Optional[str] = None) -> CleanupResult:
        """
        Clean up memory data for a specific user session (called on logout).

        Args:
            user_id: User ID to clean up data for
            session_id: Optional specific session ID to clean up

        Returns:
            CleanupResult with details of cleanup operation
        """
        start_time = time.time()
        session = None
        result = CleanupResult()

        try:
            session = self._get_session()

            # Clean up user's conversation data
            conversation_query = session.query(EnhancedChatHistory).filter(
                EnhancedChatHistory.user_id == user_id
            )

            # If specific session provided, filter by session too
            if session_id:
                conversation_query = conversation_query.filter(
                    EnhancedChatHistory.session_id == session_id
                )

            # For logout cleanup, only clean conversations older than 1 hour
            # to preserve recent conversation context
            conversation_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            old_conversations = conversation_query.filter(
                EnhancedChatHistory.created_at < conversation_cutoff
            )
            result.conversations_cleaned = old_conversations.count()
            old_conversations.delete()

            # Clean up user's context cache entries
            # MemoryContextCache has user_id field but no session_id field
            cache_query = session.query(MemoryContextCache).filter(
                MemoryContextCache.user_id == user_id
            )

            # For session-specific cleanup, we can only filter by user_id
            # since MemoryContextCache doesn't have session_id field
            result.context_entries_cleaned = cache_query.count()
            cache_query.delete()

            # Clean up tool usage metrics
            # ToolUsageMetrics doesn't have user_id or session_id fields
            # So we clean by age only (older than 24 hours)
            metrics_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            old_metrics = session.query(ToolUsageMetrics).filter(
                ToolUsageMetrics.created_at < metrics_cutoff
            )
            result.tool_metrics_cleaned = old_metrics.count()
            old_metrics.delete()

            session.commit()

            result.cleanup_duration = time.time() - start_time

            if self.config.log_memory_operations:
                cleanup_details = []
                if result.conversations_cleaned > 0:
                    cleanup_details.append(f"{result.conversations_cleaned} conversations")
                if result.context_entries_cleaned > 0:
                    cleanup_details.append(f"{result.context_entries_cleaned} cache entries")
                if result.tool_metrics_cleaned > 0:
                    cleanup_details.append(f"{result.tool_metrics_cleaned} tool metrics")

                if cleanup_details:
                    self.logger.info(f"User logout cleanup completed for user {user_id} in {result.cleanup_duration:.3f}s: "
                                   f"{', '.join(cleanup_details)}")
                else:
                    self.logger.info(f"User logout cleanup completed for user {user_id} in {result.cleanup_duration:.3f}s: "
                                   "No data to clean")

            return result

        except Exception as e:
            if session:
                session.rollback()
            self._log_error('cleanup_user_session_data', e)
            result.errors.append(str(e))
            return result

        finally:
            if session:
                self._close_session(session)