#!/usr/bin/env python3
"""
Test script to verify admin dashboard data loading
"""

import sys
sys.path.append('.')
from main import app
from fastapi.testclient import TestClient
from backend.database import SessionLocal
from backend.unified_models import UnifiedUser, UnifiedTicket, TicketStatus, TicketPriority, TicketCategory, UserRole
from backend.unified_auth import auth_service
import json

def create_test_data():
    """Create some test data in the database"""
    db = SessionLocal()
    try:
        # Create test admin user if not exists
        admin_user = db.query(UnifiedUser).filter(UnifiedUser.email == "admin@example.com").first()
        if not admin_user:
            admin_user = UnifiedUser(
                user_id="admin_test",
                username="admin",
                email="admin@example.com",
                password_hash=auth_service.hash_password("admin123"),
                full_name="Admin User",
                is_admin=True,
                is_active=True,
                role=UserRole.ADMIN
            )
            db.add(admin_user)
            db.commit()
            print("✅ Created test admin user")
        else:
            print("✅ Admin user already exists")

        # Create test customer user if not exists
        customer_user = db.query(UnifiedUser).filter(UnifiedUser.email == "customer@example.com").first()
        if not customer_user:
            customer_user = UnifiedUser(
                user_id="customer_test",
                username="customer",
                email="customer@example.com",
                password_hash=auth_service.hash_password("customer123"),
                full_name="Test Customer",
                is_admin=False,
                is_active=True,
                role=UserRole.CUSTOMER
            )
            db.add(customer_user)
            db.commit()
            print("✅ Created test customer user")
        else:
            print("✅ Customer user already exists")

        # Create test tickets if not exist
        ticket_count = db.query(UnifiedTicket).count()
        if ticket_count == 0:
            test_tickets = [
                UnifiedTicket(
                    title="Login Issue",
                    description="User cannot login to the system",
                    status=TicketStatus.OPEN,
                    priority=TicketPriority.HIGH,
                    category=TicketCategory.TECHNICAL,
                    customer_id=customer_user.id
                ),
                UnifiedTicket(
                    title="Billing Question",
                    description="Question about monthly charges",
                    status=TicketStatus.PENDING,
                    priority=TicketPriority.MEDIUM,
                    category=TicketCategory.BILLING,
                    customer_id=customer_user.id
                ),
                UnifiedTicket(
                    title="Feature Request",
                    description="Request for new dashboard feature",
                    status=TicketStatus.RESOLVED,
                    priority=TicketPriority.LOW,
                    category=TicketCategory.GENERAL,
                    customer_id=customer_user.id
                )
            ]
            
            for ticket in test_tickets:
                db.add(ticket)
            
            db.commit()
            print(f"✅ Created {len(test_tickets)} test tickets")
        else:
            print(f"✅ Database already has {ticket_count} tickets")

    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        db.rollback()
    finally:
        db.close()

def test_admin_login_and_data():
    """Test admin login and data loading"""
    client = TestClient(app)
    
    print("\n" + "="*50)
    print("TESTING ADMIN DASHBOARD DATA SYNC")
    print("="*50)
    
    # Create test data first
    create_test_data()
    
    print("\n1. Testing admin login...")
    
    # Test admin login
    login_response = client.post("/api/auth/login", json={
        "email": "admin@example.com",
        "password": "admin123"
    })
    
    print(f"   Login Status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"   Login failed: {login_response.text}")
        return
    
    login_data = login_response.json()
    print(f"   Login response keys: {list(login_data.keys())}")
    print(f"   Login cookies: {login_response.cookies}")
    
    token = login_data.get("token") or login_data.get("access_token")
    
    # Try to get token from cookies if not in response
    if not token:
        session_token = login_response.cookies.get("session_token")
        if session_token:
            token = session_token
            print(f"   ✅ Token found in cookies")
        else:
            print("   ❌ No token received from login (neither in response nor cookies)")
            return
    
    print(f"   ✅ Login successful, token received")
    
    # Test API endpoints with authentication
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n2. Testing ticket statistics endpoint...")
    stats_response = client.get("/api/tickets/stats", headers=headers)
    print(f"   /api/tickets/stats Status: {stats_response.status_code}")
    
    if stats_response.status_code == 200:
        stats_data = stats_response.json()
        print(f"   ✅ Ticket stats loaded: {json.dumps(stats_data, indent=2)}")
    else:
        print(f"   ❌ Failed to load ticket stats: {stats_response.text}")
    
    print("\n3. Testing tickets endpoint...")
    tickets_response = client.get("/api/tickets?limit=5", headers=headers)
    print(f"   /api/tickets Status: {tickets_response.status_code}")
    
    if tickets_response.status_code == 200:
        tickets_data = tickets_response.json()
        print(f"   ✅ Tickets loaded: {len(tickets_data.get('tickets', []))} tickets")
        if tickets_data.get('tickets'):
            print(f"   Sample ticket: {tickets_data['tickets'][0]['title']}")
    else:
        print(f"   ❌ Failed to load tickets: {tickets_response.text}")
    
    print("\n4. Testing users endpoint...")
    users_response = client.get("/api/admin/users", headers=headers)
    print(f"   /api/admin/users Status: {users_response.status_code}")
    
    if users_response.status_code == 200:
        users_data = users_response.json()
        print(f"   ✅ Users loaded: {len(users_data.get('users', []))} users")
        if users_data.get('users'):
            print(f"   Sample user: {users_data['users'][0]['username']}")
    else:
        print(f"   ❌ Failed to load users: {users_response.text}")
    
    print("\n5. Testing admin dashboard pages...")
    
    # Test dashboard page
    dashboard_response = client.get("/admin/")
    print(f"   /admin/ Status: {dashboard_response.status_code}")
    
    # Test tickets page
    tickets_page_response = client.get("/admin/tickets.html")
    print(f"   /admin/tickets.html Status: {tickets_page_response.status_code}")
    
    # Test users page
    users_page_response = client.get("/admin/users.html")
    print(f"   /admin/users.html Status: {users_page_response.status_code}")
    
    print("\n" + "="*50)
    print("TEST COMPLETED")
    print("="*50)

if __name__ == "__main__":
    test_admin_login_and_data()