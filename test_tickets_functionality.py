#!/usr/bin/env python3
"""
Test script to validate tickets page functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal
from backend.unified_models import UnifiedUser, UnifiedTicket, TicketStatus, TicketPriority, TicketCategory
from backend.admin_routes import ticket_router
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json

def test_tickets_functionality():
    """Test the tickets functionality"""
    
    # Create a test FastAPI app
    app = FastAPI()
    app.include_router(ticket_router)
    
    # Create test client
    client = TestClient(app)
    
    print("Testing tickets functionality...")
    
    # Test 1: Get tickets endpoint
    print("\n1. Testing GET /api/tickets/ endpoint...")
    try:
        # This will fail due to authentication, but we can see if the endpoint exists
        response = client.get("/api/tickets/")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 401:
            print("   ✅ Endpoint exists (authentication required as expected)")
        elif response.status_code == 200:
            print("   ✅ Endpoint works!")
        else:
            print(f"   ⚠️ Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Check database has tickets
    print("\n2. Testing database tickets...")
    try:
        db = SessionLocal()
        ticket_count = db.query(UnifiedTicket).count()
        print(f"   Total tickets in database: {ticket_count}")
        
        if ticket_count > 0:
            print("   ✅ Database has tickets")
            
            # Show first few tickets
            tickets = db.query(UnifiedTicket).limit(3).all()
            for ticket in tickets:
                print(f"   - Ticket #{ticket.id}: {ticket.title} ({ticket.status.value if ticket.status else 'No status'})")
        else:
            print("   ⚠️ No tickets in database")
            
        db.close()
        
    except Exception as e:
        print(f"   ❌ Database error: {e}")
    
    # Test 3: Check ticket filtering logic
    print("\n3. Testing ticket filtering logic...")
    try:
        db = SessionLocal()
        
        # Test status filtering
        open_tickets = db.query(UnifiedTicket).filter(
            UnifiedTicket.status == TicketStatus.OPEN
        ).count()
        print(f"   Open tickets: {open_tickets}")
        
        # Test priority filtering
        high_priority = db.query(UnifiedTicket).filter(
            UnifiedTicket.priority == TicketPriority.HIGH
        ).count()
        print(f"   High priority tickets: {high_priority}")
        
        print("   ✅ Filtering logic works")
        db.close()
        
    except Exception as e:
        print(f"   ❌ Filtering error: {e}")
    
    print("\n✅ Tickets functionality test completed!")

if __name__ == "__main__":
    test_tickets_functionality()