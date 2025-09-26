"""
Authentication Error Handler and Security Event Logger

This module provides comprehensive error handling and logging specifically for
authentication failures, security events, and migration processes.

Requirements: 1.3, 5.1, 5.2, 5.3, 5.4
"""

import logging
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .unified_error_handler import (
    UnifiedErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity,
    get_error_handler
)


class AuthEventType(Enum):
    """Types of authentication events to log"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    SESSION_INVALIDATED = "session_invalidated"
    PASSWORD_CHANGE = "password_change"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    ADMIN_ACCESS_GRANTED = "admin_access_granted"
    ADMIN_ACCESS_DENIED = "admin_access_denied"
    MIGRATION_STARTED = "migration_started"
    MIGRATION_COMPLETED = "migration_completed"
    MIGRATION_FAILED = "migration_failed"
    MIGRATION_ROLLED_BACK = "migration_rolled_back"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class SecurityLevel(Enum):
    """Security levels for events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuthEvent:
    """Authentication event data structure"""
    event_type: AuthEventType
    user_identifier: Optional[str] = None
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    security_level: SecurityLevel = SecurityLevel.LOW
    additional_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for logging"""
        return {
            'event_type': self.event_type.value,
            'user_identifier': self.user_identifier,
            'user_id': self.user_id,
            'session_id': self.session_id[:8] + '...' if self.session_id else None,  # Truncate for security
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'endpoint': self.endpoint,
            'success': self.success,
            'error_message': self.error_message,
            'security_level': self.security_level.value,
            'additional_data': self.additional_data,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class AuthFailureTracker:
    """Track authentication failures for rate limiting and security"""
    user_identifier: str
    failure_count: int = 0
    first_failure: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    locked_until: Optional[datetime] = None
    failure_ips: List[str] = field(default_factory=list)
    
    def add_failure(self, ip_address: Optional[str] = None):
        """Add a failure event"""
        now = datetime.now(timezone.utc)
        
        if self.first_failure is None:
            self.first_failure = now
        
        self.last_failure = now
        self.failure_count += 1
        
        if ip_address and ip_address not in self.failure_ips:
            self.failure_ips.append(ip_address)
    
    def is_locked(self) -> bool:
        """Check if account is currently locked"""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until
    
    def lock_account(self, duration_minutes: int = 30):
        """Lock account for specified duration"""
        self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
    
    def reset_failures(self):
        """Reset failure tracking after successful login"""
        self.failure_count = 0
        self.first_failure = None
        self.last_failure = None
        self.locked_until = None
        self.failure_ips.clear()


class AuthenticationErrorHandler:
    """
    Comprehensive authentication error handler with security event logging
    """
    
    def __init__(self, 
                 error_handler: Optional[UnifiedErrorHandler] = None,
                 security_log_file: Optional[str] = None,
                 max_login_attempts: int = 5,
                 lockout_duration_minutes: int = 30):
        self.error_handler = error_handler or get_error_handler()
        self.max_login_attempts = max_login_attempts
        self.lockout_duration_minutes = lockout_duration_minutes
        
        # Setup security logger
        self.security_logger = self._setup_security_logger(security_log_file)
        
        # Track authentication failures
        self.failure_tracker: Dict[str, AuthFailureTracker] = {}
        
        # Setup event handlers
        self._setup_event_handlers()
    
    def _setup_security_logger(self, log_file_path: Optional[str] = None) -> logging.Logger:
        """Setup dedicated security event logger"""
        logger = logging.getLogger("auth_security")
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Console handler for immediate visibility
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler for security events
        if not log_file_path:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file_path = log_dir / "security_events.log"
        
        file_handler = logging.FileHandler(log_file_path)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _setup_event_handlers(self):
        """Setup event-specific handlers"""
        self.event_handlers = {
            AuthEventType.LOGIN_FAILURE: self._handle_login_failure,
            AuthEventType.LOGIN_SUCCESS: self._handle_login_success,
            AuthEventType.ADMIN_ACCESS_DENIED: self._handle_admin_access_denied,
            AuthEventType.SUSPICIOUS_ACTIVITY: self._handle_suspicious_activity,
            AuthEventType.MIGRATION_FAILED: self._handle_migration_failure,
        }
    
    async def handle_auth_error(self, 
                              error: Exception, 
                              user_identifier: Optional[str] = None,
                              request: Optional[Request] = None,
                              auth_type: str = "login") -> Dict[str, Any]:
        """
        Handle authentication errors with comprehensive logging and security tracking
        """
        # Extract request context
        ip_address = None
        user_agent = None
        endpoint = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent')
            endpoint = str(request.url.path)
        
        # Create error context
        error_context = ErrorContext(
            user_id=user_identifier,
            component='authentication',
            operation=auth_type,
            endpoint=endpoint,
            additional_data={
                'ip_address': ip_address,
                'user_agent': user_agent,
                'auth_type': auth_type
            }
        )
        
        # Use unified error handler
        error_result = await self.error_handler.handle_error(error, error_context)
        
        # Determine event type and security level
        event_type = self._determine_auth_event_type(error, auth_type)
        security_level = self._determine_security_level(error, user_identifier)
        
        # Create authentication event
        auth_event = AuthEvent(
            event_type=event_type,
            user_identifier=user_identifier,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            success=False,
            error_message=str(error),
            security_level=security_level,
            additional_data={
                'error_id': error_result.get('error_id'),
                'error_category': error_result.get('category'),
                'auth_type': auth_type
            }
        )
        
        # Log security event
        await self.log_security_event(auth_event)
        
        # Handle specific event types
        if event_type in self.event_handlers:
            await self.event_handlers[event_type](auth_event, error)
        
        # Check for account lockout
        should_lock = self._should_lock_account(user_identifier, ip_address)
        
        return {
            'auth_error': True,
            'event_type': event_type.value,
            'security_level': security_level.value,
            'should_lock_account': should_lock,
            'error_id': error_result.get('error_id'),
            'message': self._get_user_friendly_message(error, should_lock),
            'recovery_available': error_result.get('recovery_result', {}).get('success', False)
        }
    
    async def log_security_event(self, event: AuthEvent):
        """Log security event with appropriate level"""
        event_data = event.to_dict()
        
        # Create log message
        log_message = (
            f"AUTH_EVENT: {event.event_type.value} - "
            f"User: {event.user_identifier or 'unknown'} - "
            f"IP: {event.ip_address or 'unknown'} - "
            f"Success: {event.success}"
        )
        
        # Log based on security level
        if event.security_level == SecurityLevel.CRITICAL:
            self.security_logger.critical(log_message, extra={'event_data': event_data})
        elif event.security_level == SecurityLevel.HIGH:
            self.security_logger.error(log_message, extra={'event_data': event_data})
        elif event.security_level == SecurityLevel.MEDIUM:
            self.security_logger.warning(log_message, extra={'event_data': event_data})
        else:
            self.security_logger.info(log_message, extra={'event_data': event_data})
        
        # Store event for analysis (in production, this might go to a security database)
        await self._store_security_event(event)
    
    async def log_successful_auth(self, 
                                user_identifier: str,
                                user_id: Optional[int] = None,
                                session_id: Optional[str] = None,
                                request: Optional[Request] = None,
                                auth_type: str = "login"):
        """Log successful authentication event"""
        ip_address = None
        user_agent = None
        endpoint = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent')
            endpoint = str(request.url.path)
        
        event = AuthEvent(
            event_type=AuthEventType.LOGIN_SUCCESS,
            user_identifier=user_identifier,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            success=True,
            security_level=SecurityLevel.LOW,
            additional_data={'auth_type': auth_type}
        )
        
        await self.log_security_event(event)
        
        # Reset failure tracking on successful login
        if user_identifier in self.failure_tracker:
            self.failure_tracker[user_identifier].reset_failures()
    
    async def log_admin_access(self, 
                             user_identifier: str,
                             user_id: Optional[int] = None,
                             granted: bool = True,
                             required_permission: Optional[str] = None,
                             request: Optional[Request] = None):
        """Log admin access attempts"""
        ip_address = None
        user_agent = None
        endpoint = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent')
            endpoint = str(request.url.path)
        
        event_type = AuthEventType.ADMIN_ACCESS_GRANTED if granted else AuthEventType.ADMIN_ACCESS_DENIED
        security_level = SecurityLevel.MEDIUM if granted else SecurityLevel.HIGH
        
        event = AuthEvent(
            event_type=event_type,
            user_identifier=user_identifier,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            success=granted,
            security_level=security_level,
            additional_data={
                'required_permission': required_permission,
                'admin_access': True
            }
        )
        
        await self.log_security_event(event)
    
    async def log_migration_event(self, 
                                event_type: AuthEventType,
                                success: bool = True,
                                error_message: Optional[str] = None,
                                stats: Optional[Dict[str, Any]] = None):
        """Log migration process events"""
        event = AuthEvent(
            event_type=event_type,
            success=success,
            error_message=error_message,
            security_level=SecurityLevel.HIGH if not success else SecurityLevel.MEDIUM,
            additional_data={
                'migration_stats': stats or {},
                'process_type': 'auth_migration'
            }
        )
        
        await self.log_security_event(event)
    
    def _determine_auth_event_type(self, error: Exception, auth_type: str) -> AuthEventType:
        """Determine the type of authentication event"""
        error_str = str(error).lower()
        
        if 'invalid' in error_str or 'password' in error_str or 'credentials' in error_str:
            return AuthEventType.LOGIN_FAILURE
        elif 'expired' in error_str or 'session' in error_str:
            return AuthEventType.SESSION_EXPIRED
        elif 'permission' in error_str or 'admin' in error_str:
            return AuthEventType.ADMIN_ACCESS_DENIED
        elif 'rate limit' in error_str or 'too many' in error_str:
            return AuthEventType.RATE_LIMIT_EXCEEDED
        else:
            return AuthEventType.LOGIN_FAILURE
    
    def _determine_security_level(self, error: Exception, user_identifier: Optional[str]) -> SecurityLevel:
        """Determine security level of the event"""
        error_str = str(error).lower()
        
        # Check failure history
        if user_identifier and user_identifier in self.failure_tracker:
            tracker = self.failure_tracker[user_identifier]
            if tracker.failure_count >= self.max_login_attempts - 1:
                return SecurityLevel.HIGH
            elif tracker.failure_count >= 3:
                return SecurityLevel.MEDIUM
        
        # Check error type
        if 'admin' in error_str or 'permission' in error_str:
            return SecurityLevel.HIGH
        elif 'invalid' in error_str or 'password' in error_str:
            return SecurityLevel.MEDIUM
        else:
            return SecurityLevel.LOW
    
    def _should_lock_account(self, user_identifier: Optional[str], ip_address: Optional[str]) -> bool:
        """Determine if account should be locked"""
        if not user_identifier:
            return False
        
        # Get or create failure tracker
        if user_identifier not in self.failure_tracker:
            self.failure_tracker[user_identifier] = AuthFailureTracker(user_identifier)
        
        tracker = self.failure_tracker[user_identifier]
        tracker.add_failure(ip_address)
        
        # Check if should lock
        if tracker.failure_count >= self.max_login_attempts:
            tracker.lock_account(self.lockout_duration_minutes)
            return True
        
        return False
    
    def _get_user_friendly_message(self, error: Exception, should_lock: bool) -> str:
        """Get user-friendly error message"""
        if should_lock:
            return f"Account temporarily locked due to multiple failed login attempts. Try again in {self.lockout_duration_minutes} minutes."
        
        error_str = str(error).lower()
        
        if 'invalid' in error_str or 'password' in error_str:
            return "Invalid username or password. Please check your credentials and try again."
        elif 'expired' in error_str:
            return "Your session has expired. Please log in again."
        elif 'permission' in error_str or 'admin' in error_str:
            return "You don't have permission to access this resource."
        else:
            return "Authentication failed. Please try again."
    
    async def _store_security_event(self, event: AuthEvent):
        """Store security event for analysis (placeholder for database storage)"""
        # In a production system, this would store events in a security database
        # For now, we'll just ensure it's logged
        pass
    
    # Event-specific handlers
    async def _handle_login_failure(self, event: AuthEvent, error: Exception):
        """Handle login failure events"""
        if event.user_identifier:
            # Check for suspicious patterns
            if event.user_identifier in self.failure_tracker:
                tracker = self.failure_tracker[event.user_identifier]
                
                # Check for multiple IPs
                if len(tracker.failure_ips) > 3:
                    suspicious_event = AuthEvent(
                        event_type=AuthEventType.SUSPICIOUS_ACTIVITY,
                        user_identifier=event.user_identifier,
                        ip_address=event.ip_address,
                        security_level=SecurityLevel.HIGH,
                        additional_data={
                            'reason': 'multiple_ip_addresses',
                            'ip_count': len(tracker.failure_ips),
                            'failure_count': tracker.failure_count
                        }
                    )
                    await self.log_security_event(suspicious_event)
    
    async def _handle_login_success(self, event: AuthEvent, error: Exception):
        """Handle successful login events"""
        # Reset failure tracking
        if event.user_identifier and event.user_identifier in self.failure_tracker:
            self.failure_tracker[event.user_identifier].reset_failures()
    
    async def _handle_admin_access_denied(self, event: AuthEvent, error: Exception):
        """Handle admin access denial events"""
        # Log high-priority security event for admin access attempts
        if event.user_identifier:
            # Check for repeated admin access attempts
            pass  # Additional logic could be added here
    
    async def _handle_suspicious_activity(self, event: AuthEvent, error: Exception):
        """Handle suspicious activity events"""
        # In production, this might trigger additional security measures
        pass
    
    async def _handle_migration_failure(self, event: AuthEvent, error: Exception):
        """Handle migration failure events"""
        # Log critical migration failures
        self.security_logger.critical(
            f"MIGRATION_FAILURE: {event.error_message}",
            extra={'event_data': event.to_dict()}
        )
    
    def is_account_locked(self, user_identifier: str) -> bool:
        """Check if account is currently locked"""
        if user_identifier not in self.failure_tracker:
            return False
        return self.failure_tracker[user_identifier].is_locked()
    
    def get_failure_count(self, user_identifier: str) -> int:
        """Get current failure count for user"""
        if user_identifier not in self.failure_tracker:
            return 0
        return self.failure_tracker[user_identifier].failure_count
    
    def unlock_account(self, user_identifier: str):
        """Manually unlock an account"""
        if user_identifier in self.failure_tracker:
            self.failure_tracker[user_identifier].reset_failures()
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security summary for monitoring"""
        locked_accounts = sum(1 for tracker in self.failure_tracker.values() if tracker.is_locked())
        high_failure_accounts = sum(1 for tracker in self.failure_tracker.values() if tracker.failure_count >= 3)
        
        return {
            'total_tracked_accounts': len(self.failure_tracker),
            'locked_accounts': locked_accounts,
            'high_failure_accounts': high_failure_accounts,
            'max_login_attempts': self.max_login_attempts,
            'lockout_duration_minutes': self.lockout_duration_minutes
        }


