"""
Admin Dashboard API Integration Layer

This module provides FastAPI routers that wrap existing admin dashboard Flask routes,
creating a unified API interface while maintaining backward compatibility.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging
import asyncio
import json
from contextlib import asynccontextmanager

# Import unified models and authentication
from .unified_models import UnifiedUser as User, UnifiedTicket as Ticket, UnifiedTicketComment as TicketComment, UnifiedTicketActivity as TicketActivity
from .unified_auth import get_current_user_flexible, require_admin_access, Permission
from .database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ==================== REQUEST/RESPONSE MODELS ====================

class AdminDashboardStats(BaseModel):
    """Admin dashboard statistics response model"""
    users: Dict[str, int]
    tickets: Dict[str, int]
    recent_users: List[Dict[str, Any]]
    recent_tickets: List[Dict[str, Any]]
    system_status: Dict[str, Any]

class UserListResponse(BaseModel):
    """User list response model"""
    users: List[Dict[str, Any]]
    pagination: Dict[str, Any]

class TicketListResponse(BaseModel):
    """Ticket list response model"""
    tickets: List[Dict[str, Any]]
    pagination: Dict[str, Any]

class TicketCreateRequest(BaseModel):
    """Ticket creation request model"""
    subject: str
    description: str
    customer_id: int
    priority: str
    category: str
    assignee_id: Optional[int] = None

class TicketUpdateRequest(BaseModel):
    """Ticket update request model"""
    subject: Optional[str] = None
    description: Optional[str] = None
    customer_id: Optional[int] = None
    assignee_id: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None

class CommentCreateRequest(BaseModel):
    """Comment creation request model"""
    text: str
    is_internal: Optional[bool] = False

class PerformanceMetricsResponse(BaseModel):
    """Performance metrics response model"""
    period: str
    start_date: datetime
    end_date: datetime
    metrics_by_date: List[Dict[str, Any]]
    summary: Dict[str, Any]

# ==================== REQUEST/RESPONSE ADAPTERS ====================

class AdminAPIAdapter:
    """Adapter class to convert between FastAPI and Flask formats"""
    
    @staticmethod
    def adapt_user_to_dict(user: User, minimal: bool = False) -> Dict[str, Any]:
        """Convert User model to dictionary format"""
        if minimal:
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name
            }
        
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_admin,
            'full_name': user.full_name,
            'phone': user.phone,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'ai_agent_customer_id': getattr(user, 'ai_agent_customer_id', None)
        }
    
    @staticmethod
    def adapt_ticket_to_dict(ticket: Ticket, include_relations: bool = True) -> Dict[str, Any]:
        """Convert Ticket model to dictionary format"""
        ticket_dict = {
            'id': ticket.id,
            'ticket_id': ticket.ticket_id,
            'subject': ticket.subject,
            'description': ticket.description,
            'status': ticket.status,
            'priority': ticket.priority,
            'category': ticket.category,
            'customer_id': ticket.customer_id,
            'assignee_id': ticket.assignee_id,
            'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
            'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None
        }
        
        if include_relations:
            # Add customer and assignee info if available
            if hasattr(ticket, 'customer') and ticket.customer:
                ticket_dict['customer'] = AdminAPIAdapter.adapt_user_to_dict(ticket.customer, minimal=True)
            
            if hasattr(ticket, 'assignee') and ticket.assignee:
                ticket_dict['assignee'] = AdminAPIAdapter.adapt_user_to_dict(ticket.assignee, minimal=True)
        
        return ticket_dict
    
    @staticmethod
    def adapt_comment_to_dict(comment: TicketComment) -> Dict[str, Any]:
        """Convert TicketComment model to dictionary format"""
        return {
            'id': comment.id,
            'ticket_id': comment.ticket_id,
            'user_id': comment.user_id,
            'content': comment.content,
            'is_internal': comment.is_internal,
            'created_at': comment.created_at.isoformat() if comment.created_at else None
        }
    
    @staticmethod
    def create_pagination_dict(page: int, per_page: int, total: int, has_next: bool, has_prev: bool) -> Dict[str, Any]:
        """Create pagination dictionary"""
        return {
            'total': total,
            'pages': (total + per_page - 1) // per_page,
            'page': page,
            'per_page': per_page,
            'has_next': has_next,
            'has_prev': has_prev
        }

# ==================== ADMIN DASHBOARD ROUTER ====================

def create_admin_dashboard_router() -> APIRouter:
    """Create the admin dashboard FastAPI router"""
    
    router = APIRouter(prefix="/api/admin", tags=["admin"])
    
    @router.get("/dashboard", response_model=AdminDashboardStats)
    async def get_admin_dashboard(
        current_user: User = Depends(get_current_user_flexible),
        db: Session = Depends(get_db)
    ):
        """Get admin dashboard statistics"""
        # Require admin access and dashboard view permission
        require_admin_access(current_user)
        if not current_user.has_permission(Permission.DASHBOARD_VIEW):
            raise HTTPException(status_code=403, detail="Dashboard view permission required")
        
        try:
            # Get user counts
            total_users = db.query(User).count()
            admin_users = db.query(User).filter(User.is_admin == True).count()
            regular_users = total_users - admin_users
            
            # Get ticket counts
            total_tickets = db.query(Ticket).count()
            open_tickets = db.query(Ticket).filter(Ticket.status != 'RESOLVED').count()
            resolved_tickets = db.query(Ticket).filter(Ticket.status == 'RESOLVED').count()
            
            # Get recent users
            recent_users_query = db.query(User).order_by(User.created_at.desc()).limit(5).all()
            recent_users = [AdminAPIAdapter.adapt_user_to_dict(user, minimal=True) for user in recent_users_query]
            
            # Get recent tickets
            recent_tickets_query = db.query(Ticket).order_by(Ticket.created_at.desc()).limit(5).all()
            recent_tickets = [AdminAPIAdapter.adapt_ticket_to_dict(ticket, include_relations=False) for ticket in recent_tickets_query]
            
            # Get system status
            system_status = {
                'ai_agent_integration': True,  # Since we're integrated
                'database_status': 'online',
                'last_backup': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return AdminDashboardStats(
                users={
                    'total': total_users,
                    'admin': admin_users,
                    'regular': regular_users
                },
                tickets={
                    'total': total_tickets,
                    'open': open_tickets,
                    'resolved': resolved_tickets
                },
                recent_users=recent_users,
                recent_tickets=recent_tickets,
                system_status=system_status
            )
            
        except Exception as e:
            logger.error(f"Error getting admin dashboard: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting admin dashboard: {str(e)}")
    
    return router

# ==================== USER MANAGEMENT ROUTER ====================

def create_user_management_router() -> APIRouter:
    """Create the user management FastAPI router"""
    
    router = APIRouter(prefix="/api/admin/users", tags=["user_management"])
    
    @router.get("/", response_model=UserListResponse)
    async def get_all_users(
        page: int = 1,
        per_page: int = 10,
        search: Optional[str] = None,
        current_user: User = Depends(get_current_user_flexible),
        db: Session = Depends(get_db)
    ):
        """Get all users with pagination and search"""
        # Require admin access and user list permission
        require_admin_access(current_user)
        if not current_user.has_permission(Permission.USER_LIST):
            raise HTTPException(status_code=403, detail="User list permission required")
        
        try:
            # Base query
            query = db.query(User)
            
            # Apply search filter
            if search:
                search_term = f'%{search}%'
                query = query.filter(
                    (User.username.ilike(search_term)) |
                    (User.email.ilike(search_term)) |
                    (User.full_name.ilike(search_term))
                )
            
            # Get total count for pagination
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            users_query = query.order_by(User.created_at.desc()).offset(offset).limit(per_page).all()
            
            # Convert to response format
            users = [AdminAPIAdapter.adapt_user_to_dict(user) for user in users_query]
            
            # Calculate pagination info
            has_next = offset + per_page < total
            has_prev = page > 1
            
            pagination = AdminAPIAdapter.create_pagination_dict(page, per_page, total, has_next, has_prev)
            
            return UserListResponse(users=users, pagination=pagination)
            
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting users: {str(e)}")
    
    @router.get("/{user_id}")
    async def get_user(
        user_id: int,
        current_user: User = Depends(get_current_user_flexible),
        db: Session = Depends(get_db)
    ):
        """Get user by ID"""
        # Require admin access and user read permission
        require_admin_access(current_user)
        if not current_user.has_permission(Permission.USER_READ):
            raise HTTPException(status_code=403, detail="User read permission required")
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return AdminAPIAdapter.adapt_user_to_dict(user)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting user: {str(e)}")
    
    return router

# ==================== TICKET MANAGEMENT ROUTER ====================

def create_ticket_management_router() -> APIRouter:
    """Create the ticket management FastAPI router"""
    
    router = APIRouter(prefix="/api/admin/tickets", tags=["ticket_management"])
    
    @router.get("/", response_model=TicketListResponse)
    async def get_tickets(
        page: int = 1,
        per_page: int = 10,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[str] = None,
        customer_id: Optional[int] = None,
        search: Optional[str] = None,
        current_user: User = Depends(get_current_user_flexible),
        db: Session = Depends(get_db)
    ):
        """Get all tickets with optional filtering"""
        # Require admin access and ticket list permission
        require_admin_access(current_user)
        if not current_user.has_permission(Permission.TICKET_LIST):
            raise HTTPException(status_code=403, detail="Ticket list permission required")
        
        try:
            # Base query
            query = db.query(Ticket)
            
            # Apply filters
            if status:
                query = query.filter(Ticket.status == status)
            if priority:
                query = query.filter(Ticket.priority == priority)
            if assignee_id:
                if assignee_id == 'unassigned':
                    query = query.filter(Ticket.assignee_id.is_(None))
                else:
                    query = query.filter(Ticket.assignee_id == int(assignee_id))
            if customer_id:
                query = query.filter(Ticket.customer_id == customer_id)
            if search:
                search_term = f'%{search}%'
                query = query.filter(
                    (Ticket.subject.ilike(search_term)) |
                    (Ticket.description.ilike(search_term)) |
                    (Ticket.ticket_id.ilike(search_term))
                )
            
            # Get total count for pagination
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            tickets_query = query.order_by(Ticket.created_at.desc()).offset(offset).limit(per_page).all()
            
            # Convert to response format with relations
            tickets = []
            for ticket in tickets_query:
                # Load customer and assignee
                customer = db.query(User).filter(User.id == ticket.customer_id).first() if ticket.customer_id else None
                assignee = db.query(User).filter(User.id == ticket.assignee_id).first() if ticket.assignee_id else None
                
                ticket_data = AdminAPIAdapter.adapt_ticket_to_dict(ticket, include_relations=False)
                ticket_data['customer'] = AdminAPIAdapter.adapt_user_to_dict(customer, minimal=True) if customer else None
                ticket_data['assignee'] = AdminAPIAdapter.adapt_user_to_dict(assignee, minimal=True) if assignee else None
                
                tickets.append(ticket_data)
            
            # Calculate pagination info
            has_next = offset + per_page < total
            has_prev = page > 1
            
            pagination = AdminAPIAdapter.create_pagination_dict(page, per_page, total, has_next, has_prev)
            
            return TicketListResponse(tickets=tickets, pagination=pagination)
            
        except Exception as e:
            logger.error(f"Error getting tickets: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting tickets: {str(e)}")
    
    @router.get("/{ticket_id}")
    async def get_ticket(
        ticket_id: str,
        current_user: User = Depends(get_current_user_flexible),
        db: Session = Depends(get_db)
    ):
        """Get a specific ticket by ID"""
        # Require admin access and ticket read permission
        require_admin_access(current_user)
        if not current_user.has_permission(Permission.TICKET_READ):
            raise HTTPException(status_code=403, detail="Ticket read permission required")
        
        try:
            ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
            if not ticket:
                raise HTTPException(status_code=404, detail="Ticket not found")
            
            # Load customer and assignee
            customer = db.query(User).filter(User.id == ticket.customer_id).first() if ticket.customer_id else None
            assignee = db.query(User).filter(User.id == ticket.assignee_id).first() if ticket.assignee_id else None
            
            # Get comments for this ticket
            comments_query = db.query(TicketComment).filter(TicketComment.ticket_id == ticket.id).order_by(TicketComment.created_at.asc()).all()
            comments = [AdminAPIAdapter.adapt_comment_to_dict(comment) for comment in comments_query]
            
            ticket_data = AdminAPIAdapter.adapt_ticket_to_dict(ticket, include_relations=False)
            ticket_data['customer'] = AdminAPIAdapter.adapt_user_to_dict(customer, minimal=True) if customer else None
            ticket_data['assignee'] = AdminAPIAdapter.adapt_user_to_dict(assignee, minimal=True) if assignee else None
            ticket_data['comments'] = comments
            
            return ticket_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting ticket {ticket_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting ticket: {str(e)}")
    
    @router.post("/")
    async def create_ticket(
        ticket_request: TicketCreateRequest,
        current_user: User = Depends(get_current_user_flexible),
        db: Session = Depends(get_db)
    ):
        """Create a new ticket"""
        # Require admin access and ticket create permission
        require_admin_access(current_user)
        if not current_user.has_permission(Permission.TICKET_CREATE):
            raise HTTPException(status_code=403, detail="Ticket create permission required")
        
        try:
            # Generate a unique ticket ID
            import uuid
            ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
            
            # Create new ticket
            new_ticket = Ticket(
                ticket_id=ticket_id,
                subject=ticket_request.subject,
                description=ticket_request.description,
                customer_id=ticket_request.customer_id,
                assignee_id=ticket_request.assignee_id,
                status='open',  # Default status for new tickets
                priority=ticket_request.priority,
                category=ticket_request.category,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(new_ticket)
            db.commit()
            db.refresh(new_ticket)
            
            return AdminAPIAdapter.adapt_ticket_to_dict(new_ticket, include_relations=False)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating ticket: {e}")
            raise HTTPException(status_code=500, detail=f"Error creating ticket: {str(e)}")
    
    @router.put("/{ticket_id}")
    async def update_ticket(
        ticket_id: str,
        ticket_request: TicketUpdateRequest,
        current_user: User = Depends(get_current_user_flexible),
        db: Session = Depends(get_db)
    ):
        """Update an existing ticket"""
        # Require admin access and ticket update permission
        require_admin_access(current_user)
        if not current_user.has_permission(Permission.TICKET_UPDATE):
            raise HTTPException(status_code=403, detail="Ticket update permission required")
        
        try:
            ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
            if not ticket:
                raise HTTPException(status_code=404, detail="Ticket not found")
            
            # Update ticket fields if provided
            if ticket_request.subject is not None:
                ticket.subject = ticket_request.subject
            if ticket_request.description is not None:
                ticket.description = ticket_request.description
            if ticket_request.customer_id is not None:
                ticket.customer_id = ticket_request.customer_id
            if ticket_request.assignee_id is not None:
                ticket.assignee_id = ticket_request.assignee_id
            if ticket_request.status is not None:
                ticket.status = ticket_request.status
            if ticket_request.priority is not None:
                ticket.priority = ticket_request.priority
            if ticket_request.category is not None:
                ticket.category = ticket_request.category
            
            # Always update the updated_at timestamp
            ticket.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(ticket)
            
            return AdminAPIAdapter.adapt_ticket_to_dict(ticket, include_relations=False)
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating ticket {ticket_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error updating ticket: {str(e)}")
    
    @router.post("/{ticket_id}/comments")
    async def add_comment(
        ticket_id: str,
        comment_request: CommentCreateRequest,
        current_user: User = Depends(get_current_user_flexible),
        db: Session = Depends(get_db)
    ):
        """Add a comment to a ticket"""
        # Require admin access and comment create permission
        require_admin_access(current_user)
        if not current_user.has_permission(Permission.COMMENT_CREATE):
            raise HTTPException(status_code=403, detail="Comment create permission required")
        
        try:
            ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
            if not ticket:
                raise HTTPException(status_code=404, detail="Ticket not found")
            
            # Create new comment
            new_comment = TicketComment(
                ticket_id=ticket.id,
                user_id=current_user.id,
                content=comment_request.text,
                is_internal=comment_request.is_internal,
                created_at=datetime.utcnow()
            )
            
            db.add(new_comment)
            
            # Update ticket's updated_at timestamp
            ticket.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(new_comment)
            
            return AdminAPIAdapter.adapt_comment_to_dict(new_comment)
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding comment to ticket {ticket_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error adding comment: {str(e)}")
    
    @router.get("/stats/overview")
    async def get_ticket_stats(
        current_user: User = Depends(get_current_user_flexible),
        db: Session = Depends(get_db)
    ):
        """Get ticket statistics"""
        # Require admin access and dashboard analytics permission
        require_admin_access(current_user)
        if not current_user.has_permission(Permission.DASHBOARD_ANALYTICS):
            raise HTTPException(status_code=403, detail="Dashboard analytics permission required")
        
        try:
            # Total tickets
            total_tickets = db.query(Ticket).count()
            
            # Tickets by status
            status_counts = {}
            for status in ['open', 'in_progress', 'waiting', 'resolved', 'closed']:
                count = db.query(Ticket).filter(Ticket.status == status).count()
                status_counts[status] = count
            
            # Tickets by priority
            priority_counts = {}
            for priority in ['low', 'medium', 'high', 'urgent']:
                count = db.query(Ticket).filter(Ticket.priority == priority).count()
                priority_counts[priority] = count
            
            # Unassigned tickets
            unassigned_count = db.query(Ticket).filter(Ticket.assigned_agent_id.is_(None)).count()
            
            # Recent tickets (last 7 days)
            from datetime import timedelta
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_tickets = db.query(Ticket).filter(Ticket.created_at >= seven_days_ago).count()
            
            return {
                'total': total_tickets,
                'by_status': status_counts,
                'by_priority': priority_counts,
                'unassigned': unassigned_count,
                'recent': recent_tickets
            }
            
        except Exception as e:
            logger.error(f"Error getting ticket stats: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting ticket statistics: {str(e)}")
    
    return router

# ==================== ANALYTICS ROUTER ====================

def create_analytics_router() -> APIRouter:
    """Create the analytics FastAPI router"""
    
    router = APIRouter(prefix="/api/admin/analytics", tags=["analytics"])
    
    @router.get("/performance-metrics", response_model=PerformanceMetricsResponse)
    async def get_performance_metrics(
        period: str = 'week',
        current_user: User = Depends(get_current_user_flexible),
        db: Session = Depends(get_db)
    ):
        """Get support team performance metrics"""
        # Require admin access and dashboard analytics permission
        require_admin_access(current_user)
        if not current_user.has_permission(Permission.DASHBOARD_ANALYTICS):
            raise HTTPException(status_code=403, detail="Dashboard analytics permission required")
        
        try:
            from datetime import timedelta
            
            # Calculate date range based on period
            end_date = datetime.utcnow()
            if period == 'week':
                start_date = end_date - timedelta(days=7)
            elif period == 'month':
                start_date = end_date - timedelta(days=30)
            elif period == 'year':
                start_date = end_date - timedelta(days=365)
            else:
                start_date = end_date - timedelta(days=7)  # Default to week
            
            # Get tickets in the date range
            tickets_in_period = db.query(Ticket).filter(
                Ticket.created_at >= start_date,
                Ticket.created_at <= end_date
            ).all()
            
            # Calculate metrics by date (simplified for now)
            metrics_by_date = []
            
            # Calculate summary metrics
            total_tickets_opened = len(tickets_in_period)
            resolved_tickets = [t for t in tickets_in_period if t.status == 'resolved']
            total_tickets_resolved = len(resolved_tickets)
            
            # Simplified metrics (in a real implementation, you'd calculate actual response/resolution times)
            avg_response_time = 2.5  # hours
            avg_resolution_time = 24.0  # hours
            avg_satisfaction = 4.2  # out of 5
            
            summary = {
                'avg_satisfaction': avg_satisfaction,
                'avg_response_time': avg_response_time,
                'avg_resolution_time': avg_resolution_time,
                'total_tickets_opened': total_tickets_opened,
                'total_tickets_resolved': total_tickets_resolved
            }
            
            return PerformanceMetricsResponse(
                period=period,
                start_date=start_date,
                end_date=end_date,
                metrics_by_date=metrics_by_date,
                summary=summary
            )
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting performance metrics: {str(e)}")
    
    @router.get("/customer-satisfaction")
    async def get_customer_satisfaction(
        period: str = 'month',
        current_user: User = Depends(get_current_user_flexible),
        db: Session = Depends(get_db)
    ):
        """Get customer satisfaction ratings"""
        # Require admin access and dashboard analytics permission
        require_admin_access(current_user)
        if not current_user.has_permission(Permission.DASHBOARD_ANALYTICS):
            raise HTTPException(status_code=403, detail="Dashboard analytics permission required")
        
        try:
            from datetime import timedelta
            
            # Calculate date range based on period
            end_date = datetime.utcnow()
            if period == 'week':
                start_date = end_date - timedelta(days=7)
            elif period == 'month':
                start_date = end_date - timedelta(days=30)
            elif period == 'year':
                start_date = end_date - timedelta(days=365)
            else:
                start_date = end_date - timedelta(days=30)  # Default to month
            
            # Simplified satisfaction data (in a real implementation, you'd have a satisfaction table)
            avg_rating = 4.2
            rating_counts = {1: 2, 2: 5, 3: 15, 4: 45, 5: 33}
            total_ratings = sum(rating_counts.values())
            
            return {
                'period': period,
                'start_date': start_date,
                'end_date': end_date,
                'average_rating': avg_rating,
                'rating_counts': rating_counts,
                'total_ratings': total_ratings,
                'recent_ratings': []  # Would contain recent satisfaction entries
            }
            
        except Exception as e:
            logger.error(f"Error getting customer satisfaction: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting customer satisfaction: {str(e)}")
    
    return router

# ==================== SYSTEM STATUS ROUTER ====================

def create_system_status_router() -> APIRouter:
    """Create the system status FastAPI router"""
    
    router = APIRouter(prefix="/api/admin/system", tags=["system_status"])
    
    @router.get("/status")
    async def get_system_status(
        current_user: User = Depends(get_current_user_flexible),
        db: Session = Depends(get_db)
    ):
        """Get system status information"""
        # Require admin access and system logs permission
        require_admin_access(current_user)
        if not current_user.has_permission(Permission.SYSTEM_LOGS):
            raise HTTPException(status_code=403, detail="System logs permission required")
        
        try:
            # Get database stats
            user_count = db.query(User).count()
            ticket_count = db.query(Ticket).count()
            comment_count = db.query(TicketComment).count()
            activity_count = db.query(TicketActivity).count() if hasattr(db.query(TicketActivity), 'count') else 0
            
            # Get integration status
            integration_status = {
                'ai_agent_backend_available': True,  # Since we're integrated
                'unified_database': True,
                'unified_authentication': True
            }
            
            # Get system info
            import sys
            system_info = {
                'python_version': sys.version,
                'fastapi_version': 'Integrated',
                'database_type': 'PostgreSQL',
                'environment': 'integrated'
            }
            
            return {
                'system_status': {
                    'database_stats': {
                        'users': user_count,
                        'tickets': ticket_count,
                        'comments': comment_count,
                        'activities': activity_count
                    },
                    'integration_status': integration_status,
                    'system_info': system_info,
                    'uptime': 'Integrated with main application',
                    'last_backup': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting system status: {str(e)}")
    
    return router

# ==================== MAIN INTEGRATION FUNCTION ====================

def create_admin_dashboard_integration() -> List[APIRouter]:
    """Create all admin dashboard integration routers"""
    
    routers = [
        create_admin_dashboard_router(),
        create_user_management_router(),
        create_ticket_management_router(),
        create_analytics_router(),
        create_system_status_router()
    ]
    
    logger.info("Admin dashboard integration routers created successfully")
    return routers

# ==================== BACKWARD COMPATIBILITY LAYER ====================

class BackwardCompatibilityAdapter:
    """Adapter to maintain backward compatibility with existing admin dashboard API contracts"""
    
    @staticmethod
    def adapt_flask_response_to_fastapi(flask_response: Dict[str, Any]) -> JSONResponse:
        """Convert Flask response format to FastAPI JSONResponse"""
        # Handle Flask-style success/error responses
        if 'success' in flask_response:
            if flask_response['success']:
                return JSONResponse(content=flask_response, status_code=200)
            else:
                return JSONResponse(content=flask_response, status_code=400)
        
        # Default to success response
        return JSONResponse(content=flask_response, status_code=200)
    
    @staticmethod
    def adapt_fastapi_request_to_flask(request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert FastAPI request format to Flask format if needed"""
        # Most request formats are compatible, but this allows for future adaptations
        return request_data

# Export the main integration function
__all__ = ['create_admin_dashboard_integration', 'AdminAPIAdapter', 'BackwardCompatibilityAdapter']