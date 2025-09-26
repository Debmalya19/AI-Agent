"""
Error Monitoring and Health Check Routes

This module provides FastAPI routes for monitoring the error handling system,
viewing error metrics, and checking system health.

Requirements: 4.4, 1.4, 3.4
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
import logging

from .unified_error_handler import UnifiedErrorHandler, get_error_handler, ErrorCategory
from .error_integration_utils import (
    get_admin_error_integration,
    get_sync_error_integration,
    get_db_error_integration,
    get_auth_error_integration
)

logger = logging.getLogger(__name__)

# Create router for error monitoring endpoints
error_monitoring_router = APIRouter(prefix="/api/error-monitoring", tags=["Error Monitoring"])


@error_monitoring_router.get("/health")
async def get_error_system_health(
    error_handler: UnifiedErrorHandler = Depends(get_error_handler)
) -> Dict[str, Any]:
    """
    Get comprehensive health report for the error handling system
    """
    try:
        health_report = error_handler.get_health_report()
        
        # Add component-specific health information
        db_integration = get_db_error_integration()
        sync_integration = get_sync_error_integration()
        
        health_report['components'] = {
            'database': db_integration.check_database_health(),
            'sync_service': sync_integration.get_sync_error_summary(),
            'error_handler': {
                'total_categories': len(error_handler.error_metrics),
                'circuit_breakers_count': len(error_handler.circuit_breakers),
                'active_circuit_breakers': sum(1 for cb in error_handler.circuit_breakers.values() if cb.state.is_open)
            }
        }
        
        return health_report
        
    except Exception as e:
        logger.error(f"Error getting health report: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health report")


@error_monitoring_router.get("/metrics")
async def get_error_metrics(
    category: Optional[str] = Query(None, description="Filter by error category"),
    error_handler: UnifiedErrorHandler = Depends(get_error_handler)
) -> Dict[str, Any]:
    """
    Get error metrics, optionally filtered by category
    """
    try:
        all_metrics = error_handler.get_error_metrics()
        
        if category:
            # Filter by specific category
            if category in all_metrics:
                return {category: all_metrics[category]}
            else:
                return {}
        
        return all_metrics
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error metrics")


@error_monitoring_router.get("/circuit-breakers")
async def get_circuit_breaker_status(
    error_handler: UnifiedErrorHandler = Depends(get_error_handler)
) -> Dict[str, Any]:
    """
    Get status of all circuit breakers
    """
    try:
        return error_handler.get_circuit_breaker_status()
        
    except Exception as e:
        logger.error(f"Error getting circuit breaker status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get circuit breaker status")


@error_monitoring_router.post("/circuit-breakers/{breaker_name}/reset")
async def reset_circuit_breaker(
    breaker_name: str,
    error_handler: UnifiedErrorHandler = Depends(get_error_handler)
) -> Dict[str, Any]:
    """
    Reset a specific circuit breaker
    """
    try:
        if breaker_name not in error_handler.circuit_breakers:
            raise HTTPException(status_code=404, detail=f"Circuit breaker '{breaker_name}' not found")
        
        error_handler.reset_circuit_breakers(breaker_name)
        
        return {
            'success': True,
            'message': f"Circuit breaker '{breaker_name}' has been reset",
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting circuit breaker {breaker_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset circuit breaker")


@error_monitoring_router.post("/metrics/reset")
async def reset_error_metrics(
    category: Optional[str] = Query(None, description="Category to reset (all if not specified)"),
    error_handler: UnifiedErrorHandler = Depends(get_error_handler)
) -> Dict[str, Any]:
    """
    Reset error metrics for a specific category or all categories
    """
    try:
        if category:
            try:
                error_category = ErrorCategory(category)
                error_handler.reset_metrics(error_category)
                message = f"Metrics for category '{category}' have been reset"
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid category '{category}'")
        else:
            error_handler.reset_metrics()
            message = "All error metrics have been reset"
        
        return {
            'success': True,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset metrics")


@error_monitoring_router.get("/admin/errors")
async def get_admin_error_summary() -> Dict[str, Any]:
    """
    Get summary of admin dashboard errors
    """
    try:
        admin_integration = get_admin_error_integration()
        
        # Get recent admin errors from error handler
        error_handler = get_error_handler()
        admin_metrics = {}
        
        for category, metrics in error_handler.error_metrics.items():
            if category in [ErrorCategory.INTEGRATION, ErrorCategory.AUTHENTICATION, ErrorCategory.AUTHORIZATION]:
                admin_metrics[category.value] = {
                    'error_count': metrics.error_count,
                    'last_occurrence': metrics.last_occurrence.isoformat() if metrics.last_occurrence else None,
                    'success_rate': metrics.success_rate
                }
        
        return {
            'admin_metrics': admin_metrics,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting admin error summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin error summary")


@error_monitoring_router.get("/sync/errors")
async def get_sync_error_summary() -> Dict[str, Any]:
    """
    Get summary of data synchronization errors
    """
    try:
        sync_integration = get_sync_error_integration()
        return sync_integration.get_sync_error_summary()
        
    except Exception as e:
        logger.error(f"Error getting sync error summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sync error summary")


@error_monitoring_router.post("/sync/retry")
async def retry_failed_sync_operations(
    max_retries: int = Query(3, description="Maximum number of retries per operation")
) -> Dict[str, Any]:
    """
    Retry failed synchronization operations
    """
    try:
        sync_integration = get_sync_error_integration()
        retry_results = await sync_integration.retry_failed_sync_operations(max_retries)
        
        return {
            'retry_results': retry_results,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error retrying sync operations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry sync operations")


@error_monitoring_router.get("/database/health")
async def get_database_health() -> Dict[str, Any]:
    """
    Get database connection health status
    """
    try:
        db_integration = get_db_error_integration()
        return db_integration.check_database_health()
        
    except Exception as e:
        logger.error(f"Error getting database health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get database health")


@error_monitoring_router.get("/auth/failed-attempts")
async def get_auth_failed_attempts() -> Dict[str, Any]:
    """
    Get summary of failed authentication attempts
    """
    try:
        auth_integration = get_auth_error_integration()
        
        # Get summary without exposing sensitive user data
        total_users_with_failures = len(auth_integration.failed_auth_attempts)
        total_failed_attempts = sum(len(attempts) for attempts in auth_integration.failed_auth_attempts.values())
        
        # Get recent failure patterns (last hour)
        current_time = datetime.now(timezone.utc)
        recent_threshold = current_time - timedelta(hours=1)
        
        recent_failures = 0
        for attempts in auth_integration.failed_auth_attempts.values():
            recent_failures += sum(1 for attempt in attempts if attempt > recent_threshold)
        
        return {
            'total_users_with_failures': total_users_with_failures,
            'total_failed_attempts': total_failed_attempts,
            'recent_failures_last_hour': recent_failures,
            'timestamp': current_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting auth failed attempts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get auth failed attempts")


@error_monitoring_router.post("/auth/reset-attempts/{user_identifier}")
async def reset_user_auth_attempts(user_identifier: str) -> Dict[str, Any]:
    """
    Reset failed authentication attempts for a specific user
    """
    try:
        auth_integration = get_auth_error_integration()
        auth_integration.reset_failed_attempts(user_identifier)
        
        return {
            'success': True,
            'message': f"Failed authentication attempts reset for user",
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error resetting auth attempts for user: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset auth attempts")


@error_monitoring_router.get("/dashboard")
async def get_error_dashboard_data(
    hours: int = Query(24, description="Hours of data to include")
) -> Dict[str, Any]:
    """
    Get comprehensive error dashboard data
    """
    try:
        error_handler = get_error_handler()
        
        # Get current time and threshold
        current_time = datetime.now(timezone.utc)
        threshold = current_time - timedelta(hours=hours)
        
        # Collect dashboard data
        dashboard_data = {
            'overview': {
                'total_error_categories': len(error_handler.error_metrics),
                'active_circuit_breakers': sum(1 for cb in error_handler.circuit_breakers.values() if cb.state.is_open),
                'system_health_score': error_handler.get_health_report().get('health_score', 0),
                'timestamp': current_time.isoformat()
            },
            'error_metrics': error_handler.get_error_metrics(),
            'circuit_breakers': error_handler.get_circuit_breaker_status(),
            'component_health': {
                'database': get_db_error_integration().check_database_health(),
                'sync_service': get_sync_error_integration().get_sync_error_summary()
            }
        }
        
        # Add recent error trends
        recent_errors = {}
        for category, metrics in error_handler.error_metrics.items():
            if metrics.last_occurrence and metrics.last_occurrence > threshold:
                recent_errors[category.value] = {
                    'count': metrics.error_count,
                    'last_occurrence': metrics.last_occurrence.isoformat(),
                    'success_rate': metrics.success_rate
                }
        
        dashboard_data['recent_errors'] = recent_errors
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard data")


@error_monitoring_router.get("/logs/recent")
async def get_recent_error_logs(
    limit: int = Query(50, description="Maximum number of log entries to return"),
    category: Optional[str] = Query(None, description="Filter by error category"),
    severity: Optional[str] = Query(None, description="Filter by severity level")
) -> Dict[str, Any]:
    """
    Get recent error log entries (this would typically read from log files)
    """
    try:
        # In a real implementation, this would read from log files
        # For now, we'll return a placeholder response
        return {
            'message': 'Log retrieval not implemented in this demo',
            'note': 'In production, this would read from log files and return recent error entries',
            'parameters': {
                'limit': limit,
                'category': category,
                'severity': severity
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting recent logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recent logs")


# Health check endpoint that can be used by load balancers
@error_monitoring_router.get("/ping")
async def ping_error_system() -> Dict[str, Any]:
    """
    Simple ping endpoint for error monitoring system health
    """
    try:
        error_handler = get_error_handler()
        health_report = error_handler.get_health_report()
        
        return {
            'status': 'healthy' if health_report['is_healthy'] else 'unhealthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'health_score': health_report.get('health_score', 0)
        }
        
    except Exception as e:
        logger.error(f"Error in ping endpoint: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


def setup_error_monitoring_routes(app):
    """Setup error monitoring routes in FastAPI app"""
    app.include_router(error_monitoring_router)
    logger.info("Error monitoring routes setup completed")