"""
Admin Dashboard Authentication Proxy
Provides unified authentication endpoints for admin dashboard frontend
"""

from fastapi import APIRouter, HTTPException, Depends, Response, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta

# Import existing authentication components
from .unified_auth import (
    auth_service,
    get_current_user_flexible,
    require_admin_access
)
from .unified_models import UnifiedUser as User, UnifiedUserSession as UserSession
from .database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Create router for authentication endpoints
auth_api_router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None

@auth_api_router.post("/login")
async def admin_login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Admin dashboard login endpoint"""
    try:
        # Authenticate user using unified auth system
        user = auth_service.authenticate_user(login_data.email, login_data.password, db)
        
        if not user:
            raise HTTPException(
                status_code=401, 
                detail="Invalid email or password"
            )
        
        # Check if user has admin access
        if not user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
        
        # Create session token
        session_token = auth_service.create_user_session(user, db)
        
        # Set session cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=86400  # 24 hours
        )
        
        # Update last login time
        user.last_login = datetime.now()
        db.commit()
        
        return {
            "success": True,
            "message": "Login successful",
            "token": session_token,  # Also return in response for localStorage
            "user": {
                "id": user.id,
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_admin": user.is_admin
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@auth_api_router.post("/logout")
async def admin_logout(
    response: Response,
    session_token: str = Cookie(None),
    db: Session = Depends(get_db)
):
    """Admin dashboard logout endpoint"""
    try:
        if session_token:
            # Invalidate session in database
            session = db.query(UserSession).filter(
                UserSession.session_id == session_token
            ).first()
            
            if session:
                session.is_active = False
                session.logout_time = datetime.now()
                db.commit()
        
        # Clear session cookie
        response.delete_cookie("session_token")
        
        return {
            "success": True,
            "message": "Logout successful"
        }
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Still clear cookie even if database update fails
        response.delete_cookie("session_token")
        return {
            "success": True,
            "message": "Logout successful"
        }

@auth_api_router.get("/profile")
async def get_admin_profile(
    current_user: User = Depends(get_current_user_flexible)
):
    """Get current admin user profile"""
    try:
        return {
            "success": True,
            "data": {
                "id": current_user.id,
                "user_id": current_user.user_id,
                "username": current_user.username,
                "email": current_user.email,
                "full_name": current_user.full_name,
                "phone": current_user.phone,
                "is_admin": current_user.is_admin,
                "is_active": current_user.is_active,
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
                "last_login": current_user.last_login.isoformat() if current_user.last_login else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to get profile")

@auth_api_router.put("/profile")
async def update_admin_profile(
    profile_data: Dict[str, Any],
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Update current admin user profile"""
    try:
        # Update allowed fields
        if 'username' in profile_data:
            current_user.username = profile_data['username']
        if 'email' in profile_data:
            current_user.email = profile_data['email']
        if 'full_name' in profile_data:
            current_user.full_name = profile_data['full_name']
        if 'phone' in profile_data:
            current_user.phone = profile_data['phone']
        
        db.commit()
        
        return {
            "success": True,
            "message": "Profile updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update profile")

@auth_api_router.post("/register")
async def admin_register(
    register_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register new admin user (restricted endpoint)"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == register_data.email) | 
            (User.username == register_data.username)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="User with this email or username already exists"
            )
        
        # Create new admin user
        new_user = User(
            user_id=f"admin_{register_data.username}",
            username=register_data.username,
            email=register_data.email,
            full_name=register_data.full_name,
            password_hash=auth_service.hash_password(register_data.password),
            is_admin=True,  # New registrations are admin users
            is_active=True,
            created_at=datetime.now()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "success": True,
            "message": "Admin user registered successfully",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "is_admin": new_user.is_admin
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Registration failed")

@auth_api_router.get("/verify")
async def verify_admin_session(
    current_user: User = Depends(get_current_user_flexible)
):
    """Verify admin session is valid"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return {
            "success": True,
            "valid": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "is_admin": current_user.is_admin
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session verification error: {e}")
        raise HTTPException(status_code=500, detail="Session verification failed")


def setup_admin_auth_proxy(app):
    """Setup admin authentication proxy router"""
    app.include_router(auth_api_router)
    logger.info("Admin authentication proxy router setup completed")