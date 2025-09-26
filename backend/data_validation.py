"""
Data validation utilities to ensure integrity during migration.
Provides comprehensive validation for unified models and migration processes.
"""

import re
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import logging

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

class ValidationResult:
    """Represents the result of a validation operation"""
    
    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        self.info = []
    
    def add_error(self, message: str, entity_type: str = None, entity_id: Any = None):
        """Add an error to the validation result"""
        self.is_valid = False
        error_msg = f"{entity_type} {entity_id}: {message}" if entity_type and entity_id else message
        self.errors.append(error_msg)
        logger.error(f"Validation error: {error_msg}")
    
    def add_warning(self, message: str, entity_type: str = None, entity_id: Any = None):
        """Add a warning to the validation result"""
        warning_msg = f"{entity_type} {entity_id}: {message}" if entity_type and entity_id else message
        self.warnings.append(warning_msg)
        logger.warning(f"Validation warning: {warning_msg}")
    
    def add_info(self, message: str):
        """Add an info message to the validation result"""
        self.info.append(message)
        logger.info(f"Validation info: {message}")
    
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result into this one"""
        if not other.is_valid:
            self.is_valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.info.extend(other.info)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary"""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
        }

class FieldValidator:
    """Validates individual fields"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        if not phone:
            return True  # Phone is optional
        
        # Remove common formatting characters
        cleaned_phone = re.sub(r'[\s\-\(\)\+]', '', phone)
        
        # Check if it's all digits and reasonable length
        return cleaned_phone.isdigit() and 7 <= len(cleaned_phone) <= 15
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        if not username:
            return False
        
        # Username should be 3-50 characters, alphanumeric plus underscore/dash
        username_pattern = r'^[a-zA-Z0-9_-]{3,50}$'
        return re.match(username_pattern, username) is not None
    
    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """Validate user_id format"""
        if not user_id:
            return False
        
        # User ID should be 1-50 characters
        return 1 <= len(user_id) <= 50
    
    @staticmethod
    def validate_text_length(text: str, min_length: int = 0, max_length: int = None) -> bool:
        """Validate text length"""
        if not text and min_length > 0:
            return False
        
        text_length = len(text) if text else 0
        
        if text_length < min_length:
            return False
        
        if max_length and text_length > max_length:
            return False
        
        return True
    
    @staticmethod
    def validate_datetime(dt: datetime) -> bool:
        """Validate datetime object"""
        if not isinstance(dt, datetime):
            return False
        
        # Check if datetime is reasonable (not too far in past or future)
        now = datetime.now(timezone.utc)
        min_date = datetime(1900, 1, 1, tzinfo=timezone.utc)
        max_date = now.replace(year=now.year + 10)  # 10 years in future
        
        return min_date <= dt <= max_date

class ModelValidator:
    """Validates unified models"""
    
    def __init__(self):
        self.field_validator = FieldValidator()
    
    def validate_user(self, user: UnifiedUser) -> ValidationResult:
        """Validate UnifiedUser model"""
        result = ValidationResult()
        
        # Required fields
        if not user.user_id:
            result.add_error("user_id is required", "User", user.id)
        elif not self.field_validator.validate_user_id(user.user_id):
            result.add_error("user_id format is invalid", "User", user.id)
        
        if not user.username:
            result.add_error("username is required", "User", user.id)
        elif not self.field_validator.validate_username(user.username):
            result.add_error("username format is invalid", "User", user.id)
        
        if not user.email:
            result.add_error("email is required", "User", user.id)
        elif not self.field_validator.validate_email(user.email):
            result.add_error("email format is invalid", "User", user.id)
        
        # Optional fields validation
        if user.phone and not self.field_validator.validate_phone(user.phone):
            result.add_warning("phone format may be invalid", "User", user.id)
        
        if user.full_name and not self.field_validator.validate_text_length(user.full_name, max_length=255):
            result.add_error("full_name is too long", "User", user.id)
        
        # Enum validation
        if user.role not in UserRole:
            result.add_error(f"invalid role: {user.role}", "User", user.id)
        
        # Datetime validation
        if user.created_at and not self.field_validator.validate_datetime(user.created_at):
            result.add_error("created_at is invalid", "User", user.id)
        
        if user.updated_at and not self.field_validator.validate_datetime(user.updated_at):
            result.add_error("updated_at is invalid", "User", user.id)
        
        if user.last_login and not self.field_validator.validate_datetime(user.last_login):
            result.add_warning("last_login is invalid", "User", user.id)
        
        return result
    
    def validate_ticket(self, ticket: UnifiedTicket) -> ValidationResult:
        """Validate UnifiedTicket model"""
        result = ValidationResult()
        
        # Required fields
        if not ticket.title:
            result.add_error("title is required", "Ticket", ticket.id)
        elif not self.field_validator.validate_text_length(ticket.title, min_length=1, max_length=255):
            result.add_error("title length is invalid", "Ticket", ticket.id)
        
        if not ticket.description:
            result.add_error("description is required", "Ticket", ticket.id)
        elif not self.field_validator.validate_text_length(ticket.description, min_length=1):
            result.add_error("description is required", "Ticket", ticket.id)
        
        # Enum validation
        if ticket.status not in TicketStatus:
            result.add_error(f"invalid status: {ticket.status}", "Ticket", ticket.id)
        
        if ticket.priority not in TicketPriority:
            result.add_error(f"invalid priority: {ticket.priority}", "Ticket", ticket.id)
        
        if ticket.category not in TicketCategory:
            result.add_error(f"invalid category: {ticket.category}", "Ticket", ticket.id)
        
        # Datetime validation
        if ticket.created_at and not self.field_validator.validate_datetime(ticket.created_at):
            result.add_error("created_at is invalid", "Ticket", ticket.id)
        
        if ticket.updated_at and not self.field_validator.validate_datetime(ticket.updated_at):
            result.add_error("updated_at is invalid", "Ticket", ticket.id)
        
        if ticket.resolved_at and not self.field_validator.validate_datetime(ticket.resolved_at):
            result.add_error("resolved_at is invalid", "Ticket", ticket.id)
        
        # Business logic validation
        if ticket.resolved_at and ticket.created_at and ticket.resolved_at < ticket.created_at:
            result.add_error("resolved_at cannot be before created_at", "Ticket", ticket.id)
        
        if ticket.status == TicketStatus.RESOLVED and not ticket.resolved_at:
            result.add_warning("resolved ticket should have resolved_at timestamp", "Ticket", ticket.id)
        
        return result
    
    def validate_comment(self, comment: UnifiedTicketComment) -> ValidationResult:
        """Validate UnifiedTicketComment model"""
        result = ValidationResult()
        
        # Required fields
        if not comment.ticket_id:
            result.add_error("ticket_id is required", "Comment", comment.id)
        
        if not comment.comment and not comment.content:
            result.add_error("comment content is required", "Comment", comment.id)
        
        # Validate content length
        content = comment.comment or comment.content
        if content and not self.field_validator.validate_text_length(content, min_length=1):
            result.add_error("comment content cannot be empty", "Comment", comment.id)
        
        # Datetime validation
        if comment.created_at and not self.field_validator.validate_datetime(comment.created_at):
            result.add_error("created_at is invalid", "Comment", comment.id)
        
        return result
    
    def validate_activity(self, activity: UnifiedTicketActivity) -> ValidationResult:
        """Validate UnifiedTicketActivity model"""
        result = ValidationResult()
        
        # Required fields
        if not activity.ticket_id:
            result.add_error("ticket_id is required", "Activity", activity.id)
        
        if not activity.activity_type:
            result.add_error("activity_type is required", "Activity", activity.id)
        elif not self.field_validator.validate_text_length(activity.activity_type, min_length=1, max_length=50):
            result.add_error("activity_type length is invalid", "Activity", activity.id)
        
        if not activity.description:
            result.add_error("description is required", "Activity", activity.id)
        elif not self.field_validator.validate_text_length(activity.description, min_length=1):
            result.add_error("description cannot be empty", "Activity", activity.id)
        
        # Datetime validation
        if activity.created_at and not self.field_validator.validate_datetime(activity.created_at):
            result.add_error("created_at is invalid", "Activity", activity.id)
        
        return result

class DatabaseValidator:
    """Validates database integrity and relationships"""
    
    def __init__(self, session: Session):
        self.session = session
        self.model_validator = ModelValidator()
    
    def validate_all(self) -> ValidationResult:
        """Validate all data in the database"""
        result = ValidationResult()
        
        result.add_info("Starting comprehensive database validation")
        
        # Validate individual models
        result.merge(self.validate_users())
        result.merge(self.validate_tickets())
        result.merge(self.validate_comments())
        result.merge(self.validate_activities())
        
        # Validate relationships
        result.merge(self.validate_relationships())
        
        # Validate business rules
        result.merge(self.validate_business_rules())
        
        # Generate statistics
        result.merge(self.generate_statistics())
        
        result.add_info("Database validation completed")
        
        return result
    
    def validate_users(self) -> ValidationResult:
        """Validate all users in the database"""
        result = ValidationResult()
        
        users = self.session.query(UnifiedUser).all()
        result.add_info(f"Validating {len(users)} users")
        
        # Check for duplicates
        email_counts = self.session.query(
            UnifiedUser.email, 
            func.count(UnifiedUser.id)
        ).group_by(UnifiedUser.email).having(func.count(UnifiedUser.id) > 1).all()
        
        for email, count in email_counts:
            result.add_error(f"Duplicate email found: {email} ({count} users)")
        
        username_counts = self.session.query(
            UnifiedUser.username,
            func.count(UnifiedUser.id)
        ).group_by(UnifiedUser.username).having(func.count(UnifiedUser.id) > 1).all()
        
        for username, count in username_counts:
            result.add_error(f"Duplicate username found: {username} ({count} users)")
        
        user_id_counts = self.session.query(
            UnifiedUser.user_id,
            func.count(UnifiedUser.id)
        ).group_by(UnifiedUser.user_id).having(func.count(UnifiedUser.id) > 1).all()
        
        for user_id, count in user_id_counts:
            result.add_error(f"Duplicate user_id found: {user_id} ({count} users)")
        
        # Validate individual users
        for user in users:
            user_result = self.model_validator.validate_user(user)
            result.merge(user_result)
        
        return result
    
    def validate_tickets(self) -> ValidationResult:
        """Validate all tickets in the database"""
        result = ValidationResult()
        
        tickets = self.session.query(UnifiedTicket).all()
        result.add_info(f"Validating {len(tickets)} tickets")
        
        for ticket in tickets:
            ticket_result = self.model_validator.validate_ticket(ticket)
            result.merge(ticket_result)
        
        return result
    
    def validate_comments(self) -> ValidationResult:
        """Validate all comments in the database"""
        result = ValidationResult()
        
        comments = self.session.query(UnifiedTicketComment).all()
        result.add_info(f"Validating {len(comments)} comments")
        
        for comment in comments:
            comment_result = self.model_validator.validate_comment(comment)
            result.merge(comment_result)
        
        return result
    
    def validate_activities(self) -> ValidationResult:
        """Validate all activities in the database"""
        result = ValidationResult()
        
        activities = self.session.query(UnifiedTicketActivity).all()
        result.add_info(f"Validating {len(activities)} activities")
        
        for activity in activities:
            activity_result = self.model_validator.validate_activity(activity)
            result.merge(activity_result)
        
        return result
    
    def validate_relationships(self) -> ValidationResult:
        """Validate foreign key relationships"""
        result = ValidationResult()
        
        result.add_info("Validating foreign key relationships")
        
        # Check for orphaned tickets (customer_id not in users)
        orphaned_tickets = self.session.query(UnifiedTicket).filter(
            UnifiedTicket.customer_id.isnot(None),
            ~UnifiedTicket.customer_id.in_(
                self.session.query(UnifiedUser.id)
            )
        ).count()
        
        if orphaned_tickets > 0:
            result.add_error(f"Found {orphaned_tickets} tickets with invalid customer_id")
        
        # Check for orphaned tickets (assigned_agent_id not in users)
        orphaned_assigned_tickets = self.session.query(UnifiedTicket).filter(
            UnifiedTicket.assigned_agent_id.isnot(None),
            ~UnifiedTicket.assigned_agent_id.in_(
                self.session.query(UnifiedUser.id)
            )
        ).count()
        
        if orphaned_assigned_tickets > 0:
            result.add_error(f"Found {orphaned_assigned_tickets} tickets with invalid assigned_agent_id")
        
        # Check for orphaned comments
        orphaned_comments = self.session.query(UnifiedTicketComment).filter(
            ~UnifiedTicketComment.ticket_id.in_(
                self.session.query(UnifiedTicket.id)
            )
        ).count()
        
        if orphaned_comments > 0:
            result.add_error(f"Found {orphaned_comments} comments with invalid ticket_id")
        
        # Check for orphaned activities
        orphaned_activities = self.session.query(UnifiedTicketActivity).filter(
            ~UnifiedTicketActivity.ticket_id.in_(
                self.session.query(UnifiedTicket.id)
            )
        ).count()
        
        if orphaned_activities > 0:
            result.add_error(f"Found {orphaned_activities} activities with invalid ticket_id")
        
        return result
    
    def validate_business_rules(self) -> ValidationResult:
        """Validate business logic rules"""
        result = ValidationResult()
        
        result.add_info("Validating business rules")
        
        # Check for tickets assigned to non-agent users
        tickets_assigned_to_customers = self.session.query(UnifiedTicket).join(
            UnifiedUser, UnifiedTicket.assigned_agent_id == UnifiedUser.id
        ).filter(
            UnifiedUser.role == UserRole.CUSTOMER
        ).count()
        
        if tickets_assigned_to_customers > 0:
            result.add_warning(f"Found {tickets_assigned_to_customers} tickets assigned to customers")
        
        # Check for resolved tickets without resolution date
        resolved_without_date = self.session.query(UnifiedTicket).filter(
            UnifiedTicket.status == TicketStatus.RESOLVED,
            UnifiedTicket.resolved_at.is_(None)
        ).count()
        
        if resolved_without_date > 0:
            result.add_warning(f"Found {resolved_without_date} resolved tickets without resolution date")
        
        # Check for tickets with resolution date but not resolved status
        dated_not_resolved = self.session.query(UnifiedTicket).filter(
            UnifiedTicket.resolved_at.isnot(None),
            UnifiedTicket.status != TicketStatus.RESOLVED
        ).count()
        
        if dated_not_resolved > 0:
            result.add_warning(f"Found {dated_not_resolved} tickets with resolution date but not resolved status")
        
        return result
    
    def generate_statistics(self) -> ValidationResult:
        """Generate database statistics"""
        result = ValidationResult()
        
        # Count records
        user_count = self.session.query(UnifiedUser).count()
        ticket_count = self.session.query(UnifiedTicket).count()
        comment_count = self.session.query(UnifiedTicketComment).count()
        activity_count = self.session.query(UnifiedTicketActivity).count()
        
        result.add_info(f"Database contains {user_count} users, {ticket_count} tickets, {comment_count} comments, {activity_count} activities")
        
        # Count by status
        status_counts = self.session.query(
            UnifiedTicket.status,
            func.count(UnifiedTicket.id)
        ).group_by(UnifiedTicket.status).all()
        
        for status, count in status_counts:
            result.add_info(f"Tickets with status {status.value}: {count}")
        
        # Count by role
        role_counts = self.session.query(
            UnifiedUser.role,
            func.count(UnifiedUser.id)
        ).group_by(UnifiedUser.role).all()
        
        for role, count in role_counts:
            result.add_info(f"Users with role {role.value}: {count}")
        
        return result

class MigrationValidator:
    """Validates migration-specific data integrity"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def validate_migration_integrity(self) -> ValidationResult:
        """Validate that migration preserved data integrity"""
        result = ValidationResult()
        
        result.add_info("Validating migration integrity")
        
        # Check for missing legacy IDs (indicates incomplete migration)
        users_without_legacy = self.session.query(UnifiedUser).filter(
            and_(
                UnifiedUser.legacy_customer_id.is_(None),
                UnifiedUser.legacy_admin_user_id.is_(None)
            )
        ).count()
        
        if users_without_legacy > 0:
            result.add_warning(f"Found {users_without_legacy} users without legacy IDs")
        
        tickets_without_legacy = self.session.query(UnifiedTicket).filter(
            and_(
                UnifiedTicket.legacy_backend_ticket_id.is_(None),
                UnifiedTicket.legacy_admin_ticket_id.is_(None)
            )
        ).count()
        
        if tickets_without_legacy > 0:
            result.add_warning(f"Found {tickets_without_legacy} tickets without legacy IDs")
        
        # Check for duplicate legacy IDs (indicates migration conflicts)
        duplicate_backend_tickets = self.session.query(
            UnifiedTicket.legacy_backend_ticket_id,
            func.count(UnifiedTicket.id)
        ).filter(
            UnifiedTicket.legacy_backend_ticket_id.isnot(None)
        ).group_by(
            UnifiedTicket.legacy_backend_ticket_id
        ).having(func.count(UnifiedTicket.id) > 1).all()
        
        for legacy_id, count in duplicate_backend_tickets:
            result.add_error(f"Duplicate legacy backend ticket ID {legacy_id} found {count} times")
        
        return result

def validate_database(session: Session) -> ValidationResult:
    """Main function to validate the entire database"""
    validator = DatabaseValidator(session)
    return validator.validate_all()

def validate_migration(session: Session) -> ValidationResult:
    """Main function to validate migration integrity"""
    validator = MigrationValidator(session)
    return validator.validate_migration_integrity()

def validate_model_instance(model_instance: Any) -> ValidationResult:
    """Validate a single model instance"""
    validator = ModelValidator()
    
    if isinstance(model_instance, UnifiedUser):
        return validator.validate_user(model_instance)
    elif isinstance(model_instance, UnifiedTicket):
        return validator.validate_ticket(model_instance)
    elif isinstance(model_instance, UnifiedTicketComment):
        return validator.validate_comment(model_instance)
    elif isinstance(model_instance, UnifiedTicketActivity):
        return validator.validate_activity(model_instance)
    else:
        result = ValidationResult()
        result.add_warning(f"No validator available for {type(model_instance).__name__}")
        return result

# Export main functions and classes
__all__ = [
    'ValidationResult',
    'FieldValidator',
    'ModelValidator',
    'DatabaseValidator',
    'MigrationValidator',
    'validate_database',
    'validate_migration',
    'validate_model_instance',
]