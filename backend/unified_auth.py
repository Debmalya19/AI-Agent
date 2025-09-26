"""
Unified Authentication System
Extends existing FastAPI JWT authentication to support admin dashboard functionality
with role-based access control (RBAC) system and unified session management.
"""

import jwt
import bcrypt
import secrets
import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import logging
from fastapi import HTTPException, Depends, Cookie, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .database import get_db
from .unified_models import UnifiedUser, UnifiedUserSession, UserRole

logger = logging.getLogger(__name__)

# Security scheme for FastAPI
security = HTTPBearer()

# UserRole is imported from unified_models.py

class Permission(Enum):
    """System permissions for fine-grained access control"""
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"
    
    # Ticket management
    TICKET_CREATE = "ticket:create"
    TICKET_READ = "ticket:read"
    TICKET_UPDATE = "ticket:update"
    TICKET_DELETE = "ticket:delete"
    TICKET_LIST = "ticket:list"
    TICKET_ASSIGN = "ticket:assign"
    
    # Comment management
    COMMENT_CREATE = "comment:create"
    COMMENT_READ = "comment:read"
    COMMENT_UPDATE = "comment:update"
    COMMENT_DELETE = "comment:delete"
    
    # Admin dashboard permissions
    DASHBOARD_VIEW = "dashboard:view"
    DASHBOARD_ANALYTICS = "dashboard:analytics"
    DASHBOARD_REPORTS = "dashboard:reports"
    
    # System administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_BACKUP = "system:backup"
    
    # Chat management
    CHAT_VIEW = "chat:view"
    CHAT_MODERATE = "chat:moderate"
    CHAT_ASSIGN = "chat:assign"

# Role-Permission mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.CUSTOMER: {
        Permission.TICKET_CREATE,
        Permission.TICKET_READ,  # Own tickets only
        Permission.COMMENT_CREATE,  # Own tickets only
        Permission.COMMENT_READ,  # Own tickets only
        Permission.CHAT_VIEW,  # Own chats only
    },
    UserRole.AGENT: {
        Permission.TICKET_READ,
        Permission.TICKET_UPDATE,
        Permission.TICKET_LIST,
        Permission.COMMENT_CREATE,
        Permission.COMMENT_READ,
        Permission.COMMENT_UPDATE,
        Permission.CHAT_VIEW,
        Permission.CHAT_MODERATE,
        Permission.USER_READ,  # Limited to assigned customers
        Permission.DASHBOARD_VIEW,
    },
    UserRole.ADMIN: {
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_LIST,
        Permission.TICKET_CREATE,
        Permission.TICKET_READ,
        Permission.TICKET_UPDATE,
        Permission.TICKET_DELETE,
        Permission.TICKET_LIST,
        Permission.TICKET_ASSIGN,
        Permission.COMMENT_CREATE,
        Permission.COMMENT_READ,
        Permission.COMMENT_UPDATE,
        Permission.COMMENT_DELETE,
        Permission.DASHBOARD_VIEW,
        Permission.DASHBOARD_ANALYTICS,
        Permission.DASHBOARD_REPORTS,
        Permission.CHAT_VIEW,
        Permission.CHAT_MODERATE,
        Permission.CHAT_ASSIGN,
        Permission.SYSTEM_CONFIG,
        Permission.SYSTEM_LOGS,
        Permission.SYSTEM_BACKUP,
    },
    UserRole.SUPER_ADMIN: {
        # Super admin has all permissions
        *[perm for perm in Permission],
    }
}

@dataclass
class AuthenticatedUser:
    """Authenticated user data transfer object"""
    id: int
    user_id: str
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    is_admin: bool
    permissions: Set[Permission]
    session_id: str
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions"""
        return any(perm in self.permissions for perm in permissions)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if user has all of the specified permissions"""
        return all(perm in self.permissions for perm in permissions)

