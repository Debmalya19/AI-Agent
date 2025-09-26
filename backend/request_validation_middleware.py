"""
Request Validation and Sanitization Middleware
Provides comprehensive request validation, sanitization, and security checks
"""

import logging
import json
import re
from typing import Dict, Any, Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import html

logger = logging.getLogger(__name__)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation, sanitization, and security"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Security patterns to detect potential attacks
        self.security_patterns = [
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'on\w+\s*=', re.IGNORECASE),
            re.compile(r'(union|select|insert|update|delete|drop|create|alter)\s+', re.IGNORECASE),
            re.compile(r'(\.\./|\.\.\\)', re.IGNORECASE),
        ]
        
        # Rate limiting storage (simple in-memory for demo)
        self.request_counts: Dict[str, Dict[str, int]] = {}
        self.max_requests_per_minute = 60
        self.max_login_attempts_per_minute = 5
    
    async def dispatch(self, request: Request, call_next):
        """Process request through validation and sanitization"""
        
        try:
            # Skip validation for static files and health checks
            if self._should_skip_validation(request):
                return await call_next(request)
            
            # Rate limiting
            if not self._check_rate_limit(request):
                logger.warning(f"Rate limit exceeded for IP: {request.client.host}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please try again later."}
                )
            
            # Validate and sanitize request
            await self._validate_request(request)
            
            # Process request
            response = await call_next(request)
            
            # Add security headers to response
            self._add_security_headers(response)
            
            return response
            
        except HTTPException as e:
            logger.warning(f"Request validation failed: {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except Exception as e:
            logger.error(f"Request validation middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Request processing failed"}
            )
    
    def _should_skip_validation(self, request: Request) -> bool:
        """Check if request should skip validation"""
        skip_paths = [
            "/static/",
            "/admin-static/",
            "/health",
            "/favicon.ico",
            "/robots.txt"
        ]
        
        path = str(request.url.path)
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    def _check_rate_limit(self, request: Request) -> bool:
        """Simple rate limiting check"""
        if not request.client:
            return True
        
        client_ip = request.client.host
        current_minute = int(__import__('time').time() // 60)
        
        # Initialize tracking for this IP
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {}
        
        # Clean old entries
        self.request_counts[client_ip] = {
            minute: count for minute, count in self.request_counts[client_ip].items()
            if minute >= current_minute - 1
        }
        
        # Check general rate limit
        total_requests = sum(self.request_counts[client_ip].values())
        if total_requests >= self.max_requests_per_minute:
            return False
        
        # Check login-specific rate limit
        if request.url.path.endswith('/login'):
            login_requests = self.request_counts[client_ip].get(current_minute, 0)
            if login_requests >= self.max_login_attempts_per_minute:
                return False
        
        # Update count
        self.request_counts[client_ip][current_minute] = (
            self.request_counts[client_ip].get(current_minute, 0) + 1
        )
        
        return True
    
    async def _validate_request(self, request: Request):
        """Validate and sanitize request data"""
        
        # Validate headers
        self._validate_headers(request)
        
        # Validate and sanitize body for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            await self._validate_body(request)
        
        # Validate query parameters
        self._validate_query_params(request)
    
    def _validate_headers(self, request: Request):
        """Validate request headers"""
        
        # Check Content-Type for JSON endpoints
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if "/api/" in str(request.url.path) and not content_type.startswith("application/json"):
                if not content_type.startswith("application/x-www-form-urlencoded"):
                    logger.warning(f"Invalid content type: {content_type} for API endpoint")
        
        # Validate User-Agent (basic check)
        user_agent = request.headers.get("user-agent", "")
        if len(user_agent) > 500:  # Suspiciously long user agent
            logger.warning(f"Suspiciously long user agent from IP: {request.client.host}")
        
        # Check for suspicious headers
        for header_name, header_value in request.headers.items():
            if self._contains_malicious_content(header_value):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid header content detected: {header_name}"
                )
    
    async def _validate_body(self, request: Request):
        """Validate and sanitize request body"""
        
        try:
            # Get the body
            body = await request.body()
            if not body:
                return
            
            # Parse JSON body
            content_type = request.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                try:
                    json_data = json.loads(body)
                    self._sanitize_json_data(json_data)
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid JSON format")
            
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            logger.error(f"Body validation error: {e}")
            raise HTTPException(status_code=400, detail="Request body validation failed")
    
    def _validate_query_params(self, request: Request):
        """Validate query parameters"""
        
        for param_name, param_value in request.query_params.items():
            # Check parameter length
            if len(param_value) > 1000:  # Reasonable limit
                raise HTTPException(
                    status_code=400,
                    detail=f"Query parameter too long: {param_name}"
                )
            
            # Check for malicious content
            if self._contains_malicious_content(param_value):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid query parameter content: {param_name}"
                )
    
    def _sanitize_json_data(self, data: Any) -> Any:
        """Recursively sanitize JSON data"""
        
        if isinstance(data, dict):
            return {key: self._sanitize_json_data(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_json_data(item) for item in data]
        elif isinstance(data, str):
            return self._sanitize_string(data)
        else:
            return data
    
    def _sanitize_string(self, value: str) -> str:
        """Sanitize string value"""
        
        # HTML escape
        sanitized = html.escape(value)
        
        # Check for malicious patterns
        if self._contains_malicious_content(value):
            logger.warning(f"Potentially malicious content detected and sanitized")
        
        return sanitized
    
    def _contains_malicious_content(self, value: str) -> bool:
        """Check if string contains potentially malicious content"""
        
        for pattern in self.security_patterns:
            if pattern.search(value):
                return True
        
        return False
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        
        # Only add headers to HTML/JSON responses
        content_type = response.headers.get("content-type", "")
        if not (content_type.startswith("text/html") or content_type.startswith("application/json")):
            return
        
        # Security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:; font-src 'self' https://cdn.jsdelivr.net;",
        }
        
        for header_name, header_value in security_headers.items():
            if header_name not in response.headers:
                response.headers[header_name] = header_value


def setup_request_validation_middleware(app):
    """Setup request validation middleware"""
    app.add_middleware(RequestValidationMiddleware)
    logger.info("✅ Request validation middleware added")