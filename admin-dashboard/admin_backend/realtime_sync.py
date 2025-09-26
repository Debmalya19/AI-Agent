# Real-time Bidirectional Data Synchronization Service
# Implements event-driven architecture with WebSocket support and efficient polling fallback

import asyncio
import websockets
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time
from queue import Queue, Empty
import uuid
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask import request
import redis
import aioredis
import aiohttp
from sqlalchemy import event, text
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

# Import local modules
from .models import db, User
from .models_support import Ticket, TicketComment, TicketActivity
from .integration_api import IntegrationEvent, EventType, integration_manager
from .auth import token_required

# Setup logging
logger = logging.getLogger(__name__)

class SyncStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    SYNCING = "syncing"
    ERROR = "error"
    RECONNECTING = "reconnecting"

@dataclass
class SyncMetrics:
    """Metrics for synchronization performance"""
    events_processed: int = 0
    events_failed: int = 0
    last_sync_time: Optional[datetime] = None
    average_latency: float = 0.0
    connection_uptime: timedelta = timedelta()
    sync_errors: List[str] = None
    
    def __post_init__(self):
        if self.sync_errors is None:
            self.sync_errors = []

@dataclass
class ConnectionInfo:
    """Information about a client connection"""
    session_id: str
    user_id: Optional[int]
    connected_at: datetime
    last_activity: datetime
    subscribed_events: Set[str]
    room: Optional[str] = None
    
