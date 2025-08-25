"""
Enhanced database models for memory layer functionality.
These models extend the existing database schema to support
persistent conversation memory, context caching, and tool analytics.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean, Index
from sqlalchemy.orm import relationship
from backend.database import Base
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
import json
import re
import hashlib

class EnhancedChatHistory(Base):
    """Enhanced chat history with metadata and tool performance tracking"""
    __tablename__ = "enhanced_chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    user_message = Column(Text, nullable=True)  # Made nullable for encrypted storage
    bot_response = Column(Text, nullable=True)  # Made nullable for encrypted storage
    # Encrypted fields for sensitive data
    user_message_encrypted = Column(JSON)  # Encrypted user message with metadata
    bot_response_encrypted = Column(JSON)  # Encrypted bot response with metadata
    tools_used = Column(JSON)  # List of tool names used
    tool_performance = Column(JSON)  # Dict of tool_name -> performance metrics
    context_used = Column(JSON)  # List of context entries used
    response_quality_score = Column(Float)  # Quality score for the response
    semantic_features = Column(JSON)  # Extracted semantic features for similarity
    # Security and privacy fields
    data_classification = Column(String(50), default="internal")  # public, internal, confidential, restricted
    retention_policy = Column(String(100))  # Retention policy identifier
    deleted_at = Column(DateTime)  # Soft delete timestamp
    anonymized_at = Column(DateTime)  # Anonymization timestamp
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    context_cache_entries = relationship("MemoryContextCache", 
                                       primaryjoin="and_(EnhancedChatHistory.user_id == MemoryContextCache.user_id, "
                                                  "EnhancedChatHistory.session_id == MemoryContextCache.cache_key)",
                                       foreign_keys="MemoryContextCache.user_id",
                                       viewonly=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_enhanced_chat_user_session', 'user_id', 'session_id'),
        Index('idx_enhanced_chat_created', 'created_at'),
        Index('idx_enhanced_chat_quality', 'response_quality_score'),
    )
    
    def to_conversation_entry(self) -> 'ConversationEntry':
        """Convert to ConversationEntry DTO"""
        return ConversationEntry(
            session_id=self.session_id,
            user_id=self.user_id,
            user_message=self.user_message,
            bot_response=self.bot_response,
            tools_used=self.tools_used or [],
            tool_performance=self.tool_performance or {},
            context_used=self.context_used or [],
            response_quality_score=self.response_quality_score,
            timestamp=self.created_at
        )

class MemoryContextCache(Base):
    """Cache for frequently accessed context data with relevance scoring"""
    __tablename__ = "memory_context_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(50), index=True)
    context_data = Column(JSON, nullable=True)  # The actual context content (unencrypted)
    context_data_encrypted = Column(JSON)  # Encrypted context data with metadata
    context_type = Column(String(50), nullable=False, index=True)  # conversation, tool_usage, etc.
    relevance_score = Column(Float, index=True)  # Relevance score for ranking
    # Security and privacy fields
    data_classification = Column(String(50), default="internal")  # public, internal, confidential, restricted
    access_control = Column(JSON)  # Access control metadata
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_context_cache_user_type', 'user_id', 'context_type'),
        Index('idx_context_cache_expires', 'expires_at'),
        Index('idx_context_cache_relevance', 'relevance_score'),
    )
    
    def to_context_entry(self) -> 'ContextEntry':
        """Convert to ContextEntry DTO"""
        return ContextEntry(
            content=str(self.context_data.get('content', '')),
            source=str(self.context_data.get('source', 'cache')),
            relevance_score=self.relevance_score or 0.0,
            context_type=self.context_type,
            timestamp=self.created_at,
            metadata=self.context_data.get('metadata', {})
        )
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return datetime.now(timezone.utc) > self.expires_at

class ToolUsageMetrics(Base):
    """Metrics for tool usage patterns and performance analysis"""
    __tablename__ = "tool_usage_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    tool_name = Column(String(100), nullable=False, index=True)
    query_type = Column(String(50), index=True)  # Type of query that triggered the tool
    query_hash = Column(String(64), index=True)  # Hash of similar queries for grouping
    success_rate = Column(Float, default=0.0)  # Success rate percentage
    average_response_time = Column(Float, default=0.0)  # Average response time in seconds
    response_quality_score = Column(Float, default=0.0)  # Average quality score
    usage_count = Column(Integer, default=1)  # Number of times used
    last_used = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_tool_metrics_name_type', 'tool_name', 'query_type'),
        Index('idx_tool_metrics_success', 'success_rate'),
        Index('idx_tool_metrics_quality', 'response_quality_score'),
        Index('idx_tool_metrics_usage', 'usage_count'),
    )
    
    def to_tool_recommendation(self, reason: str = "Based on historical performance") -> 'ToolRecommendation':
        """Convert to ToolRecommendation DTO"""
        # Calculate confidence based on success rate and usage count
        confidence = min(1.0, (self.success_rate * 0.7) + (min(self.usage_count / 10, 1.0) * 0.3))
        
        return ToolRecommendation(
            tool_name=self.tool_name,
            confidence_score=confidence,
            reason=reason,
            expected_performance=self.response_quality_score or 0.5
        )
    
    def update_metrics(self, success: bool, response_time: float, quality_score: float) -> None:
        """Update metrics with new usage data"""
        # Update success rate
        total_attempts = self.usage_count
        current_successes = self.success_rate * total_attempts
        new_successes = current_successes + (1 if success else 0)
        self.success_rate = new_successes / (total_attempts + 1)
        
        # Update average response time
        self.average_response_time = ((self.average_response_time * total_attempts) + response_time) / (total_attempts + 1)
        
        # Update average quality score
        if quality_score is not None:
            current_quality_total = self.response_quality_score * total_attempts
            self.response_quality_score = (current_quality_total + quality_score) / (total_attempts + 1)
        
        # Update usage count and last used
        self.usage_count += 1
        self.last_used = datetime.now(timezone.utc)

class ConversationSummary(Base):
    """Summaries of conversations for long-term memory and context"""
    __tablename__ = "conversation_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    session_id = Column(String(255), index=True)
    summary_text = Column(Text, nullable=False)
    key_topics = Column(JSON)  # List of key topics discussed
    important_context = Column(JSON)  # Important context to remember
    date_range_start = Column(DateTime, index=True)
    date_range_end = Column(DateTime, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_conversation_summary_user', 'user_id'),
        Index('idx_conversation_summary_date_range', 'date_range_start', 'date_range_end'),
    )

class MemoryConfiguration(Base):
    """Configuration settings for memory layer behavior"""
    __tablename__ = "memory_configuration"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(JSON, nullable=False)  # Flexible JSON configuration
    config_type = Column(String(50), nullable=False)  # retention, performance, etc.
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class MemoryHealthMetrics(Base):
    """Health and performance metrics for the memory system"""
    __tablename__ = "memory_health_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20))  # seconds, bytes, count, etc.
    metric_category = Column(String(50), index=True)  # performance, storage, quality
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_health_metrics_name_time', 'metric_name', 'recorded_at'),
        Index('idx_health_metrics_category', 'metric_category'),
    )

class EnhancedUserSession(Base):
    """Enhanced user session management with security features"""
    __tablename__ = "enhanced_user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    session_token_hash = Column(String(128))  # Hashed session token for validation
    is_active = Column(Boolean, default=True, index=True)
    ip_address = Column(String(45))  # IPv4 or IPv6 address
    user_agent = Column(Text)  # Browser/client user agent
    session_metadata = Column(JSON)  # Additional session metadata
    last_activity = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    expires_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_enhanced_user_sessions_user_active', 'user_id', 'is_active'),
        Index('idx_enhanced_user_sessions_expires', 'expires_at'),
        Index('idx_enhanced_user_sessions_activity', 'last_activity'),
    )

class DataProcessingConsent(Base):
    """GDPR consent records for data processing"""
    __tablename__ = "data_processing_consent"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    consent_id = Column(String(255), unique=True, nullable=False, index=True)
    purpose = Column(String(100), nullable=False, index=True)  # Purpose of data processing
    consent_given = Column(Boolean, nullable=False)
    consent_timestamp = Column(DateTime, nullable=False)
    consent_method = Column(String(50))  # web_form, api, etc.
    consent_version = Column(String(20))  # Version of privacy policy/terms
    withdrawal_timestamp = Column(DateTime)  # When consent was withdrawn
    legal_basis = Column(String(50), default="consent")  # GDPR legal basis
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_consent_user_purpose', 'user_id', 'purpose'),
        Index('idx_consent_given', 'consent_given'),
        Index('idx_consent_timestamp', 'consent_timestamp'),
    )

class DataSubjectRights(Base):
    """GDPR data subject rights requests"""
    __tablename__ = "data_subject_rights"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    request_type = Column(String(50), nullable=False, index=True)  # access, rectification, erasure, etc.
    status = Column(String(50), default="pending", index=True)  # pending, in_progress, completed, rejected
    requested_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    request_details = Column(JSON)  # Additional request details
    response_data = Column(JSON)  # Response data (for access requests)
    notes = Column(Text)  # Processing notes
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_dsr_user_type', 'user_id', 'request_type'),
        Index('idx_dsr_status', 'status'),
        Index('idx_dsr_requested', 'requested_at'),
    )

# Data Transfer Objects (DTOs) for type safety and validation
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import re

@dataclass
class ConversationEntry:
    """Data transfer object for conversation entries with validation"""
    session_id: str
    user_id: str
    user_message: str
    bot_response: str
    tools_used: List[str] = field(default_factory=list)
    tool_performance: Dict[str, float] = field(default_factory=dict)
    context_used: List[str] = field(default_factory=list)
    response_quality_score: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate data after initialization"""
        self.validate()
    
    def validate(self) -> None:
        """Validate conversation entry data"""
        if not self.session_id or not isinstance(self.session_id, str):
            raise ValueError("session_id must be a non-empty string")
        
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError("user_id must be a non-empty string")
        
        if not self.user_message or not isinstance(self.user_message, str):
            raise ValueError("user_message must be a non-empty string")
        
        if not self.bot_response or not isinstance(self.bot_response, str):
            raise ValueError("bot_response must be a non-empty string")
        
        if self.response_quality_score is not None:
            if not isinstance(self.response_quality_score, (int, float)):
                raise ValueError("response_quality_score must be a number")
            if not 0.0 <= self.response_quality_score <= 1.0:
                raise ValueError("response_quality_score must be between 0.0 and 1.0")
        
        if not isinstance(self.tools_used, list):
            raise ValueError("tools_used must be a list")
        
        if not isinstance(self.tool_performance, dict):
            raise ValueError("tool_performance must be a dictionary")
        
        if not isinstance(self.context_used, list):
            raise ValueError("context_used must be a list")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'user_message': self.user_message,
            'bot_response': self.bot_response,
            'tools_used': self.tools_used,
            'tool_performance': self.tool_performance,
            'context_used': self.context_used,
            'response_quality_score': self.response_quality_score,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationEntry':
        """Create instance from dictionary"""
        timestamp = None
        if data.get('timestamp'):
            if isinstance(data['timestamp'], str):
                timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            elif isinstance(data['timestamp'], datetime):
                timestamp = data['timestamp']
        
        return cls(
            session_id=data['session_id'],
            user_id=data['user_id'],
            user_message=data['user_message'],
            bot_response=data['bot_response'],
            tools_used=data.get('tools_used', []),
            tool_performance=data.get('tool_performance', {}),
            context_used=data.get('context_used', []),
            response_quality_score=data.get('response_quality_score'),
            timestamp=timestamp or datetime.now(timezone.utc)
        )

