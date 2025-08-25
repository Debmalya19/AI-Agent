"""
Resource Monitoring and Limits System for Intelligent Chat UI

This module implements resource monitoring, execution timeouts, memory usage tracking,
and database connection pooling optimization for the intelligent chat system.

Requirements covered:
- 6.1: Resource monitoring and limits
- 6.2: Memory usage optimization
- 6.4: Database connection pooling
"""

import asyncio
import logging
import psutil
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import weakref

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from backend.database import DATABASE_URL


class ResourceType(Enum):
    """Types of resources to monitor."""
    MEMORY = "memory"
    CPU = "cpu"
    DATABASE = "database"
    TOOL_EXECUTION = "tool_execution"
    CONVERSATION_CONTEXT = "conversation_context"


class AlertLevel(Enum):
    """Alert levels for resource monitoring."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class ResourceLimit:
    """Resource limit configuration."""
    resource_type: ResourceType
    soft_limit: float
    hard_limit: float
    unit: str
    enabled: bool = True


@dataclass
class ResourceUsage:
    """Current resource usage information."""
    resource_type: ResourceType
    current_value: float
    percentage_used: float
    limit: Optional[ResourceLimit] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ResourceAlert:
    """Resource alert information."""
    resource_type: ResourceType
    level: AlertLevel
    message: str
    current_usage: ResourceUsage
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExecutionContext:
    """Context for tool execution monitoring."""
    tool_name: str
    start_time: datetime
    timeout: float
    memory_limit: Optional[float] = None
    cpu_limit: Optional[float] = None
    
    def elapsed_time(self) -> float:
        """Get elapsed execution time."""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()
    
    def is_timeout(self) -> bool:
        """Check if execution has timed out."""
        return self.elapsed_time() > self.timeout


class ResourceMonitor:
    """
    Comprehensive resource monitoring system.
    
    Features:
    - Memory usage tracking
    - CPU usage monitoring
    - Database connection monitoring
    - Tool execution timeouts
    - Conversation context memory limits
    - Alert system with configurable thresholds
    """
    
    def __init__(self):
        """Initialize resource monitor."""
        self.logger = logging.getLogger(__name__)
        
        # Resource limits configuration
        self.limits = {
            ResourceType.MEMORY: ResourceLimit(
                resource_type=ResourceType.MEMORY,
                soft_limit=80.0,  # 80% memory usage
                hard_limit=90.0,  # 90% memory usage
                unit="percentage"
            ),
            ResourceType.CPU: ResourceLimit(
                resource_type=ResourceType.CPU,
                soft_limit=70.0,  # 70% CPU usage
                hard_limit=85.0,  # 85% CPU usage
                unit="percentage"
            ),
            ResourceType.DATABASE: ResourceLimit(
                resource_type=ResourceType.DATABASE,
                soft_limit=80.0,  # 80% of pool size
                hard_limit=95.0,  # 95% of pool size
                unit="percentage"
            ),
            ResourceType.TOOL_EXECUTION: ResourceLimit(
                resource_type=ResourceType.TOOL_EXECUTION,
                soft_limit=30.0,  # 30 seconds
                hard_limit=60.0,  # 60 seconds
                unit="seconds"
            ),
            ResourceType.CONVERSATION_CONTEXT: ResourceLimit(
                resource_type=ResourceType.CONVERSATION_CONTEXT,
                soft_limit=50.0,  # 50 MB per conversation
                hard_limit=100.0,  # 100 MB per conversation
                unit="megabytes"
            )
        }
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread = None
        self.monitor_interval = 10  # seconds
        
        # Alert callbacks
        self._alert_callbacks: List[Callable[[ResourceAlert], None]] = []
        
        # Execution contexts
        self._execution_contexts: Dict[str, ExecutionContext] = {}
        self._context_lock = threading.RLock()
        
        # Conversation memory tracking
        self._conversation_memory: Dict[str, float] = {}  # session_id -> memory_mb
        
        # Resource usage history
        self._usage_history: Dict[ResourceType, List[ResourceUsage]] = {
            resource_type: [] for resource_type in ResourceType
        }
        self.history_limit = 100  # Keep last 100 measurements
    
    def start_monitoring(self) -> None:
        """Start resource monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="resource-monitor",
            daemon=True
        )
        self._monitor_thread.start()
        self.logger.info("Started resource monitoring")
    
    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("Stopped resource monitoring")
    
    def add_alert_callback(self, callback: Callable[[ResourceAlert], None]) -> None:
        """Add callback for resource alerts."""
        self._alert_callbacks.append(callback)
    
    def get_current_usage(self) -> Dict[ResourceType, ResourceUsage]:
        """Get current resource usage for all monitored resources."""
        usage = {}
        
        # Memory usage
        memory_info = psutil.virtual_memory()
        usage[ResourceType.MEMORY] = ResourceUsage(
            resource_type=ResourceType.MEMORY,
            current_value=memory_info.percent,
            percentage_used=memory_info.percent,
            limit=self.limits[ResourceType.MEMORY]
        )
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        usage[ResourceType.CPU] = ResourceUsage(
            resource_type=ResourceType.CPU,
            current_value=cpu_percent,
            percentage_used=cpu_percent,
            limit=self.limits[ResourceType.CPU]
        )
        
        # Database connections (if available)
        db_usage = self._get_database_usage()
        if db_usage:
            usage[ResourceType.DATABASE] = db_usage
        
        return usage
    
    def check_resource_limits(self) -> List[ResourceAlert]:
        """Check all resource limits and return alerts."""
        alerts = []
        current_usage = self.get_current_usage()
        
        for resource_type, usage in current_usage.items():
            if not usage.limit or not usage.limit.enabled:
                continue
            
            alert = self._check_single_limit(usage)
            if alert:
                alerts.append(alert)
        
        return alerts
    
    @contextmanager
    def monitor_tool_execution(
        self,
        tool_name: str,
        timeout: float = 60.0,
        memory_limit: Optional[float] = None
    ):
        """
        Context manager for monitoring tool execution.
        
        Args:
            tool_name: Name of the tool being executed
            timeout: Execution timeout in seconds
            memory_limit: Memory limit in MB (optional)
        """
        execution_id = f"{tool_name}_{int(time.time() * 1000)}"
        
        context = ExecutionContext(
            tool_name=tool_name,
            start_time=datetime.now(timezone.utc),
            timeout=timeout,
            memory_limit=memory_limit
        )
        
        with self._context_lock:
            self._execution_contexts[execution_id] = context
        
        try:
            self.logger.debug(f"Started monitoring tool execution: {tool_name}")
            yield context
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Tool execution timeout: {tool_name}")
            raise
            
        except Exception as e:
            self.logger.error(f"Tool execution error: {tool_name} - {e}")
            raise
            
        finally:
            with self._context_lock:
                self._execution_contexts.pop(execution_id, None)
            
            execution_time = context.elapsed_time()
            self.logger.debug(f"Completed tool execution: {tool_name} ({execution_time:.2f}s)")
    
    def track_conversation_memory(self, session_id: str, memory_mb: float) -> bool:
        """
        Track memory usage for a conversation session.
        
        Args:
            session_id: Conversation session ID
            memory_mb: Memory usage in megabytes
            
        Returns:
            True if within limits, False if exceeding limits
        """
        self._conversation_memory[session_id] = memory_mb
        
        limit = self.limits[ResourceType.CONVERSATION_CONTEXT]
        if limit.enabled and memory_mb > limit.hard_limit:
            alert = ResourceAlert(
                resource_type=ResourceType.CONVERSATION_CONTEXT,
                level=AlertLevel.CRITICAL,
                message=f"Conversation {session_id} exceeds memory limit: {memory_mb:.1f}MB",
                current_usage=ResourceUsage(
                    resource_type=ResourceType.CONVERSATION_CONTEXT,
                    current_value=memory_mb,
                    percentage_used=(memory_mb / limit.hard_limit) * 100,
                    limit=limit
                )
            )
            self._trigger_alert(alert)
            return False
        
        return True
    
    def get_conversation_memory_usage(self) -> Dict[str, float]:
        """Get memory usage for all tracked conversations."""
        return self._conversation_memory.copy()
    
    def cleanup_conversation_memory(self, session_id: str) -> None:
        """Clean up memory tracking for a conversation."""
        self._conversation_memory.pop(session_id, None)
    
    def get_usage_history(self, resource_type: ResourceType, limit: int = 50) -> List[ResourceUsage]:
        """Get usage history for a resource type."""
        history = self._usage_history.get(resource_type, [])
        return history[-limit:] if history else []
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        current_usage = self.get_current_usage()
        
        stats = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_usage': {
                resource_type.value: {
                    'current': usage.current_value,
                    'percentage': usage.percentage_used,
                    'limit_soft': usage.limit.soft_limit if usage.limit else None,
                    'limit_hard': usage.limit.hard_limit if usage.limit else None,
                    'unit': usage.limit.unit if usage.limit else None
                }
                for resource_type, usage in current_usage.items()
            },
            'active_executions': len(self._execution_contexts),
            'tracked_conversations': len(self._conversation_memory),
            'total_conversation_memory': sum(self._conversation_memory.values()),
            'monitoring_active': self._monitoring
        }
        
        return stats
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                # Check resource limits
                alerts = self.check_resource_limits()
                for alert in alerts:
                    self._trigger_alert(alert)
                
                # Check tool execution timeouts
                self._check_execution_timeouts()
                
                # Update usage history
                self._update_usage_history()
                
                # Clean up old history
                self._cleanup_history()
                
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                self.logger.error(f"Error in resource monitoring loop: {e}")
                time.sleep(5)  # Wait before retrying
    
    def _check_single_limit(self, usage: ResourceUsage) -> Optional[ResourceAlert]:
        """Check a single resource limit and return alert if needed."""
        if not usage.limit:
            return None
        
        if usage.percentage_used >= usage.limit.hard_limit:
            return ResourceAlert(
                resource_type=usage.resource_type,
                level=AlertLevel.CRITICAL,
                message=f"{usage.resource_type.value} usage critical: {usage.current_value:.1f}{usage.limit.unit}",
                current_usage=usage
            )
        elif usage.percentage_used >= usage.limit.soft_limit:
            return ResourceAlert(
                resource_type=usage.resource_type,
                level=AlertLevel.WARNING,
                message=f"{usage.resource_type.value} usage high: {usage.current_value:.1f}{usage.limit.unit}",
                current_usage=usage
            )
        
        return None
    
    def _check_execution_timeouts(self) -> None:
        """Check for tool execution timeouts."""
        with self._context_lock:
            timed_out = []
            
            for execution_id, context in self._execution_contexts.items():
                if context.is_timeout():
                    timed_out.append((execution_id, context))
            
            for execution_id, context in timed_out:
                alert = ResourceAlert(
                    resource_type=ResourceType.TOOL_EXECUTION,
                    level=AlertLevel.WARNING,
                    message=f"Tool execution timeout: {context.tool_name} ({context.elapsed_time():.1f}s)",
                    current_usage=ResourceUsage(
                        resource_type=ResourceType.TOOL_EXECUTION,
                        current_value=context.elapsed_time(),
                        percentage_used=(context.elapsed_time() / context.timeout) * 100
                    )
                )
                self._trigger_alert(alert)
    
    def _get_database_usage(self) -> Optional[ResourceUsage]:
        """Get database connection pool usage."""
        try:
            # This would need to be implemented based on the specific
            # database connection pool being used
            # For now, return None as placeholder
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting database usage: {e}")
            return None
    
    def _update_usage_history(self) -> None:
        """Update usage history for all resource types."""
        current_usage = self.get_current_usage()
        
        for resource_type, usage in current_usage.items():
            history = self._usage_history[resource_type]
            history.append(usage)
            
            # Keep only recent history
            if len(history) > self.history_limit:
                history.pop(0)
    
    def _cleanup_history(self) -> None:
        """Clean up old usage history."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        for resource_type, history in self._usage_history.items():
            # Remove entries older than 24 hours
            self._usage_history[resource_type] = [
                usage for usage in history
                if usage.timestamp > cutoff_time
            ]
    
    def _trigger_alert(self, alert: ResourceAlert) -> None:
        """Trigger alert callbacks."""
        self.logger.warning(f"Resource alert: {alert.message}")
        
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")


class DatabaseConnectionManager:
    """
    Optimized database connection manager with pooling and monitoring.
    """
    
    def __init__(self, database_url: str = DATABASE_URL):
        """Initialize connection manager."""
        self.database_url = database_url
        self.logger = logging.getLogger(__name__)
        
        # Connection pool configuration
        self.pool_size = 10
        self.max_overflow = 20
        self.pool_timeout = 30
        self.pool_recycle = 3600  # 1 hour
        
        # Create optimized engine
        self.engine = self._create_optimized_engine()
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Connection monitoring
        self._active_connections = 0
        self._connection_stats = {
            'total_created': 0,
            'total_closed': 0,
            'current_active': 0,
            'peak_active': 0
        }
        
        # Setup connection event listeners
        self._setup_connection_events()
    
    def _create_optimized_engine(self):
        """Create optimized database engine with connection pooling."""
        return create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_timeout=self.pool_timeout,
            pool_recycle=self.pool_recycle,
            pool_pre_ping=True,  # Validate connections before use
            echo=False,  # Set to True for debugging
            connect_args={
                "connect_timeout": 10,
                "application_name": "intelligent_chat_ui"
            }
        )
    
    def _setup_connection_events(self):
        """Setup connection event listeners for monitoring."""
        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            self._connection_stats['total_created'] += 1
            self._active_connections += 1
            self._connection_stats['current_active'] = self._active_connections
            
            if self._active_connections > self._connection_stats['peak_active']:
                self._connection_stats['peak_active'] = self._active_connections
        
        @event.listens_for(self.engine, "close")
        def on_close(dbapi_connection, connection_record):
            self._connection_stats['total_closed'] += 1
            self._active_connections = max(0, self._active_connections - 1)
            self._connection_stats['current_active'] = self._active_connections
    
    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        pool = self.engine.pool
        
        try:
            # Some pool methods may not be available in all SQLAlchemy versions
            pool_size = pool.size() if hasattr(pool, 'size') else self.pool_size
            checked_in = pool.checkedin() if hasattr(pool, 'checkedin') else 0
            checked_out = pool.checkedout() if hasattr(pool, 'checkedout') else 0
            overflow = pool.overflow() if hasattr(pool, 'overflow') else 0
            
            return {
                'pool_size': pool_size,
                'checked_in': checked_in,
                'checked_out': checked_out,
                'overflow': overflow,
                'total_created': self._connection_stats['total_created'],
                'total_closed': self._connection_stats['total_closed'],
                'current_active': self._connection_stats['current_active'],
                'peak_active': self._connection_stats['peak_active'],
                'utilization_percent': (checked_out / max(pool_size + overflow, 1)) * 100
            }
        except Exception as e:
            self.logger.error(f"Error getting connection stats: {e}")
            return {
                'pool_size': self.pool_size,
                'checked_in': 0,
                'checked_out': 0,
                'overflow': 0,
                'total_created': self._connection_stats['total_created'],
                'total_closed': self._connection_stats['total_closed'],
                'current_active': self._connection_stats['current_active'],
                'peak_active': self._connection_stats['peak_active'],
                'utilization_percent': 0
            }
    
    def health_check(self) -> bool:
        """Perform database health check."""
        try:
            from sqlalchemy import text
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False


# Global instances
_resource_monitor = None
_db_manager = None


def get_resource_monitor() -> ResourceMonitor:
    """Get global resource monitor instance."""
    global _resource_monitor
    if _resource_monitor is None:
        _resource_monitor = ResourceMonitor()
    return _resource_monitor


def get_db_manager() -> DatabaseConnectionManager:
    """Get global database connection manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseConnectionManager()
    return _db_manager


def start_resource_monitoring() -> None:
    """Start global resource monitoring."""
    monitor = get_resource_monitor()
    monitor.start_monitoring()


def stop_resource_monitoring() -> None:
    """Stop global resource monitoring."""
    global _resource_monitor
    if _resource_monitor:
        _resource_monitor.stop_monitoring()