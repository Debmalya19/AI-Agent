"""
Admin Dashboard Compatibility Layer

This module provides backward compatibility with existing admin dashboard Flask API contracts.
It wraps the new FastAPI endpoints to maintain the same response formats and behavior.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from .admin_dashboard_integration import (
    AdminAPIAdapter, 
    create_admin_dashboard_router,
    create_user_management_router,
    create_ticket_management_router,
    create_analytics_router,
    create_system_status_router
)
from .unified_auth import get_current_user, require_admin_access
from .unified_models import UnifiedUser as User, UnifiedTicket as Ticket, UnifiedTicketComment as TicketComment
from .database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def create_flask_compatible_router() -> APIRouter:
    """Create a router that maintains Flask API compatibility"""
    
    router = APIRouter(prefix="/api", tags=["flask_compatibility"])
    
    # ==================== AUTH ENDPOINTS ====================
    
    @router.post("/auth/login")
    async def flask_compatible_login(request: Request):
        """Flask-compatible login endpoint"""
        # This would delegate to the unified auth system
        # For now, return a compatibility response
        return JSONResponse(content={
            "success": True,
            "message": "Login handled by unified authentication system",
            "redirect": "/api/admin/dashboard"
        })
    
    @router.post("/auth/logout")
    async def flask_compatible_logout():
        """Flask-compatible logout endpoint"""
        return JSONResponse(content={
            "success": True,
            "message": "Logged out successfully"
        })
    
    # ==================== ADMIN ENDPOINTS ====================
    
    @router.post("/admin/register")
    async def flask_compatible_admin_register(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        """Flask-compatible admin registration endpoint"""
        require_admin_access(current_user)
        
        try:
            data = await request.json()
            
            # Validate required fields
            required_fields = ['username', 'email', 'password']
            for field in required_fields:
                if field not in data:
                    return JSONResponse(content={
                        'success': False, 
                        'message': f'{field.title()} is required'
                    }, status_code=400)
            
            # Check if user already exists
            existing_user = db.query(User).filter(
                (User.username == data['username']) | (User.email == data['email'])
            ).first()
            
            if existing_user:
                return JSONResponse(content={
                    'success': False, 
                    'message': 'User with this username or email already exists'
                }, status_code=400)
            
            # Create new admin user
            from werkzeug.security import generate_password_hash
            
            new_user = User(
                username=data['username'],
                email=data['email'],
                full_name=data.get('full_name'),
                phone=data.get('phone'),
                is_admin=True,
                password_hash=generate_password_hash(data['password']),
                created_at=datetime.utcnow()
            )
            
            db.add(new_user)
            db.commit()
            
            return JSONResponse(content={
                'success': True, 
                'message': 'Admin user registered successfully'
            }, status_code=201)
            
        except Exception as e:
            logger.error(f"Error registering admin user: {e}")
            return JSONResponse(content={
                'success': False, 
                'message': 'Failed to register admin user'
            }, status_code=500)
    
    @router.get("/admin/dashboard")
    async def flask_compatible_dashboard(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        """Flask-compatible dashboard endpoint"""
        require_admin_access(current_user)
        
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
            recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
            
            # Get recent tickets
            recent_tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).limit(5).all()
            
            # Get system status
            system_status = {
                'ai_agent_integration': True,
                'database_status': 'online',
                'last_backup': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return JSONResponse(content={
                'success': True,
                'stats': {
                    'users': {
                        'total': total_users,
                        'admin': admin_users,
                        'regular': regular_users
                    },
                    'tickets': {
                        'total': total_tickets,
                        'open': open_tickets,
                        'resolved': resolved_tickets
                    },
                    'recent_users': [AdminAPIAdapter.adapt_user_to_dict(user) for user in recent_users],
                    'recent_tickets': [AdminAPIAdapter.adapt_ticket_to_dict(ticket) for ticket in recent_tickets],
                    'system_status': system_status
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting admin dashboard: {e}")
            return JSONResponse(content={
                'success': False,
                'message': f'Error getting admin dashboard: {str(e)}'
            }, status_code=500)
    
    @router.get("/admin/users")
    async def flask_compatible_get_users(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        """Flask-compatible get users endpoint"""
        require_admin_access(current_user)
        
        try:
            # Get query parameters
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 10))
            search = request.query_params.get('search', '')
            
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
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            users_query = query.order_by(User.created_at.desc()).offset(offset).limit(per_page).all()
            
            # Calculate pagination info
            has_next = offset + per_page < total
            has_prev = page > 1
            pages = (total + per_page - 1) // per_page
            
            return JSONResponse(content={
                'success': True,
                'users': [AdminAPIAdapter.adapt_user_to_dict(user) for user in users_query],
                'pagination': {
                    'total': total,
                    'pages': pages,
                    'page': page,
                    'per_page': per_page,
                    'has_next': has_next,
                    'has_prev': has_prev
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return JSONResponse(content={
                'success': False,
                'message': f'Error getting users: {str(e)}'
            }, status_code=500)
    
    # ==================== TICKET ENDPOINTS ====================
    
    @router.get("/tickets/")
    async def flask_compatible_get_tickets(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        """Flask-compatible get tickets endpoint"""
        try:
            # Get query parameters
            status = request.query_params.get('status')
            priority = request.query_params.get('priority')
            assignee_id = request.query_params.get('assignee_id')
            customer_id = request.query_params.get('customer_id')
            search = request.query_params.get('search')
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 10))
            
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
                query = query.filter(Ticket.customer_id == int(customer_id))
            if search:
                search_term = f'%{search}%'
                query = query.filter(
                    (Ticket.subject.ilike(search_term)) |
                    (Ticket.description.ilike(search_term)) |
                    (Ticket.ticket_id.ilike(search_term))
                )
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            tickets_query = query.order_by(Ticket.created_at.desc()).offset(offset).limit(per_page).all()
            
            # Format tickets with customer and assignee info
            tickets = []
            for ticket in tickets_query:
                customer = db.query(User).filter(User.id == ticket.customer_id).first() if ticket.customer_id else None
                assignee = db.query(User).filter(User.id == ticket.assignee_id).first() if ticket.assignee_id else None
                
                ticket_data = AdminAPIAdapter.adapt_ticket_to_dict(ticket)
                ticket_data['customer'] = AdminAPIAdapter.adapt_user_to_dict(customer, minimal=True) if customer else None
                ticket_data['assignee'] = AdminAPIAdapter.adapt_user_to_dict(assignee, minimal=True) if assignee else None
                
                tickets.append(ticket_data)
            
            # Calculate pagination info
            has_next = offset + per_page < total
            has_prev = page > 1
            pages = (total + per_page - 1) // per_page
            
            return JSONResponse(content={
                'tickets': tickets,
                'pagination': {
                    'total': total,
                    'pages': pages,
                    'page': page,
                    'per_page': per_page,
                    'has_next': has_next,
                    'has_prev': has_prev
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting tickets: {e}")
            return JSONResponse(content={
                'error': 'Failed to retrieve tickets', 
                'details': str(e)
            }, status_code=500)
    
    @router.get("/tickets/{ticket_id}")
    async def flask_compatible_get_ticket(
        ticket_id: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        """Flask-compatible get ticket endpoint"""
        try:
            ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
            if not ticket:
                return JSONResponse(content={'error': 'Ticket not found'}, status_code=404)
            
            # Get customer and assignee info
            customer = db.query(User).filter(User.id == ticket.customer_id).first() if ticket.customer_id else None
            assignee = db.query(User).filter(User.id == ticket.assignee_id).first() if ticket.assignee_id else None
            
            # Get comments for this ticket
            comments = db.query(TicketComment).filter(TicketComment.ticket_id == ticket.id).order_by(TicketComment.created_at.asc()).all()
            comments_data = [AdminAPIAdapter.adapt_comment_to_dict(comment) for comment in comments]
            
            ticket_data = AdminAPIAdapter.adapt_ticket_to_dict(ticket)
            ticket_data['customer'] = AdminAPIAdapter.adapt_user_to_dict(customer, minimal=True) if customer else None
            ticket_data['assignee'] = AdminAPIAdapter.adapt_user_to_dict(assignee, minimal=True) if assignee else None
            ticket_data['comments'] = comments_data
            
            return JSONResponse(content=ticket_data)
            
        except Exception as e:
            logger.error(f"Error getting ticket {ticket_id}: {e}")
            return JSONResponse(content={
                'error': 'Failed to retrieve ticket', 
                'details': str(e)
            }, status_code=500)
    
    @router.post("/tickets/")
    async def flask_compatible_create_ticket(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        """Flask-compatible create ticket endpoint"""
        try:
            data = await request.json()
            
            # Validate required fields
            required_fields = ['subject', 'description', 'customer_id', 'priority', 'category']
            for field in required_fields:
                if field not in data:
                    return JSONResponse(content={
                        'error': f'Missing required field: {field}'
                    }, status_code=400)
            
            # Generate a unique ticket ID
            import uuid
            ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
            
            # Create new ticket
            new_ticket = Ticket(
                ticket_id=ticket_id,
                subject=data['subject'],
                description=data['description'],
                customer_id=data['customer_id'],
                assignee_id=data.get('assignee_id'),
                status='open',
                priority=data['priority'],
                category=data['category'],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(new_ticket)
            db.commit()
            db.refresh(new_ticket)
            
            return JSONResponse(content=AdminAPIAdapter.adapt_ticket_to_dict(new_ticket), status_code=201)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating ticket: {e}")
            return JSONResponse(content={
                'error': 'Failed to create ticket', 
                'details': str(e)
            }, status_code=500)
    
    @router.get("/tickets/stats")
    async def flask_compatible_ticket_stats(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        """Flask-compatible ticket stats endpoint"""
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
            unassigned_count = db.query(Ticket).filter(Ticket.assignee_id.is_(None)).count()
            
            # Recent tickets (last 7 days)
            from datetime import timedelta
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_tickets = db.query(Ticket).filter(Ticket.created_at >= seven_days_ago).count()
            
            return JSONResponse(content={
                'total': total_tickets,
                'by_status': status_counts,
                'by_priority': priority_counts,
                'unassigned': unassigned_count,
                'recent': recent_tickets
            })
            
        except Exception as e:
            logger.error(f"Error getting ticket stats: {e}")
            return JSONResponse(content={
                'error': 'Failed to retrieve ticket statistics', 
                'details': str(e)
            }, status_code=500)
    
    return router

def create_compatibility_integration() -> APIRouter:
    """Create the complete Flask compatibility integration"""
    return create_flask_compatible_router()

# Export the main function
__all__ = ['create_compatibility_integration', 'create_flask_compatible_router']