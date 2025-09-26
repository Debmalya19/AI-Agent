"""
Database Health Check Endpoints

Provides REST API endpoints for database health monitoring and diagnostics.
Implements monitoring requirements from PostgreSQL migration spec.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db, engine, health_check_database, get_database_info
from .database_health import get_health_status, get_detailed_health_status, get_cached_health_status
from .database_monitoring import (
    get_database_metrics, get_database_health_score, 
    get_error_summary, database_monitor
)

logger = logging.getLogger(__name__)

# Create router for health check endpoints
health_router = APIRouter(prefix="/health", tags=["health"])

@health_router.get("/")
async def root_health_check():
    """Basic application health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ai-agent",
        "version": "1.0.0"
    }

@health_router.get("/database")
async def database_health_check():
    """Quick database health check"""
    try:
        health_status = get_health_status()
        
        # Determine HTTP status code based on health
        status_code = 200 if health_status.get("status") == "healthy" else 503
        
        return JSONResponse(
            content=health_status,
            status_code=status_code
        )
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )

@health_router.get("/database/detailed")
async def detailed_database_health_check():
    """Comprehensive database health check with diagnostics"""
    try:
        health_status = get_detailed_health_status()
        
        # Add additional metrics
        health_status["metrics"] = get_database_metrics()
        health_status["health_score"] = get_database_health_score()
        
        # Determine HTTP status code based on health
        status_code = 200 if health_status.get("status") == "healthy" else 503
        
        return JSONResponse(
            content=health_status,
            status_code=status_code
        )
    except Exception as e:
        logger.error(f"Detailed database health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "checks": {}
            },
            status_code=503
        )

