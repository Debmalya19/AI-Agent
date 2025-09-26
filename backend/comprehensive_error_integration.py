"""
Comprehensive Error Handling Integration

This module integrates all error handling components for the authentication system,
providing a unified interface for error handling, logging, and recovery.

Requirements: 1.3, 5.1, 5.2, 5.3, 5.4
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from sqlalchemy.orm import Session

from .unified_error_handler import (
    UnifiedErrorHandler, ErrorContext, setup_error_handler
)
from .auth_error_handler import (
    AuthenticationErrorHandler, AuthEvent, AuthEventType, SecurityLevel,
    setup_auth_error_handler
)
from .migration_error_handler import (
    MigrationErrorHandler, MigrationError, MigrationPhase,
    setup_migration_error_handler
)
from .error_middleware import setup_error_middleware, create_error_handlers
from .error_integration_utils import setup_error_integrations


logger = logging.getLogger(__name__)


class ComprehensiveErrorManager:
    """
    Central manager for all authentication-related error handling
    """
    
    def __init__(self, 
                 log_directory: str = "logs",
                 max_login_attempts: int = 5,
                 lockout_duration_minutes: int = 30):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(exist_ok=True)
        
        # Initialize all error handlers
        self.unified_handler = setup_error_handler(
            log_file_path=str(self.log_directory / "unified_errors.log")
        )
        
        self.auth_handler = setup_auth_error_handler(
            error_handler=self.unified_handler,
            security_log_file=str(self.log_directory / "security_events.log"),
            max_login_attempts=max_login_attempts,
            lockout_duration_minutes=lockout_duration_minutes
        )
        
        self.migration_handler = setup_migration_error_handler(
            error_handler=self.unified_handler,
            auth_error_handler=self.auth_handler,
            migration_log_file=str(self.log_directory / "migration_errors.log")
        )
        
        # Setup error integrations
        setup_error_integrations(self.unified_handler)
        
        # Statistics tracking
        self.error_stats = {
            'auth_errors': 0,
            'migration_errors': 0,
            'system_errors': 0,
            'recovery_attempts': 0,
            'successful_recoveries': 0
        }
        
        logger.info("Comprehensive error handling system initialized")
    
    async def handle_authentication_error(self, 
                                        error: Exception,
                                        user_identifier: Optional[str] = None,
                                        request: Optional[Request] = None,
                                        auth_type: str = "login") -> Dict[str, Any]:
        """Handle authentication errors with full logging and recovery"""
        self.error_stats['auth_errors'] += 1
        
        try:
            result = await self.auth_handler.handle_auth_error(
                error=error,
                user_identifier=user_identifier,
                request=request,
                auth_type=auth_type
            )
            
            # Track recovery attempts
            if result.get('recovery_available'):
                self.error_stats['recovery_attempts'] += 1
                if result.get('recovery_result', {}).get('success'):
                    self.error_stats['successful_recoveries'] += 1
            
            return result
            
        except Exception as handler_error:
            logger.error(f"Error in authentication error handler: {handler_error}")
            self.error_stats['system_errors'] += 1
            raise
    
    async def handle_migration_error(self,
                                   error: Exception,
                                   phase: MigrationPhase,
                                   affected_records: int = 0,
                                   additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle migration errors with full logging and recovery"""
        self.error_stats['migration_errors'] += 1
        
        try:
            result = await self.migration_handler.handle_migration_error(
                error=error,
                phase=phase,
                affected_records=affected_records,
                additional_context=additional_context
            )
            
            # Track recovery attempts
            if result.get('recovery_possible'):
                self.error_stats['recovery_attempts'] += 1
                if result.get('recovery_result', {}).get('success'):
                    self.error_stats['successful_recoveries'] += 1
            
            return result
            
        except Exception as handler_error:
            logger.error(f"Error in migration error handler: {handler_error}")
            self.error_stats['system_errors'] += 1
            raise
    
    async def log_security_event(self, 
                               event_type: AuthEventType,
                               user_identifier: Optional[str] = None,
                               user_id: Optional[int] = None,
                               session_id: Optional[str] = None,
                               request: Optional[Request] = None,
                               success: bool = True,
                               error_message: Optional[str] = None,
                               security_level: SecurityLevel = SecurityLevel.LOW,
                               additional_data: Optional[Dict[str, Any]] = None):
        """Log security events with comprehensive context"""
        ip_address = None
        user_agent = None
        endpoint = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent')
            endpoint = str(request.url.path)
        
        event = AuthEvent(
            event_type=event_type,
            user_identifier=user_identifier,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            success=success,
            error_message=error_message,
            security_level=security_level,
            additional_data=additional_data or {}
        )
        
        await self.auth_handler.log_security_event(event)
    
    def is_account_locked(self, user_identifier: str) -> bool:
        """Check if account is locked due to failed attempts"""
        return self.auth_handler.is_account_locked(user_identifier)
    
    def get_failure_count(self, user_identifier: str) -> int:
        """Get current failure count for user"""
        return self.auth_handler.get_failure_count(user_identifier)
    
    def unlock_account(self, user_identifier: str):
        """Manually unlock an account"""
        self.auth_handler.unlock_account(user_identifier)
        logger.info(f"Account manually unlocked: {user_identifier}")
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all error handling systems"""
        return {
            'error_statistics': self.error_stats,
            'auth_handler_status': self.auth_handler.get_security_summary(),
            'migration_handler_status': self.migration_handler.get_error_summary(),
            'unified_handler_status': self.unified_handler.get_error_metrics(),
            'circuit_breakers': self.unified_handler.get_circuit_breaker_status(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_security_report(self) -> Dict[str, Any]:
        """Generate security report for monitoring"""
        auth_summary = self.auth_handler.get_security_summary()
        
        return {
            'report_timestamp': datetime.now(timezone.utc).isoformat(),
            'authentication_security': {
                'total_tracked_accounts': auth_summary.get('total_tracked_accounts', 0),
                'locked_accounts': auth_summary.get('locked_accounts', 0),
                'high_failure_accounts': auth_summary.get('high_failure_accounts', 0),
                'max_login_attempts': auth_summary.get('max_login_attempts', 5),
                'lockout_duration_minutes': auth_summary.get('lockout_duration_minutes', 30)
            },
            'error_statistics': self.error_stats,
            'system_health': {
                'error_handlers_active': True,
                'logging_active': True,
                'recovery_success_rate': (
                    self.error_stats['successful_recoveries'] / max(self.error_stats['recovery_attempts'], 1)
                )
            }
        }
    
    async def cleanup_expired_data(self):
        """Clean up expired error tracking data"""
        try:
            # Clean up old failure tracking data
            current_time = datetime.now(timezone.utc)
            
            # Remove failure trackers older than 24 hours
            expired_trackers = []
            for user_id, tracker in self.auth_handler.failure_tracker.items():
                if (tracker.last_failure and 
                    (current_time - tracker.last_failure).total_seconds() > 86400):  # 24 hours
                    expired_trackers.append(user_id)
            
            for user_id in expired_trackers:
                del self.auth_handler.failure_tracker[user_id]
            
            if expired_trackers:
                logger.info(f"Cleaned up {len(expired_trackers)} expired failure trackers")
            
            # Clean up old migration errors (keep last 100)
            if len(self.migration_handler.migration_errors) > 100:
                self.migration_handler.migration_errors = self.migration_handler.migration_errors[-100:]
                logger.info("Cleaned up old migration error records")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Global error manager instance
_error_manager: Optional[ComprehensiveErrorManager] = None

def get_error_manager() -> ComprehensiveErrorManager:
    """Get or create comprehensive error manager instance"""
    global _error_manager
    if _error_manager is None:
        _error_manager = ComprehensiveErrorManager()
    return _error_manager

def setup_comprehensive_error_handling(
    app: Optional[FastAPI] = None,
    log_directory: str = "logs",
    max_login_attempts: int = 5,
    lockout_duration_minutes: int = 30
) -> ComprehensiveErrorManager:
    """Setup comprehensive error handling for FastAPI application"""
    global _error_manager
    
    # Initialize error manager
    _error_manager = ComprehensiveErrorManager(
        log_directory=log_directory,
        max_login_attempts=max_login_attempts,
        lockout_duration_minutes=lockout_duration_minutes
    )
    
    # Setup FastAPI error middleware and handlers only if app is provided
    if app is not None:
        try:
            setup_error_middleware(app, _error_manager.unified_handler)
            create_error_handlers(app, _error_manager.unified_handler)
            logger.info("Comprehensive error handling setup completed for FastAPI application")
        except Exception as e:
            logger.error(f"Error setting up middleware: {e}")
    else:
        logger.info("Comprehensive error handling initialized (app will be configured later)")
    
    return _error_manager

def configure_error_handling_for_app(app: FastAPI) -> bool:
    """Configure error handling for an existing FastAPI app"""
    try:
        error_manager = get_error_manager()
        if error_manager:
            setup_error_middleware(app, error_manager.unified_handler)
            create_error_handlers(app, error_manager.unified_handler)
            logger.info("Error handling configured for FastAPI application")
            return True
        else:
            logger.error("Error manager not initialized")
            return False
    except Exception as e:
        logger.error(f"Failed to configure error handling for app: {e}")
        return False

async def initialize_error_monitoring():
    """Initialize error monitoring and cleanup tasks"""
    error_manager = get_error_manager()
    
    # Schedule periodic cleanup
    async def periodic_cleanup():
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await error_manager.cleanup_expired_data()
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    # Start cleanup task
    asyncio.create_task(periodic_cleanup())
    logger.info("Error monitoring and cleanup tasks initialized")

# Convenience functions for common operations
async def log_login_attempt(
    username: str,
    success: bool,
    request: Optional[Request] = None,
    error_message: Optional[str] = None
):
    """Log login attempt with appropriate security level"""
    error_manager = get_error_manager()
    
    event_type = AuthEventType.LOGIN_SUCCESS if success else AuthEventType.LOGIN_FAILURE
    security_level = SecurityLevel.LOW if success else SecurityLevel.MEDIUM
    
    await error_manager.log_security_event(
        event_type=event_type,
        user_identifier=username,
        request=request,
        success=success,
        error_message=error_message,
        security_level=security_level
    )

async def log_admin_access_attempt(
    username: str,
    user_id: Optional[int],
    granted: bool,
    required_permission: Optional[str] = None,
    request: Optional[Request] = None
):
    """Log admin access attempt"""
    error_manager = get_error_manager()
    
    await error_manager.log_security_event(
        event_type=AuthEventType.ADMIN_ACCESS_GRANTED if granted else AuthEventType.ADMIN_ACCESS_DENIED,
        user_identifier=username,
        user_id=user_id,
        request=request,
        success=granted,
        security_level=SecurityLevel.MEDIUM if granted else SecurityLevel.HIGH,
        additional_data={'required_permission': required_permission}
    )

async def log_migration_event(
    event_type: AuthEventType,
    success: bool = True,
    error_message: Optional[str] = None,
    stats: Optional[Dict[str, Any]] = None
):
    """Log migration event"""
    error_manager = get_error_manager()
    
    await error_manager.log_security_event(
        event_type=event_type,
        success=success,
        error_message=error_message,
        security_level=SecurityLevel.HIGH if not success else SecurityLevel.MEDIUM,
        additional_data={'migration_stats': stats or {}}
    )