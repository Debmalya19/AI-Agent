#!/usr/bin/env python3
"""
Direct test of admin authentication without server
"""

import sys
import os
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal
from backend.unified_auth import auth_service

def test_admin_authentication():
    """Test admin authentication directly"""
    print("🧪 Direct Admin Authentication Test")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        # Test credentials that were failing
        test_cases = [
            ("admin@example.com", "admin123"),
            ("admin", "admin123"),
        ]
        
        for email, password in test_cases:
            print(f"\n🔍 Testing login: {email}")
            
            user = auth_service.authenticate_user(email, password, db)
            
            if user:
                print(f"✅ Authentication successful!")
                print(f"   📧 Email: {user.email}")
                print(f"   👤 Username: {user.username}")
                print(f"   🔑 User ID: {user.user_id}")
                print(f"   🛡️  Is Admin: {user.is_admin}")
                print(f"   ✅ Is Active: {user.is_active}")
                print(f"   🎭 Role: {user.role.value}")
                
                # Test password verification directly
                print(f"   🔐 Password hash verification: {auth_service.verify_password(password, user.password_hash)}")
                
            else:
                print(f"❌ Authentication failed for {email}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False
    finally:
        db.close()

def main():
    """Main function"""
    print("🚀 Admin Authentication Direct Test")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = test_admin_authentication()
    
    if success:
        print("\n🎉 Direct authentication test completed!")
    else:
        print("\n❌ Direct authentication test failed!")
    
    print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()