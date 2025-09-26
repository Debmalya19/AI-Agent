"""
Error Monitoring and Health Check Endpoints

This module provides endpoints for monitoring the error handling system,
security events, and system health.

Requirements: 5.1, 5.2, 5.3, 5.4
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .database import get_db
from .unified_auth import get_current_user_flexible, AuthenticatedUser, require_admin_access
from .comprehensive_error_integration import get_error_manager


logger = logging.getLogger(__name__)

# Create router for error monitoring endpoints
error_monitoring_router = APIRouter(prefix="/api/error-monitoring", tags=["Error Monitoring"])


@error_monitoring_router.get("/health")
async def get_error_system_health(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible)
):
    """Get health status of the error handling system"""
    try:
        # Require admin access for error monitoring
        require_admin_access(current_user)
        
        error_manager = get_error_manager()
        
        # Get comprehensive status
        status = error_manager.get_comprehensive_status()
        
        # Determine overall health
        error_rate = status['error_statistics']['auth_errors'] + status['error_statistics']['migration_errors']
        recovery_rate = status['error_statistics'].get('successful_recoveries', 0) / max(
            status['error_statistics'].get('recovery_attempts', 1), 1
        )
        
        health_status = "healthy"
        if error_rate > 100:  # High error count
            health_status = "degraded"
        if recovery_rate < 0.5:  # Low recovery success rate
            health_status = "unhealthy"
        
        return {
            "status": "success",
            "health_status": health_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_status": status,
            "metrics": {
                "total_errors": error_rate,
                "recovery_success_rate": recovery_rate,
                "locked_accounts": status['auth_handler_status'].get('locked_accounts', 0),
                "active_circuit_breakers": len([
                    cb for cb in status.get('circuit_breakers', {}).values() 
                    if cb.get('is_open', False)
                ])
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system health")


@error_monitoring_router.get("/security-report")
async def get_security_report(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    hours: int = Query(24, description="Hours to look back for security events")
):
    """Get comprehensive security report"""
    try:
        require_admin_access(current_user)
        
        error_manager = get_error_manager()
        
        # Get security report
        report = error_manager.get_security_report()
        
        # Add time range information
        report['report_period'] = {
            'hours': hours,
            'start_time': (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(),
            'end_time': datetime.now(timezone.utc).isoformat()
        }
        
        return {
            "status": "success",
            "security_report": report
        }
        
    except Exception as e:
        logger.error(f"Error generating security report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate security report")


@error_monitoring_router.get("/error-statistics")
async def get_error_statistics(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible)
):
    """Get detailed error statistics"""
    try:
        require_admin_access(current_user)
        
        error_manager = get_error_manager()
        
        # Get error metrics from all handlers
        unified_metrics = error_manager.unified_handler.get_error_metrics()
        auth_summary = error_manager.auth_handler.get_security_summary()
        migration_summary = error_manager.migration_handler.get_error_summary()
        
        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_statistics": {
                "unified_handler": unified_metrics,
                "authentication_handler": auth_summary,
                "migration_handler": migration_summary,
                "overall_stats": error_manager.error_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting error statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error statistics")


@error_monitoring_router.get("/locked-accounts")
async def get_locked_accounts(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible)
):
    """Get list of currently locked accounts"""
    try:
        require_admin_access(current_user)
        
        error_manager = get_error_manager()
        
        # Get locked accounts information
        locked_accounts = []
        for user_id, tracker in error_manager.auth_handler.failure_tracker.items():
            if tracker.is_locked():
                locked_accounts.append({
                    'user_identifier': user_id,
                    'failure_count': tracker.failure_count,
                    'locked_until': tracker.locked_until.isoformat() if tracker.locked_until else None,
                    'first_failure': tracker.first_failure.isoformat() if tracker.first_failure else None,
                    'last_failure': tracker.last_failure.isoformat() if tracker.last_failure else None,
                    'failure_ips': tracker.failure_ips
                })
        
        return {
            "status": "success",
            "locked_accounts": locked_accounts,
            "total_locked": len(locked_accounts),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting locked accounts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get locked accounts")


@error_monitoring_router.post("/unlock-account")
async def unlock_account(
    user_identifier: str,
    current_user: AuthenticatedUser = Depends(get_current_user_flexible)
):
    """Manually unlock a user account"""
    try:
        require_admin_access(current_user)
        
        error_manager = get_error_manager()
        
        # Check if account is actually locked
        if not error_manager.is_account_locked(user_identifier):
            return {
                "status": "info",
                "message": f"Account {user_identifier} is not currently locked"
            }
        
        # Unlock the account
        error_manager.unlock_account(user_identifier)
        
        # Log the admin action
        await error_manager.log_security_event(
            event_type=error_manager.auth_handler.AuthEventType.ACCOUNT_UNLOCKED,
            user_identifier=user_identifier,
            success=True,
            security_level=error_manager.auth_handler.SecurityLevel.MEDIUM,
            additional_data={
                'unlocked_by_admin': current_user.username,
                'admin_user_id': current_user.user_id
            }
        )
        
        logger.info(f"Account {user_identifier} unlocked by admin {current_user.username}")
        
        return {
            "status": "success",
            "message": f"Account {user_identifier} has been unlocked",
            "unlocked_by": current_user.username,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error unlocking account {user_identifier}: {e}")
        raise HTTPException(status_code=500, detail="Failed to unlock account")


@error_monitoring_router.get("/circuit-breakers")
async def get_circuit_breaker_status(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible)
):
    """Get status of all circuit breakers"""
    try:
        require_admin_access(current_user)
        
        error_manager = get_error_manager()
        
        # Get circuit breaker status
        circuit_breakers = error_manager.unified_handler.get_circuit_breaker_status()
        
        return {
            "status": "success",
            "circuit_breakers": circuit_breakers,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting circuit breaker status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get circuit breaker status")


@error_monitoring_router.post("/reset-circuit-breaker")
async def reset_circuit_breaker(
    breaker_name: str,
    current_user: AuthenticatedUser = Depends(get_current_user_flexible)
):
    """Manually reset a circuit breaker"""
    try:
        require_admin_access(current_user)
        
        error_manager = get_error_manager()
        
        # Check if circuit breaker exists
        if breaker_name not in error_manager.unified_handler.circuit_breakers:
            raise HTTPException(status_code=404, detail=f"Circuit breaker '{breaker_name}' not found")
        
        # Reset the circuit breaker
        breaker = error_manager.unified_handler.circuit_breakers[breaker_name]
        breaker.state.is_open = False
        breaker.state.failure_count = 0
        breaker.state.next_attempt_time = None
        breaker.state.half_open_attempts = 0
        
        logger.info(f"Circuit breaker '{breaker_name}' reset by admin {current_user.username}")
        
        return {
            "status": "success",
            "message": f"Circuit breaker '{breaker_name}' has been reset",
            "reset_by": current_user.username,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting circuit breaker {breaker_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset circuit breaker")


@error_monitoring_router.get("/migration-status")
async def get_migration_status(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible)
):
    """Get status of migration error handling"""
    try:
        require_admin_access(current_user)
        
        error_manager = get_error_manager()
        
        # Get migration error summary
        migration_status = error_manager.migration_handler.get_error_summary()
        
        return {
            "status": "success",
            "migration_status": migration_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting migration status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get migration status")


@error_monitoring_router.post("/cleanup-expired-data")
async def cleanup_expired_data(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible)
):
    """Manually trigger cleanup of expired error tracking data"""
    try:
        require_admin_access(current_user)
        
        error_manager = get_error_manager()
        
        # Perform cleanup
        await error_manager.cleanup_expired_data()
        
        logger.info(f"Manual cleanup triggered by admin {current_user.username}")
        
        return {
            "status": "success",
            "message": "Expired data cleanup completed",
            "triggered_by": current_user.username,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error during manual cleanup: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup expired data")


@error_monitoring_router.get("/system-logs")
async def get_system_logs(
    current_user: AuthenticatedUser = Depends(get_current_user_flexible),
    log_type: str = Query("security", description="Type of logs to retrieve (security, migration, unified)"),
    lines: int = Query(100, description="Number of recent log lines to retrieve")
):
    """Get recent system logs"""
    try:
        require_admin_access(current_user)
        
        # Map log types to file paths
        log_files = {
            "security": "logs/security_events.log",
            "migration": "logs/migration_errors.log",
            "unified": "logs/unified_errors.log"
        }
        
        if log_type not in log_files:
            raise HTTPException(status_code=400, detail=f"Invalid log type. Must be one of: {list(log_files.keys())}")
        
        log_file_path = log_files[log_type]
        
        try:
            # Read recent log lines
            with open(log_file_path, 'r') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            return {
                "status": "success",
                "log_type": log_type,
                "lines_requested": lines,
                "lines_returned": len(recent_lines),
                "logs": [line.strip() for line in recent_lines],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except FileNotFoundError:
            return {
                "status": "info",
                "message": f"Log file {log_file_path} not found",
                "logs": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving system logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system logs")


# Health check endpoint that doesn't require authentication
@error_monitoring_router.get("/ping")
async def ping_error_system():
    """Simple ping endpoint to check if error monitoring is responsive"""
    return {
        "status": "success",
        "message": "Error monitoring system is responsive",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }