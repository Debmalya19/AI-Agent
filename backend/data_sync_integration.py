"""
Data Synchronization Integration

This module integrates the data synchronization service with the main FastAPI application,
providing startup/shutdown hooks and API endpoints for monitoring sync status.

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.data_sync_service import (
    data_sync_service, start_data_sync_service, stop_data_sync_service,
    sync_conversation_to_ticket, create_ticket_from_conversation,
    sync_user_data, handle_ticket_status_change, perform_consistency_check
)
from backend.sync_events import (
    event_sync_manager, initialize_event_sync, setup_default_event_handlers
)
from backend.conversation_to_ticket_utils import (
    analyze_conversation_for_ticket, should_create_ticket_from_conversation
)
from backend.unified_models import UnifiedChatHistory, UnifiedTicket, TicketStatus

logger = logging.getLogger(__name__)

# Create router for data sync endpoints
sync_router = APIRouter(prefix="/api/sync", tags=["data-synchronization"])

class DataSyncIntegration:
    """
    Integration class for data synchronization with the main application
    """
    
    def __init__(self):
        self.is_initialized = False
        self.startup_tasks = []
        self.shutdown_tasks = []
    
    async def initialize(self):
        """Initialize data synchronization integration"""
        if self.is_initialized:
            return
        
        logger.info("Initializing data synchronization integration")
        
        try:
            # Initialize event-driven synchronization
            initialize_event_sync()
            setup_default_event_handlers()
            
            # Start the data sync service
            await start_data_sync_service()
            
            # Register custom event handlers
            self._register_custom_event_handlers()
            
            self.is_initialized = True
            logger.info("Data synchronization integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize data synchronization: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown data synchronization integration"""
        if not self.is_initialized:
            return
        
        logger.info("Shutting down data synchronization integration")
        
        try:
            # Stop the data sync service
            await stop_data_sync_service()
            
            self.is_initialized = False
            logger.info("Data synchronization integration shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during data sync shutdown: {e}")
    
    def _register_custom_event_handlers(self):
        """Register custom event handlers for the application"""
        from backend.sync_events import register_sync_event_handler
        
        # Handler for automatic ticket creation
        async def auto_ticket_creation_handler(event_data):
            """Automatically create tickets for conversations that need them"""
            if (event_data.table_name == "unified_chat_history" and 
                event_data.operation == "insert" and 
                event_data.entity_id):
                
                try:
                    # Check if conversation should create a ticket
                    if should_create_ticket_from_conversation(event_data.entity_id, threshold=0.7):
                        result = create_ticket_from_conversation(event_data.entity_id)
                        if result.success:
                            logger.info(f"Auto-created ticket {result.entity_id} from conversation {event_data.entity_id}")
                        else:
                            logger.warning(f"Failed to auto-create ticket from conversation {event_data.entity_id}: {result.message}")
                
                except Exception as e:
                    logger.error(f"Error in auto ticket creation handler: {e}")
        
        # Handler for user data synchronization
        async def user_sync_handler(event_data):
            """Sync user data when changes occur"""
            if (event_data.table_name == "unified_users" and 
                event_data.operation == "update" and 
                event_data.entity_id):
                
                try:
                    result = sync_user_data(event_data.entity_id)
                    if not result.success:
                        logger.warning(f"User sync failed for user {event_data.entity_id}: {result.message}")
                
                except Exception as e:
                    logger.error(f"Error in user sync handler: {e}")
        
        # Register the handlers
        register_sync_event_handler("chat_history_changed", auto_ticket_creation_handler)
        register_sync_event_handler("user_changed", user_sync_handler)
        
        logger.info("Custom event handlers registered")

# Global integration instance
data_sync_integration = DataSyncIntegration()

# FastAPI lifespan integration functions
async def startup_data_sync():
    """Startup function for data synchronization (call from main app lifespan)"""
    await data_sync_integration.initialize()

async def shutdown_data_sync():
    """Shutdown function for data synchronization (call from main app lifespan)"""
    await data_sync_integration.shutdown()

# API Endpoints for monitoring and control

