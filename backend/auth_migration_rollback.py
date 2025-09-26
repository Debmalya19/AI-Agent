"""
Authentication Migration Rollback System

This module provides comprehensive rollback functionality for the authentication migration.
It can restore the system to its pre-migration state in case of issues or failures.

Requirements addressed:
- 3.2: Safe migration with rollback capability
- 4.1, 4.2, 4.3: Preserve existing user account data during rollback
"""

import os
import json
import logging
import shutil
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager

from backend.database import SessionLocal as MainSessionLocal
from backend.models import User as LegacyUser, UserSession as LegacyUserSession
from backend.unified_models import UnifiedUser, UnifiedUserSession
from backend.data_validation import ValidationResult

logger = logging.getLogger(__name__)

@dataclass
class RollbackStats:
    """Statistics for rollback operations"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Counts
    unified_users_removed: int = 0
    unified_sessions_removed: int = 0
    legacy_users_restored: int = 0
    legacy_sessions_restored: int = 0
    
    # Status
    success: bool = False
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    def add_error(self, error: str):
        """Add an error to rollback stats"""
        self.errors.append(error)
        logger.error(f"Rollback error: {error}")
    
    def add_warning(self, warning: str):
        """Add a warning to rollback stats"""
        self.warnings.append(warning)
        logger.warning(f"Rollback warning: {warning}")
    
    def start(self):
        """Mark rollback start time"""
        self.start_time = datetime.now(timezone.utc)
    
    def finish(self, success: bool):
        """Mark rollback completion"""
        self.end_time = datetime.now(timezone.utc)
        self.success = success
    
    def duration_seconds(self) -> Optional[float]:
        """Get rollback duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary"""
        return {
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds(),
            'unified_users_removed': self.unified_users_removed,
            'unified_sessions_removed': self.unified_sessions_removed,
            'legacy_users_restored': self.legacy_users_restored,
            'legacy_sessions_restored': self.legacy_sessions_restored,
            'success': self.success,
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
        }

class AuthMigrationRollback:
    """Handles rollback of authentication migration"""
    
    def __init__(self, backup_path: str):
        self.backup_path = Path(backup_path)
        self.stats = RollbackStats()
        
        # Validate backup exists
        if not self.backup_path.exists():
            raise FileNotFoundError(f"Backup directory not found: {backup_path}")
        
        # Load backup metadata
        self.backup_info = self._load_backup_info()
    
    @contextmanager
    def get_session(self):
        """Get database session with transaction management"""
        session = MainSessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def _load_backup_info(self) -> Dict[str, Any]:
        """Load backup metadata"""
        info_file = self.backup_path / 'backup_info.json'
        if not info_file.exists():
            raise FileNotFoundError(f"Backup info file not found: {info_file}")
        
        with open(info_file, 'r') as f:
            return json.load(f)
    
    def validate_backup(self) -> ValidationResult:
        """Validate that backup is complete and usable"""
        result = ValidationResult()
        result.add_info("Validating backup for rollback")
        
        try:
            # Check required files exist
            required_files = ['users.json', 'sessions.json', 'backup_info.json']
            for filename in required_files:
                file_path = self.backup_path / filename
                if not file_path.exists():
                    result.add_error(f"Required backup file missing: {filename}")
            
            # Validate backup data
            if (self.backup_path / 'users.json').exists():
                with open(self.backup_path / 'users.json', 'r') as f:
                    users_data = json.load(f)
                    result.add_info(f"Backup contains {len(users_data)} users")
                    
                    # Validate user data structure
                    for i, user in enumerate(users_data[:5]):  # Check first 5 users
                        required_fields = ['id', 'user_id', 'username', 'email', 'password_hash']
                        for field in required_fields:
                            if field not in user:
                                result.add_error(f"User {i} missing required field: {field}")
            
            if (self.backup_path / 'sessions.json').exists():
                with open(self.backup_path / 'sessions.json', 'r') as f:
                    sessions_data = json.load(f)
                    result.add_info(f"Backup contains {len(sessions_data)} sessions")
            
            # Check backup age
            backup_time = datetime.fromisoformat(self.backup_info['created_at'].replace('Z', '+00:00'))
            age_hours = (datetime.now(timezone.utc) - backup_time).total_seconds() / 3600
            
            if age_hours > 24:
                result.add_warning(f"Backup is {age_hours:.1f} hours old")
            
        except Exception as e:
            result.add_error(f"Backup validation failed: {str(e)}")
        
        return result
    
    def rollback_migration(self, preserve_unified_data: bool = False) -> RollbackStats:
        """
        Rollback the authentication migration
        
        Args:
            preserve_unified_data: If True, backup unified data before removal
        
        Returns:
            RollbackStats: Statistics of the rollback operation
        """
        self.stats.start()
        
        try:
            logger.info("🔄 Starting authentication migration rollback")
            
            # Validate backup before proceeding
            validation_result = self.validate_backup()
            if not validation_result.is_valid:
                raise Exception(f"Backup validation failed: {validation_result.errors}")
            
            # Preserve unified data if requested
            if preserve_unified_data:
                self._preserve_unified_data()
            
            # Remove unified data
            self._remove_unified_data()
            
            # Restore legacy data (if needed)
            self._restore_legacy_data()
            
            # Verify rollback
            self._verify_rollback()
            
            self.stats.finish(True)
            logger.info("✅ Authentication migration rollback completed successfully")
            
        except Exception as e:
            self.stats.add_error(f"Rollback failed: {str(e)}")
            self.stats.finish(False)
            logger.error(f"❌ Rollback failed: {e}")
            raise
        
        return self.stats
    
    def _preserve_unified_data(self):
        """Preserve unified data before rollback"""
        logger.info("💾 Preserving unified data before rollback")
        
        try:
            # Create preservation directory
            preserve_dir = self.backup_path / 'unified_data_preserved'
            preserve_dir.mkdir(exist_ok=True)
            
            with self.get_session() as session:
                # Export unified users
                unified_users = session.query(UnifiedUser).all()
                users_data = []
                for user in unified_users:
                    users_data.append({
                        'id': user.id,
                        'user_id': user.user_id,
                        'username': user.username,
                        'email': user.email,
                        'password_hash': user.password_hash,
                        'full_name': user.full_name,
                        'phone': user.phone,
                        'is_active': user.is_active,
                        'is_admin': user.is_admin,
                        'role': user.role.value if user.role else None,
                        'last_login': user.last_login.isoformat() if user.last_login else None,
                        'created_at': user.created_at.isoformat() if user.created_at else None,
                        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
                        'legacy_customer_id': user.legacy_customer_id,
                        'legacy_admin_user_id': user.legacy_admin_user_id,
                    })
                
                # Export unified sessions
                unified_sessions = session.query(UnifiedUserSession).all()
                sessions_data = []
                for session_obj in unified_sessions:
                    sessions_data.append({
                        'id': session_obj.id,
                        'session_id': session_obj.session_id,
                        'user_id': session_obj.user_id,
                        'token_hash': session_obj.token_hash,
                        'created_at': session_obj.created_at.isoformat() if session_obj.created_at else None,
                        'expires_at': session_obj.expires_at.isoformat() if session_obj.expires_at else None,
                        'last_accessed': session_obj.last_accessed.isoformat() if session_obj.last_accessed else None,
                        'is_active': session_obj.is_active,
                    })
            
            # Save preserved data
            with open(preserve_dir / 'unified_users.json', 'w') as f:
                json.dump(users_data, f, indent=2)
            
            with open(preserve_dir / 'unified_sessions.json', 'w') as f:
                json.dump(sessions_data, f, indent=2)
            
            # Save preservation metadata
            preserve_info = {
                'preserved_at': datetime.now(timezone.utc).isoformat(),
                'users_count': len(users_data),
                'sessions_count': len(sessions_data),
            }
            
            with open(preserve_dir / 'preserve_info.json', 'w') as f:
                json.dump(preserve_info, f, indent=2)
            
            logger.info(f"✅ Preserved {len(users_data)} users and {len(sessions_data)} sessions")
            
        except Exception as e:
            self.stats.add_warning(f"Failed to preserve unified data: {str(e)}")
    
    def _remove_unified_data(self):
        """Remove unified authentication data"""
        logger.info("🗑️ Removing unified authentication data")
        
        try:
            with self.get_session() as session:
                # Remove unified sessions first (foreign key constraint)
                sessions_removed = session.query(UnifiedUserSession).count()
                session.query(UnifiedUserSession).delete()
                self.stats.unified_sessions_removed = sessions_removed
                
                # Remove unified users
                users_removed = session.query(UnifiedUser).count()
                session.query(UnifiedUser).delete()
                self.stats.unified_users_removed = users_removed
                
                logger.info(f"✅ Removed {users_removed} unified users and {sessions_removed} unified sessions")
        
        except Exception as e:
            raise Exception(f"Failed to remove unified data: {str(e)}")
    
    def _restore_legacy_data(self):
        """Restore legacy authentication data from backup"""
        logger.info("📥 Restoring legacy authentication data")
        
        try:
            with self.get_session() as session:
                # Check if legacy data already exists
                existing_users = session.query(LegacyUser).count()
                existing_sessions = session.query(LegacyUserSession).count()
                
                if existing_users > 0 or existing_sessions > 0:
                    self.stats.add_warning(f"Legacy data already exists: {existing_users} users, {existing_sessions} sessions")
                    return
                
                # Restore users from backup
                with open(self.backup_path / 'users.json', 'r') as f:
                    users_data = json.load(f)
                
                for user_data in users_data:
                    try:
                        # Convert datetime strings back to datetime objects
                        created_at = None
                        if user_data.get('created_at'):
                            created_at = datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00'))
                        
                        updated_at = None
                        if user_data.get('updated_at'):
                            updated_at = datetime.fromisoformat(user_data['updated_at'].replace('Z', '+00:00'))
                        
                        legacy_user = LegacyUser(
                            id=user_data['id'],
                            user_id=user_data['user_id'],
                            username=user_data['username'],
                            email=user_data['email'],
                            password_hash=user_data['password_hash'],
                            full_name=user_data.get('full_name'),
                            is_active=user_data.get('is_active', True),
                            is_admin=user_data.get('is_admin', False),
                            created_at=created_at,
                            updated_at=updated_at,
                        )
                        
                        session.add(legacy_user)
                        self.stats.legacy_users_restored += 1
                    
                    except Exception as e:
                        self.stats.add_error(f"Failed to restore user {user_data.get('user_id', 'unknown')}: {str(e)}")
                
                # Restore sessions from backup
                with open(self.backup_path / 'sessions.json', 'r') as f:
                    sessions_data = json.load(f)
                
                for session_data in sessions_data:
                    try:
                        # Convert datetime strings back to datetime objects
                        created_at = None
                        if session_data.get('created_at'):
                            created_at = datetime.fromisoformat(session_data['created_at'].replace('Z', '+00:00'))
                        
                        expires_at = None
                        if session_data.get('expires_at'):
                            expires_at = datetime.fromisoformat(session_data['expires_at'].replace('Z', '+00:00'))
                        
                        last_accessed = None
                        if session_data.get('last_accessed'):
                            last_accessed = datetime.fromisoformat(session_data['last_accessed'].replace('Z', '+00:00'))
                        
                        legacy_session = LegacyUserSession(
                            id=session_data['id'],
                            session_id=session_data['session_id'],
                            user_id=session_data['user_id'],
                            token_hash=session_data['token_hash'],
                            created_at=created_at,
                            expires_at=expires_at,
                            last_accessed=last_accessed,
                            is_active=session_data.get('is_active', True),
                        )
                        
                        session.add(legacy_session)
                        self.stats.legacy_sessions_restored += 1
                    
                    except Exception as e:
                        self.stats.add_error(f"Failed to restore session {session_data.get('session_id', 'unknown')}: {str(e)}")
                
                logger.info(f"✅ Restored {self.stats.legacy_users_restored} users and {self.stats.legacy_sessions_restored} sessions")
        
        except Exception as e:
            raise Exception(f"Failed to restore legacy data: {str(e)}")
    
    def _verify_rollback(self):
        """Verify that rollback was successful"""
        logger.info("🔍 Verifying rollback completion")
        
        try:
            with self.get_session() as session:
                # Check that unified data is gone
                unified_user_count = session.query(UnifiedUser).count()
                unified_session_count = session.query(UnifiedUserSession).count()
                
                if unified_user_count > 0:
                    self.stats.add_error(f"Rollback incomplete: {unified_user_count} unified users still exist")
                
                if unified_session_count > 0:
                    self.stats.add_error(f"Rollback incomplete: {unified_session_count} unified sessions still exist")
                
                # Check that legacy data is restored (if we restored it)
                if self.stats.legacy_users_restored > 0:
                    legacy_user_count = session.query(LegacyUser).count()
                    if legacy_user_count != self.stats.legacy_users_restored:
                        self.stats.add_error(f"Legacy user count mismatch: expected {self.stats.legacy_users_restored}, found {legacy_user_count}")
                
                if self.stats.legacy_sessions_restored > 0:
                    legacy_session_count = session.query(LegacyUserSession).count()
                    if legacy_session_count != self.stats.legacy_sessions_restored:
                        self.stats.add_error(f"Legacy session count mismatch: expected {self.stats.legacy_sessions_restored}, found {legacy_session_count}")
                
                logger.info("✅ Rollback verification completed")
        
        except Exception as e:
            self.stats.add_error(f"Rollback verification failed: {str(e)}")
    
    def create_rollback_report(self) -> str:
        """Create a detailed rollback report"""
        report_path = self.backup_path / 'rollback_report.json'
        
        report_data = {
            'rollback_info': {
                'backup_path': str(self.backup_path),
                'backup_created_at': self.backup_info.get('created_at'),
                'rollback_executed_at': datetime.now(timezone.utc).isoformat(),
            },
            'rollback_stats': self.stats.to_dict(),
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        return str(report_path)

def rollback_auth_migration(backup_path: str, preserve_unified_data: bool = False) -> RollbackStats:
    """
    Convenience function to rollback authentication migration
    
    Args:
        backup_path: Path to the backup directory
        preserve_unified_data: Whether to preserve unified data before rollback
    
    Returns:
        RollbackStats: Statistics of the rollback operation
    """
    rollback_system = AuthMigrationRollback(backup_path)
    return rollback_system.rollback_migration(preserve_unified_data)

def validate_rollback_backup(backup_path: str) -> ValidationResult:
    """
    Validate that a backup is suitable for rollback
    
    Args:
        backup_path: Path to the backup directory
    
    Returns:
        ValidationResult: Validation results
    """
    try:
        rollback_system = AuthMigrationRollback(backup_path)
        return rollback_system.validate_backup()
    except Exception as e:
        result = ValidationResult()
        result.add_error(f"Failed to validate backup: {str(e)}")
        return result

# Export main classes and functions
__all__ = [
    'AuthMigrationRollback',
    'RollbackStats',
    'rollback_auth_migration',
    'validate_rollback_backup',
]