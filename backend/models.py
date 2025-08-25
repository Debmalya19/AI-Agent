from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON, Enum, Boolean
from sqlalchemy.orm import relationship
from backend.database import Base
from datetime import datetime
import enum

# Import memory layer models
from backend.memory_models import (
    EnhancedChatHistory,
    MemoryContextCache,
    ToolUsageMetrics,
    ConversationSummary,
    MemoryConfiguration,
    MemoryHealthMetrics,
    ConversationEntry,
    ContextEntry,
    ToolRecommendation,
    ConversationEntryDTO,
    ContextEntryDTO,
    ToolRecommendationDTO,
    create_enhanced_chat_entry,
    create_context_cache_entry,
    create_tool_usage_metric,
    generate_query_hash,
    validate_json_serializable,
    sanitize_for_storage,
    create_conversation_summary,
    batch_create_entries,
    ValidationError,
    validate_conversation_data,
    validate_context_data,
    validate_tool_recommendation_data
)

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # Additional fields
    tags = Column(String(500), nullable=True)
    ticket_metadata = Column(Text, nullable=True)
    
    # Relationships
    customer = relationship("Customer", foreign_keys=[customer_id], back_populates="tickets")
    assigned_agent = relationship("Customer", foreign_keys=[assigned_agent_id], back_populates="assigned_tickets")

class TicketComment(Base):
    __tablename__ = 'ticket_comments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    author_id = Column(Integer, ForeignKey('customers.id'), nullable=True)
    comment = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
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
    created_at = Column(DateTime, default=datetime.utcnow)
    
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
    created_at = Column(DateTime, default=datetime.utcnow)
    
    customer = relationship("Customer", back_populates="orders")

class SupportIntent(Base):
    __tablename__ = "support_intents"
    
    id = Column(Integer, primary_key=True, index=True)
    intent_id = Column(String(50), unique=True, index=True)
    intent_name = Column(String(255))
    description = Column(Text)
    category = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class SupportResponse(Base):
    __tablename__ = "support_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    intent_id = Column(String(50), ForeignKey("support_intents.intent_id"))
    response_text = Column(Text)
    response_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    intent = relationship("SupportIntent", back_populates="responses")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True)
    user_message = Column(Text)
    bot_response = Column(Text)
    tools_used = Column(JSON)
    sources = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="sessions")

# Add relationships
Customer.orders = relationship("Order", back_populates="customer")
Customer.tickets = relationship("Ticket", foreign_keys="Ticket.customer_id", back_populates="customer")
Customer.assigned_tickets = relationship("Ticket", foreign_keys="Ticket.assigned_agent_id", back_populates="assigned_agent")
SupportIntent.responses = relationship("SupportResponse", back_populates="intent")
Ticket.comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")
Ticket.activities = relationship("TicketActivity", back_populates="ticket", cascade="all, delete-orphan")
User.sessions = relationship("UserSession", back_populates="user")