@sync_router.get("/status")
async def get_sync_status():
    """Get current synchronization service status"""
    try:
        status = {
            "service_running": data_sync_service.is_running,
            "initialized": data_sync_integration.is_initialized,
            "background_tasks": len(data_sync_service.background_tasks),
            "queued_events": len(data_sync_service.sync_events),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return JSONResponse(content=status)
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sync status")

@sync_router.post("/consistency-check")
async def trigger_consistency_check(background_tasks: BackgroundTasks):
    """Trigger a manual data consistency check"""
    try:
        async def run_consistency_check():
            result = await perform_consistency_check()
            logger.info(f"Manual consistency check completed: {result.inconsistencies_found} issues found, {result.resolved_count} resolved")
        
        background_tasks.add_task(run_consistency_check)
        
        return JSONResponse(content={
            "message": "Consistency check started",
            "status": "running"
        })
        
    except Exception as e:
        logger.error(f"Error triggering consistency check: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger consistency check")

@sync_router.post("/conversations/{conversation_id}/analyze")
async def analyze_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Analyze a conversation for ticket creation potential"""
    try:
        # Verify conversation exists
        conversation = db.query(UnifiedChatHistory).filter(
            UnifiedChatHistory.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Analyze conversation
        analysis = analyze_conversation_for_ticket(conversation_id)
        
        return JSONResponse(content={
            "conversation_id": conversation_id,
            "analysis_result": analysis.analysis_result.value,
            "confidence_score": analysis.confidence_score,
            "reasoning": analysis.reasoning,
            "ticket_metadata": {
                "title": analysis.ticket_metadata.title if analysis.ticket_metadata else None,
                "category": analysis.ticket_metadata.category.value if analysis.ticket_metadata else None,
                "priority": analysis.ticket_metadata.priority.value if analysis.ticket_metadata else None,
                "urgency_score": analysis.ticket_metadata.urgency_score if analysis.ticket_metadata else None,
                "complexity_score": analysis.ticket_metadata.complexity_score if analysis.ticket_metadata else None,
                "sentiment_score": analysis.ticket_metadata.sentiment_score if analysis.ticket_metadata else None,
                "tags": analysis.ticket_metadata.tags if analysis.ticket_metadata else []
            } if analysis.ticket_metadata else None,
            "extracted_entities": analysis.extracted_entities
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze conversation")

@sync_router.post("/conversations/{conversation_id}/create-ticket")
async def create_ticket_from_conversation_endpoint(conversation_id: int, db: Session = Depends(get_db)):
    """Create a support ticket from a conversation"""
    try:
        # Verify conversation exists
        conversation = db.query(UnifiedChatHistory).filter(
            UnifiedChatHistory.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Check if conversation already has a ticket
        if conversation.ticket_id:
            raise HTTPException(status_code=400, detail="Conversation already linked to a ticket")
        
        # Create ticket
        result = create_ticket_from_conversation(conversation_id)
        
        if result.success:
            return JSONResponse(content={
                "success": True,
                "ticket_id": result.entity_id,
                "message": result.message,
                "actions_taken": result.actions_taken
            })
        else:
            raise HTTPException(status_code=400, detail=result.message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ticket from conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create ticket")

@sync_router.post("/conversations/{conversation_id}/link-ticket/{ticket_id}")
async def link_conversation_to_ticket(conversation_id: int, ticket_id: int, db: Session = Depends(get_db)):
    """Link an existing conversation to an existing ticket"""
    try:
        # Verify conversation exists
        conversation = db.query(UnifiedChatHistory).filter(
            UnifiedChatHistory.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Verify ticket exists
        ticket = db.query(UnifiedTicket).filter(
            UnifiedTicket.id == ticket_id
        ).first()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Link conversation to ticket
        result = sync_conversation_to_ticket(conversation_id, ticket_id)
        
        if result.success:
            return JSONResponse(content={
                "success": True,
                "message": result.message,
                "actions_taken": result.actions_taken
            })
        else:
            raise HTTPException(status_code=400, detail=result.message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking conversation {conversation_id} to ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to link conversation to ticket")

@sync_router.post("/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: int, 
    new_status: str, 
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Update ticket status and sync related data"""
    try:
        # Verify ticket exists
        ticket = db.query(UnifiedTicket).filter(
            UnifiedTicket.id == ticket_id
        ).first()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Validate status
        try:
            status_enum = TicketStatus(new_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")
        
        # Update ticket status
        result = handle_ticket_status_change(ticket_id, status_enum, user_id)
        
        if result.success:
            return JSONResponse(content={
                "success": True,
                "message": result.message,
                "actions_taken": result.actions_taken
            })
        else:
            raise HTTPException(status_code=400, detail=result.message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ticket {ticket_id} status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update ticket status")

@sync_router.get("/users/{user_id}/sync")
async def sync_user_data_endpoint(user_id: int, db: Session = Depends(get_db)):
    """Manually sync user data across systems"""
    try:
        # Verify user exists
        from backend.unified_models import UnifiedUser
        user = db.query(UnifiedUser).filter(UnifiedUser.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Sync user data
        result = sync_user_data(user_id)
        
        if result.success:
            return JSONResponse(content={
                "success": True,
                "message": result.message,
                "actions_taken": result.actions_taken,
                "conflicts_detected": result.conflicts_detected
            })
        else:
            raise HTTPException(status_code=400, detail=result.message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing user {user_id} data: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync user data")

@sync_router.get("/events/recent")
async def get_recent_sync_events(limit: int = 50):
    """Get recent synchronization events"""
    try:
        # Get recent events from the service
        recent_events = data_sync_service.sync_events[-limit:] if data_sync_service.sync_events else []
        
        events_data = []
        for event in recent_events:
            events_data.append({
                "event_type": event.event_type.value,
                "entity_id": event.entity_id,
                "entity_type": event.entity_type,
                "timestamp": event.timestamp.isoformat(),
                "user_id": event.user_id,
                "session_id": event.session_id,
                "data": event.data
            })
        
        return JSONResponse(content={
            "events": events_data,
            "total_events": len(events_data),
            "service_running": data_sync_service.is_running
        })
        
    except Exception as e:
        logger.error(f"Error getting recent sync events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sync events")

# Background task for periodic sync health monitoring
async def sync_health_monitor():
    """Background task to monitor sync service health"""
    while data_sync_service.is_running:
        try:
            # Check service health
            if not data_sync_service.is_running:
                logger.warning("Data sync service is not running")
            
            # Check for excessive queued events
            if len(data_sync_service.sync_events) > 1000:
                logger.warning(f"High number of queued sync events: {len(data_sync_service.sync_events)}")
            
            # Check background task health
            active_tasks = [task for task in data_sync_service.background_tasks if not task.done()]
            if len(active_tasks) != len(data_sync_service.background_tasks):
                logger.warning("Some background sync tasks have stopped")
            
            # Wait before next check
            await asyncio.sleep(300)  # Check every 5 minutes
            
        except Exception as e:
            logger.error(f"Error in sync health monitor: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error

# Utility function to add sync router to main app
def include_sync_router(app):
    """Include the sync router in the main FastAPI app"""
    app.include_router(sync_router)
    logger.info("Data synchronization API endpoints registered")