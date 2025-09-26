"""
Diagnostic Error Logger
Provides detailed error logging with categorization and debugging information
for admin dashboard login troubleshooting.
"""

import logging
import json
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .database import get_db, Base
from .unified_models import DiagnosticErrorLog

logger = logging.getLogger(__name__)

class ErrorCategory(Enum):
    """Error categories for classification"""
    FRONTEND = "frontend"
    COMMUNICATION = "communication"
    AUTHENTICATION = "authentication"
    SESSION = "session"
    BACKEND = "backend"
    NETWORK = "network"
    BROWSER = "browser"
    SECURITY = "security"
    CONFIGURATION = "configuration"

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorContext:
    """Context information for error logging"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    referer: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    timestamp: Optional[str] = None

@dataclass
class DiagnosticError:
    """Structured diagnostic error information"""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any]
    context: ErrorContext
    error_code: Optional[str] = None
    suggested_actions: List[str] = None
    related_errors: List[str] = None



class DiagnosticErrorLogger:
    """Main diagnostic error logger class"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_patterns = self._initialize_error_patterns()
    
    def _initialize_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize common error patterns and their classifications"""
        return {
            'invalid_credentials': {
                'category': ErrorCategory.AUTHENTICATION,
                'severity': ErrorSeverity.MEDIUM,
                'suggested_actions': [
                    'Verify email and password are correct',
                    'Check if Caps Lock is enabled',
                    'Try using username instead of email',
                    'Contact administrator if account is locked'
                ]
            },
            'user_not_found': {
                'category': ErrorCategory.AUTHENTICATION,
                'severity': ErrorSeverity.MEDIUM,
                'suggested_actions': [
                    'Verify the email/username is correct',
                    'Check if the account exists in the system',
                    'Contact administrator to create account'
                ]
            },
            'network_error': {
                'category': ErrorCategory.NETWORK,
                'severity': ErrorSeverity.HIGH,
                'suggested_actions': [
                    'Check internet connection',
                    'Refresh the page and try again',
                    'Clear browser cache and cookies',
                    'Try a different browser'
                ]
            },
            'session_expired': {
                'category': ErrorCategory.SESSION,
                'severity': ErrorSeverity.LOW,
                'suggested_actions': [
                    'Log in again to create a new session',
                    'Clear browser data if issues persist',
                    'Check if cookies are enabled'
                ]
            },
            'api_endpoint_not_found': {
                'category': ErrorCategory.COMMUNICATION,
                'severity': ErrorSeverity.HIGH,
                'suggested_actions': [
                    'Verify API endpoints are properly registered',
                    'Check server configuration',
                    'Contact system administrator'
                ]
            },
            'database_error': {
                'category': ErrorCategory.BACKEND,
                'severity': ErrorSeverity.CRITICAL,
                'suggested_actions': [
                    'Check database connectivity',
                    'Verify database configuration',
                    'Contact system administrator immediately'
                ]
            },
            'browser_compatibility': {
                'category': ErrorCategory.BROWSER,
                'severity': ErrorSeverity.MEDIUM,
                'suggested_actions': [
                    'Update browser to latest version',
                    'Enable JavaScript and cookies',
                    'Try a different browser',
                    'Clear browser cache and data'
                ]
            }
        }
    
    def log_error(
        self,
        error_type: str,
        message: str,
        details: Dict[str, Any] = None,
        context: ErrorContext = None,
        db: Session = None
    ) -> DiagnosticError:
        """Log a diagnostic error with full context and classification"""
        
        # Get error pattern or use defaults
        pattern = self.error_patterns.get(error_type, {
            'category': ErrorCategory.BACKEND,
            'severity': ErrorSeverity.MEDIUM,
            'suggested_actions': ['Contact system administrator for assistance']
        })
        
        # Create diagnostic error
        diagnostic_error = DiagnosticError(
            category=pattern['category'],
            severity=pattern['severity'],
            message=message,
            details=details or {},
            context=context or ErrorContext(),
            error_code=error_type,
            suggested_actions=pattern.get('suggested_actions', [])
        )
        
        # Log to standard logger
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(diagnostic_error.severity, logging.ERROR)
        
        self.logger.log(
            log_level,
            f"[{diagnostic_error.category.value.upper()}] {message}",
            extra={
                'error_code': error_type,
                'details': details,
                'context': asdict(context) if context else {}
            }
        )
        
        # Store in database if session provided
        if db:
            try:
                self._store_error_in_db(diagnostic_error, db)
            except Exception as e:
                self.logger.error(f"Failed to store error in database: {e}")
        
        return diagnostic_error
    
    def _store_error_in_db(self, error: DiagnosticError, db: Session):
        """Store error in database for persistence and analysis"""
        
        db_error = DiagnosticErrorLog(
            category=error.category.value,
            severity=error.severity.value,
            error_code=error.error_code,
            message=error.message,
            details=json.dumps(error.details) if error.details else None,
            suggested_actions=json.dumps(error.suggested_actions) if error.suggested_actions else None,
            related_errors=json.dumps(error.related_errors) if error.related_errors else None,
            user_id=error.context.user_id,
            session_id=error.context.session_id,
            request_id=error.context.request_id,
            user_agent=error.context.user_agent,
            ip_address=error.context.ip_address,
            referer=error.context.referer,
            endpoint=error.context.endpoint,
            method=error.context.method
        )
        
        db.add(db_error)
        db.commit()
    
    def log_authentication_error(
        self,
        error_type: str,
        username: str = None,
        email: str = None,
        request: Request = None,
        db: Session = None,
        additional_details: Dict[str, Any] = None
    ) -> DiagnosticError:
        """Log authentication-specific errors with enhanced context"""
        
        details = {
            'username': username,
            'email': email,
            **(additional_details or {})
        }
        
        context = ErrorContext()
        if request:
            context = ErrorContext(
                user_agent=request.headers.get('user-agent'),
                ip_address=request.client.host if request.client else None,
                referer=request.headers.get('referer'),
                endpoint=str(request.url.path),
                method=request.method,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        return self.log_error(
            error_type=error_type,
            message=f"Authentication error: {error_type}",
            details=details,
            context=context,
            db=db
        )
    
    def log_session_error(
        self,
        error_type: str,
        session_id: str = None,
        user_id: str = None,
        request: Request = None,
        db: Session = None,
        additional_details: Dict[str, Any] = None
    ) -> DiagnosticError:
        """Log session-specific errors with enhanced context"""
        
        details = {
            'session_id': session_id,
            'user_id': user_id,
            **(additional_details or {})
        }
        
        context = ErrorContext(
            user_id=user_id,
            session_id=session_id
        )
        
        if request:
            context.user_agent = request.headers.get('user-agent')
            context.ip_address = request.client.host if request.client else None
            context.referer = request.headers.get('referer')
            context.endpoint = str(request.url.path)
            context.method = request.method
            context.timestamp = datetime.now(timezone.utc).isoformat()
        
        return self.log_error(
            error_type=error_type,
            message=f"Session error: {error_type}",
            details=details,
            context=context,
            db=db
        )
    
    def log_frontend_error(
        self,
        error_type: str,
        error_message: str,
        stack_trace: str = None,
        user_agent: str = None,
        url: str = None,
        db: Session = None,
        additional_details: Dict[str, Any] = None
    ) -> DiagnosticError:
        """Log frontend JavaScript errors"""
        
        details = {
            'error_message': error_message,
            'stack_trace': stack_trace,
            'url': url,
            **(additional_details or {})
        }
        
        context = ErrorContext(
            user_agent=user_agent,
            referer=url,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        return self.log_error(
            error_type=error_type,
            message=f"Frontend error: {error_message}",
            details=details,
            context=context,
            db=db
        )
    
    def get_recent_errors(
        self,
        db: Session,
        hours: int = 24,
        category: ErrorCategory = None,
        severity: ErrorSeverity = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve recent errors for analysis"""
        
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            query = db.query(DiagnosticErrorLog).filter(
                DiagnosticErrorLog.timestamp > cutoff_time
            )
            
            if category:
                query = query.filter(DiagnosticErrorLog.category == category.value)
            
            if severity:
                query = query.filter(DiagnosticErrorLog.severity == severity.value)
            
            errors = query.order_by(
                DiagnosticErrorLog.timestamp.desc()
            ).limit(limit).all()
            
            return [error.to_dict() for error in errors]
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve recent errors: {e}")
            return []
    
    def get_error_statistics(
        self,
        db: Session,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Count by category
            category_counts = {}
            for category in ErrorCategory:
                count = db.query(DiagnosticErrorLog).filter(
                    DiagnosticErrorLog.timestamp > cutoff_time,
                    DiagnosticErrorLog.category == category.value
                ).count()
                category_counts[category.value] = count
            
            # Count by severity
            severity_counts = {}
            for severity in ErrorSeverity:
                count = db.query(DiagnosticErrorLog).filter(
                    DiagnosticErrorLog.timestamp > cutoff_time,
                    DiagnosticErrorLog.severity == severity.value
                ).count()
                severity_counts[severity.value] = count
            
            # Total count
            total_errors = db.query(DiagnosticErrorLog).filter(
                DiagnosticErrorLog.timestamp > cutoff_time
            ).count()
            
            return {
                'total_errors': total_errors,
                'category_breakdown': category_counts,
                'severity_breakdown': severity_counts,
                'time_period_hours': hours,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get error statistics: {e}")
            return {
                'total_errors': 0,
                'category_breakdown': {},
                'severity_breakdown': {},
                'error': str(e)
            }

# Global instance
diagnostic_logger = DiagnosticErrorLogger()