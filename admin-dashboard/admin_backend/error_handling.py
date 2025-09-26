# Comprehensive Error Handling System
# Implements automatic retry logic, detailed logging, alerting, and graceful degradation

import logging
import traceback
import functools
import time
import json
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
from queue import Queue, Empty
import redis
import requests
from flask import current_app, request, g
import sys
import os
from contextlib import contextmanager

# Setup structured logging
class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add request context if available
        if hasattr(g, 'request_id'):
            log_data['request_id'] = g.request_id
        
        if request:
            log_data['request'] = {
                'method': request.method,
                'url': request.url,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', '')
            }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                log_data['extra'] = log_data.get('extra', {})
                log_data['extra'][key] = value
        
        return json.dumps(log_data, default=str)

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    DATABASE = "database"
    API = "api"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    INTEGRATION = "integration"
    SYSTEM = "system"
    NETWORK = "network"
    PERFORMANCE = "performance"

@dataclass
class ErrorContext:
    """Context information for errors"""
    request_id: Optional[str] = None
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

@dataclass
class ErrorInfo:
    """Comprehensive error information"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    exception_type: str
    traceback: List[str]
    context: ErrorContext
    retry_count: int = 0
    resolved: bool = False
    resolution_time: Optional[datetime] = None

class RetryConfig:
    """Configuration for retry logic"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        delay = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)
        
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
        
        return delay