@dataclass
class ContextEntry:
    """Data transfer object for context entries with validation"""
    content: str
    source: str
    relevance_score: float
    context_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate data after initialization"""
        self.validate()
    
    def validate(self) -> None:
        """Validate context entry data"""
        if not self.content or not isinstance(self.content, str):
            raise ValueError("content must be a non-empty string")
        
        if not self.source or not isinstance(self.source, str):
            raise ValueError("source must be a non-empty string")
        
        if not isinstance(self.relevance_score, (int, float)):
            raise ValueError("relevance_score must be a number")
        
        if not 0.0 <= self.relevance_score <= 1.0:
            raise ValueError("relevance_score must be between 0.0 and 1.0")
        
        if not self.context_type or not isinstance(self.context_type, str):
            raise ValueError("context_type must be a non-empty string")
        
        # Validate context_type against allowed values
        allowed_types = ['conversation', 'tool_usage', 'document', 'summary', 'user_preference']
        if self.context_type not in allowed_types:
            raise ValueError(f"context_type must be one of: {', '.join(allowed_types)}")
        
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dictionary")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'content': self.content,
            'source': self.source,
            'relevance_score': self.relevance_score,
            'context_type': self.context_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextEntry':
        """Create instance from dictionary"""
        timestamp = None
        if data.get('timestamp'):
            if isinstance(data['timestamp'], str):
                timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            elif isinstance(data['timestamp'], datetime):
                timestamp = data['timestamp']
        
        return cls(
            content=data['content'],
            source=data['source'],
            relevance_score=data['relevance_score'],
            context_type=data['context_type'],
            timestamp=timestamp or datetime.now(timezone.utc),
            metadata=data.get('metadata', {})
        )

@dataclass
class ToolRecommendation:
    """Data transfer object for tool recommendations with validation"""
    tool_name: str
    confidence_score: float
    reason: str
    expected_performance: float
    
    def __post_init__(self):
        """Validate data after initialization"""
        self.validate()
    
    def validate(self) -> None:
        """Validate tool recommendation data"""
        if not self.tool_name or not isinstance(self.tool_name, str):
            raise ValueError("tool_name must be a non-empty string")
        
        # Validate tool name format (alphanumeric, underscores, hyphens)
        if not re.match(r'^[a-zA-Z0-9_-]+$', self.tool_name):
            raise ValueError("tool_name must contain only alphanumeric characters, underscores, and hyphens")
        
        if not isinstance(self.confidence_score, (int, float)):
            raise ValueError("confidence_score must be a number")
        
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        
        if not self.reason or not isinstance(self.reason, str):
            raise ValueError("reason must be a non-empty string")
        
        if not isinstance(self.expected_performance, (int, float)):
            raise ValueError("expected_performance must be a number")
        
        if not 0.0 <= self.expected_performance <= 1.0:
            raise ValueError("expected_performance must be between 0.0 and 1.0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'tool_name': self.tool_name,
            'confidence_score': self.confidence_score,
            'reason': self.reason,
            'expected_performance': self.expected_performance
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolRecommendation':
        """Create instance from dictionary"""
        return cls(
            tool_name=data['tool_name'],
            confidence_score=data['confidence_score'],
            reason=data['reason'],
            expected_performance=data['expected_performance']
        )

# Legacy DTO classes for backward compatibility
class ConversationEntryDTO(ConversationEntry):
    """Legacy DTO class - use ConversationEntry instead"""
    pass

class ContextEntryDTO(ContextEntry):
    """Legacy DTO class - use ContextEntry instead"""
    pass

class ToolRecommendationDTO(ToolRecommendation):
    """Legacy DTO class - use ToolRecommendation instead"""
    pass

# Utility functions for model operations
def create_enhanced_chat_entry(
    session_id: str,
    user_id: str,
    user_message: str,
    bot_response: str,
    **kwargs
) -> EnhancedChatHistory:
    """Create an enhanced chat history entry with optional metadata"""
    return EnhancedChatHistory(
        session_id=session_id,
        user_id=user_id,
        user_message=user_message,
        bot_response=bot_response,
        tools_used=kwargs.get('tools_used'),
        tool_performance=kwargs.get('tool_performance'),
        context_used=kwargs.get('context_used'),
        response_quality_score=kwargs.get('response_quality_score'),
        semantic_features=kwargs.get('semantic_features')
    )

def create_context_cache_entry(
    cache_key: str,
    context_data: Dict[str, Any],
    context_type: str,
    expires_at: datetime,
    user_id: Optional[str] = None,
    relevance_score: Optional[float] = None
) -> MemoryContextCache:
    """Create a memory context cache entry"""
    return MemoryContextCache(
        cache_key=cache_key,
        user_id=user_id,
        context_data=context_data,
        context_type=context_type,
        relevance_score=relevance_score or 0.0,
        expires_at=expires_at
    )

def create_tool_usage_metric(
    tool_name: str,
    query_type: Optional[str] = None,
    query_hash: Optional[str] = None,
    **kwargs
) -> ToolUsageMetrics:
    """Create a tool usage metrics entry"""
    return ToolUsageMetrics(
        tool_name=tool_name,
        query_type=query_type,
        query_hash=query_hash,
        success_rate=kwargs.get('success_rate', 0.0),
        average_response_time=kwargs.get('average_response_time', 0.0),
        response_quality_score=kwargs.get('response_quality_score', 0.0),
        usage_count=kwargs.get('usage_count', 1)
    )

# Additional utility functions for data processing
def generate_query_hash(query: str) -> str:
    """Generate a hash for similar query grouping"""
    # Normalize query for consistent hashing
    normalized = re.sub(r'\s+', ' ', query.lower().strip())
    return hashlib.md5(normalized.encode()).hexdigest()[:16]

def validate_json_serializable(data: Any) -> bool:
    """Check if data is JSON serializable"""
    try:
        json.dumps(data)
        return True
    except (TypeError, ValueError):
        return False

def sanitize_for_storage(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize data for database storage"""
    sanitized = {}
    for key, value in data.items():
        if validate_json_serializable(value):
            sanitized[key] = value
        else:
            # Convert non-serializable objects to string representation
            sanitized[key] = str(value)
    return sanitized

