"""
Simple integration test for unified authentication system.
Tests basic functionality without complex test setup.
"""

import os
import sys
import tempfile
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path so we can import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.unified_auth import UnifiedAuthService, UserRole, Permission, ROLE_PERMISSIONS
from backend.unified_models import Base, UnifiedUser, UnifiedUserSession
from backend.session_utils import SessionUtils

def test_basic_auth_functionality():
    """Test basic authentication functionality"""
    print("Testing basic authentication functionality...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_url = f"sqlite:///{tmp_file.name}"
    
    # Create engine and session
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Create auth service
        auth_service = UnifiedAuthService(
            jwt_secret="test-secret-key",
            jwt_algorithm="HS256",
            token_expire_hours=1
        )
        
        print("✓ Auth service created")
        
        # Test password hashing
        password = "test_password_123"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password(password, hashed)
        assert not auth_service.verify_password("wrong_password", hashed)
        print("✓ Password hashing works")
        
        # Create test user
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
        print("✓ Test user created")
        
        # Test authentication
        auth_user = auth_service.authenticate_user("testuser", password, db)
        assert auth_user is not None
        assert auth_user.username == "testuser"
        print("✓ User authentication works")
        
        # Test session creation
        session_token = auth_service.create_user_session(auth_user, db)
        assert session_token is not None
        print("✓ Session creation works")
        
        # Test session validation
        validated_user = auth_service.get_user_from_session(session_token, db)
        assert validated_user is not None
        assert validated_user.username == "testuser"
        assert validated_user.role == UserRole.CUSTOMER
        print("✓ Session validation works")
        
        # Test permissions
        customer_perms = ROLE_PERMISSIONS[UserRole.CUSTOMER]
        assert Permission.TICKET_CREATE in customer_perms
        assert Permission.USER_DELETE not in customer_perms
        assert validated_user.has_permission(Permission.TICKET_CREATE)
        assert not validated_user.has_permission(Permission.USER_DELETE)
        print("✓ Permission system works")
        
        # Test JWT token
        jwt_token = auth_service.create_jwt_token(auth_user)
        assert jwt_token is not None
        jwt_user = auth_service.get_user_from_jwt(jwt_token, db)
        assert jwt_user is not None
        assert jwt_user.username == "testuser"
        print("✓ JWT token system works")
        
        # Test session utilities
        session_count = SessionUtils.get_active_sessions_count(user.id, db)
        assert session_count == 1
        print("✓ Session utilities work")
        
        # Test session invalidation
        result = auth_service.invalidate_session(session_token, db)
        assert result is True
        invalid_user = auth_service.get_user_from_session(session_token, db)
        assert invalid_user is None
        print("✓ Session invalidation works")
        
        print("\n🎉 All basic authentication tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()
        # Clean up temporary database
        try:
            os.unlink(tmp_file.name)
        except:
            pass

def test_role_permissions():
    """Test role-based permission system"""
    print("\nTesting role-based permission system...")
    
    try:
        # Test all roles have expected permissions
        for role, permissions in ROLE_PERMISSIONS.items():
            print(f"✓ {role.value}: {len(permissions)} permissions")
        
        # Test super admin has all permissions
        super_admin_perms = ROLE_PERMISSIONS[UserRole.SUPER_ADMIN]
        all_perms = set(Permission)
        assert super_admin_perms == all_perms
        print("✓ Super admin has all permissions")
        
        # Test permission hierarchy
        customer_perms = ROLE_PERMISSIONS[UserRole.CUSTOMER]
        agent_perms = ROLE_PERMISSIONS[UserRole.AGENT]
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        
        # Agents should have more permissions than customers
        assert len(agent_perms) > len(customer_perms)
        # Admins should have more permissions than agents
        assert len(admin_perms) > len(agent_perms)
        print("✓ Permission hierarchy is correct")
        
        print("🎉 Role permission tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Role permission test failed: {e}")
        return False

def test_admin_user_workflow():
    """Test admin user workflow"""
    print("\nTesting admin user workflow...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_url = f"sqlite:///{tmp_file.name}"
    
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        auth_service = UnifiedAuthService("test-secret")
        
        # Create admin user
        admin_user = UnifiedUser(
            user_id="admin_user_001",
            username="adminuser",
            email="admin@example.com",
            password_hash=auth_service.hash_password("admin_password"),
            full_name="Admin User",
            role=UserRole.ADMIN,
            is_admin=True,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        # Create session for admin
        session_token = auth_service.create_user_session(admin_user, db)
        auth_admin = auth_service.get_user_from_session(session_token, db)
        
        # Test admin permissions
        assert auth_admin.is_admin
        assert auth_admin.role == UserRole.ADMIN
        assert auth_admin.has_permission(Permission.USER_CREATE)
        assert auth_admin.has_permission(Permission.DASHBOARD_VIEW)
        assert auth_admin.has_permission(Permission.TICKET_ASSIGN)
        print("✓ Admin user has correct permissions")
        
        # Test admin can manage users (permission-wise)
        assert auth_admin.has_permission(Permission.USER_UPDATE)
        assert auth_admin.has_permission(Permission.USER_LIST)
        print("✓ Admin can manage users")
        
        print("🎉 Admin workflow tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Admin workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()
        try:
            os.unlink(tmp_file.name)
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting unified authentication integration tests...\n")
    
    success = True
    success &= test_basic_auth_functionality()
    success &= test_role_permissions()
    success &= test_admin_user_workflow()
    
    if success:
        print("\n🎉 All integration tests passed! The unified authentication system is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)