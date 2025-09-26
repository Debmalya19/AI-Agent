"""
Unified database models that merge admin dashboard and main backend models.
This module provides a single source of truth for all database entities.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON, Enum, Boolean
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID, ARRAY
from sqlalchemy.orm import relationship
from backend.database import Base
from datetime import datetime, timezone
import enum
import uuid

# Database-agnostic JSON column type
def get_json_column():
    """Return appropriate JSON column type based on database"""
    try:
        # Try to use JSONB for PostgreSQL
        return JSONB
    except:
        # Fall back to JSON for SQLite and other databases
        return JSON

# Unified Enums
class TicketStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"  # Added from admin dashboard
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TicketCategory(enum.Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    GENERAL = "general"
    ACCOUNT = "account"  # Added from admin dashboard
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    BUG = "bug"  # Alias for admin dashboard compatibility

class UserRole(enum.Enum):
    CUSTOMER = "CUSTOMER"
    AGENT = "AGENT"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"

# Unified User Model (extends existing backend User)
class UnifiedUser(Base):
    """Unified user model supporting both customers and admin agents"""
    __tablename__ = "unified_users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    
    # Core fields from backend User model
    user_id = Column(String(50), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    
    # Additional fields from admin dashboard User model
    phone = Column(String(20), nullable=True)
    is_admin = Column(Boolean, default=False)
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Enhanced user management fields
    is_active = Column(Boolean, default=True)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER)
    
    # Timestamps (PostgreSQL optimized)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Migration tracking fields
    legacy_customer_id = Column(Integer, nullable=True)  # Original customer ID from backend
    legacy_admin_user_id = Column(Integer, nullable=True)  # Original admin user ID
    
    # Relationships
    sessions = relationship("UnifiedUserSession", back_populates="user")
    voice_settings = relationship("UnifiedVoiceSettings", back_populates="user", uselist=False)
    voice_analytics = relationship("UnifiedVoiceAnalytics", back_populates="user")
    
    # Ticket relationships
    created_tickets = relationship("UnifiedTicket", foreign_keys="UnifiedTicket.customer_id", back_populates="customer")
    assigned_tickets = relationship("UnifiedTicket", foreign_keys="UnifiedTicket.assigned_agent_id", back_populates="assigned_agent")
    
    # Comment and activity relationships
    ticket_comments = relationship("UnifiedTicketComment", back_populates="author")
    ticket_activities = relationship("UnifiedTicketActivity", back_populates="performed_by")
    
    # Chat relationships
    customer_chat_sessions = relationship("UnifiedChatSession", foreign_keys="UnifiedChatSession.customer_id", back_populates="customer")
    agent_chat_sessions = relationship("UnifiedChatSession", foreign_keys="UnifiedChatSession.agent_id", back_populates="agent")
    chat_messages = relationship("UnifiedChatMessage", back_populates="user")
    
    # Performance and satisfaction relationships
    performance_metrics = relationship("UnifiedPerformanceMetric", back_populates="agent")
    given_satisfaction_ratings = relationship("UnifiedCustomerSatisfaction", foreign_keys="UnifiedCustomerSatisfaction.customer_id", back_populates="customer")
    received_satisfaction_ratings = relationship("UnifiedCustomerSatisfaction", foreign_keys="UnifiedCustomerSatisfaction.agent_id", back_populates="agent")

# Unified Ticket Model (enhanced from both systems)
class UnifiedTicket(Base):
    """Unified ticket model with features from both systems"""
    __tablename__ = 'unified_tickets'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(50), unique=True, index=True, nullable=True)  # External ticket ID
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM)
    category = Column(Enum(TicketCategory), default=TicketCategory.GENERAL)
    
    # Foreign keys
    customer_id = Column(Integer, ForeignKey("unified_users.id"), nullable=True)
    assigned_agent_id = Column(Integer, ForeignKey("unified_users.id"), nullable=True)
    
    # Timestamps (PostgreSQL optimized)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Additional fields
    tags = Column(String(500), nullable=True)
    ticket_metadata = Column(Text, nullable=True)
    
    # Migration tracking fields
    legacy_backend_ticket_id = Column(Integer, nullable=True)  # Original backend ticket ID
    legacy_admin_ticket_id = Column(Integer, nullable=True)  # Original admin dashboard ticket ID
    
    # Relationships
    customer = relationship("UnifiedUser", foreign_keys=[customer_id], back_populates="created_tickets")
    assigned_agent = relationship("UnifiedUser", foreign_keys=[assigned_agent_id], back_populates="assigned_tickets")
    comments = relationship("UnifiedTicketComment", back_populates="ticket", cascade="all, delete-orphan")
    activities = relationship("UnifiedTicketActivity", back_populates="ticket", cascade="all, delete-orphan")
    chat_sessions = relationship("UnifiedChatSession", back_populates="ticket")
    satisfaction_ratings = relationship("UnifiedCustomerSatisfaction", back_populates="ticket")

# Unified Ticket Comment Model
class UnifiedTicketComment(Base):
    """Unified ticket comment model"""
    __tablename__ = 'unified_ticket_comments'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey('unified_tickets.id'), nullable=False)
    author_id = Column(Integer, ForeignKey('unified_users.id'), nullable=True)
    comment = Column(Text, nullable=False)  # Backend uses 'comment', admin uses 'content'
    content = Column(Text, nullable=True)  # For admin dashboard compatibility
    is_internal = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Migration tracking fields
    legacy_backend_comment_id = Column(Integer, nullable=True)
    legacy_admin_comment_id = Column(Integer, nullable=True)

    # Relationships
    ticket = relationship("UnifiedTicket", back_populates="comments")
    author = relationship("UnifiedUser", back_populates="ticket_comments")

# Unified Ticket Activity Model
class UnifiedTicketActivity(Base):
    """Unified ticket activity model"""
    __tablename__ = 'unified_ticket_activities'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey('unified_tickets.id'), nullable=False)
    activity_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    performed_by_id = Column(Integer, ForeignKey('unified_users.id'), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Migration tracking fields
    legacy_backend_activity_id = Column(Integer, nullable=True)
    legacy_admin_activity_id = Column(Integer, nullable=True)
    
    # Relationships
    ticket = relationship("UnifiedTicket", back_populates="activities")
    performed_by = relationship("UnifiedUser", back_populates="ticket_activities")

# Unified User Session Model
class UnifiedUserSession(Base):
    """Unified user session model"""
    __tablename__ = "unified_user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("unified_users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    last_accessed = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    user = relationship("UnifiedUser", back_populates="sessions")

# Chat System Models (from admin dashboard)
class UnifiedChatSession(Base):
    """Unified chat session model"""
    __tablename__ = 'unified_chat_sessions'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('unified_users.id'), nullable=False)
    agent_id = Column(Integer, ForeignKey('unified_users.id'), nullable=True)
    ticket_id = Column(Integer, ForeignKey('unified_tickets.id'), nullable=True)
    status = Column(String(20), default='active')
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Migration tracking
    legacy_admin_session_id = Column(Integer, nullable=True)
    
    # Relationships
    customer = relationship("UnifiedUser", foreign_keys=[customer_id], back_populates="customer_chat_sessions")
    agent = relationship("UnifiedUser", foreign_keys=[agent_id], back_populates="agent_chat_sessions")
    ticket = relationship("UnifiedTicket", back_populates="chat_sessions")
    messages = relationship("UnifiedChatMessage", back_populates="session", cascade="all, delete-orphan")
    satisfaction_ratings = relationship("UnifiedCustomerSatisfaction", back_populates="chat_session")

class UnifiedChatMessage(Base):
    """Unified chat message model"""
    __tablename__ = 'unified_chat_messages'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('unified_chat_sessions.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('unified_users.id'), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Migration tracking
    legacy_admin_message_id = Column(Integer, nullable=True)
    
    # Relationships
    session = relationship("UnifiedChatSession", back_populates="messages")
    user = relationship("UnifiedUser", back_populates="chat_messages")

# Analytics and Performance Models (from admin dashboard)
class UnifiedPerformanceMetric(Base):
    """Unified performance metrics model"""
    __tablename__ = 'unified_performance_metrics'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('unified_users.id'), nullable=True)
    metric_type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    date = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Migration tracking
    legacy_admin_metric_id = Column(Integer, nullable=True)
    
    # Relationships
    agent = relationship("UnifiedUser", back_populates="performance_metrics")

class UnifiedCustomerSatisfaction(Base):
    """Unified customer satisfaction model"""
    __tablename__ = 'unified_customer_satisfaction'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('unified_tickets.id'), nullable=True)
    chat_session_id = Column(Integer, ForeignKey('unified_chat_sessions.id'), nullable=True)
    customer_id = Column(Integer, ForeignKey('unified_users.id'), nullable=False)
    agent_id = Column(Integer, ForeignKey('unified_users.id'), nullable=True)
    rating = Column(Integer, nullable=False)
    feedback = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Migration tracking
    legacy_admin_satisfaction_id = Column(Integer, nullable=True)
    
    # Relationships
    ticket = relationship("UnifiedTicket", back_populates="satisfaction_ratings")
    chat_session = relationship("UnifiedChatSession", back_populates="satisfaction_ratings")
    customer = relationship("UnifiedUser", foreign_keys=[customer_id], back_populates="given_satisfaction_ratings")
    agent = relationship("UnifiedUser", foreign_keys=[agent_id], back_populates="received_satisfaction_ratings")

# Voice Assistant Models (from backend)
class UnifiedVoiceSettings(Base):
    """Unified voice assistant settings"""
    __tablename__ = "unified_voice_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("unified_users.id"), nullable=False, unique=True, index=True)
    auto_play_enabled = Column(Boolean, default=False, nullable=False)
    voice_name = Column(String(100), default="default", nullable=False)
    speech_rate = Column(Float, default=1.0, nullable=False)
    speech_pitch = Column(Float, default=1.0, nullable=False)
    speech_volume = Column(Float, default=1.0, nullable=False)
    language = Column(String(10), default="en-US", nullable=False)
    microphone_sensitivity = Column(Float, default=0.5, nullable=False)
    noise_cancellation = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Migration tracking
    legacy_backend_voice_settings_id = Column(Integer, nullable=True)
    
    # Relationship
    user = relationship("UnifiedUser", back_populates="voice_settings")

class UnifiedVoiceAnalytics(Base):
    """Unified voice assistant analytics"""
    __tablename__ = "unified_voice_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("unified_users.id"), nullable=False, index=True)
    session_id = Column(String(255), index=True)
    action_type = Column(String(50), nullable=False, index=True)
    duration_ms = Column(Integer)
    text_length = Column(Integer)
    accuracy_score = Column(Float)
    error_message = Column(Text)
    analytics_metadata = Column(JSON)  # Database agnostic
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # Migration tracking
    legacy_backend_analytics_id = Column(Integer, nullable=True)
    
    # Relationship
    user = relationship("UnifiedUser", back_populates="voice_analytics")

# Knowledge Base and Support Models (from backend)
class UnifiedKnowledgeEntry(Base):
    """Unified knowledge entry model"""
    __tablename__ = "unified_knowledge_entries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)
    content = Column(Text)
    source = Column(String(255))
    embedding = Column(JSON)  # Database agnostic
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Migration tracking
    legacy_backend_knowledge_id = Column(Integer, nullable=True)

class UnifiedOrder(Base):
    """Unified order model"""
    __tablename__ = "unified_orders"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("unified_users.id"))
    order_date = Column(TIMESTAMP(timezone=True))
    amount = Column(Float)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Migration tracking
    legacy_backend_order_id = Column(Integer, nullable=True)
    
    customer = relationship("UnifiedUser")

class UnifiedSupportIntent(Base):
    """Unified support intent model"""
    __tablename__ = "unified_support_intents"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    intent_id = Column(String(50), unique=True, index=True)
    intent_name = Column(String(255))
    description = Column(Text)
    category = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Migration tracking
    legacy_backend_intent_id = Column(Integer, nullable=True)
    
    responses = relationship("UnifiedSupportResponse", back_populates="intent")

class UnifiedSupportResponse(Base):
    """Unified support response model"""
    __tablename__ = "unified_support_responses"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    intent_id = Column(String(50), ForeignKey("unified_support_intents.intent_id"))
    response_text = Column(Text)
    response_type = Column(String(50))
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Migration tracking
    legacy_backend_response_id = Column(Integer, nullable=True)

    intent = relationship("UnifiedSupportIntent", back_populates="responses")

class UnifiedChatHistory(Base):
    """Unified chat history model (AI conversations)"""
    __tablename__ = "unified_chat_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True)
    user_message = Column(Text)
    bot_response = Column(Text)
    tools_used = Column(JSON)  # Database agnostic
    sources = Column(JSON)  # Database agnostic
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Enhanced fields for integration
    user_id = Column(Integer, ForeignKey("unified_users.id"), nullable=True)  # Link to user if authenticated
    ticket_id = Column(Integer, ForeignKey("unified_tickets.id"), nullable=True)  # Link to ticket if created
    
    # Migration tracking
    legacy_backend_chat_id = Column(Integer, nullable=True)
    
    # Relationships
    user = relationship("UnifiedUser")
    ticket = relationship("UnifiedTicket")

# Diagnostic Error Logging Model
class DiagnosticErrorLog(Base):
    """Database model for storing diagnostic errors"""
    __tablename__ = "diagnostic_error_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Error classification
    category = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    error_code = Column(String(50), index=True)
    
    # Error content
    message = Column(Text, nullable=False)
    details = Column(Text)  # JSON string
    suggested_actions = Column(Text)  # JSON string
    related_errors = Column(Text)  # JSON string
    
    # Context information
    user_id = Column(String(255), index=True)
    session_id = Column(String(255), index=True)
    request_id = Column(String(255), index=True)
    user_agent = Column(Text)
    ip_address = Column(String(45))
    referer = Column(Text)
    endpoint = Column(String(255))
    method = Column(String(10))
    
    # Metadata
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        import json
        return {
            'id': self.id,
            'category': self.category,
            'severity': self.severity,
            'error_code': self.error_code,
            'message': self.message,
            'details': json.loads(self.details) if self.details else {},
            'suggested_actions': json.loads(self.suggested_actions) if self.suggested_actions else [],
            'related_errors': json.loads(self.related_errors) if self.related_errors else [],
            'context': {
                'user_id': self.user_id,
                'session_id': self.session_id,
                'request_id': self.request_id,
                'user_agent': self.user_agent,
                'ip_address': self.ip_address,
                'referer': self.referer,
                'endpoint': self.endpoint,
                'method': self.method
            },
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'resolved': self.resolved,
            'resolution_notes': self.resolution_notes
        }