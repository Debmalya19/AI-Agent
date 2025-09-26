"""
Authentication middleware for unified FastAPI and admin dashboard integration.
Provides middleware components that work with both session-based and JWT authentication.
"""

import logging
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy.orm import Session

from .database import get_db
from .unified_auth import auth_service, AuthenticatedUser, UserRole, Permission

logger = logging.getLogger(__name__)

class UnifiedAuthMiddleware(BaseHTTPMiddleware):
    """
    Unified authentication middleware that handles both API and web routes.
    Supports both session-based authentication (for web/admin) and JWT (for API).
    """
    
    def __init__(
        self, 
        app: ASGIApp,
        admin_routes_prefix: str = "/admin",
        api_routes_prefix: str = "/api",
        public_routes: list = None,
        require_admin_for_admin_routes: bool = True
    ):
        super().__init__(app)
        self.admin_routes_prefix = admin_routes_prefix
        self.api_routes_prefix = api_routes_prefix
        self.public_routes = public_routes or [
            "/", "/login.html", "/register.html", "/login", "/register", 
            "/static", "/favicon.ico", "/health", "/docs", "/openapi.json"
        ]
        self.require_admin_for_admin_routes = require_admin_for_admin_routes
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through authentication middleware"""
        
        # Skip authentication for public routes
        if self._is_public_route(request.url.path):
            return await call_next(request)
        
        # Get database session
        db = next(get_db())
        try:
            # Attempt to authenticate user
            user = await self._authenticate_request(request, db)
            
            # Handle admin routes
            if request.url.path.startswith(self.admin_routes_prefix):
                return await self._handle_admin_route(request, call_next, user)
            
            # Handle API routes
            elif request.url.path.startswith(self.api_routes_prefix):
                return await self._handle_api_route(request, call_next, user)
            
            # Handle other protected routes
            else:
                return await self._handle_protected_route(request, call_next, user)
                
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Authentication service unavailable"}
            )
        finally:
            db.close()
    
    def _is_public_route(self, path: str) -> bool:
        """Check if route is public and doesn't require authentication"""
        return any(path.startswith(route) for route in self.public_routes)
    
    async def _authenticate_request(self, request: Request, db: Session) -> Optional[AuthenticatedUser]:
        """Attempt to authenticate request using available methods"""
        user = None
        
        # Try session-based authentication first (for web routes)
        session_token = request.cookies.get("session_token")
        if session_token:
            user = auth_service.get_user_from_session(session_token, db)
            if user:
                logger.debug(f"Authenticated user {user.username} via session")
        
        # Try JWT authentication (for API routes)
        if not user:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                user = auth_service.get_user_from_jwt(token, db)
                if user:
                    logger.debug(f"Authenticated user {user.username} via JWT")
        
        return user
    
    async def _handle_admin_route(self, request: Request, call_next: Callable, 
                                 user: Optional[AuthenticatedUser]) -> Response:
        """Handle authentication for admin dashboard routes"""
        
        if not user:
            # Redirect to login for unauthenticated admin access
            if request.method == "GET":
                return RedirectResponse(url="/login.html", status_code=302)
            else:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Authentication required"}
                )
        
        # Check admin permissions if required
        if self.require_admin_for_admin_routes:
            if not user.is_admin and user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                if request.method == "GET":
                    return RedirectResponse(url="/login.html?error=access_denied", status_code=302)
                else:
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Admin access required"}
                    )
        
        # Add user to request state
        request.state.user = user
        return await call_next(request)
    
    async def _handle_api_route(self, request: Request, call_next: Callable,
                               user: Optional[AuthenticatedUser]) -> Response:
        """Handle authentication for API routes"""
        
        if not user:
            return JSONResponse(
                status_code=401,
                content={"error": "Authentication required"}
            )
        
        # Add user to request state
        request.state.user = user
        return await call_next(request)
    
    async def _handle_protected_route(self, request: Request, call_next: Callable,
                                    user: Optional[AuthenticatedUser]) -> Response:
        """Handle authentication for other protected routes"""
        
        if not user:
            # Redirect to login for web routes, return JSON for others
            if request.headers.get("Accept", "").startswith("text/html"):
                return RedirectResponse(url="/login.html", status_code=302)
            else:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Authentication required"}
                )
        
        # Add user to request state
        request.state.user = user
        return await call_next(request)

class PermissionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for checking specific permissions on routes.
    Should be used after UnifiedAuthMiddleware.
    """
    
    def __init__(self, app: ASGIApp, route_permissions: dict = None):
        super().__init__(app)
        # Map of route patterns to required permissions
        self.route_permissions = route_permissions or {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check permissions for specific routes"""
        
        # Get user from request state (set by auth middleware)
        user = getattr(request.state, 'user', None)
        
        # Check if route requires specific permissions
        required_permissions = self._get_required_permissions(request.url.path)
        
        if required_permissions and user:
            missing_permissions = []
            for permission in required_permissions:
                if not user.has_permission(permission):
                    missing_permissions.append(permission.value)
            
            if missing_permissions:
                logger.warning(
                    f"User {user.username} denied access to {request.url.path}. "
                    f"Missing permissions: {missing_permissions}"
                )
                
                if request.headers.get("Accept", "").startswith("text/html"):
                    return RedirectResponse(url="/login.html?error=insufficient_permissions", status_code=302)
                else:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "Insufficient permissions",
                            "required_permissions": missing_permissions
                        }
                    )
        
        return await call_next(request)
    
    def _get_required_permissions(self, path: str) -> list:
        """Get required permissions for a route path"""
        for pattern, permissions in self.route_permissions.items():
            if path.startswith(pattern):
                return permissions
        return []

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware for authentication endpoints.
    """
    
    def __init__(self, app: ASGIApp, max_requests: int = 10, window_seconds: int = 300):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_counts = {}  # In production, use Redis or similar
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to authentication routes"""
        
        # Only apply to auth routes
        if not self._is_auth_route(request.url.path):
            return await call_next(request)
        
        # Get client identifier
        client_ip = request.client.host
        current_time = int(time.time())
        window_start = current_time - self.window_seconds
        
        # Clean old entries
        self.request_counts = {
            ip: [(timestamp, count) for timestamp, count in requests 
                 if timestamp > window_start]
            for ip, requests in self.request_counts.items()
        }
        
        # Count requests in current window
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        current_requests = len(self.request_counts[client_ip])
        
        if current_requests >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Please try again later."}
            )
        
        # Record this request
        self.request_counts[client_ip].append((current_time, 1))
        
        return await call_next(request)
    
    def _is_auth_route(self, path: str) -> bool:
        """Check if route is an authentication endpoint"""
        auth_routes = ["/login", "/register", "/logout", "/api/auth/"]
        return any(path.startswith(route) for route in auth_routes)

# Utility functions for FastAPI route protection
def get_current_user_from_request(request: Request) -> Optional[AuthenticatedUser]:
    """Get current user from request state (set by middleware)"""
    return getattr(request.state, 'user', None)

def require_authenticated_user(request: Request) -> AuthenticatedUser:
    """Require authenticated user, raise exception if not found"""
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

def require_admin_user(request: Request) -> AuthenticatedUser:
    """Require admin user, raise exception if not admin"""
    user = require_authenticated_user(request)
    if not user.is_admin and user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def require_permission_check(request: Request, permission: Permission) -> AuthenticatedUser:
    """Require specific permission, raise exception if not authorized"""
    user = require_authenticated_user(request)
    if not user.has_permission(permission):
        raise HTTPException(
            status_code=403, 
            detail=f"Permission required: {permission.value}"
        )
    return user

# Import time for rate limiting
import time