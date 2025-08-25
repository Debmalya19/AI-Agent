"""
Unit tests for MemoryErrorHandler and error recovery mechanisms.

Tests cover error handling scenarios, fallback strategies, circuit breaker patterns,
and error monitoring functionality.
"""

import pytest
import time
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from memory_error_handler import (
    MemoryErrorHandler,
    ErrorType,
    FallbackStrategy,
    CircuitBreaker,
    CircuitBreakerState,
    ErrorMetrics,
    handle_memory_errors
)


class TestCircuitBreaker:
    """Test cases for CircuitBreaker implementation."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization with default values."""
        breaker = CircuitBreaker()
        
        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout == 60
        assert breaker.expected_exception == (Exception,)
        assert not breaker.state.is_open
        assert breaker.state.failure_count == 0
    
    def test_circuit_breaker_custom_parameters(self):
        """Test circuit breaker initialization with custom parameters."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=(ValueError, TypeError)
        )
        
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 30
        assert breaker.expected_exception == (ValueError, TypeError)
    
    def test_circuit_breaker_success_flow(self):
        """Test circuit breaker with successful function calls."""
        breaker = CircuitBreaker(failure_threshold=2)
        
        @breaker
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
        assert breaker.state.success_count == 1
        assert breaker.state.failure_count == 0
        assert not breaker.state.is_open
    
    def test_circuit_breaker_failure_flow(self):
        """Test circuit breaker with failing function calls."""
        breaker = CircuitBreaker(failure_threshold=2)
        
        @breaker
        def failing_function():
            raise ValueError("Test error")
        
        # First failure
        with pytest.raises(ValueError):
            failing_function()
        assert breaker.state.failure_count == 1
        assert not breaker.state.is_open
        
        # Second failure - should open circuit
        with pytest.raises(ValueError):
            failing_function()
        assert breaker.state.failure_count == 2
        assert breaker.state.is_open
        
        # Third call - should be blocked
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            failing_function()
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        @breaker
        def test_function(should_fail=True):
            if should_fail:
                raise ValueError("Test error")
            return "success"
        
        # Trigger circuit open
        with pytest.raises(ValueError):
            test_function()
        assert breaker.state.is_open
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Should allow one attempt and succeed
        result = test_function(should_fail=False)
        assert result == "success"
        assert not breaker.state.is_open
        assert breaker.state.success_count == 1


class TestMemoryErrorHandler:
    """Test cases for MemoryErrorHandler class."""
    
    @pytest.fixture
    def error_handler(self):
        """Create a MemoryErrorHandler instance for testing."""
        logger = Mock(spec=logging.Logger)
        return MemoryErrorHandler(logger=logger)
    
    def test_initialization(self, error_handler):
        """Test MemoryErrorHandler initialization."""
        assert error_handler.error_metrics == {}
        assert len(error_handler.circuit_breakers) == 3
        assert 'database' in error_handler.circuit_breakers
        assert 'cache' in error_handler.circuit_breakers
        assert 'external_api' in error_handler.circuit_breakers
    
    def test_handle_database_connection_error(self, error_handler):
        """Test handling of database connection errors."""
        error = Exception("connection refused")
        strategy = error_handler.handle_database_error(error, "test_operation")
        
        assert strategy == FallbackStrategy.USE_CACHE
        assert ErrorType.DATABASE_CONNECTION in error_handler.error_metrics
        assert error_handler.error_metrics[ErrorType.DATABASE_CONNECTION].error_count == 1
    
    def test_handle_database_query_error(self, error_handler):
        """Test handling of database query errors."""
        error = Exception("syntax error in query")
        strategy = error_handler.handle_database_error(error, "test_query")
        
        assert strategy == FallbackStrategy.RETURN_EMPTY
        assert ErrorType.DATABASE_QUERY in error_handler.error_metrics
    
    def test_handle_database_timeout_error(self, error_handler):
        """Test handling of database timeout errors."""
        error = Exception("query timeout exceeded")
        strategy = error_handler.handle_database_error(error, "slow_query")
        
        assert strategy == FallbackStrategy.RETRY_WITH_BACKOFF
        assert ErrorType.DATABASE_CONNECTION in error_handler.error_metrics
    
    def test_handle_cache_connection_error(self, error_handler):
        """Test handling of cache connection errors."""
        error = Exception("redis connection failed")
        strategy = error_handler.handle_cache_error(error, "cache_get")
        
        assert strategy == FallbackStrategy.USE_DATABASE
        assert ErrorType.CACHE_CONNECTION in error_handler.error_metrics
    
    def test_handle_cache_operation_error(self, error_handler):
        """Test handling of cache operation errors."""
        error = Exception("cache operation failed")
        strategy = error_handler.handle_cache_error(error, "cache_set")
        
        assert strategy == FallbackStrategy.USE_DATABASE
        assert ErrorType.CACHE_OPERATION in error_handler.error_metrics
    
    def test_handle_context_error(self, error_handler):
        """Test handling of context retrieval errors."""
        error = Exception("context retrieval failed")
        strategy = error_handler.handle_context_error(error, "test query")
        
        assert strategy == FallbackStrategy.RETURN_EMPTY
        assert ErrorType.CONTEXT_RETRIEVAL in error_handler.error_metrics
    
    def test_handle_tool_analytics_error(self, error_handler):
        """Test handling of tool analytics errors."""
        error = Exception("analytics calculation failed")
        strategy = error_handler.handle_tool_analytics_error(error, "test_tool")
        
        assert strategy == FallbackStrategy.USE_DEFAULT
        assert ErrorType.TOOL_ANALYTICS in error_handler.error_metrics
    
    def test_handle_memory_storage_space_error(self, error_handler):
        """Test handling of memory storage space errors."""
        error = Exception("insufficient memory space")
        strategy = error_handler.handle_memory_storage_error(error, 1024)
        
        assert strategy == FallbackStrategy.FAIL_GRACEFULLY
        assert ErrorType.MEMORY_STORAGE in error_handler.error_metrics
    
    def test_handle_memory_storage_generic_error(self, error_handler):
        """Test handling of generic memory storage errors."""
        error = Exception("storage operation failed")
        strategy = error_handler.handle_memory_storage_error(error, 512)
        
        assert strategy == FallbackStrategy.RETRY_WITH_BACKOFF
        assert ErrorType.MEMORY_STORAGE in error_handler.error_metrics
    
    def test_error_recovery_context_success(self, error_handler):
        """Test error recovery context with successful operation."""
        with error_handler.error_recovery_context("test_operation") as retry_count:
            assert retry_count == 0
            # Simulate successful operation
            result = "success"
        
        assert result == "success"
    
    def test_error_recovery_context_with_retries(self, error_handler):
        """Test error recovery context with retries."""
        call_count = 0
        
        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = error_handler.retry_operation(failing_operation, "test_operation", max_retries=3)
        
        assert result == "success"
        assert call_count == 3
    
    def test_error_recovery_context_max_retries_exceeded(self, error_handler):
        """Test error recovery context when max retries are exceeded."""
        def always_failing_operation():
            raise ValueError("Persistent failure")
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(ValueError, match="Persistent failure"):
                error_handler.retry_operation(always_failing_operation, "test_operation", max_retries=2)
    
    def test_get_circuit_breaker(self, error_handler):
        """Test getting circuit breaker by name."""
        db_breaker = error_handler.get_circuit_breaker('database')
        assert db_breaker is not None
        assert isinstance(db_breaker, CircuitBreaker)
        
        nonexistent_breaker = error_handler.get_circuit_breaker('nonexistent')
        assert nonexistent_breaker is None
    
    def test_get_error_metrics(self, error_handler):
        """Test getting error metrics."""
        # Generate some errors
        error_handler.handle_database_error(Exception("test"), "test")
        error_handler.handle_cache_error(Exception("test"), "test")
        
        metrics = error_handler.get_error_metrics()
        assert len(metrics) == 2
        assert ErrorType.DATABASE_CONNECTION in metrics
        assert ErrorType.CACHE_CONNECTION in metrics
    
    def test_reset_error_metrics_specific(self, error_handler):
        """Test resetting specific error metrics."""
        # Generate errors
        error_handler.handle_database_error(Exception("test"), "test")
        error_handler.handle_cache_error(Exception("test"), "test")
        
        # Reset specific error type
        error_handler.reset_error_metrics(ErrorType.DATABASE_CONNECTION)
        
        metrics = error_handler.get_error_metrics()
        assert ErrorType.DATABASE_CONNECTION not in metrics
        assert ErrorType.CACHE_CONNECTION in metrics
    
    def test_reset_error_metrics_all(self, error_handler):
        """Test resetting all error metrics."""
        # Generate errors
        error_handler.handle_database_error(Exception("test"), "test")
        error_handler.handle_cache_error(Exception("test"), "test")
        
        # Reset all metrics
        error_handler.reset_error_metrics()
        
        metrics = error_handler.get_error_metrics()
        assert len(metrics) == 0
    
    def test_is_system_healthy_true(self, error_handler):
        """Test system health check when system is healthy."""
        assert error_handler.is_system_healthy() is True
    
    def test_is_system_healthy_false(self, error_handler):
        """Test system health check when system is unhealthy."""
        # Generate many recent errors
        for _ in range(15):
            error_handler.handle_database_error(Exception("test"), "test")
        
        assert error_handler.is_system_healthy() is False
    
    def test_get_health_report(self, error_handler):
        """Test generating health report."""
        # Generate some errors
        error_handler.handle_database_error(Exception("test"), "test")
        
        report = error_handler.get_health_report()
        
        assert "is_healthy" in report
        assert "error_metrics" in report
        assert "circuit_breakers" in report
        assert "timestamp" in report
        
        assert len(report["error_metrics"]) == 1
        assert len(report["circuit_breakers"]) == 3


class TestErrorHandlingDecorator:
    """Test cases for the error handling decorator."""
    
    @pytest.fixture
    def error_handler(self):
        """Create a MemoryErrorHandler instance for testing."""
        logger = Mock(spec=logging.Logger)
        return MemoryErrorHandler(logger=logger)
    
    def test_decorator_database_error(self, error_handler):
        """Test decorator handling database errors."""
        @handle_memory_errors(error_handler, "test_operation")
        def database_operation():
            raise Exception("database connection failed")
        
        result = database_operation()
        assert result is None  # Should return None for USE_CACHE strategy fallback
        assert ErrorType.DATABASE_CONNECTION in error_handler.error_metrics
    
    def test_decorator_cache_error(self, error_handler):
        """Test decorator handling cache errors."""
        @handle_memory_errors(error_handler, "test_operation")
        def cache_operation():
            raise Exception("redis connection failed")
        
        result = cache_operation()
        assert result is None  # Should return None for USE_DATABASE strategy fallback
    
    def test_decorator_context_error(self, error_handler):
        """Test decorator handling context errors."""
        @handle_memory_errors(error_handler, "test_operation")
        def context_operation():
            raise Exception("context retrieval failed")
        
        result = context_operation()
        assert result is None  # Should return None for RETURN_EMPTY strategy
    
    def test_decorator_generic_error(self, error_handler):
        """Test decorator handling generic errors."""
        @handle_memory_errors(error_handler, "test_operation")
        def generic_operation():
            raise ValueError("generic error")
        
        result = generic_operation()
        assert result is None  # Should return None for FAIL_GRACEFULLY strategy
    
    def test_decorator_success(self, error_handler):
        """Test decorator with successful operation."""
        @handle_memory_errors(error_handler, "test_operation")
        def successful_operation():
            return "success"
        
        result = successful_operation()
        assert result == "success"


class TestErrorMetrics:
    """Test cases for error metrics tracking."""
    
    def test_error_metrics_creation(self):
        """Test creation of ErrorMetrics dataclass."""
        metrics = ErrorMetrics(
            error_type=ErrorType.DATABASE_CONNECTION,
            error_count=5,
            last_error_time=datetime.now(),
            total_recovery_time=10.5,
            success_rate=0.8
        )
        
        assert metrics.error_type == ErrorType.DATABASE_CONNECTION
        assert metrics.error_count == 5
        assert metrics.total_recovery_time == 10.5
        assert metrics.success_rate == 0.8
    
    def test_error_metrics_with_fallback(self):
        """Test ErrorMetrics with fallback strategy."""
        metrics = ErrorMetrics(
            error_type=ErrorType.CACHE_CONNECTION,
            error_count=3,
            last_error_time=datetime.now(),
            total_recovery_time=5.0,
            success_rate=0.9,
            fallback_used=FallbackStrategy.USE_DATABASE
        )
        
        assert metrics.fallback_used == FallbackStrategy.USE_DATABASE


class TestCircuitBreakerState:
    """Test cases for CircuitBreakerState dataclass."""
    
    def test_circuit_breaker_state_defaults(self):
        """Test CircuitBreakerState default values."""
        state = CircuitBreakerState()
        
        assert state.is_open is False
        assert state.failure_count == 0
        assert state.last_failure_time is None
        assert state.next_attempt_time is None
        assert state.success_count == 0
    
    def test_circuit_breaker_state_custom_values(self):
        """Test CircuitBreakerState with custom values."""
        now = datetime.now()
        state = CircuitBreakerState(
            is_open=True,
            failure_count=5,
            last_failure_time=now,
            next_attempt_time=now + timedelta(minutes=1),
            success_count=10
        )
        
        assert state.is_open is True
        assert state.failure_count == 5
        assert state.last_failure_time == now
        assert state.success_count == 10


if __name__ == "__main__":
    pytest.main([__file__])