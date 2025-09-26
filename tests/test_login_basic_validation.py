#!/usr/bin/env python3
"""
Basic Login Validation Test Suite
Simplified tests for login functionality without complex dependencies.

Requirements covered: 1.1, 1.2, 1.3, 1.4, 6.1, 6.2, 6.3, 6.4
"""

import pytest
import sys
import os
import tempfile
import shutil
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.database import Base
from backend.unified_models import UnifiedUser, UnifiedUserSession, UserRole
from backend.unified_auth import UnifiedAuthService

class TestBasicLoginValidation:
    """Basic login validation tests"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Create in-memory SQLite database for testing
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        
        self.auth_service = UnifiedAuthService(
            jwt_secret="test-secret-key-12345",
            jwt_algorithm="HS256",
            token_expire_hours=1
        )
    
    def teardown_method(self):
        """Cleanup after each test method"""
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
    
    def create_test_user(self, username: str, email: str, password: str, 
                        is_admin: bool = False, role: UserRole = UserRole.CUSTOMER, 
                        is_active: bool = True) -> UnifiedUser:
        """Create a test user"""
        db = self.SessionLocal()
        try:
            user = UnifiedUser(
                user_id=f"test_{username}",
                username=username,
                email=email,
                password_hash=self.auth_service.hash_password(password),
                full_name=f"Test {username}",
                role=role,
                is_admin=is_admin,
                is_active=is_active,
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()
    
    def test_user_authentication_with_email(self):
        """Test user authentication using email"""
        # Create test user
        test_user = self.create_test_user("testuser", "test@example.com", "password123")
        
        db = self.SessionLocal()
        try:
            # Test authentication
            authenticated_user = self.auth_service.authenticate_user("test@example.com", "password123", db)
            
            assert authenticated_user is not None
            assert authenticated_user.username == "testuser"
            assert authenticated_user.email == "test@example.com"
            assert authenticated_user.role == UserRole.CUSTOMER
        finally:
            db.close()
    
    def test_user_authentication_with_username(self):
        """Test user authentication using username"""
        # Create test user
        test_user = self.create_test_user("testuser2", "test2@example.com", "password123")
        
        db = self.SessionLocal()
        try:
            # Test authentication
            authenticated_user = self.auth_service.authenticate_user("testuser2", "password123", db)
            
            assert authenticated_user is not None
            assert authenticated_user.username == "testuser2"
            assert authenticated_user.email == "test2@example.com"
        finally:
            db.close()
    
    def test_admin_user_authentication(self):
        """Test admin user authentication"""
        # Create admin user
        admin_user = self.create_test_user(
            "adminuser", "admin@example.com", "adminpass123", 
            is_admin=True, role=UserRole.ADMIN
        )
        
        db = self.SessionLocal()
        try:
            # Test authentication
            authenticated_user = self.auth_service.authenticate_user("admin@example.com", "adminpass123", db)
            
            assert authenticated_user is not None
            assert authenticated_user.is_admin is True
            assert authenticated_user.role == UserRole.ADMIN
        finally:
            db.close()
    
    def test_invalid_credentials(self):
        """Test authentication with invalid credentials"""
        # Create test user
        test_user = self.create_test_user("testuser3", "test3@example.com", "correctpass")
        
        db = self.SessionLocal()
        try:
            # Test with wrong password
            authenticated_user = self.auth_service.authenticate_user("test3@example.com", "wrongpass", db)
            assert authenticated_user is None
            
            # Test with non-existent user
            authenticated_user = self.auth_service.authenticate_user("nonexistent@example.com", "password", db)
            assert authenticated_user is None
        finally:
            db.close()
    
    def test_inactive_user_authentication(self):
        """Test authentication with inactive user"""
        # Create inactive user
        inactive_user = self.create_test_user(
            "inactiveuser", "inactive@example.com", "password123", 
            is_active=False
        )
        
        db = self.SessionLocal()
        try:
            # Test authentication should fail for inactive user
            authenticated_user = self.auth_service.authenticate_user("inactive@example.com", "password123", db)
            assert authenticated_user is None
        finally:
            db.close()
    
    def test_session_creation_and_validation(self):
        """Test session creation and validation"""
        # Create test user
        test_user = self.create_test_user("sessionuser", "session@example.com", "password123")
        
        db = self.SessionLocal()
        try:
            # Create session
            session_token = self.auth_service.create_user_session(test_user, db)
            
            assert session_token is not None
            assert len(session_token) > 20
            
            # Validate session
            session_user = self.auth_service.get_user_from_session(session_token, db)
            assert session_user is not None
            assert session_user.username == "sessionuser"
            
            # Check session exists in database
            session_record = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.session_id == session_token
            ).first()
            assert session_record is not None
            assert session_record.user_id == test_user.id
            assert session_record.is_active is True
        finally:
            db.close()
    
    def test_session_invalidation(self):
        """Test session invalidation"""
        # Create test user and session
        test_user = self.create_test_user("invalidateuser", "invalidate@example.com", "password123")
        
        db = self.SessionLocal()
        try:
            session_token = self.auth_service.create_user_session(test_user, db)
            
            # Verify session is valid
            session_user = self.auth_service.get_user_from_session(session_token, db)
            assert session_user is not None
            
            # Invalidate session
            result = self.auth_service.invalidate_session(session_token, db)
            assert result is True
            
            # Verify session is no longer valid
            invalid_user = self.auth_service.get_user_from_session(session_token, db)
            assert invalid_user is None
        finally:
            db.close()
    
    def test_session_expiration(self):
        """Test session expiration handling"""
        # Create test user
        test_user = self.create_test_user("expireuser", "expire@example.com", "password123")
        
        db = self.SessionLocal()
        try:
            # Create session
            session_token = self.auth_service.create_user_session(test_user, db)
            
            # Manually expire the session
            session_record = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.session_id == session_token
            ).first()
            session_record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db.commit()
            
            # Session should be invalid due to expiration
            expired_user = self.auth_service.get_user_from_session(session_token, db)
            assert expired_user is None
        finally:
            db.close()
    
    def test_password_hashing_security(self):
        """Test password hashing security"""
        password = "test_password_123"
        
        # Test password hashing
        hash1 = self.auth_service.hash_password(password)
        hash2 = self.auth_service.hash_password(password)
        
        # Hashes should be different (salt)
        assert hash1 != hash2
        
        # Both should verify correctly
        assert self.auth_service.verify_password(password, hash1)
        assert self.auth_service.verify_password(password, hash2)
        
        # Wrong password should fail
        assert not self.auth_service.verify_password("wrong_password", hash1)
    
    def test_jwt_token_creation_and_validation(self):
        """Test JWT token creation and validation"""
        # Create test user
        test_user = self.create_test_user("jwtuser", "jwt@example.com", "password123")
        
        db = self.SessionLocal()
        try:
            # Create JWT token
            jwt_token = self.auth_service.create_jwt_token(test_user)
            assert jwt_token is not None
            
            # Validate JWT token
            jwt_user = self.auth_service.get_user_from_jwt(jwt_token, db)
            assert jwt_user is not None
            assert jwt_user.username == "jwtuser"
        finally:
            db.close()
    
    def test_role_based_permissions(self):
        """Test role-based permission system"""
        # Create users with different roles
        customer = self.create_test_user("customer", "customer@example.com", "password", role=UserRole.CUSTOMER)
        admin = self.create_test_user("admin", "admin@example.com", "password", is_admin=True, role=UserRole.ADMIN)
        
        db = self.SessionLocal()
        try:
            # Test customer permissions
            customer_auth = self.auth_service.authenticate_user("customer", "password", db)
            assert customer_auth.role == UserRole.CUSTOMER
            assert customer_auth.is_admin is False
            
            # Test admin permissions
            admin_auth = self.auth_service.authenticate_user("admin", "password", db)
            assert admin_auth.role == UserRole.ADMIN
            assert admin_auth.is_admin is True
        finally:
            db.close()

def run_basic_validation_tests():
    """Run basic validation tests"""
    print("Running Basic Login Validation Tests...")
    
    try:
        # Create test instance
        test_instance = TestBasicLoginValidation()
        
        # Get all test methods
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        passed_tests = 0
        failed_tests = []
        
        for test_method in test_methods:
            print(f"  Running {test_method}...")
            
            try:
                # Setup
                test_instance.setup_method()
                
                # Run test
                getattr(test_instance, test_method)()
                
                # Cleanup
                test_instance.teardown_method()
                
                passed_tests += 1
                print(f"    PASSED")
                
            except Exception as e:
                failed_tests.append(f"{test_method}: {str(e)}")
                print(f"    FAILED: {str(e)}")
        
        print(f"\nBasic Validation Test Results:")
        print(f"Total tests: {len(test_methods)}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {len(failed_tests)}")
        
        if failed_tests:
            print(f"\nFailed tests:")
            for failure in failed_tests:
                print(f"  - {failure}")
            return False
        else:
            print(f"\nAll basic validation tests passed!")
            return True
            
    except Exception as e:
        print(f"Test execution failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        success = run_basic_validation_tests()
        sys.exit(0 if success else 1)
    else:
        # Run with pytest
        pytest.main([__file__, "-v"])