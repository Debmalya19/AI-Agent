"""
Database Logging Configuration

Enhanced logging configuration for database operations, errors, and monitoring.
Implements comprehensive logging requirements from PostgreSQL migration spec.
"""

import logging
import logging.handlers
import os
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class DatabaseLogFormatter(logging.Formatter):
    """Custom formatter for database logs with structured data"""
    
    def format(self, record):
        # Create base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        if hasattr(record, 'duration'):
            log_entry['duration_ms'] = record.duration
        if hasattr(record, 'error_category'):
            log_entry['error_category'] = record.error_category
        if hasattr(record, 'retry_count'):
            log_entry['retry_count'] = record.retry_count
        if hasattr(record, 'connection_info'):
            log_entry['connection_info'] = record.connection_info
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)

class DatabaseLogFilter(logging.Filter):
    """Filter for database-related log records"""
    
    def filter(self, record):
        # Only allow database-related logs
        database_loggers = [
            'ai-agent.database',
            'sqlalchemy.engine',
            'sqlalchemy.pool',
            'sqlalchemy.dialects.postgresql',
            'psycopg2'
        ]
        
        return any(record.name.startswith(logger_name) for logger_name in database_loggers)

def setup_database_logging(log_directory: str = "logs", log_level: str = "INFO"):
    """Setup comprehensive database logging configuration"""
    
    # Create log directory
    log_dir = Path(log_directory)
    log_dir.mkdir(exist_ok=True)
    
    # Configure database logger
    db_logger = logging.getLogger('ai-agent.database')
    db_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    for handler in db_logger.handlers[:]:
        db_logger.removeHandler(handler)
    
    # 1. Database operations log file (structured JSON)
    operations_handler = logging.handlers.RotatingFileHandler(
        log_dir / "database_operations.log",
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10
    )
    operations_handler.setLevel(logging.INFO)
    operations_handler.setFormatter(DatabaseLogFormatter())
    db_logger.addHandler(operations_handler)
    
    # 2. Database errors log file (detailed errors)
    errors_handler = logging.handlers.RotatingFileHandler(
        log_dir / "database_errors.log",
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=5
    )
    errors_handler.setLevel(logging.WARNING)
    errors_handler.setFormatter(DatabaseLogFormatter())
    db_logger.addHandler(errors_handler)
    
    # 3. Console handler for development
    if os.getenv("ENVIRONMENT", "development").lower() == "development":
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        db_logger.addHandler(console_handler)
    
    # Configure SQLAlchemy logging
    setup_sqlalchemy_logging(log_dir, log_level)
    
    # Configure psycopg2 logging
    setup_psycopg2_logging(log_dir, log_level)
    
    db_logger.info("Database logging configuration completed")

def setup_sqlalchemy_logging(log_dir: Path, log_level: str):
    """Setup SQLAlchemy-specific logging"""
    
    # SQLAlchemy engine logging (connection events, SQL statements)
    engine_logger = logging.getLogger('sqlalchemy.engine')
    engine_logger.setLevel(logging.INFO if log_level.upper() == "DEBUG" else logging.WARNING)
    
    # SQLAlchemy pool logging (connection pool events)
    pool_logger = logging.getLogger('sqlalchemy.pool')
    pool_logger.setLevel(logging.INFO if log_level.upper() == "DEBUG" else logging.WARNING)
    
    # Create SQLAlchemy log file
    sqlalchemy_handler = logging.handlers.RotatingFileHandler(
        log_dir / "sqlalchemy.log",
        maxBytes=30 * 1024 * 1024,  # 30MB
        backupCount=5
    )
    sqlalchemy_handler.setLevel(logging.INFO)
    sqlalchemy_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    sqlalchemy_handler.setFormatter(sqlalchemy_formatter)
    
    engine_logger.addHandler(sqlalchemy_handler)
    pool_logger.addHandler(sqlalchemy_handler)

def setup_psycopg2_logging(log_dir: Path, log_level: str):
    """Setup psycopg2-specific logging"""
    
    psycopg2_logger = logging.getLogger('psycopg2')
    psycopg2_logger.setLevel(logging.WARNING)  # Only log warnings and errors
    
    # Create psycopg2 log file
    psycopg2_handler = logging.handlers.RotatingFileHandler(
        log_dir / "postgresql_driver.log",
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=3
    )
    psycopg2_handler.setLevel(logging.WARNING)
    psycopg2_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    psycopg2_handler.setFormatter(psycopg2_formatter)
    
    psycopg2_logger.addHandler(psycopg2_handler)

