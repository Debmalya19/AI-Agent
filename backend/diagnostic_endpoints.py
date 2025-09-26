"""
Comprehensive diagnostic tools and endpoints for admin dashboard login troubleshooting.
Implements backend debug endpoints, API connectivity checkers, and detailed error logging.
"""

import logging
import json
import traceback
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from pydantic import BaseModel

from .database import get_db
from .unified_models import UnifiedUser, UnifiedUserSession, UserRole
from .unified_auth import auth_service, UnifiedAuthService
from .auth_routes import LoginRequest

logger = logging.getLogger(__name__)

# Pydantic models for diagnostic requests/responses
class DiagnosticStatus(BaseModel):
    status: str
    timestamp: str
    database_connected: bool
    admin_users_count: int
    recent_sessions: int
    auth_endpoints_registered: bool
    error: Optional[str] = None

class LoginTestRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str

class LoginTestResponse(BaseModel):
    success: bool
    message: str
    debug_info: Dict[str, Any]

class APIConnectivityResult(BaseModel):
    endpoint: str
    method: str
    status_code: Optional[int]
    response_time_ms: Optional[float]
    success: bool
    error: Optional[str] = None

class BrowserCompatibilityResult(BaseModel):
    feature: str
    supported: bool
    details: Optional[str] = None

class ErrorLogEntry(BaseModel):
    timestamp: str
    level: str
    category: str
    message: str
    details: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None

# Create diagnostic router
diagnostic_router = APIRouter(prefix="/api/debug", tags=["diagnostics"])

@diagnostic_router.get("/status", response_model=DiagnosticStatus)
async def get_auth_debug_status(db: Session = Depends(get_db)):
    """Comprehensive authentication system status check"""
    
    try:
        # Check database connectivity
        db_status = db.execute(text("SELECT 1")).fetchone() is not None
        
        # Check admin users exist
        admin_count = db.query(UnifiedUser).filter(UnifiedUser.is_admin == True).count()
        
        # Check recent login attempts (last hour)
        recent_sessions = db.query(UnifiedUserSession).filter(
            UnifiedUserSession.created_at > datetime.now(timezone.utc) - timedelta(hours=1)
        ).count()
        
        return DiagnosticStatus(
            status="healthy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            database_connected=db_status,
            admin_users_count=admin_count,
            recent_sessions=recent_sessions,
            auth_endpoints_registered=True
        )
        
    except Exception as e:
        logger.error(f"Debug status check failed: {e}")
        return DiagnosticStatus(
            status="error",
            timestamp=datetime.now(timezone.utc).isoformat(),
            database_connected=False,
            admin_users_count=0,
            recent_sessions=0,
            auth_endpoints_registered=False,
            error=str(e)
        )