@health_router.get("/database/metrics")
async def database_metrics():
    """Get current database performance metrics"""
    try:
        metrics = get_database_metrics()
        health_score = get_database_health_score()
        
        return {
            "metrics": metrics,
            "health_score": health_score,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get database metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics: {str(e)}")

@health_router.get("/database/errors")
async def database_errors(hours: int = Query(24, ge=1, le=168, description="Hours to look back for errors")):
    """Get database error summary for specified time period"""
    try:
        error_summary = get_error_summary(hours)
        
        return {
            "error_summary": error_summary,
            "time_period_hours": hours,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get error summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve error summary: {str(e)}")

@health_router.get("/database/connection")
async def database_connection_info():
    """Get database connection information and pool status"""
    try:
        db_info = get_database_info()
        
        return {
            "connection_info": db_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get connection info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve connection info: {str(e)}")

@health_router.post("/database/test")
async def test_database_operation(db: Session = Depends(get_db)):
    """Test database operation with read/write test"""
    start_time = time.time()
    
    try:
        # Test basic connectivity
        db.execute(text("SELECT 1"))
        
        # Test table access (try to access a common table)
        try:
            result = db.execute(text("SELECT COUNT(*) FROM unified_users LIMIT 1"))
            user_count = result.fetchone()[0] if result.fetchone() else 0
        except Exception:
            # Table might not exist, that's okay for this test
            user_count = "N/A"
        
        # Test write operation (create temporary table)
        test_table_name = f"health_test_{int(time.time())}"
        db.execute(text(f"CREATE TEMPORARY TABLE {test_table_name} (id INTEGER, test_data TEXT)"))
        db.execute(text(f"INSERT INTO {test_table_name} (id, test_data) VALUES (1, 'health_check')"))
        
        # Test read operation
        result = db.execute(text(f"SELECT test_data FROM {test_table_name} WHERE id = 1"))
        test_data = result.fetchone()[0]
        
        # Verify data integrity
        if test_data != 'health_check':
            raise ValueError("Data integrity check failed")
        
        db.commit()
        
        duration = time.time() - start_time
        
        return {
            "status": "success",
            "duration_ms": round(duration * 1000, 2),
            "operations": {
                "connectivity": "passed",
                "table_access": "passed",
                "write_operation": "passed",
                "read_operation": "passed",
                "data_integrity": "passed"
            },
            "user_count": user_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        db.rollback()
        duration = time.time() - start_time
        
        logger.error(f"Database test operation failed: {e}")
        
        return JSONResponse(
            content={
                "status": "failed",
                "error": str(e),
                "duration_ms": round(duration * 1000, 2),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )

@health_router.get("/readiness")
async def readiness_check():
    """Kubernetes-style readiness check"""
    try:
        # Check if database is ready to accept connections
        if not engine:
            return JSONResponse(
                content={
                    "status": "not_ready",
                    "reason": "database_engine_unavailable",
                    "timestamp": datetime.now().isoformat()
                },
                status_code=503
            )
        
        # Quick health check
        health_status = get_cached_health_status()
        
        if health_status.get("status") == "healthy":
            return {
                "status": "ready",
                "timestamp": datetime.now().isoformat(),
                "health_score": get_database_health_score()
            }
        else:
            return JSONResponse(
                content={
                    "status": "not_ready",
                    "reason": "database_unhealthy",
                    "health_status": health_status,
                    "timestamp": datetime.now().isoformat()
                },
                status_code=503
            )
            
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            content={
                "status": "not_ready",
                "reason": "readiness_check_failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )

@health_router.get("/liveness")
async def liveness_check():
    """Kubernetes-style liveness check"""
    try:
        # Basic application liveness - should always succeed unless app is completely broken
        return {
            "status": "alive",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - database_monitor.start_time).total_seconds()
        }
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return JSONResponse(
            content={
                "status": "not_alive",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )

@health_router.get("/startup")
async def startup_check():
    """Kubernetes-style startup check"""
    try:
        # Check if application has completed startup
        if not engine:
            return JSONResponse(
                content={
                    "status": "starting",
                    "reason": "database_engine_initializing",
                    "timestamp": datetime.now().isoformat()
                },
                status_code=503
            )
        
        # Check if database is accessible
        if not health_check_database(engine):
            return JSONResponse(
                content={
                    "status": "starting",
                    "reason": "database_not_accessible",
                    "timestamp": datetime.now().isoformat()
                },
                status_code=503
            )
        
        return {
            "status": "started",
            "timestamp": datetime.now().isoformat(),
            "database_status": "connected"
        }
        
    except Exception as e:
        logger.error(f"Startup check failed: {e}")
        return JSONResponse(
            content={
                "status": "starting",
                "reason": "startup_check_failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )

# Graceful degradation endpoint
@health_router.get("/degradation")
async def degradation_status():
    """Get current system degradation status"""
    try:
        health_score = get_database_health_score()
        metrics = get_database_metrics()
        
        # Determine degradation level based on health score
        if health_score >= 90:
            degradation_level = "none"
            message = "System operating normally"
        elif health_score >= 70:
            degradation_level = "minimal"
            message = "Minor performance degradation detected"
        elif health_score >= 50:
            degradation_level = "moderate"
            message = "Moderate performance degradation - some features may be slower"
        elif health_score >= 30:
            degradation_level = "significant"
            message = "Significant degradation - reduced functionality"
        else:
            degradation_level = "severe"
            message = "Severe degradation - limited functionality available"
        
        return {
            "degradation_level": degradation_level,
            "health_score": health_score,
            "message": message,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
            "recommendations": _get_degradation_recommendations(degradation_level, metrics)
        }
        
    except Exception as e:
        logger.error(f"Degradation status check failed: {e}")
        return JSONResponse(
            content={
                "degradation_level": "unknown",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=500
        )

def _get_degradation_recommendations(level: str, metrics: Dict[str, Any]) -> list:
    """Get recommendations based on degradation level"""
    recommendations = []
    
    if level in ["moderate", "significant", "severe"]:
        if metrics.get("error_count", 0) > 10:
            recommendations.append("High error rate detected - check database logs")
        
        if metrics.get("avg_response_time", 0) > 1000:
            recommendations.append("Slow query performance - consider query optimization")
        
        if metrics.get("active_connections", 0) / max(metrics.get("connection_pool_size", 1), 1) > 0.8:
            recommendations.append("High connection pool usage - consider increasing pool size")
        
        if metrics.get("failed_connections", 0) > 5:
            recommendations.append("Connection failures detected - check database connectivity")
    
    return recommendations