class UnifiedAuthService:
    """Unified authentication service for both FastAPI and admin dashboard"""
    
    def __init__(self, jwt_secret: str, jwt_algorithm: str = "HS256", token_expire_hours: int = 24):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.token_expire_hours = token_expire_hours
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def create_jwt_token(self, user: UnifiedUser) -> str:
        """Create JWT token for user"""
        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role.value if user.role else UserRole.CUSTOMER.value,
            "exp": datetime.now(timezone.utc) + timedelta(hours=self.token_expire_hours),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def create_session_token(self) -> str:
        """Create secure session token"""
        return secrets.token_urlsafe(32)
    
    def hash_session_token(self, token: str) -> str:
        """Hash session token for storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def authenticate_user(self, username: str, password: str, db: Session) -> Optional[UnifiedUser]:
        """Authenticate user with username/password with comprehensive error logging"""
        try:
            # Try to find user by user_id, username, or email
            user = db.query(UnifiedUser).filter(
                (UnifiedUser.user_id == username) | 
                (UnifiedUser.username == username) | 
                (UnifiedUser.email == username)
            ).first()
            
            if not user:
                logger.warning(f"Authentication failed - User not found: {username}")
                return None
            
            if not user.is_active:
                logger.warning(f"Authentication failed - Inactive user attempted login: {username} (ID: {user.user_id})")
                return None
            
            if not self.verify_password(password, user.password_hash):
                logger.warning(f"Authentication failed - Invalid password for user: {username} (ID: {user.user_id})")
                return None
            
            # Update last login
            user.last_login = datetime.now(timezone.utc)
            db.commit()
            
            logger.info(f"Authentication successful for user: {username} (ID: {user.user_id})")
            return user
            
        except Exception as e:
            logger.error(f"Authentication system error for user {username}: {e}")
            return None
    
    def create_user_session(self, user: UnifiedUser, db: Session, 
                           request: Optional[Request] = None) -> str:
        """Create new user session and return session token"""
        try:
            # Generate session token
            session_token = self.create_session_token()
            token_hash = self.hash_session_token(session_token)
            
            # Create session record
            session = UnifiedUserSession(
                session_id=session_token,
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=self.token_expire_hours),
                is_active=True
            )
            
            db.add(session)
            db.commit()
            
            logger.info(f"Created session for user {user.username}")
            return session_token
            
        except Exception as e:
            logger.error(f"Session creation error: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Session creation failed")
    
    def get_user_from_session(self, session_token: str, db: Session) -> Optional[AuthenticatedUser]:
        """Get authenticated user from session token"""
        try:
            if not session_token:
                return None
            
            # Find active session
            session = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.session_id == session_token,
                UnifiedUserSession.is_active == True,
                UnifiedUserSession.expires_at > datetime.now(timezone.utc)
            ).first()
            
            if not session:
                return None
            
            # Get user
            user = db.query(UnifiedUser).filter(
                UnifiedUser.id == session.user_id,
                UnifiedUser.is_active == True
            ).first()
            
            if not user:
                return None
            
            # Update last accessed
            session.last_accessed = datetime.now(timezone.utc)
            db.commit()
            
            # Get user permissions based on role
            role = user.role or UserRole.CUSTOMER
            permissions = ROLE_PERMISSIONS.get(role, set())
            
            return AuthenticatedUser(
                id=user.id,
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                role=role,
                is_active=user.is_active,
                is_admin=user.is_admin,
                permissions=permissions,
                session_id=session_token
            )
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None
    
    def get_user_from_jwt(self, token: str, db: Session) -> Optional[AuthenticatedUser]:
        """Get authenticated user from JWT token"""
        try:
            payload = self.verify_jwt_token(token)
            if not payload:
                return None
            
            user = db.query(UnifiedUser).filter(
                UnifiedUser.user_id == payload["user_id"],
                UnifiedUser.is_active == True
            ).first()
            
            if not user:
                return None
            
            # Get user permissions based on role
            role = user.role or UserRole.CUSTOMER
            permissions = ROLE_PERMISSIONS.get(role, set())
            
            return AuthenticatedUser(
                id=user.id,
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                role=role,
                is_active=user.is_active,
                is_admin=user.is_admin,
                permissions=permissions,
                session_id=""  # JWT doesn't have session ID
            )
            
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            return None
    
    def invalidate_session(self, session_token: str, db: Session) -> bool:
        """Invalidate user session"""
        try:
            session = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.session_id == session_token
            ).first()
            
            if session:
                session.is_active = False
                db.commit()
                logger.info(f"Invalidated session: {session_token[:8]}...")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Session invalidation error: {e}")
            return False
    
    def invalidate_all_user_sessions(self, user_id: int, db: Session) -> bool:
        """Invalidate all sessions for a user"""
        try:
            db.query(UnifiedUserSession).filter(
                UnifiedUserSession.user_id == user_id
            ).update({"is_active": False})
            db.commit()
            
            logger.info(f"Invalidated all sessions for user ID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Bulk session invalidation error: {e}")
            return False
    
    def cleanup_expired_sessions(self, db: Session) -> int:
        """Clean up expired sessions"""
        try:
            expired_count = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.expires_at < datetime.now(timezone.utc)
            ).update({"is_active": False})
            
            db.commit()
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")
            return 0

# Global auth service instance
auth_service = UnifiedAuthService(
    jwt_secret=os.getenv("JWT_SECRET", "your-secret-key-change-in-production"),
    jwt_algorithm="HS256",
    token_expire_hours=24
)

# Dependency functions for FastAPI
async def get_current_user_session(
    session_token: str = Cookie(None),
    db: Session = Depends(get_db)
) -> AuthenticatedUser:
    """FastAPI dependency to get current user from session cookie"""
    if not session_token:
        raise HTTPException(status_code=401, detail="No session token provided")
    
    user = auth_service.get_user_from_session(session_token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user

async def get_current_user_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AuthenticatedUser:
    """FastAPI dependency to get current user from JWT token"""
    if not credentials:
        raise HTTPException(status_code=401, detail="No authorization token provided")
    
    user = auth_service.get_user_from_jwt(credentials.credentials, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user

async def get_optional_bearer_token(
    authorization: Optional[str] = Header(None)
) -> Optional[HTTPAuthorizationCredentials]:
    """Optional bearer token extraction"""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return None

async def get_current_user_flexible(
    session_token: str = Cookie(None),
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_optional_bearer_token)
) -> AuthenticatedUser:
    """FastAPI dependency that accepts either session cookie or JWT token"""
    user = None
    
    # Try session token first
    if session_token:
        user = auth_service.get_user_from_session(session_token, db)
    
    # Try JWT token if session failed and credentials provided
    if not user and credentials:
        user = auth_service.get_user_from_jwt(credentials.credentials, db)
    
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    return user

# Alias for admin dashboard compatibility
async def get_current_user(
    session_token: str = Cookie(None),
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_optional_bearer_token)
) -> AuthenticatedUser:
    """Alias for get_current_user_flexible for admin dashboard compatibility"""
    return await get_current_user_flexible(session_token, db, credentials)

def require_admin_access(user: AuthenticatedUser):
    """Function to require admin access - raises HTTPException if not admin"""
    if not user.is_admin and user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

def require_admin_role(user: AuthenticatedUser):
    """Function to require admin role - raises HTTPException if not admin (alias for require_admin_access)"""
    require_admin_access(user)

def setup_admin_authentication():
    """Setup admin authentication - placeholder for initialization"""
    logger.info("Admin authentication setup completed")

def require_permission(permission: Permission):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (should be injected by dependency)
            user = kwargs.get('current_user')
            if not user or not isinstance(user, AuthenticatedUser):
                raise HTTPException(status_code=401, detail="Authentication required")
            
            if not user.has_permission(permission):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Permission required: {permission.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(role: UserRole):
    """Decorator to require specific role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (should be injected by dependency)
            user = kwargs.get('current_user')
            if not user or not isinstance(user, AuthenticatedUser):
                raise HTTPException(status_code=401, detail="Authentication required")
            
            if user.role != role:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Role required: {role.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_admin():
    """Decorator to require admin role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (should be injected by dependency)
            user = kwargs.get('current_user')
            if not user or not isinstance(user, AuthenticatedUser):
                raise HTTPException(status_code=401, detail="Authentication required")
            
            if not user.is_admin and user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                raise HTTPException(status_code=403, detail="Admin access required")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Authentication middleware for admin dashboard routes
class AdminAuthMiddleware:
    """Authentication middleware for admin dashboard routes"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Check if this is an admin dashboard route
            if request.url.path.startswith("/admin/"):
                # Get session token from cookie
                session_token = request.cookies.get("session_token")
                
                if not session_token:
                    # Redirect to login for admin routes
                    response = RedirectResponse(url="/login.html", status_code=302)
                    await response(scope, receive, send)
                    return
                
                # Validate session
                db = next(get_db())
                try:
                    user = auth_service.get_user_from_session(session_token, db)
                    if not user or not user.is_admin:
                        # Redirect to login for invalid/non-admin sessions
                        response = RedirectResponse(url="/login.html", status_code=302)
                        await response(scope, receive, send)
                        return
                    
                    # Add user to request state
                    scope["user"] = user
                    
                finally:
                    db.close()
        
        await self.app(scope, receive, send)

# Session management utilities
class SessionManager:
    """Utilities for managing user sessions"""
    
    @staticmethod
    def create_session_response(session_token: str, user: AuthenticatedUser, 
                              redirect_url: str = "/chat.html") -> Dict[str, Any]:
        """Create standardized session response"""
        return {
            "success": True,
            "message": "Authentication successful",
            "user": {
                "id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "is_admin": user.is_admin,
                "permissions": [perm.value for perm in user.permissions]
            },
            "session_token": session_token,
            "redirect_url": redirect_url
        }
    
    @staticmethod
    def set_session_cookie(response, session_token: str, max_age: int = 86400):
        """Set session cookie on response"""
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=max_age,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
    
    @staticmethod
    def clear_session_cookie(response):
        """Clear session cookie from response"""
        response.delete_cookie(
            key="session_token",
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
    
    @staticmethod
    def clear_session_cookie(response):
        """Clear session cookie"""
        response.delete_cookie(key="session_token")

from fastapi.responses import RedirectResponse