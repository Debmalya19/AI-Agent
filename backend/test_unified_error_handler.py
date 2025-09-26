"""
Tests for Unified Error Handling System

This module contains comprehensive tests for the unified error handler,
middleware, and integration utilities.

Requirements: 4.4, 1.4, 3.4
"""

import pytest
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, FastAPI, Request
from fastapi.testclient import TestClient
import jwt
from sqlalchemy.exc import OperationalError, IntegrityError

from .unified_error_handler import (
    UnifiedErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity,
    RecoveryStrategy, CircuitBreaker, setup_error_handler
)
from .error_middleware import ErrorHandlingMiddleware, setup_error_middleware
from .error_integration_utils import (
    AdminDashboardErrorIntegration, DataSyncErrorIntegration,
    DatabaseErrorIntegration, AuthenticationErrorIntegration
)


class TestUnifiedErrorHandler:
    """Test cases for UnifiedErrorHandler"""
    
    @pytest.fixture
    def error_handler(self):
        """Create error handler instance for testing"""
        return UnifiedErrorHandler()
    
    @pytest.fixture
    def error_context(self):
        """Create error context for testing"""
        return ErrorContext(
            user_id="test_user",
            session_id="test_session",
            request_id="test_request",
            endpoint="/test/endpoint",
            method="GET",
            component="test_component"
        )
    
    def test_error_categorization(self, error_handler, error_context):
        """Test error categorization logic"""
        # Test authentication errors
        auth_error = jwt.InvalidTokenError("Invalid token")
        category = error_handler.categorize_error(auth_error, error_context)
        assert category == ErrorCategory.AUTHENTICATION
        
        # Test database errors
        db_error = OperationalError("Connection failed", None, None)
        category = error_handler.categorize_error(db_error, error_context)
        assert category == ErrorCategory.DATABASE
        
        # Test validation errors
        validation_error = ValueError("Invalid input")
        category = error_handler.categorize_error(validation_error, error_context)
        assert category == ErrorCategory.VALIDATION
        
        # Test sync errors
        sync_context = ErrorContext(component="data_sync")
        sync_error = Exception("Sync failed")
        category = error_handler.categorize_error(sync_error, sync_context)
        assert category == ErrorCategory.SYNC
    
    def test_severity_determination(self, error_handler, error_context):
        """Test error severity determination"""
        # Test critical database connection error
        db_error = OperationalError("Connection failed", None, None)
        severity = error_handler.determine_severity(db_error, ErrorCategory.DATABASE, error_context)
        assert severity == ErrorSeverity.CRITICAL
        
        # Test high severity auth error
        auth_error = jwt.InvalidTokenError("Invalid token")
        severity = error_handler.determine_severity(auth_error, ErrorCategory.AUTHENTICATION, error_context)
        assert severity == ErrorSeverity.HIGH
        
        # Test medium severity integration error
        integration_error = Exception("Integration failed")
        severity = error_handler.determine_severity(integration_error, ErrorCategory.INTEGRATION, error_context)
        assert severity == ErrorSeverity.MEDIUM
    
    def test_recovery_strategy_determination(self, error_handler, error_context):
        """Test recovery strategy determination"""
        # Test database connection error strategy
        db_error = OperationalError("Connection timeout", None, None)
        strategy = error_handler.determine_recovery_strategy(
            db_error, ErrorCategory.DATABASE, ErrorSeverity.HIGH, error_context
        )
        assert strategy == RecoveryStrategy.RETRY_WITH_BACKOFF
        
        # Test authentication error strategy
        auth_error = jwt.InvalidTokenError("Invalid token")
        strategy = error_handler.determine_recovery_strategy(
            auth_error, ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, error_context
        )
        assert strategy == RecoveryStrategy.FAIL_FAST
        
        # Test integration error strategy
        integration_error = Exception("Integration failed")
        strategy = error_handler.determine_recovery_strategy(
            integration_error, ErrorCategory.INTEGRATION, ErrorSeverity.MEDIUM, error_context
        )
        assert strategy == RecoveryStrategy.GRACEFUL_DEGRADATION
    
    @pytest.mark.asyncio
    async def test_handle_error(self, error_handler, error_context):
        """Test main error handling method"""
        test_error = ValueError("Test validation error")
        
        result = await error_handler.handle_error(test_error, error_context)
        
        assert 'error_id' in result
        assert result['category'] == 'validation'
        assert result['severity'] == 'low'
        assert 'recovery_result' in result
        assert 'timestamp' in result
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff(self, error_handler, error_context):
        """Test retry with backoff mechanism"""
        test_error = Exception("Temporary failure")
        
        # Mock the retry mechanism to simulate success after first retry
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await error_handler._retry_with_backoff(test_error, error_context, max_retries=2)
            
            assert result['success'] == True
            assert result['action'] == 'retry_success'
            assert result['attempts'] == 2
    
    def test_circuit_breaker_functionality(self, error_handler):
        """Test circuit breaker functionality"""
        breaker = error_handler.circuit_breakers['database']
        
        # Initially closed
        assert not breaker.state.is_open
        
        # Simulate failures to open circuit
        for _ in range(breaker.failure_threshold):
            breaker._on_failure()
        
        assert breaker.state.is_open
        assert breaker.state.failure_count == breaker.failure_threshold
        
        # Test success resets circuit
        breaker._on_success()
        assert not breaker.state.is_open
        assert breaker.state.failure_count == 0
    
    def test_error_metrics_recording(self, error_handler, error_context):
        """Test error metrics recording"""
        test_error = ValueError("Test error")
        
        # Record error
        error_handler._record_error_metrics(ErrorCategory.VALIDATION, test_error, error_context)
        
        # Check metrics
        assert ErrorCategory.VALIDATION in error_handler.error_metrics
        metrics = error_handler.error_metrics[ErrorCategory.VALIDATION]
        assert metrics.error_count == 1
        assert metrics.last_occurrence is not None
    
    def test_health_report_generation(self, error_handler):
        """Test health report generation"""
        health_report = error_handler.get_health_report()
        
        assert 'is_healthy' in health_report
        assert 'error_metrics' in health_report
        assert 'circuit_breakers' in health_report
        assert 'timestamp' in health_report
        assert 'health_score' in health_report
    
    @pytest.mark.asyncio
    async def test_error_context_manager(self, error_handler, error_context):
        """Test async error context manager"""
        with pytest.raises(ValueError):
            async with error_handler.error_context(error_context):
                raise ValueError("Test error in context")
    
    def test_sync_error_context_manager(self, error_handler, error_context):
        """Test sync error context manager"""
        with pytest.raises(ValueError):
            with error_handler.sync_error_context(error_context):
                raise ValueError("Test error in sync context")


