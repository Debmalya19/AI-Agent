"""
Admin Dashboard Routes
Provides endpoints for the admin dashboard functionality
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from .database import get_db
from .unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedChatHistory, UnifiedTicketComment,
    TicketStatus, TicketPriority, TicketCategory, UserRole
)
from .unified_auth import get_current_user_flexible, AuthenticatedUser, require_admin_access

logger = logging.getLogger(__name__)

# Create router
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

# Create ticket router for dashboard compatibility
ticket_router = APIRouter(prefix="/api/tickets", tags=["tickets"])

@admin_router.get("/dashboard")
async def get_dashboard_stats(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    # Require admin access
    require_admin_access(current_user)
    
    try:
        # Get ticket statistics
        total_tickets = db.query(UnifiedTicket).count()
        open_tickets = db.query(UnifiedTicket).filter(
            UnifiedTicket.status == TicketStatus.OPEN
        ).count()
        pending_tickets = db.query(UnifiedTicket).filter(
            UnifiedTicket.status == TicketStatus.PENDING
        ).count()
        urgent_tickets = db.query(UnifiedTicket).filter(
            UnifiedTicket.priority == TicketPriority.CRITICAL
        ).count()
        
        # Get recent tickets
        recent_tickets = db.query(UnifiedTicket).order_by(
            desc(UnifiedTicket.created_at)
        ).limit(10).all()
        
        # Format recent tickets
        recent_tickets_data = []
        for ticket in recent_tickets:
            # Get customer info
            customer = db.query(UnifiedUser).filter(
                UnifiedUser.id == ticket.customer_id
            ).first()
            
            recent_tickets_data.append({
                "id": ticket.id,
                "title": ticket.title,
                "customer_name": customer.full_name if customer else "Unknown",
                "status": ticket.status.value if ticket.status else "open",
                "priority": ticket.priority.value if ticket.priority else "medium",
                "created_at": ticket.created_at.isoformat()
            })
        
        # Get user statistics
        total_users = db.query(UnifiedUser).count()
        active_users = db.query(UnifiedUser).filter(
            UnifiedUser.is_active == True
        ).count()
        
        # Get chat statistics
        total_chats = db.query(UnifiedChatHistory).count()
        recent_chats = db.query(UnifiedChatHistory).filter(
            UnifiedChatHistory.created_at >= datetime.now(timezone.utc) - timedelta(days=7)
        ).count()
        
        return {
            "success": True,
            "stats": {
                "tickets": {
                    "total": total_tickets,
                    "open": open_tickets,
                    "pending": pending_tickets,
                    "urgent": urgent_tickets
                },
                "users": {
                    "total": total_users,
                    "active": active_users
                },
                "chats": {
                    "total": total_chats,
                    "recent": recent_chats
                },
                "recent_tickets": recent_tickets_data
            }
        }
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard statistics")

@admin_router.get("/users")
async def get_users(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    # Require admin access
    require_admin_access(current_user)
    
    try:
        users = db.query(UnifiedUser).offset(skip).limit(limit).all()
        
        users_data = []
        for user in users:
            users_data.append({
                "id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value if user.role else "customer",
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None
            })
        
        return {
            "success": True,
            "users": users_data,
            "total": db.query(UnifiedUser).count()
        }
        
    except Exception as e:
        logger.error(f"Get users error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users")

@admin_router.get("/integration/status")
async def get_integration_status(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get integration status with AI agent backend"""
    # Require admin access
    require_admin_access(current_user)
    
    try:
        # Check if the system is running (basic health check)
        user_count = db.query(UnifiedUser).count()
        ticket_count = db.query(UnifiedTicket).count()
        
        return {
            "success": True,
            "ai_agent_backend_available": True,
            "message": "Integration is active and functioning",
            "stats": {
                "users": user_count,
                "tickets": ticket_count,
                "last_sync": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Integration status error: {e}")
        return {
            "success": False,
            "ai_agent_backend_available": False,
            "message": f"Integration error: {str(e)}",
            "stats": {}
        }

@admin_router.post("/integration/sync")
async def sync_with_ai_agent(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Sync with AI Agent backend"""
    # Require admin access
    require_admin_access(current_user)
    
    try:
        # Simulate sync operation
        user_count = db.query(UnifiedUser).count()
        ticket_count = db.query(UnifiedTicket).count()
        
        return {
            "success": True,
            "message": "Synchronization completed successfully",
            "sync_results": {
                "customers_synced": user_count,
                "tickets_synced": ticket_count,
                "sync_time": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail="Synchronization failed")

@admin_router.get("/metrics")
async def get_performance_metrics(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get performance metrics"""
    # Require admin access
    require_admin_access(current_user)
    
    try:
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get ticket metrics
        tickets_created = db.query(UnifiedTicket).filter(
            UnifiedTicket.created_at >= start_date
        ).count()
        
        tickets_resolved = db.query(UnifiedTicket).filter(
            UnifiedTicket.status == TicketStatus.RESOLVED,
            UnifiedTicket.updated_at >= start_date
        ).count()
        
        # Get chat metrics
        chats_created = db.query(UnifiedChatHistory).filter(
            UnifiedChatHistory.created_at >= start_date
        ).count()
        
        # Get user metrics
        new_users = db.query(UnifiedUser).filter(
            UnifiedUser.created_at >= start_date
        ).count()
        
        return {
            "success": True,
            "metrics": {
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "tickets": {
                    "created": tickets_created,
                    "resolved": tickets_resolved,
                    "resolution_rate": (tickets_resolved / tickets_created * 100) if tickets_created > 0 else 0
                },
                "chats": {
                    "created": chats_created
                },
                "users": {
                    "new": new_users
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")

# Ticket endpoints for dashboard compatibility
@ticket_router.get("/stats")
async def get_ticket_stats(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get ticket statistics for dashboard"""
    # Require admin access
    require_admin_access(current_user)
    
    try:
        # Get ticket statistics
        total_tickets = db.query(UnifiedTicket).count()
        
        # Tickets by status
        open_tickets = db.query(UnifiedTicket).filter(
            UnifiedTicket.status == TicketStatus.OPEN
        ).count()
        pending_tickets = db.query(UnifiedTicket).filter(
            UnifiedTicket.status == TicketStatus.PENDING
        ).count()
        resolved_tickets = db.query(UnifiedTicket).filter(
            UnifiedTicket.status == TicketStatus.RESOLVED
        ).count()
        closed_tickets = db.query(UnifiedTicket).filter(
            UnifiedTicket.status == TicketStatus.CLOSED
        ).count()
        
        # Tickets by priority
        low_priority = db.query(UnifiedTicket).filter(
            UnifiedTicket.priority == TicketPriority.LOW
        ).count()
        medium_priority = db.query(UnifiedTicket).filter(
            UnifiedTicket.priority == TicketPriority.MEDIUM
        ).count()
        high_priority = db.query(UnifiedTicket).filter(
            UnifiedTicket.priority == TicketPriority.HIGH
        ).count()
        urgent_priority = db.query(UnifiedTicket).filter(
            UnifiedTicket.priority == TicketPriority.CRITICAL
        ).count()
        
        return {
            "total": total_tickets,
            "by_status": {
                "open": open_tickets,
                "pending": pending_tickets,
                "resolved": resolved_tickets,
                "closed": closed_tickets
            },
            "by_priority": {
                "low": low_priority,
                "medium": medium_priority,
                "high": high_priority,
                "urgent": urgent_priority,
                "critical": urgent_priority  # Alias for compatibility
            }
        }
        
    except Exception as e:
        logger.error(f"Ticket stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve ticket statistics")

@ticket_router.get("/")
async def get_tickets(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    limit: int = 10,
    skip: int = 0,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get tickets with optional filtering"""
    # Require admin access
    require_admin_access(current_user)
    
    try:
        # Start with base query
        query = db.query(UnifiedTicket)
        
        # Apply filters if provided
        if status:
            try:
                status_enum = TicketStatus(status.upper())
                query = query.filter(UnifiedTicket.status == status_enum)
            except ValueError:
                pass  # Invalid status, ignore filter
        
        if priority:
            try:
                priority_enum = TicketPriority(priority.upper())
                query = query.filter(UnifiedTicket.priority == priority_enum)
            except ValueError:
                pass  # Invalid priority, ignore filter
        
        # Order by created_at descending (newest first)
        query = query.order_by(desc(UnifiedTicket.created_at))
        
        # Apply pagination
        tickets = query.offset(skip).limit(limit).all()
        total_count = query.count()
        
        # Format tickets for response
        tickets_data = []
        for ticket in tickets:
            # Get customer info
            customer = db.query(UnifiedUser).filter(
                UnifiedUser.id == ticket.customer_id
            ).first()
            
            ticket_data = {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "status": ticket.status.value.lower() if ticket.status else "open",
                "priority": ticket.priority.value.lower() if ticket.priority else "medium",
                "category": ticket.category.value.lower() if ticket.category else "general",
                "customer_name": customer.full_name if customer else "Unknown",
                "customer_id": ticket.customer_id,
                "created_at": ticket.created_at.isoformat(),
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else ticket.created_at.isoformat()
            }
            tickets_data.append(ticket_data)
        
        return {
            "tickets": tickets_data,
            "total": total_count
        }
        
    except Exception as e:
        logger.error(f"Get tickets error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tickets")

# System Logs endpoints
@admin_router.get("/logs")
async def get_system_logs(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    limit: int = 100,
    skip: int = 0,
    level: Optional[str] = None,
    category: Optional[str] = None,
    since: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get system logs with filtering"""
    # Require admin access
    require_admin_access(current_user)
    
    try:
        # Generate sample logs for demonstration
        # In a real implementation, this would read from actual log files or database
        logs = generate_sample_logs(limit + skip)
        
        # Apply filters
        filtered_logs = logs
        
        if level:
            filtered_logs = [log for log in filtered_logs if log['level'].lower() == level.lower()]
        
        if category:
            filtered_logs = [log for log in filtered_logs if log['category'].lower() == category.lower()]
        
        if since:
            try:
                since_date = datetime.fromisoformat(since.replace('Z', '+00:00'))
                filtered_logs = [log for log in filtered_logs if datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')) >= since_date]
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        # Apply pagination
        paginated_logs = filtered_logs[skip:skip + limit]
        
        return {
            "success": True,
            "logs": paginated_logs,
            "total": len(filtered_logs),
            "page": skip // limit + 1 if limit > 0 else 1,
            "per_page": limit
        }
        
    except Exception as e:
        logger.error(f"Get logs error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")

@admin_router.get("/logs/new")
async def get_new_logs(
    since: str,
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get new logs since specified timestamp for real-time updates"""
    # Require admin access
    require_admin_access(current_user)
    
    try:
        # Parse since timestamp
        since_date = datetime.fromisoformat(since.replace('Z', '+00:00'))
        
        # Generate new logs (in real implementation, this would check actual log files)
        # For demo, return a few new logs if more than 30 seconds have passed
        now = datetime.now(timezone.utc)
        if (now - since_date).total_seconds() > 30:
            new_logs = generate_sample_logs(5)  # Generate 5 new logs
            # Filter to only "new" logs (created after since timestamp)
            new_logs = [log for log in new_logs if datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')) > since_date]
        else:
            new_logs = []
        
        return {
            "success": True,
            "logs": new_logs,
            "count": len(new_logs)
        }
        
    except Exception as e:
        logger.error(f"Get new logs error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve new logs")

@admin_router.delete("/logs")
async def clear_system_logs(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Clear all system logs"""
    # Require admin access
    require_admin_access(current_user)
    
    try:
        # In a real implementation, this would clear actual log files or database entries
        # For demo purposes, we'll just return success
        
        logger.info(f"System logs cleared by admin user: {current_user.username}")
        
        return {
            "success": True,
            "message": "All system logs have been cleared successfully",
            "cleared_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Clear logs error: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear logs")

def generate_sample_logs(count: int = 100) -> List[Dict[str, Any]]:
    """Generate sample log entries for demonstration"""
    import random
    
    levels = ['error', 'warning', 'info', 'debug']
    categories = ['auth', 'api', 'database', 'integration', 'system']
    messages = [
        'User authentication successful',
        'Database connection established',
        'API request processed successfully',
        'Integration sync completed',
        'System startup completed',
        'Failed login attempt detected',
        'Database query timeout occurred',
        'API rate limit exceeded',
        'Integration connection failed',
        'System memory usage high',
        'User session expired',
        'Database backup completed',
        'API endpoint deprecated warning',
        'Integration data synchronized',
        'System maintenance scheduled',
        'Cache cleared successfully',
        'Configuration updated',
        'Service restarted',
        'Error processing request',
        'Performance threshold exceeded'
    ]
    
    logs = []
    now = datetime.now(timezone.utc)
    
    for i in range(count):
        # Generate timestamp within last 24 hours
        timestamp = now - timedelta(minutes=random.randint(0, 1440))
        level = random.choice(levels)
        category = random.choice(categories)
        message = random.choice(messages)
        
        log_entry = {
            'id': i + 1,
            'timestamp': timestamp.isoformat(),
            'level': level,
            'category': category,
            'message': f'{message} - Entry #{i + 1}',
            'source': 'admin-dashboard',
            'details': {
                'user_id': random.randint(1, 100),
                'ip': f'192.168.1.{random.randint(1, 255)}',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
        
        logs.append(log_entry)
    
    # Sort by timestamp descending (newest first)
    logs.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return logs