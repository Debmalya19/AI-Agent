from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum
from .models import db, User
import os
import sys

# Add the parent directory to sys.path to allow importing from ai-agent backend
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)  # Insert at beginning to prioritize root backend

# Try to import ai-agent backend models
try:
    import importlib.util
    # Load database module first as models depend on it
    root_backend_database_path = os.path.join(parent_dir, "backend", "database.py")
    spec_db = importlib.util.spec_from_file_location("root_backend_database", root_backend_database_path)
    root_backend_database = importlib.util.module_from_spec(spec_db)
    spec_db.loader.exec_module(root_backend_database)

    root_backend_models_path = os.path.join(parent_dir, "backend", "models.py")
    spec = importlib.util.spec_from_file_location("root_backend_models", root_backend_models_path)
    root_backend_models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(root_backend_models)
    print(f"Imported backend.models from: {root_backend_models.__file__}")
    AIAgentTicketStatus = root_backend_models.TicketStatus
    AIAgentTicketPriority = root_backend_models.TicketPriority
    AIAgentTicketCategory = root_backend_models.TicketCategory
    AI_AGENT_MODELS_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not import ai-agent backend models: {e}")
    # Define fallback enums if import fails
    import enum
    class AIAgentTicketStatus(enum.Enum):
        OPEN = "open"
        IN_PROGRESS = "in_progress"
        RESOLVED = "resolved"
        CLOSED = "closed"

    class AIAgentTicketPriority(enum.Enum):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"

    class AIAgentTicketCategory(enum.Enum):
        TECHNICAL = "technical"
        BILLING = "billing"
        GENERAL = "general"
        FEATURE_REQUEST = "feature_request"
        BUG_REPORT = "bug_report"

    AI_AGENT_MODELS_AVAILABLE = False

# Enums for ticket properties
class TicketStatus(Enum):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    PENDING = 'pending'
    RESOLVED = 'resolved'
    CLOSED = 'closed'

class TicketPriority(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

class TicketCategory(Enum):
    TECHNICAL = 'technical'
    BILLING = 'billing'
    ACCOUNT = 'account'
    GENERAL = 'general'
    FEATURE_REQUEST = 'feature_request'
    BUG = 'bug'

# Ticket Management Models
class Ticket(db.Model):
    """Ticket model for customer support requests"""
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(TicketStatus), default=TicketStatus.OPEN)
    priority = db.Column(db.Enum(TicketPriority), default=TicketPriority.MEDIUM)
    category = db.Column(db.Enum(TicketCategory), default=TicketCategory.GENERAL)
    
    # Foreign keys
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_agent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # Integration field to track sync with ai-agent backend
    ai_agent_ticket_id = db.Column(db.Integer, nullable=True)
    
    # Relationships
    customer = db.relationship('User', foreign_keys=[customer_id], overlaps="tickets")
    assigned_agent = db.relationship('User', foreign_keys=[assigned_agent_id], overlaps="assigned_tickets")
    comments = db.relationship('TicketComment', backref='ticket', lazy=True, cascade='all, delete-orphan')
    activities = db.relationship('TicketActivity', backref='ticket', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Ticket {self.id}: {self.title}'
    
    def to_dict(self):
        """Convert ticket object to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'priority': self.priority.value,
            'category': self.category.value,
            'customer_id': self.customer_id,
            'customer_name': self.customer.username if self.customer else None,
            'assigned_agent_id': self.assigned_agent_id,
            'assigned_agent_name': self.assigned_agent.username if self.assigned_agent else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'comments_count': len(self.comments),
            'ai_agent_ticket_id': self.ai_agent_ticket_id
        }

class TicketComment(db.Model):
    """Comments on support tickets"""
    __tablename__ = 'ticket_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)  # Internal notes visible only to agents
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Integration field to track sync with ai-agent backend
    ai_agent_comment_id = db.Column(db.Integer, nullable=True)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('ticket_comments', lazy=True), overlaps="comments")
    
    def __repr__(self):
        return f'<TicketComment {self.id} for Ticket {self.ticket_id}'
    
    def to_dict(self):
        """Convert comment object to dictionary"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'user_id': self.user_id,
            'user_name': self.user.username,
            'content': self.content,
            'is_internal': self.is_internal,
            'created_at': self.created_at.isoformat(),
            'ai_agent_comment_id': self.ai_agent_comment_id
        }