class RealTimeSyncService:
    """Real-time synchronization service with event-driven architecture"""
    
    def __init__(self, socketio: SocketIO, redis_url: str = "redis://localhost:6379"):
        self.socketio = socketio
        self.redis_url = redis_url
        self.redis_client = None
        self.connections: Dict[str, ConnectionInfo] = {}
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.sync_metrics = SyncMetrics()
        self.polling_interval = 5  # seconds
        self.max_retry_attempts = 3
        self.retry_delay = 2  # seconds
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 300  # seconds
        
        # Event queues for different priorities
        self.high_priority_queue = Queue()
        self.normal_priority_queue = Queue()
        self.low_priority_queue = Queue()
        
        # Background tasks
        self.polling_task = None
        self.heartbeat_task = None
        self.cleanup_task = None
        
        # Initialize Redis connection
        self._init_redis()
        
        # Register default event handlers
        self._register_default_handlers()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _init_redis(self):
        """Initialize Redis connection for pub/sub"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connection established for real-time sync")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    def _register_default_handlers(self):
        """Register default event handlers"""
        self.register_event_handler(EventType.TICKET_CREATED, self._handle_ticket_created)
        self.register_event_handler(EventType.TICKET_UPDATED, self._handle_ticket_updated)
        self.register_event_handler(EventType.COMMENT_ADDED, self._handle_comment_added)
        self.register_event_handler(EventType.USER_CREATED, self._handle_user_created)
        self.register_event_handler(EventType.SYSTEM_STATUS, self._handle_system_status)
    
    def _start_background_tasks(self):
        """Start background tasks for polling and maintenance"""
        # Start polling task
        self.polling_task = threading.Thread(target=self._polling_worker, daemon=True)
        self.polling_task.start()
        
        # Start heartbeat task
        self.heartbeat_task = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self.heartbeat_task.start()
        
        # Start cleanup task
        self.cleanup_task = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_task.start()
        
        logger.info("Background tasks started for real-time sync")
    
    def register_event_handler(self, event_type: EventType, handler: Callable):
        """Register an event handler for a specific event type"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for {event_type.value}")
    
    def emit_event(self, event: IntegrationEvent, priority: str = "normal"):
        """Emit an event to the appropriate queue based on priority"""
        event_data = {
            'event_type': event.event_type.value,
            'entity_id': event.entity_id,
            'entity_type': event.entity_type,
            'data': event.data,
            'timestamp': event.timestamp.isoformat(),
            'source': event.source,
            'target': event.target
        }
        
        # Add to appropriate queue based on priority
        if priority == "high":
            self.high_priority_queue.put(event_data)
        elif priority == "low":
            self.low_priority_queue.put(event_data)
        else:
            self.normal_priority_queue.put(event_data)
        
        # Also publish to Redis for cross-instance communication
        if self.redis_client:
            try:
                self.redis_client.publish('sync_events', json.dumps(event_data))
            except Exception as e:
                logger.error(f"Failed to publish event to Redis: {e}")
    
    def _process_event_queue(self):
        """Process events from queues in priority order"""
        queues = [
            (self.high_priority_queue, "high"),
            (self.normal_priority_queue, "normal"),
            (self.low_priority_queue, "low")
        ]
        
        for queue, priority in queues:
            try:
                while not queue.empty():
                    event_data = queue.get_nowait()
                    self._handle_event(event_data)
                    self.sync_metrics.events_processed += 1
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing {priority} priority queue: {e}")
                self.sync_metrics.events_failed += 1
    
    def _handle_event(self, event_data: Dict):
        """Handle a single event"""
        try:
            event_type = EventType(event_data['event_type'])
            
            # Execute registered handlers
            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    try:
                        handler(event_data)
                    except Exception as e:
                        logger.error(f"Event handler error for {event_type.value}: {e}")
            
            # Emit to connected clients
            self._emit_to_subscribers(event_data)
            
        except Exception as e:
            logger.error(f"Error handling event: {e}")
            self.sync_metrics.events_failed += 1
    
    def _emit_to_subscribers(self, event_data: Dict):
        """Emit event to subscribed clients"""
        event_type = event_data['event_type']
        
        # Find connections subscribed to this event type
        for session_id, conn_info in self.connections.items():
            if event_type in conn_info.subscribed_events:
                try:
                    if conn_info.room:
                        self.socketio.emit('sync_event', event_data, room=conn_info.room)
                    else:
                        self.socketio.emit('sync_event', event_data, to=session_id)
                except Exception as e:
                    logger.error(f"Failed to emit to session {session_id}: {e}")
    
    def _polling_worker(self):
        """Background worker for polling-based synchronization fallback"""
        while True:
            try:
                # Process event queues
                self._process_event_queue()
                
                # Poll for changes if WebSocket is not available
                if not self._has_active_websocket_connections():
                    self._poll_for_changes()
                
                time.sleep(self.polling_interval)
                
            except Exception as e:
                logger.error(f"Polling worker error: {e}")
                time.sleep(self.polling_interval * 2)  # Back off on error
    
    def _heartbeat_worker(self):
        """Background worker for connection heartbeat"""
        while True:
            try:
                current_time = datetime.utcnow()
                
                # Send heartbeat to all connections
                for session_id, conn_info in list(self.connections.items()):
                    try:
                        # Check if connection is stale
                        if (current_time - conn_info.last_activity).total_seconds() > self.connection_timeout:
                            self._remove_connection(session_id)
                            continue
                        
                        # Send heartbeat
                        self.socketio.emit('heartbeat', {
                            'timestamp': current_time.isoformat(),
                            'server_time': current_time.isoformat()
                        }, to=session_id)
                        
                    except Exception as e:
                        logger.error(f"Heartbeat error for session {session_id}: {e}")
                        self._remove_connection(session_id)
                
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Heartbeat worker error: {e}")
                time.sleep(self.heartbeat_interval)
    
    def _cleanup_worker(self):
        """Background worker for cleanup tasks"""
        while True:
            try:
                # Clean up old metrics
                if len(self.sync_metrics.sync_errors) > 100:
                    self.sync_metrics.sync_errors = self.sync_metrics.sync_errors[-50:]
                
                # Update sync metrics
                self.sync_metrics.last_sync_time = datetime.utcnow()
                
                time.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                time.sleep(300)
    
    def _has_active_websocket_connections(self) -> bool:
        """Check if there are active WebSocket connections"""
        return len(self.connections) > 0
    
    def _poll_for_changes(self):
        """Poll for database changes as fallback mechanism"""
        try:
            # Check for recent ticket updates
            recent_time = datetime.utcnow() - timedelta(seconds=self.polling_interval * 2)
            
            # Query for recent tickets
            recent_tickets = Ticket.query.filter(
                Ticket.updated_at >= recent_time
            ).all()
            
            for ticket in recent_tickets:
                event = IntegrationEvent(
                    event_type=EventType.TICKET_UPDATED,
                    entity_id=str(ticket.id),
                    entity_type="ticket",
                    data=ticket.to_dict(),
                    timestamp=datetime.utcnow()
                )
                self.emit_event(event, priority="normal")
            
            # Query for recent comments
            recent_comments = TicketComment.query.filter(
                TicketComment.created_at >= recent_time
            ).all()
            
            for comment in recent_comments:
                event = IntegrationEvent(
                    event_type=EventType.COMMENT_ADDED,
                    entity_id=str(comment.id),
                    entity_type="comment",
                    data=comment.to_dict(),
                    timestamp=datetime.utcnow()
                )
                self.emit_event(event, priority="normal")
                
        except Exception as e:
            logger.error(f"Polling error: {e}")
    
    def add_connection(self, session_id: str, user_id: Optional[int] = None, 
                     subscribed_events: Set[str] = None):
        """Add a new connection"""
        if subscribed_events is None:
            subscribed_events = set()
        
        conn_info = ConnectionInfo(
            session_id=session_id,
            user_id=user_id,
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            subscribed_events=subscribed_events
        )
        
        self.connections[session_id] = conn_info
        logger.info(f"Added connection: {session_id}")
    
    def _remove_connection(self, session_id: str):
        """Remove a connection"""
        if session_id in self.connections:
            del self.connections[session_id]
            logger.info(f"Removed connection: {session_id}")
    
    def update_connection_activity(self, session_id: str):
        """Update last activity time for a connection"""
        if session_id in self.connections:
            self.connections[session_id].last_activity = datetime.utcnow()
    
    def subscribe_to_events(self, session_id: str, event_types: List[str]):
        """Subscribe a connection to specific event types"""
        if session_id in self.connections:
            self.connections[session_id].subscribed_events.update(event_types)
            logger.info(f"Session {session_id} subscribed to: {event_types}")
    
    def unsubscribe_from_events(self, session_id: str, event_types: List[str]):
        """Unsubscribe a connection from specific event types"""
        if session_id in self.connections:
            self.connections[session_id].subscribed_events.difference_update(event_types)
            logger.info(f"Session {session_id} unsubscribed from: {event_types}")
    
    def get_sync_metrics(self) -> Dict:
        """Get current synchronization metrics"""
        return {
            'events_processed': self.sync_metrics.events_processed,
            'events_failed': self.sync_metrics.events_failed,
            'success_rate': (
                (self.sync_metrics.events_processed / 
                 max(1, self.sync_metrics.events_processed + self.sync_metrics.events_failed)) * 100
            ),
            'active_connections': len(self.connections),
            'last_sync_time': self.sync_metrics.last_sync_time.isoformat() if self.sync_metrics.last_sync_time else None,
            'average_latency': self.sync_metrics.average_latency,
            'recent_errors': self.sync_metrics.sync_errors[-10:],  # Last 10 errors
            'queue_sizes': {
                'high_priority': self.high_priority_queue.qsize(),
                'normal_priority': self.normal_priority_queue.qsize(),
                'low_priority': self.low_priority_queue.qsize()
            }
        }
    
    # Event handlers
    def _handle_ticket_created(self, event_data: Dict):
        """Handle ticket creation event"""
        logger.info(f"Handling ticket created: {event_data['entity_id']}")
        # Additional processing for ticket creation
    
    def _handle_ticket_updated(self, event_data: Dict):
        """Handle ticket update event"""
        logger.info(f"Handling ticket updated: {event_data['entity_id']}")
        # Additional processing for ticket updates
    
    def _handle_comment_added(self, event_data: Dict):
        """Handle comment addition event"""
        logger.info(f"Handling comment added: {event_data['entity_id']}")
        # Additional processing for comments
    
    def _handle_user_created(self, event_data: Dict):
        """Handle user creation event"""
        logger.info(f"Handling user created: {event_data['entity_id']}")
        # Additional processing for user creation
    
    def _handle_system_status(self, event_data: Dict):
        """Handle system status event"""
        logger.info(f"Handling system status update: {event_data['data']}")
        # Additional processing for system status

