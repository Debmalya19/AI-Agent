"""
Social Media Ticket Service
Handles automatic ticket generation and management for social media mentions
"""

from typing import Dict, Optional, List, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .models import Customer, Ticket, TicketStatus, TicketPriority, TicketCategory
from .database import SessionLocal
from .ticking_service import TickingService
from .social_media_integration import SocialMediaMonitor
from .sentiment_analyzer import analyze_social_media_content

class SocialMediaTicketService:
    """Service for managing social media-related tickets"""
    
    def __init__(self, db_session: Session = None):
        self.db = db_session or SessionLocal()
        self.social_media_monitor = SocialMediaMonitor(self.db)
        self.ticking_service = TickingService(self.db)
    
    def process_social_mention(self, platform: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a social media mention and create or update a ticket
        Returns the ticket information and appropriate response
        """
        if platform.lower() == "twitter":
            ticket_id = self.social_media_monitor.process_tweet(content)
            if ticket_id:
                return self._create_response(ticket_id, platform)
        
        return {
            "success": False,
            "message": "Unable to process social media mention",
            "error": "Unsupported platform or invalid content"
        }
    
    def get_ticket_status(self, ticket_id: int) -> Dict[str, Any]:
        """
        Get the current status of a ticket
        Returns ticket details and status information
        """
        ticket = self.ticking_service.get_ticket(ticket_id)
        if not ticket:
            return {
                "success": False,
                "message": "Ticket not found",
                "error": f"No ticket found with ID {ticket_id}"
            }
        
        return {
            "success": True,
            "ticket_id": ticket.id,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "created_at": ticket.created_at.isoformat(),
            "last_updated": ticket.updated_at.isoformat(),
            "response_message": self._generate_status_message(ticket)
        }
    
    def update_ticket_from_social(self, ticket_id: int, update_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a ticket based on a social media response/update
        """
        ticket = self.ticking_service.get_ticket(ticket_id)
        if not ticket:
            return {
                "success": False,
                "message": "Ticket not found",
                "error": f"No ticket found with ID {ticket_id}"
            }
        
        # Add the update as a comment
        comment = self._create_social_comment(update_content)
        self.ticking_service.add_comment(
            ticket_id=ticket_id,
            comment=comment,
            author_id=ticket.customer_id,
            is_internal=False
        )
        
        return {
            "success": True,
            "message": "Ticket updated successfully",
            "ticket_id": ticket_id
        }
    
    def _create_response(self, ticket_id: int, platform: str) -> Dict[str, Any]:
        """Create a response for the social media mention"""
        ticket = self.ticking_service.get_ticket(ticket_id)
        if not ticket:
            return {
                "success": False,
                "message": "Failed to create ticket",
                "error": "Ticket creation failed"
            }
        
        response_message = f"""Thank you for reaching out! We've created a support ticket to address your concern.
Ticket #{ticket_id} - Status: {ticket.status.value}
We'll keep you updated on the progress. You can check the status anytime by referencing this ticket number."""

        return {
            "success": True,
            "ticket_id": ticket_id,
            "platform": platform,
            "response_message": response_message,
            "status": ticket.status.value
        }
    
    def _generate_status_message(self, ticket: Ticket) -> str:
        """Generate a status message for the ticket"""
        status_messages = {
            TicketStatus.OPEN: "We've received your request and are reviewing it.",
            TicketStatus.IN_PROGRESS: "Our team is actively working on your request.",
            TicketStatus.RESOLVED: "We've resolved your request. Please let us know if you need anything else.",
            TicketStatus.CLOSED: "This ticket has been closed. Please create a new ticket if you need further assistance."
        }
        
        return f"Ticket #{ticket.id} - {status_messages.get(ticket.status, 'Status unknown')}"
    
    def _create_social_comment(self, update_content: Dict[str, Any]) -> str:
        """Create a comment from social media update content"""
        platform = update_content.get("platform", "social media")
        content = update_content.get("text", "")
        user = update_content.get("user", {})
        timestamp = update_content.get("created_at", datetime.now(timezone.utc).isoformat())
        
        return f"""Update from {platform}:
Content: {content}
From: @{user.get('screen_name', 'unknown')}
Time: {timestamp}"""