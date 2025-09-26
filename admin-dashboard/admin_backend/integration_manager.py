# Main Integration Manager
# Coordinates all integration components and provides unified interface

import asyncio
import threading
import time
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import asynccontextmanager
import redis
from flask import Flask, current_app
from sqlalchemy import event
from sqlalchemy.orm import Session

# Import local modules
from .models import db, User
from .models_support import Ticket, TicketComment, PerformanceMetric
from .integration_api import IntegrationManager, integration_manager
from .realtime_sync import RealTimeSyncService, sync_service, IntegrationEvent, EventType
from .error_handling import ErrorHandler, error_handler, ErrorCategory, ErrorSeverity, ErrorContext
from .security import SecurityManager, security_manager, Permission, Role
from .data_pipeline import DataPipeline, data_pipeline, init_data_pipeline
from .monitoring import MonitoringSystem, monitoring_system, init_monitoring_system

# Setup logging
logger = logging.getLogger(__name__)

class IntegrationStatus(Enum):
    """Integration system status"""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"
    STOPPED = "stopped"

class ComponentStatus(Enum):
    """Individual component status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"

@dataclass
class ComponentHealth:
    """Health status of a component"""
    name: str
    status: ComponentStatus
    last_check: datetime
    error_count: int = 0
    last_error: Optional[str] = None
    uptime: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class IntegrationConfig:
    """Configuration for the integration system"""
    # Database configuration
    database_url: str
    
    # Redis configuration
    redis_url: str = "redis://localhost:6379"
    
    # AI Agent backend configuration
    ai_agent_url: str = "http://localhost:8000"
    ai_agent_timeout: int = 30
    
    # Security configuration
    jwt_secret_key: str = "your-secret-key"
    encryption_key: Optional[str] = None
    
    # Monitoring configuration
    monitoring_enabled: bool = True
    metrics_retention_days: int = 30
    alert_email_enabled: bool = False
    
    # Data pipeline configuration
    pipeline_max_workers: int = 4
    pipeline_batch_size: int = 100
    
    # Real-time sync configuration
    sync_enabled: bool = True
    sync_interval: int = 60
    websocket_enabled: bool = True
    
    # Error handling configuration
    max_retry_attempts: int = 3
    error_notification_enabled: bool = True
    
    # Performance configuration
    cache_enabled: bool = True
    cache_ttl: int = 3600
    
    @classmethod
    def from_flask_config(cls, app: Flask) -> 'IntegrationConfig':
        """Create configuration from Flask app config"""
        return cls(
            database_url=app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///admin_dashboard.db'),
            redis_url=app.config.get('REDIS_URL', 'redis://localhost:6379'),
            ai_agent_url=app.config.get('AI_AGENT_BACKEND_URL', 'http://localhost:8000'),
            ai_agent_timeout=app.config.get('AI_AGENT_TIMEOUT', 30),
            jwt_secret_key=app.config.get('JWT_SECRET_KEY', 'your-secret-key'),
            encryption_key=app.config.get('ENCRYPTION_KEY'),
            monitoring_enabled=app.config.get('MONITORING_ENABLED', True),
            metrics_retention_days=app.config.get('METRICS_RETENTION_DAYS', 30),
            alert_email_enabled=app.config.get('ALERT_EMAIL_ENABLED', False),
            pipeline_max_workers=app.config.get('PIPELINE_MAX_WORKERS', 4),
            pipeline_batch_size=app.config.get('PIPELINE_BATCH_SIZE', 100),
            sync_enabled=app.config.get('SYNC_ENABLED', True),
            sync_interval=app.config.get('SYNC_INTERVAL', 60),
            websocket_enabled=app.config.get('WEBSOCKET_ENABLED', True),
            max_retry_attempts=app.config.get('MAX_RETRY_ATTEMPTS', 3),
            error_notification_enabled=app.config.get('ERROR_NOTIFICATION_ENABLED', True),
            cache_enabled=app.config.get('CACHE_ENABLED', True),
            cache_ttl=app.config.get('CACHE_TTL', 3600)
        )

class AdminDashboardIntegration:
    """Main integration manager for the admin dashboard"""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.status = IntegrationStatus.INITIALIZING
        self.components = {}
        self.component_health = {}
        self.start_time = datetime.utcnow()
        self.redis_client = None
        
        # Component references
        self.integration_api = None
        self.sync_service = None
        self.error_handler = None
        self.security_manager = None
        self.data_pipeline = None
        self.monitoring_system = None
        
        # Event handlers
        self.event_handlers = {}
        
        # Background tasks
        self.background_tasks = []
        self.running = False
        
        logger.info("Admin Dashboard Integration initialized")
    
    async def initialize(self, app: Flask = None):
        """Initialize all integration components"""
        try:
            self.status = IntegrationStatus.INITIALIZING
            logger.info("Starting integration system initialization...")
            
            # Initialize Redis connection
            await self._init_redis()
            
            # Initialize core components
            await self._init_error_handler()
            await self._init_security_manager()
            await self._init_data_pipeline()
            await self._init_monitoring_system()
            await self._init_integration_api()
            await self._init_sync_service()
            
            # Setup database event listeners
            self._setup_database_events()
            
            # Start background tasks
            await self._start_background_tasks()
            
            # Register Flask app if provided
            if app:
                self._register_flask_app(app)
            
            self.status = IntegrationStatus.HEALTHY
            self.running = True
            
            logger.info("Integration system initialization completed successfully")
            
        except Exception as e:
            self.status = IntegrationStatus.CRITICAL
            logger.error(f"Integration system initialization failed: {e}")
            raise
    
    async def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(self.config.redis_url, decode_responses=False)
            await asyncio.get_event_loop().run_in_executor(None, self.redis_client.ping)
            
            self._update_component_health('redis', ComponentStatus.ACTIVE)
            logger.info("Redis connection established")
            
        except Exception as e:
            self._update_component_health('redis', ComponentStatus.ERROR, str(e))
            logger.error(f"Failed to connect to Redis: {e}")
            # Continue without Redis - some features will be degraded
    
    async def _init_error_handler(self):
        """Initialize error handling system"""
        try:
            global error_handler
            if not error_handler:
                from .error_handling import init_error_handler
                error_handler = init_error_handler({
                    'redis_url': self.config.redis_url,
                    'max_retry_attempts': self.config.max_retry_attempts,
                    'notification_enabled': self.config.error_notification_enabled
                })
            
            self.error_handler = error_handler
            self._update_component_health('error_handler', ComponentStatus.ACTIVE)
            logger.info("Error handler initialized")
            
        except Exception as e:
            self._update_component_health('error_handler', ComponentStatus.ERROR, str(e))
            logger.error(f"Failed to initialize error handler: {e}")
            raise
    
    async def _init_security_manager(self):
        """Initialize security management system"""
        try:
            global security_manager
            if not security_manager:
                from .security import init_security_manager
                security_manager = init_security_manager({
                    'jwt_secret_key': self.config.jwt_secret_key,
                    'encryption_key': self.config.encryption_key,
                    'redis_url': self.config.redis_url
                })
            
            self.security_manager = security_manager
            self._update_component_health('security_manager', ComponentStatus.ACTIVE)
            logger.info("Security manager initialized")
            
        except Exception as e:
            self._update_component_health('security_manager', ComponentStatus.ERROR, str(e))
            logger.error(f"Failed to initialize security manager: {e}")
            raise
    
    async def _init_data_pipeline(self):
        """Initialize data processing pipeline"""
        try:
            global data_pipeline
            if not data_pipeline:
                pipeline_config = {
                    'max_workers': self.config.pipeline_max_workers,
                    'batch_size': self.config.pipeline_batch_size,
                    'redis_url': self.config.redis_url,
                    'cache': {
                        'enabled': self.config.cache_enabled,
                        'default_ttl': self.config.cache_ttl
                    }
                }
                data_pipeline = init_data_pipeline(pipeline_config)
            
            self.data_pipeline = data_pipeline
            self._update_component_health('data_pipeline', ComponentStatus.ACTIVE)
            logger.info("Data pipeline initialized")
            
        except Exception as e:
            self._update_component_health('data_pipeline', ComponentStatus.ERROR, str(e))
            logger.error(f"Failed to initialize data pipeline: {e}")
            raise
    
    async def _init_monitoring_system(self):
        """Initialize monitoring system"""
        try:
            if self.config.monitoring_enabled:
                global monitoring_system
                if not monitoring_system:
                    monitoring_system = init_monitoring_system(
                        config_dir="config",
                        redis_url=self.config.redis_url
                    )
                
                self.monitoring_system = monitoring_system
                self._update_component_health('monitoring_system', ComponentStatus.ACTIVE)
                logger.info("Monitoring system initialized")
            else:
                logger.info("Monitoring system disabled")
                
        except Exception as e:
            self._update_component_health('monitoring_system', ComponentStatus.ERROR, str(e))
            logger.error(f"Failed to initialize monitoring system: {e}")
            # Continue without monitoring - not critical
    
    async def _init_integration_api(self):
        """Initialize integration API"""
        try:
            global integration_manager
            if not integration_manager:
                from .integration_api import init_integration_manager
                integration_manager = init_integration_manager({
                    'ai_agent_url': self.config.ai_agent_url,
                    'timeout': self.config.ai_agent_timeout,
                    'redis_url': self.config.redis_url
                })
            
            self.integration_api = integration_manager
            self._update_component_health('integration_api', ComponentStatus.ACTIVE)
            logger.info("Integration API initialized")
            
        except Exception as e:
            self._update_component_health('integration_api', ComponentStatus.ERROR, str(e))
            logger.error(f"Failed to initialize integration API: {e}")
            raise
    
    async def _init_sync_service(self):
        """Initialize real-time sync service"""
        try:
            if self.config.sync_enabled:
                global sync_service
                if not sync_service:
                    from .realtime_sync import init_sync_service
                    sync_service = init_sync_service({
                        'redis_url': self.config.redis_url,
                        'sync_interval': self.config.sync_interval,
                        'websocket_enabled': self.config.websocket_enabled
                    })
                
                self.sync_service = sync_service
                self._update_component_health('sync_service', ComponentStatus.ACTIVE)
                logger.info("Sync service initialized")
            else:
                logger.info("Sync service disabled")
                
        except Exception as e:
            self._update_component_health('sync_service', ComponentStatus.ERROR, str(e))
            logger.error(f"Failed to initialize sync service: {e}")
            # Continue without sync - not critical for basic functionality
    
    def _setup_database_events(self):
        """Setup database event listeners for real-time sync"""
        try:
            # Listen for ticket changes
            @event.listens_for(Ticket, 'after_insert')
            def ticket_created(mapper, connection, target):
                self._emit_database_event('ticket_created', target)
            
            @event.listens_for(Ticket, 'after_update')
            def ticket_updated(mapper, connection, target):
                self._emit_database_event('ticket_updated', target)
            
            @event.listens_for(Ticket, 'after_delete')
            def ticket_deleted(mapper, connection, target):
                self._emit_database_event('ticket_deleted', target)
            
            # Listen for user changes
            @event.listens_for(User, 'after_insert')
            def user_created(mapper, connection, target):
                self._emit_database_event('user_created', target)
            
            @event.listens_for(User, 'after_update')
            def user_updated(mapper, connection, target):
                self._emit_database_event('user_updated', target)
            
            logger.info("Database event listeners setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup database events: {e}")
    
    def _emit_database_event(self, event_type: str, entity):
        """Emit database change event"""
        try:
            if self.sync_service:
                # Determine entity type and ID
                entity_type = entity.__class__.__name__.lower()
                entity_id = getattr(entity, 'id', None)
                
                if entity_id:
                    # Create integration event
                    integration_event = IntegrationEvent(
                        event_type=EventType.DATA_SYNC,
                        entity_id=str(entity_id),
                        entity_type=entity_type,
                        data={'action': event_type, 'timestamp': datetime.utcnow().isoformat()},
                        timestamp=datetime.utcnow()
                    )
                    
                    # Emit event
                    self.sync_service.emit_event(integration_event)
                    
        except Exception as e:
            logger.error(f"Failed to emit database event: {e}")
    
    async def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        try:
            # Health check task
            health_task = asyncio.create_task(self._health_check_loop())
            self.background_tasks.append(health_task)
            
            # Metrics collection task
            if self.monitoring_system:
                metrics_task = asyncio.create_task(self._metrics_collection_loop())
                self.background_tasks.append(metrics_task)
            
            # Cleanup task
            cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.background_tasks.append(cleanup_task)
            
            logger.info("Background tasks started")
            
        except Exception as e:
            logger.error(f"Failed to start background tasks: {e}")
    
    async def _health_check_loop(self):
        """Background health check loop"""
        while self.running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(300)
    
    async def _metrics_collection_loop(self):
        """Background metrics collection loop"""
        while self.running:
            try:
                await self._collect_integration_metrics()
                await asyncio.sleep(60)  # Collect every minute
            except Exception as e:
                logger.error(f"Metrics collection loop error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while self.running:
            try:
                await self._perform_cleanup()
                await asyncio.sleep(3600)  # Cleanup every hour
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(3600)
    
    async def _perform_health_checks(self):
        """Perform health checks on all components"""
        try:
            # Check Redis connection
            if self.redis_client:
                try:
                    await asyncio.get_event_loop().run_in_executor(None, self.redis_client.ping)
                    self._update_component_health('redis', ComponentStatus.ACTIVE)
                except Exception as e:
                    self._update_component_health('redis', ComponentStatus.ERROR, str(e))
            
            # Check AI Agent backend
            if self.integration_api:
                try:
                    health_status = await self.integration_api.check_health()
                    if health_status.get('status') == 'healthy':
                        self._update_component_health('ai_agent_backend', ComponentStatus.ACTIVE)
                    else:
                        self._update_component_health('ai_agent_backend', ComponentStatus.ERROR, 'Unhealthy')
                except Exception as e:
                    self._update_component_health('ai_agent_backend', ComponentStatus.ERROR, str(e))
            
            # Check database connection
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: db.session.execute(db.text('SELECT 1'))
                )
                self._update_component_health('database', ComponentStatus.ACTIVE)
            except Exception as e:
                self._update_component_health('database', ComponentStatus.ERROR, str(e))
            
            # Update overall status
            self._update_overall_status()
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
    
    async def _collect_integration_metrics(self):
        """Collect integration-specific metrics"""
        try:
            if self.monitoring_system and self.monitoring_system.metrics_collector:
                # Collect component health metrics
                for component_name, health in self.component_health.items():
                    metric_name = f"integration.component.{component_name}.status"
                    status_value = 1 if health.status == ComponentStatus.ACTIVE else 0
                    
                    self.monitoring_system.metrics_collector.collect_metric(
                        metric_name, status_value, 
                        tags={'component': component_name},
                        metadata={'last_error': health.last_error}
                    )
                
                # Collect uptime metric
                uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
                self.monitoring_system.metrics_collector.collect_metric(
                    "integration.uptime", uptime_seconds
                )
                
                # Collect status metric
                status_value = {
                    IntegrationStatus.HEALTHY: 1,
                    IntegrationStatus.DEGRADED: 0.5,
                    IntegrationStatus.CRITICAL: 0,
                    IntegrationStatus.MAINTENANCE: 0.8
                }.get(self.status, 0)
                
                self.monitoring_system.metrics_collector.collect_metric(
                    "integration.status", status_value
                )
                
        except Exception as e:
            logger.error(f"Metrics collection error: {e}")
    
    async def _perform_cleanup(self):
        """Perform periodic cleanup tasks"""
        try:
            # Clean up old metrics
            if self.monitoring_system:
                cutoff_date = datetime.utcnow() - timedelta(days=self.config.metrics_retention_days)
                
                # Clean up old performance metrics
                deleted_count = db.session.query(PerformanceMetric).filter(
                    PerformanceMetric.timestamp < cutoff_date
                ).delete()
                
                if deleted_count > 0:
                    db.session.commit()
                    logger.info(f"Cleaned up {deleted_count} old performance metrics")
            
            # Clean up Redis cache if needed
            if self.redis_client:
                # This would implement cache cleanup logic
                pass
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            db.session.rollback()
    
    def _update_component_health(self, component_name: str, status: ComponentStatus, error: str = None):
        """Update component health status"""
        if component_name not in self.component_health:
            self.component_health[component_name] = ComponentHealth(
                name=component_name,
                status=status,
                last_check=datetime.utcnow()
            )
        else:
            health = self.component_health[component_name]
            
            # Update status
            if health.status != status:
                if status == ComponentStatus.ERROR:
                    health.error_count += 1
                    health.last_error = error
                elif status == ComponentStatus.ACTIVE:
                    health.error_count = 0
                    health.last_error = None
                
                health.status = status
            
            health.last_check = datetime.utcnow()
            
            # Calculate uptime
            if status == ComponentStatus.ACTIVE:
                health.uptime = (datetime.utcnow() - self.start_time).total_seconds()
    
    def _update_overall_status(self):
        """Update overall integration status based on component health"""
        if not self.component_health:
            self.status = IntegrationStatus.INITIALIZING
            return
        
        critical_components = ['database', 'error_handler', 'security_manager']
        critical_errors = sum(1 for name, health in self.component_health.items() 
                            if name in critical_components and health.status == ComponentStatus.ERROR)
        
        total_errors = sum(1 for health in self.component_health.values() 
                         if health.status == ComponentStatus.ERROR)
        
        if critical_errors > 0:
            self.status = IntegrationStatus.CRITICAL
        elif total_errors > len(self.component_health) // 2:
            self.status = IntegrationStatus.DEGRADED
        else:
            self.status = IntegrationStatus.HEALTHY
    
    def _register_flask_app(self, app: Flask):
        """Register integration with Flask app"""
        try:
            # Add integration routes
            from .integration_routes import create_integration_blueprint
            integration_bp = create_integration_blueprint(self)
            app.register_blueprint(integration_bp, url_prefix='/api/integration')
            
            # Add error handlers
            @app.errorhandler(Exception)
            def handle_error(error):
                if self.error_handler:
                    context = ErrorContext(
                        operation='flask_request',
                        component='admin_dashboard',
                        user_id=getattr(current_app, 'current_user_id', None)
                    )
                    self.error_handler.handle_error(error, context, ErrorSeverity.MEDIUM, ErrorCategory.APPLICATION)
                
                return {'error': 'Internal server error'}, 500
            
            logger.info("Flask app integration completed")
            
        except Exception as e:
            logger.error(f"Failed to register Flask app: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status"""
        return {
            'status': self.status.value,
            'uptime': (datetime.utcnow() - self.start_time).total_seconds(),
            'components': {
                name: {
                    'status': health.status.value,
                    'last_check': health.last_check.isoformat(),
                    'error_count': health.error_count,
                    'last_error': health.last_error,
                    'uptime': health.uptime
                }
                for name, health in self.component_health.items()
            },
            'config': {
                'ai_agent_url': self.config.ai_agent_url,
                'sync_enabled': self.config.sync_enabled,
                'monitoring_enabled': self.config.monitoring_enabled,
                'cache_enabled': self.config.cache_enabled
            },
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def get_health(self) -> Dict[str, Any]:
        """Get health status for health checks"""
        healthy_components = sum(1 for health in self.component_health.values() 
                               if health.status == ComponentStatus.ACTIVE)
        total_components = len(self.component_health)
        
        return {
            'status': 'healthy' if self.status == IntegrationStatus.HEALTHY else 'unhealthy',
            'components_healthy': f"{healthy_components}/{total_components}",
            'uptime': (datetime.utcnow() - self.start_time).total_seconds(),
            'version': '1.0.0'
        }
    
    async def shutdown(self):
        """Gracefully shutdown the integration system"""
        try:
            self.status = IntegrationStatus.STOPPING
            self.running = False
            
            logger.info("Shutting down integration system...")
            
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # Shutdown components
            if self.sync_service:
                await self.sync_service.stop()
            
            if self.data_pipeline:
                self.data_pipeline.stop()
            
            if self.monitoring_system:
                self.monitoring_system.stop()
            
            # Close Redis connection
            if self.redis_client:
                await asyncio.get_event_loop().run_in_executor(None, self.redis_client.close)
            
            self.status = IntegrationStatus.STOPPED
            logger.info("Integration system shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            self.status = IntegrationStatus.CRITICAL

# Global integration instance
admin_integration = None

async def init_admin_integration(config: IntegrationConfig, app: Flask = None) -> AdminDashboardIntegration:
    """Initialize the admin dashboard integration"""
    global admin_integration
    
    if admin_integration is None:
        admin_integration = AdminDashboardIntegration(config)
        await admin_integration.initialize(app)
    
    return admin_integration

def get_integration_status() -> Dict[str, Any]:
    """Get current integration status"""
    if admin_integration is None:
        return {
            'status': 'not_initialized',
            'message': 'Integration system not initialized'
        }
    
    return admin_integration.get_status()

def get_integration_health() -> Dict[str, Any]:
    """Get integration health for health checks"""
    if admin_integration is None:
        return {
            'status': 'unhealthy',
            'message': 'Integration system not initialized'
        }
    
    return admin_integration.get_health()

# Context manager for integration lifecycle
@asynccontextmanager
async def integration_context(config: IntegrationConfig, app: Flask = None):
    """Context manager for integration lifecycle"""
    integration = None
    try:
        integration = await init_admin_integration(config, app)
        yield integration
    finally:
        if integration:
            await integration.shutdown()