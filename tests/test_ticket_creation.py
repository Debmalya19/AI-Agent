"""
Test ticket creation
"""
from ticking_service import TickingService, TicketPriority, TicketCategory
from database import get_db

def test_create_ticket():
    # Get a database session
    db = next(get_db())
    
    # Create a ticket service instance
    service = TickingService(db)
    
    # Create a test ticket
    test_ticket = service.create_ticket(
        title="Test Ticket",
        description="This is a test ticket to verify the ticketing system",
        priority=TicketPriority.HIGH,
        category=TicketCategory.TECHNICAL,
        tags=["test", "verification"]
    )
    
    # Verify the ticket was created
    if test_ticket and test_ticket.id:
        print(f"✅ Test ticket created successfully with ID: {test_ticket.id}")
        print(f"Title: {test_ticket.title}")
        print(f"Status: {test_ticket.status}")
        print(f"Priority: {test_ticket.priority}")
        print(f"Category: {test_ticket.category}")
        print(f"Tags: {test_ticket.tags}")
    else:
        print("❌ Failed to create test ticket")
    
    db.close()

if __name__ == "__main__":
    test_create_ticket()
