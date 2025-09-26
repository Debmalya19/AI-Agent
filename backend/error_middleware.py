"""
FastAPI Error Handling Middleware

This module provides FastAPI middleware for integrating the unified error handler
with web requests, providing automatic error handling, logging, and recovery.

Requirements: 4.4, 1.4, 3.4
"""

import asyncio
import json
import time
import uuid
from typing import Callable, Dict, Any, Optional
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
try:
    from fastapi.middleware.base import BaseHTTPMiddleware
except ImportError:
    from starlette.middleware.base import BaseHTTPMiddleware

try:
    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.responses import Response as StarletteResponse
except ImportError:
    # Fallback for older versions
    RequestResponseEndpoint = None
    StarletteResponse = None
import logging

from .unified_error_handler import (
    UnifiedErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity,
    get_error_handler
)

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for unified error handling across all requests
    """
    
    def __init__(self, app: FastAPI, error_handler: Optional[UnifiedErrorHandler] = None):
        super().__init__(app)
        self.error_handler = error_handler or get_error_handler()
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> StarletteResponse:
        """Process request with unified error handling"""
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract user context if available
        user_id = None
        session_id = None
        
        try:
            # Try to get user info from session cookie or authorization header
            session_token = request.cookies.get('session_token')
            if session_token:
                session_id = session_token
                # You could decode the session to get user_id here
                
            # Try to get user from authorization header
            auth_header = request.headers.get('authorization')
            if auth_header and auth_header.startswith('Bearer '):
                # You could decode JWT to get user_id here
                pass
                
        except Exception:
            # Ignore errors in user context extraction
            pass
        
        # Create error context
        error_context = ErrorContext(
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            endpoint=str(request.url.path),
            method=request.method,
            component='fastapi_app',
            additional_data={
                'user_agent': request.headers.get('user-agent'),
                'client_ip': request.client.host if request.client else None,
                'query_params': dict(request.query_params)
            }
        )
        
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Log successful request
            duration = time.time() - start_time
            logger.info(
                f"Request completed - {request.method} {request.url.path} - "
                f"Status: {response.status_code} - Duration: {duration:.3f}s - "
                f"Request ID: {request_id}"
            )
            
            return response
            
        except Exception as error:
            # Handle the error using unified error handler
            duration = time.time() - start_time
            
            logger.error(
                f"Request failed - {request.method} {request.url.path} - "
                f"Error: {str(error)} - Duration: {duration:.3f}s - "
                f"Request ID: {request_id}"
            )
            
            # Use unified error handler
            error_result = await self.error_handler.handle_error(error, error_context)
            
            # Convert error to appropriate HTTP response
            return await self._create_error_response(error, error_result, request_id)
    
    async def _create_error_response(self, error: Exception, error_result: Dict[str, Any], 
                                   request_id: str) -> JSONResponse:
        """Create appropriate HTTP error response"""
        
        # Determine HTTP status code based on error type and category
        status_code = self._determine_status_code(error, error_result)
        
        # Create user-friendly error message
        user_message = self._create_user_message(error, error_result)
        
        # Prepare response data
        response_data = {
            'error': True,
            'message': user_message,
            'request_id': request_id,
            'timestamp': error_result.get('timestamp'),
            'category': error_result.get('category')
        }
        
        # Add recovery information if available
        recovery_result = error_result.get('recovery_result', {})
        if recovery_result.get('success'):
            response_data['recovery'] = {
                'action': recovery_result.get('action'),
                'message': recovery_result.get('message')
            }
        
        # Add debug information in development mode
        if logger.level <= logging.DEBUG:
            response_data['debug'] = {
                'error_type': type(error).__name__,
                'error_id': error_result.get('error_id'),
                'severity': error_result.get('severity'),
                'strategy': error_result.get('strategy')
            }
        
        return JSONResponse(
            status_code=status_code,
            content=response_data,
            headers={'X-Request-ID': request_id}
        )
    
    def _determine_status_code(self, error: Exception, error_result: Dict[str, Any]) -> int:
        """Determine appropriate HTTP status code"""
        category = error_result.get('category', 'system')
        severity = error_result.get('severity', 'medium')
        
        # Handle specific exception types
        if isinstance(error, HTTPException):
            return error.status_code
        
        # Handle by category
        if category == 'authentication':
            return 401
        elif category == 'authorization':
            return 403
        elif category == 'validation':
            return 400
        elif category == 'database':
            if severity == 'critical':
                return 503  # Service Unavailable
            else:
                return 500
        elif category == 'integration':
            return 502  # Bad Gateway
        elif category == 'external_api':
            return 503  # Service Unavailable
        elif category == 'network':
            return 504  # Gateway Timeout
        elif category == 'sync':
            return 500
        else:
            # Default server error
            return 500
    
    def _create_user_message(self, error: Exception, error_result: Dict[str, Any]) -> str:
        """Create user-friendly error message"""
        category = error_result.get('category', 'system')
        severity = error_result.get('severity', 'medium')
        recovery_result = error_result.get('recovery_result', {})
        
        # Check if recovery was successful
        if recovery_result.get('success'):
            recovery_message = recovery_result.get('message', '')
            if recovery_message:
                return f"Temporary issue resolved: {recovery_message}"
        
        # Category-specific messages
        if category == 'authentication':
            return "Authentication required. Please log in again."
        elif category == 'authorization':
            return "You don't have permission to access this resource."
        elif category == 'validation':
            return "Invalid request data. Please check your input and try again."
        elif category == 'database':
            if severity == 'critical':
                return "Database service is temporarily unavailable. Please try again later."
            else:
                return "A database error occurred. The issue has been logged."
        elif category == 'integration':
            return "Admin dashboard features are temporarily unavailable."
        elif category == 'external_api':
            return "External service is temporarily unavailable. Please try again later."
        elif category == 'network':
            return "Network timeout occurred. Please try again."
        elif category == 'sync':
            return "Data synchronization issue. Your request has been queued for retry."
        else:
            # Generic message for unknown errors
            if severity == 'critical':
                return "A critical system error occurred. Please contact support."
            else:
                return "An unexpected error occurred. The issue has been logged."


class AdminErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Specialized error handling middleware for admin dashboard routes
    """
    
    def __init__(self, app: FastAPI, error_handler: Optional[UnifiedErrorHandler] = None):
        super().__init__(app)
        self.error_handler = error_handler or get_error_handler()
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> StarletteResponse:
        """Process admin requests with specialized error handling"""
        
        # Only apply to admin routes
        if not request.url.path.startswith('/admin'):
            return await call_next(request)
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Create admin-specific error context
        error_context = ErrorContext(
            request_id=request_id,
            endpoint=str(request.url.path),
            method=request.method,
            component='admin_dashboard',
            additional_data={
                'is_admin_request': True,
                'user_agent': request.headers.get('user-agent'),
                'client_ip': request.client.host if request.client else None
            }
        )
        
        try:
            response = await call_next(request)
            return response
            
        except Exception as error:
            # Handle admin-specific errors
            error_result = await self.error_handler.handle_error(error, error_context)
            
            # Create admin-specific error response
            return await self._create_admin_error_response(error, error_result, request_id)
    
    async def _create_admin_error_response(self, error: Exception, error_result: Dict[str, Any], 
                                         request_id: str) -> JSONResponse:
        """Create admin-specific error response"""
        
        status_code = self._determine_admin_status_code(error, error_result)
        
        response_data = {
            'error': True,
            'message': self._create_admin_message(error, error_result),
            'request_id': request_id,
            'timestamp': error_result.get('timestamp'),
            'admin_context': True
        }
        
        # Add admin-specific recovery information
        recovery_result = error_result.get('recovery_result', {})
        if recovery_result.get('success'):
            response_data['fallback_available'] = True
            response_data['fallback_message'] = recovery_result.get('message')
        
        return JSONResponse(
            status_code=status_code,
            content=response_data,
            headers={'X-Request-ID': request_id}
        )
    
    def _determine_admin_status_code(self, error: Exception, error_result: Dict[str, Any]) -> int:
        """Determine status code for admin requests"""
        category = error_result.get('category', 'system')
        
        # Admin-specific status codes
        if category == 'integration':
            return 503  # Service Unavailable for admin integration issues
        elif category == 'sync':
            return 202  # Accepted - operation will be retried
        else:
            # Use standard status code determination
            return self._determine_status_code(error, error_result)
    
    def _determine_status_code(self, error: Exception, error_result: Dict[str, Any]) -> int:
        """Standard status code determination (copied from main middleware)"""
        category = error_result.get('category', 'system')
        severity = error_result.get('severity', 'medium')
        
        if isinstance(error, HTTPException):
            return error.status_code
        
        if category == 'authentication':
            return 401
        elif category == 'authorization':
            return 403
        elif category == 'validation':
            return 400
        elif category == 'database':
            return 503 if severity == 'critical' else 500
        elif category == 'integration':
            return 502
        elif category == 'external_api':
            return 503
        elif category == 'network':
            return 504
        else:
            return 500
    
    def _create_admin_message(self, error: Exception, error_result: Dict[str, Any]) -> str:
        """Create admin-specific error message"""
        category = error_result.get('category', 'system')
        recovery_result = error_result.get('recovery_result', {})
        
        if recovery_result.get('success'):
            return f"Admin operation completed with fallback: {recovery_result.get('message', '')}"
        
        # Admin-specific messages
        if category == 'integration':
            return "Admin dashboard integration is temporarily unavailable. Core functionality remains active."
        elif category == 'sync':
            return "Data synchronization is queued for retry. Changes will be reflected shortly."
        elif category == 'database':
            return "Database operation failed. Admin operations are temporarily limited."
        else:
            return f"Admin operation failed: {category} error occurred."


