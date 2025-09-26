"""
Model adapters to handle Flask-SQLAlchemy to pure SQLAlchemy conversion.
Provides utilities to convert between legacy models and unified models.
"""

from typing import Dict, Any, Optional, List, Type, Union
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import inspect
import logging

# Import legacy models
try:
    from backend.models import (
        User as BackendUser,
        Customer as BackendCustomer,
        Ticket as BackendTicket,
        TicketComment as BackendTicketComment,
        TicketActivity as BackendTicketActivity,
        UserSession as BackendUserSession,
        VoiceSettings as BackendVoiceSettings,
        VoiceAnalytics as BackendVoiceAnalytics,
        KnowledgeEntry as BackendKnowledgeEntry,
        Order as BackendOrder,
        SupportIntent as BackendSupportIntent,
        SupportResponse as BackendSupportResponse,
        ChatHistory as BackendChatHistory,
    )
    BACKEND_MODELS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import backend models: {e}")
    BACKEND_MODELS_AVAILABLE = False

# Import admin dashboard models
try:
    import sys
    import os
    admin_path = os.path.join(os.path.dirname(__file__), '..', 'admin-dashboard')
    if admin_path not in sys.path:
        sys.path.append(admin_path)
    
    from admin_backend.models import User as AdminUser
    from admin_backend.models_support import (
        Ticket as AdminTicket,
        TicketComment as AdminTicketComment,
        TicketActivity as AdminTicketActivity,
        ChatSession as AdminChatSession,
        ChatMessage as AdminChatMessage,
        PerformanceMetric as AdminPerformanceMetric,
        CustomerSatisfaction as AdminCustomerSatisfaction,
    )
    ADMIN_MODELS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import admin dashboard models: {e}")
    ADMIN_MODELS_AVAILABLE = False

# Import unified models
from backend.unified_models import (
    UnifiedUser,
    UnifiedTicket,
    UnifiedTicketComment,
    UnifiedTicketActivity,
    UnifiedUserSession,
    UnifiedChatSession,
    UnifiedChatMessage,
    UnifiedPerformanceMetric,
    UnifiedCustomerSatisfaction,
    UnifiedVoiceSettings,
    UnifiedVoiceAnalytics,
    UnifiedKnowledgeEntry,
    UnifiedOrder,
    UnifiedSupportIntent,
    UnifiedSupportResponse,
    UnifiedChatHistory,
    UserRole,
    TicketStatus,
    TicketPriority,
    TicketCategory,
)

logger = logging.getLogger(__name__)

class ModelAdapter:
    """Base class for model adapters"""
    
    @staticmethod
    def safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
        """Safely get attribute from object"""
        try:
            return getattr(obj, attr, default)
        except Exception:
            return default
    
    @staticmethod
    def convert_datetime(dt: Any) -> Optional[datetime]:
        """Convert various datetime formats to timezone-aware datetime"""
        if dt is None:
            return None
        
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        
        if isinstance(dt, str):
            try:
                parsed = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed
            except Exception:
                return None
        
        return None
    
    @staticmethod
    def convert_enum_value(value: Any, enum_class: Type) -> Any:
        """Convert string or enum value to target enum"""
        if value is None:
            return None
        
        if isinstance(value, enum_class):
            return value
        
        if isinstance(value, str):
            try:
                return enum_class(value)
            except ValueError:
                # Try to find by name
                for enum_val in enum_class:
                    if enum_val.name.lower() == value.lower():
                        return enum_val
                # Return first enum value as fallback
                return list(enum_class)[0]
        
        return None

