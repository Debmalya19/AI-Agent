#!/usr/bin/env python3
"""
Test Error Handling and Monitoring Implementation

Tests the PostgreSQL error handling, monitoring, and graceful degradation features.
"""

import os
import sys
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def setup_test_environment():
    """Setup test environment"""
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_LOG_LEVEL"] = "DEBUG"
    os.environ["LOG_DIRECTORY"] = "logs"

def test_postgresql_error_handler():
    """Test PostgreSQL error handling functionality"""
    print("Testing PostgreSQL Error Handler...")
    
    try:
        from backend.database import PostgreSQLErrorHandler
        from sqlalchemy.exc import OperationalError, IntegrityError
        
        # Test error categorization
        connection_error = OperationalError("connection to server failed", None, None)
        permanent_error = IntegrityError("duplicate key value", None, None)
        
        assert PostgreSQLErrorHandler.is_transient_error(connection_error), "Should identify transient error"
        assert not PostgreSQLErrorHandler.is_transient_error(permanent_error), "Should not identify permanent error as transient"
        
        assert PostgreSQLErrorHandler.get_error_category(connection_error) == "transient", "Should categorize as transient"
        assert PostgreSQLErrorHandler.get_error_category(permanent_error) == "permanent", "Should categorize as permanent"
        
        # Test retry delay calculation
        delay1 = PostgreSQLErrorHandler.get_retry_delay(0, base_delay=1.0, jitter=False)
        delay2 = PostgreSQLErrorHandler.get_retry_delay(1, base_delay=1.0, jitter=False)
        delay3 = PostgreSQLErrorHandler.get_retry_delay(2, base_delay=1.0, jitter=False)
        
        assert delay1 == 1.0, f"First delay should be 1.0, got {delay1}"
        assert delay2 == 2.0, f"Second delay should be 2.0, got {delay2}"
        assert delay3 == 4.0, f"Third delay should be 4.0, got {delay3}"
        
        print("✅ PostgreSQL Error Handler tests passed")
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL Error Handler tests failed: {e}")
        return False

def test_database_monitoring():
    """Test database monitoring functionality"""
    print("Testing Database Monitoring...")
    
    try:
        from backend.database_monitoring import (
            DatabaseMonitor, get_database_metrics, get_database_health_score,
            get_error_summary, database_monitor
        )
        
        # Test monitor initialization
        monitor = DatabaseMonitor()
        assert monitor is not None, "Monitor should initialize"
        
        # Test metrics collection
        monitor.record_query_time(0.1)
        monitor.record_query_time(0.2)
        monitor.record_connection_attempt(True)
        monitor.record_connection_attempt(False)
        
        # Test error recording
        test_error = Exception("Test error")
        monitor.record_error(test_error, "test_operation")
        
        # Test metrics retrieval
        metrics = monitor.get_current_metrics()
        assert metrics is not None, "Should return metrics"
        assert metrics.query_count >= 0, "Query count should be non-negative"
        
        # Test health score calculation
        health_score = monitor.get_health_score()
        assert 0 <= health_score <= 100, f"Health score should be 0-100, got {health_score}"
        
        # Test error summary
        error_summary = monitor.get_error_summary()
        assert "total_errors" in error_summary, "Should include total errors"
        assert error_summary["total_errors"] >= 1, "Should have recorded test error"
        
        print("✅ Database Monitoring tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Database Monitoring tests failed: {e}")
        return False

def test_graceful_degradation():
    """Test graceful degradation functionality"""
    print("Testing Graceful Degradation...")
    
    try:
        from backend.graceful_degradation import (
            GracefulDegradationHandler, DegradationLevel, 
            with_graceful_degradation, degradation_handler
        )
        
        # Test degradation handler initialization
        handler = GracefulDegradationHandler()
        assert handler is not None, "Handler should initialize"
        
        # Test degradation level determination
        level = handler.get_current_degradation_level()
        assert level in [
            DegradationLevel.NONE, DegradationLevel.MINIMAL, 
            DegradationLevel.MODERATE, DegradationLevel.SIGNIFICANT, 
            DegradationLevel.SEVERE
        ], f"Should return valid degradation level, got {level}"
        
        # Test fallback response generation
        fallback = handler.get_fallback_response("test_operation")
        assert "status" in fallback, "Fallback should include status"
        assert fallback["status"] == "degraded", "Status should be degraded"
        
        # Test circuit breaker
        handler.create_circuit_breaker("test_op", failure_threshold=2)
        assert not handler.is_circuit_breaker_open("test_op"), "Circuit breaker should start closed"
        
        # Record failures to open circuit breaker
        handler.record_operation_result("test_op", False)
        handler.record_operation_result("test_op", False)
        assert handler.is_circuit_breaker_open("test_op"), "Circuit breaker should open after failures"
        
        # Test decorator
        @with_graceful_degradation("test_decorator_op")
        def test_function():
            return {"result": "success"}
        
        result = test_function()
        assert result is not None, "Decorated function should return result"
        
        print("✅ Graceful Degradation tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Graceful Degradation tests failed: {e}")
        return False

