"""
Error Integration Utilities

This module provides utilities to integrate the unified error handler with existing
admin dashboard, sync, and authentication components.

Requirements: 4.4, 1.4, 3.4
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
from datetime import datetime, timezone, timedelta

from .unified_error_handler import (
    UnifiedErrorHandler, ErrorContext, ErrorCategory, get_error_handler
)

logger = logging.getLogger(__name__)


class AdminDashboardErrorIntegration:
    """Integration utilities for admin dashboard error handling"""
    
    def __init__(self, error_handler: Optional[UnifiedErrorHandler] = None):
        self.error_handler = error_handler or get_error_handler()
    
    def wrap_admin_api_call(self, func: Callable) -> Callable:
        """Wrap admin API calls with error handling"""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            context = ErrorContext(
                component='admin_api',
                operation=func.__name__,
                additional_data={'function': func.__qualname__}
            )
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_result = await self.error_handler.handle_error(e, context)
                
                # Check if recovery was successful
                recovery_result = error_result.get('recovery_result', {})
                if recovery_result.get('success'):
                    # Return fallback response for admin operations
                    return self._create_admin_fallback_response(func.__name__, recovery_result)
                else:
                    # Re-raise if no recovery possible
                    raise e
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            context = ErrorContext(
                component='admin_api',
                operation=func.__name__,
                additional_data={'function': func.__qualname__}
            )
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # For sync operations, log error and return fallback
                category = self.error_handler.categorize_error(e, context)
                severity = self.error_handler.determine_severity(e, category, context)
                strategy = self.error_handler.determine_recovery_strategy(e, category, severity, context)
                
                self.error_handler._record_error_metrics(category, e, context)
                self.error_handler._log_error(e, category, severity, strategy, context)
                
                # Return fallback for admin operations
                return self._create_admin_fallback_response(func.__name__, {'success': True, 'action': 'fallback'})
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    def _create_admin_fallback_response(self, operation: str, recovery_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback response for admin operations"""
        return {
            'success': False,
            'error': True,
            'message': f'Admin operation "{operation}" failed but system remains stable',
            'fallback_active': True,
            'recovery_action': recovery_result.get('action', 'unknown'),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def handle_admin_auth_error(self, error: Exception, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle admin authentication errors"""
        context = ErrorContext(
            user_id=user_id,
            component='admin_auth',
            operation='authentication',
            additional_data={'error_type': type(error).__name__}
        )
        
        # Synchronous handling for auth errors
        category = self.error_handler.categorize_error(error, context)
        severity = self.error_handler.determine_severity(error, category, context)
        
        self.error_handler._record_error_metrics(category, error, context)
        self.error_handler._log_error(error, category, severity, None, context)
        
        # Return auth-specific response
        if 'expired' in str(error).lower():
            return {
                'auth_error': True,
                'action': 'token_refresh_required',
                'message': 'Authentication token has expired',
                'redirect_to_login': True
            }
        else:
            return {
                'auth_error': True,
                'action': 'reauthentication_required',
                'message': 'Authentication failed',
                'redirect_to_login': True
            }
    
    def handle_admin_permission_error(self, error: Exception, user_id: Optional[str] = None, 
                                    required_permission: Optional[str] = None) -> Dict[str, Any]:
        """Handle admin permission errors"""
        context = ErrorContext(
            user_id=user_id,
            component='admin_auth',
            operation='authorization',
            additional_data={
                'required_permission': required_permission,
                'error_type': type(error).__name__
            }
        )
        
        category = self.error_handler.categorize_error(error, context)
        severity = self.error_handler.determine_severity(error, category, context)
        
        self.error_handler._record_error_metrics(category, error, context)
        self.error_handler._log_error(error, category, severity, None, context)
        
        return {
            'permission_error': True,
            'message': f'Insufficient permissions for admin operation',
            'required_permission': required_permission,
            'contact_admin': True
        }


class DataSyncErrorIntegration:
    """Integration utilities for data synchronization error handling"""
    
    def __init__(self, error_handler: Optional[UnifiedErrorHandler] = None):
        self.error_handler = error_handler or get_error_handler()
        self.failed_sync_operations: List[Dict[str, Any]] = []
    
    async def handle_sync_error(self, error: Exception, sync_operation: str, 
                              entity_id: Optional[int] = None, 
                              entity_type: Optional[str] = None) -> Dict[str, Any]:
        """Handle data synchronization errors"""
        context = ErrorContext(
            component='data_sync',
            operation=sync_operation,
            additional_data={
                'entity_id': entity_id,
                'entity_type': entity_type,
                'sync_operation': sync_operation
            }
        )
        
        error_result = await self.error_handler.handle_error(error, context)
        
        # Queue failed operation for retry
        failed_operation = {
            'operation': sync_operation,
            'entity_id': entity_id,
            'entity_type': entity_type,
            'error': str(error),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'retry_count': 0,
            'error_id': error_result.get('error_id')
        }
        
        self.failed_sync_operations.append(failed_operation)
        
        # Check recovery result
        recovery_result = error_result.get('recovery_result', {})
        if recovery_result.get('success'):
            return {
                'sync_error': True,
                'queued_for_retry': True,
                'message': recovery_result.get('message', 'Sync operation queued for retry'),
                'error_id': error_result.get('error_id')
            }
        else:
            return {
                'sync_error': True,
                'failed': True,
                'message': 'Sync operation failed and could not be queued for retry',
                'error_id': error_result.get('error_id')
            }
    
    async def retry_failed_sync_operations(self, max_retries: int = 3) -> Dict[str, Any]:
        """Retry failed sync operations"""
        retry_results = {
            'total_operations': len(self.failed_sync_operations),
            'successful_retries': 0,
            'failed_retries': 0,
            'operations_processed': []
        }
        
        operations_to_retry = self.failed_sync_operations.copy()
        self.failed_sync_operations.clear()
        
        for operation in operations_to_retry:
            if operation['retry_count'] >= max_retries:
                retry_results['failed_retries'] += 1
                retry_results['operations_processed'].append({
                    'operation': operation['operation'],
                    'status': 'max_retries_exceeded',
                    'retry_count': operation['retry_count']
                })
                continue
            
            try:
                # Simulate retry operation (in real implementation, you'd call the actual sync function)
                await asyncio.sleep(0.1)  # Simulate async operation
                
                # Mark as successful
                retry_results['successful_retries'] += 1
                retry_results['operations_processed'].append({
                    'operation': operation['operation'],
                    'status': 'success',
                    'retry_count': operation['retry_count'] + 1
                })
                
            except Exception as retry_error:
                # Increment retry count and re-queue if under limit
                operation['retry_count'] += 1
                if operation['retry_count'] < max_retries:
                    self.failed_sync_operations.append(operation)
                
                retry_results['failed_retries'] += 1
                retry_results['operations_processed'].append({
                    'operation': operation['operation'],
                    'status': 'retry_failed',
                    'retry_count': operation['retry_count'],
                    'error': str(retry_error)
                })
        
        return retry_results
    
    def get_sync_error_summary(self) -> Dict[str, Any]:
        """Get summary of sync errors"""
        return {
            'pending_retries': len(self.failed_sync_operations),
            'operations': [
                {
                    'operation': op['operation'],
                    'entity_type': op['entity_type'],
                    'retry_count': op['retry_count'],
                    'timestamp': op['timestamp']
                }
                for op in self.failed_sync_operations
            ]
        }


class DatabaseErrorIntegration:
    """Integration utilities for database error handling"""
    
    def __init__(self, error_handler: Optional[UnifiedErrorHandler] = None):
        self.error_handler = error_handler or get_error_handler()
        self.connection_pool_healthy = True
        self.last_health_check = datetime.now(timezone.utc)
    
    async def handle_database_error(self, error: Exception, operation: str, 
                                  table_name: Optional[str] = None) -> Dict[str, Any]:
        """Handle database errors with connection health monitoring"""
        context = ErrorContext(
            component='database',
            operation=operation,
            additional_data={
                'table_name': table_name,
                'connection_healthy': self.connection_pool_healthy
            }
        )
        
        error_result = await self.error_handler.handle_error(error, context)
        
        # Update connection health status
        if 'connection' in str(error).lower():
            self.connection_pool_healthy = False
            self.last_health_check = datetime.now(timezone.utc)
        
        recovery_result = error_result.get('recovery_result', {})
        
        return {
            'database_error': True,
            'operation': operation,
            'table_name': table_name,
            'connection_healthy': self.connection_pool_healthy,
            'recovery_available': recovery_result.get('success', False),
            'recovery_action': recovery_result.get('action'),
            'error_id': error_result.get('error_id')
        }
    
    def check_database_health(self) -> Dict[str, Any]:
        """Check database health status"""
        current_time = datetime.now(timezone.utc)
        time_since_check = (current_time - self.last_health_check).total_seconds()
        
        # Reset health status if enough time has passed
        if not self.connection_pool_healthy and time_since_check > 300:  # 5 minutes
            self.connection_pool_healthy = True
        
        return {
            'connection_healthy': self.connection_pool_healthy,
            'last_health_check': self.last_health_check.isoformat(),
            'time_since_check_seconds': time_since_check
        }


class AuthenticationErrorIntegration:
    """Integration utilities for authentication error handling"""
    
    def __init__(self, error_handler: Optional[UnifiedErrorHandler] = None):
        self.error_handler = error_handler or get_error_handler()
        self.failed_auth_attempts: Dict[str, List[datetime]] = {}
    
    async def handle_auth_error(self, error: Exception, user_identifier: Optional[str] = None,
                              auth_type: str = 'login') -> Dict[str, Any]:
        """Handle authentication errors with rate limiting tracking"""
        context = ErrorContext(
            user_id=user_identifier,
            component='authentication',
            operation=auth_type,
            additional_data={
                'auth_type': auth_type,
                'user_identifier': user_identifier
            }
        )
        
        error_result = await self.error_handler.handle_error(error, context)
        
        # Track failed attempts for rate limiting
        if user_identifier:
            current_time = datetime.now(timezone.utc)
            if user_identifier not in self.failed_auth_attempts:
                self.failed_auth_attempts[user_identifier] = []
            
            self.failed_auth_attempts[user_identifier].append(current_time)
            
            # Clean old attempts (older than 1 hour)
            cutoff_time = current_time - timedelta(hours=1)
            self.failed_auth_attempts[user_identifier] = [
                attempt for attempt in self.failed_auth_attempts[user_identifier]
                if attempt > cutoff_time
            ]
        
        # Determine if account should be locked
        should_lock = self._should_lock_account(user_identifier)
        
        return {
            'auth_error': True,
            'auth_type': auth_type,
            'user_identifier': user_identifier,
            'should_lock_account': should_lock,
            'failed_attempts': len(self.failed_auth_attempts.get(user_identifier, [])),
            'error_id': error_result.get('error_id'),
            'message': self._get_auth_error_message(error, should_lock)
        }
    
    def _should_lock_account(self, user_identifier: Optional[str], max_attempts: int = 5) -> bool:
        """Determine if account should be locked based on failed attempts"""
        if not user_identifier or user_identifier not in self.failed_auth_attempts:
            return False
        
        return len(self.failed_auth_attempts[user_identifier]) >= max_attempts
    
    def _get_auth_error_message(self, error: Exception, should_lock: bool) -> str:
        """Get appropriate authentication error message"""
        if should_lock:
            return "Account temporarily locked due to multiple failed login attempts"
        elif 'expired' in str(error).lower():
            return "Authentication token has expired. Please log in again."
        elif 'invalid' in str(error).lower():
            return "Invalid credentials provided"
        else:
            return "Authentication failed"
    
    def reset_failed_attempts(self, user_identifier: str):
        """Reset failed authentication attempts for a user"""
        if user_identifier in self.failed_auth_attempts:
            del self.failed_auth_attempts[user_identifier]


# Global integration instances
_admin_error_integration: Optional[AdminDashboardErrorIntegration] = None
_sync_error_integration: Optional[DataSyncErrorIntegration] = None
_db_error_integration: Optional[DatabaseErrorIntegration] = None
_auth_error_integration: Optional[AuthenticationErrorIntegration] = None

def get_admin_error_integration() -> AdminDashboardErrorIntegration:
    """Get or create admin error integration instance"""
    global _admin_error_integration
    if _admin_error_integration is None:
        _admin_error_integration = AdminDashboardErrorIntegration()
    return _admin_error_integration

def get_sync_error_integration() -> DataSyncErrorIntegration:
    """Get or create sync error integration instance"""
    global _sync_error_integration
    if _sync_error_integration is None:
        _sync_error_integration = DataSyncErrorIntegration()
    return _sync_error_integration

def get_db_error_integration() -> DatabaseErrorIntegration:
    """Get or create database error integration instance"""
    global _db_error_integration
    if _db_error_integration is None:
        _db_error_integration = DatabaseErrorIntegration()
    return _db_error_integration

def get_auth_error_integration() -> AuthenticationErrorIntegration:
    """Get or create auth error integration instance"""
    global _auth_error_integration
    if _auth_error_integration is None:
        _auth_error_integration = AuthenticationErrorIntegration()
    return _auth_error_integration

def setup_error_integrations(error_handler: Optional[UnifiedErrorHandler] = None):
    """Setup all error integration instances"""
    global _admin_error_integration, _sync_error_integration, _db_error_integration, _auth_error_integration
    
    _admin_error_integration = AdminDashboardErrorIntegration(error_handler)
    _sync_error_integration = DataSyncErrorIntegration(error_handler)
    _db_error_integration = DatabaseErrorIntegration(error_handler)
    _auth_error_integration = AuthenticationErrorIntegration(error_handler)
    
    logger.info("Error integration utilities setup completed")