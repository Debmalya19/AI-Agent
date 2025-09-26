"""
Authentication Migration Validator

This module provides comprehensive validation for the authentication migration process.
It ensures data integrity, validates password hash formats, and verifies that all
user data migrates correctly without loss.

Requirements addressed:
- 1.3: Consistent authentication method validation
- 3.1: Single user model validation
- 3.2: Proper data migration validation
- 4.1, 4.2, 4.3: Data preservation validation
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from backend.models import User as LegacyUser, UserSession as LegacyUserSession
from backend.unified_models import UnifiedUser, UnifiedUserSession, UserRole
from backend.data_validation import ValidationResult, FieldValidator
from backend.auth_migration_system import PasswordHashMigrator, PasswordHashType

logger = logging.getLogger(__name__)

class AuthMigrationValidator:
    """Validates authentication migration data integrity"""
    
    def __init__(self, session: Session):
        self.session = session
        self.field_validator = FieldValidator()
        self.password_migrator = PasswordHashMigrator()
    
    def validate_pre_migration(self) -> ValidationResult:
        """Validate system state before migration"""
        result = ValidationResult()
        result.add_info("Starting pre-migration validation")
        
        # Validate legacy data
        result.merge(self._validate_legacy_users())
        result.merge(self._validate_legacy_sessions())
        result.merge(self._validate_legacy_data_integrity())
        
        # Check for existing unified data
        result.merge(self._check_existing_unified_data())
        
        result.add_info("Pre-migration validation completed")
        return result
    
    def validate_post_migration(self) -> ValidationResult:
        """Validate system state after migration"""
        result = ValidationResult()
        result.add_info("Starting post-migration validation")
        
        # Validate unified data
        result.merge(self._validate_unified_users())
        result.merge(self._validate_unified_sessions())
        result.merge(self._validate_unified_data_integrity())
        
        # Validate migration completeness
        result.merge(self._validate_migration_completeness())
        
        # Validate data consistency
        result.merge(self._validate_data_consistency())
        
        result.add_info("Post-migration validation completed")
        return result
    
    def validate_migration_integrity(self) -> ValidationResult:
        """Validate that migration preserved data integrity"""
        result = ValidationResult()
        result.add_info("Starting migration integrity validation")
        
        # Compare legacy and unified data
        result.merge(self._compare_user_data())
        result.merge(self._compare_session_data())
        
        # Validate password hash migration
        result.merge(self._validate_password_hash_migration())
        
        # Check for data loss
        result.merge(self._check_data_loss())
        
        result.add_info("Migration integrity validation completed")
        return result
    
    def _validate_legacy_users(self) -> ValidationResult:
        """Validate legacy user data"""
        result = ValidationResult()
        
        try:
            users = self.session.query(LegacyUser).all()
            result.add_info(f"Validating {len(users)} legacy users")
            
            for user in users:
                # Required fields
                if not user.user_id:
                    result.add_error(f"User {user.id} missing user_id", "LegacyUser", user.id)
                elif not self.field_validator.validate_user_id(user.user_id):
                    result.add_error(f"User {user.id} has invalid user_id format", "LegacyUser", user.id)
                
                if not user.username:
                    result.add_error(f"User {user.id} missing username", "LegacyUser", user.id)
                elif not self.field_validator.validate_username(user.username):
                    result.add_error(f"User {user.id} has invalid username format", "LegacyUser", user.id)
                
                if not user.email:
                    result.add_error(f"User {user.id} missing email", "LegacyUser", user.id)
                elif not self.field_validator.validate_email(user.email):
                    result.add_error(f"User {user.id} has invalid email format", "LegacyUser", user.id)
                
                if not user.password_hash:
                    result.add_error(f"User {user.id} missing password_hash", "LegacyUser", user.id)
                else:
                    # Validate password hash format
                    hash_type = self.password_migrator.detect_hash_type(user.password_hash)
                    if hash_type == PasswordHashType.UNKNOWN:
                        result.add_error(f"User {user.id} has unknown password hash format", "LegacyUser", user.id)
                    elif hash_type == PasswordHashType.SHA256:
                        result.add_warning(f"User {user.id} uses SHA256 hash (cannot convert to bcrypt)", "LegacyUser", user.id)
                
                # Optional fields validation
                if user.full_name and len(user.full_name) > 255:
                    result.add_error(f"User {user.id} full_name too long", "LegacyUser", user.id)
                
                # Datetime validation
                if user.created_at and not self.field_validator.validate_datetime(user.created_at):
                    result.add_warning(f"User {user.id} has invalid created_at", "LegacyUser", user.id)
                
                if user.updated_at and not self.field_validator.validate_datetime(user.updated_at):
                    result.add_warning(f"User {user.id} has invalid updated_at", "LegacyUser", user.id)
            
            # Check for duplicates
            self._check_legacy_user_duplicates(result)
            
        except Exception as e:
            result.add_error(f"Failed to validate legacy users: {str(e)}")
        
        return result
    
    def _validate_legacy_sessions(self) -> ValidationResult:
        """Validate legacy session data"""
        result = ValidationResult()
        
        try:
            sessions = self.session.query(LegacyUserSession).all()
            result.add_info(f"Validating {len(sessions)} legacy sessions")
            
            for session_obj in sessions:
                # Required fields
                if not session_obj.session_id:
                    result.add_error(f"Session {session_obj.id} missing session_id", "LegacyUserSession", session_obj.id)
                
                if not session_obj.user_id:
                    result.add_error(f"Session {session_obj.id} missing user_id", "LegacyUserSession", session_obj.id)
                
                if not session_obj.token_hash:
                    result.add_error(f"Session {session_obj.id} missing token_hash", "LegacyUserSession", session_obj.id)
                
                # Datetime validation
                if session_obj.created_at and not self.field_validator.validate_datetime(session_obj.created_at):
                    result.add_warning(f"Session {session_obj.id} has invalid created_at", "LegacyUserSession", session_obj.id)
                
                if session_obj.expires_at and not self.field_validator.validate_datetime(session_obj.expires_at):
                    result.add_error(f"Session {session_obj.id} has invalid expires_at", "LegacyUserSession", session_obj.id)
                
                # Business logic validation
                if session_obj.created_at and session_obj.expires_at and session_obj.expires_at <= session_obj.created_at:
                    result.add_error(f"Session {session_obj.id} expires before creation", "LegacyUserSession", session_obj.id)
                
                # Check if user exists
                user_exists = self.session.query(LegacyUser).filter(
                    LegacyUser.user_id == session_obj.user_id
                ).first() is not None
                
                if not user_exists:
                    result.add_error(f"Session {session_obj.id} references non-existent user {session_obj.user_id}", "LegacyUserSession", session_obj.id)
            
        except Exception as e:
            result.add_error(f"Failed to validate legacy sessions: {str(e)}")
        
        return result
    
    def _validate_legacy_data_integrity(self) -> ValidationResult:
        """Validate legacy data integrity"""
        result = ValidationResult()
        
        try:
            # Check referential integrity
            orphaned_sessions = self.session.query(LegacyUserSession).filter(
                ~LegacyUserSession.user_id.in_(
                    self.session.query(LegacyUser.user_id)
                )
            ).count()
            
            if orphaned_sessions > 0:
                result.add_error(f"Found {orphaned_sessions} orphaned legacy sessions")
            
            # Check for expired but active sessions
            now = datetime.now(timezone.utc)
            expired_active_sessions = self.session.query(LegacyUserSession).filter(
                LegacyUserSession.is_active == True,
                LegacyUserSession.expires_at < now
            ).count()
            
            if expired_active_sessions > 0:
                result.add_warning(f"Found {expired_active_sessions} expired but active sessions")
            
        except Exception as e:
            result.add_error(f"Failed to validate legacy data integrity: {str(e)}")
        
        return result
    
    def _check_existing_unified_data(self) -> ValidationResult:
        """Check for existing unified data that might conflict"""
        result = ValidationResult()
        
        try:
            unified_user_count = self.session.query(UnifiedUser).count()
            unified_session_count = self.session.query(UnifiedUserSession).count()
            
            if unified_user_count > 0:
                result.add_warning(f"Unified user table already contains {unified_user_count} users")
                
                # Check for potential conflicts
                legacy_user_ids = set(user_id for user_id, in self.session.query(LegacyUser.user_id).all())
                unified_user_ids = set(user_id for user_id, in self.session.query(UnifiedUser.user_id).all())
                
                conflicts = legacy_user_ids.intersection(unified_user_ids)
                if conflicts:
                    result.add_error(f"Found {len(conflicts)} user_id conflicts between legacy and unified tables")
            
            if unified_session_count > 0:
                result.add_warning(f"Unified session table already contains {unified_session_count} sessions")
            
        except Exception as e:
            result.add_error(f"Failed to check existing unified data: {str(e)}")
        
        return result
    
    def _validate_unified_users(self) -> ValidationResult:
        """Validate unified user data"""
        result = ValidationResult()
        
        try:
            users = self.session.query(UnifiedUser).all()
            result.add_info(f"Validating {len(users)} unified users")
            
            for user in users:
                # Use existing model validator
                from backend.data_validation import ModelValidator
                model_validator = ModelValidator()
                user_result = model_validator.validate_user(user)
                result.merge(user_result)
                
                # Additional migration-specific validation
                if user.legacy_customer_id is None and user.legacy_admin_user_id is None:
                    result.add_warning(f"User {user.id} has no legacy ID reference", "UnifiedUser", user.id)
            
        except Exception as e:
            result.add_error(f"Failed to validate unified users: {str(e)}")
        
        return result
    
    def _validate_unified_sessions(self) -> ValidationResult:
        """Validate unified session data"""
        result = ValidationResult()
        
        try:
            sessions = self.session.query(UnifiedUserSession).all()
            result.add_info(f"Validating {len(sessions)} unified sessions")
            
            for session_obj in sessions:
                # Required fields
                if not session_obj.session_id:
                    result.add_error(f"Session {session_obj.id} missing session_id", "UnifiedUserSession", session_obj.id)
                
                if not session_obj.user_id:
                    result.add_error(f"Session {session_obj.id} missing user_id", "UnifiedUserSession", session_obj.id)
                
                if not session_obj.token_hash:
                    result.add_error(f"Session {session_obj.id} missing token_hash", "UnifiedUserSession", session_obj.id)
                
                # Check if user exists
                user_exists = self.session.query(UnifiedUser).filter(
                    UnifiedUser.id == session_obj.user_id
                ).first() is not None
                
                if not user_exists:
                    result.add_error(f"Session {session_obj.id} references non-existent user {session_obj.user_id}", "UnifiedUserSession", session_obj.id)
            
        except Exception as e:
            result.add_error(f"Failed to validate unified sessions: {str(e)}")
        
        return result
    
    def _validate_unified_data_integrity(self) -> ValidationResult:
        """Validate unified data integrity"""
        result = ValidationResult()
        
        try:
            # Check referential integrity
            orphaned_sessions = self.session.query(UnifiedUserSession).filter(
                ~UnifiedUserSession.user_id.in_(
                    self.session.query(UnifiedUser.id)
                )
            ).count()
            
            if orphaned_sessions > 0:
                result.add_error(f"Found {orphaned_sessions} orphaned unified sessions")
            
            # Check for duplicates
            duplicate_user_ids = self.session.query(
                UnifiedUser.user_id, 
                func.count(UnifiedUser.id)
            ).group_by(UnifiedUser.user_id).having(func.count(UnifiedUser.id) > 1).all()
            
            for user_id, count in duplicate_user_ids:
                result.add_error(f"Duplicate unified user_id: {user_id} ({count} occurrences)")
            
            duplicate_emails = self.session.query(
                UnifiedUser.email,
                func.count(UnifiedUser.id)
            ).group_by(UnifiedUser.email).having(func.count(UnifiedUser.id) > 1).all()
            
            for email, count in duplicate_emails:
                result.add_error(f"Duplicate unified email: {email} ({count} occurrences)")
            
        except Exception as e:
            result.add_error(f"Failed to validate unified data integrity: {str(e)}")
        
        return result
    
    def _validate_migration_completeness(self) -> ValidationResult:
        """Validate that migration is complete"""
        result = ValidationResult()
        
        try:
            # Count records
            legacy_user_count = self.session.query(LegacyUser).count()
            unified_user_count = self.session.query(UnifiedUser).count()
            
            legacy_session_count = self.session.query(LegacyUserSession).filter(
                LegacyUserSession.is_active == True
            ).count()
            unified_session_count = self.session.query(UnifiedUserSession).filter(
                UnifiedUserSession.is_active == True
            ).count()
            
            result.add_info(f"Legacy users: {legacy_user_count}, Unified users: {unified_user_count}")
            result.add_info(f"Legacy active sessions: {legacy_session_count}, Unified active sessions: {unified_session_count}")
            
            # Check if all users were migrated
            if unified_user_count < legacy_user_count:
                missing_users = legacy_user_count - unified_user_count
                result.add_error(f"Migration incomplete: {missing_users} users not migrated")
            
            # Check for users with legacy IDs
            users_with_legacy_ids = self.session.query(UnifiedUser).filter(
                or_(
                    UnifiedUser.legacy_customer_id.isnot(None),
                    UnifiedUser.legacy_admin_user_id.isnot(None)
                )
            ).count()
            
            result.add_info(f"Users with legacy ID references: {users_with_legacy_ids}")
            
            if users_with_legacy_ids == 0 and unified_user_count > 0:
                result.add_warning("No users have legacy ID references - migration may not have been run")
            
        except Exception as e:
            result.add_error(f"Failed to validate migration completeness: {str(e)}")
        
        return result
    
    def _validate_data_consistency(self) -> ValidationResult:
        """Validate data consistency between legacy and unified systems"""
        result = ValidationResult()
        
        try:
            # Check that all legacy user_ids exist in unified system
            legacy_user_ids = set(user_id for user_id, in self.session.query(LegacyUser.user_id).all())
            unified_user_ids = set(user_id for user_id, in self.session.query(UnifiedUser.user_id).all())
            
            missing_in_unified = legacy_user_ids - unified_user_ids
            if missing_in_unified:
                result.add_error(f"Users missing in unified system: {missing_in_unified}")
            
            extra_in_unified = unified_user_ids - legacy_user_ids
            if extra_in_unified:
                result.add_warning(f"Extra users in unified system: {extra_in_unified}")
            
        except Exception as e:
            result.add_error(f"Failed to validate data consistency: {str(e)}")
        
        return result
    
    def _compare_user_data(self) -> ValidationResult:
        """Compare user data between legacy and unified systems"""
        result = ValidationResult()
        
        try:
            # Get all legacy users
            legacy_users = {user.user_id: user for user in self.session.query(LegacyUser).all()}
            
            # Get all unified users with legacy references
            unified_users = self.session.query(UnifiedUser).filter(
                UnifiedUser.legacy_customer_id.isnot(None)
            ).all()
            
            for unified_user in unified_users:
                legacy_user = legacy_users.get(unified_user.user_id)
                if not legacy_user:
                    result.add_error(f"Unified user {unified_user.user_id} has no corresponding legacy user")
                    continue
                
                # Compare key fields
                if unified_user.username != legacy_user.username:
                    result.add_error(f"Username mismatch for {unified_user.user_id}: {unified_user.username} != {legacy_user.username}")
                
                if unified_user.email != legacy_user.email:
                    result.add_error(f"Email mismatch for {unified_user.user_id}: {unified_user.email} != {legacy_user.email}")
                
                if unified_user.full_name != legacy_user.full_name:
                    result.add_warning(f"Full name mismatch for {unified_user.user_id}: {unified_user.full_name} != {legacy_user.full_name}")
                
                if unified_user.is_active != legacy_user.is_active:
                    result.add_error(f"Active status mismatch for {unified_user.user_id}: {unified_user.is_active} != {legacy_user.is_active}")
                
                if unified_user.is_admin != legacy_user.is_admin:
                    result.add_error(f"Admin status mismatch for {unified_user.user_id}: {unified_user.is_admin} != {legacy_user.is_admin}")
            
        except Exception as e:
            result.add_error(f"Failed to compare user data: {str(e)}")
        
        return result
    
    def _compare_session_data(self) -> ValidationResult:
        """Compare session data between legacy and unified systems"""
        result = ValidationResult()
        
        try:
            # Get active legacy sessions
            legacy_sessions = {
                session.session_id: session 
                for session in self.session.query(LegacyUserSession).filter(
                    LegacyUserSession.is_active == True
                ).all()
            }
            
            # Get unified sessions
            unified_sessions = self.session.query(UnifiedUserSession).all()
            
            for unified_session in unified_sessions:
                legacy_session = legacy_sessions.get(unified_session.session_id)
                if not legacy_session:
                    result.add_warning(f"Unified session {unified_session.session_id} has no corresponding legacy session")
                    continue
                
                # Compare key fields
                if unified_session.token_hash != legacy_session.token_hash:
                    result.add_error(f"Token hash mismatch for session {unified_session.session_id}")
                
                if unified_session.is_active != legacy_session.is_active:
                    result.add_error(f"Active status mismatch for session {unified_session.session_id}")
            
        except Exception as e:
            result.add_error(f"Failed to compare session data: {str(e)}")
        
        return result
    
    def _validate_password_hash_migration(self) -> ValidationResult:
        """Validate password hash migration"""
        result = ValidationResult()
        
        try:
            unified_users = self.session.query(UnifiedUser).all()
            
            bcrypt_count = 0
            sha256_count = 0
            unknown_count = 0
            
            for user in unified_users:
                hash_type = self.password_migrator.detect_hash_type(user.password_hash)
                
                if hash_type == PasswordHashType.BCRYPT:
                    bcrypt_count += 1
                elif hash_type == PasswordHashType.SHA256:
                    sha256_count += 1
                else:
                    unknown_count += 1
                    result.add_error(f"User {user.user_id} has unknown password hash format")
            
            result.add_info(f"Password hash types: bcrypt={bcrypt_count}, sha256={sha256_count}, unknown={unknown_count}")
            
            if unknown_count > 0:
                result.add_error(f"Found {unknown_count} users with unknown password hash formats")
            
        except Exception as e:
            result.add_error(f"Failed to validate password hash migration: {str(e)}")
        
        return result
    
    def _check_data_loss(self) -> ValidationResult:
        """Check for potential data loss during migration"""
        result = ValidationResult()
        
        try:
            # Check for missing users
            legacy_user_count = self.session.query(LegacyUser).count()
            unified_user_count = self.session.query(UnifiedUser).count()
            
            if unified_user_count < legacy_user_count:
                lost_users = legacy_user_count - unified_user_count
                result.add_error(f"Potential data loss: {lost_users} users missing from unified system")
            
            # Check for missing sessions
            legacy_active_sessions = self.session.query(LegacyUserSession).filter(
                LegacyUserSession.is_active == True
            ).count()
            unified_active_sessions = self.session.query(UnifiedUserSession).filter(
                UnifiedUserSession.is_active == True
            ).count()
            
            if unified_active_sessions < legacy_active_sessions:
                lost_sessions = legacy_active_sessions - unified_active_sessions
                result.add_warning(f"Potential session loss: {lost_sessions} active sessions missing from unified system")
            
        except Exception as e:
            result.add_error(f"Failed to check data loss: {str(e)}")
        
        return result
    
    def _check_legacy_user_duplicates(self, result: ValidationResult):
        """Check for duplicate users in legacy system"""
        try:
            # Check duplicate user_ids
            duplicate_user_ids = self.session.query(
                LegacyUser.user_id,
                func.count(LegacyUser.id)
            ).group_by(LegacyUser.user_id).having(func.count(LegacyUser.id) > 1).all()
            
            for user_id, count in duplicate_user_ids:
                result.add_error(f"Duplicate legacy user_id: {user_id} ({count} occurrences)")
            
            # Check duplicate emails
            duplicate_emails = self.session.query(
                LegacyUser.email,
                func.count(LegacyUser.id)
            ).group_by(LegacyUser.email).having(func.count(LegacyUser.id) > 1).all()
            
            for email, count in duplicate_emails:
                result.add_error(f"Duplicate legacy email: {email} ({count} occurrences)")
            
            # Check duplicate usernames
            duplicate_usernames = self.session.query(
                LegacyUser.username,
                func.count(LegacyUser.id)
            ).group_by(LegacyUser.username).having(func.count(LegacyUser.id) > 1).all()
            
            for username, count in duplicate_usernames:
                result.add_error(f"Duplicate legacy username: {username} ({count} occurrences)")
            
        except Exception as e:
            result.add_error(f"Failed to check legacy user duplicates: {str(e)}")

def validate_auth_migration_pre(session: Session) -> ValidationResult:
    """Convenience function for pre-migration validation"""
    validator = AuthMigrationValidator(session)
    return validator.validate_pre_migration()

def validate_auth_migration_post(session: Session) -> ValidationResult:
    """Convenience function for post-migration validation"""
    validator = AuthMigrationValidator(session)
    return validator.validate_post_migration()

def validate_auth_migration_integrity(session: Session) -> ValidationResult:
    """Convenience function for migration integrity validation"""
    validator = AuthMigrationValidator(session)
    return validator.validate_migration_integrity()

# Export main classes and functions
__all__ = [
    'AuthMigrationValidator',
    'validate_auth_migration_pre',
    'validate_auth_migration_post',
    'validate_auth_migration_integrity',
]