class UserAdapter(ModelAdapter):
    """Adapter for User models"""
    
    @classmethod
    def from_backend_user(cls, backend_user: 'BackendUser') -> UnifiedUser:
        """Convert backend User to UnifiedUser"""
        if not BACKEND_MODELS_AVAILABLE:
            raise RuntimeError("Backend models not available")
        
        return UnifiedUser(
            user_id=cls.safe_getattr(backend_user, 'user_id'),
            username=cls.safe_getattr(backend_user, 'username'),
            email=cls.safe_getattr(backend_user, 'email'),
            password_hash=cls.safe_getattr(backend_user, 'password_hash'),
            full_name=cls.safe_getattr(backend_user, 'full_name'),
            phone=None,  # Not in backend model
            is_admin=cls.safe_getattr(backend_user, 'is_admin', False),
            last_login=None,  # Not in backend model
            is_active=cls.safe_getattr(backend_user, 'is_active', True),
            role=UserRole.ADMIN if cls.safe_getattr(backend_user, 'is_admin', False) else UserRole.CUSTOMER,
            created_at=cls.convert_datetime(cls.safe_getattr(backend_user, 'created_at')),
            updated_at=cls.convert_datetime(cls.safe_getattr(backend_user, 'updated_at')),
            legacy_customer_id=None,
            legacy_admin_user_id=None,
        )
    
    @classmethod
    def from_backend_customer(cls, backend_customer: 'BackendCustomer') -> UnifiedUser:
        """Convert backend Customer to UnifiedUser"""
        if not BACKEND_MODELS_AVAILABLE:
            raise RuntimeError("Backend models not available")
        
        return UnifiedUser(
            user_id=str(cls.safe_getattr(backend_customer, 'customer_id', f"cust_{backend_customer.id}")),
            username=cls.safe_getattr(backend_customer, 'name', f"customer_{backend_customer.id}"),
            email=cls.safe_getattr(backend_customer, 'email'),
            password_hash="",  # Customers don't have passwords in backend
            full_name=cls.safe_getattr(backend_customer, 'name'),
            phone=cls.safe_getattr(backend_customer, 'phone'),
            is_admin=False,
            last_login=None,
            is_active=True,
            role=UserRole.CUSTOMER,
            created_at=cls.convert_datetime(cls.safe_getattr(backend_customer, 'created_at')),
            updated_at=cls.convert_datetime(cls.safe_getattr(backend_customer, 'created_at')),
            legacy_customer_id=cls.safe_getattr(backend_customer, 'id'),
            legacy_admin_user_id=None,
        )
    
    @classmethod
    def from_admin_user(cls, admin_user: 'AdminUser') -> UnifiedUser:
        """Convert admin dashboard User to UnifiedUser"""
        if not ADMIN_MODELS_AVAILABLE:
            raise RuntimeError("Admin models not available")
        
        return UnifiedUser(
            user_id=cls.safe_getattr(admin_user, 'username', f"admin_{admin_user.id}"),
            username=cls.safe_getattr(admin_user, 'username'),
            email=cls.safe_getattr(admin_user, 'email'),
            password_hash=cls.safe_getattr(admin_user, 'password', ''),
            full_name=cls.safe_getattr(admin_user, 'full_name'),
            phone=cls.safe_getattr(admin_user, 'phone'),
            is_admin=cls.safe_getattr(admin_user, 'is_admin', False),
            last_login=cls.convert_datetime(cls.safe_getattr(admin_user, 'last_login')),
            is_active=True,
            role=UserRole.ADMIN if cls.safe_getattr(admin_user, 'is_admin', False) else UserRole.AGENT,
            created_at=cls.convert_datetime(cls.safe_getattr(admin_user, 'created_at')),
            updated_at=cls.convert_datetime(cls.safe_getattr(admin_user, 'created_at')),
            legacy_customer_id=cls.safe_getattr(admin_user, 'ai_agent_customer_id'),
            legacy_admin_user_id=cls.safe_getattr(admin_user, 'id'),
        )

class TicketAdapter(ModelAdapter):
    """Adapter for Ticket models"""
    
    @classmethod
    def from_backend_ticket(cls, backend_ticket: 'BackendTicket', user_mapping: Dict[int, int] = None) -> UnifiedTicket:
        """Convert backend Ticket to UnifiedTicket"""
        if not BACKEND_MODELS_AVAILABLE:
            raise RuntimeError("Backend models not available")
        
        user_mapping = user_mapping or {}
        
        return UnifiedTicket(
            title=cls.safe_getattr(backend_ticket, 'title'),
            description=cls.safe_getattr(backend_ticket, 'description'),
            status=cls.convert_enum_value(cls.safe_getattr(backend_ticket, 'status'), TicketStatus),
            priority=cls.convert_enum_value(cls.safe_getattr(backend_ticket, 'priority'), TicketPriority),
            category=cls.convert_enum_value(cls.safe_getattr(backend_ticket, 'category'), TicketCategory),
            customer_id=user_mapping.get(cls.safe_getattr(backend_ticket, 'customer_id')),
            assigned_agent_id=user_mapping.get(cls.safe_getattr(backend_ticket, 'assigned_agent_id')),
            created_at=cls.convert_datetime(cls.safe_getattr(backend_ticket, 'created_at')),
            updated_at=cls.convert_datetime(cls.safe_getattr(backend_ticket, 'updated_at')),
            resolved_at=cls.convert_datetime(cls.safe_getattr(backend_ticket, 'resolved_at')),
            tags=cls.safe_getattr(backend_ticket, 'tags'),
            ticket_metadata=cls.safe_getattr(backend_ticket, 'ticket_metadata'),
            legacy_backend_ticket_id=cls.safe_getattr(backend_ticket, 'id'),
            legacy_admin_ticket_id=None,
        )
    
    @classmethod
    def from_admin_ticket(cls, admin_ticket: 'AdminTicket', user_mapping: Dict[int, int] = None) -> UnifiedTicket:
        """Convert admin dashboard Ticket to UnifiedTicket"""
        if not ADMIN_MODELS_AVAILABLE:
            raise RuntimeError("Admin models not available")
        
        user_mapping = user_mapping or {}
        
        return UnifiedTicket(
            title=cls.safe_getattr(admin_ticket, 'title'),
            description=cls.safe_getattr(admin_ticket, 'description'),
            status=cls.convert_enum_value(cls.safe_getattr(admin_ticket, 'status'), TicketStatus),
            priority=cls.convert_enum_value(cls.safe_getattr(admin_ticket, 'priority'), TicketPriority),
            category=cls.convert_enum_value(cls.safe_getattr(admin_ticket, 'category'), TicketCategory),
            customer_id=user_mapping.get(cls.safe_getattr(admin_ticket, 'customer_id')),
            assigned_agent_id=user_mapping.get(cls.safe_getattr(admin_ticket, 'assigned_agent_id')),
            created_at=cls.convert_datetime(cls.safe_getattr(admin_ticket, 'created_at')),
            updated_at=cls.convert_datetime(cls.safe_getattr(admin_ticket, 'updated_at')),
            resolved_at=cls.convert_datetime(cls.safe_getattr(admin_ticket, 'resolved_at')),
            tags=None,  # Not in admin model
            ticket_metadata=None,  # Not in admin model
            legacy_backend_ticket_id=cls.safe_getattr(admin_ticket, 'ai_agent_ticket_id'),
            legacy_admin_ticket_id=cls.safe_getattr(admin_ticket, 'id'),
        )

