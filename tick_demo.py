"""
Demo script for the ticking system
"""

from init_ticking_system import init_ticking_system
from ticking_service import TickingService, TicketContextRetriever, TicketStatus, TicketPriority, TicketCategory
from models import Customer
from database import get_db_session
import random

def create_demo_data():
    """Create demo data for testing the ticking system"""
    
    session = next(get_db_session())
    
    # Create demo customers if they don't exist
    customers = session.query(Customer).all()
    if not customers:
        # Create some demo customers
        demo_customers = [
            Customer(customer_id=1001, name="John Doe", email="john@example.com", phone="123-456-7890"),
            Customer(customer_id=1002, name="Jane Smith", email="jane@example.com", phone="987-654-3210"),
            Customer(customer_id=1003, name="Bob Johnson", email="bob@example.com", phone="555-123-4567")
        ]
        
        for customer in demo_customers:
            session.add(customer)
        session.commit()
        customers = demo_customers
    
    session.close()
    
    # Create ticking service
    ticking_service = TickingService()
    context_retriever = TicketContextRetriever()
    
    # Create demo tickets
    demo_tickets = [
        {
            "title": "Login Issue - Cannot access account",
            "description": "Customer reports unable to login with correct credentials",
            "customer_id": customers[0].id,
            "priority": TicketPriority.HIGH,
            "category": TicketCategory.TECHNICAL,
            "tags": ["login", "authentication", "urgent"]
        },
        {
            "title": "Billing Question - Invoice #12345",
            "description": "Customer asking about charges on their latest invoice",
            "customer_id": customers[1].id,
            "priority": TicketPriority.MEDIUM,
            "category": TicketCategory.BILLING,
            "tags": ["billing", "invoice", "charges"]
        },
        {
            "title": "Feature Request - Dark Mode",
            "description": "Customer requesting dark mode feature for the application",
            "customer_id": customers[2].id,
            "priority": TicketPriority.LOW,
            "category": TicketCategory.FEATURE_REQUEST,
            "tags": ["feature", "ui", "dark-mode"]
        }
    ]
    
    created_tickets = []
    for ticket_data in demo_tickets:
        ticket = ticking_service.create_ticket(**ticket_data)
        created_tickets.append(ticket)
        print(f"Created ticket: {ticket.title} (ID: {ticket.id})")
    
    # Update some ticket statuses
    ticking_service.update_ticket_status(created_tickets[0].id, TicketStatus.IN_PROGRESS)
    ticking_service.assign_ticket(created_tickets[0].id, customers[1].id)
    
    # Add comments
    ticking_service.add_comment(
        created_tickets[0].id, 
        "Looking into the login issue. Checking server logs.", 
        author_id=customers[1].id
    )
    
    return created_tickets

def demo_context_retrieval():
    """Demonstrate context retrieval capabilities"""
    
    context_retriever = TicketContextRetriever()
    
    # Get customer context
    session = next(get_db_session())
    customer = session.query(Customer).first()
    
    if customer:
        context = context_retriever.get_customer_context(customer.id)
        print("\nCustomer Context:")
        print(f"Customer: {context.get('customer_info', {}).get('name', 'Unknown')}")
        print(f"Total Orders: {context.get('customer_info', {}).get('total_orders', 0)}")
        
        # Get similar tickets
        similar_tickets = context_retriever.get_similar_tickets("login issue")
        print(f"\nFound {len(similar_tickets)} similar tickets")
        
        # Get ticket history
        history = context_retriever.get_ticket_history(customer.id)
        print(f"Customer has {len(history)} tickets in history")

def main():
    """Run the demo"""
    print("🎫 Ticking System Demo")
    print("=" * 50)
    
    # Initialize the system
    print("1. Initializing ticking system...")
    init_ticking_system()
    
    # Create demo data
    print("\n2. Creating demo data...")
    tickets = create_demo_data()
    
    # Demonstrate context retrieval
    print("\n3. Demonstrating context retrieval...")
    demo_context_retrieval()
    
    # Show statistics
    print("\n4. Ticket Statistics:")
    ticking_service = TickingService()
    stats = ticking_service.get_ticket_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Demo completed successfully!")

if __name__ == "__main__":
    main()
