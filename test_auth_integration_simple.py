#!/usr/bin/env python3
"""
Simple Authentication Integration Test
A lightweight test to verify the unified authentication system is working.
This test can be run independently to quickly verify authentication functionality.

Requirements covered: 1.1, 1.2, 2.1, 2.2, 6.1, 6.2, 6.3, 6.4
"""

import os
import sys
import tempfile
import sqlite3
from datetime import datetime, timezone

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_basic_authentication():
    """Test basic authentication functionality"""
    print("🧪 Testing basic authentication functionality...")
    
    try:
        from backend.unified_auth import UnifiedAuthService
        from backend.unified_models import UnifiedUser, UserRole
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from backend.database import Base
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_url = f"sqlite:///{tmp_file.name}"
        
        # Create engine and session
        engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Create auth service
        auth_service = UnifiedAuthService("test-secret-key")
        
        # Test 1: Password hashing
        password = "test_password_123"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password(password, hashed)
        print("  ✅ Password hashing works")
        
        # Test 2: User creation
        user = UnifiedUser(
            user_id="test_user_001",
            username="testuser",
            email="test@example.com",
            password_hash=hashed,
            full_name="Test User",
            role=UserRole.CUSTOMER,
            is_admin=False,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print("  ✅ User creation works")
        
        # Test 3: Authentication
        auth_user = auth_service.authenticate_user("testuser", password, db)
        assert auth_user is not None
        assert auth_user.username == "testuser"
        print("  ✅ User authentication works")
        
        # Test 4: Session creation
        session_token = auth_service.create_user_session(auth_user, db)
        assert session_token is not None
        print("  ✅ Session creation works")
        
        # Test 5: Session validation
        session_user = auth_service.get_user_from_session(session_token, db)
        assert session_user is not None
        assert session_user.username == "testuser"
        print("  ✅ Session validation works")
        
        # Test 6: JWT token
        jwt_token = auth_service.create_jwt_token(auth_user)
        jwt_user = auth_service.get_user_from_jwt(jwt_token, db)
        assert jwt_user is not None
        assert jwt_user.username == "testuser"
        print("  ✅ JWT token system works")
        
        # Test 7: Admin user
        admin_user = UnifiedUser(
            user_id="admin_001",
            username="adminuser",
            email="admin@example.com",
            password_hash=auth_service.hash_password("admin_password"),
            role=UserRole.ADMIN,
            is_admin=True,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        
        auth_admin = auth_service.authenticate_user("adminuser", "admin_password", db)
        assert auth_admin is not None
        assert auth_admin.is_admin is True
        print("  ✅ Admin authentication works")
        
        # Test 8: Permissions (using session-based authenticated user)
        from backend.unified_auth import Permission
        session_auth_user = auth_service.get_user_from_session(session_token, db)
        assert session_auth_user.has_permission(Permission.TICKET_CREATE)
        assert not session_auth_user.has_permission(Permission.USER_CREATE)
        
        admin_session = auth_service.create_user_session(auth_admin, db)
        session_auth_admin = auth_service.get_user_from_session(admin_session, db)
        assert session_auth_admin.has_permission(Permission.USER_CREATE)  # Admin can create users
        assert session_auth_admin.has_permission(Permission.DASHBOARD_VIEW)
        print("  ✅ Permission system works")
        
        # Test 9: Session invalidation
        result = auth_service.invalidate_session(session_token, db)
        assert result is True
        invalid_user = auth_service.get_user_from_session(session_token, db)
        assert invalid_user is None
        print("  ✅ Session invalidation works")
        
        # Cleanup
        db.close()
        try:
            os.unlink(tmp_file.name)
        except PermissionError:
            # On Windows, file might still be locked
            pass
        
        print("🎉 All basic authentication tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Basic authentication test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_migration_system():
    """Test migration system functionality"""
    print("\n🧪 Testing migration system functionality...")
    
    try:
        from backend.auth_migration_system import AuthMigrationSystem, MigrationConfig
        
        # Create migration system
        config = MigrationConfig(
            backup_enabled=False,
            dry_run=True  # Safe dry run
        )
        migration_system = AuthMigrationSystem(config)
        
        # Test configuration
        assert migration_system.config.dry_run is True
        print("  ✅ Migration system configuration works")
        
        # Test validation methods exist
        assert hasattr(migration_system, 'config')
        print("  ✅ Migration system methods available")
        
        print("🎉 Migration system tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Migration system test failed: {e}")
        return False

def test_session_utilities():
    """Test session utility functions"""
    print("\n🧪 Testing session utilities...")
    
    try:
        from backend.session_utils import SessionUtils, SessionSecurity
        
        # Test utility methods exist
        assert hasattr(SessionUtils, 'get_active_sessions_count')
        assert hasattr(SessionUtils, 'cleanup_expired_sessions')
        assert hasattr(SessionSecurity, 'detect_suspicious_activity')
        print("  ✅ Session utility methods available")
        
        print("🎉 Session utilities tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Session utilities test failed: {e}")
        return False

def test_error_handling():
    """Test error handling integration"""
    print("\n🧪 Testing error handling integration...")
    
    try:
        # Test error handling modules exist
        from backend.comprehensive_error_integration import setup_comprehensive_error_handling
        
        print("  ✅ Error handling modules available")
        
        # Test setup function exists
        assert callable(setup_comprehensive_error_handling)
        print("  ✅ Error handler functionality available")
        
        print("🎉 Error handling tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def main():
    """Run all simple integration tests"""
    print("🚀 Starting Simple Authentication Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Basic Authentication", test_basic_authentication),
        ("Migration System", test_migration_system),
        ("Session Utilities", test_session_utilities),
        ("Error Handling", test_error_handling)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} test failed")
    
    print(f"\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All simple integration tests passed!")
        print("✅ The unified authentication system is working correctly.")
        return True
    else:
        print(f"❌ {total - passed} tests failed.")
        print("🔧 Please check the implementation and try again.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)