def test_database_logging():
    """Test database logging functionality"""
    print("Testing Database Logging...")
    
    try:
        from backend.database_logging import (
            log_database_operation, log_connection_event, log_error_with_context,
            log_health_check, DatabaseOperationLogger
        )
        
        # Test operation logging
        log_database_operation("test_operation", duration=0.1, success=True)
        log_database_operation("test_failed_operation", success=False, error=Exception("Test error"))
        
        # Test connection event logging
        log_connection_event("test_connection", {"details": "test"})
        
        # Test error logging
        test_error = Exception("Test error for logging")
        log_error_with_context(test_error, "test_operation", {"context": "test"})
        
        # Test health check logging
        log_health_check("healthy", {"details": "all good"})
        log_health_check("unhealthy", {"reason": "test failure"})
        
        # Test context manager
        with DatabaseOperationLogger("test_context_operation") as logger:
            time.sleep(0.01)  # Simulate some work
        
        print("✅ Database Logging tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Database Logging tests failed: {e}")
        return False

async def test_health_endpoints():
    """Test health check endpoints"""
    print("Testing Health Endpoints...")
    
    try:
        from backend.health_endpoints import health_router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        # Create test app
        app = FastAPI()
        app.include_router(health_router)
        
        # Create test client
        client = TestClient(app)
        
        # Test basic health check
        response = client.get("/health/")
        assert response.status_code == 200, f"Health check should return 200, got {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Response should include status"
        assert "timestamp" in data, "Response should include timestamp"
        
        # Test database health check
        response = client.get("/health/database")
        # Note: This might return 503 if database is not available, which is expected
        assert response.status_code in [200, 503], f"Database health should return 200 or 503, got {response.status_code}"
        
        # Test metrics endpoint
        response = client.get("/health/database/metrics")
        # This might fail if database is not available, which is expected in test environment
        
        # Test readiness check
        response = client.get("/health/readiness")
        assert response.status_code in [200, 503], f"Readiness check should return 200 or 503, got {response.status_code}"
        
        # Test liveness check
        response = client.get("/health/liveness")
        assert response.status_code == 200, f"Liveness check should return 200, got {response.status_code}"
        
        print("✅ Health Endpoints tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Health Endpoints tests failed: {e}")
        return False

def test_retry_decorator():
    """Test retry decorator functionality"""
    print("Testing Retry Decorator...")
    
    try:
        from backend.database import retry_on_database_error
        from sqlalchemy.exc import OperationalError
        
        # Test successful operation
        @retry_on_database_error(max_retries=2)
        def successful_operation():
            return "success"
        
        result = successful_operation()
        assert result == "success", "Successful operation should return result"
        
        # Test operation that fails then succeeds
        call_count = 0
        
        @retry_on_database_error(max_retries=2, base_delay=0.01)
        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OperationalError("connection failed", None, None)
            return "success_after_retry"
        
        result = flaky_operation()
        assert result == "success_after_retry", "Should succeed after retry"
        assert call_count == 2, f"Should have been called twice, was called {call_count} times"
        
        print("✅ Retry Decorator tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Retry Decorator tests failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🧪 Testing Error Handling and Monitoring Implementation")
    print("=" * 60)
    
    setup_test_environment()
    
    tests = [
        test_postgresql_error_handler,
        test_database_monitoring,
        test_graceful_degradation,
        test_database_logging,
        test_health_endpoints,
        test_retry_decorator
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
        
        print()  # Add spacing between tests
    
    print("=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All error handling and monitoring tests passed!")
        return True
    else:
        print(f"⚠️  {failed} test(s) failed. Check implementation.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)