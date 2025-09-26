"""
Database Monitoring and Error Handling Module

Provides comprehensive monitoring, logging, and error handling for PostgreSQL operations.
Implements requirements 1.4 and 4.4 from the PostgreSQL migration spec.
"""

import time
import logging
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from sqlalchemy import text, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .database import engine, PostgreSQLErrorHandler

logger = logging.getLogger(__name__)

@dataclass
class DatabaseMetrics:
    """Database performance and health metrics"""
    timestamp: datetime
    connection_pool_size: int
    active_connections: int
    idle_connections: int
    overflow_connections: int
    query_count: int
    error_count: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    failed_connections: int
    successful_connections: int

@dataclass
class ErrorMetrics:
    """Database error tracking metrics"""
    timestamp: datetime
    error_type: str
    error_category: str
    error_message: str
    operation: str
    retry_count: int
    resolved: bool
    duration: float

class DatabaseMonitor:
    """Comprehensive database monitoring and metrics collection"""
    
    def __init__(self, metrics_window_minutes: int = 60):
        self.metrics_window = timedelta(minutes=metrics_window_minutes)
        self.query_times = deque(maxlen=1000)  # Store last 1000 query times
        self.error_history = deque(maxlen=500)  # Store last 500 errors
        self.connection_attempts = {"successful": 0, "failed": 0}
        self.query_count = 0
        self.error_count = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        
        # Setup SQLAlchemy event listeners for monitoring
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for automatic monitoring"""
        if not engine:
            logger.warning("Database engine not available, skipping event listener setup")
            return
        
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if hasattr(context, '_query_start_time'):
                query_time = time.time() - context._query_start_time
                self.record_query_time(query_time)
        
        @event.listens_for(engine, "handle_error")
        def handle_error(exception_context):
            self.record_error(
                error=exception_context.original_exception,
                operation="database_query",
                statement=str(exception_context.statement) if exception_context.statement else "unknown"
            )
    
    def record_query_time(self, query_time: float):
        """Record query execution time"""
        with self._lock:
            self.query_times.append((datetime.now(), query_time))
            self.query_count += 1
    
    def record_error(self, error: Exception, operation: str, statement: str = None, retry_count: int = 0):
        """Record database error with categorization"""
        with self._lock:
            error_category = PostgreSQLErrorHandler.get_error_category(error)
            
            error_metric = ErrorMetrics(
                timestamp=datetime.now(),
                error_type=type(error).__name__,
                error_category=error_category,
                error_message=str(error)[:500],  # Truncate long messages
                operation=operation,
                retry_count=retry_count,
                resolved=False,
                duration=0.0
            )
            
            self.error_history.append(error_metric)
            self.error_count += 1
            
            # Log error with appropriate level based on category
            if error_category == "permanent":
                logger.error(f"Permanent database error in {operation}: {error}")
            elif error_category in ["transient", "connection"]:
                logger.warning(f"Transient database error in {operation} (retry {retry_count}): {error}")
            else:
                logger.error(f"Unknown database error in {operation}: {error}")
    
    def record_connection_attempt(self, successful: bool):
        """Record database connection attempt"""
        with self._lock:
            if successful:
                self.connection_attempts["successful"] += 1
            else:
                self.connection_attempts["failed"] += 1
    
    def get_current_metrics(self) -> DatabaseMetrics:
        """Get current database metrics"""
        with self._lock:
            now = datetime.now()
            cutoff_time = now - self.metrics_window
            
            # Filter recent query times
            recent_queries = [
                query_time for timestamp, query_time in self.query_times 
                if timestamp > cutoff_time
            ]
            
            # Calculate response time statistics
            if recent_queries:
                avg_response_time = sum(recent_queries) / len(recent_queries)
                max_response_time = max(recent_queries)
                min_response_time = min(recent_queries)
            else:
                avg_response_time = max_response_time = min_response_time = 0.0
            
            # Get connection pool information
            pool_info = self._get_pool_info()
            
            # Count recent errors
            recent_errors = [
                error for error in self.error_history 
                if error.timestamp > cutoff_time
            ]
            
            return DatabaseMetrics(
                timestamp=now,
                connection_pool_size=pool_info.get("pool_size", 0),
                active_connections=pool_info.get("checked_out", 0),
                idle_connections=pool_info.get("checked_in", 0),
                overflow_connections=pool_info.get("overflow", 0),
                query_count=len(recent_queries),
                error_count=len(recent_errors),
                avg_response_time=avg_response_time * 1000,  # Convert to ms
                max_response_time=max_response_time * 1000,
                min_response_time=min_response_time * 1000,
                failed_connections=self.connection_attempts["failed"],
                successful_connections=self.connection_attempts["successful"]
            )
    
    def _get_pool_info(self) -> Dict[str, Any]:
        """Get connection pool information"""
        if not engine or not hasattr(engine, 'pool'):
            return {}
        
        try:
            pool = engine.pool
            return {
                "pool_size": getattr(pool, 'size', lambda: 0)(),
                "checked_out": getattr(pool, 'checkedout', lambda: 0)(),
                "checked_in": getattr(pool, 'checkedin', lambda: 0)(),
                "overflow": getattr(pool, 'overflow', lambda: 0)(),
            }
        except Exception as e:
            logger.warning(f"Failed to get pool info: {e}")
            return {}
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_errors = [
                error for error in self.error_history 
                if error.timestamp > cutoff_time
            ]
            
            # Group errors by category and type
            error_by_category = defaultdict(int)
            error_by_type = defaultdict(int)
            
            for error in recent_errors:
                error_by_category[error.error_category] += 1
                error_by_type[error.error_type] += 1
            
            return {
                "total_errors": len(recent_errors),
                "error_by_category": dict(error_by_category),
                "error_by_type": dict(error_by_type),
                "recent_errors": [asdict(error) for error in recent_errors[-10:]]  # Last 10 errors
            }
    
    def get_health_score(self) -> float:
        """Calculate database health score (0-100)"""
        metrics = self.get_current_metrics()
        
        # Base score
        score = 100.0
        
        # Penalize for errors (max 30 points)
        if metrics.query_count > 0:
            error_rate = metrics.error_count / metrics.query_count
            score -= min(error_rate * 100, 30)
        
        # Penalize for slow queries (max 20 points)
        if metrics.avg_response_time > 1000:  # > 1 second
            score -= min((metrics.avg_response_time - 1000) / 100, 20)
        
        # Penalize for connection issues (max 25 points)
        total_connections = metrics.failed_connections + metrics.successful_connections
        if total_connections > 0:
            failure_rate = metrics.failed_connections / total_connections
            score -= min(failure_rate * 100, 25)
        
        # Penalize for pool exhaustion (max 25 points)
        if metrics.connection_pool_size > 0:
            pool_usage = metrics.active_connections / metrics.connection_pool_size
            if pool_usage > 0.8:  # > 80% usage
                score -= min((pool_usage - 0.8) * 125, 25)
        
        return max(score, 0.0)

class DatabaseLogger:
    """Enhanced database operation logging"""
    
    def __init__(self, log_file: str = "logs/database.log"):
        self.log_file = log_file
        self.setup_file_logging()
    
    def setup_file_logging(self):
        """Setup file logging for database operations"""
        try:
            import os
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            
            # Create file handler for database logs
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            
            # Add handler to database logger
            db_logger = logging.getLogger('ai-agent.database')
            db_logger.addHandler(file_handler)
            db_logger.setLevel(logging.INFO)
            
        except Exception as e:
            logger.warning(f"Failed to setup database file logging: {e}")
    
    def log_operation(self, operation: str, duration: float, success: bool, details: Dict[str, Any] = None):
        """Log database operation with structured data"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "duration_ms": round(duration * 1000, 2),
            "success": success,
            "details": details or {}
        }
        
        db_logger = logging.getLogger('ai-agent.database')
        if success:
            db_logger.info(f"DB_OPERATION: {json.dumps(log_data)}")
        else:
            db_logger.error(f"DB_OPERATION_FAILED: {json.dumps(log_data)}")

# Global monitor instance
database_monitor = DatabaseMonitor()
database_logger = DatabaseLogger()

def get_database_metrics() -> Dict[str, Any]:
    """Get current database metrics as dictionary"""
    metrics = database_monitor.get_current_metrics()
    return asdict(metrics)

def get_database_health_score() -> float:
    """Get current database health score"""
    return database_monitor.get_health_score()

def get_error_summary(hours: int = 24) -> Dict[str, Any]:
    """Get database error summary"""
    return database_monitor.get_error_summary(hours)

def log_database_operation(operation: str):
    """Decorator to log database operations"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            error_details = None
            
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                error_details = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "error_category": PostgreSQLErrorHandler.get_error_category(e)
                }
                database_monitor.record_error(e, operation)
                raise
            finally:
                duration = time.time() - start_time
                database_logger.log_operation(
                    operation=operation,
                    duration=duration,
                    success=success,
                    details=error_details
                )
        
        return wrapper
    return decorator