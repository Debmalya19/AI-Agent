"""
Comprehensive tests for the unified authentication system.
Tests authentication, authorization, session management, and middleware functionality.
"""

import pytest
import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .database import Base, get_db
from .unified_models import UnifiedUser, UnifiedUserSession
from .unified_auth import (
    UnifiedAuthService, AuthenticatedUser, UserRole, Permission,
    ROLE_PERMISSIONS, auth_service
)
from .session_utils import SessionUtils, SessionSecurity
from .auth_middleware import UnifiedAuthMiddleware
from .auth_routes import auth_router

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def auth_service_instance():
    """Create auth service instance for testing"""
    return UnifiedAuthService(
        jwt_secret="test-secret-key",
        jwt_algorithm="HS256",
        token_expire_hours=1
    )

@pytest.fixture
def test_user(db_session, auth_service_instance):
    """Create a test user"""
    user = UnifiedUser(
        user_id="test_user_123",
        username="testuser",
        email="test@example.com",
        password_hash=auth_service_instance.hash_password("testpassword"),
        full_name="Test User",
        role=UserRole.CUSTOMER,
        is_admin=False,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def admin_user(db_session, auth_service_instance):
    """Create an admin test user"""
    user = UnifiedUser(
        user_id="admin_user_123",
        username="adminuser",
        email="admin@example.com",
        password_hash=auth_service_instance.hash_password("adminpassword"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_admin=True,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

class TestUnifiedAuthService:
    """Test the unified authentication service"""
    
    def test_password_hashing(self, auth_service_instance):
        """Test password hashing and verification"""
        password = "test_password_123"
        hashed = auth_service_instance.hash_password(password)
        
        assert hashed != password
        assert auth_service_instance.verify_password(password, hashed)
        assert not auth_service_instance.verify_password("wrong_password", hashed)
    
    def test_jwt_token_creation_and_verification(self, auth_service_instance, test_user):
        """Test JWT token creation and verification"""
        token = auth_service_instance.create_jwt_token(test_user)
        
        assert token is not None
        assert isinstance(token, str)
        
        payload = auth_service_instance.verify_jwt_token(token)
        assert payload is not None
        assert payload["user_id"] == test_user.user_id
        assert payload["username"] == test_user.username
    
    def test_jwt_token_expiration(self, auth_service_instance, test_user):
        """Test JWT token expiration"""
        # Create service with very short expiration
        short_auth_service = UnifiedAuthService(
            jwt_secret="test-secret",
            token_expire_hours=0.001  # Very short expiration
        )
        
        token = short_auth_service.create_jwt_token(test_user)
        
        # Wait for token to expire
        import time
        time.sleep(0.1)
        
        payload = short_auth_service.verify_jwt_token(token)
        assert payload is None  # Should be expired
    
    def test_user_authentication(self, auth_service_instance, test_user, db_session):
        """Test user authentication with username/password"""
        # Test successful authentication
        authenticated_user = auth_service_instance.authenticate_user(
            "testuser", "testpassword", db_session
        )
        assert authenticated_user is not None
        assert authenticated_user.username == test_user.username
        
        # Test authentication with email
        authenticated_user = auth_service_instance.authenticate_user(
            "test@example.com", "testpassword", db_session
        )
        assert authenticated_user is not None
        
        # Test failed authentication
        failed_user = auth_service_instance.authenticate_user(
            "testuser", "wrongpassword", db_session
        )
        assert failed_user is None
        
        # Test non-existent user
        failed_user = auth_service_instance.authenticate_user(
            "nonexistent", "password", db_session
        )
        assert failed_user is None
    
    def test_session_creation_and_validation(self, auth_service_instance, test_user, db_session):
        """Test session creation and validation"""
        # Create session
        session_token = auth_service_instance.create_user_session(test_user, db_session)
        
        assert session_token is not None
        assert isinstance(session_token, str)
        
        # Validate session
        auth_user = auth_service_instance.get_user_from_session(session_token, db_session)
        
        assert auth_user is not None
        assert isinstance(auth_user, AuthenticatedUser)
        assert auth_user.username == test_user.username
        assert auth_user.user_id == test_user.user_id
        assert auth_user.role == test_user.role
    
    def test_session_invalidation(self, auth_service_instance, test_user, db_session):
        """Test session invalidation"""
        # Create session
        session_token = auth_service_instance.create_user_session(test_user, db_session)
        
        # Verify session is valid
        auth_user = auth_service_instance.get_user_from_session(session_token, db_session)
        assert auth_user is not None
        
        # Invalidate session
        result = auth_service_instance.invalidate_session(session_token, db_session)
        assert result is True
        
        # Verify session is no longer valid
        auth_user = auth_service_instance.get_user_from_session(session_token, db_session)
        assert auth_user is None

class TestRoleBasedAccessControl:
    """Test role-based access control system"""
    
    def test_role_permissions(self):
        """Test role permission mappings"""
        # Test customer permissions
        customer_perms = ROLE_PERMISSIONS[UserRole.CUSTOMER]
        assert Permission.TICKET_CREATE in customer_perms
        assert Permission.TICKET_READ in customer_perms
        assert Permission.USER_DELETE not in customer_perms
        
        # Test admin permissions
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        assert Permission.USER_CREATE in admin_perms
        assert Permission.TICKET_ASSIGN in admin_perms
        assert Permission.DASHBOARD_VIEW in admin_perms
        
        # Test super admin has all permissions
        super_admin_perms = ROLE_PERMISSIONS[UserRole.SUPER_ADMIN]
        assert len(super_admin_perms) == len(list(Permission))
    
    def test_authenticated_user_permissions(self, auth_service_instance, test_user, admin_user, db_session):
        """Test AuthenticatedUser permission checking"""
        # Create customer session
        customer_token = auth_service_instance.create_user_session(test_user, db_session)
        customer_auth = auth_service_instance.get_user_from_session(customer_token, db_session)
        
        # Test customer permissions
        assert customer_auth.has_permission(Permission.TICKET_CREATE)
        assert not customer_auth.has_permission(Permission.USER_DELETE)
        assert customer_auth.has_any_permission([Permission.TICKET_CREATE, Permission.USER_DELETE])
        assert not customer_auth.has_all_permissions([Permission.TICKET_CREATE, Permission.USER_DELETE])
        
        # Create admin session
        admin_token = auth_service_instance.create_user_session(admin_user, db_session)
        admin_auth = auth_service_instance.get_user_from_session(admin_token, db_session)
        
        # Test admin permissions
        assert admin_auth.has_permission(Permission.USER_CREATE)
        assert admin_auth.has_permission(Permission.DASHBOARD_VIEW)
        assert admin_auth.has_all_permissions([Permission.TICKET_CREATE, Permission.USER_READ])

class TestSessionUtils:
    """Test session management utilities"""
    
    def test_session_count(self, auth_service_instance, test_user, db_session):
        """Test active session counting"""
        # Initially no sessions
        count = SessionUtils.get_active_sessions_count(test_user.id, db_session)
        assert count == 0
        
        # Create sessions
        session1 = auth_service_instance.create_user_session(test_user, db_session)
        session2 = auth_service_instance.create_user_session(test_user, db_session)
        
        count = SessionUtils.get_active_sessions_count(test_user.id, db_session)
        assert count == 2
        
        # Invalidate one session
        auth_service_instance.invalidate_session(session1, db_session)
        
        count = SessionUtils.get_active_sessions_count(test_user.id, db_session)
        assert count == 1
    
    def test_session_cleanup(self, auth_service_instance, test_user, db_session):
        """Test session cleanup functionality"""
        # Create session
        session_token = auth_service_instance.create_user_session(test_user, db_session)
        
        # Manually expire the session
        session = db_session.query(UnifiedUserSession).filter(
            UnifiedUserSession.session_id == session_token
        ).first()
        session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()
        
        # Run cleanup
        cleaned_count = SessionUtils.cleanup_expired_sessions(db_session)
        assert cleaned_count >= 1
        
        # Verify session is no longer valid
        auth_user = auth_service_instance.get_user_from_session(session_token, db_session)
        assert auth_user is None
    
    def test_session_extension(self, auth_service_instance, test_user, db_session):
        """Test session extension"""
        # Create session
        session_token = auth_service_instance.create_user_session(test_user, db_session)
        
        # Get original expiration
        session = db_session.query(UnifiedUserSession).filter(
            UnifiedUserSession.session_id == session_token
        ).first()
        original_expiration = session.expires_at
        
        # Extend session
        result = SessionUtils.extend_session(session_token, db_session, extend_hours=2)
        assert result is True
        
        # Verify extension
        db_session.refresh(session)
        assert session.expires_at > original_expiration
    
    def test_session_limit_enforcement(self, auth_service_instance, test_user, db_session):
        """Test session limit enforcement"""
        # Create more sessions than the limit
        sessions = []
        for i in range(7):  # Assuming limit is 5
            session_token = auth_service_instance.create_user_session(test_user, db_session)
            sessions.append(session_token)
        
        # Enforce limit
        result = SessionUtils.enforce_session_limit(test_user.id, db_session)
        assert result is True
        
        # Verify limit is enforced
        active_count = SessionUtils.get_active_sessions_count(test_user.id, db_session)
        assert active_count <= SessionUtils.get_concurrent_sessions_limit()

class TestSessionSecurity:
    """Test session security features"""
    
    def test_suspicious_activity_detection(self, auth_service_instance, test_user, db_session):
        """Test detection of suspicious session activity"""
        # Create many sessions to trigger detection
        for i in range(12):
            auth_service_instance.create_user_session(test_user, db_session)
        
        # Check for suspicious activity
        activities = SessionSecurity.detect_suspicious_activity(test_user.id, db_session)
        
        assert len(activities) > 0
        assert any(activity["type"] == "excessive_sessions" for activity in activities)
    
    def test_force_user_logout(self, auth_service_instance, test_user, db_session):
        """Test force logout functionality"""
        # Create sessions
        session1 = auth_service_instance.create_user_session(test_user, db_session)
        session2 = auth_service_instance.create_user_session(test_user, db_session)
        
        # Verify sessions are active
        assert auth_service_instance.get_user_from_session(session1, db_session) is not None
        assert auth_service_instance.get_user_from_session(session2, db_session) is not None
        
        # Force logout
        result = SessionSecurity.force_user_logout(test_user.id, "Security test", db_session)
        assert result is True
        
        # Verify all sessions are invalidated
        assert auth_service_instance.get_user_from_session(session1, db_session) is None
        assert auth_service_instance.get_user_from_session(session2, db_session) is None

class TestAuthMiddleware:
    """Test authentication middleware"""
    
    @pytest.fixture
    def mock_app(self):
        """Create mock ASGI app"""
        async def app(scope, receive, send):
            response = {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            }
            await send(response)
            await send({"type": "http.response.body", "body": b'{"message": "success"}'})
        return app
    
    @pytest.fixture
    def auth_middleware(self, mock_app):
        """Create auth middleware instance"""
        return UnifiedAuthMiddleware(mock_app)
    
    def test_public_route_access(self, auth_middleware):
        """Test access to public routes without authentication"""
        # This would require more complex ASGI testing setup
        # For now, test the route checking logic
        assert auth_middleware._is_public_route("/")
        assert auth_middleware._is_public_route("/login.html")
        assert auth_middleware._is_public_route("/static/css/style.css")
        assert not auth_middleware._is_public_route("/admin/dashboard")
        assert not auth_middleware._is_public_route("/api/users")

@pytest.mark.asyncio
class TestAuthRoutes:
    """Test authentication API routes"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(auth_router)
        app.dependency_overrides[get_db] = override_get_db
        return TestClient(app)
    
    def test_login_endpoint(self, client, test_user, db_session):
        """Test login API endpoint"""
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpassword"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "user" in data
        assert data["user"]["username"] == "testuser"
    
    def test_login_invalid_credentials(self, client, test_user, db_session):
        """Test login with invalid credentials"""
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
    
    def test_jwt_token_creation(self, client, test_user, db_session):
        """Test JWT token creation endpoint"""
        response = client.post(
            "/api/auth/token",
            json={"username": "testuser", "password": "testpassword"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

class TestIntegrationScenarios:
    """Test complete integration scenarios"""
    
    def test_complete_auth_flow(self, auth_service_instance, db_session):
        """Test complete authentication flow"""
        # 1. Create user
        user = UnifiedUser(
            user_id="integration_user",
            username="integrationuser",
            email="integration@example.com",
            password_hash=auth_service_instance.hash_password("password123"),
            role=UserRole.CUSTOMER,
            is_admin=False,
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        
        # 2. Authenticate user
        auth_user = auth_service_instance.authenticate_user(
            "integrationuser", "password123", db_session
        )
        assert auth_user is not None
        
        # 3. Create session
        session_token = auth_service_instance.create_user_session(auth_user, db_session)
        assert session_token is not None
        
        # 4. Validate session
        validated_user = auth_service_instance.get_user_from_session(session_token, db_session)
        assert validated_user is not None
        assert validated_user.username == "integrationuser"
        
        # 5. Check permissions
        assert validated_user.has_permission(Permission.TICKET_CREATE)
        assert not validated_user.has_permission(Permission.USER_DELETE)
        
        # 6. Create JWT token
        jwt_token = auth_service_instance.create_jwt_token(auth_user)
        assert jwt_token is not None
        
        # 7. Validate JWT
        jwt_user = auth_service_instance.get_user_from_jwt(jwt_token, db_session)
        assert jwt_user is not None
        assert jwt_user.username == "integrationuser"
        
        # 8. Logout (invalidate session)
        result = auth_service_instance.invalidate_session(session_token, db_session)
        assert result is True
        
        # 9. Verify session is invalid
        invalid_user = auth_service_instance.get_user_from_session(session_token, db_session)
        assert invalid_user is None
    
    def test_admin_user_workflow(self, auth_service_instance, admin_user, db_session):
        """Test admin user workflow"""
        # Create session for admin
        session_token = auth_service_instance.create_user_session(admin_user, db_session)
        auth_admin = auth_service_instance.get_user_from_session(session_token, db_session)
        
        # Verify admin permissions
        assert auth_admin.is_admin
        assert auth_admin.role == UserRole.ADMIN
        assert auth_admin.has_permission(Permission.USER_CREATE)
        assert auth_admin.has_permission(Permission.DASHBOARD_VIEW)
        assert auth_admin.has_permission(Permission.TICKET_ASSIGN)
        
        # Test admin can manage other users (permission-wise)
        assert auth_admin.has_permission(Permission.USER_UPDATE)
        assert auth_admin.has_permission(Permission.USER_LIST)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])