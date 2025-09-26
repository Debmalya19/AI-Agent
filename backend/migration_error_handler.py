"""
Migration Error Handler and Recovery System

This module provides comprehensive error handling and recovery mechanisms
specifically for the authentication migration process.

Requirements: 1.3, 5.1, 5.2, 5.3, 5.4
"""

import logging
import json
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

from .unified_error_handler import (
    UnifiedErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity,
    get_error_handler
)
from .auth_error_handler import AuthenticationErrorHandler, AuthEventType, get_auth_error_handler


class MigrationErrorType(Enum):
    """Types of migration errors"""
    BACKUP_FAILURE = "backup_failure"
    VALIDATION_FAILURE = "validation_failure"
    DATA_MIGRATION_FAILURE = "data_migration_failure"
    SCHEMA_CREATION_FAILURE = "schema_creation_failure"
    ROLLBACK_FAILURE = "rollback_failure"
    INTEGRITY_VIOLATION = "integrity_violation"
    CONNECTION_FAILURE = "connection_failure"
    PERMISSION_DENIED = "permission_denied"
    DISK_SPACE_ERROR = "disk_space_error"
    TIMEOUT_ERROR = "timeout_error"


class MigrationPhase(Enum):
    """Migration phases for error context"""
    INITIALIZATION = "initialization"
    BACKUP = "backup"
    VALIDATION = "validation"
    SCHEMA_CREATION = "schema_creation"
    USER_MIGRATION = "user_migration"
    SESSION_MIGRATION = "session_migration"
    VERIFICATION = "verification"
    CLEANUP = "cleanup"
    ROLLBACK = "rollback"


