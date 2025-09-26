#!/usr/bin/env python3
"""
Create sample data for testing the admin dashboard
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal
from backend.unified_models import UnifiedUser, UnifiedTicket, TicketStatus, TicketPriority, TicketCategory, UserRole
from datetime import datetime, timezone
import hashlib

def create_sample_data():
    db = SessionLocal()
    
    try:
        # Create sample users if they don't exist
        existing_users = db.query(UnifiedUser).count()
        if existing_users < 5:
            print("Creating sample users...")
            
            # Create regular users
            for i in range(1, 4):
                user = UnifiedUser(
                    user_id=f"user_{i}",
                    username=f"user{i}",
                    email=f"user{i}@example.com",
                    password_hash=hashlib.sha256(f"password{i}".encode()).hexdigest(),
                    full_name=f"User {i}",
                    phone=f"555-000{i}",
                    is_admin=False,
                    is_active=True,
                    role=UserRole.CUSTOMER,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(user)
            
            # Create admin user
            admin_user = UnifiedUser(
                user_id="admin_1",
                username="admin",
                email="admin@example.com",
                password_hash=hashlib.sha256("admin123".encode()).hexdigest(),
                full_name="Admin User",
                phone="555-0000",
                is_admin=True,
                is_active=True,
                role=UserRole.ADMIN,
                created_at=datetime.now(timezone.utc)
            )
            db.add(admin_user)
            
            db.commit()
            print("Sample users created!")
        
        # Create sample tickets if they don't exist
        existing_tickets = db.query(UnifiedTicket).count()
        if existing_tickets < 10:
            print("Creating sample tickets...")
            
            # Get user IDs for tickets
            users = db.query(UnifiedUser).filter(UnifiedUser.is_admin == False).all()
            
            sample_tickets = [
                {
                    "title": "Login Issues",
                    "description": "Unable to login to the system. Getting authentication errors.",
                    "status": TicketStatus.OPEN,
                    "priority": TicketPriority.HIGH,
                    "category": TicketCategory.TECHNICAL
                },
                {
                    "title": "Billing Question",
                    "description": "Need clarification on the latest invoice charges.",
                    "status": TicketStatus.PENDING,
                    "priority": TicketPriority.MEDIUM,
                    "category": TicketCategory.BILLING
                },
                {
                    "title": "Feature Request: Dark Mode",
                    "description": "Would like to request a dark mode theme for the application.",
                    "status": TicketStatus.OPEN,
                    "priority": TicketPriority.LOW,
                    "category": TicketCategory.FEATURE_REQUEST
                },
                {
                    "title": "Password Reset Not Working",
                    "description": "The password reset email is not being received.",
                    "status": TicketStatus.RESOLVED,
                    "priority": TicketPriority.MEDIUM,
                    "category": TicketCategory.TECHNICAL
                },
                {
                    "title": "Account Suspension",
                    "description": "My account has been suspended without notice. Need immediate assistance.",
                    "status": TicketStatus.OPEN,
                    "priority": TicketPriority.CRITICAL,
                    "category": TicketCategory.ACCOUNT
                },
                {
                    "title": "Data Export Request",
                    "description": "Need to export all my data for compliance purposes.",
                    "status": TicketStatus.PENDING,
                    "priority": TicketPriority.MEDIUM,
                    "category": TicketCategory.GENERAL
                },
                {
                    "title": "Mobile App Crashes",
                    "description": "The mobile application keeps crashing on startup.",
                    "status": TicketStatus.OPEN,
                    "priority": TicketPriority.HIGH,
                    "category": TicketCategory.TECHNICAL
                },
                {
                    "title": "Refund Request",
                    "description": "Requesting a refund for the premium subscription.",
                    "status": TicketStatus.CLOSED,
                    "priority": TicketPriority.MEDIUM,
                    "category": TicketCategory.BILLING
                }
            ]
            
            for i, ticket_data in enumerate(sample_tickets):
                customer = users[i % len(users)] if users else None
                
                ticket = UnifiedTicket(
                    title=ticket_data["title"],
                    description=ticket_data["description"],
                    status=ticket_data["status"],
                    priority=ticket_data["priority"],
                    category=ticket_data["category"],
                    customer_id=customer.id if customer else None,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(ticket)
            
            db.commit()
            print("Sample tickets created!")
        
        print("Sample data creation completed!")
        
        # Print summary
        user_count = db.query(UnifiedUser).count()
        ticket_count = db.query(UnifiedTicket).count()
        print(f"Total users: {user_count}")
        print(f"Total tickets: {ticket_count}")
        
    except Exception as e:
        print(f"Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_data()