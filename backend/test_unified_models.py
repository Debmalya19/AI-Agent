#!/usr/bin/env python3
"""
Test script for unified models.
Verifies that the unified models can be created and work correctly.
"""

import sys
import os
from datetime import datetime, timezone

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.database import engine, SessionLocal
from backend.unified_models import (
    Base,
    UnifiedUser,
    UnifiedTicket,
    UnifiedTicketComment,
    UnifiedTicketActivity,
    UserRole,
    TicketStatus,
    TicketPriority,
    TicketCategory,
)
from backend.data_validation import validate_model_instance

def test_create_tables():
    """Test creating unified tables"""
    print("Testing table creation...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def test_create_user():
    """Test creating a unified user"""
    print("Testing user creation...")
    try:
        session = SessionLocal()
        
        user = UnifiedUser(
            user_id="test_user_001",
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User",
            phone="+1234567890",
            is_admin=False,
            role=UserRole.CUSTOMER,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        # Validate the user
        validation_result = validate_model_instance(user)
        if not validation_result.is_valid:
            print(f"❌ User validation failed: {validation_result.errors}")
            return False
        
        session.add(user)
        session.commit()
        
        # Verify user was created
        retrieved_user = session.query(UnifiedUser).filter_by(username="testuser").first()
        if retrieved_user:
            print(f"✅ User created successfully: {retrieved_user.username} ({retrieved_user.email})")
            session.close()
            return True
        else:
            print("❌ User not found after creation")
            session.close()
            return False
            
    except Exception as e:
        print(f"❌ Failed to create user: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

def test_create_ticket():
    """Test creating a unified ticket"""
    print("Testing ticket creation...")
    try:
        session = SessionLocal()
        
        # Get the test user
        user = session.query(UnifiedUser).filter_by(username="testuser").first()
        if not user:
            print("❌ Test user not found")
            session.close()
            return False
        
        ticket = UnifiedTicket(
            title="Test Ticket",
            description="This is a test ticket for validation",
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            category=TicketCategory.TECHNICAL,
            customer_id=user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        # Validate the ticket
        validation_result = validate_model_instance(ticket)
        if not validation_result.is_valid:
            print(f"❌ Ticket validation failed: {validation_result.errors}")
            session.close()
            return False
        
        session.add(ticket)
        session.commit()
        
        # Verify ticket was created
        retrieved_ticket = session.query(UnifiedTicket).filter_by(title="Test Ticket").first()
        if retrieved_ticket:
            print(f"✅ Ticket created successfully: {retrieved_ticket.title} (ID: {retrieved_ticket.id})")
            session.close()
            return True
        else:
            print("❌ Ticket not found after creation")
            session.close()
            return False
            
    except Exception as e:
        print(f"❌ Failed to create ticket: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

def test_create_comment():
    """Test creating a unified comment"""
    print("Testing comment creation...")
    try:
        session = SessionLocal()
        
        # Get the test user and ticket
        user = session.query(UnifiedUser).filter_by(username="testuser").first()
        ticket = session.query(UnifiedTicket).filter_by(title="Test Ticket").first()
        
        if not user or not ticket:
            print("❌ Test user or ticket not found")
            session.close()
            return False
        
        comment = UnifiedTicketComment(
            ticket_id=ticket.id,
            author_id=user.id,
            comment="This is a test comment",
            content="This is a test comment",  # For admin dashboard compatibility
            is_internal=False,
            created_at=datetime.now(timezone.utc),
        )
        
        # Validate the comment
        validation_result = validate_model_instance(comment)
        if not validation_result.is_valid:
            print(f"❌ Comment validation failed: {validation_result.errors}")
            session.close()
            return False
        
        session.add(comment)
        session.commit()
        
        # Verify comment was created
        retrieved_comment = session.query(UnifiedTicketComment).filter_by(ticket_id=ticket.id).first()
        if retrieved_comment:
            print(f"✅ Comment created successfully: {retrieved_comment.comment[:50]}...")
            session.close()
            return True
        else:
            print("❌ Comment not found after creation")
            session.close()
            return False
            
    except Exception as e:
        print(f"❌ Failed to create comment: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

def test_create_activity():
    """Test creating a unified activity"""
    print("Testing activity creation...")
    try:
        session = SessionLocal()
        
        # Get the test user and ticket
        user = session.query(UnifiedUser).filter_by(username="testuser").first()
        ticket = session.query(UnifiedTicket).filter_by(title="Test Ticket").first()
        
        if not user or not ticket:
            print("❌ Test user or ticket not found")
            session.close()
            return False
        
        activity = UnifiedTicketActivity(
            ticket_id=ticket.id,
            activity_type="created",
            description="Ticket was created for testing",
            performed_by_id=user.id,
            created_at=datetime.now(timezone.utc),
        )
        
        # Validate the activity
        validation_result = validate_model_instance(activity)
        if not validation_result.is_valid:
            print(f"❌ Activity validation failed: {validation_result.errors}")
            session.close()
            return False
        
        session.add(activity)
        session.commit()
        
        # Verify activity was created
        retrieved_activity = session.query(UnifiedTicketActivity).filter_by(ticket_id=ticket.id).first()
        if retrieved_activity:
            print(f"✅ Activity created successfully: {retrieved_activity.activity_type}")
            session.close()
            return True
        else:
            print("❌ Activity not found after creation")
            session.close()
            return False
            
    except Exception as e:
        print(f"❌ Failed to create activity: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

def test_relationships():
    """Test model relationships"""
    print("Testing model relationships...")
    try:
        session = SessionLocal()
        
        # Get the test user and ticket
        user = session.query(UnifiedUser).filter_by(username="testuser").first()
        ticket = session.query(UnifiedTicket).filter_by(title="Test Ticket").first()
        
        if not user or not ticket:
            print("❌ Test user or ticket not found")
            session.close()
            return False
        
        # Test user -> tickets relationship
        user_tickets = user.created_tickets
        print(f"User has {len(user_tickets)} created tickets")
        
        # Test ticket -> customer relationship
        ticket_customer = ticket.customer
        if ticket_customer and ticket_customer.id == user.id:
            print("✅ Ticket -> customer relationship works")
        else:
            print("❌ Ticket -> customer relationship failed")
            session.close()
            return False
        
        # Test ticket -> comments relationship
        ticket_comments = ticket.comments
        print(f"Ticket has {len(ticket_comments)} comments")
        
        # Test ticket -> activities relationship
        ticket_activities = ticket.activities
        print(f"Ticket has {len(ticket_activities)} activities")
        
        session.close()
        print("✅ Relationships work correctly")
        return True
        
    except Exception as e:
        print(f"❌ Failed to test relationships: {e}")
        if 'session' in locals():
            session.close()
        return False

def cleanup_test_data():
    """Clean up test data"""
    print("Cleaning up test data...")
    try:
        session = SessionLocal()
        
        # Delete in reverse order of dependencies
        session.query(UnifiedTicketActivity).filter(
            UnifiedTicketActivity.ticket_id.in_(
                session.query(UnifiedTicket.id).filter_by(title="Test Ticket")
            )
        ).delete(synchronize_session=False)
        
        session.query(UnifiedTicketComment).filter(
            UnifiedTicketComment.ticket_id.in_(
                session.query(UnifiedTicket.id).filter_by(title="Test Ticket")
            )
        ).delete(synchronize_session=False)
        
        session.query(UnifiedTicket).filter_by(title="Test Ticket").delete()
        session.query(UnifiedUser).filter_by(username="testuser").delete()
        
        session.commit()
        session.close()
        print("✅ Test data cleaned up")
        return True
        
    except Exception as e:
        print(f"❌ Failed to clean up test data: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Unified Models")
    print("=" * 50)
    
    tests = [
        test_create_tables,
        test_create_user,
        test_create_ticket,
        test_create_comment,
        test_create_activity,
        test_relationships,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
        print()
    
    # Clean up
    cleanup_test_data()
    
    print("=" * 50)
    print(f"Tests completed: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())