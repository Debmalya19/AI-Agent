"""
Data Synchronization Service

This module provides real-time synchronization between AI agent conversations and support tickets,
background tasks for data consistency checks, and utilities for converting conversations to tickets.

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from dataclasses import dataclass
from enum import Enum
import json
import hashlib

from backend.database import SessionLocal, get_db
from backend.unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedChatHistory, UnifiedTicketComment,
    UnifiedTicketActivity, TicketStatus, TicketPriority, TicketCategory
)

logger = logging.getLogger(__name__)

class SyncEventType(Enum):
    """Types of synchronization events"""
    CONVERSATION_TO_TICKET = "conversation_to_ticket"
    TICKET_STATUS_CHANGE = "ticket_status_change"
    USER_DATA_UPDATE = "user_data_update"
    CONVERSATION_UPDATE = "conversation_update"

class ConflictResolutionStrategy(Enum):
    """Strategies for resolving data conflicts"""
    LATEST_WINS = "latest_wins"
    MANUAL_REVIEW = "manual_review"
    MERGE_DATA = "merge_data"
    PRESERVE_BOTH = "preserve_both"

@dataclass
class SyncEvent:
    """Represents a synchronization event"""
    event_type: SyncEventType
    entity_id: int
    entity_type: str
    timestamp: datetime
    data: Dict[str, Any]
    user_id: Optional[int] = None
    session_id: Optional[str] = None

@dataclass
class SyncResult:
    """Result of a synchronization operation"""
    success: bool
    message: str
    entity_id: Optional[int] = None
    conflicts_detected: List[str] = None
    actions_taken: List[str] = None
    
    def __post_init__(self):
        if self.conflicts_detected is None:
            self.conflicts_detected = []
        if self.actions_taken is None:
            self.actions_taken = []

@dataclass
class ConsistencyCheckResult:
    """Result of a data consistency check"""
    total_checked: int
    inconsistencies_found: int
    issues: List[Dict[str, Any]]
    resolved_count: int
    errors: List[str]
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.errors is None:
            self.errors = []

class DataSyncService:
    """
    Main data synchronization service that handles real-time sync between
    AI agent conversations and support tickets.
    """
    
    def __init__(self):
        self.sync_events: List[SyncEvent] = []
        self.background_tasks: List[asyncio.Task] = []
        self.is_running = False
        
    async def start_service(self):
        """Start the data synchronization service"""
        if self.is_running:
            logger.warning("Data sync service is already running")
            return
            
        self.is_running = True
        logger.info("Starting data synchronization service")
        
        # Start background tasks
        self.background_tasks = [
            asyncio.create_task(self._consistency_check_task()),
            asyncio.create_task(self._sync_event_processor()),
            asyncio.create_task(self._cleanup_old_events())
        ]
        
        logger.info("Data synchronization service started successfully")
    
    async def stop_service(self):
        """Stop the data synchronization service"""
        if not self.is_running:
            return
            
        self.is_running = False
        logger.info("Stopping data synchronization service")
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
            
        # Wait for tasks to complete
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()
        
        logger.info("Data synchronization service stopped")
    
    def sync_ai_conversation_to_ticket(self, conversation_id: int, ticket_id: Optional[int] = None) -> SyncResult:
        """
        Synchronize AI agent conversation to support ticket
        Requirement: 2.1 - Same information visible in both interfaces
        """
        try:
            with SessionLocal() as db:
                # Get the conversation
                conversation = db.query(UnifiedChatHistory).filter(
                    UnifiedChatHistory.id == conversation_id
                ).first()
                
                if not conversation:
                    return SyncResult(
                        success=False,
                        message=f"Conversation {conversation_id} not found"
                    )
                
                # If ticket_id provided, link to existing ticket
                if ticket_id:
                    ticket = db.query(UnifiedTicket).filter(
                        UnifiedTicket.id == ticket_id
                    ).first()
                    
                    if not ticket:
                        return SyncResult(
                            success=False,
                            message=f"Ticket {ticket_id} not found"
                        )
                    
                    # Link conversation to ticket
                    conversation.ticket_id = ticket_id
                    
                    # Add conversation content as ticket comment
                    if conversation.user_message and conversation.bot_response:
                        comment_content = f"AI Conversation:\nUser: {conversation.user_message}\nAssistant: {conversation.bot_response}"
                        
                        comment = UnifiedTicketComment(
                            ticket_id=ticket_id,
                            author_id=conversation.user_id,
                            comment=comment_content,
                            is_internal=False,
                            created_at=conversation.created_at
                        )
                        db.add(comment)
                        
                        # Add activity record
                        activity = UnifiedTicketActivity(
                            ticket_id=ticket_id,
                            activity_type="conversation_linked",
                            description=f"AI conversation {conversation_id} linked to ticket",
                            performed_by_id=conversation.user_id,
                            created_at=datetime.now(timezone.utc)
                        )
                        db.add(activity)
                    
                    db.commit()
                    
                    return SyncResult(
                        success=True,
                        message=f"Conversation {conversation_id} linked to ticket {ticket_id}",
                        entity_id=ticket_id,
                        actions_taken=["conversation_linked", "comment_added", "activity_recorded"]
                    )
                
                else:
                    # Create new ticket from conversation
                    return self.create_ticket_from_conversation(conversation_id)
                    
        except Exception as e:
            logger.error(f"Error syncing conversation to ticket: {e}")
            return SyncResult(
                success=False,
                message=f"Error syncing conversation: {str(e)}"
            )
    
    def create_ticket_from_conversation(self, conversation_id: int) -> SyncResult:
        """
        Create a support ticket from an AI agent conversation
        Requirement: 2.2 - Support tickets created in either system visible in both
        """
        try:
            with SessionLocal() as db:
                # Get the conversation
                conversation = db.query(UnifiedChatHistory).filter(
                    UnifiedChatHistory.id == conversation_id
                ).first()
                
                if not conversation:
                    return SyncResult(
                        success=False,
                        message=f"Conversation {conversation_id} not found"
                    )
                
                # Determine ticket category and priority from conversation content
                category, priority = self._analyze_conversation_for_ticket_metadata(
                    conversation.user_message, conversation.bot_response
                )
                
                # Create ticket title from user message (truncated)
                title = conversation.user_message[:100] + "..." if len(conversation.user_message) > 100 else conversation.user_message
                
                # Create description from conversation
                description = f"Ticket created from AI conversation:\n\nUser Query: {conversation.user_message}\n\nAI Response: {conversation.bot_response}"
                
                if conversation.tools_used:
                    description += f"\n\nTools Used: {', '.join(conversation.tools_used)}"
                
                # Create the ticket
                ticket = UnifiedTicket(
                    title=title,
                    description=description,
                    status=TicketStatus.OPEN,
                    priority=priority,
                    category=category,
                    customer_id=conversation.user_id,
                    created_at=conversation.created_at or datetime.now(timezone.utc)
                )
                
                db.add(ticket)
                db.flush()  # Get the ticket ID
                
                # Link conversation to ticket
                conversation.ticket_id = ticket.id
                
                # Add initial activity
                activity = UnifiedTicketActivity(
                    ticket_id=ticket.id,
                    activity_type="ticket_created",
                    description=f"Ticket created from AI conversation {conversation_id}",
                    performed_by_id=conversation.user_id,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(activity)
                
                db.commit()
                
                # Queue sync event
                self._queue_sync_event(SyncEvent(
                    event_type=SyncEventType.CONVERSATION_TO_TICKET,
                    entity_id=ticket.id,
                    entity_type="ticket",
                    timestamp=datetime.now(timezone.utc),
                    data={
                        "conversation_id": conversation_id,
                        "ticket_id": ticket.id,
                        "action": "created"
                    },
                    user_id=conversation.user_id,
                    session_id=conversation.session_id
                ))
                
                return SyncResult(
                    success=True,
                    message=f"Ticket {ticket.id} created from conversation {conversation_id}",
                    entity_id=ticket.id,
                    actions_taken=["ticket_created", "conversation_linked", "activity_recorded"]
                )
                
        except Exception as e:
            logger.error(f"Error creating ticket from conversation: {e}")
            return SyncResult(
                success=False,
                message=f"Error creating ticket: {str(e)}"
            )
    
    def sync_user_data(self, user_id: int) -> SyncResult:
        """
        Synchronize user data across systems
        Requirement: 2.3 - Customer data updated in one system reflected in other immediately
        """
        try:
            with SessionLocal() as db:
                user = db.query(UnifiedUser).filter(UnifiedUser.id == user_id).first()
                
                if not user:
                    return SyncResult(
                        success=False,
                        message=f"User {user_id} not found"
                    )
                
                # Check for data consistency issues
                conflicts = []
                actions_taken = []
                
                # Update last_login if needed
                if user.last_login is None:
                    user.last_login = datetime.now(timezone.utc)
                    actions_taken.append("last_login_updated")
                
                # Ensure user has proper role assignment
                if user.role is None:
                    from backend.unified_models import UserRole
                    user.role = UserRole.CUSTOMER
                    actions_taken.append("role_assigned")
                
                # Update timestamp
                user.updated_at = datetime.now(timezone.utc)
                
                db.commit()
                
                # Queue sync event
                self._queue_sync_event(SyncEvent(
                    event_type=SyncEventType.USER_DATA_UPDATE,
                    entity_id=user_id,
                    entity_type="user",
                    timestamp=datetime.now(timezone.utc),
                    data={
                        "user_id": user_id,
                        "actions": actions_taken
                    },
                    user_id=user_id
                ))
                
                return SyncResult(
                    success=True,
                    message=f"User {user_id} data synchronized",
                    entity_id=user_id,
                    conflicts_detected=conflicts,
                    actions_taken=actions_taken
                )
                
        except Exception as e:
            logger.error(f"Error syncing user data: {e}")
            return SyncResult(
                success=False,
                message=f"Error syncing user data: {str(e)}"
            )
    
    def handle_ticket_status_change(self, ticket_id: int, new_status: TicketStatus, user_id: Optional[int] = None) -> SyncResult:
        """
        Handle ticket status changes and sync related data
        Requirement: 2.4 - Search results include data from all integrated sources
        """
        try:
            with SessionLocal() as db:
                ticket = db.query(UnifiedTicket).filter(UnifiedTicket.id == ticket_id).first()
                
                if not ticket:
                    return SyncResult(
                        success=False,
                        message=f"Ticket {ticket_id} not found"
                    )
                
                old_status = ticket.status
                ticket.status = new_status
                ticket.updated_at = datetime.now(timezone.utc)
                
                # Set resolved_at if ticket is being resolved
                if new_status in [TicketStatus.RESOLVED, TicketStatus.CLOSED] and not ticket.resolved_at:
                    ticket.resolved_at = datetime.now(timezone.utc)
                
                # Add activity record
                activity = UnifiedTicketActivity(
                    ticket_id=ticket_id,
                    activity_type="status_change",
                    description=f"Status changed from {old_status.value} to {new_status.value}",
                    performed_by_id=user_id,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(activity)
                
                # Update related conversations if any
                conversations = db.query(UnifiedChatHistory).filter(
                    UnifiedChatHistory.ticket_id == ticket_id
                ).all()
                
                actions_taken = ["status_updated", "activity_recorded"]
                
                if conversations:
                    # Update conversation metadata to reflect ticket status
                    for conv in conversations:
                        if not conv.sources:
                            conv.sources = {}
                        conv.sources["ticket_status"] = new_status.value
                    actions_taken.append("conversations_updated")
                
                db.commit()
                
                # Queue sync event
                self._queue_sync_event(SyncEvent(
                    event_type=SyncEventType.TICKET_STATUS_CHANGE,
                    entity_id=ticket_id,
                    entity_type="ticket",
                    timestamp=datetime.now(timezone.utc),
                    data={
                        "ticket_id": ticket_id,
                        "old_status": old_status.value,
                        "new_status": new_status.value,
                        "conversations_count": len(conversations)
                    },
                    user_id=user_id
                ))
                
                return SyncResult(
                    success=True,
                    message=f"Ticket {ticket_id} status updated to {new_status.value}",
                    entity_id=ticket_id,
                    actions_taken=actions_taken
                )
                
        except Exception as e:
            logger.error(f"Error handling ticket status change: {e}")
            return SyncResult(
                success=False,
                message=f"Error updating ticket status: {str(e)}"
            )
    
    async def perform_consistency_check(self) -> ConsistencyCheckResult:
        """
        Perform comprehensive data consistency check
        Background task for data consistency checks and conflict resolution
        """
        logger.info("Starting data consistency check")
        
        issues = []
        resolved_count = 0
        errors = []
        total_checked = 0
        
        try:
            with SessionLocal() as db:
                # Check 1: Orphaned conversations (conversations without valid users)
                orphaned_conversations = db.query(UnifiedChatHistory).filter(
                    and_(
                        UnifiedChatHistory.user_id.isnot(None),
                        ~UnifiedChatHistory.user_id.in_(
                            db.query(UnifiedUser.id)
                        )
                    )
                ).all()
                
                total_checked += len(orphaned_conversations)
                
                for conv in orphaned_conversations:
                    issues.append({
                        "type": "orphaned_conversation",
                        "entity_id": conv.id,
                        "description": f"Conversation {conv.id} references non-existent user {conv.user_id}",
                        "severity": "medium"
                    })
                    
                    # Auto-resolve: Set user_id to None for orphaned conversations
                    conv.user_id = None
                    resolved_count += 1
                
                # Check 2: Tickets without customers
                orphaned_tickets = db.query(UnifiedTicket).filter(
                    and_(
                        UnifiedTicket.customer_id.isnot(None),
                        ~UnifiedTicket.customer_id.in_(
                            db.query(UnifiedUser.id)
                        )
                    )
                ).all()
                
                total_checked += len(orphaned_tickets)
                
                for ticket in orphaned_tickets:
                    issues.append({
                        "type": "orphaned_ticket",
                        "entity_id": ticket.id,
                        "description": f"Ticket {ticket.id} references non-existent customer {ticket.customer_id}",
                        "severity": "high"
                    })
                    # Don't auto-resolve tickets - they need manual review
                
                # Check 3: Conversations linked to non-existent tickets
                invalid_ticket_links = db.query(UnifiedChatHistory).filter(
                    and_(
                        UnifiedChatHistory.ticket_id.isnot(None),
                        ~UnifiedChatHistory.ticket_id.in_(
                            db.query(UnifiedTicket.id)
                        )
                    )
                ).all()
                
                total_checked += len(invalid_ticket_links)
                
                for conv in invalid_ticket_links:
                    issues.append({
                        "type": "invalid_ticket_link",
                        "entity_id": conv.id,
                        "description": f"Conversation {conv.id} linked to non-existent ticket {conv.ticket_id}",
                        "severity": "medium"
                    })
                    
                    # Auto-resolve: Remove invalid ticket link
                    conv.ticket_id = None
                    resolved_count += 1
                
                # Check 4: Duplicate conversations (same session_id, user_message, timestamp)
                duplicate_conversations = db.execute(text("""
                    SELECT session_id, user_message, created_at, COUNT(*) as count
                    FROM unified_chat_history 
                    WHERE session_id IS NOT NULL AND user_message IS NOT NULL
                    GROUP BY session_id, user_message, created_at
                    HAVING COUNT(*) > 1
                """)).fetchall()
                
                total_checked += len(duplicate_conversations)
                
                for dup in duplicate_conversations:
                    issues.append({
                        "type": "duplicate_conversation",
                        "entity_id": None,
                        "description": f"Duplicate conversations found for session {dup.session_id}",
                        "severity": "low",
                        "count": dup.count
                    })
                
                # Check 5: Tickets with inconsistent timestamps
                inconsistent_tickets = db.query(UnifiedTicket).filter(
                    UnifiedTicket.resolved_at < UnifiedTicket.created_at
                ).all()
                
                total_checked += len(inconsistent_tickets)
                
                for ticket in inconsistent_tickets:
                    issues.append({
                        "type": "inconsistent_timestamps",
                        "entity_id": ticket.id,
                        "description": f"Ticket {ticket.id} has resolved_at before created_at",
                        "severity": "medium"
                    })
                    
                    # Auto-resolve: Clear invalid resolved_at
                    ticket.resolved_at = None
                    resolved_count += 1
                
                # Check 6: Users with missing required fields
                incomplete_users = db.query(UnifiedUser).filter(
                    or_(
                        UnifiedUser.email.is_(None),
                        UnifiedUser.username.is_(None),
                        UnifiedUser.user_id.is_(None)
                    )
                ).all()
                
                total_checked += len(incomplete_users)
                
                for user in incomplete_users:
                    issues.append({
                        "type": "incomplete_user",
                        "entity_id": user.id,
                        "description": f"User {user.id} missing required fields",
                        "severity": "high"
                    })
                
                # Commit all auto-resolutions
                if resolved_count > 0:
                    db.commit()
                    logger.info(f"Auto-resolved {resolved_count} consistency issues")
                
        except Exception as e:
            error_msg = f"Error during consistency check: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        result = ConsistencyCheckResult(
            total_checked=total_checked,
            inconsistencies_found=len(issues),
            issues=issues,
            resolved_count=resolved_count,
            errors=errors
        )
        
        logger.info(f"Consistency check completed: {result.inconsistencies_found} issues found, {result.resolved_count} resolved")
        return result
    
    def _analyze_conversation_for_ticket_metadata(self, user_message: str, bot_response: str) -> Tuple[TicketCategory, TicketPriority]:
        """
        Analyze conversation content to determine appropriate ticket category and priority
        """
        user_msg_lower = user_message.lower() if user_message else ""
        bot_msg_lower = bot_response.lower() if bot_response else ""
        
        # Determine category
        category = TicketCategory.GENERAL
        
        if any(word in user_msg_lower for word in ["bill", "payment", "charge", "invoice", "cost", "price"]):
            category = TicketCategory.BILLING
        elif any(word in user_msg_lower for word in ["technical", "error", "bug", "not working", "broken", "issue"]):
            category = TicketCategory.TECHNICAL
        elif any(word in user_msg_lower for word in ["account", "login", "password", "profile", "settings"]):
            category = TicketCategory.ACCOUNT
        elif any(word in user_msg_lower for word in ["feature", "request", "suggestion", "improvement"]):
            category = TicketCategory.FEATURE_REQUEST
        elif any(word in user_msg_lower for word in ["bug", "error", "crash", "problem"]):
            category = TicketCategory.BUG_REPORT
        
        # Determine priority
        priority = TicketPriority.MEDIUM
        
        if any(word in user_msg_lower for word in ["urgent", "critical", "emergency", "asap", "immediately"]):
            priority = TicketPriority.CRITICAL
        elif any(word in user_msg_lower for word in ["important", "high", "priority", "soon"]):
            priority = TicketPriority.HIGH
        elif any(word in user_msg_lower for word in ["low", "minor", "whenever", "no rush"]):
            priority = TicketPriority.LOW
        
        return category, priority
    
    def _queue_sync_event(self, event: SyncEvent):
        """Queue a synchronization event for processing"""
        self.sync_events.append(event)
        logger.debug(f"Queued sync event: {event.event_type.value} for {event.entity_type} {event.entity_id}")
    
    async def _sync_event_processor(self):
        """Background task to process synchronization events"""
        while self.is_running:
            try:
                if self.sync_events:
                    # Process events in batches
                    batch_size = 10
                    events_to_process = self.sync_events[:batch_size]
                    self.sync_events = self.sync_events[batch_size:]
                    
                    for event in events_to_process:
                        await self._process_sync_event(event)
                
                # Wait before next processing cycle
                await asyncio.sleep(5)  # Process every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in sync event processor: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def _process_sync_event(self, event: SyncEvent):
        """Process a single synchronization event"""
        try:
            logger.debug(f"Processing sync event: {event.event_type.value}")
            
            # Log the event for audit purposes
            with SessionLocal() as db:
                # You could create a sync_events table to log all events
                # For now, we'll just log to application logs
                logger.info(f"Sync event processed: {event.event_type.value} for {event.entity_type} {event.entity_id}")
                
                # Perform any additional sync operations based on event type
                if event.event_type == SyncEventType.CONVERSATION_TO_TICKET:
                    # Additional processing for conversation-to-ticket sync
                    pass
                elif event.event_type == SyncEventType.TICKET_STATUS_CHANGE:
                    # Additional processing for ticket status changes
                    pass
                elif event.event_type == SyncEventType.USER_DATA_UPDATE:
                    # Additional processing for user data updates
                    pass
                
        except Exception as e:
            logger.error(f"Error processing sync event {event.event_type.value}: {e}")
    
    async def _consistency_check_task(self):
        """Background task for periodic consistency checks"""
        while self.is_running:
            try:
                logger.info("Running scheduled consistency check")
                result = await self.perform_consistency_check()
                
                if result.errors:
                    logger.error(f"Consistency check had errors: {result.errors}")
                
                if result.inconsistencies_found > 0:
                    logger.warning(f"Found {result.inconsistencies_found} data inconsistencies")
                
                # Wait 1 hour before next check
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in consistency check task: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes on error
    
    async def _cleanup_old_events(self):
        """Background task to cleanup old sync events"""
        while self.is_running:
            try:
                # Keep only events from last 24 hours
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                
                # Remove old events from memory
                self.sync_events = [
                    event for event in self.sync_events 
                    if event.timestamp > cutoff_time
                ]
                
                logger.debug(f"Cleaned up old sync events, {len(self.sync_events)} remaining")
                
                # Wait 6 hours before next cleanup
                await asyncio.sleep(21600)
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

# Global instance of the data sync service
data_sync_service = DataSyncService()

# Utility functions for easy access
async def start_data_sync_service():
    """Start the global data synchronization service"""
    await data_sync_service.start_service()

async def stop_data_sync_service():
    """Stop the global data synchronization service"""
    await data_sync_service.stop_service()

def sync_conversation_to_ticket(conversation_id: int, ticket_id: Optional[int] = None) -> SyncResult:
    """Sync AI conversation to support ticket"""
    return data_sync_service.sync_ai_conversation_to_ticket(conversation_id, ticket_id)

def create_ticket_from_conversation(conversation_id: int) -> SyncResult:
    """Create support ticket from AI conversation"""
    return data_sync_service.create_ticket_from_conversation(conversation_id)

def sync_user_data(user_id: int) -> SyncResult:
    """Sync user data across systems"""
    return data_sync_service.sync_user_data(user_id)

def handle_ticket_status_change(ticket_id: int, new_status: TicketStatus, user_id: Optional[int] = None) -> SyncResult:
    """Handle ticket status change and sync related data"""
    return data_sync_service.handle_ticket_status_change(ticket_id, new_status, user_id)

async def perform_consistency_check() -> ConsistencyCheckResult:
    """Perform data consistency check"""
    return await data_sync_service.perform_consistency_check()