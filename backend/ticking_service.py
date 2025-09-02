"""
Ticking Service - Business logic for ticket management
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from backend.models import Ticket, TicketComment, TicketActivity, TicketStatus, TicketPriority, TicketCategory
from backend.database import get_db

class TickingService:
    """Service class for managing tickets with database context retrieval"""
    
    def __init__(self, db_session: Session = None):
        self.db = db_session or next(get_db())
    
    def create_ticket(self, title: str, description: str, user_id: int = None, 
                     priority: TicketPriority = TicketPriority.MEDIUM, 
                     category: TicketCategory = TicketCategory.GENERAL,
                     tags: List[str] = None, ticket_metadata: Dict[str, Any] = None) -> Ticket:
        """Create a new ticket"""
        
        ticket = Ticket(
            title=title,
            description=description,
            customer_id=user_id,  # Using customer_id field in DB but passing user_id
            priority=priority,
            category=category,
            tags=",".join(tags) if tags else None,
            ticket_metadata=str(ticket_metadata) if ticket_metadata else None
        )
        
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        
        # Log activity
        self._log_activity(ticket.id, "ticket_created", f"Ticket created: {title}")
        
        return ticket
    
    def get_ticket(self, ticket_id: int) -> Optional[Ticket]:
        """Retrieve a ticket by ID with all related data"""
        return self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    def get_tickets(self, status: TicketStatus = None, user_id: int = None,
                   priority: TicketPriority = None, category: TicketCategory = None,
                   limit: int = 100, offset: int = 0) -> List[Ticket]:
        """Retrieve tickets with filters"""
        
        query = self.db.query(Ticket)
        
        if status:
            query = query.filter(Ticket.status == status)
        if user_id:
            query = query.filter(Ticket.customer_id == user_id)  # Using customer_id field in DB but passing user_id
        if priority:
            query = query.filter(Ticket.priority == priority)
        if category:
            query = query.filter(Ticket.category == category)
            
        return query.order_by(Ticket.created_at.desc()).offset(offset).limit(limit).all()
    
    def update_ticket_status(self, ticket_id: int, new_status: TicketStatus, 
                           user_id: int = None) -> bool:
        """Update ticket status"""
        
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return False
            
        old_status = ticket.status
        ticket.status = new_status
        ticket.updated_at = datetime.now(timezone.utc)
        
        if new_status == TicketStatus.RESOLVED:
            ticket.resolved_at = datetime.now(timezone.utc)
            
        self.db.commit()
        
        # Log activity
        self._log_activity(ticket.id, "status_change", 
                           f"Status changed from {old_status.value} to {new_status.value}", 
                           user_id)
        
        return True
    
    def assign_ticket(self, ticket_id: int, agent_id: int, user_id: int = None) -> bool:
        """Assign ticket to an agent"""
        
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return False
            
        ticket.assigned_agent_id = agent_id
        ticket.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        
        # Log activity
        self._log_activity(ticket.id, "ticket_assigned", 
                           f"Ticket assigned to agent ID: {agent_id}", 
                           user_id)
        
        return True
    
    def add_comment(self, ticket_id: int, comment: str, author_id: int = None,
                   is_internal: bool = False) -> Optional[TicketComment]:
        """Add a comment to a ticket"""
        
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return None
            
        ticket_comment = TicketComment(
            ticket_id=ticket_id,
            author_id=author_id,
            comment=comment,
            is_internal=is_internal
        )
        
        self.db.add(ticket_comment)
        self.db.commit()
        self.db.refresh(ticket_comment)
        
        # Log activity
        comment_type = "internal_comment" if is_internal else "public_comment"
        self._log_activity(ticket.id, comment_type, "Comment added", author_id)
        
        return ticket_comment
    
    def search_tickets(self, query: str, limit: int = 50) -> List[Ticket]:
        """Search tickets using database context retrieval"""
        
        search_term = f"%{query}%"
        return self.db.query(Ticket).filter(
            or_(
                Ticket.title.ilike(search_term),
                Ticket.description.ilike(search_term),
                Ticket.tags.ilike(search_term)
            )
        ).order_by(Ticket.created_at.desc()).limit(limit).all()
    
    def get_ticket_statistics(self) -> Dict[str, Any]:
        """Get ticket statistics for dashboard"""
        
        stats = {
            "total_tickets": self.db.query(Ticket).count(),
            "open_tickets": self.db.query(Ticket).filter(Ticket.status == TicketStatus.OPEN).count(),
            "in_progress_tickets": self.db.query(Ticket).filter(Ticket.status == TicketStatus.IN_PROGRESS).count(),
            "resolved_tickets": self.db.query(Ticket).filter(Ticket.status == TicketStatus.RESOLVED).count(),
            "closed_tickets": self.db.query(Ticket).filter(Ticket.status == TicketStatus.CLOSED).count(),
            "high_priority_tickets": self.db.query(Ticket).filter(Ticket.priority == TicketPriority.HIGH).count(),
            "critical_priority_tickets": self.db.query(Ticket).filter(Ticket.priority == TicketPriority.CRITICAL).count()
        }
        
        return stats
    
    def _log_activity(self, ticket_id: int, activity_type: str, description: str, 
                     user_id: int = None):
        """Log ticket activity"""
        
        activity = TicketActivity(
            ticket_id=ticket_id,
            activity_type=activity_type,
            description=description,
            performed_by_id=user_id
        )
        
        self.db.add(activity)
        self.db.commit()

class TicketContextRetriever:
    """Context retrieval service using database for ticket system"""
    
    def __init__(self, db_session: Session = None):
        self.db = db_session or next(get_db())
    
    def get_customer_context(self, user_id: int) -> Dict[str, Any]:
        """Get customer context for ticket creation"""
        
        from backend.models import Customer, Order
        
        customer = self.db.query(Customer).filter(Customer.id == user_id).first()
        if not customer:
            return {}
        
        # Get customer orders
        orders = self.db.query(Order).filter(Order.customer_id == customer.customer_id).all()
        
        return {
            "customer_info": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "total_orders": len(orders)
            },
            "recent_orders": [
                {
                    "order_id": order.order_id,
                    "date": order.order_date.isoformat() if order.order_date else None,
                    "amount": float(order.amount) if order.amount else 0
                }
                for order in orders[-5:]  # Last 5 orders
            ]
        }
    
    def get_similar_tickets(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find similar tickets based on content"""
        
        from sqlalchemy import or_
        
        search_term = f"%{query}%"
        tickets = self.db.query(Ticket).filter(
            or_(
                Ticket.title.ilike(search_term),
                Ticket.description.ilike(search_term)
            )
        ).order_by(Ticket.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description[:100] + "...",
                "status": ticket.status.value,
                "priority": ticket.priority.value,
                "category": ticket.category.value,
                "created_at": ticket.created_at.isoformat()
            }
            for ticket in tickets
        ]
    
    def get_ticket_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Get ticket history for a user"""
        
        tickets = self.db.query(Ticket).filter(
            Ticket.customer_id == user_id  # Using customer_id field in DB but passing user_id
        ).order_by(Ticket.created_at.desc()).all()
        
        return [
            {
                "id": ticket.id,
                "title": ticket.title,
                "status": ticket.status.value,
                "priority": ticket.priority.value,
                "category": ticket.category.value,
                "created_at": ticket.created_at.isoformat(),
                "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None
            }
            for ticket in tickets
        ]
