# Integration module for connecting admin-dashboard with ai-agent backend

from sqlalchemy.orm import Session
import importlib.util
import sys
import os
import logging

# Path to the ai-agent root directory
AI_AGENT_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add the ai-agent backend directory to sys.path FIRST (before admin-dashboard backend)
backend_path = os.path.join(AI_AGENT_ROOT_PATH, 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Add the ai-agent root path to sys.path if it's not already there
if AI_AGENT_ROOT_PATH not in sys.path:
    sys.path.insert(0, AI_AGENT_ROOT_PATH)

# Import ai-agent backend modules
try:
    import backend.database as root_backend_database
    import backend.models as root_backend_models

    AIAgentTicket = root_backend_models.Ticket
    AIAgentTicketComment = root_backend_models.TicketComment
    AIAgentTicketActivity = root_backend_models.TicketActivity
    AIAgentCustomer = root_backend_models.Customer
    get_db = root_backend_database.get_db

    # Flag to indicate successful imports
    AI_AGENT_BACKEND_AVAILABLE = True
except Exception as e:
    logging.warning(f"Warning: Could not import ai-agent backend modules: {e}")
    # Set dummy values to avoid runtime errors
    AIAgentTicket = None
    AIAgentTicketComment = None
    AIAgentTicketActivity = None
    AIAgentCustomer = None
    get_db = None
    AI_AGENT_BACKEND_AVAILABLE = False

# Function to sync a ticket from admin-dashboard to ai-agent backend
def sync_ticket_to_ai_agent(admin_ticket, db_session=None):
    """Sync a ticket from admin-dashboard to ai-agent backend"""
    if not AI_AGENT_BACKEND_AVAILABLE:
        return None
    
    # Get a database session if one wasn't provided
    close_session = False
    if db_session is None:
        db_session = next(get_db())
        close_session = True
    
    try:
        # Check if the ticket already exists in the ai-agent backend
        ai_agent_ticket = db_session.query(AIAgentTicket).filter_by(title=admin_ticket.title).first()
        
        if ai_agent_ticket is None:
            # Create a new ticket in the ai-agent backend
            ai_agent_ticket = AIAgentTicket(
                title=admin_ticket.title,
                description=admin_ticket.description,
                status=admin_ticket.status.value,
                priority=admin_ticket.priority.value,
                category=admin_ticket.category.value,
                created_at=admin_ticket.created_at,
                updated_at=admin_ticket.updated_at,
                resolved_at=admin_ticket.resolved_at
            )
            db_session.add(ai_agent_ticket)
            db_session.commit()
        else:
            # Update the existing ticket
            ai_agent_ticket.title = admin_ticket.title
            ai_agent_ticket.description = admin_ticket.description
            ai_agent_ticket.status = admin_ticket.status.value
            ai_agent_ticket.priority = admin_ticket.priority.value
            ai_agent_ticket.category = admin_ticket.category.value
            ai_agent_ticket.updated_at = admin_ticket.updated_at
            ai_agent_ticket.resolved_at = admin_ticket.resolved_at
            db_session.commit()
        
        return ai_agent_ticket
    
    finally:
        if close_session:
            db_session.close()

# Function to sync a customer from admin-dashboard to ai-agent backend
def sync_customer_to_ai_agent(admin_user, db_session=None):
    """Sync a user from admin-dashboard to ai-agent backend as a customer"""
    if not AI_AGENT_BACKEND_AVAILABLE:
        return None
    
    # Get a database session if one wasn't provided
    close_session = False
    if db_session is None:
        db_session = next(get_db())
        close_session = True
    
    try:
        # Check if the customer already exists in the ai-agent backend
        ai_agent_customer = db_session.query(AIAgentCustomer).filter_by(email=admin_user.email).first()
        
        if ai_agent_customer is None:
            # Create a new customer in the ai-agent backend
            ai_agent_customer = AIAgentCustomer(
                name=admin_user.username,
                email=admin_user.email,
                created_at=admin_user.created_at
            )
            db_session.add(ai_agent_customer)
            db_session.commit()
        else:
            # Update the existing customer
            ai_agent_customer.name = admin_user.username
            ai_agent_customer.email = admin_user.email
            db_session.commit()
        
        return ai_agent_customer
    
    finally:
        if close_session:
            db_session.close()

# Function to sync all customers from admin-dashboard to ai-agent backend
def sync_all_customers_to_ai_agent():
    """Sync all users from admin-dashboard to ai-agent backend as customers"""
    if not AI_AGENT_BACKEND_AVAILABLE:
        return 0
    
    try:
        from models import User
        
        # Get all users
        users = User.query.all()
        synced_count = 0
        
        # Get a database session
        db_session = next(get_db())
        
        for user in users:
            ai_agent_customer = sync_customer_to_ai_agent(user, db_session)
            if ai_agent_customer:
                # Update user with ai-agent customer ID
                user.ai_agent_customer_id = ai_agent_customer.id
                synced_count += 1
        
        # Commit changes to admin-dashboard database
        from models import db
        db.session.commit()
        
        db_session.close()
        return synced_count
    
    except Exception as e:
        print(f"Error syncing all customers to ai-agent backend: {e}")
        return 0

# Function to sync all tickets from admin-dashboard to ai-agent backend
def sync_all_tickets_to_ai_agent():
    """Sync all tickets from admin-dashboard to ai-agent backend"""
    if not AI_AGENT_BACKEND_AVAILABLE:
        return 0
    
    try:
        from models import Ticket
        
        # Get all tickets
        tickets = Ticket.query.all()
        synced_count = 0
        
        # Get a database session
        db_session = next(get_db())
        
        for ticket in tickets:
            # Ensure customer is synced first
            if ticket.customer and not ticket.customer.ai_agent_customer_id:
                sync_customer_to_ai_agent(ticket.customer, db_session)
            
            # Sync ticket
            ai_agent_ticket = sync_ticket_to_ai_agent(ticket, db_session)
            if ai_agent_ticket:
                # Update ticket with ai-agent ticket ID
                ticket.ai_agent_ticket_id = ai_agent_ticket.id
                synced_count += 1
        
        # Commit changes to admin-dashboard database
        from models import db
        db.session.commit()
        
        db_session.close()
        return synced_count
    
    except Exception as e:
        print(f"Error syncing all tickets to ai-agent backend: {e}")
        return 0