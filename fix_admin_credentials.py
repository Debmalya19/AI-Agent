#!/usr/bin/env python3
"""
Fix admin credentials to match expected login attempts
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

def fix_admin_credentials():
    """Create or update admin user with expected credentials"""
    print("🔧 Fixing Admin Credentials")
    print("=" * 50)
    
    # Create tables if they don't exist
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables ensured")
    except Exception as e:
        print(f"⚠️  Database table creation warning: {e}")
    
    db = SessionLocal()
    try:
        # First, check if admin user with admin@example.com exists
        existing_admin = db.query(UnifiedUser).filter(
            UnifiedUser.email == "admin@example.com"
        ).first()
        
        if existing_admin:
            print(f"👤 Admin user with admin@example.com already exists:")
            print(f"   📧 Email: {existing_admin.email}")
            print(f"   👤 Username: {existing_admin.username}")
            print(f"   🔑 User ID: {existing_admin.user_id}")
            
            # Update password to ensure it's correct
            existing_admin.password_hash = auth_service.hash_password("admin123")
            existing_admin.is_admin = True
            existing_admin.is_active = True
            existing_admin.role = UserRole.ADMIN
            db.commit()
            print("🔄 Updated admin user password and permissions")
            return existing_admin
        
        # Check if there's an existing admin user with different email
        existing_admin_by_username = db.query(UnifiedUser).filter(
            UnifiedUser.username == "admin"
        ).first()
        
        if existing_admin_by_username:
            print(f"👤 Found existing admin user with username 'admin':")
            print(f"   📧 Current Email: {existing_admin_by_username.email}")
            print(f"   👤 Username: {existing_admin_by_username.username}")
            print(f"   🔑 User ID: {existing_admin_by_username.user_id}")
            
            # Update email and password
            existing_admin_by_username.email = "admin@example.com"
            existing_admin_by_username.password_hash = auth_service.hash_password("admin123")
            existing_admin_by_username.is_admin = True
            existing_admin_by_username.is_active = True
            existing_admin_by_username.role = UserRole.ADMIN
            existing_admin_by_username.updated_at = datetime.now(timezone.utc)
            db.commit()
            
            print("🔄 Updated existing admin user:")
            print(f"   📧 New Email: {existing_admin_by_username.email}")
            print(f"   🔒 Password: admin123")
            print(f"   🛡️  Role: {existing_admin_by_username.role.value}")
            
            return existing_admin_by_username
        
        # Create new admin user with admin@example.com
        user_id = f"admin_{secrets.token_hex(8)}"
        
        admin_user = UnifiedUser(
            user_id=user_id,
            username="admin",
            email="admin@example.com",
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
        print(f"❌ Error fixing admin credentials: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def verify_admin_login():
    """Test admin login with the fixed credentials"""
    print("\n🔍 Verifying Admin Login")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        # Test authentication
        user = auth_service.authenticate_user("admin@example.com", "admin123", db)
        
        if user:
            print("✅ Admin login verification successful!")
            print(f"   📧 Email: {user.email}")
            print(f"   👤 Username: {user.username}")
            print(f"   🔑 User ID: {user.user_id}")
            print(f"   🛡️  Is Admin: {user.is_admin}")
            print(f"   ✅ Is Active: {user.is_active}")
            return True
        else:
            print("❌ Admin login verification failed!")
            return False
            
    except Exception as e:
        print(f"❌ Login verification error: {e}")
        return False
    finally:
        db.close()

def main():
    """Main function"""
    print("🚀 Admin Credentials Fix Script")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Fix admin credentials
    admin_user = fix_admin_credentials()
    
    if admin_user:
        # Verify login works
        if verify_admin_login():
            print("\n🎉 Admin credentials fixed successfully!")
            print("\nYou can now login with:")
            print("   📧 Email: admin@example.com")
            print("   🔒 Password: admin123")
        else:
            print("\n❌ Admin login verification failed")
    else:
        print("\n❌ Admin credentials fix failed")
    
    print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()