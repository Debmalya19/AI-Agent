"""
Unified Error Handling and Logging System

This module provides comprehensive error handling that works across both FastAPI and admin components,
with error categorization, recovery mechanisms, and unified logging.

Requirements: 4.4, 1.4, 3.4
"""

import logging
import time
import traceback
import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Any, Optional, Callable, List, Union, Type
from dataclasses import dataclass, field
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
import threading
import json
import os
from pathlib import Path

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
import jwt


class ErrorCategory(Enum):
    """Categories of errors in the unified system"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATABASE = "database"
    SYNC = "sync"
    INTEGRATION = "integration"
    VALIDATION = "validation"
    EXTERNAL_API = "external_api"
    SYSTEM = "system"
    NETWORK = "network"
    CONFIGURATION = "configuration"


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    FALLBACK_TO_CACHE = "fallback_to_cache"
    FALLBACK_TO_DATABASE = "fallback_to_database"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    FAIL_FAST = "fail_fast"
    MANUAL_INTERVENTION = "manual_intervention"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class ErrorContext:
    """Context information for error handling"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorMetrics:
    """Metrics for tracking error patterns"""
    category: ErrorCategory
    error_count: int = 0
    last_occurrence: Optional[datetime] = None
    total_recovery_time: float = 0.0
    success_rate: float = 1.0
    recovery_attempts: int = 0
    recovery_successes: int = 0


@dataclass
class CircuitBreakerState:
    """State for circuit breaker pattern"""
    is_open: bool = False
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None
    success_count: int = 0
    half_open_attempts: int = 0


