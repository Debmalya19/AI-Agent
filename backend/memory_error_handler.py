"""
Memory Error Handler for graceful error handling and recovery mechanisms.

This module provides comprehensive error handling for the memory layer system,
including fallback strategies, circuit breaker patterns, and error monitoring.
"""

import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from contextlib import contextmanager
import threading
from functools import wraps


class ErrorType(Enum):
    """Types of errors that can occur in the memory system."""
    DATABASE_CONNECTION = "database_connection"
    DATABASE_QUERY = "database_query"
    CACHE_CONNECTION = "cache_connection"
    CACHE_OPERATION = "cache_operation"
    CONTEXT_RETRIEVAL = "context_retrieval"
    TOOL_ANALYTICS = "tool_analytics"
    MEMORY_STORAGE = "memory_storage"
    CONFIGURATION = "configuration"


class FallbackStrategy(Enum):
    """Fallback strategies for different error scenarios."""
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    USE_CACHE = "use_cache"
    USE_DATABASE = "use_database"
    RETURN_EMPTY = "return_empty"
    USE_DEFAULT = "use_default"
    FAIL_GRACEFULLY = "fail_gracefully"


@dataclass
class ErrorMetrics:
    """Metrics for tracking error occurrences and patterns."""
    error_type: ErrorType
    error_count: int
    last_error_time: datetime
    total_recovery_time: float
    success_rate: float
    fallback_used: Optional[FallbackStrategy] = None


@dataclass
class CircuitBreakerState:
    """State information for circuit breaker pattern."""
    is_open: bool = False
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None
    success_count: int = 0