class CommentAdapter(ModelAdapter):
    """Adapter for Comment models"""
    
    @classmethod
    def from_backend_comment(cls, backend_comment: 'BackendTicketComment', 
                           user_mapping: Dict[int, int] = None,
                           ticket_mapping: Dict[int, int] = None) -> UnifiedTicketComment:
        """Convert backend TicketComment to UnifiedTicketComment"""
        if not BACKEND_MODELS_AVAILABLE:
            raise RuntimeError("Backend models not available")
        
        user_mapping = user_mapping or {}
        ticket_mapping = ticket_mapping or {}
        
        return UnifiedTicketComment(
            ticket_id=ticket_mapping.get(cls.safe_getattr(backend_comment, 'ticket_id')),
            author_id=user_mapping.get(cls.safe_getattr(backend_comment, 'author_id')),
            comment=cls.safe_getattr(backend_comment, 'comment'),
            content=cls.safe_getattr(backend_comment, 'comment'),  # Copy to content field
            is_internal=cls.safe_getattr(backend_comment, 'is_internal', False),
            created_at=cls.convert_datetime(cls.safe_getattr(backend_comment, 'created_at')),
            legacy_backend_comment_id=cls.safe_getattr(backend_comment, 'id'),
            legacy_admin_comment_id=None,
        )
    
    @classmethod
    def from_admin_comment(cls, admin_comment: 'AdminTicketComment',
                          user_mapping: Dict[int, int] = None,
                          ticket_mapping: Dict[int, int] = None) -> UnifiedTicketComment:
        """Convert admin dashboard TicketComment to UnifiedTicketComment"""
        if not ADMIN_MODELS_AVAILABLE:
            raise RuntimeError("Admin models not available")
        
        user_mapping = user_mapping or {}
        ticket_mapping = ticket_mapping or {}
        
        return UnifiedTicketComment(
            ticket_id=ticket_mapping.get(cls.safe_getattr(admin_comment, 'ticket_id')),
            author_id=user_mapping.get(cls.safe_getattr(admin_comment, 'user_id')),
            comment=cls.safe_getattr(admin_comment, 'content'),
            content=cls.safe_getattr(admin_comment, 'content'),
            is_internal=cls.safe_getattr(admin_comment, 'is_internal', False),
            created_at=cls.convert_datetime(cls.safe_getattr(admin_comment, 'created_at')),
            legacy_backend_comment_id=cls.safe_getattr(admin_comment, 'ai_agent_comment_id'),
            legacy_admin_comment_id=cls.safe_getattr(admin_comment, 'id'),
        )