def create_conversation_summary(
    user_id: str,
    session_id: str,
    summary_text: str,
    key_topics: List[str],
    important_context: Dict[str, Any],
    date_range_start: datetime,
    date_range_end: datetime
) -> ConversationSummary:
    """Create a conversation summary entry"""
    return ConversationSummary(
        user_id=user_id,
        session_id=session_id,
        summary_text=summary_text,
        key_topics=key_topics,
        important_context=sanitize_for_storage(important_context),
        date_range_start=date_range_start,
        date_range_end=date_range_end
    )

def batch_create_entries(entries: List[Union[ConversationEntry, ContextEntry]], 
                        session) -> List[Union[EnhancedChatHistory, MemoryContextCache]]:
    """Batch create database entries from DTOs"""
    db_entries = []
    
    for entry in entries:
        if isinstance(entry, ConversationEntry):
            db_entry = EnhancedChatHistory(
                session_id=entry.session_id,
                user_id=entry.user_id,
                user_message=entry.user_message,
                bot_response=entry.bot_response,
                tools_used=entry.tools_used,
                tool_performance=entry.tool_performance,
                context_used=entry.context_used,
                response_quality_score=entry.response_quality_score,
                created_at=entry.timestamp
            )
            db_entries.append(db_entry)
        elif isinstance(entry, ContextEntry):
            # Create cache entry with appropriate expiration
            expires_at = entry.timestamp + timedelta(hours=24)  # Default 24 hour expiration
            cache_key = f"{entry.source}:{generate_query_hash(entry.content)}"
            
            db_entry = MemoryContextCache(
                cache_key=cache_key,
                context_data={
                    'content': entry.content,
                    'source': entry.source,
                    'metadata': entry.metadata
                },
                context_type=entry.context_type,
                relevance_score=entry.relevance_score,
                expires_at=expires_at,
                created_at=entry.timestamp
            )
            db_entries.append(db_entry)
    
    # Add all entries to session
    session.add_all(db_entries)
    return db_entries