class CircuitBreaker:
    """Circuit breaker implementation for external dependencies."""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: tuple = (Exception,)):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.state = CircuitBreakerState()
        self._lock = threading.Lock()
        
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker to a function."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self._call_with_circuit_breaker(func, *args, **kwargs)
        return wrapper
    
    def _call_with_circuit_breaker(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker logic."""
        with self._lock:
            if self._should_attempt_call():
                try:
                    result = func(*args, **kwargs)
                    self._on_success()
                    return result
                except self.expected_exception as e:
                    self._on_failure()
                    raise e
            else:
                raise Exception("Circuit breaker is OPEN - calls are blocked")
    
    def _should_attempt_call(self) -> bool:
        """Determine if a call should be attempted based on circuit state."""
        if not self.state.is_open:
            return True
            
        if (self.state.next_attempt_time and 
            datetime.now() >= self.state.next_attempt_time):
            return True
            
        return False
    
    def _on_success(self):
        """Handle successful call."""
        self.state.failure_count = 0
        self.state.success_count += 1
        if self.state.is_open:
            self.state.is_open = False
            self.state.next_attempt_time = None
    
    def _on_failure(self):
        """Handle failed call."""
        self.state.failure_count += 1
        self.state.last_failure_time = datetime.now()
        
        if self.state.failure_count >= self.failure_threshold:
            self.state.is_open = True
            self.state.next_attempt_time = (
                datetime.now() + timedelta(seconds=self.recovery_timeout)
            )


class MemoryErrorHandler:
    """
    Central error handler for memory layer operations.
    
    Provides graceful error handling, fallback strategies, and recovery mechanisms
    for various memory system components.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_metrics: Dict[ErrorType, ErrorMetrics] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._setup_circuit_breakers()
        
    def _setup_circuit_breakers(self):
        """Initialize circuit breakers for external dependencies."""
        self.circuit_breakers = {
            'database': CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=30,
                expected_exception=(Exception,)
            ),
            'cache': CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=15,
                expected_exception=(Exception,)
            ),
            'external_api': CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=60,
                expected_exception=(Exception,)
            )
        }
    
    def handle_database_error(self, error: Exception, operation: str = "unknown") -> FallbackStrategy:
        """
        Handle database-related errors with appropriate fallback strategies.
        
        Args:
            error: The database error that occurred
            operation: Description of the operation that failed
            
        Returns:
            FallbackStrategy: The recommended fallback strategy
        """
        # Determine error type and fallback strategy based on error message
        if "connection" in str(error).lower():
            error_type = ErrorType.DATABASE_CONNECTION
            self._record_error(error_type, error, {"operation": operation})
            self.logger.warning(f"Database connection error in {operation}: {error}")
            return FallbackStrategy.USE_CACHE
        elif "timeout" in str(error).lower():
            error_type = ErrorType.DATABASE_CONNECTION  # Timeout is connection-related
            self._record_error(error_type, error, {"operation": operation})
            self.logger.warning(f"Database timeout in {operation}: {error}")
            return FallbackStrategy.RETRY_WITH_BACKOFF
        elif "query" in str(error).lower() or "syntax" in str(error).lower():
            error_type = ErrorType.DATABASE_QUERY
            self._record_error(error_type, error, {"operation": operation})
            self.logger.error(f"Database query error in {operation}: {error}")
            return FallbackStrategy.RETURN_EMPTY
        else:
            error_type = ErrorType.DATABASE_CONNECTION
            self._record_error(error_type, error, {"operation": operation})
            self.logger.error(f"Database error in {operation}: {error}")
            return FallbackStrategy.RETURN_EMPTY
    
    def handle_cache_error(self, error: Exception, operation: str = "unknown") -> FallbackStrategy:
        """
        Handle cache-related errors with appropriate fallback strategies.
        
        Args:
            error: The cache error that occurred
            operation: Description of the operation that failed
            
        Returns:
            FallbackStrategy: The recommended fallback strategy
        """
        error_type = ErrorType.CACHE_CONNECTION
        if "operation" in str(error).lower():
            error_type = ErrorType.CACHE_OPERATION
            
        self._record_error(error_type, error, {"operation": operation})
        
        if "connection" in str(error).lower():
            self.logger.warning(f"Cache connection error in {operation}: {error}")
            return FallbackStrategy.USE_DATABASE
        else:
            self.logger.warning(f"Cache operation error in {operation}: {error}")
            return FallbackStrategy.USE_DATABASE
    
    def handle_context_error(self, error: Exception, query: str = "") -> FallbackStrategy:
        """
        Handle context retrieval errors with appropriate fallback strategies.
        
        Args:
            error: The context retrieval error that occurred
            query: The query that caused the error
            
        Returns:
            FallbackStrategy: The recommended fallback strategy
        """
        self._record_error(
            ErrorType.CONTEXT_RETRIEVAL, 
            error, 
            {"query_length": len(query)}
        )
        
        self.logger.warning(f"Context retrieval error for query '{query[:50]}...': {error}")
        return FallbackStrategy.RETURN_EMPTY
    
    def handle_tool_analytics_error(self, error: Exception, tool_name: str = "") -> FallbackStrategy:
        """
        Handle tool analytics errors with appropriate fallback strategies.
        
        Args:
            error: The tool analytics error that occurred
            tool_name: The tool that caused the error
            
        Returns:
            FallbackStrategy: The recommended fallback strategy
        """
        self._record_error(
            ErrorType.TOOL_ANALYTICS, 
            error, 
            {"tool_name": tool_name}
        )
        
        self.logger.warning(f"Tool analytics error for tool '{tool_name}': {error}")
        return FallbackStrategy.USE_DEFAULT
    
    def handle_memory_storage_error(self, error: Exception, data_size: int = 0) -> FallbackStrategy:
        """
        Handle memory storage errors with appropriate fallback strategies.
        
        Args:
            error: The memory storage error that occurred
            data_size: Size of data that failed to store
            
        Returns:
            FallbackStrategy: The recommended fallback strategy
        """
        self._record_error(
            ErrorType.MEMORY_STORAGE, 
            error, 
            {"data_size": data_size}
        )
        
        if "space" in str(error).lower() or "memory" in str(error).lower():
            self.logger.error(f"Memory storage space error (size: {data_size}): {error}")
            return FallbackStrategy.FAIL_GRACEFULLY
        else:
            self.logger.warning(f"Memory storage error (size: {data_size}): {error}")
            return FallbackStrategy.RETRY_WITH_BACKOFF
    
    def _record_error(self, error_type: ErrorType, error: Exception, context: Dict[str, Any]):
        """Record error metrics for monitoring and analysis."""
        current_time = datetime.now()
        
        if error_type not in self.error_metrics:
            self.error_metrics[error_type] = ErrorMetrics(
                error_type=error_type,
                error_count=0,
                last_error_time=current_time,
                total_recovery_time=0.0,
                success_rate=1.0
            )
        
        metrics = self.error_metrics[error_type]
        metrics.error_count += 1
        metrics.last_error_time = current_time
        
        # Log error with context
        self.logger.error(
            f"Memory system error - Type: {error_type.value}, "
            f"Error: {str(error)}, Context: {context}"
        )
    
    def retry_operation(self, operation_func: Callable, operation: str, max_retries: int = 3, *args, **kwargs):
        """
        Retry an operation with exponential backoff.
        
        Args:
            operation_func: The function to retry
            operation: Description of the operation
            max_retries: Maximum number of retry attempts
            *args, **kwargs: Arguments to pass to the operation function
            
        Returns:
            The result of the successful operation
        """
        retries = 0
        last_exception = None
        
        while retries <= max_retries:
            try:
                return operation_func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                retries += 1
                if retries > max_retries:
                    self.logger.error(f"Operation '{operation}' failed after {max_retries} retries: {e}")
                    raise e
                else:
                    wait_time = min(2 ** retries, 30)  # Exponential backoff, max 30s
                    self.logger.warning(
                        f"Operation '{operation}' failed (attempt {retries}/{max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
    
    @contextmanager
    def error_recovery_context(self, operation: str, max_retries: int = 3):
        """
        Context manager for automatic error recovery with retries.
        
        Args:
            operation: Description of the operation
            max_retries: Maximum number of retry attempts
        """
        retries = 0
        
        while retries <= max_retries:
            try:
                yield retries
                break  # Success, exit the loop
            except Exception as e:
                retries += 1
                if retries > max_retries:
                    self.logger.error(f"Operation '{operation}' failed after {max_retries} retries: {e}")
                    raise e
                else:
                    wait_time = min(2 ** retries, 30)  # Exponential backoff, max 30s
                    self.logger.warning(
                        f"Operation '{operation}' failed (attempt {retries}/{max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        return self.circuit_breakers.get(name)
    
    def get_error_metrics(self) -> Dict[ErrorType, ErrorMetrics]:
        """Get current error metrics for monitoring."""
        return self.error_metrics.copy()
    
    def reset_error_metrics(self, error_type: Optional[ErrorType] = None):
        """Reset error metrics for monitoring."""
        if error_type:
            if error_type in self.error_metrics:
                del self.error_metrics[error_type]
        else:
            self.error_metrics.clear()
    
    def is_system_healthy(self) -> bool:
        """Check if the memory system is healthy based on error rates."""
        current_time = datetime.now()
        recent_threshold = current_time - timedelta(minutes=5)
        
        for metrics in self.error_metrics.values():
            if (metrics.last_error_time > recent_threshold and 
                metrics.error_count > 10):
                return False
        
        return True
    
    def get_health_report(self) -> Dict[str, Any]:
        """Generate a comprehensive health report."""
        return {
            "is_healthy": self.is_system_healthy(),
            "error_metrics": {
                error_type.value: {
                    "error_count": metrics.error_count,
                    "last_error": metrics.last_error_time.isoformat() if metrics.last_error_time else None,
                    "success_rate": metrics.success_rate
                }
                for error_type, metrics in self.error_metrics.items()
            },
            "circuit_breakers": {
                name: {
                    "is_open": breaker.state.is_open,
                    "failure_count": breaker.state.failure_count,
                    "success_count": breaker.state.success_count
                }
                for name, breaker in self.circuit_breakers.items()
            },
            "timestamp": datetime.now().isoformat()
        }


# Decorator for automatic error handling
def handle_memory_errors(error_handler: MemoryErrorHandler, operation: str = "unknown"):
    """
    Decorator for automatic error handling in memory operations.
    
    Args:
        error_handler: The MemoryErrorHandler instance to use
        operation: Description of the operation being performed
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Determine error type and handle accordingly
                if "database" in str(e).lower() or "sql" in str(e).lower():
                    fallback = error_handler.handle_database_error(e, operation)
                elif "cache" in str(e).lower() or "redis" in str(e).lower():
                    fallback = error_handler.handle_cache_error(e, operation)
                elif "context" in str(e).lower():
                    fallback = error_handler.handle_context_error(e)
                else:
                    # Generic error handling
                    error_handler._record_error(ErrorType.MEMORY_STORAGE, e, {"operation": operation})
                    fallback = FallbackStrategy.FAIL_GRACEFULLY
                
                # Apply fallback strategy
                if fallback in [FallbackStrategy.RETURN_EMPTY, FallbackStrategy.USE_CACHE, FallbackStrategy.USE_DATABASE]:
                    return None
                elif fallback == FallbackStrategy.USE_DEFAULT:
                    return {}
                elif fallback == FallbackStrategy.FAIL_GRACEFULLY:
                    return None
                else:
                    raise e
        return wrapper
    return decorator