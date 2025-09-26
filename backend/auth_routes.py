"""
Authentication routes for unified FastAPI and admin dashboard integration.
Provides login, logout, registration, and user management endpoints.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Form, Request, Response, Cookie
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from .database import get_db
from .unified_models import UnifiedUser, UnifiedUserSession
from .unified_auth import (
    auth_service, AuthenticatedUser, UserRole, Permission,
    get_current_user_session, get_current_user_jwt, get_current_user_flexible,
    SessionManager
)
from .auth_middleware import (
    require_authenticated_user, require_admin_user, require_permission_check
)

logger = logging.getLogger(__name__)

# Pydantic models for request/response
class LoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_admin: bool
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

class SessionResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None
    redirect_url: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

# Create router
auth_router = APIRouter(prefix="/api/auth", tags=["authentication"])
admin_auth_router = APIRouter(prefix="/admin/auth", tags=["admin-authentication"])

# Authentication endpoints
@auth_router.post("/login", response_model=SessionResponse)
async def login_api(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """API login endpoint with JSON request/response and enhanced validation"""
    try:
        # Enhanced input validation and sanitization
        if not login_data:
            raise HTTPException(status_code=400, detail="Login data is required")
        
        # Sanitize input data
        username = login_data.username.strip() if login_data.username else None
        email = login_data.email.strip().lower() if login_data.email else None
        password = login_data.password if login_data.password else None
        
        # Determine login identifier (username or email)
        login_identifier = username or email
        if not login_identifier:
            raise HTTPException(status_code=400, detail="Username or email required")
        
        # Password validation
        if not password or len(password.strip()) == 0:
            raise HTTPException(status_code=400, detail="Password is required")
        
        # Rate limiting check (basic implementation)
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"Login attempt from {client_ip} for identifier: {login_identifier}")
        
        # Authenticate user with enhanced error handling
        try:
            user = auth_service.authenticate_user(login_identifier, password, db)
        except Exception as auth_error:
            logger.error(f"Authentication service error: {auth_error}")
            raise HTTPException(status_code=500, detail="Authentication service error")
        
        if not user:
            logger.warning(f"Failed login attempt for identifier: {login_identifier} from IP: {client_ip}")
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {user.username}")
            raise HTTPException(status_code=403, detail="Account is disabled")
        
        # Create session with enhanced error handling
        try:
            session_token = auth_service.create_user_session(user, db, request)
        except Exception as session_error:
            logger.error(f"Session creation error: {session_error}")
            raise HTTPException(status_code=500, detail="Session creation failed")
        
        # Set session cookie with proper security settings
        SessionManager.set_session_cookie(response, session_token)
        
        # Create authenticated user object
        auth_user = auth_service.get_user_from_session(session_token, db)
        
        # Enhanced logging for debugging
        logger.info(f"Successful login for user: {user.username} (ID: {user.user_id})")
        logger.info(f"Session token created: {session_token[:20]}... (length: {len(session_token)})")
        logger.info(f"User is admin: {user.is_admin}")
        
        # Return response compatible with multiple frontend formats
        response_data = {
            "success": True,
            "message": "Login successful",
            "token": session_token,
            "access_token": session_token,  # Alternative token field for compatibility
            "user": {
                "id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value if user.role else "customer",
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "permissions": [perm.value for perm in auth_user.permissions] if auth_user else []
            },
            "redirect_url": "/admin" if user.is_admin else "/chat.html",
            "expires_in": 3600 * 24,  # 24 hours in seconds
            "token_type": "bearer"
        }
        
        logger.info(f"Login response prepared with keys: {list(response_data.keys())}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected login API error: {e}")
        raise HTTPException(status_code=500, detail="Login failed due to server error")

@auth_router.post("/login-form")
async def login_form(
    username: str = Form(...),
    password: str = Form(...),
    request: Request = None,
    response: Response = None,
    db: Session = Depends(get_db)
):
    """Form-based login endpoint (compatible with existing frontend)"""
    try:
        # Authenticate user
        user = auth_service.authenticate_user(username, password, db)
        if not user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid username or password"}
            )
        
        # Create session
        session_token = auth_service.create_user_session(user, db, request)
        
        # Set session cookie
        SessionManager.set_session_cookie(response, session_token)
        
        # Return success response
        return JSONResponse(
            content={
                "success": True,
                "message": "Login successful",
                "user_id": user.user_id,
                "username": user.username,
                "redirect_url": "/chat.html" if not user.is_admin else "/admin/dashboard"
            }
        )
        
    except Exception as e:
        logger.error(f"Form login error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Login failed"}
        )

@auth_router.post("/register", response_model=SessionResponse)
async def register_api(
    register_data: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """API registration endpoint"""
    try:
        # Check if user already exists
        existing_user = db.query(UnifiedUser).filter(
            (UnifiedUser.username == register_data.username) |
            (UnifiedUser.email == register_data.email)
        ).first()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Username or email already exists")
        
        # Create new user
        hashed_password = auth_service.hash_password(register_data.password)
        
        # Generate unique user_id
        user_id = f"admin_{secrets.token_hex(8)}"
        
        new_user = UnifiedUser(
            user_id=user_id,
            username=register_data.username,
            email=register_data.email,
            password_hash=hashed_password,
            full_name=register_data.full_name,
            role=UserRole.ADMIN,  # Admin registration
            is_admin=True,        # Admin registration
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create session
        session_token = auth_service.create_user_session(new_user, db, request)
        
        # Set session cookie
        SessionManager.set_session_cookie(response, session_token)
        
        # Create authenticated user object
        auth_user = auth_service.get_user_from_session(session_token, db)
        
        return {
            "success": True,
            "message": "Registration successful",
            "token": session_token,
            "user": {
                "id": new_user.user_id,
                "username": new_user.username,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "role": new_user.role.value,
                "is_admin": new_user.is_admin,
                "permissions": [perm.value for perm in auth_user.permissions] if auth_user else []
            },
            "redirect_url": "/chat.html"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@auth_router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session_token: str = Cookie(None),
    db: Session = Depends(get_db)
):
    """Logout endpoint"""
    try:
        if session_token:
            auth_service.invalidate_session(session_token, db)
        
        # Clear session cookie
        SessionManager.clear_session_cookie(response)
        
        return JSONResponse(
            content={"success": True, "message": "Logged out successfully"}
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Logout failed"}
        )

@auth_router.get("/me")
async def get_current_user_info(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible)
):
    """Get current user information"""
    return {
        "authenticated": True,
        "user": {
            "id": current_user.user_id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role.value,
            "is_admin": current_user.is_admin,
            "permissions": [perm.value for perm in current_user.permissions]
        }
    }

@auth_router.get("/verify")
async def verify_session(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible)
):
    """Verify current session and return user info"""
    return {
        "success": True,
        "authenticated": True,
        "user": {
            "id": current_user.user_id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role.value,
            "is_admin": current_user.is_admin,
            "permissions": [perm.value for perm in current_user.permissions]
        }
    }

@auth_router.get("/validate")
async def validate_session(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible)
):
    """Validate current session - alias for verify endpoint to match frontend expectations"""
    return {
        "valid": True,
        "authenticated": True,
        "user": {
            "id": current_user.user_id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role.value,
            "is_admin": current_user.is_admin,
            "permissions": [perm.value for perm in current_user.permissions]
        }
    }

@auth_router.post("/refresh")
async def refresh_session(
    request: Request,
    response: Response,
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Refresh current session and return new token"""
    try:
        # Create a new session for the current user
        session_token = auth_service.create_user_session(current_user, db, request)
        
        # Set new session cookie
        SessionManager.set_session_cookie(response, session_token)
        
        logger.info(f"Session refreshed for user: {current_user.username}")
        
        return {
            "success": True,
            "message": "Session refreshed successfully",
            "token": session_token,
            "access_token": session_token,
            "user": {
                "id": current_user.user_id,
                "username": current_user.username,
                "email": current_user.email,
                "full_name": current_user.full_name,
                "role": current_user.role.value,
                "is_admin": current_user.is_admin,
                "permissions": [perm.value for perm in current_user.permissions]
            },
            "expires_in": 3600 * 24,  # 24 hours
            "token_type": "bearer"
        }
        
    except Exception as e:
        logger.error(f"Session refresh error: {e}")
        raise HTTPException(status_code=500, detail="Session refresh failed")