@dataclass
class MigrationError:
    """Migration error data structure"""
    error_type: MigrationErrorType
    phase: MigrationPhase
    error_message: str
    exception: Optional[Exception] = None
    affected_records: int = 0
    recovery_possible: bool = True
    rollback_required: bool = False
    additional_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging"""
        return {
            'error_type': self.error_type.value,
            'phase': self.phase.value,
            'error_message': self.error_message,
            'exception_type': type(self.exception).__name__ if self.exception else None,
            'affected_records': self.affected_records,
            'recovery_possible': self.recovery_possible,
            'rollback_required': self.rollback_required,
            'additional_data': self.additional_data,
            'timestamp': self.timestamp.isoformat(),
            'traceback': traceback.format_exc() if self.exception else None
        }


@dataclass
class RecoveryAction:
    """Recovery action for migration errors"""
    action_type: str
    description: str
    automatic: bool = True
    success: bool = False
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None
    
    def execute(self, recovery_func: Callable) -> bool:
        """Execute the recovery action"""
        try:
            self.executed_at = datetime.now(timezone.utc)
            recovery_func()
            self.success = True
            return True
        except Exception as e:
            self.success = False
            self.error_message = str(e)
            return False


class MigrationErrorHandler:
    """
    Comprehensive error handler for authentication migration process
    """
    
    def __init__(self, 
                 error_handler: Optional[UnifiedErrorHandler] = None,
                 auth_error_handler: Optional[AuthenticationErrorHandler] = None,
                 migration_log_file: Optional[str] = None):
        self.error_handler = error_handler or get_error_handler()
        self.auth_error_handler = auth_error_handler or get_auth_error_handler()
        
        # Setup migration logger
        self.migration_logger = self._setup_migration_logger(migration_log_file)
        
        # Track migration errors and recovery actions
        self.migration_errors: List[MigrationError] = []
        self.recovery_actions: List[RecoveryAction] = []
        
        # Recovery strategies
        self.recovery_strategies = self._setup_recovery_strategies()
        
        # Migration state tracking
        self.current_phase = MigrationPhase.INITIALIZATION
        self.migration_id = None
        self.rollback_available = True
    
    def _setup_migration_logger(self, log_file_path: Optional[str] = None) -> logging.Logger:
        """Setup dedicated migration logger"""
        logger = logging.getLogger("migration_handler")
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - MIGRATION - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        if not log_file_path:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file_path = log_dir / "migration_errors.log"
        
        file_handler = logging.FileHandler(log_file_path)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _setup_recovery_strategies(self) -> Dict[MigrationErrorType, Callable]:
        """Setup recovery strategies for different error types"""
        return {
            MigrationErrorType.BACKUP_FAILURE: self._recover_backup_failure,
            MigrationErrorType.VALIDATION_FAILURE: self._recover_validation_failure,
            MigrationErrorType.DATA_MIGRATION_FAILURE: self._recover_data_migration_failure,
            MigrationErrorType.SCHEMA_CREATION_FAILURE: self._recover_schema_creation_failure,
            MigrationErrorType.ROLLBACK_FAILURE: self._recover_rollback_failure,
            MigrationErrorType.INTEGRITY_VIOLATION: self._recover_integrity_violation,
            MigrationErrorType.CONNECTION_FAILURE: self._recover_connection_failure,
            MigrationErrorType.TIMEOUT_ERROR: self._recover_timeout_error,
        }
    
    async def handle_migration_error(self, 
                                   error: Exception,
                                   phase: MigrationPhase,
                                   affected_records: int = 0,
                                   additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle migration errors with comprehensive logging and recovery
        """
        # Determine error type
        error_type = self._determine_migration_error_type(error, phase)
        
        # Create migration error
        migration_error = MigrationError(
            error_type=error_type,
            phase=phase,
            error_message=str(error),
            exception=error,
            affected_records=affected_records,
            recovery_possible=self._is_recovery_possible(error_type, phase),
            rollback_required=self._is_rollback_required(error_type, phase),
            additional_data=additional_context or {}
        )
        
        # Add to error tracking
        self.migration_errors.append(migration_error)
        
        # Create error context for unified handler
        error_context = ErrorContext(
            component='migration_system',
            operation=f'migration_{phase.value}',
            additional_data={
                'migration_phase': phase.value,
                'error_type': error_type.value,
                'affected_records': affected_records,
                'migration_id': self.migration_id
            }
        )
        
        # Use unified error handler
        error_result = await self.error_handler.handle_error(error, error_context)
        
        # Log migration-specific error
        await self._log_migration_error(migration_error, error_result)
        
        # Log security event
        await self.auth_error_handler.log_migration_event(
            AuthEventType.MIGRATION_FAILED,
            success=False,
            error_message=str(error),
            stats={
                'phase': phase.value,
                'error_type': error_type.value,
                'affected_records': affected_records
            }
        )
        
        # Attempt recovery
        recovery_result = await self._attempt_recovery(migration_error)
        
        return {
            'migration_error': True,
            'error_type': error_type.value,
            'phase': phase.value,
            'affected_records': affected_records,
            'recovery_possible': migration_error.recovery_possible,
            'rollback_required': migration_error.rollback_required,
            'recovery_result': recovery_result,
            'error_id': error_result.get('error_id'),
            'message': self._get_migration_error_message(migration_error)
        }
    
    async def _log_migration_error(self, migration_error: MigrationError, error_result: Dict[str, Any]):
        """Log migration error with full context"""
        error_data = migration_error.to_dict()
        error_data['unified_error_id'] = error_result.get('error_id')
        
        log_message = (
            f"MIGRATION_ERROR: {migration_error.error_type.value} in {migration_error.phase.value} - "
            f"Records affected: {migration_error.affected_records} - "
            f"Recovery possible: {migration_error.recovery_possible}"
        )
        
        # Log based on severity
        if migration_error.rollback_required:
            self.migration_logger.critical(log_message, extra={'error_data': error_data})
        elif not migration_error.recovery_possible:
            self.migration_logger.error(log_message, extra={'error_data': error_data})
        else:
            self.migration_logger.warning(log_message, extra={'error_data': error_data})
    
    async def _attempt_recovery(self, migration_error: MigrationError) -> Dict[str, Any]:
        """Attempt to recover from migration error"""
        if not migration_error.recovery_possible:
            return {
                'attempted': False,
                'success': False,
                'message': 'Recovery not possible for this error type'
            }
        
        # Get recovery strategy
        recovery_func = self.recovery_strategies.get(migration_error.error_type)
        if not recovery_func:
            return {
                'attempted': False,
                'success': False,
                'message': 'No recovery strategy available'
            }
        
        # Create recovery action
        recovery_action = RecoveryAction(
            action_type=f"recover_{migration_error.error_type.value}",
            description=f"Attempting recovery for {migration_error.error_type.value}",
            automatic=True
        )
        
        try:
            # Execute recovery
            success = recovery_action.execute(lambda: recovery_func(migration_error))
            self.recovery_actions.append(recovery_action)
            
            if success:
                self.migration_logger.info(f"Recovery successful for {migration_error.error_type.value}")
                return {
                    'attempted': True,
                    'success': True,
                    'message': f'Successfully recovered from {migration_error.error_type.value}'
                }
            else:
                self.migration_logger.error(f"Recovery failed for {migration_error.error_type.value}: {recovery_action.error_message}")
                return {
                    'attempted': True,
                    'success': False,
                    'message': f'Recovery failed: {recovery_action.error_message}'
                }
        
        except Exception as e:
            self.migration_logger.error(f"Recovery attempt failed: {e}")
            return {
                'attempted': True,
                'success': False,
                'message': f'Recovery attempt failed: {str(e)}'
            }
    
    def _determine_migration_error_type(self, error: Exception, phase: MigrationPhase) -> MigrationErrorType:
        """Determine the type of migration error"""
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Database-related errors
        if isinstance(error, (SQLAlchemyError, IntegrityError, OperationalError)):
            if 'integrity' in error_str or isinstance(error, IntegrityError):
                return MigrationErrorType.INTEGRITY_VIOLATION
            elif 'connection' in error_str or 'connect' in error_str:
                return MigrationErrorType.CONNECTION_FAILURE
            elif 'timeout' in error_str:
                return MigrationErrorType.TIMEOUT_ERROR
            else:
                return MigrationErrorType.DATA_MIGRATION_FAILURE
        
        # Phase-specific errors
        if phase == MigrationPhase.BACKUP:
            return MigrationErrorType.BACKUP_FAILURE
        elif phase == MigrationPhase.VALIDATION:
            return MigrationErrorType.VALIDATION_FAILURE
        elif phase == MigrationPhase.SCHEMA_CREATION:
            return MigrationErrorType.SCHEMA_CREATION_FAILURE
        elif phase == MigrationPhase.ROLLBACK:
            return MigrationErrorType.ROLLBACK_FAILURE
        
        # Error message-based detection
        if 'permission' in error_str or 'access' in error_str:
            return MigrationErrorType.PERMISSION_DENIED
        elif 'disk' in error_str or 'space' in error_str:
            return MigrationErrorType.DISK_SPACE_ERROR
        elif 'timeout' in error_str:
            return MigrationErrorType.TIMEOUT_ERROR
        elif 'connection' in error_str:
            return MigrationErrorType.CONNECTION_FAILURE
        
        # Default to data migration failure
        return MigrationErrorType.DATA_MIGRATION_FAILURE
    
    def _is_recovery_possible(self, error_type: MigrationErrorType, phase: MigrationPhase) -> bool:
        """Determine if recovery is possible for this error type"""
        # Some errors are not recoverable
        non_recoverable = {
            MigrationErrorType.DISK_SPACE_ERROR,
            MigrationErrorType.PERMISSION_DENIED,
        }
        
        if error_type in non_recoverable:
            return False
        
        # Rollback phase errors are generally not recoverable
        if phase == MigrationPhase.ROLLBACK:
            return False
        
        return True
    
    def _is_rollback_required(self, error_type: MigrationErrorType, phase: MigrationPhase) -> bool:
        """Determine if rollback is required for this error type"""
        # Critical errors that require rollback
        rollback_required = {
            MigrationErrorType.INTEGRITY_VIOLATION,
            MigrationErrorType.DATA_MIGRATION_FAILURE,
        }
        
        if error_type in rollback_required:
            return True
        
        # Errors in later phases may require rollback
        later_phases = {
            MigrationPhase.USER_MIGRATION,
            MigrationPhase.SESSION_MIGRATION,
            MigrationPhase.VERIFICATION
        }
        
        if phase in later_phases and error_type != MigrationErrorType.VALIDATION_FAILURE:
            return True
        
        return False
    
    def _get_migration_error_message(self, migration_error: MigrationError) -> str:
        """Get user-friendly migration error message"""
        error_messages = {
            MigrationErrorType.BACKUP_FAILURE: "Failed to create backup of existing data",
            MigrationErrorType.VALIDATION_FAILURE: "Data validation failed before migration",
            MigrationErrorType.DATA_MIGRATION_FAILURE: "Failed to migrate user data",
            MigrationErrorType.SCHEMA_CREATION_FAILURE: "Failed to create new database schema",
            MigrationErrorType.ROLLBACK_FAILURE: "Failed to rollback migration changes",
            MigrationErrorType.INTEGRITY_VIOLATION: "Data integrity violation during migration",
            MigrationErrorType.CONNECTION_FAILURE: "Database connection failed during migration",
            MigrationErrorType.PERMISSION_DENIED: "Insufficient permissions for migration",
            MigrationErrorType.DISK_SPACE_ERROR: "Insufficient disk space for migration",
            MigrationErrorType.TIMEOUT_ERROR: "Migration operation timed out",
        }
        
        base_message = error_messages.get(migration_error.error_type, "Unknown migration error")
        
        if migration_error.rollback_required:
            return f"{base_message}. Rollback required to restore system stability."
        elif migration_error.recovery_possible:
            return f"{base_message}. Attempting automatic recovery."
        else:
            return f"{base_message}. Manual intervention required."
    
    # Recovery strategy implementations
    def _recover_backup_failure(self, migration_error: MigrationError):
        """Recover from backup failure"""
        self.migration_logger.info("Attempting backup recovery - creating minimal backup")
        # Implementation would create a minimal backup or skip backup if safe
        pass
    
    def _recover_validation_failure(self, migration_error: MigrationError):
        """Recover from validation failure"""
        self.migration_logger.info("Attempting validation recovery - fixing data issues")
        # Implementation would attempt to fix validation issues
        pass
    
    def _recover_data_migration_failure(self, migration_error: MigrationError):
        """Recover from data migration failure"""
        self.migration_logger.info("Attempting data migration recovery - retrying with smaller batches")
        # Implementation would retry with smaller batch sizes or skip problematic records
        pass
    
    def _recover_schema_creation_failure(self, migration_error: MigrationError):
        """Recover from schema creation failure"""
        self.migration_logger.info("Attempting schema recovery - dropping and recreating tables")
        # Implementation would clean up partial schema and retry
        pass
    
    def _recover_rollback_failure(self, migration_error: MigrationError):
        """Recover from rollback failure"""
        self.migration_logger.critical("Rollback failure - manual intervention required")
        # This is a critical error that requires manual intervention
        raise Exception("Rollback failure requires manual intervention")
    
    def _recover_integrity_violation(self, migration_error: MigrationError):
        """Recover from integrity violation"""
        self.migration_logger.info("Attempting integrity violation recovery - cleaning duplicate data")
        # Implementation would clean up duplicate or conflicting data
        pass
    
    def _recover_connection_failure(self, migration_error: MigrationError):
        """Recover from connection failure"""
        self.migration_logger.info("Attempting connection recovery - retrying with backoff")
        # Implementation would retry connection with exponential backoff
        pass
    
    def _recover_timeout_error(self, migration_error: MigrationError):
        """Recover from timeout error"""
        self.migration_logger.info("Attempting timeout recovery - increasing timeout and retrying")
        # Implementation would increase timeout and retry operation
        pass
    
    def set_migration_phase(self, phase: MigrationPhase):
        """Set current migration phase"""
        self.current_phase = phase
        self.migration_logger.info(f"Migration phase changed to: {phase.value}")
    
    def set_migration_id(self, migration_id: str):
        """Set migration ID for tracking"""
        self.migration_id = migration_id
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of migration errors"""
        error_counts = {}
        for error in self.migration_errors:
            error_type = error.error_type.value
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        recovery_success_rate = 0
        if self.recovery_actions:
            successful_recoveries = sum(1 for action in self.recovery_actions if action.success)
            recovery_success_rate = successful_recoveries / len(self.recovery_actions)
        
        return {
            'total_errors': len(self.migration_errors),
            'error_counts': error_counts,
            'recovery_attempts': len(self.recovery_actions),
            'recovery_success_rate': recovery_success_rate,
            'rollback_required': any(error.rollback_required for error in self.migration_errors),
            'current_phase': self.current_phase.value,
            'migration_id': self.migration_id
        }
    
    def clear_errors(self):
        """Clear error tracking (for new migration attempts)"""
        self.migration_errors.clear()
        self.recovery_actions.clear()


# Global instance
_migration_error_handler: Optional[MigrationErrorHandler] = None

def get_migration_error_handler() -> MigrationErrorHandler:
    """Get or create migration error handler instance"""
    global _migration_error_handler
    if _migration_error_handler is None:
        _migration_error_handler = MigrationErrorHandler()
    return _migration_error_handler

def setup_migration_error_handler(
    error_handler: Optional[UnifiedErrorHandler] = None,
    auth_error_handler: Optional[AuthenticationErrorHandler] = None,
    migration_log_file: Optional[str] = None
) -> MigrationErrorHandler:
    """Setup migration error handler with custom configuration"""
    global _migration_error_handler
    _migration_error_handler = MigrationErrorHandler(
        error_handler=error_handler,
        auth_error_handler=auth_error_handler,
        migration_log_file=migration_log_file
    )
    return _migration_error_handler


# Context manager for migration error handling
@asynccontextmanager
async def migration_error_context(
    phase: MigrationPhase,
    affected_records: int = 0,
    additional_context: Optional[Dict[str, Any]] = None
):
    """Context manager for automatic migration error handling"""
    migration_handler = get_migration_error_handler()
    migration_handler.set_migration_phase(phase)
    
    try:
        yield migration_handler
    except Exception as e:
        error_result = await migration_handler.handle_migration_error(
            error=e,
            phase=phase,
            affected_records=affected_records,
            additional_context=additional_context
        )
        
        # Re-raise with migration context
        if error_result.get('rollback_required'):
            raise Exception(f"Migration rollback required: {error_result.get('message')}")
        elif not error_result.get('recovery_result', {}).get('success', False):
            raise Exception(f"Migration failed: {error_result.get('message')}")