# Global sync service instance
sync_service = None

def init_sync_service(socketio: SocketIO, redis_url: str = "redis://localhost:6379"):
    """Initialize the global sync service"""
    global sync_service
    sync_service = RealTimeSyncService(socketio, redis_url)
    return sync_service

# SocketIO event handlers
def register_socketio_handlers(socketio: SocketIO):
    """Register SocketIO event handlers"""
    
    @socketio.on('connect')
    def handle_connect(auth):
        """Handle client connection"""
        session_id = request.sid
        user_id = None
        
        # Extract user info from auth if available
        if auth and 'token' in auth:
            # Validate token and extract user info
            # This would integrate with your auth system
            pass
        
        if sync_service:
            sync_service.add_connection(session_id, user_id)
        
        emit('connected', {
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"Client connected: {session_id}")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        session_id = request.sid
        
        if sync_service:
            sync_service._remove_connection(session_id)
        
        logger.info(f"Client disconnected: {session_id}")
    
    @socketio.on('subscribe')
    def handle_subscribe(data):
        """Handle event subscription"""
        session_id = request.sid
        event_types = data.get('event_types', [])
        
        if sync_service:
            sync_service.subscribe_to_events(session_id, event_types)
            sync_service.update_connection_activity(session_id)
        
        emit('subscribed', {
            'event_types': event_types,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('unsubscribe')
    def handle_unsubscribe(data):
        """Handle event unsubscription"""
        session_id = request.sid
        event_types = data.get('event_types', [])
        
        if sync_service:
            sync_service.unsubscribe_from_events(session_id, event_types)
            sync_service.update_connection_activity(session_id)
        
        emit('unsubscribed', {
            'event_types': event_types,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('heartbeat_response')
    def handle_heartbeat_response(data):
        """Handle heartbeat response from client"""
        session_id = request.sid
        
        if sync_service:
            sync_service.update_connection_activity(session_id)
    
    @socketio.on('get_metrics')
    def handle_get_metrics():
        """Handle metrics request"""
        if sync_service:
            metrics = sync_service.get_sync_metrics()
            emit('metrics', metrics)
        else:
            emit('error', {'message': 'Sync service not available'})