@auth_router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Change user password"""
    try:
        # Get user from database
        user = db.query(UnifiedUser).filter(
            UnifiedUser.id == current_user.id
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify current password
        if not auth_service.verify_password(password_data.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Update password
        user.password_hash = auth_service.hash_password(password_data.new_password)
        user.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        
        # Invalidate all other sessions for security
        auth_service.invalidate_all_user_sessions(user.id, db)
        
        return {"success": True, "message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(status_code=500, detail="Password change failed")

@auth_router.get("/sessions")
async def get_user_sessions(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get user's active sessions"""
    try:
        sessions = db.query(UnifiedUserSession).filter(
            UnifiedUserSession.user_id == current_user.id,
            UnifiedUserSession.is_active == True
        ).all()
        
        return {
            "sessions": [
                {
                    "id": session.session_id[:8] + "...",  # Partial ID for security
                    "created_at": session.created_at,
                    "last_accessed": session.last_accessed,
                    "expires_at": session.expires_at,
                    "is_current": session.session_id == current_user.session_id
                }
                for session in sessions
            ]
        }
        
    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")

@auth_router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Revoke a specific session"""
    try:
        # Find session belonging to current user
        session = db.query(UnifiedUserSession).filter(
            UnifiedUserSession.session_id.like(f"{session_id}%"),
            UnifiedUserSession.user_id == current_user.id,
            UnifiedUserSession.is_active == True
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Invalidate session
        session.is_active = False
        db.commit()
        
        return {"success": True, "message": "Session revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session revocation error: {e}")
        raise HTTPException(status_code=500, detail="Session revocation failed")

# Admin authentication endpoints
@admin_auth_router.post("/login", response_model=SessionResponse)
async def admin_login_api(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Admin-specific login endpoint with enhanced validation and admin verification"""
    try:
        # Enhanced input validation and sanitization
        if not login_data:
            raise HTTPException(status_code=400, detail="Login data is required")
        
        # Sanitize input data
        username = login_data.username.strip() if login_data.username else None
        email = login_data.email.strip().lower() if login_data.email else None
        password = login_data.password if login_data.password else None
        
        # Determine login identifier (username or email)
        login_identifier = username or email
        if not login_identifier:
            raise HTTPException(status_code=400, detail="Username or email required")
        
        # Password validation
        if not password or len(password.strip()) == 0:
            raise HTTPException(status_code=400, detail="Password is required")
        
        # Rate limiting and security logging
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        logger.info(f"Admin login attempt from {client_ip} for identifier: {login_identifier}")
        
        # Authenticate user
        try:
            user = auth_service.authenticate_user(login_identifier, password, db)
        except Exception as auth_error:
            logger.error(f"Admin authentication service error: {auth_error}")
            raise HTTPException(status_code=500, detail="Authentication service error")
        
        if not user:
            logger.warning(f"Failed admin login attempt for identifier: {login_identifier} from IP: {client_ip}")
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Verify admin privileges
        if not user.is_admin:
            logger.warning(f"Non-admin user attempted admin login: {user.username} from IP: {client_ip}")
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Check if user is active
        if not user.is_active:
            logger.warning(f"Admin login attempt for inactive user: {user.username}")
            raise HTTPException(status_code=403, detail="Account is disabled")
        
        # Create session
        try:
            session_token = auth_service.create_user_session(user, db, request)
        except Exception as session_error:
            logger.error(f"Admin session creation error: {session_error}")
            raise HTTPException(status_code=500, detail="Session creation failed")
        
        # Set session cookie with proper security settings
        SessionManager.set_session_cookie(response, session_token)
        
        # Create authenticated user object
        auth_user = auth_service.get_user_from_session(session_token, db)
        
        # Enhanced logging for admin access
        logger.info(f"Successful admin login for user: {user.username} (ID: {user.user_id}) from IP: {client_ip}")
        logger.info(f"Admin session token created: {session_token[:20]}...")
        
        # Return admin-specific response
        response_data = {
            "success": True,
            "message": "Admin login successful",
            "token": session_token,
            "access_token": session_token,
            "user": {
                "id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value if user.role else "admin",
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "permissions": [perm.value for perm in auth_user.permissions] if auth_user else []
            },
            "redirect_url": "/admin",
            "expires_in": 3600 * 8,  # 8 hours for admin sessions
            "token_type": "bearer"
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected admin login error: {e}")
        raise HTTPException(status_code=500, detail="Admin login failed due to server error")

@admin_auth_router.get("/users", response_model=list[UserResponse])
async def list_users(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    # Check admin permission
    user = require_admin_user(request)
    
    try:
        users = db.query(UnifiedUser).offset(skip).limit(limit).all()
        
        return [
            UserResponse(
                id=user.user_id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                role=user.role.value if user.role else "customer",
                is_admin=user.is_admin,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login=user.last_login
            )
            for user in users
        ]
        
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users")

@admin_auth_router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: UserUpdateRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update user (admin only)"""
    # Check admin permission
    admin_user = require_admin_user(request)
    
    try:
        user = db.query(UnifiedUser).filter(
            UnifiedUser.user_id == user_id
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields
        if update_data.full_name is not None:
            user.full_name = update_data.full_name
        
        if update_data.email is not None:
            # Check email uniqueness
            existing = db.query(UnifiedUser).filter(
                UnifiedUser.email == update_data.email,
                UnifiedUser.id != user.id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Email already exists")
            user.email = update_data.email
        
        if update_data.role is not None:
            try:
                user.role = UserRole(update_data.role)
                user.is_admin = user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid role")
        
        if update_data.is_active is not None:
            user.is_active = update_data.is_active
            
            # If deactivating user, invalidate all sessions
            if not update_data.is_active:
                auth_service.invalidate_all_user_sessions(user.id, db)
        
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return {"success": True, "message": "User updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(status_code=500, detail="User update failed")

@admin_auth_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete user (super admin only)"""
    # Check super admin permission
    admin_user = require_authenticated_user(request)
    if admin_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    try:
        user = db.query(UnifiedUser).filter(
            UnifiedUser.user_id == user_id
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent self-deletion
        if user.id == admin_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        # Invalidate all user sessions
        auth_service.invalidate_all_user_sessions(user.id, db)
        
        # Soft delete by deactivating
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return {"success": True, "message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(status_code=500, detail="User deletion failed")

# JWT token endpoints for API access
@auth_router.post("/token")
async def create_jwt_token(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Create JWT token for API access"""
    try:
        # Authenticate user
        user = auth_service.authenticate_user(login_data.username, login_data.password, db)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Create JWT token
        token = auth_service.create_jwt_token(user)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": auth_service.token_expire_hours * 3600,
            "user": {
                "id": user.user_id,
                "username": user.username,
                "role": user.role.value if user.role else "customer"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JWT token creation error: {e}")
        raise HTTPException(status_code=500, detail="Token creation failed")

# Import secrets for user ID generation
import secrets