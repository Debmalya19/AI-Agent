#!/usr/bin/env python3
"""
Test script for Admin User Verification and Credential Management Tools

This script tests all functionality of the admin user verification system
to ensure it meets the requirements.
"""

import sys
import os
import pytest
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import SessionLocal
from backend.unified_models import UnifiedUser, UnifiedUserSession, UserRole
from backend.unified_auth import auth_service
from admin_user_verification import AdminUserManager

class TestAdminUserVerification:
    """Test suite for admin user verification functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.db = SessionLocal()
        self.manager = AdminUserManager()
        
        # Clean up any existing test data
        self.cleanup_test_data()
    
    def teardown_method(self):
        """Cleanup after tests"""
        self.cleanup_test_data()
        self.db.close()
        self.manager.db.close()
    
    def cleanup_test_data(self):
        """Remove test data from database"""
        try:
            # Remove test users
            test_users = self.db.query(UnifiedUser).filter(
                UnifiedUser.username.like('test_%')
            ).all()
            
            for user in test_users:
                # Remove sessions first
                self.db.query(UnifiedUserSession).filter(
                    UnifiedUserSession.user_id == user.id
                ).delete()
                
                # Remove user
                self.db.delete(user)
            
            self.db.commit()
        except Exception as e:
            print(f"Cleanup error: {e}")
            self.db.rollback()
    
    def create_test_user(self, username: str, is_admin: bool = False, 
                        role: UserRole = UserRole.CUSTOMER, is_active: bool = True) -> UnifiedUser:
        """Create a test user"""
        user = UnifiedUser(
            user_id=f"test_{username}",
            username=username,
            email=f"{username}@test.com",
            password_hash=auth_service.hash_password("testpassword123"),
            full_name=f"Test {username}",
            role=role,
            is_admin=is_admin,
            is_active=is_active,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def test_verify_admin_users_empty_database(self):
        """Test admin user verification with empty database"""
        results = self.manager.verify_admin_users()
        
        assert results['total_users'] >= 0
        assert results['admin_users'] >= 0
        assert 'admin_users_details' in results
        assert 'issues_found' in results
        assert 'recommendations' in results
    
    def test_verify_admin_users_with_admin(self):
        """Test admin user verification with admin users"""
        # Create test admin user
        admin_user = self.create_test_user(
            "test_admin", is_admin=True, role=UserRole.ADMIN
        )
        
        results = self.manager.verify_admin_users()
        
        assert results['admin_users'] >= 1
        assert results['active_admin_users'] >= 1
        
        # Check admin user details
        admin_details = [
            user for user in results['admin_users_details'] 
            if user['username'] == 'test_admin'
        ]
        assert len(admin_details) == 1
        assert admin_details[0]['is_admin'] == True
        assert admin_details[0]['role'] == 'admin'
        assert admin_details[0]['password_hash_valid'] == True
    
    def test_verify_admin_users_with_inactive_admin(self):
        """Test admin user verification with inactive admin"""
        # Create inactive admin user
        inactive_admin = self.create_test_user(
            "test_inactive_admin", is_admin=True, role=UserRole.ADMIN, is_active=False
        )
        
        results = self.manager.verify_admin_users()
        
        assert results['inactive_admin_users'] >= 1
        
        # Should have issue about inactive admin
        inactive_issues = [
            issue for issue in results['issues_found']
            if 'test_inactive_admin' in issue and 'inactive' in issue
        ]
        assert len(inactive_issues) >= 1
    
    def test_validate_password_hash_valid_user(self):
        """Test password hash validation for valid user"""
        # Create test user
        test_user = self.create_test_user("test_validate_user")
        
        result = self.manager.validate_password_hash("test_validate_user", "testpassword123")
        
        assert result['user_found'] == True
        assert result['password_valid'] == True
        assert result['hash_format_valid'] == True
        assert result['error'] is None
    
    def test_validate_password_hash_invalid_password(self):
        """Test password hash validation with invalid password"""
        # Create test user
        test_user = self.create_test_user("test_validate_invalid")
        
        result = self.manager.validate_password_hash("test_validate_invalid", "wrongpassword")
        
        assert result['user_found'] == True
        assert result['password_valid'] == False
        assert result['hash_format_valid'] == True
        assert result['error'] is None
    
    def test_validate_password_hash_user_not_found(self):
        """Test password hash validation for non-existent user"""
        result = self.manager.validate_password_hash("nonexistent_user", "password")
        
        assert result['user_found'] == False
        assert result['password_valid'] == False
        assert result['error'] == "User not found"
    
    def test_reset_user_password_success(self):
        """Test successful password reset"""
        # Create test user
        test_user = self.create_test_user("test_reset_user")
        original_hash = test_user.password_hash
        
        result = self.manager.reset_user_password("test_reset_user", "newpassword123")
        
        assert result['success'] == True
        assert result['user_found'] == True
        assert result['error'] is None
        
        # Verify password was actually changed
        self.db.refresh(test_user)
        assert test_user.password_hash != original_hash
        
        # Verify new password works
        assert auth_service.verify_password("newpassword123", test_user.password_hash)
    
    def test_reset_user_password_short_password(self):
        """Test password reset with too short password"""
        # Create test user
        test_user = self.create_test_user("test_reset_short")
        
        result = self.manager.reset_user_password("test_reset_short", "short")
        
        assert result['success'] == False
        assert result['user_found'] == True
        assert "at least 8 characters" in result['error']
    
    def test_reset_user_password_user_not_found(self):
        """Test password reset for non-existent user"""
        result = self.manager.reset_user_password("nonexistent_user", "newpassword123")
        
        assert result['success'] == False
        assert result['user_found'] == False
        assert result['error'] == "User not found"
    
    def test_create_admin_user_success(self):
        """Test successful admin user creation"""
        result = self.manager.create_admin_user(
            "test_new_admin", "newadmin@test.com", "adminpassword123", 
            "New Admin User", "admin"
        )
        
        assert result['success'] == True
        assert result['user_created'] == True
        assert result['error'] is None
        assert result['user_id'] is not None
        
        # Verify user was created in database
        created_user = self.db.query(UnifiedUser).filter(
            UnifiedUser.username == "test_new_admin"
        ).first()
        
        assert created_user is not None
        assert created_user.is_admin == True
        assert created_user.role == UserRole.ADMIN
        assert created_user.email == "newadmin@test.com"
        assert created_user.full_name == "New Admin User"
    
    def test_create_admin_user_super_admin(self):
        """Test creating super admin user"""
        result = self.manager.create_admin_user(
            "test_super_admin", "superadmin@test.com", "superpassword123", 
            "Super Admin User", "super_admin"
        )
        
        assert result['success'] == True
        
        # Verify user was created with super admin role
        created_user = self.db.query(UnifiedUser).filter(
            UnifiedUser.username == "test_super_admin"
        ).first()
        
        assert created_user.role == UserRole.SUPER_ADMIN
        assert created_user.is_admin == True
    
    def test_create_admin_user_duplicate_username(self):
        """Test admin user creation with duplicate username"""
        # Create first user
        self.create_test_user("test_duplicate")
        
        result = self.manager.create_admin_user(
            "test_duplicate", "different@test.com", "password123"
        )
        
        assert result['success'] == False
        assert result['user_created'] == False
        assert "already exists" in result['error']
    
    def test_create_admin_user_invalid_role(self):
        """Test admin user creation with invalid role"""
        result = self.manager.create_admin_user(
            "test_invalid_role", "invalid@test.com", "password123", 
            role="invalid_role"
        )
        
        assert result['success'] == False
        assert result['user_created'] == False
        assert "Invalid role" in result['error']
    
    def test_create_admin_user_short_password(self):
        """Test admin user creation with short password"""
        result = self.manager.create_admin_user(
            "test_short_pass", "short@test.com", "short"
        )
        
        assert result['success'] == False
        assert result['user_created'] == False
        assert "at least 8 characters" in result['error']
    
    def test_check_database_integrity_clean_database(self):
        """Test database integrity check with clean database"""
        # Create some valid test data
        admin_user = self.create_test_user(
            "test_integrity_admin", is_admin=True, role=UserRole.ADMIN
        )
        regular_user = self.create_test_user("test_integrity_user")
        
        results = self.manager.check_database_integrity()
        
        assert len(results['checks_performed']) > 0
        assert 'statistics' in results
        assert results['statistics']['total_users'] >= 2
        assert results['statistics']['admin_users'] >= 1
    
    def test_check_database_integrity_with_issues(self):
        """Test database integrity check with issues"""
        # Create user with inconsistent admin flags
        inconsistent_user = UnifiedUser(
            user_id="test_inconsistent",
            username="test_inconsistent",
            email="inconsistent@test.com",
            password_hash=auth_service.hash_password("password123"),
            role=UserRole.ADMIN,
            is_admin=False,  # Inconsistent with role
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(inconsistent_user)
        self.db.commit()
        
        results = self.manager.check_database_integrity()
        
        # Should find the inconsistency
        inconsistency_issues = [
            issue for issue in results['issues_found']
            if 'test_inconsistent' in issue
        ]
        assert len(inconsistency_issues) >= 1
    
    def test_list_admin_users(self):
        """Test listing admin users"""
        # Create test admin users
        admin1 = self.create_test_user(
            "test_list_admin1", is_admin=True, role=UserRole.ADMIN
        )
        admin2 = self.create_test_user(
            "test_list_admin2", is_admin=True, role=UserRole.SUPER_ADMIN
        )
        regular_user = self.create_test_user("test_list_regular")
        
        admin_users = self.manager.list_admin_users()
        
        # Should include both admin users but not regular user
        admin_usernames = [user['username'] for user in admin_users]
        assert 'test_list_admin1' in admin_usernames
        assert 'test_list_admin2' in admin_usernames
        assert 'test_list_regular' not in admin_usernames
        
        # Check admin user details
        admin1_details = [
            user for user in admin_users 
            if user['username'] == 'test_list_admin1'
        ][0]
        assert admin1_details['role'] == 'admin'
        assert admin1_details['is_admin'] == True
    
    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions"""
        # Create test user and expired session
        test_user = self.create_test_user("test_cleanup_user")
        
        expired_session = UnifiedUserSession(
            session_id="expired_session_token",
            user_id=test_user.id,
            token_hash="expired_hash",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            is_active=True
        )
        
        self.db.add(expired_session)
        self.db.commit()
        
        result = self.manager.cleanup_expired_sessions()
        
        assert result['success'] == True
        assert result['cleaned_sessions'] >= 1
        
        # Verify session was deactivated
        self.db.refresh(expired_session)
        assert expired_session.is_active == False

