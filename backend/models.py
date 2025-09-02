from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON, Enum, Boolean
from sqlalchemy.orm import relationship
from backend.database import Base
from datetime import datetime, timezone
import enum

# Memory layer models are imported directly where needed to avoid circular imports
# and duplicate model registration in SQLAlchemy

class TicketStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
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
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"

class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)
    content = Column(Text)
    source = Column(String(255))
    embedding = Column(JSON)  # Store vector embeddings
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, unique=True, index=True)
    name = Column(String(255))
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(50))
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Ticket relationships
    tickets = relationship("Ticket", foreign_keys="Ticket.customer_id", back_populates="customer")
    assigned_tickets = relationship("Ticket", foreign_keys="Ticket.assigned_agent_id", back_populates="assigned_agent")
    orders = relationship("Order", back_populates="customer")

class Ticket(Base):
    __tablename__ = 'tickets'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM)
    category = Column(Enum(TicketCategory), default=TicketCategory.GENERAL)
    
    # Foreign keys
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    assigned_agent_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)
    
    # Additional fields
    tags = Column(String(500), nullable=True)
    ticket_metadata = Column(Text, nullable=True)
    
    # Relationships
    customer = relationship("Customer", foreign_keys=[customer_id], back_populates="tickets")
    assigned_agent = relationship("Customer", foreign_keys=[assigned_agent_id], back_populates="assigned_tickets")
    comments = relationship("TicketComment", back_populates="ticket")
    activities = relationship("TicketActivity", back_populates="ticket")

class TicketComment(Base):
    __tablename__ = 'ticket_comments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    author_id = Column(Integer, ForeignKey('customers.id'), nullable=True)
    comment = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("Customer")

class TicketActivity(Base):
    __tablename__ = 'ticket_activities'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    activity_type = Column(String(50), nullable=False)  # status_change, comment_added, assigned, etc.
    description = Column(Text, nullable=False)
    performed_by_id = Column(Integer, ForeignKey('customers.id'), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    ticket = relationship("Ticket", back_populates="activities")
    performed_by = relationship("Customer")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"))
    order_date = Column(DateTime)
    amount = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    customer = relationship("Customer", back_populates="orders")

class SupportIntent(Base):
    __tablename__ = "support_intents"
    
    id = Column(Integer, primary_key=True, index=True)
    intent_id = Column(String(50), unique=True, index=True)
    intent_name = Column(String(255))
    description = Column(Text)
    category = Column(String(100))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    responses = relationship("SupportResponse", back_populates="intent")

class SupportResponse(Base):
    __tablename__ = "support_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    intent_id = Column(String(50), ForeignKey("support_intents.intent_id"))
    response_text = Column(Text)
    response_type = Column(String(50))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    intent = relationship("SupportIntent", back_populates="responses")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True)
    user_message = Column(Text)
    bot_response = Column(Text)
    tools_used = Column(JSON)
    sources = Column(JSON)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    sessions = relationship("UserSession", back_populates="user")
    voice_settings = relationship("VoiceSettings", back_populates="user", uselist=False)
    voice_analytics = relationship("VoiceAnalytics", back_populates="user")

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    last_accessed = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="sessions")

class VoiceSettings(Base):
    """Voice assistant settings for users"""
    __tablename__ = "voice_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, unique=True, index=True)
    auto_play_enabled = Column(Boolean, default=False, nullable=False)
    voice_name = Column(String(100), default="default", nullable=False)
    speech_rate = Column(Float, default=1.0, nullable=False)
    speech_pitch = Column(Float, default=1.0, nullable=False)
    speech_volume = Column(Float, default=1.0, nullable=False)
    language = Column(String(10), default="en-US", nullable=False)
    microphone_sensitivity = Column(Float, default=0.5, nullable=False)
    noise_cancellation = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="voice_settings")


class VoiceAnalytics(Base):
    """Voice assistant usage analytics"""
    __tablename__ = "voice_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    session_id = Column(String(255), index=True)
    action_type = Column(String(50), nullable=False, index=True)  # stt_start, stt_complete, tts_start, etc.
    duration_ms = Column(Integer)
    text_length = Column(Integer)
    accuracy_score = Column(Float)
    error_message = Column(Text)
    analytics_metadata = Column(JSON)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # Relationship
    user = relationship("User", back_populates="voice_analytics")


# Note: Relationships are now defined within their respective class definitions
# to avoid SQLAlchemy 2.0 deprecation warnings about duplicate attribute assignments
