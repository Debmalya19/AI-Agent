#!/usr/bin/env python3
"""
Comprehensive Authentication Integration Tests - Final Implementation
Tests all aspects of the unified authentication system including:
- User login flow using unified authentication
- Admin dashboard access with unified auth system  
- Session management and validation
- Migration process and data integrity
- End-to-end authentication workflows

Requirements covered: 1.1, 1.2, 2.1, 2.2, 4.1, 4.2, 6.1, 6.2, 6.3, 6.4
"""

import pytest
import asyncio
import requests
import time
import subprocess
import sys
import os
import json
import sqlite3
import tempfile
import shutil
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import Base, get_db
from backend.unified_models import UnifiedUser, UnifiedUserSession, UserRole
from backend.unified_auth import UnifiedAuthService, AuthenticatedUser, Permission
from backend.auth_migration_system import AuthMigrationSystem, MigrationConfig, MigrationStats
from backend.session_utils import SessionUtils
from backend.auth_routes import auth_router

class TestDatabaseSetup:
    """Setup test databases and utilities"""
    
    @staticmethod
    def create_test_db():
        """Create a test database"""
        engine = create_engine(
            "sqlite:///./test_auth_integration.db",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        return engine, TestingSessionLocal
    
    @staticmethod
    def cleanup_test_db():
        """Clean up test database"""
        try:
            if os.path.exists("./test_auth_integration.db"):
                os.remove("./test_auth_integration.db")
        except Exception as e:
            print(f"Warning: Could not clean up test database: {e}")

class TestUserLoginFlow:
    """Test user login flow using unified authentication - Requirements 1.1, 1.2, 6.1"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.engine, self.SessionLocal = TestDatabaseSetup.create_test_db()
        self.auth_service = UnifiedAuthService(
            jwt_secret="test-secret-key-12345",
            jwt_algorithm="HS256",
            token_expire_hours=1
        )
    
    def teardown_method(self):
        """Cleanup after each test method"""
        TestDatabaseSetup.cleanup_test_db()
    
    def test_user_registration_and_login_flow(self):
        """Test complete user registration and login flow"""
        db = self.SessionLocal()
        try:
            # 1. Create a new user (registration)
            user_data = {
                "user_id": "test_user_001",
                "username": "testuser",
                "email": "test@example.com",
                "password": "secure_password_123",
                "full_name": "Test User"
            }
            
            # Hash password
            password_hash = self.auth_service.hash_password(user_data["password"])
            
            # Create user
            user = UnifiedUser(
                user_id=user_data["user_id"],
                username=user_data["username"],
                email=user_data["email"],
                password_hash=password_hash,
                full_name=user_data["full_name"],
                role=UserRole.CUSTOMER,
                is_admin=False,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # 2. Test login with username
            authenticated_user = self.auth_service.authenticate_user(
                user_data["username"], user_data["password"], db
            )
            assert authenticated_user is not None
            assert authenticated_user.username == user_data["username"]
            assert authenticated_user.email == user_data["email"]
            assert authenticated_user.role == UserRole.CUSTOMER
            
            # 3. Test login with email
            authenticated_user_email = self.auth_service.authenticate_user(
                user_data["email"], user_data["password"], db
            )
            assert authenticated_user_email is not None
            assert authenticated_user_email.username == user_data["username"]
            
            # 4. Test session creation
            session_token = self.auth_service.create_user_session(authenticated_user, db)
            assert session_token is not None
            assert len(session_token) > 20  # Should be a proper token
            
            # 5. Test session validation
            session_user = self.auth_service.get_user_from_session(session_token, db)
            assert session_user is not None
            assert session_user.username == user_data["username"]
            assert session_user.has_permission(Permission.TICKET_CREATE)
            
            # 6. Test JWT token creation
            jwt_token = self.auth_service.create_jwt_token(authenticated_user)
            assert jwt_token is not None
            
            # 7. Test JWT validation
            jwt_user = self.auth_service.get_user_from_jwt(jwt_token, db)
            assert jwt_user is not None
            assert jwt_user.username == user_data["username"]
            
            print("✓ User registration and login flow test passed")
            
        finally:
            db.close()
    
    def test_login_failure_scenarios(self):
        """Test various login failure scenarios"""
        db = self.SessionLocal()
        try:
            # Create test user
            user = UnifiedUser(
                user_id="test_user_002",
                username="testuser2",
                email="test2@example.com",
                password_hash=self.auth_service.hash_password("correct_password"),
                role=UserRole.CUSTOMER,
                is_active=True
            )
            db.add(user)
            db.commit()
            
            # Test wrong password
            auth_user = self.auth_service.authenticate_user("testuser2", "wrong_password", db)
            assert auth_user is None
            
            # Test non-existent user
            auth_user = self.auth_service.authenticate_user("nonexistent", "password", db)
            assert auth_user is None
            
            # Test inactive user
            user.is_active = False
            db.commit()
            auth_user = self.auth_service.authenticate_user("testuser2", "correct_password", db)
            assert auth_user is None
            
            print("✓ Login failure scenarios test passed")
            
        finally:
            db.close()
    
    def test_password_security(self):
        """Test password hashing and security"""
        # Test password hashing
        password = "test_password_123"
        hash1 = self.auth_service.hash_password(password)
        hash2 = self.auth_service.hash_password(password)
        
        # Hashes should be different (salt)
        assert hash1 != hash2
        
        # Both should verify correctly
        assert self.auth_service.verify_password(password, hash1)
        assert self.auth_service.verify_password(password, hash2)
        
        # Wrong password should fail
        assert not self.auth_service.verify_password("wrong_password", hash1)
        
        print("✓ Password security test passed")

class TestAdminDashboardAccess:
    """Test admin dashboard access with unified auth system - Requirements 2.1, 2.2, 2.3, 2.4, 6.2, 6.4"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.engine, self.SessionLocal = TestDatabaseSetup.create_test_db()
        self.auth_service = UnifiedAuthService(
            jwt_secret="test-secret-key-12345",
            jwt_algorithm="HS256",
            token_expire_hours=1
        )
    
    def teardown_method(self):
        """Cleanup after each test method"""
        TestDatabaseSetup.cleanup_test_db()
    
    def test_admin_user_creation_and_access(self):
        """Test admin user creation and dashboard access"""
        db = self.SessionLocal()
        try:
            # Create admin user
            admin_user = UnifiedUser(
                user_id="admin_001",
                username="adminuser",
                email="admin@example.com",
                password_hash=self.auth_service.hash_password("admin_password_123"),
                full_name="Admin User",
                role=UserRole.ADMIN,
                is_admin=True,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            # Test admin authentication
            auth_admin = self.auth_service.authenticate_user("adminuser", "admin_password_123", db)
            assert auth_admin is not None
            assert auth_admin.is_admin is True
            assert auth_admin.role == UserRole.ADMIN
            
            # Test admin permissions
            assert auth_admin.has_permission(Permission.DASHBOARD_VIEW)
            assert auth_admin.has_permission(Permission.USER_CREATE)
            assert auth_admin.has_permission(Permission.USER_UPDATE)
            assert auth_admin.has_permission(Permission.USER_DELETE)
            assert auth_admin.has_permission(Permission.TICKET_ASSIGN)
            assert auth_admin.has_permission(Permission.DASHBOARD_ANALYTICS)
            
            # Test admin session creation
            session_token = self.auth_service.create_user_session(auth_admin, db)
            assert session_token is not None
            
            # Test admin session validation
            session_admin = self.auth_service.get_user_from_session(session_token, db)
            assert session_admin is not None
            assert session_admin.is_admin is True
            assert session_admin.has_permission(Permission.DASHBOARD_VIEW)
            
            print("✓ Admin user creation and access test passed")
            
        finally:
            db.close()
    
    def test_role_based_permissions(self):
        """Test role-based permission system"""
        db = self.SessionLocal()
        try:
            # Create users with different roles
            customer = UnifiedUser(
                user_id="customer_001",
                username="customer",
                email="customer@example.com",
                password_hash=self.auth_service.hash_password("password"),
                role=UserRole.CUSTOMER,
                is_admin=False
            )
            
            agent = UnifiedUser(
                user_id="agent_001",
                username="agent",
                email="agent@example.com",
                password_hash=self.auth_service.hash_password("password"),
                role=UserRole.AGENT,
                is_admin=False
            )
            
            admin = UnifiedUser(
                user_id="admin_001",
                username="admin",
                email="admin@example.com",
                password_hash=self.auth_service.hash_password("password"),
                role=UserRole.ADMIN,
                is_admin=True
            )
            
            super_admin = UnifiedUser(
                user_id="super_admin_001",
                username="superadmin",
                email="superadmin@example.com",
                password_hash=self.auth_service.hash_password("password"),
                role=UserRole.SUPER_ADMIN,
                is_admin=True
            )
            
            db.add_all([customer, agent, admin, super_admin])
            db.commit()
            
            # Test customer permissions
            customer_auth = self.auth_service.authenticate_user("customer", "password", db)
            assert customer_auth.has_permission(Permission.TICKET_CREATE)
            assert customer_auth.has_permission(Permission.TICKET_READ)
            assert not customer_auth.has_permission(Permission.USER_DELETE)
            assert not customer_auth.has_permission(Permission.DASHBOARD_VIEW)
            
            # Test agent permissions
            agent_auth = self.auth_service.authenticate_user("agent", "password", db)
            assert agent_auth.has_permission(Permission.TICKET_READ)
            assert agent_auth.has_permission(Permission.TICKET_UPDATE)
            assert agent_auth.has_permission(Permission.DASHBOARD_VIEW)
            assert not agent_auth.has_permission(Permission.USER_DELETE)
            
            # Test admin permissions
            admin_auth = self.auth_service.authenticate_user("admin", "password", db)
            assert admin_auth.has_permission(Permission.USER_CREATE)
            assert admin_auth.has_permission(Permission.USER_DELETE)
            assert admin_auth.has_permission(Permission.DASHBOARD_VIEW)
            assert admin_auth.has_permission(Permission.TICKET_ASSIGN)
            
            # Test super admin permissions (should have all)
            super_admin_auth = self.auth_service.authenticate_user("superadmin", "password", db)
            all_permissions = list(Permission)
            for permission in all_permissions:
                assert super_admin_auth.has_permission(permission)
            
            print("✓ Role-based permissions test passed")
            
        finally:
            db.close()
    
    def test_admin_dashboard_integration(self):
        """Test admin dashboard integration with unified auth"""
        db = self.SessionLocal()
        try:
            # Create admin user
            admin = UnifiedUser(
                user_id="dashboard_admin",
                username="dashboardadmin",
                email="dashboard@example.com",
                password_hash=self.auth_service.hash_password("dashboard_pass"),
                role=UserRole.ADMIN,
                is_admin=True
            )
            db.add(admin)
            db.commit()
            
            # Simulate admin dashboard login
            auth_admin = self.auth_service.authenticate_user("dashboardadmin", "dashboard_pass", db)
            session_token = self.auth_service.create_user_session(auth_admin, db)
            
            # Test dashboard-specific permissions
            assert auth_admin.has_permission(Permission.DASHBOARD_VIEW)
            assert auth_admin.has_permission(Permission.DASHBOARD_ANALYTICS)
            assert auth_admin.has_permission(Permission.DASHBOARD_REPORTS)
            
            # Test user management permissions
            assert auth_admin.has_permission(Permission.USER_LIST)
            assert auth_admin.has_permission(Permission.USER_CREATE)
            assert auth_admin.has_permission(Permission.USER_UPDATE)
            
            # Test ticket management permissions
            assert auth_admin.has_permission(Permission.TICKET_LIST)
            assert auth_admin.has_permission(Permission.TICKET_ASSIGN)
            assert auth_admin.has_permission(Permission.TICKET_UPDATE)
            
            print("✓ Admin dashboard integration test passed")
            
        finally:
            db.close()

class TestSessionManagement:
    """Test session management and validation - Requirements 6.1, 6.3"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.engine, self.SessionLocal = TestDatabaseSetup.create_test_db()
        self.auth_service = UnifiedAuthService(
            jwt_secret="test-secret-key-12345",
            jwt_algorithm="HS256",
            token_expire_hours=1
        )
    
    def teardown_method(self):
        """Cleanup after each test method"""
        TestDatabaseSetup.cleanup_test_db()
    
    def test_session_creation_and_validation(self):
        """Test session creation and validation"""
        db = self.SessionLocal()
        try:
            # Create test user
            user = UnifiedUser(
                user_id="session_user",
                username="sessionuser",
                email="session@example.com",
                password_hash=self.auth_service.hash_password("password"),
                role=UserRole.CUSTOMER
            )
            db.add(user)
            db.commit()
            
            # Create session
            session_token = self.auth_service.create_user_session(user, db)
            assert session_token is not None
            
            # Validate session
            session_user = self.auth_service.get_user_from_session(session_token, db)
            assert session_user is not None
            assert session_user.username == "sessionuser"
            
            # Check session exists in database
            session_record = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.session_id == session_token
            ).first()
            assert session_record is not None
            assert session_record.user_id == user.id
            assert session_record.is_active is True
            
            print("✓ Session creation and validation test passed")
            
        finally:
            db.close()
    
    def test_session_invalidation(self):
        """Test session invalidation"""
        db = self.SessionLocal()
        try:
            # Create user and session
            user = UnifiedUser(
                user_id="invalidation_user",
                username="invalidationuser",
                email="invalidation@example.com",
                password_hash=self.auth_service.hash_password("password"),
                role=UserRole.CUSTOMER
            )
            db.add(user)
            db.commit()
            
            session_token = self.auth_service.create_user_session(user, db)
            
            # Verify session is valid
            session_user = self.auth_service.get_user_from_session(session_token, db)
            assert session_user is not None
            
            # Invalidate session
            result = self.auth_service.invalidate_session(session_token, db)
            assert result is True
            
            # Verify session is no longer valid
            invalid_user = self.auth_service.get_user_from_session(session_token, db)
            assert invalid_user is None
            
            # Check session is marked inactive in database
            session_record = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.session_id == session_token
            ).first()
            assert session_record is not None
            assert session_record.is_active is False
            
            print("✓ Session invalidation test passed")
            
        finally:
            db.close()
    
    def test_multiple_sessions_per_user(self):
        """Test multiple sessions per user"""
        db = self.SessionLocal()
        try:
            # Create user
            user = UnifiedUser(
                user_id="multi_session_user",
                username="multisessionuser",
                email="multisession@example.com",
                password_hash=self.auth_service.hash_password("password"),
                role=UserRole.CUSTOMER
            )
            db.add(user)
            db.commit()
            
            # Create multiple sessions
            session1 = self.auth_service.create_user_session(user, db)
            session2 = self.auth_service.create_user_session(user, db)
            session3 = self.auth_service.create_user_session(user, db)
            
            # All sessions should be valid
            assert self.auth_service.get_user_from_session(session1, db) is not None
            assert self.auth_service.get_user_from_session(session2, db) is not None
            assert self.auth_service.get_user_from_session(session3, db) is not None
            
            # Check session count
            active_sessions = SessionUtils.get_active_sessions_count(user.id, db)
            assert active_sessions == 3
            
            # Invalidate one session
            self.auth_service.invalidate_session(session2, db)
            
            # Check remaining sessions
            assert self.auth_service.get_user_from_session(session1, db) is not None
            assert self.auth_service.get_user_from_session(session2, db) is None
            assert self.auth_service.get_user_from_session(session3, db) is not None
            
            active_sessions = SessionUtils.get_active_sessions_count(user.id, db)
            assert active_sessions == 2
            
            print("✓ Multiple sessions per user test passed")
            
        finally:
            db.close()
    
    def test_session_expiration(self):
        """Test session expiration"""
        db = self.SessionLocal()
        try:
            # Create user
            user = UnifiedUser(
                user_id="expiry_user",
                username="expiryuser",
                email="expiry@example.com",
                password_hash=self.auth_service.hash_password("password"),
                role=UserRole.CUSTOMER
            )
            db.add(user)
            db.commit()
            
            # Create session
            session_token = self.auth_service.create_user_session(user, db)
            
            # Manually expire the session
            session_record = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.session_id == session_token
            ).first()
            session_record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db.commit()
            
            # Session should be invalid due to expiration
            expired_user = self.auth_service.get_user_from_session(session_token, db)
            assert expired_user is None
            
            print("✓ Session expiration test passed")
            
        finally:
            db.close()

class TestMigrationProcess:
    """Test migration process and data integrity - Requirements 3.1, 3.2, 4.1, 4.2, 4.3"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.test_dir = tempfile.mkdtemp()
        self.engine, self.SessionLocal = TestDatabaseSetup.create_test_db()
        
        # Create legacy tables for migration testing
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    user_id VARCHAR(50) UNIQUE,
                    username VARCHAR(100) UNIQUE,
                    email VARCHAR(255) UNIQUE,
                    password_hash VARCHAR(255),
                    full_name VARCHAR(255),
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY,
                    session_id VARCHAR(255) UNIQUE,
                    user_id INTEGER,
                    token_hash VARCHAR(255),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """))
            conn.commit()
    
    def teardown_method(self):
        """Cleanup after each test method"""
        TestDatabaseSetup.cleanup_test_db()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_user_data_migration(self):
        """Test user data migration from legacy to unified system"""
        db = self.SessionLocal()
        try:
            # Create legacy users
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO users (user_id, username, email, password_hash, full_name, is_admin)
                    VALUES 
                    ('legacy_001', 'legacyuser1', 'legacy1@example.com', 'hash1', 'Legacy User 1', FALSE),
                    ('legacy_002', 'legacyuser2', 'legacy2@example.com', 'hash2', 'Legacy User 2', FALSE),
                    ('admin_001', 'legacyadmin', 'admin@example.com', 'adminhash', 'Legacy Admin', TRUE)
                """))
                conn.commit()
            
            # Create migration system
            config = MigrationConfig(
                backup_enabled=False,  # Skip backup for test
                dry_run=False
            )
            migration_system = AuthMigrationSystem(config)
            
            # Run user migration
            with patch.object(migration_system, 'db_session', db):
                result = migration_system.migrate_users()
            
            assert result.success is True
            assert result.users_migrated == 3
            
            # Verify migrated users
            migrated_users = db.query(UnifiedUser).all()
            assert len(migrated_users) == 3
            
            # Check specific user data
            user1 = db.query(UnifiedUser).filter(UnifiedUser.user_id == 'legacy_001').first()
            assert user1 is not None
            assert user1.username == 'legacyuser1'
            assert user1.email == 'legacy1@example.com'
            assert user1.role == UserRole.CUSTOMER
            assert user1.is_admin is False
            
            admin_user = db.query(UnifiedUser).filter(UnifiedUser.user_id == 'admin_001').first()
            assert admin_user is not None
            assert admin_user.is_admin is True
            assert admin_user.role == UserRole.ADMIN
            
            print("✓ User data migration test passed")
            
        finally:
            db.close()
    
    def test_session_migration(self):
        """Test session migration from legacy to unified system"""
        db = self.SessionLocal()
        try:
            # Create legacy user and sessions
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO users (id, user_id, username, email, password_hash)
                    VALUES (1, 'session_user', 'sessionuser', 'session@example.com', 'hash')
                """))
                
                conn.execute(text("""
                    INSERT INTO user_sessions (session_id, user_id, token_hash, expires_at)
                    VALUES 
                    ('session_001', 1, 'token_hash_1', datetime('now', '+1 day')),
                    ('session_002', 1, 'token_hash_2', datetime('now', '+1 day'))
                """))
                conn.commit()
            
            # First migrate users
            config = MigrationConfig(backup_enabled=False, dry_run=False)
            migration_system = AuthMigrationSystem(config)
            
            with patch.object(migration_system, 'db_session', db):
                user_result = migration_system.migrate_users()
                assert user_result.success is True
                
                # Then migrate sessions
                session_result = migration_system.migrate_sessions()
                assert session_result.success is True
                assert session_result.sessions_migrated == 2
            
            # Verify migrated sessions
            migrated_sessions = db.query(UnifiedUserSession).all()
            assert len(migrated_sessions) == 2
            
            # Check session data
            session1 = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.session_id == 'session_001'
            ).first()
            assert session1 is not None
            assert session1.is_active is True
            
            print("✓ Session migration test passed")
            
        finally:
            db.close()
    
    def test_migration_data_integrity(self):
        """Test data integrity during migration"""
        db = self.SessionLocal()
        try:
            # Create comprehensive test data
            with self.engine.connect() as conn:
                # Users with various scenarios
                conn.execute(text("""
                    INSERT INTO users (id, user_id, username, email, password_hash, full_name, is_admin)
                    VALUES 
                    (1, 'integrity_001', 'user1', 'user1@example.com', 'hash1', 'User One', FALSE),
                    (2, 'integrity_002', 'user2', 'user2@example.com', 'hash2', 'User Two', FALSE),
                    (3, 'integrity_003', 'admin1', 'admin1@example.com', 'hash3', 'Admin One', TRUE)
                """))
                
                # Sessions for users
                conn.execute(text("""
                    INSERT INTO user_sessions (session_id, user_id, token_hash, expires_at, is_active)
                    VALUES 
                    ('int_session_001', 1, 'token1', datetime('now', '+1 day'), TRUE),
                    ('int_session_002', 2, 'token2', datetime('now', '+1 day'), TRUE),
                    ('int_session_003', 1, 'token3', datetime('now', '-1 day'), FALSE)
                """))
                conn.commit()
            
            # Run migration
            config = MigrationConfig(backup_enabled=False, dry_run=False)
            migration_system = AuthMigrationSystem(config)
            
            with patch.object(migration_system, 'db_session', db):
                # Migrate users
                user_result = migration_system.migrate_users()
                assert user_result.success is True
                assert user_result.users_migrated == 3
                
                # Migrate sessions
                session_result = migration_system.migrate_sessions()
                assert session_result.success is True
                assert session_result.sessions_migrated == 3
                
                # Validate data integrity
                validation_result = migration_system.validate_migration()
                assert validation_result.success is True
            
            # Verify all data is correctly migrated
            users = db.query(UnifiedUser).all()
            sessions = db.query(UnifiedUserSession).all()
            
            assert len(users) == 3
            assert len(sessions) == 3
            
            # Check user-session relationships
            user1 = db.query(UnifiedUser).filter(UnifiedUser.user_id == 'integrity_001').first()
            user1_sessions = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.user_id == user1.id
            ).all()
            assert len(user1_sessions) == 2  # Two sessions for user1
            
            print("✓ Migration data integrity test passed")
            
        finally:
            db.close()

class TestEndToEndWorkflows:
    """Test complete end-to-end authentication workflows - Requirements 6.1, 6.2, 6.3, 6.4"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.engine, self.SessionLocal = TestDatabaseSetup.create_test_db()
        self.auth_service = UnifiedAuthService(
            jwt_secret="test-secret-key-12345",
            jwt_algorithm="HS256",
            token_expire_hours=1
        )
        
        # Create FastAPI test app
        self.app = FastAPI()
        self.app.include_router(auth_router)
        
        # Override database dependency
        def override_get_db():
            try:
                db = self.SessionLocal()
                yield db
            finally:
                db.close()
        
        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)
    
    def teardown_method(self):
        """Cleanup after each test method"""
        TestDatabaseSetup.cleanup_test_db()
    
    def test_complete_user_workflow(self):
        """Test complete user workflow from registration to logout"""
        db = self.SessionLocal()
        try:
            # 1. User Registration
            user_data = {
                "user_id": "workflow_user",
                "username": "workflowuser",
                "email": "workflow@example.com",
                "password": "secure_password_123",
                "full_name": "Workflow User"
            }
            
            user = UnifiedUser(
                user_id=user_data["user_id"],
                username=user_data["username"],
                email=user_data["email"],
                password_hash=self.auth_service.hash_password(user_data["password"]),
                full_name=user_data["full_name"],
                role=UserRole.CUSTOMER
            )
            db.add(user)
            db.commit()
            
            # 2. Login
            auth_user = self.auth_service.authenticate_user(
                user_data["username"], user_data["password"], db
            )
            assert auth_user is not None
            
            # 3. Session Creation
            session_token = self.auth_service.create_user_session(auth_user, db)
            assert session_token is not None
            
            # 4. Access Protected Resource (simulate)
            session_user = self.auth_service.get_user_from_session(session_token, db)
            assert session_user is not None
            assert session_user.has_permission(Permission.TICKET_CREATE)
            
            # 5. JWT Token for API Access
            jwt_token = self.auth_service.create_jwt_token(auth_user)
            jwt_user = self.auth_service.get_user_from_jwt(jwt_token, db)
            assert jwt_user is not None
            
            # 6. Logout
            logout_result = self.auth_service.invalidate_session(session_token, db)
            assert logout_result is True
            
            # 7. Verify session is invalid
            invalid_user = self.auth_service.get_user_from_session(session_token, db)
            assert invalid_user is None
            
            print("✓ Complete user workflow test passed")
            
        finally:
            db.close()
    
    def test_admin_workflow(self):
        """Test complete admin workflow"""
        db = self.SessionLocal()
        try:
            # 1. Create Admin User
            admin = UnifiedUser(
                user_id="workflow_admin",
                username="workflowadmin",
                email="workflowadmin@example.com",
                password_hash=self.auth_service.hash_password("admin_password"),
                role=UserRole.ADMIN,
                is_admin=True
            )
            db.add(admin)
            db.commit()
            
            # 2. Admin Login
            auth_admin = self.auth_service.authenticate_user("workflowadmin", "admin_password", db)
            assert auth_admin is not None
            assert auth_admin.is_admin is True
            
            # 3. Admin Session
            session_token = self.auth_service.create_user_session(auth_admin, db)
            session_admin = self.auth_service.get_user_from_session(session_token, db)
            
            # 4. Admin Dashboard Access (permission check)
            assert session_admin.has_permission(Permission.DASHBOARD_VIEW)
            assert session_admin.has_permission(Permission.USER_CREATE)
            assert session_admin.has_permission(Permission.TICKET_ASSIGN)
            
            # 5. User Management (simulate creating a user)
            assert session_admin.has_permission(Permission.USER_CREATE)
            
            # Create a customer user (simulating admin action)
            customer = UnifiedUser(
                user_id="admin_created_user",
                username="admincreated",
                email="admincreated@example.com",
                password_hash=self.auth_service.hash_password("customer_password"),
                role=UserRole.CUSTOMER
            )
            db.add(customer)
            db.commit()
            
            # 6. Verify customer can login
            auth_customer = self.auth_service.authenticate_user("admincreated", "customer_password", db)
            assert auth_customer is not None
            assert auth_customer.role == UserRole.CUSTOMER
            
            print("✓ Admin workflow test passed")
            
        finally:
            db.close()
    
    def test_concurrent_sessions_workflow(self):
        """Test concurrent sessions workflow"""
        db = self.SessionLocal()
        try:
            # Create user
            user = UnifiedUser(
                user_id="concurrent_user",
                username="concurrentuser",
                email="concurrent@example.com",
                password_hash=self.auth_service.hash_password("password"),
                role=UserRole.CUSTOMER
            )
            db.add(user)
            db.commit()
            
            # Create multiple sessions (simulate multiple devices)
            sessions = []
            for i in range(3):
                auth_user = self.auth_service.authenticate_user("concurrentuser", "password", db)
                session_token = self.auth_service.create_user_session(auth_user, db)
                sessions.append(session_token)
            
            # Verify all sessions are active
            for session_token in sessions:
                session_user = self.auth_service.get_user_from_session(session_token, db)
                assert session_user is not None
            
            # Check session count
            active_count = SessionUtils.get_active_sessions_count(user.id, db)
            assert active_count == 3
            
            # Logout from one session
            self.auth_service.invalidate_session(sessions[1], db)
            
            # Verify remaining sessions
            assert self.auth_service.get_user_from_session(sessions[0], db) is not None
            assert self.auth_service.get_user_from_session(sessions[1], db) is None
            assert self.auth_service.get_user_from_session(sessions[2], db) is not None
            
            active_count = SessionUtils.get_active_sessions_count(user.id, db)
            assert active_count == 2
            
            print("✓ Concurrent sessions workflow test passed")
            
        finally:
            db.close()

