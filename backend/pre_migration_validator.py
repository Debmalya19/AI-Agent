#!/usr/bin/env python3
"""
Pre-Migration Validation System

This module provides comprehensive pre-migration validation to ensure the system
is ready for authentication migration. It checks system state, data integrity,
and identifies potential issues before migration begins.

Requirements addressed:
- 3.2: Proper data migration validation
- 4.1, 4.2, 4.3: Data preservation validation
- 4.4: Migration status tracking
"""

import logging
import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass
import json

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.database import SessionLocal
from backend.models import User as LegacyUser, UserSession as LegacyUserSession
from backend.unified_models import UnifiedUser, UnifiedUserSession
from backend.data_validation import ValidationResult
from backend.auth_migration_validator import AuthMigrationValidator
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

@dataclass
class SystemRequirement:
    """Represents a system requirement for migration"""
    name: str
    description: str
    required: bool
    check_function: str
    error_message: str
    warning_message: Optional[str] = None

@dataclass
class PreMigrationReport:
    """Comprehensive pre-migration validation report"""
    validation_time: datetime
    overall_status: str  # 'ready', 'warning', 'not_ready'
    
    # System checks
    database_connectivity: bool
    disk_space_sufficient: bool
    backup_directory_writable: bool
    
    # Data validation
    legacy_data_valid: bool
    no_data_conflicts: bool
    password_hashes_supported: bool
    
    # Counts
    legacy_users_count: int
    legacy_sessions_count: int
    unified_users_count: int
    unified_sessions_count: int
    
    # Issues
    critical_issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    
    # Detailed results
    validation_results: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary"""
        return {
            'validation_time': self.validation_time.isoformat(),
            'overall_status': self.overall_status,
            'database_connectivity': self.database_connectivity,
            'disk_space_sufficient': self.disk_space_sufficient,
            'backup_directory_writable': self.backup_directory_writable,
            'legacy_data_valid': self.legacy_data_valid,
            'no_data_conflicts': self.no_data_conflicts,
            'password_hashes_supported': self.password_hashes_supported,
            'legacy_users_count': self.legacy_users_count,
            'legacy_sessions_count': self.legacy_sessions_count,
            'unified_users_count': self.unified_users_count,
            'unified_sessions_count': self.unified_sessions_count,
            'critical_issues': self.critical_issues,
            'warnings': self.warnings,
            'recommendations': self.recommendations,
            'validation_results': self.validation_results
        }

class PreMigrationValidator:
    """Comprehensive pre-migration validation system"""
    
    def __init__(self, backup_directory: str = "migration_backups"):
        self.backup_directory = Path(backup_directory)
        self.requirements = self._define_system_requirements()
    
    def _define_system_requirements(self) -> List[SystemRequirement]:
        """Define system requirements for migration"""
        return [
            SystemRequirement(
                name="database_connectivity",
                description="Database connection is working",
                required=True,
                check_function="check_database_connectivity",
                error_message="Cannot connect to database",
                warning_message=None
            ),
            SystemRequirement(
                name="legacy_data_exists",
                description="Legacy user data exists",
                required=True,
                check_function="check_legacy_data_exists",
                error_message="No legacy user data found to migrate",
                warning_message="Very few legacy users found"
            ),
            SystemRequirement(
                name="no_duplicate_users",
                description="No duplicate users in legacy system",
                required=True,
                check_function="check_no_duplicate_users",
                error_message="Duplicate users found in legacy system",
                warning_message="Some duplicate data detected"
            ),
            SystemRequirement(
                name="password_hashes_valid",
                description="All password hashes are in supported format",
                required=False,
                check_function="check_password_hashes_valid",
                error_message="Unsupported password hash formats found",
                warning_message="Some password hashes may need conversion"
            ),
            SystemRequirement(
                name="disk_space_available",
                description="Sufficient disk space for backup",
                required=True,
                check_function="check_disk_space_available",
                error_message="Insufficient disk space for backup",
                warning_message="Disk space is getting low"
            ),
            SystemRequirement(
                name="backup_directory_writable",
                description="Backup directory is writable",
                required=True,
                check_function="check_backup_directory_writable",
                error_message="Cannot write to backup directory",
                warning_message=None
            ),
            SystemRequirement(
                name="no_unified_conflicts",
                description="No conflicts with existing unified data",
                required=True,
                check_function="check_no_unified_conflicts",
                error_message="Conflicts with existing unified data",
                warning_message="Some unified data already exists"
            ),
            SystemRequirement(
                name="session_integrity",
                description="User sessions have valid references",
                required=False,
                check_function="check_session_integrity",
                error_message="Invalid session references found",
                warning_message="Some sessions may be orphaned"
            )
        ]
    
    def validate_system_readiness(self) -> PreMigrationReport:
        """Run comprehensive pre-migration validation"""
        logger.info("🔍 Starting comprehensive pre-migration validation")
        
        validation_time = datetime.now(timezone.utc)
        
        # Initialize report
        report = PreMigrationReport(
            validation_time=validation_time,
            overall_status='ready',
            database_connectivity=False,
            disk_space_sufficient=False,
            backup_directory_writable=False,
            legacy_data_valid=False,
            no_data_conflicts=False,
            password_hashes_supported=False,
            legacy_users_count=0,
            legacy_sessions_count=0,
            unified_users_count=0,
            unified_sessions_count=0,
            critical_issues=[],
            warnings=[],
            recommendations=[],
            validation_results={}
        )
        
        try:
            # Run system requirement checks
            for requirement in self.requirements:
                try:
                    check_method = getattr(self, requirement.check_function)
                    result = check_method()
                    
                    report.validation_results[requirement.name] = result
                    
                    if not result['passed']:
                        if requirement.required:
                            report.critical_issues.append(requirement.error_message)
                            report.overall_status = 'not_ready'
                        else:
                            if requirement.warning_message:
                                report.warnings.append(requirement.warning_message)
                            if report.overall_status == 'ready':
                                report.overall_status = 'warning'
                    
                except Exception as e:
                    error_msg = f"Failed to check {requirement.name}: {str(e)}"
                    report.critical_issues.append(error_msg)
                    report.overall_status = 'not_ready'
                    logger.error(error_msg)
            
            # Run detailed data validation
            data_validation_result = self._run_detailed_data_validation()
            report.validation_results['detailed_data_validation'] = data_validation_result
            
            # Update report fields based on validation results
            self._update_report_from_validation(report)
            
            # Generate recommendations
            self._generate_recommendations(report)
            
            logger.info(f"✅ Pre-migration validation completed with status: {report.overall_status}")
            
        except Exception as e:
            report.critical_issues.append(f"Validation failed: {str(e)}")
            report.overall_status = 'not_ready'
            logger.error(f"Pre-migration validation failed: {e}")
        
        return report
    
    def check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            with SessionLocal() as session:
                session.execute(text("SELECT 1"))
                return {
                    'passed': True,
                    'message': 'Database connection successful',
                    'details': {}
                }
        except Exception as e:
            return {
                'passed': False,
                'message': f'Database connection failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def check_legacy_data_exists(self) -> Dict[str, Any]:
        """Check if legacy data exists"""
        try:
            with SessionLocal() as session:
                user_count = session.query(LegacyUser).count()
                session_count = session.query(LegacyUserSession).count()
                
                if user_count == 0:
                    return {
                        'passed': False,
                        'message': 'No legacy users found',
                        'details': {'user_count': user_count, 'session_count': session_count}
                    }
                elif user_count < 5:
                    return {
                        'passed': True,
                        'message': f'Found {user_count} legacy users (very few)',
                        'details': {'user_count': user_count, 'session_count': session_count},
                        'warning': True
                    }
                else:
                    return {
                        'passed': True,
                        'message': f'Found {user_count} legacy users and {session_count} sessions',
                        'details': {'user_count': user_count, 'session_count': session_count}
                    }
        except Exception as e:
            return {
                'passed': False,
                'message': f'Failed to check legacy data: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def check_no_duplicate_users(self) -> Dict[str, Any]:
        """Check for duplicate users in legacy system"""
        try:
            with SessionLocal() as session:
                # Check duplicate user_ids
                duplicate_user_ids = session.query(
                    LegacyUser.user_id,
                    func.count(LegacyUser.id)
                ).group_by(LegacyUser.user_id).having(func.count(LegacyUser.id) > 1).all()
                
                # Check duplicate emails
                duplicate_emails = session.query(
                    LegacyUser.email,
                    func.count(LegacyUser.id)
                ).group_by(LegacyUser.email).having(func.count(LegacyUser.id) > 1).all()
                
                # Check duplicate usernames
                duplicate_usernames = session.query(
                    LegacyUser.username,
                    func.count(LegacyUser.id)
                ).group_by(LegacyUser.username).having(func.count(LegacyUser.id) > 1).all()
                
                duplicates = {
                    'user_ids': [(uid, count) for uid, count in duplicate_user_ids],
                    'emails': [(email, count) for email, count in duplicate_emails],
                    'usernames': [(username, count) for username, count in duplicate_usernames]
                }
                
                total_duplicates = len(duplicate_user_ids) + len(duplicate_emails) + len(duplicate_usernames)
                
                if total_duplicates == 0:
                    return {
                        'passed': True,
                        'message': 'No duplicate users found',
                        'details': duplicates
                    }
                else:
                    return {
                        'passed': False,
                        'message': f'Found {total_duplicates} types of duplicates',
                        'details': duplicates
                    }
        except Exception as e:
            return {
                'passed': False,
                'message': f'Failed to check duplicates: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def check_password_hashes_valid(self) -> Dict[str, Any]:
        """Check password hash formats"""
        try:
            from backend.auth_migration_system import PasswordHashMigrator, PasswordHashType
            
            migrator = PasswordHashMigrator()
            
            with SessionLocal() as session:
                users = session.query(LegacyUser).all()
                
                hash_types = {
                    'bcrypt': 0,
                    'sha256': 0,
                    'unknown': 0,
                    'missing': 0
                }
                
                for user in users:
                    if not user.password_hash:
                        hash_types['missing'] += 1
                    else:
                        hash_type = migrator.detect_hash_type(user.password_hash)
                        if hash_type == PasswordHashType.BCRYPT:
                            hash_types['bcrypt'] += 1
                        elif hash_type == PasswordHashType.SHA256:
                            hash_types['sha256'] += 1
                        else:
                            hash_types['unknown'] += 1
                
                unsupported = hash_types['unknown'] + hash_types['missing']
                
                if unsupported == 0:
                    return {
                        'passed': True,
                        'message': 'All password hashes are supported',
                        'details': hash_types
                    }
                elif unsupported < len(users) * 0.1:  # Less than 10%
                    return {
                        'passed': True,
                        'message': f'{unsupported} unsupported hashes (acceptable)',
                        'details': hash_types,
                        'warning': True
                    }
                else:
                    return {
                        'passed': False,
                        'message': f'{unsupported} unsupported password hashes',
                        'details': hash_types
                    }
        except Exception as e:
            return {
                'passed': False,
                'message': f'Failed to check password hashes: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def check_disk_space_available(self) -> Dict[str, Any]:
        """Check available disk space for backup"""
        try:
            import shutil
            
            # Get disk usage
            total, used, free = shutil.disk_usage(self.backup_directory.parent)
            
            # Estimate backup size (rough calculation)
            with SessionLocal() as session:
                user_count = session.query(LegacyUser).count()
                session_count = session.query(LegacyUserSession).count()
            
            # Rough estimate: 1KB per user + 0.5KB per session
            estimated_backup_size = (user_count * 1024) + (session_count * 512)
            
            # Require at least 10x the estimated size or 100MB, whichever is larger
            required_space = max(estimated_backup_size * 10, 100 * 1024 * 1024)
            
            details = {
                'total_space': total,
                'used_space': used,
                'free_space': free,
                'estimated_backup_size': estimated_backup_size,
                'required_space': required_space
            }
            
            if free < required_space:
                return {
                    'passed': False,
                    'message': f'Insufficient disk space: {free // (1024*1024)}MB free, {required_space // (1024*1024)}MB required',
                    'details': details
                }
            elif free < required_space * 2:
                return {
                    'passed': True,
                    'message': f'Disk space adequate but limited: {free // (1024*1024)}MB free',
                    'details': details,
                    'warning': True
                }
            else:
                return {
                    'passed': True,
                    'message': f'Sufficient disk space: {free // (1024*1024)}MB free',
                    'details': details
                }
        except Exception as e:
            return {
                'passed': False,
                'message': f'Failed to check disk space: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def check_backup_directory_writable(self) -> Dict[str, Any]:
        """Check if backup directory is writable"""
        try:
            # Create backup directory if it doesn't exist
            self.backup_directory.mkdir(parents=True, exist_ok=True)
            
            # Test write access
            test_file = self.backup_directory / 'test_write.tmp'
            test_file.write_text('test')
            test_file.unlink()
            
            return {
                'passed': True,
                'message': f'Backup directory is writable: {self.backup_directory}',
                'details': {'backup_directory': str(self.backup_directory)}
            }
        except Exception as e:
            return {
                'passed': False,
                'message': f'Cannot write to backup directory: {str(e)}',
                'details': {'backup_directory': str(self.backup_directory), 'error': str(e)}
            }
    
    def check_no_unified_conflicts(self) -> Dict[str, Any]:
        """Check for conflicts with existing unified data"""
        try:
            with SessionLocal() as session:
                unified_user_count = session.query(UnifiedUser).count()
                unified_session_count = session.query(UnifiedUserSession).count()
                
                if unified_user_count == 0 and unified_session_count == 0:
                    return {
                        'passed': True,
                        'message': 'No existing unified data',
                        'details': {'unified_users': unified_user_count, 'unified_sessions': unified_session_count}
                    }
                
                # Check for potential conflicts
                legacy_user_ids = set(uid for uid, in session.query(LegacyUser.user_id).all())
                unified_user_ids = set(uid for uid, in session.query(UnifiedUser.user_id).all())
                
                conflicts = legacy_user_ids.intersection(unified_user_ids)
                
                details = {
                    'unified_users': unified_user_count,
                    'unified_sessions': unified_session_count,
                    'conflicts': list(conflicts)
                }
                
                if conflicts:
                    return {
                        'passed': False,
                        'message': f'Found {len(conflicts)} user ID conflicts',
                        'details': details
                    }
                elif unified_user_count > 0:
                    return {
                        'passed': True,
                        'message': f'Existing unified data but no conflicts: {unified_user_count} users',
                        'details': details,
                        'warning': True
                    }
                else:
                    return {
                        'passed': True,
                        'message': 'No conflicts with unified data',
                        'details': details
                    }
        except Exception as e:
            return {
                'passed': False,
                'message': f'Failed to check unified conflicts: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def check_session_integrity(self) -> Dict[str, Any]:
        """Check session integrity"""
        try:
            with SessionLocal() as session:
                # Count orphaned sessions
                orphaned_sessions = session.query(LegacyUserSession).filter(
                    ~LegacyUserSession.user_id.in_(
                        session.query(LegacyUser.user_id)
                    )
                ).count()
                
                total_sessions = session.query(LegacyUserSession).count()
                
                details = {
                    'total_sessions': total_sessions,
                    'orphaned_sessions': orphaned_sessions
                }
                
                if orphaned_sessions == 0:
                    return {
                        'passed': True,
                        'message': 'All sessions have valid user references',
                        'details': details
                    }
                elif orphaned_sessions < total_sessions * 0.05:  # Less than 5%
                    return {
                        'passed': True,
                        'message': f'{orphaned_sessions} orphaned sessions (acceptable)',
                        'details': details,
                        'warning': True
                    }
                else:
                    return {
                        'passed': False,
                        'message': f'{orphaned_sessions} orphaned sessions found',
                        'details': details
                    }
        except Exception as e:
            return {
                'passed': False,
                'message': f'Failed to check session integrity: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def _run_detailed_data_validation(self) -> Dict[str, Any]:
        """Run detailed data validation using existing validator"""
        try:
            with SessionLocal() as session:
                validator = AuthMigrationValidator(session)
                result = validator.validate_pre_migration()
                
                return {
                    'passed': result.is_valid,
                    'errors': result.errors,
                    'warnings': result.warnings,
                    'info': result.info,
                    'error_count': len(result.errors),
                    'warning_count': len(result.warnings)
                }
        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'errors': [f"Detailed validation failed: {str(e)}"],
                'warnings': [],
                'info': []
            }
    
    def _update_report_from_validation(self, report: PreMigrationReport):
        """Update report fields from validation results"""
        # Update boolean fields
        report.database_connectivity = report.validation_results.get('database_connectivity', {}).get('passed', False)
        report.disk_space_sufficient = report.validation_results.get('disk_space_available', {}).get('passed', False)
        report.backup_directory_writable = report.validation_results.get('backup_directory_writable', {}).get('passed', False)
        report.legacy_data_valid = report.validation_results.get('detailed_data_validation', {}).get('passed', False)
        report.no_data_conflicts = report.validation_results.get('no_unified_conflicts', {}).get('passed', False)
        report.password_hashes_supported = report.validation_results.get('password_hashes_valid', {}).get('passed', False)
        
        # Update counts
        legacy_data = report.validation_results.get('legacy_data_exists', {}).get('details', {})
        report.legacy_users_count = legacy_data.get('user_count', 0)
        report.legacy_sessions_count = legacy_data.get('session_count', 0)
        
        unified_data = report.validation_results.get('no_unified_conflicts', {}).get('details', {})
        report.unified_users_count = unified_data.get('unified_users', 0)
        report.unified_sessions_count = unified_data.get('unified_sessions', 0)
    
    def _generate_recommendations(self, report: PreMigrationReport):
        """Generate recommendations based on validation results"""
        if not report.database_connectivity:
            report.recommendations.append("Fix database connectivity issues before proceeding")
        
        if not report.disk_space_sufficient:
            report.recommendations.append("Free up disk space or use a different backup directory")
        
        if not report.backup_directory_writable:
            report.recommendations.append("Ensure backup directory has write permissions")
        
        if not report.legacy_data_valid:
            report.recommendations.append("Fix data validation issues in legacy system")
        
        if not report.no_data_conflicts:
            report.recommendations.append("Resolve conflicts with existing unified data")
        
        if not report.password_hashes_supported:
            report.recommendations.append("Consider updating unsupported password hashes")
        
        if report.legacy_users_count == 0:
            report.recommendations.append("No users to migrate - migration may not be necessary")
        elif report.legacy_users_count < 5:
            report.recommendations.append("Very few users to migrate - verify this is expected")
        
        if report.unified_users_count > 0:
            report.recommendations.append("Consider backing up existing unified data before migration")
        
        if report.overall_status == 'ready':
            report.recommendations.append("System appears ready for migration")
            report.recommendations.append("Consider running a dry-run migration first")
            report.recommendations.append("Ensure you have a recent database backup")
        elif report.overall_status == 'warning':
            report.recommendations.append("System can proceed with migration but review warnings")
            report.recommendations.append("Consider addressing warnings before proceeding")
        else:
            report.recommendations.append("System is not ready for migration - address critical issues first")
    
    def save_report(self, report: PreMigrationReport, filename: Optional[str] = None) -> Path:
        """Save validation report to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"pre_migration_validation_{timestamp}.json"
        
        report_dir = Path("migration_reports")
        report_dir.mkdir(exist_ok=True)
        report_file = report_dir / filename
        
        with open(report_file, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        logger.info(f"Pre-migration validation report saved to {report_file}")
        return report_file

def main():
    """CLI entry point for pre-migration validation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pre-migration validation tool")
    parser.add_argument('--backup-dir', default='migration_backups', help='Backup directory to check')
    parser.add_argument('--save-report', action='store_true', help='Save validation report to file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Run validation
    validator = PreMigrationValidator(args.backup_dir)
    report = validator.validate_system_readiness()
    
    # Print summary
    print("\n" + "="*60)
    print("PRE-MIGRATION VALIDATION REPORT")
    print("="*60)
    print(f"Overall Status: {report.overall_status.upper()}")
    print(f"Validation Time: {report.validation_time}")
    
    print(f"\nSYSTEM CHECKS:")
    print(f"  Database Connectivity: {'✅' if report.database_connectivity else '❌'}")
    print(f"  Disk Space Sufficient: {'✅' if report.disk_space_sufficient else '❌'}")
    print(f"  Backup Directory Writable: {'✅' if report.backup_directory_writable else '❌'}")
    
    print(f"\nDATA VALIDATION:")
    print(f"  Legacy Data Valid: {'✅' if report.legacy_data_valid else '❌'}")
    print(f"  No Data Conflicts: {'✅' if report.no_data_conflicts else '❌'}")
    print(f"  Password Hashes Supported: {'✅' if report.password_hashes_supported else '❌'}")
    
    print(f"\nDATA COUNTS:")
    print(f"  Legacy Users: {report.legacy_users_count}")
    print(f"  Legacy Sessions: {report.legacy_sessions_count}")
    print(f"  Unified Users: {report.unified_users_count}")
    print(f"  Unified Sessions: {report.unified_sessions_count}")
    
    if report.critical_issues:
        print(f"\nCRITICAL ISSUES:")
        for issue in report.critical_issues:
            print(f"  ❌ {issue}")
    
    if report.warnings:
        print(f"\nWARNINGS:")
        for warning in report.warnings:
            print(f"  ⚠️  {warning}")
    
    if report.recommendations:
        print(f"\nRECOMMENDATIONS:")
        for rec in report.recommendations:
            print(f"  💡 {rec}")
    
    # Save report if requested
    if args.save_report:
        report_file = validator.save_report(report)
        print(f"\nReport saved to: {report_file}")
    
    # Exit with appropriate code
    if report.overall_status == 'not_ready':
        return 1
    elif report.overall_status == 'warning':
        return 2
    else:
        return 0

if __name__ == '__main__':
    sys.exit(main())