# Global instance
_auth_error_handler: Optional[AuthenticationErrorHandler] = None

def get_auth_error_handler() -> AuthenticationErrorHandler:
    """Get or create authentication error handler instance"""
    global _auth_error_handler
    if _auth_error_handler is None:
        _auth_error_handler = AuthenticationErrorHandler()
    return _auth_error_handler

def setup_auth_error_handler(
    error_handler: Optional[UnifiedErrorHandler] = None,
    security_log_file: Optional[str] = None,
    max_login_attempts: int = 5,
    lockout_duration_minutes: int = 30
) -> AuthenticationErrorHandler:
    """Setup authentication error handler with custom configuration"""
    global _auth_error_handler
    _auth_error_handler = AuthenticationErrorHandler(
        error_handler=error_handler,
        security_log_file=security_log_file,
        max_login_attempts=max_login_attempts,
        lockout_duration_minutes=lockout_duration_minutes
    )
    return _auth_error_handler


# Context manager for authentication error handling
@asynccontextmanager
async def auth_error_context(
    user_identifier: Optional[str] = None,
    request: Optional[Request] = None,
    auth_type: str = "login"
):
    """Context manager for automatic authentication error handling"""
    auth_handler = get_auth_error_handler()
    
    try:
        yield auth_handler
    except Exception as e:
        error_result = await auth_handler.handle_auth_error(
            error=e,
            user_identifier=user_identifier,
            request=request,
            auth_type=auth_type
        )
        # Re-raise with additional context
        if error_result.get('should_lock_account'):
            raise HTTPException(
                status_code=423,  # Locked
                detail=error_result.get('message')
            )
        else:
            raise HTTPException(
                status_code=401,
                detail=error_result.get('message')
            )