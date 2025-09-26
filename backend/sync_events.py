"""
Event-driven synchronization system

This module provides event-driven synchronization using database triggers
and application events for real-time data sync between AI agent conversations
and support tickets.

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from sqlalchemy import event, text
from sqlalchemy.orm import Session
from dataclasses import dataclass
from enum import Enum
import json

from backend.database import SessionLocal, engine
from backend.unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedChatHistory, UnifiedTicketComment,
    UnifiedTicketActivity, TicketStatus
)

logger = logging.getLogger(__name__)

class EventTriggerType(Enum):
    """Types of database event triggers"""
    AFTER_INSERT = "after_insert"
    AFTER_UPDATE = "after_update"
    AFTER_DELETE = "after_delete"
    BEFORE_INSERT = "before_insert"
    BEFORE_UPDATE = "before_update"

@dataclass
class SyncEventData:
    """Data structure for synchronization events"""
    table_name: str
    operation: str
    entity_id: int
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

class EventDrivenSyncManager:
    """
    Manages event-driven synchronization between database entities
    """
    
    def __init__(self):
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.is_initialized = False
        
    def initialize(self):
        """Initialize event-driven synchronization"""
        if self.is_initialized:
            return
            
        logger.info("Initializing event-driven synchronization")
        
        # Register SQLAlchemy event listeners
        self._register_sqlalchemy_events()
        
        # Create database triggers for real-time sync
        self._create_database_triggers()
        
        self.is_initialized = True
        logger.info("Event-driven synchronization initialized successfully")
    
    def _register_sqlalchemy_events(self):
        """Register SQLAlchemy event listeners for model changes"""
        
        # Chat History events
        @event.listens_for(UnifiedChatHistory, 'after_insert')
        def chat_history_inserted(mapper, connection, target):
            """Handle new chat history entries"""
            asyncio.create_task(self._handle_chat_history_event(
                'insert', target, connection
            ))
        
        @event.listens_for(UnifiedChatHistory, 'after_update')
        def chat_history_updated(mapper, connection, target):
            """Handle chat history updates"""
            asyncio.create_task(self._handle_chat_history_event(
                'update', target, connection
            ))
        
        # Ticket events
        @event.listens_for(UnifiedTicket, 'after_insert')
        def ticket_inserted(mapper, connection, target):
            """Handle new ticket creation"""
            asyncio.create_task(self._handle_ticket_event(
                'insert', target, connection
            ))
        
        @event.listens_for(UnifiedTicket, 'after_update')
        def ticket_updated(mapper, connection, target):
            """Handle ticket updates"""
            asyncio.create_task(self._handle_ticket_event(
                'update', target, connection
            ))
        
        # User events - temporarily disabled to prevent session binding issues
        # @event.listens_for(UnifiedUser, 'after_update')
        # def user_updated(mapper, connection, target):
        #     """Handle user data updates"""
        #     asyncio.create_task(self._handle_user_event(
        #         'update', target, connection
        #     ))
        
        # Ticket Comment events
        @event.listens_for(UnifiedTicketComment, 'after_insert')
        def ticket_comment_inserted(mapper, connection, target):
            """Handle new ticket comments"""
            asyncio.create_task(self._handle_ticket_comment_event(
                'insert', target, connection
            ))
        
        logger.info("SQLAlchemy event listeners registered")
    
    def _create_database_triggers(self):
        """Create database triggers for real-time synchronization"""
        try:
            # Check database type - only PostgreSQL supports these advanced triggers
            db_url = str(engine.url)
            if 'sqlite' in db_url.lower():
                logger.info("SQLite detected - skipping PostgreSQL-specific triggers")
                return
            elif 'postgresql' not in db_url.lower():
                logger.warning(f"Database type not fully supported for triggers: {db_url}")
                return
                
            with SessionLocal() as db:
                # Create trigger function for chat history changes
                chat_history_trigger_sql = """
                CREATE OR REPLACE FUNCTION notify_chat_history_change()
                RETURNS TRIGGER AS $$
                BEGIN
                    -- Notify application of chat history changes
                    PERFORM pg_notify('chat_history_changed', 
                        json_build_object(
                            'operation', TG_OP,
                            'table', TG_TABLE_NAME,
                            'id', COALESCE(NEW.id, OLD.id),
                            'user_id', COALESCE(NEW.user_id, OLD.user_id),
                            'ticket_id', COALESCE(NEW.ticket_id, OLD.ticket_id),
                            'timestamp', NOW()
                        )::text
                    );
                    
                    -- Auto-link conversations to tickets based on content analysis
                    IF TG_OP = 'INSERT' AND NEW.user_message IS NOT NULL THEN
                        -- Check if this conversation should create a ticket
                        IF NEW.user_message ILIKE '%problem%' OR 
                           NEW.user_message ILIKE '%issue%' OR 
                           NEW.user_message ILIKE '%help%' OR
                           NEW.user_message ILIKE '%support%' THEN
                            -- Mark for ticket creation (could be handled by application)
                            PERFORM pg_notify('create_ticket_from_conversation',
                                json_build_object(
                                    'conversation_id', NEW.id,
                                    'user_id', NEW.user_id,
                                    'priority', 'medium'
                                )::text
                            );
                        END IF;
                    END IF;
                    
                    RETURN COALESCE(NEW, OLD);
                END;
                $$ LANGUAGE plpgsql;
                """
                
                # Create trigger function for ticket changes
                ticket_trigger_sql = """
                CREATE OR REPLACE FUNCTION notify_ticket_change()
                RETURNS TRIGGER AS $$
                BEGIN
                    -- Notify application of ticket changes
                    PERFORM pg_notify('ticket_changed',
                        json_build_object(
                            'operation', TG_OP,
                            'table', TG_TABLE_NAME,
                            'id', COALESCE(NEW.id, OLD.id),
                            'customer_id', COALESCE(NEW.customer_id, OLD.customer_id),
                            'status', COALESCE(NEW.status, OLD.status),
                            'old_status', CASE WHEN TG_OP = 'UPDATE' THEN OLD.status ELSE NULL END,
                            'timestamp', NOW()
                        )::text
                    );
                    
                    -- Auto-update related conversations when ticket status changes
                    IF TG_OP = 'UPDATE' AND OLD.status != NEW.status THEN
                        -- Update conversation metadata
                        UPDATE unified_chat_history 
                        SET sources = COALESCE(sources, '{}'::jsonb) || 
                                     json_build_object('ticket_status', NEW.status)::jsonb
                        WHERE ticket_id = NEW.id;
                        
                        -- Create activity record
                        INSERT INTO unified_ticket_activities (
                            ticket_id, activity_type, description, 
                            performed_by_id, created_at
                        ) VALUES (
                            NEW.id, 'auto_sync', 
                            'Conversations updated due to status change',
                            NEW.assigned_agent_id, NOW()
                        );
                    END IF;
                    
                    RETURN COALESCE(NEW, OLD);
                END;
                $$ LANGUAGE plpgsql;
                """
                
                # Create trigger function for user changes
                user_trigger_sql = """
                CREATE OR REPLACE FUNCTION notify_user_change()
                RETURNS TRIGGER AS $$
                BEGIN
                    -- Notify application of user changes
                    PERFORM pg_notify('user_changed',
                        json_build_object(
                            'operation', TG_OP,
                            'table', TG_TABLE_NAME,
                            'id', COALESCE(NEW.id, OLD.id),
                            'user_id', COALESCE(NEW.user_id, OLD.user_id),
                            'email', COALESCE(NEW.email, OLD.email),
                            'timestamp', NOW()
                        )::text
                    );
                    
                    -- Update last_login timestamp
                    IF TG_OP = 'UPDATE' AND NEW.last_login IS NULL THEN
                        NEW.last_login = NOW();
                    END IF;
                    
                    RETURN COALESCE(NEW, OLD);
                END;
                $$ LANGUAGE plpgsql;
                """
                
                # Execute trigger function creation
                db.execute(text(chat_history_trigger_sql))
                db.execute(text(ticket_trigger_sql))
                db.execute(text(user_trigger_sql))
                
                # Create actual triggers
                triggers_sql = [
                    # Chat history triggers
                    """
                    DROP TRIGGER IF EXISTS chat_history_sync_trigger ON unified_chat_history;
                    CREATE TRIGGER chat_history_sync_trigger
                        AFTER INSERT OR UPDATE ON unified_chat_history
                        FOR EACH ROW EXECUTE FUNCTION notify_chat_history_change();
                    """,
                    
                    # Ticket triggers
                    """
                    DROP TRIGGER IF EXISTS ticket_sync_trigger ON unified_tickets;
                    CREATE TRIGGER ticket_sync_trigger
                        AFTER INSERT OR UPDATE ON unified_tickets
                        FOR EACH ROW EXECUTE FUNCTION notify_ticket_change();
                    """,
                    
                    # User triggers
                    """
                    DROP TRIGGER IF EXISTS user_sync_trigger ON unified_users;
                    CREATE TRIGGER user_sync_trigger
                        AFTER UPDATE ON unified_users
                        FOR EACH ROW EXECUTE FUNCTION notify_user_change();
                    """
                ]
                
                for trigger_sql in triggers_sql:
                    db.execute(text(trigger_sql))
                
                db.commit()
                logger.info("Database triggers created successfully")
                
        except Exception as e:
            logger.error(f"Error creating database triggers: {e}")
            # Continue without triggers - application events will still work
    
    async def _handle_chat_history_event(self, operation: str, target: UnifiedChatHistory, connection):
        """Handle chat history events"""
        try:
            # Create a new session to safely access the chat history object
            with SessionLocal() as db:
                # Re-fetch the chat history to ensure it's bound to this session
                chat = db.query(UnifiedChatHistory).filter(UnifiedChatHistory.id == target.id).first()
                if not chat:
                    logger.warning(f"Chat history {target.id} not found during event handling")
                    return
                
                event_data = SyncEventData(
                    table_name="unified_chat_history",
                    operation=operation,
                    entity_id=chat.id,
                    new_values={
                        "user_id": chat.user_id,
                        "session_id": chat.session_id,
                        "user_message": chat.user_message,
                        "bot_response": chat.bot_response,
                        "ticket_id": chat.ticket_id
                    }
                )
                
                # Trigger registered event handlers
                await self._trigger_event_handlers("chat_history_changed", event_data)
                
                # Auto-create ticket if conversation indicates need for support
                if operation == "insert" and chat.user_message:
                    if await self._should_create_ticket_from_conversation(chat):
                        from backend.data_sync_service import create_ticket_from_conversation
                        result = create_ticket_from_conversation(chat.id)
                        if result.success:
                            logger.info(f"Auto-created ticket {result.entity_id} from conversation {chat.id}")
            
        except Exception as e:
            logger.error(f"Error handling chat history event: {e}")
    
    async def _handle_ticket_event(self, operation: str, target: UnifiedTicket, connection):
        """Handle ticket events"""
        try:
            # Create a new session to safely access the ticket object
            with SessionLocal() as db:
                # Re-fetch the ticket to ensure it's bound to this session
                ticket = db.query(UnifiedTicket).filter(UnifiedTicket.id == target.id).first()
                if not ticket:
                    logger.warning(f"Ticket {target.id} not found during event handling")
                    return
                
                event_data = SyncEventData(
                    table_name="unified_tickets",
                    operation=operation,
                    entity_id=ticket.id,
                    new_values={
                        "customer_id": ticket.customer_id,
                        "status": ticket.status.value if ticket.status else None,
                        "priority": ticket.priority.value if ticket.priority else None,
                        "category": ticket.category.value if ticket.category else None,
                        "title": ticket.title
                    }
                )
                
                # Trigger registered event handlers
                await self._trigger_event_handlers("ticket_changed", event_data)
            
        except Exception as e:
            logger.error(f"Error handling ticket event: {e}")
    
    async def _handle_user_event(self, operation: str, target: UnifiedUser, connection):
        """Handle user events"""
        try:
            # Create a new session to safely access the user object
            with SessionLocal() as db:
                # Re-fetch the user to ensure it's bound to this session
                user = db.query(UnifiedUser).filter(UnifiedUser.id == target.id).first()
                if not user:
                    logger.warning(f"User {target.id} not found during event handling")
                    return
                
                event_data = SyncEventData(
                    table_name="unified_users",
                    operation=operation,
                    entity_id=user.id,
                    new_values={
                        "user_id": user.user_id,
                        "username": user.username,
                        "email": user.email,
                        "is_active": user.is_active,
                        "role": user.role.value if user.role else None
                    }
                )
                
                # Trigger registered event handlers
                await self._trigger_event_handlers("user_changed", event_data)
            
        except Exception as e:
            logger.error(f"Error handling user event: {e}")
    
    async def _handle_ticket_comment_event(self, operation: str, target: UnifiedTicketComment, connection):
        """Handle ticket comment events"""
        try:
            # Create a new session to safely access the comment object
            with SessionLocal() as db:
                # Re-fetch the comment to ensure it's bound to this session
                comment = db.query(UnifiedTicketComment).filter(UnifiedTicketComment.id == target.id).first()
                if not comment:
                    logger.warning(f"Ticket comment {target.id} not found during event handling")
                    return
                
                event_data = SyncEventData(
                    table_name="unified_ticket_comments",
                    operation=operation,
                    entity_id=comment.id,
                    new_values={
                        "ticket_id": comment.ticket_id,
                        "author_id": comment.author_id,
                        "comment": comment.comment,
                        "is_internal": comment.is_internal
                    }
                )
                
                # Trigger registered event handlers
                await self._trigger_event_handlers("ticket_comment_added", event_data)
                
                # Update ticket's updated_at timestamp
                if operation == "insert":
                    ticket = db.query(UnifiedTicket).filter(
                        UnifiedTicket.id == comment.ticket_id
                    ).first()
                    if ticket:
                        ticket.updated_at = datetime.now(timezone.utc)
                        db.commit()
            
        except Exception as e:
            logger.error(f"Error handling ticket comment event: {e}")
    
    async def _should_create_ticket_from_conversation(self, conversation: UnifiedChatHistory) -> bool:
        """
        Determine if a conversation should automatically create a support ticket
        """
        if not conversation.user_message:
            return False
        
        user_msg_lower = conversation.user_message.lower()
        
        # Keywords that indicate need for support ticket
        support_keywords = [
            "problem", "issue", "help", "support", "error", "bug", 
            "not working", "broken", "can't", "unable", "difficulty",
            "complaint", "billing issue", "technical problem"
        ]
        
        # Check if message contains support keywords
        has_support_keywords = any(keyword in user_msg_lower for keyword in support_keywords)
        
        # Check message length (longer messages more likely to need tickets)
        is_substantial = len(conversation.user_message) > 50
        
        # Check if user is authenticated (more likely to need tickets)
        has_user = conversation.user_id is not None
        
        return has_support_keywords and is_substantial and has_user
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler for a specific event type"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered event handler for {event_type}")
    
    async def _trigger_event_handlers(self, event_type: str, event_data: SyncEventData):
        """Trigger all registered handlers for an event type"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event_data)
                    else:
                        handler(event_data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")

# Global instance
event_sync_manager = EventDrivenSyncManager()

# Utility functions
def initialize_event_sync():
    """Initialize event-driven synchronization"""
    event_sync_manager.initialize()

def register_sync_event_handler(event_type: str, handler: Callable):
    """Register an event handler"""
    event_sync_manager.register_event_handler(event_type, handler)

# Example event handlers
async def log_sync_event(event_data: SyncEventData):
    """Example event handler that logs sync events"""
    logger.info(f"Sync event: {event_data.operation} on {event_data.table_name} (ID: {event_data.entity_id})")

def setup_default_event_handlers():
    """Setup default event handlers"""
    register_sync_event_handler("chat_history_changed", log_sync_event)
    register_sync_event_handler("ticket_changed", log_sync_event)
    register_sync_event_handler("user_changed", log_sync_event)
    register_sync_event_handler("ticket_comment_added", log_sync_event)