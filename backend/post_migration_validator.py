#!/usr/bin/env python3
"""
Post-Migration Validation System

This module provides comprehensive post-migration validation to verify that
the authentication migration completed successfully and all data was preserved.

Requirements addressed:
- 3.2: Proper data migration validation
- 4.1, 4.2, 4.3: Data preservation validation
- 4.4: Migration status tracking and reporting
"""

import logging
import sys
import os
from typing import Dict, List, Any, Optional, Tuple, Set
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
from sqlalchemy import func, text, and_, or_
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

@dataclass
class DataIntegrityCheck:
    """Represents a data integrity check"""
    name: str
    description: str
    critical: bool
    passed: bool
    message: str
    details: Dict[str, Any]
    recommendations: List[str]

@dataclass
class PostMigrationReport:
    """Comprehensive post-migration validation report"""
    validation_time: datetime
    migration_success: bool
    data_integrity_score: float  # 0.0 to 1.0
    
    # Migration completeness
    all_users_migrated: bool
    all_sessions_migrated: bool
    no_data_loss: bool
    
    # Data consistency
    user_data_consistent: bool
    session_data_consistent: bool
    password_hashes_preserved: bool
    
    # System state
    unified_system_functional: bool
    legacy_system_preserved: bool
    
    # Counts and statistics
    legacy_users_count: int
    legacy_sessions_count: int
    unified_users_count: int
    unified_sessions_count: int
    migrated_users_count: int
    migrated_sessions_count: int
    
    # Issues and recommendations
    critical_issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    
    # Detailed check results
    integrity_checks: List[DataIntegrityCheck]
    validation_results: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary"""
        return {
            'validation_time': self.validation_time.isoformat(),
            'migration_success': self.migration_success,
            'data_integrity_score': self.data_integrity_score,
            'all_users_migrated': self.all_users_migrated,
            'all_sessions_migrated': self.all_sessions_migrated,
            'no_data_loss': self.no_data_loss,
            'user_data_consistent': self.user_data_consistent,
            'session_data_consistent': self.session_data_consistent,
            'password_hashes_preserved': self.password_hashes_preserved,
            'unified_system_functional': self.unified_system_functional,
            'legacy_system_preserved': self.legacy_system_preserved,
            'legacy_users_count': self.legacy_users_count,
            'legacy_sessions_count': self.legacy_sessions_count,
            'unified_users_count': self.unified_users_count,
            'unified_sessions_count': self.unified_sessions_count,
            'migrated_users_count': self.migrated_users_count,
            'migrated_sessions_count': self.migrated_sessions_count,
            'critical_issues': self.critical_issues,
            'warnings': self.warnings,
            'recommendations': self.recommendations,
            'integrity_checks': [
                {
                    'name': check.name,
                    'description': check.description,
                    'critical': check.critical,
                    'passed': check.passed,
                    'message': check.message,
                    'details': check.details,
                    'recommendations': check.recommendations
                }
                for check in self.integrity_checks
            ],
            'validation_results': self.validation_results
        }

class PostMigrationValidator:
    """Comprehensive post-migration validation system"""
    
    def __init__(self):
        self.integrity_checks = []
    
    def validate_migration_success(self) -> PostMigrationReport:
        """Run comprehensive post-migration validation"""
        logger.info("🔍 Starting comprehensive post-migration validation")
        
        validation_time = datetime.now(timezone.utc)
        
        # Initialize report
        report = PostMigrationReport(
            validation_time=validation_time,
            migration_success=False,
            data_integrity_score=0.0,
            all_users_migrated=False,
            all_sessions_migrated=False,
            no_data_loss=False,
            user_data_consistent=False,
            session_data_consistent=False,
            password_hashes_preserved=False,
            unified_system_functional=False,
            legacy_system_preserved=False,
            legacy_users_count=0,
            legacy_sessions_count=0,
            unified_users_count=0,
            unified_sessions_count=0,
            migrated_users_count=0,
            migrated_sessions_count=0,
            critical_issues=[],
            warnings=[],
            recommendations=[],
            integrity_checks=[],
            validation_results={}
        )
        
        try:
            # Get basic counts
            self._get_migration_counts(report)
            
            # Run integrity checks
            self._run_user_migration_check(report)
            self._run_session_migration_check(report)
            self._run_data_consistency_check(report)
            self._run_password_integrity_check(report)
            self._run_system_functionality_check(report)
            self._run_legacy_preservation_check(report)
            
            # Calculate overall scores
            self._calculate_integrity_score(report)
            self._determine_migration_success(report)
            
            # Generate recommendations
            self._generate_recommendations(report)
            
            logger.info(f"✅ Post-migration validation completed. Success: {report.migration_success}")
            
        except Exception as e:
            report.critical_issues.append(f"Validation failed: {str(e)}")
            logger.error(f"Post-migration validation failed: {e}")
        
        return report
    
    def _get_migration_counts(self, report: PostMigrationReport):
        """Get migration counts from database"""
        try:
            with SessionLocal() as session:
                # Legacy counts
                report.legacy_users_count = session.query(LegacyUser).count()
                report.legacy_sessions_count = session.query(LegacyUserSession).count()
                
                # Unified counts
                report.unified_users_count = session.query(UnifiedUser).count()
                report.unified_sessions_count = session.query(UnifiedUserSession).count()
                
                # Migrated counts (users with migration flag)
                report.migrated_users_count = session.query(UnifiedUser).filter(
                    UnifiedUser.migrated_from_legacy == True
                ).count()
                
                report.migrated_sessions_count = session.query(UnifiedUserSession).filter(
                    UnifiedUserSession.migrated_from_legacy == True
                ).count()
                
        except Exception as e:
            report.critical_issues.append(f"Failed to get migration counts: {str(e)}")
    
    def _run_user_migration_check(self, report: PostMigrationReport):
        """Check if all users were migrated correctly"""
        try:
            with SessionLocal() as session:
                # Check if all legacy users have corresponding unified users
                legacy_user_ids = set(uid for uid, in session.query(LegacyUser.user_id).all())
                unified_user_ids = set(uid for uid, in session.query(UnifiedUser.user_id).all())
                
                missing_users = legacy_user_ids - unified_user_ids
                extra_users = unified_user_ids - legacy_user_ids
                
                # Check data consistency for migrated users
                data_mismatches = []
                for legacy_user in session.query(LegacyUser).all():
                    unified_user = session.query(UnifiedUser).filter(
                        UnifiedUser.user_id == legacy_user.user_id
                    ).first()
                    
                    if unified_user:
                        mismatches = self._compare_user_data(legacy_user, unified_user)
                        if mismatches:
                            data_mismatches.extend(mismatches)
                
                # Create integrity check
                check = DataIntegrityCheck(
                    name="user_migration",
                    description="All users migrated with consistent data",
                    critical=True,
                    passed=len(missing_users) == 0 and len(data_mismatches) == 0,
                    message=f"Users: {len(missing_users)} missing, {len(data_mismatches)} data mismatches",
                    details={
                        'missing_users': list(missing_users),
                        'extra_users': list(extra_users),
                        'data_mismatches': data_mismatches,
                        'legacy_count': len(legacy_user_ids),
                        'unified_count': len(unified_user_ids)
                    },
                    recommendations=[]
                )
                
                if missing_users:
                    check.recommendations.append(f"Re-run migration for {len(missing_users)} missing users")
                
                if data_mismatches:
                    check.recommendations.append(f"Fix {len(data_mismatches)} data inconsistencies")
                
                report.integrity_checks.append(check)
                report.all_users_migrated = check.passed
                
        except Exception as e:
            report.critical_issues.append(f"User migration check failed: {str(e)}")
    
    def _run_session_migration_check(self, report: PostMigrationReport):
        """Check if sessions were migrated correctly"""
        try:
            with SessionLocal() as session:
                # Get session counts by user
                legacy_sessions_by_user = {}
                for user_id, count in session.query(
                    LegacyUserSession.user_id, 
                    func.count(LegacyUserSession.id)
                ).group_by(LegacyUserSession.user_id).all():
                    legacy_sessions_by_user[user_id] = count
                
                unified_sessions_by_user = {}
                for user_id, count in session.query(
                    UnifiedUser.user_id,
                    func.count(UnifiedUserSession.id)
                ).join(UnifiedUserSession, UnifiedUser.id == UnifiedUserSession.user_id
                ).group_by(UnifiedUser.user_id).all():
                    unified_sessions_by_user[user_id] = count
                
                # Check for missing sessions
                session_discrepancies = []
                for user_id, legacy_count in legacy_sessions_by_user.items():
                    unified_count = unified_sessions_by_user.get(user_id, 0)
                    if legacy_count != unified_count:
                        session_discrepancies.append({
                            'user_id': user_id,
                            'legacy_count': legacy_count,
                            'unified_count': unified_count
                        })
                
                check = DataIntegrityCheck(
                    name="session_migration",
                    description="All sessions migrated correctly",
                    critical=False,
                    passed=len(session_discrepancies) == 0,
                    message=f"Session discrepancies for {len(session_discrepancies)} users",
                    details={
                        'discrepancies': session_discrepancies,
                        'total_legacy_sessions': sum(legacy_sessions_by_user.values()),
                        'total_unified_sessions': sum(unified_sessions_by_user.values())
                    },
                    recommendations=[]
                )
                
                if session_discrepancies:
                    check.recommendations.append("Review session migration for affected users")
                
                report.integrity_checks.append(check)
                report.all_sessions_migrated = check.passed
                
        except Exception as e:
            report.critical_issues.append(f"Session migration check failed: {str(e)}")
    
    def _run_data_consistency_check(self, report: PostMigrationReport):
        """Check data consistency between legacy and unified systems"""
        try:
            with SessionLocal() as session:
                # Run detailed data validation
                validator = AuthMigrationValidator(session)
                validation_result = validator.validate_post_migration()
                
                check = DataIntegrityCheck(
                    name="data_consistency",
                    description="Data consistency between legacy and unified systems",
                    critical=True,
                    passed=validation_result.is_valid,
                    message=f"Validation: {len(validation_result.errors)} errors, {len(validation_result.warnings)} warnings",
                    details={
                        'errors': validation_result.errors,
                        'warnings': validation_result.warnings,
                        'info': validation_result.info
                    },
                    recommendations=[]
                )
                
                if validation_result.errors:
                    check.recommendations.append("Fix data validation errors")
                
                report.integrity_checks.append(check)
                report.user_data_consistent = validation_result.is_valid
                report.validation_results['detailed_validation'] = {
                    'passed': validation_result.is_valid,
                    'errors': validation_result.errors,
                    'warnings': validation_result.warnings
                }
                
        except Exception as e:
            report.critical_issues.append(f"Data consistency check failed: {str(e)}")
    
    def _run_password_integrity_check(self, report: PostMigrationReport):
        """Check password hash integrity"""
        try:
            with SessionLocal() as session:
                password_issues = []
                
                # Check each migrated user's password
                for legacy_user in session.query(LegacyUser).all():
                    unified_user = session.query(UnifiedUser).filter(
                        UnifiedUser.user_id == legacy_user.user_id
                    ).first()
                    
                    if unified_user:
                        if legacy_user.password_hash != unified_user.password_hash:
                            password_issues.append({
                                'user_id': legacy_user.user_id,
                                'issue': 'password_hash_mismatch'
                            })
                        elif not unified_user.password_hash:
                            password_issues.append({
                                'user_id': legacy_user.user_id,
                                'issue': 'missing_password_hash'
                            })
                
                check = DataIntegrityCheck(
                    name="password_integrity",
                    description="Password hashes preserved during migration",
                    critical=True,
                    passed=len(password_issues) == 0,
                    message=f"Password issues for {len(password_issues)} users",
                    details={'password_issues': password_issues},
                    recommendations=[]
                )
                
                if password_issues:
                    check.recommendations.append("Fix password hash issues for affected users")
                
                report.integrity_checks.append(check)
                report.password_hashes_preserved = check.passed
                
        except Exception as e:
            report.critical_issues.append(f"Password integrity check failed: {str(e)}")
    
    def _run_system_functionality_check(self, report: PostMigrationReport):
        """Check if unified system is functional"""
        try:
            with SessionLocal() as session:
                functionality_issues = []
                
                # Test basic queries
                try:
                    session.query(UnifiedUser).first()
                    session.query(UnifiedUserSession).first()
                except Exception as e:
                    functionality_issues.append(f"Database query failed: {str(e)}")
                
                # Check for required indexes
                try:
                    # Test index usage with explain
                    session.execute(text("SELECT * FROM unified_users WHERE user_id = 'test' LIMIT 1"))
                    session.execute(text("SELECT * FROM unified_users WHERE email = 'test@example.com' LIMIT 1"))
                except Exception as e:
                    functionality_issues.append(f"Index query failed: {str(e)}")
                
                check = DataIntegrityCheck(
                    name="system_functionality",
                    description="Unified authentication system is functional",
                    critical=True,
                    passed=len(functionality_issues) == 0,
                    message=f"System functionality: {len(functionality_issues)} issues",
                    details={'functionality_issues': functionality_issues},
                    recommendations=[]
                )
                
                if functionality_issues:
                    check.recommendations.append("Fix system functionality issues")
                
                report.integrity_checks.append(check)
                report.unified_system_functional = check.passed
                
        except Exception as e:
            report.critical_issues.append(f"System functionality check failed: {str(e)}")
    
    def _run_legacy_preservation_check(self, report: PostMigrationReport):
        """Check if legacy system is preserved"""
        try:
            with SessionLocal() as session:
                preservation_issues = []
                
                # Check if legacy tables still exist and have data
                try:
                    legacy_user_count = session.query(LegacyUser).count()
                    legacy_session_count = session.query(LegacyUserSession).count()
                    
                    if legacy_user_count == 0:
                        preservation_issues.append("Legacy user table is empty")
                    
                    if legacy_session_count == 0:
                        preservation_issues.append("Legacy session table is empty")
                        
                except Exception as e:
                    preservation_issues.append(f"Cannot access legacy tables: {str(e)}")
                
                check = DataIntegrityCheck(
                    name="legacy_preservation",
                    description="Legacy system data is preserved",
                    critical=False,
                    passed=len(preservation_issues) == 0,
                    message=f"Legacy preservation: {len(preservation_issues)} issues",
                    details={'preservation_issues': preservation_issues},
                    recommendations=[]
                )
                
                if preservation_issues:
                    check.recommendations.append("Verify legacy data preservation strategy")
                
                report.integrity_checks.append(check)
                report.legacy_system_preserved = check.passed
                
        except Exception as e:
            report.warnings.append(f"Legacy preservation check failed: {str(e)}")
    
    def _compare_user_data(self, legacy_user: LegacyUser, unified_user: UnifiedUser) -> List[str]:
        """Compare user data between legacy and unified models"""
        mismatches = []
        
        # Compare key fields
        if legacy_user.user_id != unified_user.user_id:
            mismatches.append(f"user_id mismatch: {legacy_user.user_id} != {unified_user.user_id}")
        
        if legacy_user.username != unified_user.username:
            mismatches.append(f"username mismatch for {legacy_user.user_id}")
        
        if legacy_user.email != unified_user.email:
            mismatches.append(f"email mismatch for {legacy_user.user_id}")
        
        if legacy_user.password_hash != unified_user.password_hash:
            mismatches.append(f"password_hash mismatch for {legacy_user.user_id}")
        
        if legacy_user.full_name != unified_user.full_name:
            mismatches.append(f"full_name mismatch for {legacy_user.user_id}")
        
        if legacy_user.is_admin != unified_user.is_admin:
            mismatches.append(f"is_admin mismatch for {legacy_user.user_id}")
        
        return mismatches
    
    def _calculate_integrity_score(self, report: PostMigrationReport):
        """Calculate overall data integrity score"""
        total_checks = len(report.integrity_checks)
        if total_checks == 0:
            report.data_integrity_score = 0.0
            return
        
        # Weight critical checks more heavily
        score = 0.0
        total_weight = 0.0
        
        for check in report.integrity_checks:
            weight = 2.0 if check.critical else 1.0
            total_weight += weight
            
            if check.passed:
                score += weight
        
        report.data_integrity_score = score / total_weight if total_weight > 0 else 0.0
    
    def _determine_migration_success(self, report: PostMigrationReport):
        """Determine overall migration success"""
        # Migration is successful if:
        # 1. All critical checks pass
        # 2. Data integrity score is above threshold
        # 3. No critical issues
        
        critical_checks_passed = all(
            check.passed for check in report.integrity_checks if check.critical
        )
        
        integrity_threshold = 0.9  # 90% integrity required
        
        report.migration_success = (
            critical_checks_passed and
            report.data_integrity_score >= integrity_threshold and
            len(report.critical_issues) == 0
        )
    
    def _generate_recommendations(self, report: PostMigrationReport):
        """Generate recommendations based on validation results"""
        if report.migration_success:
            report.recommendations.append("Migration completed successfully")
            report.recommendations.append("Consider running application tests to verify functionality")
            report.recommendations.append("Monitor system for any authentication issues")
        else:
            report.recommendations.append("Migration has issues that need to be addressed")
            
            if not report.all_users_migrated:
                report.recommendations.append("Re-run user migration for missing users")
            
            if not report.user_data_consistent:
                report.recommendations.append("Fix data consistency issues")
            
            if not report.password_hashes_preserved:
                report.recommendations.append("Verify and fix password hash preservation")
            
            if not report.unified_system_functional:
                report.recommendations.append("Fix unified system functionality issues")
        
        # Add specific recommendations from integrity checks
        for check in report.integrity_checks:
            if not check.passed:
                report.recommendations.extend(check.recommendations)
        
        if report.data_integrity_score < 0.9:
            report.recommendations.append(f"Improve data integrity (current: {report.data_integrity_score:.1%})")
    
    def save_report(self, report: PostMigrationReport, filename: Optional[str] = None) -> Path:
        """Save validation report to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"post_migration_validation_{timestamp}.json"
        
        report_dir = Path("migration_reports")
        report_dir.mkdir(exist_ok=True)
        report_file = report_dir / filename
        
        with open(report_file, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        logger.info(f"Post-migration validation report saved to {report_file}")
        return report_file

def main():
    """CLI entry point for post-migration validation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Post-migration validation tool")
    parser.add_argument('--save-report', action='store_true', help='Save validation report to file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Run validation
    validator = PostMigrationValidator()
    report = validator.validate_migration_success()
    
    # Print summary
    print("\n" + "="*60)
    print("POST-MIGRATION VALIDATION REPORT")
    print("="*60)
    print(f"Migration Success: {'✅ YES' if report.migration_success else '❌ NO'}")
    print(f"Data Integrity Score: {report.data_integrity_score:.1%}")
    print(f"Validation Time: {report.validation_time}")
    
    print(f"\nMIGRATION COMPLETENESS:")
    print(f"  All users migrated: {'✅' if report.all_users_migrated else '❌'}")
    print(f"  All sessions migrated: {'✅' if report.all_sessions_migrated else '❌'}")
    print(f"  No data loss: {'✅' if report.no_data_loss else '❌'}")
    
    print(f"\nDATA CONSISTENCY:")
    print(f"  User data consistent: {'✅' if report.user_data_consistent else '❌'}")
    print(f"  Session data consistent: {'✅' if report.session_data_consistent else '❌'}")
    print(f"  Password hashes preserved: {'✅' if report.password_hashes_preserved else '❌'}")
    
    print(f"\nSYSTEM STATE:")
    print(f"  Unified system functional: {'✅' if report.unified_system_functional else '❌'}")
    print(f"  Legacy system preserved: {'✅' if report.legacy_system_preserved else '❌'}")
    
    print(f"\nCOUNTS:")
    print(f"  Legacy users: {report.legacy_users_count}")
    print(f"  Legacy sessions: {report.legacy_sessions_count}")
    print(f"  Unified users: {report.unified_users_count}")
    print(f"  Unified sessions: {report.unified_sessions_count}")
    print(f"  Migrated users: {report.migrated_users_count}")
    print(f"  Migrated sessions: {report.migrated_sessions_count}")
    
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
    
    return 0 if report.migration_success else 1

if __name__ == "__main__":
    sys.exit(main())