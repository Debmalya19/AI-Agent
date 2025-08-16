"""
Initialize the ticking system - create tables and setup
"""

from database import engine, Base
from ticking_system import Ticket, TicketComment, TicketActivity
from models import Customer, Order, SupportIntent, SupportResponse, ChatHistory, KnowledgeEntry
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_ticking_system():
    """Initialize the ticking system by creating all necessary tables"""
    
    logger.info("Initializing ticking system...")
    
    # Import all models to ensure they're registered with Base
    from ticking_system import Ticket, TicketComment, TicketActivity
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    logger.info("Ticking system initialized successfully!")
    logger.info("Created tables: tickets, ticket_comments, ticket_activities")

def verify_tables():
    """Verify that all tables are created properly"""
    
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    logger.info(f"Available tables: {tables}")
    
    expected_tables = ['tickets', 'ticket_comments', 'ticket_activities', 
                      'customers', 'orders', 'knowledge_entries', 'chat_history',
                      'support_intents', 'support_responses']
    
    for table in expected_tables:
        if table in tables:
            logger.info(f"✓ {table} table exists")
        else:
            logger.warning(f"✗ {table} table missing")

if __name__ == "__main__":
    init_ticking_system()
    verify_tables()