def log_database_operation(operation: str, duration: float = None, success: bool = True, 
                          details: Dict[str, Any] = None, error: Exception = None):
    """Log database operation with structured data"""
    
    logger = logging.getLogger('ai-agent.database')
    
    # Create log record with extra fields
    extra_fields = {
        'operation': operation,
        'success': success
    }
    
    if duration is not None:
        extra_fields['duration'] = round(duration * 1000, 2)  # Convert to ms
    
    if details:
        extra_fields.update(details)
    
    if error:
        from .database import PostgreSQLErrorHandler
        extra_fields['error_category'] = PostgreSQLErrorHandler.get_error_category(error)
        extra_fields['error_type'] = type(error).__name__
    
    # Log with appropriate level
    if success:
        logger.info(f"Database operation completed: {operation}", extra=extra_fields)
    else:
        logger.error(f"Database operation failed: {operation}", extra=extra_fields, exc_info=error)

def log_connection_event(event_type: str, details: Dict[str, Any] = None):
    """Log database connection events"""
    
    logger = logging.getLogger('ai-agent.database')
    
    extra_fields = {
        'operation': 'connection_event',
        'event_type': event_type
    }
    
    if details:
        extra_fields['connection_info'] = details
    
    logger.info(f"Database connection event: {event_type}", extra=extra_fields)

def log_error_with_context(error: Exception, operation: str, context: Dict[str, Any] = None, 
                          retry_count: int = 0):
    """Log database error with full context"""
    
    logger = logging.getLogger('ai-agent.database')
    
    from .database import PostgreSQLErrorHandler
    
    extra_fields = {
        'operation': operation,
        'error_category': PostgreSQLErrorHandler.get_error_category(error),
        'error_type': type(error).__name__,
        'retry_count': retry_count
    }
    
    if context:
        extra_fields.update(context)
    
    logger.error(f"Database error in {operation}: {error}", extra=extra_fields, exc_info=error)

def log_performance_metrics(metrics: Dict[str, Any]):
    """Log database performance metrics"""
    
    logger = logging.getLogger('ai-agent.database')
    
    extra_fields = {
        'operation': 'performance_metrics',
        'metrics': metrics
    }
    
    logger.info("Database performance metrics", extra=extra_fields)

def log_health_check(health_status: str, details: Dict[str, Any] = None):
    """Log database health check results"""
    
    logger = logging.getLogger('ai-agent.database')
    
    extra_fields = {
        'operation': 'health_check',
        'health_status': health_status
    }
    
    if details:
        extra_fields['health_details'] = details
    
    if health_status == "healthy":
        logger.info("Database health check passed", extra=extra_fields)
    else:
        logger.warning(f"Database health check failed: {health_status}", extra=extra_fields)

# Context manager for operation logging
class DatabaseOperationLogger:
    """Context manager for logging database operations"""
    
    def __init__(self, operation: str, details: Dict[str, Any] = None):
        self.operation = operation
        self.details = details or {}
        self.start_time = None
        self.success = False
        self.error = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        log_database_operation(f"{self.operation}_started", details=self.details)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.success = True
            log_database_operation(
                f"{self.operation}_completed",
                duration=duration,
                success=True,
                details=self.details
            )
        else:
            self.error = exc_val
            log_database_operation(
                f"{self.operation}_failed",
                duration=duration,
                success=False,
                details=self.details,
                error=exc_val
            )
        
        return False  # Don't suppress exceptions

# Initialize logging on module import
def initialize_database_logging():
    """Initialize database logging with default configuration"""
    try:
        log_level = os.getenv("DATABASE_LOG_LEVEL", "INFO")
        log_directory = os.getenv("LOG_DIRECTORY", "logs")
        setup_database_logging(log_directory, log_level)
    except Exception as e:
        # Fallback to basic logging if setup fails
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger('ai-agent.database')
        logger.warning(f"Failed to setup advanced database logging: {e}")

# Auto-initialize if not in test environment
if not os.getenv("TESTING"):
    initialize_database_logging()