class AlertManager:
    """Manages error alerts and notifications"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.alert_queue = Queue()
        self.email_config = config.get('email', {})
        self.webhook_config = config.get('webhook', {})
        self.redis_client = None
        
        # Initialize Redis for alert throttling
        try:
            redis_url = config.get('redis_url', 'redis://localhost:6379')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logging.error(f"Failed to connect to Redis for alerts: {e}")
        
        # Start alert processing thread
        self.alert_thread = threading.Thread(target=self._process_alerts, daemon=True)
        self.alert_thread.start()
    
    def send_alert(self, error_info: ErrorInfo, throttle_key: Optional[str] = None):
        """Send alert for error"""
        # Check if alert should be throttled
        if throttle_key and self._is_throttled(throttle_key):
            return
        
        alert_data = {
            'error_info': asdict(error_info),
            'throttle_key': throttle_key,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.alert_queue.put(alert_data)
        
        # Set throttle if specified
        if throttle_key:
            self._set_throttle(throttle_key)
    
    def _is_throttled(self, throttle_key: str) -> bool:
        """Check if alert is throttled"""
        if not self.redis_client:
            return False
        
        try:
            return self.redis_client.exists(f"alert_throttle:{throttle_key}")
        except Exception:
            return False
    
    def _set_throttle(self, throttle_key: str, duration: int = 300):
        """Set alert throttle"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.setex(f"alert_throttle:{throttle_key}", duration, "1")
        except Exception as e:
            logging.error(f"Failed to set alert throttle: {e}")
    
    def _process_alerts(self):
        """Process alerts in background thread"""
        while True:
            try:
                alert_data = self.alert_queue.get(timeout=1)
                self._send_alert_notifications(alert_data)
            except Empty:
                continue
            except Exception as e:
                logging.error(f"Error processing alert: {e}")
    
    def _send_alert_notifications(self, alert_data: Dict):
        """Send alert notifications via configured channels"""
        error_info = alert_data['error_info']
        
        # Send email alert
        if self.email_config.get('enabled', False):
            self._send_email_alert(error_info)
        
        # Send webhook alert
        if self.webhook_config.get('enabled', False):
            self._send_webhook_alert(error_info)
    
    def _send_email_alert(self, error_info: Dict):
        """Send email alert"""
        try:
            smtp_server = self.email_config.get('smtp_server')
            smtp_port = self.email_config.get('smtp_port', 587)
            username = self.email_config.get('username')
            password = self.email_config.get('password')
            from_email = self.email_config.get('from_email')
            to_emails = self.email_config.get('to_emails', [])
            
            if not all([smtp_server, username, password, from_email, to_emails]):
                logging.warning("Email configuration incomplete, skipping email alert")
                return
            
            subject = f"[{error_info['severity'].upper()}] Error Alert - {error_info['category']}"
            
            body = f"""
            Error Alert
            
            Error ID: {error_info['error_id']}
            Timestamp: {error_info['timestamp']}
            Severity: {error_info['severity']}
            Category: {error_info['category']}
            Message: {error_info['message']}
            Exception Type: {error_info['exception_type']}
            
            Context:
            - Request ID: {error_info['context'].get('request_id', 'N/A')}
            - User ID: {error_info['context'].get('user_id', 'N/A')}
            - Operation: {error_info['context'].get('operation', 'N/A')}
            - Component: {error_info['context'].get('component', 'N/A')}
            
            Traceback:
            {''.join(error_info['traceback'])}
            """
            
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            logging.info(f"Email alert sent for error {error_info['error_id']}")
            
        except Exception as e:
            logging.error(f"Failed to send email alert: {e}")
    
    def _send_webhook_alert(self, error_info: Dict):
        """Send webhook alert"""
        try:
            webhook_url = self.webhook_config.get('url')
            headers = self.webhook_config.get('headers', {})
            
            if not webhook_url:
                logging.warning("Webhook URL not configured, skipping webhook alert")
                return
            
            payload = {
                'alert_type': 'error',
                'error_info': error_info,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logging.info(f"Webhook alert sent for error {error_info['error_id']}")
            else:
                logging.error(f"Webhook alert failed with status {response.status_code}")
                
        except Exception as e:
            logging.error(f"Failed to send webhook alert: {e}")

class ErrorHandler:
    """Comprehensive error handling system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.alert_manager = AlertManager(config.get('alerts', {}))
        self.error_storage = []
        self.max_stored_errors = config.get('max_stored_errors', 1000)
        
        # Setup structured logging
        self._setup_logging()
        
        # Default retry configurations
        self.retry_configs = {
            ErrorCategory.DATABASE: RetryConfig(max_attempts=3, base_delay=1.0),
            ErrorCategory.API: RetryConfig(max_attempts=5, base_delay=0.5),
            ErrorCategory.NETWORK: RetryConfig(max_attempts=3, base_delay=2.0),
            ErrorCategory.INTEGRATION: RetryConfig(max_attempts=2, base_delay=1.0)
        }
    
    def _setup_logging(self):
        """Setup structured logging"""
        # Create logger
        self.logger = logging.getLogger('error_handler')
        self.logger.setLevel(logging.INFO)
        
        # Create handlers
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create file handler if configured
        log_file = self.config.get('log_file')
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(file_handler)
        
        # Set formatter
        console_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(console_handler)
    
    def handle_error(self, exception: Exception, context: ErrorContext, 
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    category: ErrorCategory = ErrorCategory.SYSTEM) -> ErrorInfo:
        """Handle an error with comprehensive logging and alerting"""
        import uuid
        
        error_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        error_info = ErrorInfo(
            error_id=error_id,
            timestamp=timestamp,
            severity=severity,
            category=category,
            message=str(exception),
            exception_type=type(exception).__name__,
            traceback=traceback.format_exception(type(exception), exception, exception.__traceback__),
            context=context
        )
        
        # Log the error
        self._log_error(error_info)
        
        # Store the error
        self._store_error(error_info)
        
        # Send alert if severity is high or critical
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            throttle_key = f"{category.value}:{type(exception).__name__}"
            self.alert_manager.send_alert(error_info, throttle_key)
        
        return error_info
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error with structured format"""
        log_data = {
            'error_id': error_info.error_id,
            'severity': error_info.severity.value,
            'category': error_info.category.value,
            'exception_type': error_info.exception_type,
            'context': asdict(error_info.context)
        }
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(error_info.message, extra=log_data)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(error_info.message, extra=log_data)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(error_info.message, extra=log_data)
        else:
            self.logger.info(error_info.message, extra=log_data)
    
    def _store_error(self, error_info: ErrorInfo):
        """Store error for analysis"""
        self.error_storage.append(error_info)
        
        # Maintain storage limit
        if len(self.error_storage) > self.max_stored_errors:
            self.error_storage = self.error_storage[-self.max_stored_errors//2:]
    
    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for the specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_errors = [e for e in self.error_storage if e.timestamp >= cutoff_time]
        
        stats = {
            'total_errors': len(recent_errors),
            'by_severity': {},
            'by_category': {},
            'by_exception_type': {},
            'resolution_rate': 0.0,
            'average_resolution_time': None
        }
        
        # Count by severity
        for severity in ErrorSeverity:
            stats['by_severity'][severity.value] = len([
                e for e in recent_errors if e.severity == severity
            ])
        
        # Count by category
        for category in ErrorCategory:
            stats['by_category'][category.value] = len([
                e for e in recent_errors if e.category == category
            ])
        
        # Count by exception type
        exception_counts = {}
        for error in recent_errors:
            exception_counts[error.exception_type] = exception_counts.get(error.exception_type, 0) + 1
        stats['by_exception_type'] = exception_counts
        
        # Calculate resolution metrics
        resolved_errors = [e for e in recent_errors if e.resolved]
        if recent_errors:
            stats['resolution_rate'] = len(resolved_errors) / len(recent_errors) * 100
        
        if resolved_errors:
            resolution_times = [
                (e.resolution_time - e.timestamp).total_seconds()
                for e in resolved_errors if e.resolution_time
            ]
            if resolution_times:
                stats['average_resolution_time'] = sum(resolution_times) / len(resolution_times)
        
        return stats

# Retry decorator
def retry_on_error(category: ErrorCategory = ErrorCategory.SYSTEM,
                  severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                  custom_config: Optional[RetryConfig] = None):
    """Decorator for automatic retry with error handling"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get error handler from current app context
            error_handler = getattr(current_app, 'error_handler', None)
            if not error_handler:
                # Fallback to direct execution if no error handler
                return func(*args, **kwargs)
            
            # Get retry config
            retry_config = custom_config or error_handler.retry_configs.get(
                category, RetryConfig()
            )
            
            last_exception = None
            
            for attempt in range(retry_config.max_attempts):
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    # Create error context
                    context = ErrorContext(
                        request_id=getattr(g, 'request_id', None),
                        operation=func.__name__,
                        component=func.__module__,
                        additional_data={'attempt': attempt + 1}
                    )
                    
                    # Handle the error
                    error_info = error_handler.handle_error(e, context, severity, category)
                    error_info.retry_count = attempt + 1
                    
                    # If this is the last attempt, re-raise
                    if attempt == retry_config.max_attempts - 1:
                        break
                    
                    # Wait before retry
                    delay = retry_config.get_delay(attempt)
                    time.sleep(delay)
            
            # Re-raise the last exception
            raise last_exception
        
        return wrapper
    return decorator

# Context manager for error handling
@contextmanager
def error_context(operation: str, component: str = None, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 category: ErrorCategory = ErrorCategory.SYSTEM):
    """Context manager for error handling"""
    try:
        yield
    except Exception as e:
        # Get error handler from current app context
        error_handler = getattr(current_app, 'error_handler', None)
        if error_handler:
            context = ErrorContext(
                request_id=getattr(g, 'request_id', None),
                operation=operation,
                component=component or 'unknown'
            )
            error_handler.handle_error(e, context, severity, category)
        raise

# Global error handler instance
error_handler = None

def init_error_handler(config: Dict[str, Any]):
    """Initialize the global error handler"""
    global error_handler
    error_handler = ErrorHandler(config)
    return error_handler

# Flask error handlers
def register_flask_error_handlers(app):
    """Register Flask error handlers"""
    
    @app.errorhandler(404)
    def handle_404(e):
        if error_handler:
            context = ErrorContext(
                request_id=getattr(g, 'request_id', None),
                operation='page_not_found',
                component='flask'
            )
            error_handler.handle_error(e, context, ErrorSeverity.LOW, ErrorCategory.SYSTEM)
        
        return {'error': 'Resource not found', 'error_code': 'NOT_FOUND'}, 404
    
    @app.errorhandler(500)
    def handle_500(e):
        if error_handler:
            context = ErrorContext(
                request_id=getattr(g, 'request_id', None),
                operation='internal_server_error',
                component='flask'
            )
            error_handler.handle_error(e, context, ErrorSeverity.HIGH, ErrorCategory.SYSTEM)
        
        return {'error': 'Internal server error', 'error_code': 'INTERNAL_ERROR'}, 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        if error_handler:
            context = ErrorContext(
                request_id=getattr(g, 'request_id', None),
                operation='unhandled_exception',
                component='flask'
            )
            error_handler.handle_error(e, context, ErrorSeverity.HIGH, ErrorCategory.SYSTEM)
        
        return {'error': 'An unexpected error occurred', 'error_code': 'UNEXPECTED_ERROR'}, 500

# Request ID middleware
def add_request_id():
    """Add unique request ID to each request"""
    import uuid
    g.request_id = str(uuid.uuid4())

# Health check for error handling system
def get_error_handler_health():
    """Get health status of error handling system"""
    if not error_handler:
        return {'status': 'unhealthy', 'reason': 'Error handler not initialized'}
    
    try:
        # Test basic functionality
        stats = error_handler.get_error_stats(hours=1)
        
        return {
            'status': 'healthy',
            'recent_errors': stats['total_errors'],
            'alert_queue_size': error_handler.alert_manager.alert_queue.qsize(),
            'stored_errors': len(error_handler.error_storage)
        }
    except Exception as e:
        return {'status': 'unhealthy', 'reason': str(e)}