def setup_error_middleware(app: FastAPI, error_handler: Optional[UnifiedErrorHandler] = None):
    """Setup error handling middleware for FastAPI application"""
    
    # Add main error handling middleware
    app.add_middleware(ErrorHandlingMiddleware, error_handler=error_handler)
    
    # Add admin-specific error handling middleware
    app.add_middleware(AdminErrorHandlingMiddleware, error_handler=error_handler)
    
    logger.info("Error handling middleware setup completed")


def create_error_handlers(app: FastAPI, error_handler: Optional[UnifiedErrorHandler] = None):
    """Create FastAPI exception handlers"""
    
    if not error_handler:
        error_handler = get_error_handler()
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions"""
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        error_context = ErrorContext(
            request_id=request_id,
            endpoint=str(request.url.path),
            method=request.method,
            component='fastapi_app'
        )
        
        error_result = await error_handler.handle_error(exc, error_context)
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                'error': True,
                'message': exc.detail,
                'request_id': request_id,
                'timestamp': error_result.get('timestamp')
            },
            headers={'X-Request-ID': request_id}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions"""
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        error_context = ErrorContext(
            request_id=request_id,
            endpoint=str(request.url.path),
            method=request.method,
            component='fastapi_app'
        )
        
        error_result = await error_handler.handle_error(exc, error_context)
        
        # Determine status code
        status_code = 500
        category = error_result.get('category', 'system')
        if category == 'authentication':
            status_code = 401
        elif category == 'authorization':
            status_code = 403
        elif category == 'validation':
            status_code = 400
        
        return JSONResponse(
            status_code=status_code,
            content={
                'error': True,
                'message': 'An unexpected error occurred',
                'request_id': request_id,
                'timestamp': error_result.get('timestamp')
            },
            headers={'X-Request-ID': request_id}
        )
    
    logger.info("FastAPI exception handlers created")


# Health check endpoint for error handling system
async def error_handler_health_check(error_handler: Optional[UnifiedErrorHandler] = None) -> Dict[str, Any]:
    """Health check endpoint for error handling system"""
    if not error_handler:
        error_handler = get_error_handler()
    
    return error_handler.get_health_report()


# Monitoring endpoint for error metrics
async def error_metrics_endpoint(error_handler: Optional[UnifiedErrorHandler] = None) -> Dict[str, Any]:
    """Endpoint to get error metrics"""
    if not error_handler:
        error_handler = get_error_handler()
    
    return {
        'error_metrics': error_handler.get_error_metrics(),
        'circuit_breakers': error_handler.get_circuit_breaker_status(),
        'timestamp': time.time()
    }