# Data validation schemas
class ValidationError(Exception):
    """Custom exception for data validation errors"""
    pass

def validate_conversation_data(data: Dict[str, Any]) -> None:
    """Validate conversation data before processing"""
    required_fields = ['session_id', 'user_id', 'user_message', 'bot_response']
    
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValidationError(f"Missing required field: {field}")
    
    if 'response_quality_score' in data:
        score = data['response_quality_score']
        if score is not None and (not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0):
            raise ValidationError("response_quality_score must be between 0.0 and 1.0")

def validate_context_data(data: Dict[str, Any]) -> None:
    """Validate context data before processing"""
    required_fields = ['content', 'source', 'relevance_score', 'context_type']
    
    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValidationError(f"Missing required field: {field}")
    
    score = data['relevance_score']
    if not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0:
        raise ValidationError("relevance_score must be between 0.0 and 1.0")
    
    allowed_types = ['conversation', 'tool_usage', 'document', 'summary', 'user_preference']
    if data['context_type'] not in allowed_types:
        raise ValidationError(f"context_type must be one of: {', '.join(allowed_types)}")

def validate_tool_recommendation_data(data: Dict[str, Any]) -> None:
    """Validate tool recommendation data before processing"""
    required_fields = ['tool_name', 'confidence_score', 'reason', 'expected_performance']
    
    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValidationError(f"Missing required field: {field}")
    
    # Validate tool name format
    if not re.match(r'^[a-zA-Z0-9_-]+$', data['tool_name']):
        raise ValidationError("tool_name must contain only alphanumeric characters, underscores, and hyphens")
    
    # Validate score ranges
    for score_field in ['confidence_score', 'expected_performance']:
        score = data[score_field]
        if not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0:
            raise ValidationError(f"{score_field} must be between 0.0 and 1.0")