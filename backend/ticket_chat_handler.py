"""
Ticket Chat Handler
Handles ticket-related queries in the chat system
"""

import re
from typing import Dict, Optional, Any, List
from .models import TicketStatus, Ticket
from .social_media_ticket_service import SocialMediaTicketService
from .ticking_service import TickingService
from .database import SessionLocal
from sqlalchemy import desc

class TicketChatHandler:
    """Handles ticket-related queries in chat interactions"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.social_media_service = SocialMediaTicketService(self.db)
        self.ticking_service = TickingService(self.db)
    
    def handle_ticket_query(self, query: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Handle ticket-related queries and return appropriate responses
        """
        query_lower = query.lower()
        
        # Check for customer ID in the query
        customer_id_match = re.search(r'customer\s*id\s*[:#]?\s*(\d+)', query_lower)
        if customer_id_match:
            return self._handle_customer_tickets_query(int(customer_id_match.group(1)))
        
        # Check ticket status query
        if any(keyword in query_lower for keyword in ['ticket status', 'check ticket', 'status of ticket', 'ticket #']):
            return self._handle_ticket_status_query(query_lower, user_id)
            
        # Check ticket creation query
        elif any(keyword in query_lower for keyword in ['create ticket', 'new ticket', 'open ticket', 'submit ticket']):
            return self._handle_ticket_creation_query(query, user_id)
            
        # Check ticket update query
        elif any(keyword in query_lower for keyword in ['update ticket', 'add to ticket', 'comment on ticket']):
            return self._handle_ticket_update_query(query, user_id)
            
        # If no customer ID or ticket number provided, ask for it
        if any(keyword in query_lower for keyword in ['ticket', 'tickets', 'issue', 'complaint']):
            return {
                "response": "Could you please provide your customer ID so I can look up your tickets?",
                "requires_customer_id": True
            }
            
        return None
    
    def _handle_customer_tickets_query(self, customer_id: int) -> Dict[str, Any]:
        """Handle queries for all tickets related to a customer ID"""
        try:
            # Get all tickets for the customer, most recent first
            tickets = self.db.query(Ticket).filter(
                Ticket.customer_id == customer_id
            ).order_by(desc(Ticket.created_at)).all()
            
            if not tickets:
                return {
                    "response": f"I couldn't find any tickets associated with customer ID {customer_id}. Would you like to create a new ticket?",
                    "no_tickets_found": True
                }
            
            # Get social media mentions related to these tickets
            social_mentions = []
            for ticket in tickets:
                if ticket.social_mentions:
                    for mention in ticket.social_mentions:
                        social_mentions.append({
                            "ticket_id": ticket.id,
                            "platform": mention.platform.value,
                            "content": mention.content,
                            "posted_at": mention.posted_at.isoformat()
                        })
            
            # Format response
            response = f"I found {len(tickets)} ticket(s) for customer ID {customer_id}:\n\n"
            
            for ticket in tickets:
                response += f"Ticket #{ticket.id}\n"
                response += f"Status: {ticket.status.value}\n"
                response += f"Priority: {ticket.priority.value}\n"
                response += f"Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                if ticket.resolved_at:
                    response += f"Resolved: {ticket.resolved_at.strftime('%Y-%m-%d %H:%M')}\n"
                response += "\n"
            
            if social_mentions:
                response += "\nThese tickets were created from your social media posts:\n"
                for mention in social_mentions:
                    response += f"\nTicket #{mention['ticket_id']} - {mention['platform']}\n"
                    response += f"Posted on: {mention['posted_at']}\n"
                    response += f"Content: {mention['content'][:100]}...\n"
            
            response += "\nWould you like to check the details of any specific ticket? Just provide the ticket number."
            
            return {
                "response": response,
                "tickets": [{"id": t.id, "status": t.status.value} for t in tickets],
                "social_mentions": social_mentions
            }
            
        except Exception as e:
            return {
                "response": f"I apologize, but I encountered an error while looking up tickets for customer ID {customer_id}. Please try again later.",
                "error": str(e)
            }

    def _handle_ticket_status_query(self, query: str, user_id: Optional[int]) -> Dict[str, Any]:
        """Handle queries about ticket status"""
        
        # Try to extract ticket ID from query
        ticket_id_match = re.search(r'ticket\s*#?\s*(\d+)', query, re.IGNORECASE)
        if not ticket_id_match:
            return {
                "response": "Could you please provide the ticket number you'd like to check?",
                "requires_ticket_id": True
            }
        
        ticket_id = int(ticket_id_match.group(1))
        status_info = self.social_media_service.get_ticket_status(ticket_id)
        
        if not status_info['success']:
            return {
                "response": f"I couldn't find ticket #{ticket_id}. Could you please verify the ticket number?",
                "requires_ticket_id": True
            }
        
        return {
            "response": self._format_ticket_status_response(status_info),
            "ticket_info": status_info
        }
    
    def _handle_ticket_creation_query(self, query: str, user_id: Optional[int]) -> Dict[str, Any]:
        """Handle ticket creation requests"""
        if not user_id:
            return {
                "response": "To create a ticket, I'll need your customer ID. Could you please provide it?",
                "requires_customer_id": True
            }
        
        # Create ticket using the ticking service
        try:
            ticket = self.ticking_service.create_ticket(
                title="Chat Support Request",
                description=query,
                user_id=user_id,
                category="GENERAL"  # You might want to determine this based on query content
            )
            
            return {
                "response": f"I've created ticket #{ticket.id} for you. You can use this ticket number to check the status or add updates later.",
                "ticket_id": ticket.id
            }
            
        except Exception as e:
            return {
                "response": "I apologize, but I couldn't create a ticket at this moment. Please try again later.",
                "error": str(e)
            }
    
    def _handle_ticket_update_query(self, query: str, user_id: Optional[int]) -> Dict[str, Any]:
        """Handle ticket update requests"""
        import re
        
        # Try to extract ticket ID from query
        ticket_id_match = re.search(r'ticket\s*#?\s*(\d+)', query, re.IGNORECASE)
        if not ticket_id_match:
            return {
                "response": "To update a ticket, I'll need the ticket number. Could you please provide it?",
                "requires_ticket_id": True
            }
        
        ticket_id = int(ticket_id_match.group(1))
        
        # Extract the update content (everything after the ticket number)
        update_content = query[ticket_id_match.end():].strip()
        if not update_content:
            return {
                "response": f"What would you like to add to ticket #{ticket_id}?",
                "requires_update_content": True,
                "ticket_id": ticket_id
            }
        
        # Add the update to the ticket
        try:
            self.ticking_service.add_comment(
                ticket_id=ticket_id,
                comment=update_content,
                author_id=user_id
            )
            
            return {
                "response": f"I've added your update to ticket #{ticket_id}. Is there anything else you'd like to know about this ticket?",
                "ticket_id": ticket_id
            }
            
        except Exception as e:
            return {
                "response": f"I'm sorry, but I couldn't update ticket #{ticket_id}. Please try again later.",
                "error": str(e)
            }
    
    def _format_ticket_status_response(self, status_info: Dict[str, Any]) -> str:
        """Format ticket status information into a user-friendly response"""
        ticket_id = status_info['ticket_id']
        status = status_info['status'].replace('_', ' ').title()
        created_at = status_info['created_at']
        
        response = f"Ticket #{ticket_id} Status: {status}\n"
        response += f"Created: {created_at}\n"
        
        if status == "Resolved":
            response += f"Resolved: {status_info.get('last_updated', 'Unknown')}\n"
        
        response += "\nIs there anything specific about this ticket you'd like to know?"
        
        return response