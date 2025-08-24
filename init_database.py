"""
Initialize all database tables and required data
"""

from database import init_db, engine
from ticking_system import Ticket, TicketComment, TicketActivity
from models import Customer, Order, SupportIntent, SupportResponse, ChatHistory, KnowledgeEntry, User, UserSession

def main():
    # Drop existing tables (optional - be careful with this in production!)
    # Base.metadata.drop_all(bind=engine)
    
    # Create all tables
    init_db()
    
    print("All database tables have been initialized!")

if __name__ == "__main__":
    main()