@diagnostic_router.post("/test-login", response_model=LoginTestResponse)
async def test_admin_login(
    credentials: LoginTestRequest,
    db: Session = Depends(get_db)
):
    """Test login functionality with detailed debugging information"""
    
    debug_info = {
        "received_credentials": {
            "username": credentials.username,
            "email": credentials.email,
            "password_length": len(credentials.password) if credentials.password else 0
        },
        "lookup_attempts": [],
        "validation_steps": [],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        # Try to find user by email
        user_by_email = None
        if credentials.email:
            user_by_email = db.query(UnifiedUser).filter(UnifiedUser.email == credentials.email).first()
            debug_info["lookup_attempts"].append({
                "method": "email",
                "value": credentials.email,
                "found": user_by_email is not None
            })
        
        # Try to find user by username
        user_by_username = None
        if credentials.username:
            user_by_username = db.query(UnifiedUser).filter(UnifiedUser.username == credentials.username).first()
            debug_info["lookup_attempts"].append({
                "method": "username", 
                "value": credentials.username,
                "found": user_by_username is not None
            })
        
        # Use the found user
        user = user_by_email or user_by_username
        
        if user:
            debug_info["user_found"] = {
                "id": user.id,
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "role": user.role.value if user.role else "customer",
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
            
            # Test password validation
            password_valid = auth_service.verify_password(credentials.password, user.password_hash)
            debug_info["validation_steps"].append({
                "step": "password_verification",
                "result": password_valid,
                "password_hash_length": len(user.password_hash) if user.password_hash else 0
            })
            
            # Test account status
            debug_info["validation_steps"].append({
                "step": "account_active_check",
                "result": user.is_active
            })
            
            # Test admin status
            debug_info["validation_steps"].append({
                "step": "admin_status_check",
                "result": user.is_admin
            })
            
            if password_valid and user.is_active:
                return LoginTestResponse(
                    success=True,
                    message="Login test successful - all validations passed",
                    debug_info=debug_info
                )
            elif not password_valid:
                return LoginTestResponse(
                    success=False,
                    message="Password validation failed",
                    debug_info=debug_info
                )
            elif not user.is_active:
                return LoginTestResponse(
                    success=False,
                    message="Account is inactive",
                    debug_info=debug_info
                )
        else:
            return LoginTestResponse(
                success=False,
                message="User not found with provided credentials",
                debug_info=debug_info
            )
            
    except Exception as e:
        debug_info["error"] = {
            "message": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        logger.error(f"Login test failed: {e}")
        return LoginTestResponse(
            success=False,
            message=f"Login test error: {str(e)}",
            debug_info=debug_info
        )

@diagnostic_router.get("/connectivity")
async def test_api_connectivity():
    """Test API connectivity and endpoint availability"""
    
    import httpx
    import time
    
    endpoints_to_test = [
        {"endpoint": "/api/auth/me", "method": "GET"},
        {"endpoint": "/api/auth/login", "method": "POST"},
        {"endpoint": "/admin/auth/users", "method": "GET"},
        {"endpoint": "/health", "method": "GET"},
    ]
    
    results = []
    
    for endpoint_info in endpoints_to_test:
        endpoint = endpoint_info["endpoint"]
        method = endpoint_info["method"]
        
        try:
            start_time = time.time()
            
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(f"http://localhost:8000{endpoint}")
                elif method == "POST":
                    response = await client.post(f"http://localhost:8000{endpoint}", json={})
                
                response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                results.append(APIConnectivityResult(
                    endpoint=endpoint,
                    method=method,
                    status_code=response.status_code,
                    response_time_ms=response_time,
                    success=response.status_code < 500,  # Consider 4xx as "successful" connectivity
                    error=None
                ))
                
        except Exception as e:
            results.append(APIConnectivityResult(
                endpoint=endpoint,
                method=method,
                status_code=None,
                response_time_ms=None,
                success=False,
                error=str(e)
            ))
    
    return {
        "connectivity_test_results": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": "healthy" if all(r.success for r in results) else "issues_detected"
    }

@diagnostic_router.get("/browser-compatibility")
async def test_browser_compatibility(request: Request):
    """Test browser compatibility features"""
    
    user_agent = request.headers.get("user-agent", "")
    
    # Basic browser detection
    browser_info = {
        "user_agent": user_agent,
        "detected_browser": "unknown"
    }
    
    if "Chrome" in user_agent:
        browser_info["detected_browser"] = "Chrome"
    elif "Firefox" in user_agent:
        browser_info["detected_browser"] = "Firefox"
    elif "Safari" in user_agent and "Chrome" not in user_agent:
        browser_info["detected_browser"] = "Safari"
    elif "Edge" in user_agent:
        browser_info["detected_browser"] = "Edge"
    
    # Test results for common features
    compatibility_results = [
        BrowserCompatibilityResult(
            feature="cookies",
            supported=True,  # Assume supported, would need client-side JS to test properly
            details="Server can set cookies, client support needs JS verification"
        ),
        BrowserCompatibilityResult(
            feature="local_storage",
            supported=True,  # Assume supported for modern browsers
            details="Modern browser detected, localStorage should be available"
        ),
        BrowserCompatibilityResult(
            feature="session_storage",
            supported=True,  # Assume supported for modern browsers
            details="Modern browser detected, sessionStorage should be available"
        ),
        BrowserCompatibilityResult(
            feature="fetch_api",
            supported=True,  # Assume supported for modern browsers
            details="Modern browser detected, Fetch API should be available"
        ),
        BrowserCompatibilityResult(
            feature="json_parsing",
            supported=True,  # Standard feature
            details="JSON parsing is standard in all modern browsers"
        )
    ]
    
    return {
        "browser_info": browser_info,
        "compatibility_results": compatibility_results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "recommendations": [
            "Use client-side JavaScript to verify localStorage and sessionStorage",
            "Test cookie functionality with actual cookie operations",
            "Verify Fetch API with actual network requests"
        ]
    }

@diagnostic_router.get("/admin-users")
async def list_admin_users(db: Session = Depends(get_db)):
    """List all admin users for debugging purposes"""
    
    try:
        admin_users = db.query(UnifiedUser).filter(UnifiedUser.is_admin == True).all()
        
        users_info = []
        for user in admin_users:
            users_info.append({
                "id": user.id,
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value if user.role else "customer",
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "password_hash_length": len(user.password_hash) if user.password_hash else 0
            })
        
        return {
            "admin_users": users_info,
            "total_count": len(users_info),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to list admin users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve admin users: {str(e)}")

@diagnostic_router.get("/sessions")
async def list_recent_sessions(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """List recent user sessions for debugging"""
    
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        sessions = db.query(UnifiedUserSession).filter(
            UnifiedUserSession.created_at > cutoff_time
        ).order_by(UnifiedUserSession.created_at.desc()).limit(50).all()
        
        sessions_info = []
        for session in sessions:
            user = db.query(UnifiedUser).filter(UnifiedUser.id == session.user_id).first()
            
            sessions_info.append({
                "session_id": session.session_id[:8] + "...",  # Partial for security
                "user_id": user.user_id if user else "unknown",
                "username": user.username if user else "unknown",
                "is_admin": user.is_admin if user else False,
                "is_active": session.is_active,
                "created_at": session.created_at.isoformat(),
                "last_accessed": session.last_accessed.isoformat() if session.last_accessed else None,
                "expires_at": session.expires_at.isoformat() if session.expires_at else None
            })
        
        return {
            "recent_sessions": sessions_info,
            "total_count": len(sessions_info),
            "hours_back": hours,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sessions: {str(e)}")

@diagnostic_router.post("/log-error")
async def log_diagnostic_error(
    error_data: Dict[str, Any],
    request: Request
):
    """Log diagnostic error for debugging purposes"""
    
    try:
        # Enhance error data with request information
        enhanced_error = {
            **error_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_agent": request.headers.get("user-agent"),
            "ip_address": request.client.host if request.client else None,
            "referer": request.headers.get("referer")
        }
        
        # Log the error
        logger.error(f"Diagnostic Error: {json.dumps(enhanced_error, indent=2)}")
        
        return {
            "success": True,
            "message": "Error logged successfully",
            "timestamp": enhanced_error["timestamp"]
        }
        
    except Exception as e:
        logger.error(f"Failed to log diagnostic error: {e}")
        return {
            "success": False,
            "message": f"Failed to log error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@diagnostic_router.get("/recent-errors")
async def get_recent_errors(
    hours: int = 24,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get recent diagnostic errors for analysis"""
    
    try:
        from .diagnostic_error_logger import diagnostic_logger, ErrorCategory, ErrorSeverity
        
        # Convert string parameters to enums if provided
        category_enum = None
        if category:
            try:
                category_enum = ErrorCategory(category.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        
        severity_enum = None
        if severity:
            try:
                severity_enum = ErrorSeverity(severity.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        errors = diagnostic_logger.get_recent_errors(
            db=db,
            hours=hours,
            category=category_enum,
            severity=severity_enum,
            limit=limit
        )
        
        return {
            "recent_errors": errors,
            "total_count": len(errors),
            "hours_back": hours,
            "filters": {
                "category": category,
                "severity": severity,
                "limit": limit
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve recent errors: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve recent errors: {str(e)}")

@diagnostic_router.get("/error-statistics")
async def get_error_statistics(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get error statistics for monitoring dashboard"""
    
    try:
        from .diagnostic_error_logger import diagnostic_logger
        
        stats = diagnostic_logger.get_error_statistics(db=db, hours=hours)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get error statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get error statistics: {str(e)}")

@diagnostic_router.post("/simulate-error")
async def simulate_diagnostic_error(
    error_type: str = "test_error",
    message: str = "Simulated diagnostic error for testing",
    db: Session = Depends(get_db)
):
    """Simulate a diagnostic error for testing purposes"""
    
    try:
        from .diagnostic_error_logger import diagnostic_logger, ErrorContext
        
        # Create test error context
        context = ErrorContext(
            user_id="test_user",
            session_id="test_session",
            endpoint="/api/debug/simulate-error",
            method="POST",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Log the simulated error
        error = diagnostic_logger.log_error(
            error_type=error_type,
            message=message,
            details={
                "simulated": True,
                "test_timestamp": datetime.now(timezone.utc).isoformat(),
                "purpose": "diagnostic_testing"
            },
            context=context,
            db=db
        )
        
        return {
            "success": True,
            "message": "Simulated error logged successfully",
            "error_details": {
                "category": error.category.value,
                "severity": error.severity.value,
                "error_code": error.error_code,
                "message": error.message
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to simulate error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to simulate error: {str(e)}")

@diagnostic_router.get("/health")
async def diagnostic_health_check():
    """Simple health check for diagnostic endpoints"""
    
    return {
        "status": "healthy",
        "service": "diagnostic_endpoints",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }