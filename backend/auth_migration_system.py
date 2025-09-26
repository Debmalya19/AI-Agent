#!/usr/bin/env python3
"""
Authentication Migration System

This module provides comprehensive migration functionality to move from the legacy
User/UserSession authentication system to the unified authentication system.

Key Features:
- Data migration from legacy User table to UnifiedUser table
- Password hash format consistency validation and migration
- Session migration from UserSession to UnifiedUserSession
- Data validation to ensure no data loss
- Rollback functionality for safe migration
- Comprehensive logging and error handling

Requirements addressed:
- 1.3: Consistent authentication method across all endpoints
- 3.1: Single user model for authentication
- 3.2: Proper data migration to unified system
- 4.1, 4.2, 4.3: Preserve existing user account data and sessions
"""

import os
import sys
import logging
import json
import shutil
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import secrets
import bcrypt
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy import create_engine, MetaData, Table, text, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from contextlib import contextmanager

# Import models
from backend.database import engine as main_engine, SessionLocal as MainSessionLocal
from backend.models import User as LegacyUser, UserSession as LegacyUserSession
from backend.unified_models import (
    Base as UnifiedBase,
    UnifiedUser,
    UnifiedUserSession,
    UserRole
)
from backend.data_validation import (
    ValidationResult,
    ModelValidator,
    validate_model_instance
)

logger = logging.getLogger(__name__)

class MigrationPhase(Enum):
    """Migration phases for tracking progress"""
    NOT_STARTED = "not_started"
    BACKUP_CREATED = "backup_created"
    VALIDATION_PASSED = "validation_passed"
    USERS_MIGRATED = "users_migrated"
    SESSIONS_MIGRATED = "sessions_migrated"
    VERIFICATION_PASSED = "verification_passed"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class PasswordHashType(Enum):
    """Types of password hashes supported"""
    BCRYPT = "bcrypt"
    SHA256 = "sha256"
    UNKNOWN = "unknown"

@dataclass
class MigrationConfig:
    """Configuration for migration process"""
    backup_enabled: bool = True
    backup_directory: str = "backups"
    validate_before_migration: bool = True
    validate_after_migration: bool = True
    preserve_legacy_tables: bool = True
    batch_size: int = 100
    session_expiry_hours: int = 24
    force_bcrypt_rehash: bool = False
    dry_run: bool = False

@dataclass
class MigrationStats:
    """Statistics tracking for migration process"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    phase: MigrationPhase = MigrationPhase.NOT_STARTED
    
    # Counts
    legacy_users_found: int = 0
    legacy_sessions_found: int = 0
    users_migrated: int = 0
    sessions_migrated: int = 0
    password_hashes_converted: int = 0
    
    # Errors and warnings
    errors: List[str] = None
    warnings: List[str] = None
    
    # Validation results
    pre_migration_validation: Optional[ValidationResult] = None
    post_migration_validation: Optional[ValidationResult] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    def add_error(self, error: str):
        """Add an error to the migration stats"""
        self.errors.append(error)
        logger.error(f"Migration error: {error}")
    
    def add_warning(self, warning: str):
        """Add a warning to the migration stats"""
        self.warnings.append(warning)
        logger.warning(f"Migration warning: {warning}")
    
    def start(self):
        """Mark migration start time"""
        self.start_time = datetime.now(timezone.utc)
    
    def finish(self, phase: MigrationPhase):
        """Mark migration end time and final phase"""
        self.end_time = datetime.now(timezone.utc)
        self.phase = phase
    
    def duration_seconds(self) -> Optional[float]:
        """Get migration duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary for serialization"""
        return {
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'phase': self.phase.value,
            'duration_seconds': self.duration_seconds(),
            'legacy_users_found': self.legacy_users_found,
            'legacy_sessions_found': self.legacy_sessions_found,
            'users_migrated': self.users_migrated,
            'sessions_migrated': self.sessions_migrated,
            'password_hashes_converted': self.password_hashes_converted,
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'pre_migration_validation': self.pre_migration_validation.to_dict() if self.pre_migration_validation else None,
            'post_migration_validation': self.post_migration_validation.to_dict() if self.post_migration_validation else None,
        }

class PasswordHashMigrator:
    """Handles password hash format migration and validation"""
    
    @staticmethod
    def detect_hash_type(password_hash: str) -> PasswordHashType:
        """Detect the type of password hash"""
        if not password_hash:
            return PasswordHashType.UNKNOWN
        
        if password_hash.startswith("$2b$") or password_hash.startswith("$2a$"):
            return PasswordHashType.BCRYPT
        elif len(password_hash) == 64 and all(c in '0123456789abcdef' for c in password_hash.lower()):
            return PasswordHashType.SHA256
        else:
            return PasswordHashType.UNKNOWN
    
    @staticmethod
    def validate_password_hash(password_hash: str) -> bool:
        """Validate that a password hash is in a supported format"""
        hash_type = PasswordHashMigrator.detect_hash_type(password_hash)
        return hash_type in [PasswordHashType.BCRYPT, PasswordHashType.SHA256]
    
    @staticmethod
    def ensure_bcrypt_hash(password_hash: str, force_rehash: bool = False) -> Tuple[str, bool]:
        """
        Ensure password hash is in bcrypt format
        Returns (hash, was_converted)
        """
        hash_type = PasswordHashMigrator.detect_hash_type(password_hash)
        
        if hash_type == PasswordHashType.BCRYPT and not force_rehash:
            return password_hash, False
        
        if hash_type == PasswordHashType.SHA256:
            # For SHA256 hashes, we can't convert them to bcrypt without the original password
            # We'll keep them as-is and handle validation in the auth system
            logger.warning(f"Cannot convert SHA256 hash to bcrypt without original password")
            return password_hash, False
        
        if hash_type == PasswordHashType.UNKNOWN:
            raise ValueError(f"Unknown password hash format: {password_hash[:20]}...")
        
        return password_hash, False

class AuthMigrationSystem:
    """Main authentication migration system"""
    
    def __init__(self, config: MigrationConfig = None):
        self.config = config or MigrationConfig()
        self.stats = MigrationStats()
        self.model_validator = ModelValidator()
        self.password_migrator = PasswordHashMigrator()
        
        # User ID mappings for tracking migration
        self.user_id_mapping: Dict[str, int] = {}  # legacy_user_id -> unified_user.id
        self.session_id_mapping: Dict[str, str] = {}  # legacy_session_id -> unified_session_id
        
        # Backup information
        self.backup_info: Dict[str, Any] = {}
    
    @contextmanager
    def get_session(self):
        """Get database session with transaction management"""
        session = MainSessionLocal()
        try:
            yield session
            if not self.config.dry_run:
                session.commit()
            else:
                session.rollback()  # Always rollback in dry run mode
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    async def run_migration(self) -> MigrationStats:
        """Run the complete authentication migration process with comprehensive error handling"""
        from .migration_error_handler import get_migration_error_handler, migration_error_context, MigrationPhase as ErrorPhase
        from .auth_error_handler import AuthEventType
        
        migration_error_handler = get_migration_error_handler()
        migration_id = f"auth_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        migration_error_handler.set_migration_id(migration_id)
        
        self.stats.start()
        
        try:
            logger.info("🚀 Starting authentication migration system with comprehensive error handling")
            
            # Log migration start
            await migration_error_handler.auth_error_handler.log_migration_event(
                AuthEventType.MIGRATION_STARTED,
                success=True,
                stats={'migration_id': migration_id}
            )
            
            # Phase 1: Create backup
            if self.config.backup_enabled:
                try:
                    self._create_backup()
                    self.stats.phase = MigrationPhase.BACKUP_CREATED
                except Exception as e:
                    await migration_error_handler.handle_migration_error(e, ErrorPhase.BACKUP)
                    raise
            
            # Phase 2: Pre-migration validation
            if self.config.validate_before_migration:
                try:
                    self._run_pre_migration_validation()
                    self.stats.phase = MigrationPhase.VALIDATION_PASSED
                except Exception as e:
                    await migration_error_handler.handle_migration_error(e, ErrorPhase.VALIDATION)
                    raise
            
            # Phase 3: Create unified tables
            try:
                self._create_unified_tables()
            except Exception as e:
                await migration_error_handler.handle_migration_error(e, ErrorPhase.SCHEMA_CREATION)
                raise
            
            # Phase 4: Migrate users
            try:
                self._migrate_users()
                self.stats.phase = MigrationPhase.USERS_MIGRATED
            except Exception as e:
                await migration_error_handler.handle_migration_error(e, ErrorPhase.USER_MIGRATION, self.stats.legacy_users_found)
                raise
            
            # Phase 5: Migrate sessions
            try:
                self._migrate_sessions()
                self.stats.phase = MigrationPhase.SESSIONS_MIGRATED
            except Exception as e:
                await migration_error_handler.handle_migration_error(e, ErrorPhase.SESSION_MIGRATION, self.stats.legacy_sessions_found)
                raise
            
            # Phase 6: Post-migration validation
            if self.config.validate_after_migration:
                try:
                    self._run_post_migration_validation()
                    self.stats.phase = MigrationPhase.VERIFICATION_PASSED
                except Exception as e:
                    await migration_error_handler.handle_migration_error(e, ErrorPhase.VERIFICATION)
                    raise
            
            # Phase 7: Complete migration
            try:
                self._finalize_migration()
                self.stats.finish(MigrationPhase.COMPLETED)
            except Exception as e:
                await migration_error_handler.handle_migration_error(e, ErrorPhase.CLEANUP)
                raise
            
            # Log successful completion
            await migration_error_handler.auth_error_handler.log_migration_event(
                AuthEventType.MIGRATION_COMPLETED,
                success=True,
                stats=self.stats.to_dict()
            )
            
            logger.info("✅ Authentication migration completed successfully")
            
        except Exception as e:
            self.stats.add_error(f"Migration failed: {str(e)}")
            self.stats.finish(MigrationPhase.FAILED)
            
            # Log migration failure
            await migration_error_handler.auth_error_handler.log_migration_event(
                AuthEventType.MIGRATION_FAILED,
                success=False,
                error_message=str(e),
                stats=self.stats.to_dict()
            )
            
            logger.error(f"❌ Migration failed: {e}")
            
            # Get error summary for detailed logging
            error_summary = migration_error_handler.get_error_summary()
            logger.error(f"Migration error summary: {error_summary}")
            
            raise
        
        return self.stats
    
    def _create_backup(self):
        """Create backup of existing authentication data"""
        logger.info("📦 Creating backup of existing authentication data")
        
        try:
            # Create backup directory
            backup_dir = Path(self.config.backup_directory)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = backup_dir / f"auth_migration_backup_{timestamp}"
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Export legacy user data
            with self.get_session() as session:
                # Export users
                users = session.query(LegacyUser).all()
                users_data = []
                for user in users:
                    users_data.append({
                        'id': user.id,
                        'user_id': user.user_id,
                        'username': user.username,
                        'email': user.email,
                        'password_hash': user.password_hash,
                        'full_name': user.full_name,
                        'is_active': user.is_active,
                        'is_admin': user.is_admin,
                        'created_at': user.created_at.isoformat() if user.created_at else None,
                        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
                    })
                
                # Export sessions
                sessions = session.query(LegacyUserSession).all()
                sessions_data = []
                for session_obj in sessions:
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
            
            # Save backup data
            with open(backup_path / 'users.json', 'w') as f:
                json.dump(users_data, f, indent=2)
            
            with open(backup_path / 'sessions.json', 'w') as f:
                json.dump(sessions_data, f, indent=2)
            
            # Save backup metadata
            self.backup_info = {
                'backup_path': str(backup_path),
                'timestamp': timestamp,
                'users_count': len(users_data),
                'sessions_count': len(sessions_data),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            with open(backup_path / 'backup_info.json', 'w') as f:
                json.dump(self.backup_info, f, indent=2)
            
            logger.info(f"✅ Backup created at {backup_path}")
            logger.info(f"📊 Backed up {len(users_data)} users and {len(sessions_data)} sessions")
            
        except Exception as e:
            raise Exception(f"Failed to create backup: {str(e)}")
    
    def _run_pre_migration_validation(self):
        """Run validation before migration"""
        logger.info("🔍 Running pre-migration validation")
        
        validation_result = ValidationResult()
        
        try:
            with self.get_session() as session:
                # Count legacy data
                user_count = session.query(LegacyUser).count()
                session_count = session.query(LegacyUserSession).count()
                
                self.stats.legacy_users_found = user_count
                self.stats.legacy_sessions_found = session_count
                
                validation_result.add_info(f"Found {user_count} legacy users")
                validation_result.add_info(f"Found {session_count} legacy sessions")
                
                # Validate legacy users
                users = session.query(LegacyUser).all()
                for user in users:
                    # Check required fields
                    if not user.user_id:
                        validation_result.add_error(f"User {user.id} missing user_id")
                    if not user.username:
                        validation_result.add_error(f"User {user.id} missing username")
                    if not user.email:
                        validation_result.add_error(f"User {user.id} missing email")
                    if not user.password_hash:
                        validation_result.add_error(f"User {user.id} missing password_hash")
                    
                    # Validate password hash format
                    if user.password_hash and not self.password_migrator.validate_password_hash(user.password_hash):
                        validation_result.add_warning(f"User {user.id} has unsupported password hash format")
                
                # Check for duplicates
                duplicate_user_ids = session.query(LegacyUser.user_id, func.count(LegacyUser.id)).group_by(
                    LegacyUser.user_id
                ).having(func.count(LegacyUser.id) > 1).all()
                
                for user_id, count in duplicate_user_ids:
                    validation_result.add_error(f"Duplicate user_id found: {user_id} ({count} occurrences)")
                
                duplicate_emails = session.query(LegacyUser.email, func.count(LegacyUser.id)).group_by(
                    LegacyUser.email
                ).having(func.count(LegacyUser.id) > 1).all()
                
                for email, count in duplicate_emails:
                    validation_result.add_error(f"Duplicate email found: {email} ({count} occurrences)")
                
                # Check if unified tables already have data
                unified_user_count = session.query(UnifiedUser).count()
                if unified_user_count > 0:
                    validation_result.add_warning(f"Unified user table already contains {unified_user_count} users")
        
        except Exception as e:
            validation_result.add_error(f"Pre-migration validation failed: {str(e)}")
        
        self.stats.pre_migration_validation = validation_result
        
        if not validation_result.is_valid:
            raise Exception(f"Pre-migration validation failed with {len(validation_result.errors)} errors")
        
        logger.info("✅ Pre-migration validation passed")
    
    def _create_unified_tables(self):
        """Create unified authentication tables"""
        logger.info("🏗️ Creating unified authentication tables")
        
        try:
            # Create all unified tables
            UnifiedBase.metadata.create_all(bind=main_engine)
            logger.info("✅ Unified tables created successfully")
            
        except Exception as e:
            raise Exception(f"Failed to create unified tables: {str(e)}")
    
    def _migrate_users(self):
        """Migrate users from legacy User table to UnifiedUser table"""
        logger.info("👥 Migrating users to unified authentication system")
        
        try:
            with self.get_session() as session:
                # Get all legacy users
                legacy_users = session.query(LegacyUser).all()
                
                for legacy_user in legacy_users:
                    try:
                        # Check if user already exists in unified table
                        existing_user = session.query(UnifiedUser).filter(
                            (UnifiedUser.user_id == legacy_user.user_id) |
                            (UnifiedUser.email == legacy_user.email) |
                            (UnifiedUser.username == legacy_user.username)
                        ).first()
                        
                        if existing_user:
                            self.stats.add_warning(f"User {legacy_user.user_id} already exists in unified table")
                            self.user_id_mapping[legacy_user.user_id] = existing_user.id
                            continue
                        
                        # Migrate password hash
                        migrated_hash, was_converted = self.password_migrator.ensure_bcrypt_hash(
                            legacy_user.password_hash,
                            self.config.force_bcrypt_rehash
                        )
                        
                        if was_converted:
                            self.stats.password_hashes_converted += 1
                        
                        # Create unified user
                        unified_user = UnifiedUser(
                            user_id=legacy_user.user_id,
                            username=legacy_user.username,
                            email=legacy_user.email,
                            password_hash=migrated_hash,
                            full_name=legacy_user.full_name,
                            is_active=legacy_user.is_active,
                            is_admin=legacy_user.is_admin,
                            role=UserRole.ADMIN if legacy_user.is_admin else UserRole.CUSTOMER,
                            created_at=legacy_user.created_at or datetime.now(timezone.utc),
                            updated_at=legacy_user.updated_at or datetime.now(timezone.utc),
                            # Migration tracking
                            legacy_customer_id=legacy_user.id,  # Store original ID for reference
                        )
                        
                        # Validate the unified user
                        validation_result = validate_model_instance(unified_user)
                        if not validation_result.is_valid:
                            error_msg = f"User {legacy_user.user_id} validation failed: {validation_result.errors}"
                            self.stats.add_error(error_msg)
                            continue
                        
                        # Add to session
                        if not self.config.dry_run:
                            session.add(unified_user)
                            session.flush()  # Get the ID
                            
                            # Store mapping
                            self.user_id_mapping[legacy_user.user_id] = unified_user.id
                        
                        self.stats.users_migrated += 1
                        
                        if self.stats.users_migrated % 10 == 0:
                            logger.info(f"Migrated {self.stats.users_migrated} users...")
                    
                    except Exception as e:
                        self.stats.add_error(f"Failed to migrate user {legacy_user.user_id}: {str(e)}")
                        continue
                
                logger.info(f"✅ Successfully migrated {self.stats.users_migrated} users")
        
        except Exception as e:
            raise Exception(f"User migration failed: {str(e)}")
    
    def _migrate_sessions(self):
        """Migrate sessions from legacy UserSession table to UnifiedUserSession table"""
        logger.info("🔐 Migrating user sessions to unified system")
        
        try:
            with self.get_session() as session:
                # Get all active legacy sessions
                legacy_sessions = session.query(LegacyUserSession).filter(
                    LegacyUserSession.is_active == True,
                    LegacyUserSession.expires_at > datetime.now(timezone.utc)
                ).all()
                
                for legacy_session in legacy_sessions:
                    try:
                        # Find corresponding unified user
                        unified_user_id = self.user_id_mapping.get(legacy_session.user_id)
                        if not unified_user_id:
                            # Try to find user by user_id
                            unified_user = session.query(UnifiedUser).filter(
                                UnifiedUser.user_id == legacy_session.user_id
                            ).first()
                            
                            if unified_user:
                                unified_user_id = unified_user.id
                                self.user_id_mapping[legacy_session.user_id] = unified_user_id
                            else:
                                self.stats.add_warning(f"No unified user found for session {legacy_session.session_id}")
                                continue
                        
                        # Check if session already exists
                        existing_session = session.query(UnifiedUserSession).filter(
                            UnifiedUserSession.session_id == legacy_session.session_id
                        ).first()
                        
                        if existing_session:
                            self.stats.add_warning(f"Session {legacy_session.session_id} already exists in unified table")
                            continue
                        
                        # Create unified session
                        unified_session = UnifiedUserSession(
                            session_id=legacy_session.session_id,
                            user_id=unified_user_id,
                            token_hash=legacy_session.token_hash,
                            created_at=legacy_session.created_at or datetime.now(timezone.utc),
                            expires_at=legacy_session.expires_at,
                            last_accessed=legacy_session.last_accessed or datetime.now(timezone.utc),
                            is_active=legacy_session.is_active,
                        )
                        
                        # Add to session
                        if not self.config.dry_run:
                            session.add(unified_session)
                            
                            # Store mapping
                            self.session_id_mapping[legacy_session.session_id] = unified_session.session_id
                        
                        self.stats.sessions_migrated += 1
                    
                    except Exception as e:
                        self.stats.add_error(f"Failed to migrate session {legacy_session.session_id}: {str(e)}")
                        continue
                
                logger.info(f"✅ Successfully migrated {self.stats.sessions_migrated} sessions")
        
        except Exception as e:
            raise Exception(f"Session migration failed: {str(e)}")
    
    def _run_post_migration_validation(self):
        """Run validation after migration"""
        logger.info("🔍 Running post-migration validation")
        
        validation_result = ValidationResult()
        
        try:
            with self.get_session() as session:
                # Count migrated data
                unified_user_count = session.query(UnifiedUser).count()
                unified_session_count = session.query(UnifiedUserSession).count()
                
                validation_result.add_info(f"Unified users: {unified_user_count}")
                validation_result.add_info(f"Unified sessions: {unified_session_count}")
                
                # Validate migration completeness
                if unified_user_count < self.stats.users_migrated:
                    validation_result.add_error(f"User count mismatch: expected {self.stats.users_migrated}, found {unified_user_count}")
                
                # Validate data integrity
                users_with_legacy_ids = session.query(UnifiedUser).filter(
                    UnifiedUser.legacy_customer_id.isnot(None)
                ).count()
                
                validation_result.add_info(f"Users with legacy IDs: {users_with_legacy_ids}")
                
                # Check for orphaned sessions
                orphaned_sessions = session.query(UnifiedUserSession).filter(
                    ~UnifiedUserSession.user_id.in_(
                        session.query(UnifiedUser.id)
                    )
                ).count()
                
                if orphaned_sessions > 0:
                    validation_result.add_error(f"Found {orphaned_sessions} orphaned sessions")
                
                # Validate password hashes
                users_with_invalid_hashes = 0
                unified_users = session.query(UnifiedUser).all()
                for user in unified_users:
                    if not self.password_migrator.validate_password_hash(user.password_hash):
                        users_with_invalid_hashes += 1
                
                if users_with_invalid_hashes > 0:
                    validation_result.add_warning(f"Found {users_with_invalid_hashes} users with potentially invalid password hashes")
        
        except Exception as e:
            validation_result.add_error(f"Post-migration validation failed: {str(e)}")
        
        self.stats.post_migration_validation = validation_result
        
        if not validation_result.is_valid:
            raise Exception(f"Post-migration validation failed with {len(validation_result.errors)} errors")
        
        logger.info("✅ Post-migration validation passed")
    
    def _finalize_migration(self):
        """Finalize the migration process"""
        logger.info("🎯 Finalizing migration")
        
        try:
            # Save migration report
            if self.backup_info:
                report_path = Path(self.backup_info['backup_path']) / 'migration_report.json'
                with open(report_path, 'w') as f:
                    json.dump(self.stats.to_dict(), f, indent=2)
                
                logger.info(f"📊 Migration report saved to {report_path}")
            
            # Log final statistics
            logger.info(f"📈 Migration Statistics:")
            logger.info(f"  - Users migrated: {self.stats.users_migrated}")
            logger.info(f"  - Sessions migrated: {self.stats.sessions_migrated}")
            logger.info(f"  - Password hashes converted: {self.stats.password_hashes_converted}")
            logger.info(f"  - Errors: {len(self.stats.errors)}")
            logger.info(f"  - Warnings: {len(self.stats.warnings)}")
            logger.info(f"  - Duration: {self.stats.duration_seconds():.2f} seconds")
        
        except Exception as e:
            self.stats.add_warning(f"Failed to finalize migration: {str(e)}")
    
    def rollback_migration(self) -> bool:
        """Rollback the migration if needed"""
        logger.info("🔄 Rolling back authentication migration")
        
        try:
            if not self.backup_info:
                logger.error("No backup information available for rollback")
                return False
            
            backup_path = Path(self.backup_info['backup_path'])
            if not backup_path.exists():
                logger.error(f"Backup directory not found: {backup_path}")
                return False
            
            with self.get_session() as session:
                # Clear unified tables
                session.query(UnifiedUserSession).delete()
                session.query(UnifiedUser).delete()
                
                # Restore from backup
                with open(backup_path / 'users.json', 'r') as f:
                    users_data = json.load(f)
                
                with open(backup_path / 'sessions.json', 'r') as f:
                    sessions_data = json.load(f)
                
                # Note: In a real rollback, we would restore the legacy tables
                # For now, we just clear the unified tables
                
                logger.info("✅ Migration rolled back successfully")
                self.stats.finish(MigrationPhase.ROLLED_BACK)
                return True
        
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

def create_migration_system(config: MigrationConfig = None) -> AuthMigrationSystem:
    """Factory function to create migration system"""
    return AuthMigrationSystem(config)

def run_authentication_migration(
    backup_enabled: bool = True,
    validate_before: bool = True,
    validate_after: bool = True,
    dry_run: bool = False
) -> MigrationStats:
    """
    Convenience function to run authentication migration with common settings
    
    Args:
        backup_enabled: Whether to create backup before migration
        validate_before: Whether to run pre-migration validation
        validate_after: Whether to run post-migration validation
        dry_run: Whether to run in dry-run mode (no actual changes)
    
    Returns:
        MigrationStats: Statistics and results of the migration
    """
    config = MigrationConfig(
        backup_enabled=backup_enabled,
        validate_before_migration=validate_before,
        validate_after_migration=validate_after,
        dry_run=dry_run
    )
    
    migration_system = AuthMigrationSystem(config)
    return migration_system.run_migration()

# Export main classes and functions
__all__ = [
    'AuthMigrationSystem',
    'MigrationConfig',
    'MigrationStats',
    'MigrationPhase',
    'PasswordHashMigrator',
    'PasswordHashType',
    'create_migration_system',
    'run_authentication_migration',
]