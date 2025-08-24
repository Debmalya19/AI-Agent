"""
Conversation History Store for persistent storage and retrieval of chat interactions.
This module provides comprehensive conversation management including storage, search,
filtering, archiving, and cleanup functionality.
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func, text
from sqlalchemy.exc import SQLAlchemyError
import logging
import hashlib
import json

from models import ChatHistory, User
from memory_models import (
    EnhancedChatHistory, 
    ConversationSummary,
    ConversationEntryDTO,
    create_enhanced_chat_entry
)

logger = logging.getLogger(__name__)

class ConversationFilter:
    """Filter criteria for conversation searches"""
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tools_used: Optional[List[str]] = None,
        min_quality_score: Optional[float] = None,
        search_text: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.start_date = start_date
        self.end_date = end_date
        self.tools_used = tools_used or []
        self.min_quality_score = min_quality_score
        self.search_text = search_text
        self.limit = limit
        self.offset = offset
        self.order_by = order_by
        self.order_direction = order_direction

class ConversationStats:
    """Statistics about conversation data"""
    
    def __init__(
        self,
        total_conversations: int = 0,
        total_users: int = 0,
        average_quality_score: float = 0.0,
        most_used_tools: List[Tuple[str, int]] = None,
        conversations_by_date: Dict[str, int] = None
    ):
        self.total_conversations = total_conversations
        self.total_users = total_users
        self.average_quality_score = average_quality_score
        self.most_used_tools = most_used_tools or []
        self.conversations_by_date = conversations_by_date or {}

class ConversationHistoryStore:
    """
    Persistent storage and retrieval system for conversation history.
    Provides comprehensive conversation management with search, filtering,
    archiving, and cleanup capabilities.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the conversation history store.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.logger = logging.getLogger(__name__)
    
    def save_conversation(self, entry: ConversationEntryDTO) -> str:
        """
        Save a conversation entry to persistent storage.
        
        Args:
            entry: ConversationEntryDTO containing conversation data
            
        Returns:
            str: The ID of the saved conversation entry
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Create enhanced chat history entry
            enhanced_entry = create_enhanced_chat_entry(
                session_id=entry.session_id,
                user_id=entry.user_id,
                user_message=entry.user_message,
                bot_response=entry.bot_response,
                tools_used=entry.tools_used,
                tool_performance=entry.tool_performance,
                context_used=entry.context_used,
                response_quality_score=entry.response_quality_score
            )
            
            # Also save to legacy ChatHistory for backward compatibility
            legacy_entry = ChatHistory(
                session_id=entry.session_id,
                user_message=entry.user_message,
                bot_response=entry.bot_response,
                tools_used=entry.tools_used,
                sources=entry.context_used
            )
            
            self.db.add(enhanced_entry)
            self.db.add(legacy_entry)
            self.db.commit()
            
            self.logger.info(f"Saved conversation entry for user {entry.user_id}, session {entry.session_id}")
            return str(enhanced_entry.id)
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to save conversation entry: {e}")
            raise
    
    def get_user_history(
        self, 
        user_id: str, 
        limit: int = 50, 
        filters: Optional[ConversationFilter] = None
    ) -> List[ConversationEntryDTO]:
        """
        Retrieve conversation history for a specific user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of conversations to return
            filters: Optional filter criteria
            
        Returns:
            List[ConversationEntryDTO]: List of conversation entries
        """
        try:
            query = self.db.query(EnhancedChatHistory).filter(
                EnhancedChatHistory.user_id == user_id
            )
            
            # Apply filters if provided
            if filters:
                query = self._apply_filters(query, filters)
            
            # Apply ordering and limit
            query = query.order_by(desc(EnhancedChatHistory.created_at)).limit(limit)
            
            results = query.all()
            
            # Convert to DTOs
            conversations = []
            for result in results:
                conversations.append(self._to_conversation_dto(result))
            
            self.logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
            return conversations
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to retrieve user history: {e}")
            return []
    
    def search_conversations(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        filters: Optional[ConversationFilter] = None
    ) -> List[ConversationEntryDTO]:
        """
        Search conversations using text search.
        
        Args:
            query: Search query text
            user_id: Optional user ID to limit search scope
            filters: Optional additional filter criteria
            
        Returns:
            List[ConversationEntryDTO]: Matching conversation entries
        """
        try:
            # Build base query with text search
            db_query = self.db.query(EnhancedChatHistory).filter(
                or_(
                    EnhancedChatHistory.user_message.ilike(f"%{query}%"),
                    EnhancedChatHistory.bot_response.ilike(f"%{query}%")
                )
            )
            
            # Filter by user if specified
            if user_id:
                db_query = db_query.filter(EnhancedChatHistory.user_id == user_id)
            
            # Apply additional filters
            if filters:
                db_query = self._apply_filters(db_query, filters)
            
            # Order by relevance (quality score) and recency
            db_query = db_query.order_by(
                desc(EnhancedChatHistory.response_quality_score),
                desc(EnhancedChatHistory.created_at)
            )
            
            # Apply limit
            limit = filters.limit if filters else 50
            results = db_query.limit(limit).all()
            
            # Convert to DTOs
            conversations = []
            for result in results:
                conversations.append(self._to_conversation_dto(result))
            
            self.logger.info(f"Found {len(conversations)} conversations matching query: {query}")
            return conversations
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to search conversations: {e}")
            return []
    
    def archive_old_conversations(self, retention_days: int = 90) -> int:
        """
        Archive conversations older than the specified retention period.
        
        Args:
            retention_days: Number of days to retain conversations
            
        Returns:
            int: Number of conversations archived
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Find conversations to archive
            conversations_to_archive = self.db.query(EnhancedChatHistory).filter(
                EnhancedChatHistory.created_at < cutoff_date
            ).all()
            
            archived_count = 0
            
            for conversation in conversations_to_archive:
                # Create summary before archiving
                summary = self._create_conversation_summary(conversation)
                if summary:
                    self.db.add(summary)
                    archived_count += 1
            
            # Delete old conversations after creating summaries
            if archived_count > 0:
                self.db.query(EnhancedChatHistory).filter(
                    EnhancedChatHistory.created_at < cutoff_date
                ).delete()
                
                # Also clean up legacy chat history
                self.db.query(ChatHistory).filter(
                    ChatHistory.created_at < cutoff_date
                ).delete()
                
                self.db.commit()
            
            self.logger.info(f"Archived {archived_count} conversations older than {retention_days} days")
            return archived_count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to archive conversations: {e}")
            return 0
    
    def cleanup_expired_data(self, max_age_days: int = 365) -> Dict[str, int]:
        """
        Clean up expired conversation data and summaries.
        
        Args:
            max_age_days: Maximum age in days for data retention
            
        Returns:
            Dict[str, int]: Cleanup statistics
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            
            # Count items to be deleted
            conversations_count = self.db.query(EnhancedChatHistory).filter(
                EnhancedChatHistory.created_at < cutoff_date
            ).count()
            
            summaries_count = self.db.query(ConversationSummary).filter(
                ConversationSummary.created_at < cutoff_date
            ).count()
            
            legacy_count = self.db.query(ChatHistory).filter(
                ChatHistory.created_at < cutoff_date
            ).count()
            
            # Delete expired data
            self.db.query(EnhancedChatHistory).filter(
                EnhancedChatHistory.created_at < cutoff_date
            ).delete()
            
            self.db.query(ConversationSummary).filter(
                ConversationSummary.created_at < cutoff_date
            ).delete()
            
            self.db.query(ChatHistory).filter(
                ChatHistory.created_at < cutoff_date
            ).delete()
            
            self.db.commit()
            
            cleanup_stats = {
                'conversations_deleted': conversations_count,
                'summaries_deleted': summaries_count,
                'legacy_entries_deleted': legacy_count,
                'total_deleted': conversations_count + summaries_count + legacy_count
            }
            
            self.logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to cleanup expired data: {e}")
            return {'error': str(e)}
    
    def get_conversation_stats(
        self, 
        user_id: Optional[str] = None,
        days_back: int = 30
    ) -> ConversationStats:
        """
        Get statistics about conversation data.
        
        Args:
            user_id: Optional user ID to filter stats
            days_back: Number of days to include in statistics
            
        Returns:
            ConversationStats: Statistics about conversations
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            # Base query
            query = self.db.query(EnhancedChatHistory).filter(
                EnhancedChatHistory.created_at >= start_date
            )
            
            if user_id:
                query = query.filter(EnhancedChatHistory.user_id == user_id)
            
            # Total conversations
            total_conversations = query.count()
            
            # Unique users
            total_users = self.db.query(func.count(func.distinct(EnhancedChatHistory.user_id))).filter(
                EnhancedChatHistory.created_at >= start_date
            ).scalar() or 0
            
            # Average quality score
            avg_quality = self.db.query(func.avg(EnhancedChatHistory.response_quality_score)).filter(
                EnhancedChatHistory.created_at >= start_date,
                EnhancedChatHistory.response_quality_score.isnot(None)
            ).scalar() or 0.0
            
            # Most used tools (simplified - would need more complex query for JSON field)
            # For now, return empty list - can be enhanced later
            most_used_tools = []
            
            # Conversations by date
            conversations_by_date = {}
            
            return ConversationStats(
                total_conversations=total_conversations,
                total_users=total_users,
                average_quality_score=float(avg_quality),
                most_used_tools=most_used_tools,
                conversations_by_date=conversations_by_date
            )
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get conversation stats: {e}")
            return ConversationStats()
    
    def _apply_filters(self, query, filters: ConversationFilter):
        """Apply filter criteria to a query"""
        
        if filters.session_id:
            query = query.filter(EnhancedChatHistory.session_id == filters.session_id)
        
        if filters.start_date:
            query = query.filter(EnhancedChatHistory.created_at >= filters.start_date)
        
        if filters.end_date:
            query = query.filter(EnhancedChatHistory.created_at <= filters.end_date)
        
        if filters.min_quality_score is not None:
            query = query.filter(
                EnhancedChatHistory.response_quality_score >= filters.min_quality_score
            )
        
        if filters.tools_used:
            # Filter by tools used (JSON field contains any of the specified tools)
            for tool in filters.tools_used:
                query = query.filter(
                    EnhancedChatHistory.tools_used.contains([tool])
                )
        
        # Apply ordering
        order_column = getattr(EnhancedChatHistory, filters.order_by, EnhancedChatHistory.created_at)
        if filters.order_direction.lower() == 'asc':
            query = query.order_by(asc(order_column))
        else:
            query = query.order_by(desc(order_column))
        
        # Apply pagination
        query = query.offset(filters.offset).limit(filters.limit)
        
        return query
    
    def _to_conversation_dto(self, db_entry: EnhancedChatHistory) -> ConversationEntryDTO:
        """Convert database entry to DTO"""
        return ConversationEntryDTO(
            session_id=db_entry.session_id,
            user_id=db_entry.user_id,
            user_message=db_entry.user_message,
            bot_response=db_entry.bot_response,
            tools_used=db_entry.tools_used or [],
            tool_performance=db_entry.tool_performance or {},
            context_used=db_entry.context_used or [],
            response_quality_score=db_entry.response_quality_score,
            timestamp=db_entry.created_at
        )
    
    def _create_conversation_summary(self, conversation: EnhancedChatHistory) -> Optional[ConversationSummary]:
        """Create a summary of a conversation for archival"""
        try:
            # Extract key topics and context (simplified implementation)
            key_topics = []
            important_context = {}
            
            # Simple keyword extraction from user message and bot response
            text_content = f"{conversation.user_message} {conversation.bot_response}"
            words = text_content.lower().split()
            
            # Basic topic extraction (can be enhanced with NLP)
            common_topics = ['error', 'help', 'support', 'issue', 'problem', 'question']
            for topic in common_topics:
                if topic in words:
                    key_topics.append(topic)
            
            # Store important context
            if conversation.tools_used:
                important_context['tools_used'] = conversation.tools_used
            
            if conversation.response_quality_score:
                important_context['quality_score'] = conversation.response_quality_score
            
            # Create summary text (first 500 chars of conversation)
            summary_text = f"User: {conversation.user_message[:200]}... Bot: {conversation.bot_response[:200]}..."
            
            return ConversationSummary(
                user_id=conversation.user_id,
                session_id=conversation.session_id,
                summary_text=summary_text,
                key_topics=key_topics,
                important_context=important_context,
                date_range_start=conversation.created_at,
                date_range_end=conversation.created_at
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create conversation summary: {e}")
            return None