class TicketActivity(db.Model):
    """Activity log for tickets"""
    __tablename__ = 'ticket_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # created, updated, commented, assigned, etc.
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Integration field to track sync with ai-agent backend
    ai_agent_activity_id = db.Column(db.Integer, nullable=True)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('ticket_activities', lazy=True), overlaps="activities")
    
    def __repr__(self):
        return f'<TicketActivity {self.id} for Ticket {self.ticket_id}'
    
    def to_dict(self):
        """Convert activity object to dictionary"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'user_id': self.user_id,
            'user_name': self.user.username,
            'activity_type': self.activity_type,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'ai_agent_activity_id': self.ai_agent_activity_id
        }

class ChatSession(db.Model):
    """Real-time chat session between customer and agent"""
    __tablename__ = 'chat_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Can be null if not assigned yet
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=True)  # Can be linked to a ticket
    status = db.Column(db.String(20), default='active')  # active, closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    customer = db.relationship('User', foreign_keys=[customer_id], backref=db.backref('customer_chats', lazy=True))
    agent = db.relationship('User', foreign_keys=[agent_id], backref=db.backref('agent_chats', lazy=True))
    ticket = db.relationship('Ticket', backref=db.backref('chat_sessions', lazy=True))
    messages = db.relationship('ChatMessage', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ChatSession {self.id} between {self.customer_id} and {self.agent_id}'
    
    def to_dict(self):
        """Convert chat session object to dictionary"""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'customer_name': self.customer.username,
            'agent_id': self.agent_id,
            'agent_name': self.agent.username if self.agent else None,
            'ticket_id': self.ticket_id,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'messages_count': len(self.messages)
        }

class ChatMessage(db.Model):
    """Message in a chat session"""
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Sender (customer or agent)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('chat_messages', lazy=True))
    
    def __repr__(self):
        return f'<ChatMessage {self.id} in Session {self.session_id}'
    
    def to_dict(self):
        """Convert chat message object to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'user_name': self.user.username,
            'is_agent': self.user.is_admin,
            'content': self.content,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }

# Analytics and Reporting Models
class PerformanceMetric(db.Model):
    """Performance metrics for agents and system"""
    __tablename__ = 'performance_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Can be null for system-wide metrics
    metric_type = db.Column(db.String(50), nullable=False)  # response_time, resolution_time, tickets_resolved, etc.
    value = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    agent = db.relationship('User', backref=db.backref('performance_metrics', lazy=True))
    
    def __repr__(self):
        return f'<PerformanceMetric {self.id} for Agent {self.agent_id}'
    
    def to_dict(self):
        """Convert performance metric object to dictionary"""
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'agent_name': self.agent.username if self.agent else 'System',
            'metric_type': self.metric_type,
            'value': self.value,
            'date': self.date.isoformat(),
            'created_at': self.created_at.isoformat()
        }

class CustomerSatisfaction(db.Model):
    """Customer satisfaction ratings"""
    __tablename__ = 'customer_satisfaction'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=True)  # Can be null for general feedback
    chat_session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=True)  # Can be null if not from chat
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Can be null for system feedback
    rating = db.Column(db.Integer, nullable=False)  # 1-5 star rating
    feedback = db.Column(db.Text, nullable=True)  # Optional text feedback
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ticket = db.relationship('Ticket', backref=db.backref('satisfaction_ratings', lazy=True))
    chat_session = db.relationship('ChatSession', backref=db.backref('satisfaction_ratings', lazy=True))
    customer = db.relationship('User', foreign_keys=[customer_id], backref=db.backref('given_ratings', lazy=True))
    agent = db.relationship('User', foreign_keys=[agent_id], backref=db.backref('received_ratings', lazy=True))
    
    def __repr__(self):
        return f'<CustomerSatisfaction {self.id} for Ticket {self.ticket_id}'
    
    def to_dict(self):
        """Convert customer satisfaction object to dictionary"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'chat_session_id': self.chat_session_id,
            'customer_id': self.customer_id,
            'customer_name': self.customer.username,
            'agent_id': self.agent_id,
            'agent_name': self.agent.username if self.agent else 'System',
            'rating': self.rating,
            'feedback': self.feedback,
            'created_at': self.created_at.isoformat()
        }