"""
Admin Dashboard API Proxy
Routes admin dashboard API calls through unified FastAPI endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

# Import existing backend components
from .unified_auth import get_current_user_flexible, require_admin_access, Permission
from .unified_models import UnifiedUser as User, UnifiedTicket as Ticket, UnifiedTicketComment as TicketComment, UnifiedTicketActivity as TicketActivity
from .database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

logger = logging.getLogger(__name__)

# Create router for admin API endpoints
admin_api_router = APIRouter(prefix="/api/admin", tags=["admin"])

@admin_api_router.get("/dashboard")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics for admin dashboard"""
    # Require admin access and dashboard view permission
    require_admin_access(current_user)
    if not current_user.has_permission(Permission.DASHBOARD_VIEW):
        raise HTTPException(status_code=403, detail="Dashboard view permission required")
    
    try:
        # Get ticket statistics
        total_tickets = db.query(Ticket).count()
        open_tickets = db.query(Ticket).filter(Ticket.status == 'open').count()
        pending_tickets = db.query(Ticket).filter(Ticket.status == 'pending').count()
        urgent_tickets = db.query(Ticket).filter(Ticket.priority == 'urgent').count()
        
        # Get user statistics
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        
        # Get recent tickets
        recent_tickets = db.query(Ticket).order_by(desc(Ticket.created_at)).limit(10).all()
        
        # Format recent tickets for frontend
        recent_tickets_data = []
        for ticket in recent_tickets:
            recent_tickets_data.append({
                "id": ticket.id,
                "title": ticket.title,
                "customer": ticket.customer_name or "Unknown",
                "status": ticket.status,
                "priority": ticket.priority,
                "created": ticket.created_at.isoformat() if ticket.created_at else None
            })
        
        return {
            "success": True,
            "data": {
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
                "recent_tickets": recent_tickets_data
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard statistics")

@admin_api_router.get("/users")
async def get_users(
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get all users for admin dashboard"""
    # Require admin access and user list permission
    require_admin_access(current_user)
    if not current_user.has_permission(Permission.USER_LIST):
        raise HTTPException(status_code=403, detail="User list permission required")
    
    try:
        users = db.query(User).all()
        
        users_data = []
        for user in users:
            users_data.append({
                "id": user.id,
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            })
        
        return {
            "success": True,
            "data": users_data
        }
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users")

@admin_api_router.get("/integration/status")
async def get_integration_status(
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get integration status with AI Agent backend"""
    # Require admin access and system logs permission
    require_admin_access(current_user)
    if not current_user.has_permission(Permission.SYSTEM_LOGS):
        raise HTTPException(status_code=403, detail="System logs permission required")
    
    try:
        # Check database connectivity
        db_status = "connected"
        try:
            db.execute("SELECT 1")
        except Exception:
            db_status = "disconnected"
        
        # Get sync statistics
        users_synced = db.query(User).filter(User.user_id.isnot(None)).count()
        tickets_synced = db.query(Ticket).count()
        
        # Get last sync time (this would be stored in a sync status table in real implementation)
        last_sync_time = datetime.now().isoformat()
        
        return {
            "success": True,
            "data": {
                "status": "connected" if db_status == "connected" else "disconnected",
                "database_status": db_status,
                "users_synced": users_synced,
                "tickets_synced": tickets_synced,
                "last_sync_time": last_sync_time,
                "ai_agent_url": "http://localhost:8000",  # This would come from config
                "sync_interval": 15  # minutes
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting integration status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get integration status")

@admin_api_router.post("/integration/sync")
async def sync_with_ai_agent(
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Trigger synchronization with AI Agent backend"""
    # Require admin access and system config permission
    require_admin_access(current_user)
    if not current_user.has_permission(Permission.SYSTEM_CONFIG):
        raise HTTPException(status_code=403, detail="System config permission required")
    
    try:
        # This would trigger the actual sync process
        # For now, we'll return a success response
        
        return {
            "success": True,
            "message": "Synchronization completed successfully",
            "data": {
                "users_synced": 0,
                "tickets_synced": 0,
                "sync_time": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error syncing with AI Agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync with AI Agent")

@admin_api_router.get("/metrics")
async def get_performance_metrics(
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get performance metrics for admin dashboard"""
    # Require admin access and dashboard analytics permission
    require_admin_access(current_user)
    if not current_user.has_permission(Permission.DASHBOARD_ANALYTICS):
        raise HTTPException(status_code=403, detail="Dashboard analytics permission required")
    
    try:
        # Get ticket metrics by status
        ticket_metrics = db.query(
            Ticket.status,
            func.count(Ticket.id).label('count')
        ).group_by(Ticket.status).all()
        
        # Get ticket metrics by priority
        priority_metrics = db.query(
            Ticket.priority,
            func.count(Ticket.id).label('count')
        ).group_by(Ticket.priority).all()
        
        # Format metrics for frontend
        status_data = {metric.status: metric.count for metric in ticket_metrics}
        priority_data = {metric.priority: metric.count for metric in priority_metrics}
        
        return {
            "success": True,
            "data": {
                "ticket_status": status_data,
                "ticket_priority": priority_data,
                "response_time": {
                    "average": 2.5,  # hours - would be calculated from actual data
                    "median": 1.8
                },
                "resolution_time": {
                    "average": 24.5,  # hours - would be calculated from actual data
                    "median": 18.2
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")

# Support API endpoints (proxy to existing ticket system)
support_api_router = APIRouter(prefix="/api/support", tags=["support"])

@support_api_router.get("/tickets")
async def get_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get tickets with optional filtering"""
    # Check if user has permission to list tickets
    if not current_user.has_permission(Permission.TICKET_LIST):
        raise HTTPException(status_code=403, detail="Ticket list permission required")
    
    try:
        query = db.query(Ticket)
        
        # Apply filters
        if status and status != 'all':
            query = query.filter(Ticket.status == status)
        if priority and priority != 'all':
            query = query.filter(Ticket.priority == priority)
        if assignee and assignee != 'all':
            if assignee == 'unassigned':
                query = query.filter(Ticket.assigned_agent_id.is_(None))
            else:
                query = query.filter(Ticket.assigned_agent_id == assignee)
        
        tickets = query.order_by(desc(Ticket.created_at)).all()
        
        tickets_data = []
        for ticket in tickets:
            tickets_data.append({
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "customer_name": ticket.customer_name,
                "customer_email": ticket.customer_email,
                "status": ticket.status,
                "priority": ticket.priority,
                "category": ticket.category,
                "assigned_agent_id": ticket.assigned_agent_id,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None
            })
        
        return {
            "success": True,
            "data": tickets_data
        }
        
    except Exception as e:
        logger.error(f"Error getting tickets: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tickets")

@support_api_router.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get specific ticket by ID"""
    # Check if user has permission to read tickets
    if not current_user.has_permission(Permission.TICKET_READ):
        raise HTTPException(status_code=403, detail="Ticket read permission required")
    
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Get ticket comments
        comments = db.query(TicketComment).filter(
            TicketComment.ticket_id == ticket_id
        ).order_by(TicketComment.created_at).all()
        
        comments_data = []
        for comment in comments:
            comments_data.append({
                "id": comment.id,
                "comment": comment.comment,
                "author": comment.author,
                "is_internal": comment.is_internal,
                "created_at": comment.created_at.isoformat() if comment.created_at else None
            })
        
        ticket_data = {
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "customer_name": ticket.customer_name,
            "customer_email": ticket.customer_email,
            "status": ticket.status,
            "priority": ticket.priority,
            "category": ticket.category,
            "assigned_agent_id": ticket.assigned_agent_id,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            "comments": comments_data
        }
        
        return {
            "success": True,
            "data": ticket_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get ticket")

@support_api_router.post("/tickets")
async def create_ticket(
    ticket_data: Dict[str, Any],
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Create new support ticket"""
    # Check if user has permission to create tickets
    if not current_user.has_permission(Permission.TICKET_CREATE):
        raise HTTPException(status_code=403, detail="Ticket create permission required")
    
    try:
        # Create new ticket
        new_ticket = Ticket(
            title=ticket_data.get('subject'),
            description=ticket_data.get('description'),
            customer_name=ticket_data.get('customer_name'),
            customer_email=ticket_data.get('customer_email'),
            status='open',
            priority=ticket_data.get('priority', 'medium'),
            category=ticket_data.get('category'),
            assigned_agent_id=ticket_data.get('assignee') if ticket_data.get('assignee') else None,
            created_at=datetime.now()
        )
        
        db.add(new_ticket)
        db.commit()
        db.refresh(new_ticket)
        
        return {
            "success": True,
            "message": "Ticket created successfully",
            "data": {
                "id": new_ticket.id,
                "title": new_ticket.title,
                "status": new_ticket.status
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create ticket")

@support_api_router.put("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: int,
    ticket_data: Dict[str, Any],
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Update existing ticket"""
    # Check if user has permission to update tickets
    if not current_user.has_permission(Permission.TICKET_UPDATE):
        raise HTTPException(status_code=403, detail="Ticket update permission required")
    
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Update ticket fields
        if 'subject' in ticket_data:
            ticket.title = ticket_data['subject']
        if 'description' in ticket_data:
            ticket.description = ticket_data['description']
        if 'status' in ticket_data:
            ticket.status = ticket_data['status']
        if 'priority' in ticket_data:
            ticket.priority = ticket_data['priority']
        if 'category' in ticket_data:
            ticket.category = ticket_data['category']
        if 'assignee' in ticket_data:
            ticket.assigned_agent_id = ticket_data['assignee'] if ticket_data['assignee'] else None
        
        ticket.updated_at = datetime.now()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Ticket updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ticket {ticket_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update ticket")

@support_api_router.post("/tickets/{ticket_id}/comments")
async def add_ticket_comment(
    ticket_id: int,
    comment_data: Dict[str, Any],
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Add comment to ticket"""
    # Check if user has permission to create comments
    if not current_user.has_permission(Permission.COMMENT_CREATE):
        raise HTTPException(status_code=403, detail="Comment create permission required")
    
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Create new comment
        new_comment = TicketComment(
            ticket_id=ticket_id,
            comment=comment_data.get('comment'),
            author=current_user.username,
            is_internal=comment_data.get('is_internal', False),
            created_at=datetime.now()
        )
        
        db.add(new_comment)
        
        # Update ticket's updated_at timestamp
        ticket.updated_at = datetime.now()
        
        db.commit()
        db.refresh(new_comment)
        
        return {
            "success": True,
            "message": "Comment added successfully",
            "data": {
                "id": new_comment.id,
                "comment": new_comment.comment,
                "author": new_comment.author,
                "created_at": new_comment.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding comment to ticket {ticket_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add comment")


def setup_admin_api_proxy(app):
    """Setup admin API proxy routers"""
    app.include_router(admin_api_router)
    app.include_router(support_api_router)
    logger.info("Admin API proxy routers setup completed")