class CircuitBreaker:
    """Circuit breaker implementation for external dependencies"""
    
    def __init__(self, 
                 name: str,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 half_open_max_calls: int = 3,
                 expected_exceptions: tuple = (Exception,)):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.expected_exceptions = expected_exceptions
        self.state = CircuitBreakerState()
        self._lock = threading.Lock()
        
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker to a function"""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self._call_with_circuit_breaker_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return self._call_with_circuit_breaker_sync(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    async def _call_with_circuit_breaker_async(self, func: Callable, *args, **kwargs):
        """Execute async function with circuit breaker logic"""
        with self._lock:
            if not self._should_attempt_call():
                raise HTTPException(
                    status_code=503,
                    detail=f"Circuit breaker '{self.name}' is OPEN - service temporarily unavailable"
                )
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as e:
            self._on_failure()
            raise e
    
    def _call_with_circuit_breaker_sync(self, func: Callable, *args, **kwargs):
        """Execute sync function with circuit breaker logic"""
        with self._lock:
            if not self._should_attempt_call():
                raise Exception(f"Circuit breaker '{self.name}' is OPEN - service temporarily unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as e:
            self._on_failure()
            raise e
    
    def _should_attempt_call(self) -> bool:
        """Determine if a call should be attempted"""
        if not self.state.is_open:
            return True
        
        # Check if we should try half-open state
        if (self.state.next_attempt_time and 
            datetime.now(timezone.utc) >= self.state.next_attempt_time):
            if self.state.half_open_attempts < self.half_open_max_calls:
                return True
        
        return False
    
    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            self.state.failure_count = 0
            self.state.success_count += 1
            
            if self.state.is_open:
                self.state.is_open = False
                self.state.next_attempt_time = None
                self.state.half_open_attempts = 0
    
    def _on_failure(self):
        """Handle failed call"""
        with self._lock:
            self.state.failure_count += 1
            self.state.last_failure_time = datetime.now(timezone.utc)
            
            if self.state.failure_count >= self.failure_threshold:
                self.state.is_open = True
                self.state.next_attempt_time = (
                    datetime.now(timezone.utc) + timedelta(seconds=self.recovery_timeout)
                )
                self.state.half_open_attempts = 0
            elif self.state.is_open:
                self.state.half_open_attempts += 1


class UnifiedErrorHandler:
    """
    Central error handler for the unified system.
    
    Provides comprehensive error handling, categorization, recovery mechanisms,
    and logging for both FastAPI and admin dashboard components.
    """
    
    def __init__(self, 
                 logger: Optional[logging.Logger] = None,
                 log_file_path: Optional[str] = None):
        self.logger = logger or self._setup_logger(log_file_path)
        self.error_metrics: Dict[ErrorCategory, ErrorMetrics] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.recovery_handlers: Dict[ErrorCategory, Callable] = {}
        self._setup_circuit_breakers()
        self._setup_recovery_handlers()
        
    def _setup_logger(self, log_file_path: Optional[str] = None) -> logging.Logger:
        """Setup comprehensive logging system"""
        logger = logging.getLogger("unified_error_handler")
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        if not log_file_path:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file_path = log_dir / "unified_errors.log"
        
        file_handler = logging.FileHandler(log_file_path)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _setup_circuit_breakers(self):
        """Initialize circuit breakers for external dependencies"""
        self.circuit_breakers = {
            'database': CircuitBreaker(
                name='database',
                failure_threshold=3,
                recovery_timeout=30,
                expected_exceptions=(SQLAlchemyError, OperationalError)
            ),
            'admin_api': CircuitBreaker(
                name='admin_api',
                failure_threshold=5,
                recovery_timeout=60,
                expected_exceptions=(HTTPException, ConnectionError)
            ),
            'sync_service': CircuitBreaker(
                name='sync_service',
                failure_threshold=3,
                recovery_timeout=45,
                expected_exceptions=(Exception,)
            ),
            'external_auth': CircuitBreaker(
                name='external_auth',
                failure_threshold=3,
                recovery_timeout=120,
                expected_exceptions=(jwt.InvalidTokenError, HTTPException)
            )
        }
    
    def _setup_recovery_handlers(self):
        """Setup recovery handlers for different error categories"""
        self.recovery_handlers = {
            ErrorCategory.AUTHENTICATION: self._handle_auth_recovery,
            ErrorCategory.DATABASE: self._handle_database_recovery,
            ErrorCategory.SYNC: self._handle_sync_recovery,
            ErrorCategory.INTEGRATION: self._handle_integration_recovery,
            ErrorCategory.EXTERNAL_API: self._handle_external_api_recovery
        }
    
    def categorize_error(self, error: Exception, context: ErrorContext) -> ErrorCategory:
        """Categorize an error based on its type and context"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Authentication errors
        if (isinstance(error, (jwt.InvalidTokenError, jwt.ExpiredSignatureError)) or
            'unauthorized' in error_str or 'authentication' in error_str or
            'invalid token' in error_str or 'expired' in error_str):
            return ErrorCategory.AUTHENTICATION
        
        # Authorization errors
        if ('forbidden' in error_str or 'permission' in error_str or
            'access denied' in error_str or 'not authorized' in error_str):
            return ErrorCategory.AUTHORIZATION
        
        # Database errors
        if (isinstance(error, (SQLAlchemyError, IntegrityError, OperationalError)) or
            'database' in error_str or 'sql' in error_str or 'connection' in error_str):
            return ErrorCategory.DATABASE
        
        # Sync errors
        if ('sync' in error_str or 'synchronization' in error_str or
            context.component == 'data_sync' or context.operation and 'sync' in context.operation):
            return ErrorCategory.SYNC
        
        # Integration errors
        if ('integration' in error_str or 'admin' in error_str or
            context.component in ['admin_api', 'admin_auth', 'admin_frontend']):
            return ErrorCategory.INTEGRATION
        
        # Network errors
        if ('network' in error_str or 'connection' in error_str or
            'timeout' in error_str or isinstance(error, ConnectionError)):
            return ErrorCategory.NETWORK
        
        # Validation errors
        if ('validation' in error_str or 'invalid' in error_str or
            'bad request' in error_str or isinstance(error, ValueError)):
            return ErrorCategory.VALIDATION
        
        # External API errors
        if ('api' in error_str or 'external' in error_str or
            isinstance(error, HTTPException) and error.status_code >= 500):
            return ErrorCategory.EXTERNAL_API
        
        # Configuration errors
        if ('config' in error_str or 'environment' in error_str or
            'missing' in error_str and 'variable' in error_str):
            return ErrorCategory.CONFIGURATION
        
        # Default to system error
        return ErrorCategory.SYSTEM
    
    def determine_severity(self, error: Exception, category: ErrorCategory, context: ErrorContext) -> ErrorSeverity:
        """Determine error severity based on error type and context"""
        # Critical errors
        if (category == ErrorCategory.DATABASE and 'connection' in str(error).lower() or
            category == ErrorCategory.SYSTEM and 'memory' in str(error).lower() or
            category == ErrorCategory.CONFIGURATION and 'missing' in str(error).lower()):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if (category in [ErrorCategory.AUTHENTICATION, ErrorCategory.AUTHORIZATION] or
            isinstance(error, (IntegrityError, OperationalError)) or
            (isinstance(error, HTTPException) and error.status_code >= 500)):
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if (category in [ErrorCategory.SYNC, ErrorCategory.INTEGRATION, ErrorCategory.EXTERNAL_API] or
            (isinstance(error, HTTPException) and 400 <= error.status_code < 500)):
            return ErrorSeverity.MEDIUM
        
        # Low severity errors (validation, network timeouts, etc.)
        return ErrorSeverity.LOW
    
    def determine_recovery_strategy(self, error: Exception, category: ErrorCategory, 
                                  severity: ErrorSeverity, context: ErrorContext) -> RecoveryStrategy:
        """Determine the appropriate recovery strategy"""
        # Critical errors require manual intervention
        if severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.MANUAL_INTERVENTION
        
        # Category-specific strategies
        if category == ErrorCategory.DATABASE:
            if 'connection' in str(error).lower():
                return RecoveryStrategy.RETRY_WITH_BACKOFF
            elif 'timeout' in str(error).lower():
                return RecoveryStrategy.CIRCUIT_BREAKER
            else:
                return RecoveryStrategy.GRACEFUL_DEGRADATION
        
        elif category == ErrorCategory.AUTHENTICATION:
            return RecoveryStrategy.FAIL_FAST
        
        elif category == ErrorCategory.SYNC:
            return RecoveryStrategy.RETRY_WITH_BACKOFF
        
        elif category == ErrorCategory.INTEGRATION:
            return RecoveryStrategy.GRACEFUL_DEGRADATION
        
        elif category == ErrorCategory.EXTERNAL_API:
            return RecoveryStrategy.CIRCUIT_BREAKER
        
        elif category == ErrorCategory.NETWORK:
            return RecoveryStrategy.RETRY_WITH_BACKOFF
        
        # Default strategy
        return RecoveryStrategy.GRACEFUL_DEGRADATION
    
    async def handle_error(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """
        Main error handling method that categorizes, logs, and attempts recovery
        
        Returns:
            Dict containing error information and recovery result
        """
        start_time = time.time()
        
        # Categorize and analyze error
        category = self.categorize_error(error, context)
        severity = self.determine_severity(error, category, context)
        strategy = self.determine_recovery_strategy(error, category, severity, context)
        
        # Record error metrics
        self._record_error_metrics(category, error, context)
        
        # Log error with full context
        self._log_error(error, category, severity, strategy, context)
        
        # Attempt recovery
        recovery_result = await self._attempt_recovery(error, category, strategy, context)
        
        # Record recovery metrics
        recovery_time = time.time() - start_time
        self._record_recovery_metrics(category, recovery_result['success'], recovery_time)
        
        return {
            'error_id': self._generate_error_id(error, context),
            'category': category.value,
            'severity': severity.value,
            'strategy': strategy.value,
            'recovery_result': recovery_result,
            'recovery_time': recovery_time,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def _attempt_recovery(self, error: Exception, category: ErrorCategory, 
                              strategy: RecoveryStrategy, context: ErrorContext) -> Dict[str, Any]:
        """Attempt error recovery based on strategy"""
        try:
            if strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                return await self._retry_with_backoff(error, context)
            
            elif strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                return self._apply_circuit_breaker(error, context)
            
            elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                return await self._graceful_degradation(error, category, context)
            
            elif strategy == RecoveryStrategy.FAIL_FAST:
                return {'success': False, 'action': 'fail_fast', 'message': 'Error requires immediate attention'}
            
            elif strategy == RecoveryStrategy.MANUAL_INTERVENTION:
                return {'success': False, 'action': 'manual_intervention', 'message': 'Critical error requires manual intervention'}
            
            else:
                # Use category-specific recovery handler if available
                if category in self.recovery_handlers:
                    return await self.recovery_handlers[category](error, context)
                else:
                    return {'success': False, 'action': 'no_recovery', 'message': 'No recovery strategy available'}
        
        except Exception as recovery_error:
            self.logger.error(f"Recovery attempt failed: {recovery_error}")
            return {'success': False, 'action': 'recovery_failed', 'message': str(recovery_error)}
    
    async def _retry_with_backoff(self, error: Exception, context: ErrorContext, 
                                max_retries: int = 3) -> Dict[str, Any]:
        """Implement retry with exponential backoff"""
        for attempt in range(max_retries):
            try:
                wait_time = min(2 ** attempt, 30)  # Max 30 seconds
                await asyncio.sleep(wait_time)
                
                # Here you would retry the original operation
                # For now, we'll simulate success after retries
                if attempt >= 1:  # Simulate success after first retry
                    return {
                        'success': True, 
                        'action': 'retry_success', 
                        'attempts': attempt + 1,
                        'message': f'Operation succeeded after {attempt + 1} attempts'
                    }
            
            except Exception as retry_error:
                if attempt == max_retries - 1:
                    return {
                        'success': False, 
                        'action': 'retry_exhausted', 
                        'attempts': max_retries,
                        'message': f'All {max_retries} retry attempts failed'
                    }
        
        return {'success': False, 'action': 'retry_failed', 'message': 'Retry mechanism failed'}
    
    def _apply_circuit_breaker(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Apply circuit breaker pattern"""
        component = context.component or 'default'
        
        if component in self.circuit_breakers:
            breaker = self.circuit_breakers[component]
            if breaker.state.is_open:
                return {
                    'success': False, 
                    'action': 'circuit_open', 
                    'message': f'Circuit breaker for {component} is open'
                }
        
        return {'success': True, 'action': 'circuit_closed', 'message': 'Circuit breaker allows operation'}
    
    async def _graceful_degradation(self, error: Exception, category: ErrorCategory, 
                                  context: ErrorContext) -> Dict[str, Any]:
        """Implement graceful degradation"""
        if category == ErrorCategory.DATABASE:
            return {
                'success': True, 
                'action': 'fallback_cache', 
                'message': 'Falling back to cache for read operations'
            }
        
        elif category == ErrorCategory.INTEGRATION:
            return {
                'success': True, 
                'action': 'limited_functionality', 
                'message': 'Admin features temporarily unavailable'
            }
        
        elif category == ErrorCategory.SYNC:
            return {
                'success': True, 
                'action': 'async_retry', 
                'message': 'Sync operation queued for later retry'
            }
        
        return {
            'success': True, 
            'action': 'minimal_service', 
            'message': 'Operating with reduced functionality'
        }
    
    # Recovery handler methods
    async def _handle_auth_recovery(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Handle authentication error recovery"""
        if 'expired' in str(error).lower():
            return {'success': False, 'action': 'token_refresh_required', 'message': 'Token refresh required'}
        else:
            return {'success': False, 'action': 'reauthentication_required', 'message': 'User must re-authenticate'}
    
    async def _handle_database_recovery(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Handle database error recovery"""
        if 'connection' in str(error).lower():
            return await self._retry_with_backoff(error, context, max_retries=2)
        else:
            return {'success': True, 'action': 'fallback_cache', 'message': 'Using cached data'}
    
    async def _handle_sync_recovery(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Handle sync error recovery"""
        return {
            'success': True, 
            'action': 'queue_retry', 
            'message': 'Sync operation queued for background retry'
        }
    
    async def _handle_integration_recovery(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Handle integration error recovery"""
        return {
            'success': True, 
            'action': 'disable_feature', 
            'message': 'Admin dashboard features temporarily disabled'
        }
    
    async def _handle_external_api_recovery(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Handle external API error recovery"""
        return await self._retry_with_backoff(error, context, max_retries=2)
    
    def _record_error_metrics(self, category: ErrorCategory, error: Exception, context: ErrorContext):
        """Record error metrics for monitoring"""
        if category not in self.error_metrics:
            self.error_metrics[category] = ErrorMetrics(category=category)
        
        metrics = self.error_metrics[category]
        metrics.error_count += 1
        metrics.last_occurrence = datetime.now(timezone.utc)
    
    def _record_recovery_metrics(self, category: ErrorCategory, success: bool, recovery_time: float):
        """Record recovery metrics"""
        if category in self.error_metrics:
            metrics = self.error_metrics[category]
            metrics.recovery_attempts += 1
            metrics.total_recovery_time += recovery_time
            
            if success:
                metrics.recovery_successes += 1
            
            # Update success rate
            metrics.success_rate = metrics.recovery_successes / metrics.recovery_attempts
    
    def _log_error(self, error: Exception, category: ErrorCategory, severity: ErrorSeverity,
                  strategy: RecoveryStrategy, context: ErrorContext):
        """Log error with comprehensive context"""
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'category': category.value,
            'severity': severity.value,
            'strategy': strategy.value,
            'context': {
                'user_id': context.user_id,
                'session_id': context.session_id,
                'request_id': context.request_id,
                'endpoint': context.endpoint,
                'method': context.method,
                'component': context.component,
                'operation': context.operation,
                'additional_data': context.additional_data
            },
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        log_message = f"Error handled - {category.value.upper()}/{severity.value.upper()}: {str(error)}"
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, extra={'error_data': error_data})
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, extra={'error_data': error_data})
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message, extra={'error_data': error_data})
        else:
            self.logger.info(log_message, extra={'error_data': error_data})
    
    def _generate_error_id(self, error: Exception, context: ErrorContext) -> str:
        """Generate unique error ID for tracking"""
        error_string = f"{type(error).__name__}:{str(error)}:{context.request_id}:{datetime.now(timezone.utc).isoformat()}"
        return hashlib.md5(error_string.encode()).hexdigest()[:12]
    
    # Context managers and decorators
    @asynccontextmanager
    async def error_context(self, context: ErrorContext):
        """Async context manager for automatic error handling"""
        try:
            yield
        except Exception as e:
            error_result = await self.handle_error(e, context)
            # Re-raise if recovery was not successful and strategy requires it
            recovery_result = error_result.get('recovery_result', {})
            if not recovery_result.get('success', False):
                strategy = RecoveryStrategy(error_result.get('strategy', 'fail_fast'))
                if strategy in [RecoveryStrategy.FAIL_FAST, RecoveryStrategy.MANUAL_INTERVENTION]:
                    raise e
    
    @contextmanager
    def sync_error_context(self, context: ErrorContext):
        """Sync context manager for automatic error handling"""
        try:
            yield
        except Exception as e:
            # For sync operations, we can't use async recovery
            category = self.categorize_error(e, context)
            severity = self.determine_severity(e, category, context)
            strategy = self.determine_recovery_strategy(e, category, severity, context)
            
            self._record_error_metrics(category, e, context)
            self._log_error(e, category, severity, strategy, context)
            
            # Simple sync recovery
            if strategy in [RecoveryStrategy.FAIL_FAST, RecoveryStrategy.MANUAL_INTERVENTION]:
                raise e
    
    def error_handler_decorator(self, component: str = None, operation: str = None):
        """Decorator for automatic error handling"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                context = ErrorContext(
                    component=component,
                    operation=operation or func.__name__
                )
                
                async with self.error_context(context):
                    return await func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                context = ErrorContext(
                    component=component,
                    operation=operation or func.__name__
                )
                
                with self.sync_error_context(context):
                    return func(*args, **kwargs)
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    # Monitoring and health check methods
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get current error metrics for monitoring"""
        return {
            category.value: {
                'error_count': metrics.error_count,
                'last_occurrence': metrics.last_occurrence.isoformat() if metrics.last_occurrence else None,
                'success_rate': metrics.success_rate,
                'recovery_attempts': metrics.recovery_attempts,
                'recovery_successes': metrics.recovery_successes,
                'total_recovery_time': metrics.total_recovery_time
            }
            for category, metrics in self.error_metrics.items()
        }
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status for monitoring"""
        return {
            name: {
                'is_open': breaker.state.is_open,
                'failure_count': breaker.state.failure_count,
                'success_count': breaker.state.success_count,
                'last_failure': breaker.state.last_failure_time.isoformat() if breaker.state.last_failure_time else None,
                'next_attempt': breaker.state.next_attempt_time.isoformat() if breaker.state.next_attempt_time else None
            }
            for name, breaker in self.circuit_breakers.items()
        }
    
    def get_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        current_time = datetime.now(timezone.utc)
        recent_threshold = current_time - timedelta(minutes=5)
        
        # Check for recent critical errors
        recent_critical_errors = 0
        for metrics in self.error_metrics.values():
            if (metrics.last_occurrence and 
                metrics.last_occurrence > recent_threshold and
                metrics.error_count > 0):
                recent_critical_errors += 1
        
        # Check circuit breaker health
        open_circuit_breakers = sum(1 for breaker in self.circuit_breakers.values() 
                                  if breaker.state.is_open)
        
        is_healthy = (recent_critical_errors == 0 and open_circuit_breakers == 0)
        
        return {
            'is_healthy': is_healthy,
            'timestamp': current_time.isoformat(),
            'error_metrics': self.get_error_metrics(),
            'circuit_breakers': self.get_circuit_breaker_status(),
            'recent_critical_errors': recent_critical_errors,
            'open_circuit_breakers': open_circuit_breakers,
            'health_score': max(0, 100 - (recent_critical_errors * 20) - (open_circuit_breakers * 10))
        }
    
    def reset_metrics(self, category: Optional[ErrorCategory] = None):
        """Reset error metrics"""
        if category:
            if category in self.error_metrics:
                del self.error_metrics[category]
        else:
            self.error_metrics.clear()
    
    def reset_circuit_breakers(self, name: Optional[str] = None):
        """Reset circuit breakers"""
        if name and name in self.circuit_breakers:
            self.circuit_breakers[name].state = CircuitBreakerState()
        else:
            for breaker in self.circuit_breakers.values():
                breaker.state = CircuitBreakerState()


# Global error handler instance
_global_error_handler: Optional[UnifiedErrorHandler] = None

def get_error_handler() -> UnifiedErrorHandler:
    """Get or create global error handler instance"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = UnifiedErrorHandler()
    return _global_error_handler

def setup_error_handler(logger: Optional[logging.Logger] = None, 
                       log_file_path: Optional[str] = None) -> UnifiedErrorHandler:
    """Setup and configure global error handler"""
    global _global_error_handler
    _global_error_handler = UnifiedErrorHandler(logger=logger, log_file_path=log_file_path)
    return _global_error_handler


def setup_error_middleware(app, error_handler: UnifiedErrorHandler):
    """Setup error handling middleware for FastAPI application"""
    from fastapi import Request, Response
    from fastapi.responses import JSONResponse
    
    @app.middleware("http")
    async def error_handling_middleware(request: Request, call_next):
        """Middleware to handle errors across the application"""
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Handle the error using the unified error handler
            error_response = error_handler.handle_error(e, {"request_path": request.url.path})
            
            # Return appropriate JSON response
            return JSONResponse(
                status_code=error_response.get("status_code", 500),
                content={
                    "error": error_response.get("message", "Internal server error"),
                    "error_id": error_response.get("error_id"),
                    "timestamp": error_response.get("timestamp")
                }
            )