class ActivityAdapter(ModelAdapter):
    """Adapter for Activity models"""
    
    @classmethod
    def from_backend_activity(cls, backend_activity: 'BackendTicketActivity',
                            user_mapping: Dict[int, int] = None,
                            ticket_mapping: Dict[int, int] = None) -> UnifiedTicketActivity:
        """Convert backend TicketActivity to UnifiedTicketActivity"""
        if not BACKEND_MODELS_AVAILABLE:
            raise RuntimeError("Backend models not available")
        
        user_mapping = user_mapping or {}
        ticket_mapping = ticket_mapping or {}
        
        return UnifiedTicketActivity(
            ticket_id=ticket_mapping.get(cls.safe_getattr(backend_activity, 'ticket_id')),
            activity_type=cls.safe_getattr(backend_activity, 'activity_type'),
            description=cls.safe_getattr(backend_activity, 'description'),
            performed_by_id=user_mapping.get(cls.safe_getattr(backend_activity, 'performed_by_id')),
            created_at=cls.convert_datetime(cls.safe_getattr(backend_activity, 'created_at')),
            legacy_backend_activity_id=cls.safe_getattr(backend_activity, 'id'),
            legacy_admin_activity_id=None,
        )
    
    @classmethod
    def from_admin_activity(cls, admin_activity: 'AdminTicketActivity',
                           user_mapping: Dict[int, int] = None,
                           ticket_mapping: Dict[int, int] = None) -> UnifiedTicketActivity:
        """Convert admin dashboard TicketActivity to UnifiedTicketActivity"""
        if not ADMIN_MODELS_AVAILABLE:
            raise RuntimeError("Admin models not available")
        
        user_mapping = user_mapping or {}
        ticket_mapping = ticket_mapping or {}
        
        return UnifiedTicketActivity(
            ticket_id=ticket_mapping.get(cls.safe_getattr(admin_activity, 'ticket_id')),
            activity_type=cls.safe_getattr(admin_activity, 'activity_type'),
            description=cls.safe_getattr(admin_activity, 'description'),
            performed_by_id=user_mapping.get(cls.safe_getattr(admin_activity, 'user_id')),
            created_at=cls.convert_datetime(cls.safe_getattr(admin_activity, 'created_at')),
            legacy_backend_activity_id=cls.safe_getattr(admin_activity, 'ai_agent_activity_id'),
            legacy_admin_activity_id=cls.safe_getattr(admin_activity, 'id'),
        )

class ValidationError(Exception):
    """Raised when model validation fails"""
    pass

class ModelValidator:
    """Validates unified models during migration"""
    
    @staticmethod
    def validate_user(user: UnifiedUser) -> List[str]:
        """Validate UnifiedUser model"""
        errors = []
        
        if not user.user_id:
            errors.append("user_id is required")
        
        if not user.username:
            errors.append("username is required")
        
        if not user.email:
            errors.append("email is required")
        elif '@' not in user.email:
            errors.append("email format is invalid")
        
        if user.role not in UserRole:
            errors.append(f"invalid role: {user.role}")
        
        return errors
    
    @staticmethod
    def validate_ticket(ticket: UnifiedTicket) -> List[str]:
        """Validate UnifiedTicket model"""
        errors = []
        
        if not ticket.title:
            errors.append("title is required")
        
        if not ticket.description:
            errors.append("description is required")
        
        if ticket.status not in TicketStatus:
            errors.append(f"invalid status: {ticket.status}")
        
        if ticket.priority not in TicketPriority:
            errors.append(f"invalid priority: {ticket.priority}")
        
        if ticket.category not in TicketCategory:
            errors.append(f"invalid category: {ticket.category}")
        
        return errors
    
    @staticmethod
    def validate_comment(comment: UnifiedTicketComment) -> List[str]:
        """Validate UnifiedTicketComment model"""
        errors = []
        
        if not comment.ticket_id:
            errors.append("ticket_id is required")
        
        if not comment.comment and not comment.content:
            errors.append("comment content is required")
        
        return errors
    
    @staticmethod
    def validate_activity(activity: UnifiedTicketActivity) -> List[str]:
        """Validate UnifiedTicketActivity model"""
        errors = []
        
        if not activity.ticket_id:
            errors.append("ticket_id is required")
        
        if not activity.activity_type:
            errors.append("activity_type is required")
        
        if not activity.description:
            errors.append("description is required")
        
        return errors

def validate_model(model: Any) -> None:
    """Validate a unified model and raise ValidationError if invalid"""
    validator = ModelValidator()
    
    if isinstance(model, UnifiedUser):
        errors = validator.validate_user(model)
    elif isinstance(model, UnifiedTicket):
        errors = validator.validate_ticket(model)
    elif isinstance(model, UnifiedTicketComment):
        errors = validator.validate_comment(model)
    elif isinstance(model, UnifiedTicketActivity):
        errors = validator.validate_activity(model)
    else:
        return  # No validation for other models
    
    if errors:
        raise ValidationError(f"Validation failed for {type(model).__name__}: {', '.join(errors)}")

# Export all adapters and utilities
__all__ = [
    'ModelAdapter',
    'UserAdapter', 
    'TicketAdapter',
    'CommentAdapter',
    'ActivityAdapter',
    'ModelValidator',
    'ValidationError',
    'validate_model',
    'BACKEND_MODELS_AVAILABLE',
    'ADMIN_MODELS_AVAILABLE',
]