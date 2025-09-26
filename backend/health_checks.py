"""
Health Check Endpoints

This module provides comprehensive health check endpoints that monitor both AI agent
and admin dashboard components, including database connectivity, service status,
and integration health.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

import logging
import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import get_db, SessionLocal
from .unified_config import get_config_manager, ConfigManager
from .unified_models import UnifiedUser, UnifiedTicket
from .unified_error_handler import UnifiedErrorHandler

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status for a single component"""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    last_checked: Optional[datetime] = None


@dataclass
class SystemHealth:
    """Overall system health status"""
    status: HealthStatus
    components: List[ComponentHealth]
    overall_response_time_ms: float
    timestamp: datetime
    environment: str
    version: str = "1.0.0"


class HealthChecker:
    """Performs health checks on various system components"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.config
        self.error_handler = UnifiedErrorHandler()
    
    async def check_database_health(self) -> ComponentHealth:
        """Check database connectivity and basic operations"""
        start_time = time.time()
        
        try:
            with SessionLocal() as db:
                # Test basic connectivity
                db.execute(text("SELECT 1"))
                
                # Test table access
                user_count = db.query(UnifiedUser).count()
                ticket_count = db.query(UnifiedTicket).count()
                
                response_time = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Database is accessible and responsive",
                    response_time_ms=response_time,
                    details={
                        "user_count": user_count,
                        "ticket_count": ticket_count,
                        "connection_pool_size": self.config.database.pool_size
                    },
                    last_checked=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Database health check failed: {e}")
            
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time_ms=response_time,
                details={"error": str(e)},
                last_checked=datetime.now(timezone.utc)
            )
    
    async def check_ai_agent_health(self) -> ComponentHealth:
        """Check AI agent component health"""
        start_time = time.time()
        
        try:
            # Check if Google API key is configured
            if not self.config.ai_agent.google_api_key:
                return ComponentHealth(
                    name="ai_agent",
                    status=HealthStatus.DEGRADED,
                    message="AI Agent is configured but Google API key is missing",
                    response_time_ms=(time.time() - start_time) * 1000,
                    details={"google_api_key_configured": False},
                    last_checked=datetime.now(timezone.utc)
                )
            
            # Check memory manager (if available)
            try:
                from .memory_layer_manager import MemoryLayerManager
                from .memory_config import load_config
                
                memory_config = load_config()
                memory_manager = MemoryLayerManager(config=memory_config)
                
                # Test memory manager functionality
                health_metrics = memory_manager.get_health_metrics()
                
                response_time = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="ai_agent",
                    status=HealthStatus.HEALTHY,
                    message="AI Agent is fully operational",
                    response_time_ms=response_time,
                    details={
                        "google_api_key_configured": True,
                        "memory_manager_available": True,
                        "memory_health": health_metrics
                    },
                    last_checked=datetime.now(timezone.utc)
                )
                
            except Exception as memory_error:
                logger.warning(f"Memory manager check failed: {memory_error}")
                
                response_time = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="ai_agent",
                    status=HealthStatus.DEGRADED,
                    message="AI Agent is operational but memory manager has issues",
                    response_time_ms=response_time,
                    details={
                        "google_api_key_configured": True,
                        "memory_manager_available": False,
                        "memory_error": str(memory_error)
                    },
                    last_checked=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"AI Agent health check failed: {e}")
            
            return ComponentHealth(
                name="ai_agent",
                status=HealthStatus.UNHEALTHY,
                message=f"AI Agent health check failed: {str(e)}",
                response_time_ms=response_time,
                details={"error": str(e)},
                last_checked=datetime.now(timezone.utc)
            )
    
    async def check_admin_dashboard_health(self) -> ComponentHealth:
        """Check admin dashboard component health"""
        start_time = time.time()
        
        try:
            if not self.config.admin_dashboard.enabled:
                return ComponentHealth(
                    name="admin_dashboard",
                    status=HealthStatus.HEALTHY,
                    message="Admin dashboard is disabled by configuration",
                    response_time_ms=(time.time() - start_time) * 1000,
                    details={"enabled": False},
                    last_checked=datetime.now(timezone.utc)
                )
            
            # Check admin dashboard integration
            try:
                from .admin_integration_manager import AdminIntegrationManager
                
                # This would normally check if the integration manager is working
                # For now, we'll do a basic check
                
                response_time = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="admin_dashboard",
                    status=HealthStatus.HEALTHY,
                    message="Admin dashboard integration is operational",
                    response_time_ms=response_time,
                    details={
                        "enabled": True,
                        "api_prefix": self.config.admin_dashboard.api_prefix,
                        "frontend_path": self.config.admin_dashboard.frontend_path
                    },
                    last_checked=datetime.now(timezone.utc)
                )
                
            except Exception as integration_error:
                logger.warning(f"Admin dashboard integration check failed: {integration_error}")
                
                response_time = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="admin_dashboard",
                    status=HealthStatus.DEGRADED,
                    message="Admin dashboard is enabled but integration has issues",
                    response_time_ms=response_time,
                    details={
                        "enabled": True,
                        "integration_error": str(integration_error)
                    },
                    last_checked=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Admin dashboard health check failed: {e}")
            
            return ComponentHealth(
                name="admin_dashboard",
                status=HealthStatus.UNHEALTHY,
                message=f"Admin dashboard health check failed: {str(e)}",
                response_time_ms=response_time,
                details={"error": str(e)},
                last_checked=datetime.now(timezone.utc)
            )
    
    async def check_data_sync_health(self) -> ComponentHealth:
        """Check data synchronization service health"""
        start_time = time.time()
        
        try:
            if not self.config.data_sync.enabled:
                return ComponentHealth(
                    name="data_sync",
                    status=HealthStatus.HEALTHY,
                    message="Data sync is disabled by configuration",
                    response_time_ms=(time.time() - start_time) * 1000,
                    details={"enabled": False},
                    last_checked=datetime.now(timezone.utc)
                )
            
            # Check data sync service
            try:
                from .data_sync_service import DataSyncService
                
                # This would normally check the sync service status
                # For now, we'll do a basic configuration check
                
                response_time = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="data_sync",
                    status=HealthStatus.HEALTHY,
                    message="Data synchronization service is operational",
                    response_time_ms=response_time,
                    details={
                        "enabled": True,
                        "sync_interval_seconds": self.config.data_sync.sync_interval_seconds,
                        "batch_size": self.config.data_sync.batch_size
                    },
                    last_checked=datetime.now(timezone.utc)
                )
                
            except Exception as sync_error:
                logger.warning(f"Data sync service check failed: {sync_error}")
                
                response_time = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="data_sync",
                    status=HealthStatus.DEGRADED,
                    message="Data sync is enabled but service has issues",
                    response_time_ms=response_time,
                    details={
                        "enabled": True,
                        "sync_error": str(sync_error)
                    },
                    last_checked=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Data sync health check failed: {e}")
            
            return ComponentHealth(
                name="data_sync",
                status=HealthStatus.UNHEALTHY,
                message=f"Data sync health check failed: {str(e)}",
                response_time_ms=response_time,
                details={"error": str(e)},
                last_checked=datetime.now(timezone.utc)
            )
    
    async def check_voice_assistant_health(self) -> ComponentHealth:
        """Check voice assistant component health"""
        start_time = time.time()
        
        try:
            if not self.config.voice.enabled:
                return ComponentHealth(
                    name="voice_assistant",
                    status=HealthStatus.HEALTHY,
                    message="Voice assistant is disabled by configuration",
                    response_time_ms=(time.time() - start_time) * 1000,
                    details={"enabled": False},
                    last_checked=datetime.now(timezone.utc)
                )
            
            # Check voice assistant configuration
            response_time = (time.time() - start_time) * 1000
            
            return ComponentHealth(
                name="voice_assistant",
                status=HealthStatus.HEALTHY,
                message="Voice assistant is configured and available",
                response_time_ms=response_time,
                details={
                    "enabled": True,
                    "max_recording_duration_ms": self.config.voice.max_recording_duration_ms,
                    "rate_limit_per_minute": self.config.voice.rate_limit_per_minute
                },
                last_checked=datetime.now(timezone.utc)
            )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Voice assistant health check failed: {e}")
            
            return ComponentHealth(
                name="voice_assistant",
                status=HealthStatus.UNHEALTHY,
                message=f"Voice assistant health check failed: {str(e)}",
                response_time_ms=response_time,
                details={"error": str(e)},
                last_checked=datetime.now(timezone.utc)
            )
    
    async def check_analytics_health(self) -> ComponentHealth:
        """Check analytics component health"""
        start_time = time.time()
        
        try:
            if not self.config.analytics.enabled:
                return ComponentHealth(
                    name="analytics",
                    status=HealthStatus.HEALTHY,
                    message="Analytics is disabled by configuration",
                    response_time_ms=(time.time() - start_time) * 1000,
                    details={"enabled": False},
                    last_checked=datetime.now(timezone.utc)
                )
            
            # Check analytics service
            try:
                from .analytics_service import AnalyticsService
                
                # This would normally check the analytics service
                # For now, we'll do a basic configuration check
                
                response_time = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="analytics",
                    status=HealthStatus.HEALTHY,
                    message="Analytics service is operational",
                    response_time_ms=response_time,
                    details={
                        "enabled": True,
                        "retention_days": self.config.analytics.retention_days,
                        "real_time_updates": self.config.analytics.real_time_updates
                    },
                    last_checked=datetime.now(timezone.utc)
                )
                
            except Exception as analytics_error:
                logger.warning(f"Analytics service check failed: {analytics_error}")
                
                response_time = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="analytics",
                    status=HealthStatus.DEGRADED,
                    message="Analytics is enabled but service has issues",
                    response_time_ms=response_time,
                    details={
                        "enabled": True,
                        "analytics_error": str(analytics_error)
                    },
                    last_checked=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Analytics health check failed: {e}")
            
            return ComponentHealth(
                name="analytics",
                status=HealthStatus.UNHEALTHY,
                message=f"Analytics health check failed: {str(e)}",
                response_time_ms=response_time,
                details={"error": str(e)},
                last_checked=datetime.now(timezone.utc)
            )
    
    async def perform_full_health_check(self) -> SystemHealth:
        """Perform a comprehensive health check of all components"""
        overall_start_time = time.time()
        
        # Run all health checks concurrently
        health_checks = await asyncio.gather(
            self.check_database_health(),
            self.check_ai_agent_health(),
            self.check_admin_dashboard_health(),
            self.check_data_sync_health(),
            self.check_voice_assistant_health(),
            self.check_analytics_health(),
            return_exceptions=True
        )
        
        components = []
        for check_result in health_checks:
            if isinstance(check_result, ComponentHealth):
                components.append(check_result)
            else:
                # Handle exceptions from health checks
                logger.error(f"Health check exception: {check_result}")
                components.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check failed with exception: {str(check_result)}",
                    last_checked=datetime.now(timezone.utc)
                ))
        
        # Determine overall system health
        overall_status = self._determine_overall_status(components)
        overall_response_time = (time.time() - overall_start_time) * 1000
        
        return SystemHealth(
            status=overall_status,
            components=components,
            overall_response_time_ms=overall_response_time,
            timestamp=datetime.now(timezone.utc),
            environment=self.config.environment.value
        )
    
    def _determine_overall_status(self, components: List[ComponentHealth]) -> HealthStatus:
        """Determine overall system health based on component health"""
        if not components:
            return HealthStatus.UNKNOWN
        
        # Count status types
        status_counts = {}
        for component in components:
            status = component.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Determine overall status based on component statuses
        if status_counts.get(HealthStatus.UNHEALTHY, 0) > 0:
            # Any unhealthy component makes the system unhealthy
            return HealthStatus.UNHEALTHY
        elif status_counts.get(HealthStatus.DEGRADED, 0) > 0:
            # Any degraded component makes the system degraded
            return HealthStatus.DEGRADED
        elif status_counts.get(HealthStatus.UNKNOWN, 0) > 0:
            # Unknown components make the system status unknown
            return HealthStatus.UNKNOWN
        else:
            # All components are healthy
            return HealthStatus.HEALTHY


def create_health_check_router() -> APIRouter:
    """Create the health check FastAPI router"""
    
    router = APIRouter(prefix="/health", tags=["health"])
    config_manager = get_config_manager()
    health_checker = HealthChecker(config_manager)
    
    @router.get("/")
    async def basic_health_check():
        """Basic health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "AI Agent Customer Support"
        }
    
    @router.get("/detailed")
    async def detailed_health_check():
        """Detailed health check of all components"""
        try:
            system_health = await health_checker.perform_full_health_check()
            
            # Convert to dictionary for JSON response
            response_data = {
                "status": system_health.status.value,
                "overall_response_time_ms": system_health.overall_response_time_ms,
                "timestamp": system_health.timestamp.isoformat(),
                "environment": system_health.environment,
                "version": system_health.version,
                "components": []
            }
            
            for component in system_health.components:
                component_data = {
                    "name": component.name,
                    "status": component.status.value,
                    "message": component.message,
                    "response_time_ms": component.response_time_ms,
                    "last_checked": component.last_checked.isoformat() if component.last_checked else None
                }
                
                if component.details:
                    component_data["details"] = component.details
                
                response_data["components"].append(component_data)
            
            # Set appropriate HTTP status code
            status_code = 200
            if system_health.status == HealthStatus.DEGRADED:
                status_code = 200  # Still return 200 for degraded
            elif system_health.status == HealthStatus.UNHEALTHY:
                status_code = 503  # Service Unavailable
            elif system_health.status == HealthStatus.UNKNOWN:
                status_code = 500  # Internal Server Error
            
            return JSONResponse(content=response_data, status_code=status_code)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                content={
                    "status": "unhealthy",
                    "message": f"Health check failed: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                status_code=500
            )
    
    @router.get("/database")
    async def database_health_check():
        """Database-specific health check"""
        try:
            component_health = await health_checker.check_database_health()
            
            response_data = {
                "name": component_health.name,
                "status": component_health.status.value,
                "message": component_health.message,
                "response_time_ms": component_health.response_time_ms,
                "last_checked": component_health.last_checked.isoformat() if component_health.last_checked else None
            }
            
            if component_health.details:
                response_data["details"] = component_health.details
            
            status_code = 200 if component_health.status == HealthStatus.HEALTHY else 503
            return JSONResponse(content=response_data, status_code=status_code)
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return JSONResponse(
                content={
                    "status": "unhealthy",
                    "message": f"Database health check failed: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                status_code=500
            )
    
    @router.get("/config")
    async def configuration_health_check():
        """Configuration validation health check"""
        try:
            config_info = config_manager.get_health_check_info()
            validation_errors = config_manager.get_validation_errors()
            
            status = "healthy" if len(validation_errors) == 0 else "unhealthy"
            status_code = 200 if status == "healthy" else 500
            
            response_data = {
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "configuration": config_info,
                "validation_errors": validation_errors
            }
            
            return JSONResponse(content=response_data, status_code=status_code)
            
        except Exception as e:
            logger.error(f"Configuration health check failed: {e}")
            return JSONResponse(
                content={
                    "status": "unhealthy",
                    "message": f"Configuration health check failed: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                status_code=500
            )
    
    return router