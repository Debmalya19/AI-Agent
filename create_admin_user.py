#!/usr/bin/env python3
"""
Create admin user for testing the admin dashboard
"""

import sys
import os
import secrets
from datetime import datetime, timezone

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal, engine
from backend.unified_models import UnifiedUser, UserRole, Base
from backend.unified_auth import auth_service

def create_admin_user():
    """Create an admin user for testing"""
    print("🔧 Creating Admin User")
    print("=" * 50)
    
    # Create tables if they don't exist
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables ensured")
    except Exception as e:
        print(f"⚠️  Database table creation warning: {e}")
    
    db = SessionLocal()
    try:
        # Check if admin user already exists
        existing_admin = db.query(UnifiedUser).filter(
            (UnifiedUser.email == "admin@test.com") |
            (UnifiedUser.username == "admin")
        ).first()
        
        if existing_admin:
            print(f"👤 Admin user already exists:")
            print(f"   📧 Email: {existing_admin.email}")
            print(f"   👤 Username: {existing_admin.username}")
            print(f"   🔑 User ID: {existing_admin.user_id}")
            print(f"   🛡️  Is Admin: {existing_admin.is_admin}")
            print(f"   ✅ Is Active: {existing_admin.is_active}")
            
            # Update password to ensure it's correct
            existing_admin.password_hash = auth_service.hash_password("admin123")
            existing_admin.is_admin = True
            existing_admin.is_active = True
            existing_admin.role = UserRole.ADMIN
            db.commit()
            print("🔄 Updated admin user password and permissions")
            return existing_admin
        
        # Create new admin user
        user_id = f"admin_{secrets.token_hex(8)}"
        
        admin_user = UnifiedUser(
            user_id=user_id,
            username="admin",
            email="admin@test.com",
            password_hash=auth_service.hash_password("admin123"),
            full_name="System Administrator",
            role=UserRole.ADMIN,
            is_admin=True,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully!")
        print(f"   📧 Email: {admin_user.email}")
        print(f"   👤 Username: {admin_user.username}")
        print(f"   🔑 User ID: {admin_user.user_id}")
        print(f"   🔒 Password: admin123")
        print(f"   🛡️  Role: {admin_user.role.value}")
        
        return admin_user
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def create_test_users():
    """Create additional test users"""
    print("\n👥 Creating Test Users")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        test_users = [
            {
                "username": "customer1",
                "email": "customer1@test.com",
                "full_name": "Test Customer 1",
                "role": UserRole.CUSTOMER,
                "is_admin": False
            },
            {
                "username": "agent1",
                "email": "agent1@test.com",
                "full_name": "Test Agent 1",
                "role": UserRole.AGENT,
                "is_admin": False
            }
        ]
        
        created_count = 0
        for user_data in test_users:
            # Check if user exists
            existing = db.query(UnifiedUser).filter(
                (UnifiedUser.email == user_data["email"]) |
                (UnifiedUser.username == user_data["username"])
            ).first()
            
            if not existing:
                user_id = f"{user_data['role'].value}_{secrets.token_hex(8)}"
                
                new_user = UnifiedUser(
                    user_id=user_id,
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=auth_service.hash_password("test123"),
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    is_admin=user_data["is_admin"],
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                
                db.add(new_user)
                created_count += 1
                print(f"   ✅ Created {user_data['username']} ({user_data['role'].value})")
        
        if created_count > 0:
            db.commit()
            print(f"\n✅ Created {created_count} test users")
        else:
            print("ℹ️  All test users already exist")
            
    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        db.rollback()
    finally:
        db.close()

def verify_database():
    """Verify database setup"""
    print("\n🔍 Verifying Database Setup")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        # Count users by role
        total_users = db.query(UnifiedUser).count()
        admin_users = db.query(UnifiedUser).filter(UnifiedUser.is_admin == True).count()
        active_users = db.query(UnifiedUser).filter(UnifiedUser.is_active == True).count()
        
        print(f"📊 Database Statistics:")
        print(f"   👥 Total users: {total_users}")
        print(f"   🛡️  Admin users: {admin_users}")
        print(f"   ✅ Active users: {active_users}")
        
        # List admin users
        admins = db.query(UnifiedUser).filter(UnifiedUser.is_admin == True).all()
        if admins:
            print(f"\n🛡️  Admin Users:")
            for admin in admins:
                print(f"   • {admin.username} ({admin.email}) - {admin.user_id}")
        
        return total_users > 0
        
    except Exception as e:
        print(f"❌ Database verification error: {e}")
        return False
    finally:
        db.close()

def main():
    """Main function"""
    print("🚀 Admin User Setup Script")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Create admin user
    admin_user = create_admin_user()
    
    if admin_user:
        # Create test users
        create_test_users()
        
        # Verify setup
        if verify_database():
            print("\n🎉 Setup completed successfully!")
            print("\nYou can now test the admin dashboard with:")
            print("   📧 Email: admin@test.com")
            print("   🔒 Password: admin123")
            print("\nRun the test script:")
            print("   python test_admin_login_fix.py")
        else:
            print("\n❌ Setup verification failed")
    else:
        print("\n❌ Admin user creation failed")
    
    print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()