def run_integration_test():
    """Run integration test of the admin user verification system"""
    print("Running integration test of admin user verification system...")
    
    try:
        with AdminUserManager() as manager:
            print("\n1. Testing admin user verification...")
            verification_results = manager.verify_admin_users()
            print(f"   Found {verification_results['admin_users']} admin users")
            
            print("\n2. Testing database integrity check...")
            integrity_results = manager.check_database_integrity()
            print(f"   Performed {len(integrity_results['checks_performed'])} checks")
            print(f"   Found {len(integrity_results['issues_found'])} issues")
            
            print("\n3. Testing admin user creation...")
            test_username = f"test_integration_{int(datetime.now().timestamp())}"
            create_result = manager.create_admin_user(
                test_username, f"{test_username}@test.com", "testpassword123",
                "Integration Test Admin", "admin"
            )
            
            if create_result['success']:
                print(f"   Successfully created test admin user: {test_username}")
                
                print("\n4. Testing password validation...")
                validate_result = manager.validate_password_hash(test_username, "testpassword123")
                print(f"   Password validation: {'PASS' if validate_result['password_valid'] else 'FAIL'}")
                
                print("\n5. Testing password reset...")
                reset_result = manager.reset_user_password(test_username, "newpassword123")
                print(f"   Password reset: {'PASS' if reset_result['success'] else 'FAIL'}")
                
                print("\n6. Testing updated password...")
                validate_new_result = manager.validate_password_hash(test_username, "newpassword123")
                print(f"   New password validation: {'PASS' if validate_new_result['password_valid'] else 'FAIL'}")
                
                # Cleanup test user
                print(f"\n7. Cleaning up test user...")
                test_user = manager.db.query(UnifiedUser).filter(
                    UnifiedUser.username == test_username
                ).first()
                if test_user:
                    manager.db.delete(test_user)
                    manager.db.commit()
                    print("   Test user cleaned up successfully")
            else:
                print(f"   Failed to create test admin user: {create_result['error']}")
            
            print("\n8. Testing session cleanup...")
            cleanup_result = manager.cleanup_expired_sessions()
            print(f"   Cleaned up {cleanup_result.get('cleaned_sessions', 0)} expired sessions")
            
            print("\nIntegration test completed successfully!")
            return True
            
    except Exception as e:
        print(f"Integration test failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "integration":
        success = run_integration_test()
        sys.exit(0 if success else 1)
    else:
        # Run pytest
        pytest.main([__file__, "-v"])