class TestCircuitBreaker:
    """Test cases for CircuitBreaker"""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker for testing"""
        return CircuitBreaker(
            name="test_breaker",
            failure_threshold=3,
            recovery_timeout=60,
            expected_exceptions=(Exception,)
        )
    
    def test_circuit_breaker_decorator_sync(self, circuit_breaker):
        """Test circuit breaker decorator with sync function"""
        call_count = 0
        
        @circuit_breaker
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Test failure")
            return "success"
        
        # First 3 calls should fail and open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                test_function()
        
        assert circuit_breaker.state.is_open
        
        # Next call should be blocked by circuit breaker
        with pytest.raises(Exception, match="Circuit breaker"):
            test_function()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_decorator_async(self, circuit_breaker):
        """Test circuit breaker decorator with async function"""
        call_count = 0
        
        @circuit_breaker
        async def test_async_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Test failure")
            return "success"
        
        # First 3 calls should fail and open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await test_async_function()
        
        assert circuit_breaker.state.is_open


class TestErrorMiddleware:
    """Test cases for ErrorHandlingMiddleware"""
    
    @pytest.fixture
    def app_with_middleware(self):
        """Create FastAPI app with error middleware"""
        app = FastAPI()
        error_handler = UnifiedErrorHandler()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        @app.get("/test-error")
        async def test_error_endpoint():
            raise ValueError("Test error")
        
        @app.get("/test-http-error")
        async def test_http_error_endpoint():
            raise HTTPException(status_code=400, detail="Bad request")
        
        setup_error_middleware(app, error_handler)
        return app
    
    def test_successful_request(self, app_with_middleware):
        """Test successful request handling"""
        client = TestClient(app_with_middleware)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
    
    def test_error_request_handling(self, app_with_middleware):
        """Test error request handling"""
        client = TestClient(app_with_middleware)
        response = client.get("/test-error")
        
        assert response.status_code == 400  # Validation error
        data = response.json()
        assert data['error'] == True
        assert 'message' in data
        assert 'request_id' in data
        assert 'timestamp' in data
    
    def test_http_exception_handling(self, app_with_middleware):
        """Test HTTP exception handling"""
        client = TestClient(app_with_middleware)
        response = client.get("/test-http-error")
        
        assert response.status_code == 400
        data = response.json()
        assert data['error'] == True
        assert 'request_id' in data


class TestErrorIntegrations:
    """Test cases for error integration utilities"""
    
    def test_admin_dashboard_error_integration(self):
        """Test admin dashboard error integration"""
        integration = AdminDashboardErrorIntegration()
        
        # Test auth error handling
        auth_error = jwt.InvalidTokenError("Token expired")
        result = integration.handle_admin_auth_error(auth_error, "test_user")
        
        assert result['auth_error'] == True
        assert result['action'] == 'token_refresh_required'
        assert result['redirect_to_login'] == True
    
    @pytest.mark.asyncio
    async def test_data_sync_error_integration(self):
        """Test data sync error integration"""
        integration = DataSyncErrorIntegration()
        
        # Test sync error handling
        sync_error = Exception("Sync failed")
        result = await integration.handle_sync_error(
            sync_error, "test_sync_operation", entity_id=123, entity_type="ticket"
        )
        
        assert result['sync_error'] == True
        assert 'error_id' in result
    
    @pytest.mark.asyncio
    async def test_database_error_integration(self):
        """Test database error integration"""
        integration = DatabaseErrorIntegration()
        
        # Test database error handling
        db_error = OperationalError("Connection failed", None, None)
        result = await integration.handle_database_error(
            db_error, "test_operation", table_name="test_table"
        )
        
        assert result['database_error'] == True
        assert result['operation'] == "test_operation"
        assert result['table_name'] == "test_table"
    
    @pytest.mark.asyncio
    async def test_authentication_error_integration(self):
        """Test authentication error integration"""
        integration = AuthenticationErrorIntegration()
        
        # Test auth error handling
        auth_error = Exception("Invalid credentials")
        result = await integration.handle_auth_error(
            auth_error, "test_user", "login"
        )
        
        assert result['auth_error'] == True
        assert result['auth_type'] == "login"
        assert result['user_identifier'] == "test_user"
        assert 'failed_attempts' in result


class TestErrorRecoveryMechanisms:
    """Test cases for error recovery mechanisms"""
    
    @pytest.fixture
    def error_handler(self):
        return UnifiedErrorHandler()
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_database(self, error_handler):
        """Test graceful degradation for database errors"""
        error_context = ErrorContext(component="database")
        db_error = OperationalError("Connection failed", None, None)
        
        result = await error_handler._graceful_degradation(
            db_error, ErrorCategory.DATABASE, error_context
        )
        
        assert result['success'] == True
        assert result['action'] == 'fallback_cache'
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_integration(self, error_handler):
        """Test graceful degradation for integration errors"""
        error_context = ErrorContext(component="admin_integration")
        integration_error = Exception("Admin API failed")
        
        result = await error_handler._graceful_degradation(
            integration_error, ErrorCategory.INTEGRATION, error_context
        )
        
        assert result['success'] == True
        assert result['action'] == 'limited_functionality'
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_sync(self, error_handler):
        """Test graceful degradation for sync errors"""
        error_context = ErrorContext(component="data_sync")
        sync_error = Exception("Sync failed")
        
        result = await error_handler._graceful_degradation(
            sync_error, ErrorCategory.SYNC, error_context
        )
        
        assert result['success'] == True
        assert result['action'] == 'async_retry'


class TestErrorHandlerDecorator:
    """Test cases for error handler decorator"""
    
    @pytest.fixture
    def error_handler(self):
        return UnifiedErrorHandler()
    
    @pytest.mark.asyncio
    async def test_async_decorator(self, error_handler):
        """Test error handler decorator with async function"""
        
        @error_handler.error_handler_decorator(component="test", operation="async_test")
        async def test_async_function():
            raise ValueError("Test async error")
        
        # Should not raise exception due to graceful degradation
        result = await test_async_function()
        assert result is None  # Graceful degradation returns None
    
    def test_sync_decorator(self, error_handler):
        """Test error handler decorator with sync function"""
        
        @error_handler.error_handler_decorator(component="test", operation="sync_test")
        def test_sync_function():
            raise ValueError("Test sync error")
        
        # Should not raise exception due to graceful degradation
        result = test_sync_function()
        assert result is None  # Graceful degradation returns None


class TestErrorMetricsAndMonitoring:
    """Test cases for error metrics and monitoring"""
    
    @pytest.fixture
    def error_handler(self):
        return UnifiedErrorHandler()
    
    def test_error_metrics_collection(self, error_handler):
        """Test error metrics collection"""
        error_context = ErrorContext(component="test")
        
        # Record multiple errors
        for i in range(5):
            error_handler._record_error_metrics(
                ErrorCategory.VALIDATION, 
                ValueError(f"Error {i}"), 
                error_context
            )
        
        metrics = error_handler.get_error_metrics()
        assert 'validation' in metrics
        assert metrics['validation']['error_count'] == 5
    
    def test_recovery_metrics_recording(self, error_handler):
        """Test recovery metrics recording"""
        # Record successful recovery
        error_handler._record_recovery_metrics(ErrorCategory.DATABASE, True, 1.5)
        
        # Record failed recovery
        error_handler._record_recovery_metrics(ErrorCategory.DATABASE, False, 2.0)
        
        metrics = error_handler.error_metrics[ErrorCategory.DATABASE]
        assert metrics.recovery_attempts == 2
        assert metrics.recovery_successes == 1
        assert metrics.success_rate == 0.5
        assert metrics.total_recovery_time == 3.5
    
    def test_metrics_reset(self, error_handler):
        """Test metrics reset functionality"""
        error_context = ErrorContext(component="test")
        
        # Record some errors
        error_handler._record_error_metrics(
            ErrorCategory.VALIDATION, ValueError("Test"), error_context
        )
        error_handler._record_error_metrics(
            ErrorCategory.DATABASE, Exception("Test"), error_context
        )
        
        # Reset specific category
        error_handler.reset_metrics(ErrorCategory.VALIDATION)
        assert ErrorCategory.VALIDATION not in error_handler.error_metrics
        assert ErrorCategory.DATABASE in error_handler.error_metrics
        
        # Reset all metrics
        error_handler.reset_metrics()
        assert len(error_handler.error_metrics) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])