class TestAPIEndpoints:
    """Test authentication API endpoints"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.engine, self.SessionLocal = TestDatabaseSetup.create_test_db()
        
        # Create FastAPI test app
        self.app = FastAPI()
        self.app.include_router(auth_router)
        
        # Override database dependency
        def override_get_db():
            try:
                db = self.SessionLocal()
                yield db
            finally:
                db.close()
        
        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)
    
    def teardown_method(self):
        """Cleanup after each test method"""
        TestDatabaseSetup.cleanup_test_db()
    
    def test_login_api_endpoint(self):
        """Test login API endpoint"""
        # Create test user
        db = self.SessionLocal()
        auth_service = UnifiedAuthService("test-secret")
        
        user = UnifiedUser(
            user_id="api_user",
            username="apiuser",
            email="api@example.com",
            password_hash=auth_service.hash_password("api_password"),
            role=UserRole.CUSTOMER
        )
        db.add(user)
        db.commit()
        db.close()
        
        # Test login endpoint
        response = self.client.post(
            "/api/auth/login",
            json={"username": "apiuser", "password": "api_password"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "user" in data
        assert data["user"]["username"] == "apiuser"
        
        print("✓ Login API endpoint test passed")
    
    def test_jwt_token_api_endpoint(self):
        """Test JWT token API endpoint"""
        # Create test user
        db = self.SessionLocal()
        auth_service = UnifiedAuthService("test-secret")
        
        user = UnifiedUser(
            user_id="jwt_user",
            username="jwtuser",
            email="jwt@example.com",
            password_hash=auth_service.hash_password("jwt_password"),
            role=UserRole.CUSTOMER
        )
        db.add(user)
        db.commit()
        db.close()
        
        # Test JWT token endpoint
        response = self.client.post(
            "/api/auth/token",
            json={"username": "jwtuser", "password": "jwt_password"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        
        print("✓ JWT token API endpoint test passed")

def run_all_tests():
    """Run all integration tests"""
    print("🚀 Starting Comprehensive Authentication Integration Tests\n")
    
    test_classes = [
        TestUserLoginFlow,
        TestAdminDashboardAccess,
        TestSessionManagement,
        TestMigrationProcess,
        TestEndToEndWorkflows,
        TestAPIEndpoints
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__} tests...")
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for test_method in test_methods:
            total_tests += 1
            try:
                # Create test instance
                test_instance = test_class()
                test_instance.setup_method()
                
                # Run test method
                getattr(test_instance, test_method)()
                
                # Cleanup
                test_instance.teardown_method()
                
                passed_tests += 1
                print(f"  ✅ {test_method}")
                
            except Exception as e:
                failed_tests.append(f"{test_class.__name__}.{test_method}: {str(e)}")
                print(f"  ❌ {test_method}: {str(e)}")
    
    # Print summary
    print(f"\n📊 Test Summary:")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for failure in failed_tests:
            print(f"  - {failure}")
        return False
    else:
        print(f"\n🎉 All tests passed! Authentication system is working correctly.")
        return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)