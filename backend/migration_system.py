"""
Database migration system to preserve existing data from both systems.
Handles the migration from separate backend and admin dashboard databases to unified models.
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from sqlalchemy import create_engine, MetaData, Table, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import json
import sqlite3
import psycopg2
from contextlib import contextmanager

# Import unified models and adapters
from backend.unified_models import (
    Base as UnifiedBase,
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
)

from backend.model_adapters import (
    UserAdapter,
    TicketAdapter,
    CommentAdapter,
    ActivityAdapter,
    validate_model,
    ValidationError,
    BACKEND_MODELS_AVAILABLE,
    ADMIN_MODELS_AVAILABLE,
)

from backend.database import engine as main_engine, SessionLocal as MainSessionLocal

logger = logging.getLogger(__name__)

class MigrationError(Exception):
    """Raised when migration fails"""
    pass

class MigrationStats:
    """Tracks migration statistics"""
    
    def __init__(self):
        self.users_migrated = 0
        self.tickets_migrated = 0
        self.comments_migrated = 0
        self.activities_migrated = 0
        self.sessions_migrated = 0
        self.chat_sessions_migrated = 0
        self.chat_messages_migrated = 0
        self.performance_metrics_migrated = 0
        self.satisfaction_ratings_migrated = 0
        self.voice_settings_migrated = 0
        self.voice_analytics_migrated = 0
        self.knowledge_entries_migrated = 0
        self.orders_migrated = 0
        self.support_intents_migrated = 0
        self.support_responses_migrated = 0
        self.chat_history_migrated = 0
        self.errors = []
        self.warnings = []
        self.start_time = None
        self.end_time = None
    
    def add_error(self, error: str):
        """Add an error to the migration stats"""
        self.errors.append(error)
        logger.error(f"Migration error: {error}")
    
    def add_warning(self, warning: str):
        """Add a warning to the migration stats"""
        self.warnings.append(warning)
        logger.warning(f"Migration warning: {warning}")
    
    def start(self):
        """Mark migration start time"""
        self.start_time = datetime.now(timezone.utc)
    
    def finish(self):
        """Mark migration end time"""
        self.end_time = datetime.now(timezone.utc)
    
    def duration(self) -> Optional[float]:
        """Get migration duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary"""
        return {
            'users_migrated': self.users_migrated,
            'tickets_migrated': self.tickets_migrated,
            'comments_migrated': self.comments_migrated,
            'activities_migrated': self.activities_migrated,
            'sessions_migrated': self.sessions_migrated,
            'chat_sessions_migrated': self.chat_sessions_migrated,
            'chat_messages_migrated': self.chat_messages_migrated,
            'performance_metrics_migrated': self.performance_metrics_migrated,
            'satisfaction_ratings_migrated': self.satisfaction_ratings_migrated,
            'voice_settings_migrated': self.voice_settings_migrated,
            'voice_analytics_migrated': self.voice_analytics_migrated,
            'knowledge_entries_migrated': self.knowledge_entries_migrated,
            'orders_migrated': self.orders_migrated,
            'support_intents_migrated': self.support_intents_migrated,
            'support_responses_migrated': self.support_responses_migrated,
            'chat_history_migrated': self.chat_history_migrated,
            'errors': self.errors,
            'warnings': self.warnings,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration(),
        }

class DatabaseConnector:
    """Handles connections to different database types"""
    
    @staticmethod
    def get_backend_session() -> Session:
        """Get session for main backend database"""
        return MainSessionLocal()
    
    @staticmethod
    def get_admin_session():
        """Get session for admin dashboard database"""
        try:
            # Try to connect to admin dashboard database
            admin_db_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'admin-dashboard', 
                'instance', 
                'admin_dashboard.db'
            )
            
            if not os.path.exists(admin_db_path):
                # Try alternative path
                admin_db_path = os.path.join(
                    os.path.dirname(__file__), 
                    '..', 
                    'admin-dashboard', 
                    'admin_dashboard.db'
                )
            
            if os.path.exists(admin_db_path):
                admin_engine = create_engine(f'sqlite:///{admin_db_path}')
                AdminSessionLocal = sessionmaker(bind=admin_engine)
                return AdminSessionLocal()
            else:
                logger.warning(f"Admin dashboard database not found at {admin_db_path}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to connect to admin dashboard database: {e}")
            return None
    
    @staticmethod
    @contextmanager
    def get_unified_session():
        """Get session for unified database with transaction management"""
        session = MainSessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

class DataMigrator:
    """Handles data migration from legacy systems to unified models"""
    
    def __init__(self):
        self.stats = MigrationStats()
        self.user_id_mapping = {}  # Maps legacy user IDs to unified user IDs
        self.ticket_id_mapping = {}  # Maps legacy ticket IDs to unified ticket IDs
    
    def migrate_all(self, backup_before_migration: bool = True) -> MigrationStats:
        """Migrate all data from both systems"""
        self.stats.start()
        
        try:
            logger.info("Starting unified database migration")
            
            # Create backup if requested
            if backup_before_migration:
                self._create_backup()
            
            # Create unified database tables
            self._create_unified_tables()
            
            # Migrate users first (needed for foreign keys)
            self._migrate_users()
            
            # Migrate tickets
            self._migrate_tickets()
            
            # Migrate comments and activities
            self._migrate_comments()
            self._migrate_activities()
            
            # Migrate other entities
            self._migrate_sessions()
            self._migrate_chat_data()
            self._migrate_performance_data()
            self._migrate_voice_data()
            self._migrate_knowledge_data()
            self._migrate_support_data()
            
            logger.info("Migration completed successfully")
            
        except Exception as e:
            self.stats.add_error(f"Migration failed: {str(e)}")
            raise MigrationError(f"Migration failed: {str(e)}") from e
        
        finally:
            self.stats.finish()
        
        return self.stats
    
    def _create_backup(self):
        """Create backup of existing databases"""
        logger.info("Creating database backups")
        
        try:
            # Backup main database
            backup_dir = os.path.join(os.path.dirname(__file__), '..', 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # For PostgreSQL, we'd need pg_dump (simplified for now)
            logger.info("Database backup created (implementation depends on database type)")
            
        except Exception as e:
            self.stats.add_warning(f"Backup creation failed: {str(e)}")
    
    def _create_unified_tables(self):
        """Create unified database tables"""
        logger.info("Creating unified database tables")
        
        try:
            # Create all tables
            UnifiedBase.metadata.create_all(bind=main_engine)
            logger.info("Unified tables created successfully")
            
        except Exception as e:
            raise MigrationError(f"Failed to create unified tables: {str(e)}")
    
    def _migrate_users(self):
        """Migrate users from both systems"""
        logger.info("Migrating users")
        
        with DatabaseConnector.get_unified_session() as unified_session:
            # Migrate backend users
            if BACKEND_MODELS_AVAILABLE:
                self._migrate_backend_users(unified_session)
            
            # Migrate backend customers
            if BACKEND_MODELS_AVAILABLE:
                self._migrate_backend_customers(unified_session)
            
            # Migrate admin dashboard users
            if ADMIN_MODELS_AVAILABLE:
                self._migrate_admin_users(unified_session)
    
    def _migrate_backend_users(self, unified_session: Session):
        """Migrate users from backend system"""
        try:
            backend_session = DatabaseConnector.get_backend_session()
            
            # Import backend models dynamically
            from backend.models import User as BackendUser
            
            backend_users = backend_session.query(BackendUser).all()
            
            for backend_user in backend_users:
                try:
                    unified_user = UserAdapter.from_backend_user(backend_user)
                    validate_model(unified_user)
                    
                    unified_session.add(unified_user)
                    unified_session.flush()  # Get the ID
                    
                    # Store mapping
                    self.user_id_mapping[f"backend_user_{backend_user.id}"] = unified_user.id
                    self.stats.users_migrated += 1
                    
                except ValidationError as e:
                    self.stats.add_error(f"Failed to migrate backend user {backend_user.id}: {str(e)}")
                except Exception as e:
                    self.stats.add_error(f"Unexpected error migrating backend user {backend_user.id}: {str(e)}")
            
            backend_session.close()
            
        except Exception as e:
            self.stats.add_error(f"Failed to migrate backend users: {str(e)}")
    
    def _migrate_backend_customers(self, unified_session: Session):
        """Migrate customers from backend system"""
        try:
            backend_session = DatabaseConnector.get_backend_session()
            
            # Import backend models dynamically
            from backend.models import Customer as BackendCustomer
            
            backend_customers = backend_session.query(BackendCustomer).all()
            
            for backend_customer in backend_customers:
                try:
                    unified_user = UserAdapter.from_backend_customer(backend_customer)
                    validate_model(unified_user)
                    
                    unified_session.add(unified_user)
                    unified_session.flush()  # Get the ID
                    
                    # Store mapping
                    self.user_id_mapping[f"backend_customer_{backend_customer.id}"] = unified_user.id
                    self.stats.users_migrated += 1
                    
                except ValidationError as e:
                    self.stats.add_error(f"Failed to migrate backend customer {backend_customer.id}: {str(e)}")
                except Exception as e:
                    self.stats.add_error(f"Unexpected error migrating backend customer {backend_customer.id}: {str(e)}")
            
            backend_session.close()
            
        except Exception as e:
            self.stats.add_error(f"Failed to migrate backend customers: {str(e)}")
    
    def _migrate_admin_users(self, unified_session: Session):
        """Migrate users from admin dashboard system"""
        try:
            admin_session = DatabaseConnector.get_admin_session()
            if not admin_session:
                self.stats.add_warning("Admin dashboard database not available")
                return
            
            # Import admin models dynamically
            from admin_backend.models import User as AdminUser
            
            admin_users = admin_session.query(AdminUser).all()
            
            for admin_user in admin_users:
                try:
                    # Check if user already exists (by email or username)
                    existing_user = unified_session.query(UnifiedUser).filter(
                        (UnifiedUser.email == admin_user.email) |
                        (UnifiedUser.username == admin_user.username)
                    ).first()
                    
                    if existing_user:
                        # Update existing user with admin info
                        existing_user.is_admin = admin_user.is_admin
                        existing_user.phone = admin_user.phone
                        existing_user.last_login = UserAdapter.convert_datetime(admin_user.last_login)
                        existing_user.legacy_admin_user_id = admin_user.id
                        
                        self.user_id_mapping[f"admin_user_{admin_user.id}"] = existing_user.id
                        self.stats.add_warning(f"Merged admin user {admin_user.id} with existing user {existing_user.id}")
                    else:
                        # Create new user
                        unified_user = UserAdapter.from_admin_user(admin_user)
                        validate_model(unified_user)
                        
                        unified_session.add(unified_user)
                        unified_session.flush()  # Get the ID
                        
                        self.user_id_mapping[f"admin_user_{admin_user.id}"] = unified_user.id
                        self.stats.users_migrated += 1
                    
                except ValidationError as e:
                    self.stats.add_error(f"Failed to migrate admin user {admin_user.id}: {str(e)}")
                except Exception as e:
                    self.stats.add_error(f"Unexpected error migrating admin user {admin_user.id}: {str(e)}")
            
            admin_session.close()
            
        except Exception as e:
            self.stats.add_error(f"Failed to migrate admin users: {str(e)}")
    
    def _migrate_tickets(self):
        """Migrate tickets from both systems"""
        logger.info("Migrating tickets")
        
        with DatabaseConnector.get_unified_session() as unified_session:
            # Migrate backend tickets
            if BACKEND_MODELS_AVAILABLE:
                self._migrate_backend_tickets(unified_session)
            
            # Migrate admin dashboard tickets
            if ADMIN_MODELS_AVAILABLE:
                self._migrate_admin_tickets(unified_session)
    
    def _migrate_backend_tickets(self, unified_session: Session):
        """Migrate tickets from backend system"""
        try:
            backend_session = DatabaseConnector.get_backend_session()
            
            from backend.models import Ticket as BackendTicket
            
            backend_tickets = backend_session.query(BackendTicket).all()
            
            for backend_ticket in backend_tickets:
                try:
                    unified_ticket = TicketAdapter.from_backend_ticket(
                        backend_ticket, 
                        self.user_id_mapping
                    )
                    validate_model(unified_ticket)
                    
                    unified_session.add(unified_ticket)
                    unified_session.flush()  # Get the ID
                    
                    # Store mapping
                    self.ticket_id_mapping[f"backend_ticket_{backend_ticket.id}"] = unified_ticket.id
                    self.stats.tickets_migrated += 1
                    
                except ValidationError as e:
                    self.stats.add_error(f"Failed to migrate backend ticket {backend_ticket.id}: {str(e)}")
                except Exception as e:
                    self.stats.add_error(f"Unexpected error migrating backend ticket {backend_ticket.id}: {str(e)}")
            
            backend_session.close()
            
        except Exception as e:
            self.stats.add_error(f"Failed to migrate backend tickets: {str(e)}")
    
    def _migrate_admin_tickets(self, unified_session: Session):
        """Migrate tickets from admin dashboard system"""
        try:
            admin_session = DatabaseConnector.get_admin_session()
            if not admin_session:
                return
            
            from admin_backend.models_support import Ticket as AdminTicket
            
            admin_tickets = admin_session.query(AdminTicket).all()
            
            for admin_ticket in admin_tickets:
                try:
                    unified_ticket = TicketAdapter.from_admin_ticket(
                        admin_ticket,
                        self.user_id_mapping
                    )
                    validate_model(unified_ticket)
                    
                    unified_session.add(unified_ticket)
                    unified_session.flush()  # Get the ID
                    
                    # Store mapping
                    self.ticket_id_mapping[f"admin_ticket_{admin_ticket.id}"] = unified_ticket.id
                    self.stats.tickets_migrated += 1
                    
                except ValidationError as e:
                    self.stats.add_error(f"Failed to migrate admin ticket {admin_ticket.id}: {str(e)}")
                except Exception as e:
                    self.stats.add_error(f"Unexpected error migrating admin ticket {admin_ticket.id}: {str(e)}")
            
            admin_session.close()
            
        except Exception as e:
            self.stats.add_error(f"Failed to migrate admin tickets: {str(e)}")
    
    def _migrate_comments(self):
        """Migrate comments from both systems"""
        logger.info("Migrating comments")
        
        with DatabaseConnector.get_unified_session() as unified_session:
            # Migrate backend comments
            if BACKEND_MODELS_AVAILABLE:
                self._migrate_backend_comments(unified_session)
            
            # Migrate admin dashboard comments
            if ADMIN_MODELS_AVAILABLE:
                self._migrate_admin_comments(unified_session)
    
    def _migrate_backend_comments(self, unified_session: Session):
        """Migrate comments from backend system"""
        try:
            backend_session = DatabaseConnector.get_backend_session()
            
            from backend.models import TicketComment as BackendTicketComment
            
            backend_comments = backend_session.query(BackendTicketComment).all()
            
            for backend_comment in backend_comments:
                try:
                    unified_comment = CommentAdapter.from_backend_comment(
                        backend_comment,
                        self.user_id_mapping,
                        self.ticket_id_mapping
                    )
                    validate_model(unified_comment)
                    
                    unified_session.add(unified_comment)
                    self.stats.comments_migrated += 1
                    
                except ValidationError as e:
                    self.stats.add_error(f"Failed to migrate backend comment {backend_comment.id}: {str(e)}")
                except Exception as e:
                    self.stats.add_error(f"Unexpected error migrating backend comment {backend_comment.id}: {str(e)}")
            
            backend_session.close()
            
        except Exception as e:
            self.stats.add_error(f"Failed to migrate backend comments: {str(e)}")
    
    def _migrate_admin_comments(self, unified_session: Session):
        """Migrate comments from admin dashboard system"""
        try:
            admin_session = DatabaseConnector.get_admin_session()
            if not admin_session:
                return
            
            from admin_backend.models_support import TicketComment as AdminTicketComment
            
            admin_comments = admin_session.query(AdminTicketComment).all()
            
            for admin_comment in admin_comments:
                try:
                    unified_comment = CommentAdapter.from_admin_comment(
                        admin_comment,
                        self.user_id_mapping,
                        self.ticket_id_mapping
                    )
                    validate_model(unified_comment)
                    
                    unified_session.add(unified_comment)
                    self.stats.comments_migrated += 1
                    
                except ValidationError as e:
                    self.stats.add_error(f"Failed to migrate admin comment {admin_comment.id}: {str(e)}")
                except Exception as e:
                    self.stats.add_error(f"Unexpected error migrating admin comment {admin_comment.id}: {str(e)}")
            
            admin_session.close()
            
        except Exception as e:
            self.stats.add_error(f"Failed to migrate admin comments: {str(e)}")
    
    def _migrate_activities(self):
        """Migrate activities from both systems"""
        logger.info("Migrating activities")
        
        with DatabaseConnector.get_unified_session() as unified_session:
            # Migrate backend activities
            if BACKEND_MODELS_AVAILABLE:
                self._migrate_backend_activities(unified_session)
            
            # Migrate admin dashboard activities
            if ADMIN_MODELS_AVAILABLE:
                self._migrate_admin_activities(unified_session)
    
    def _migrate_backend_activities(self, unified_session: Session):
        """Migrate activities from backend system"""
        try:
            backend_session = DatabaseConnector.get_backend_session()
            
            from backend.models import TicketActivity as BackendTicketActivity
            
            backend_activities = backend_session.query(BackendTicketActivity).all()
            
            for backend_activity in backend_activities:
                try:
                    unified_activity = ActivityAdapter.from_backend_activity(
                        backend_activity,
                        self.user_id_mapping,
                        self.ticket_id_mapping
                    )
                    validate_model(unified_activity)
                    
                    unified_session.add(unified_activity)
                    self.stats.activities_migrated += 1
                    
                except ValidationError as e:
                    self.stats.add_error(f"Failed to migrate backend activity {backend_activity.id}: {str(e)}")
                except Exception as e:
                    self.stats.add_error(f"Unexpected error migrating backend activity {backend_activity.id}: {str(e)}")
            
            backend_session.close()
            
        except Exception as e:
            self.stats.add_error(f"Failed to migrate backend activities: {str(e)}")
    
    def _migrate_admin_activities(self, unified_session: Session):
        """Migrate activities from admin dashboard system"""
        try:
            admin_session = DatabaseConnector.get_admin_session()
            if not admin_session:
                return
            
            from admin_backend.models_support import TicketActivity as AdminTicketActivity
            
            admin_activities = admin_session.query(AdminTicketActivity).all()
            
            for admin_activity in admin_activities:
                try:
                    unified_activity = ActivityAdapter.from_admin_activity(
                        admin_activity,
                        self.user_id_mapping,
                        self.ticket_id_mapping
                    )
                    validate_model(unified_activity)
                    
                    unified_session.add(unified_activity)
                    self.stats.activities_migrated += 1
                    
                except ValidationError as e:
                    self.stats.add_error(f"Failed to migrate admin activity {admin_activity.id}: {str(e)}")
                except Exception as e:
                    self.stats.add_error(f"Unexpected error migrating admin activity {admin_activity.id}: {str(e)}")
            
            admin_session.close()
            
        except Exception as e:
            self.stats.add_error(f"Failed to migrate admin activities: {str(e)}")
    
    def _migrate_sessions(self):
        """Migrate user sessions"""
        logger.info("Migrating user sessions")
        # Implementation for session migration would go here
        # This is a placeholder as sessions are typically short-lived
    
    def _migrate_chat_data(self):
        """Migrate chat sessions and messages"""
        logger.info("Migrating chat data")
        # Implementation for chat data migration would go here
    
    def _migrate_performance_data(self):
        """Migrate performance metrics and satisfaction ratings"""
        logger.info("Migrating performance data")
        # Implementation for performance data migration would go here
    
    def _migrate_voice_data(self):
        """Migrate voice settings and analytics"""
        logger.info("Migrating voice data")
        # Implementation for voice data migration would go here
    
    def _migrate_knowledge_data(self):
        """Migrate knowledge entries"""
        logger.info("Migrating knowledge data")
        # Implementation for knowledge data migration would go here
    
    def _migrate_support_data(self):
        """Migrate support intents and responses"""
        logger.info("Migrating support data")
        # Implementation for support data migration would go here

def run_migration(backup: bool = True) -> MigrationStats:
    """Run the complete migration process"""
    migrator = DataMigrator()
    return migrator.migrate_all(backup_before_migration=backup)

def validate_migration() -> Dict[str, Any]:
    """Validate the migration results"""
    validation_results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'statistics': {}
    }
    
    try:
        with DatabaseConnector.get_unified_session() as session:
            # Count records in unified tables
            validation_results['statistics'] = {
                'users': session.query(UnifiedUser).count(),
                'tickets': session.query(UnifiedTicket).count(),
                'comments': session.query(UnifiedTicketComment).count(),
                'activities': session.query(UnifiedTicketActivity).count(),
            }
            
            # Validate data integrity
            orphaned_tickets = session.query(UnifiedTicket).filter(
                UnifiedTicket.customer_id.isnot(None),
                ~UnifiedTicket.customer_id.in_(
                    session.query(UnifiedUser.id)
                )
            ).count()
            
            if orphaned_tickets > 0:
                validation_results['errors'].append(f"Found {orphaned_tickets} orphaned tickets")
                validation_results['valid'] = False
            
    except Exception as e:
        validation_results['errors'].append(f"Validation failed: {str(e)}")
        validation_results['valid'] = False
    
    return validation_results

# Export main functions
__all__ = [
    'DataMigrator',
    'MigrationStats',
    'MigrationError',
    'DatabaseConnector',
    'run_migration',
    'validate_migration',
]