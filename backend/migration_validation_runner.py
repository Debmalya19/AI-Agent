#!/usr/bin/env python3
"""
Migration Validation Runner

This module provides a unified interface for running all migration validation
checks including pre-migration, post-migration, and comprehensive validation.

Requirements addressed:
- 3.2: Proper data migration validation
- 4.1, 4.2, 4.3: Data preservation validation
- 4.4: Migration status tracking and reporting
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.pre_migration_validator import PreMigrationValidator, PreMigrationReport
from backend.migration_status_tracker import MigrationStatusTracker, MigrationState
from backend.auth_migration_validator import AuthMigrationValidator
from backend.database import SessionLocal

logger = logging.getLogger(__name__)

@dataclass
class ValidationSuite:
    """Configuration for validation suite"""
    run_pre_migration: bool = True
    run_post_migration: bool = True
    run_integrity_check: bool = True
    save_reports: bool = True
    detailed_output: bool = False
    backup_directory: str = "migration_backups"
    report_directory: str = "migration_reports"

@dataclass
class ComprehensiveValidationResult:
    """Result of comprehensive validation"""
    validation_time: datetime
    overall_success: bool
    
    # Individual validation results
    pre_migration_passed: bool
    post_migration_passed: bool
    integrity_check_passed: bool
    
    # Reports
    pre_migration_report: Optional[PreMigrationReport]
    post_migration_report: Optional[Any]
    integrity_check_result: Optional[Dict[str, Any]]
    
    # Summary
    total_checks: int
    passed_checks: int
    failed_checks: int
    warnings_count: int
    
    # Issues
    critical_issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    
    # File paths
    report_files: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'validation_time': self.validation_time.isoformat(),
            'overall_success': self.overall_success,
            'pre_migration_passed': self.pre_migration_passed,
            'post_migration_passed': self.post_migration_passed,
            'integrity_check_passed': self.integrity_check_passed,
            'total_checks': self.total_checks,
            'passed_checks': self.passed_checks,
            'failed_checks': self.failed_checks,
            'warnings_count': self.warnings_count,
            'critical_issues': self.critical_issues,
            'warnings': self.warnings,
            'recommendations': self.recommendations,
            'report_files': self.report_files,
            'pre_migration_report': self.pre_migration_report.to_dict() if self.pre_migration_report else None,
            'post_migration_report': self.post_migration_report.to_dict() if self.post_migration_report else None,
            'integrity_check_result': self.integrity_check_result
        }

class MigrationValidationRunner:
    """Comprehensive migration validation runner"""
    
    def __init__(self, suite_config: ValidationSuite):
        self.config = suite_config
        self.status_tracker = MigrationStatusTracker()
    
    async def run_comprehensive_validation(self) -> ComprehensiveValidationResult:
        """Run comprehensive migration validation"""
        logger.info("🔍 Starting comprehensive migration validation suite")
        
        validation_time = datetime.now(timezone.utc)
        
        # Initialize result
        result = ComprehensiveValidationResult(
            validation_time=validation_time,
            overall_success=False,
            pre_migration_passed=False,
            post_migration_passed=False,
            integrity_check_passed=False,
            pre_migration_report=None,
            post_migration_report=None,
            integrity_check_result=None,
            total_checks=0,
            passed_checks=0,
            failed_checks=0,
            warnings_count=0,
            critical_issues=[],
            warnings=[],
            recommendations=[],
            report_files=[]
        )
        
        try:
            # Determine which validations to run based on current state
            current_status = self.status_tracker.get_current_status()
            validation_plan = self._create_validation_plan(current_status.migration_state)
            
            logger.info(f"Migration state: {current_status.migration_state.value}")
            logger.info(f"Validation plan: {validation_plan}")
            
            # Run pre-migration validation
            if validation_plan['pre_migration'] and self.config.run_pre_migration:
                logger.info("🔍 Running pre-migration validation...")
                result.pre_migration_report = await self._run_pre_migration_validation()
                result.pre_migration_passed = result.pre_migration_report.overall_status == 'ready'
                result.total_checks += 1
                
                if result.pre_migration_passed:
                    result.passed_checks += 1
                else:
                    result.failed_checks += 1
                    result.critical_issues.extend(result.pre_migration_report.critical_issues)
                
                result.warnings.extend(result.pre_migration_report.warnings)
                result.recommendations.extend(result.pre_migration_report.recommendations)
                result.warnings_count += len(result.pre_migration_report.warnings)
            
            # Run post-migration validation
            if validation_plan['post_migration'] and self.config.run_post_migration:
                logger.info("🔍 Running post-migration validation...")
                result.post_migration_report = await self._run_post_migration_validation()
                result.post_migration_passed = result.post_migration_report.migration_success
                result.total_checks += 1
                
                if result.post_migration_passed:
                    result.passed_checks += 1
                else:
                    result.failed_checks += 1
                    result.critical_issues.extend(result.post_migration_report.critical_issues)
                
                result.warnings.extend(result.post_migration_report.warnings)
                result.recommendations.extend(result.post_migration_report.recommendations)
                result.warnings_count += len(result.post_migration_report.warnings)
            
            # Run integrity check
            if self.config.run_integrity_check:
                logger.info("🔍 Running integrity check...")
                result.integrity_check_result = await self._run_integrity_check()
                result.integrity_check_passed = result.integrity_check_result['passed']
                result.total_checks += 1
                
                if result.integrity_check_passed:
                    result.passed_checks += 1
                else:
                    result.failed_checks += 1
                    result.critical_issues.extend(result.integrity_check_result.get('errors', []))
                
                result.warnings.extend(result.integrity_check_result.get('warnings', []))
                result.warnings_count += len(result.integrity_check_result.get('warnings', []))
            
            # Determine overall success
            result.overall_success = (
                result.failed_checks == 0 and
                len(result.critical_issues) == 0
            )
            
            # Save reports if configured
            if self.config.save_reports:
                await self._save_validation_reports(result)
            
            # Generate final recommendations
            self._generate_final_recommendations(result)
            
            logger.info(f"✅ Comprehensive validation completed. Success: {result.overall_success}")
            
        except Exception as e:
            result.critical_issues.append(f"Validation suite failed: {str(e)}")
            logger.error(f"Comprehensive validation failed: {e}")
        
        return result
    
    def _create_validation_plan(self, migration_state: MigrationState) -> Dict[str, bool]:
        """Create validation plan based on current migration state"""
        plan = {
            'pre_migration': False,
            'post_migration': False,
            'integrity_check': True  # Always run integrity check
        }
        
        if migration_state in [MigrationState.NOT_STARTED, MigrationState.PARTIAL]:
            plan['pre_migration'] = True
        
        if migration_state in [MigrationState.COMPLETED, MigrationState.PARTIAL, MigrationState.FAILED]:
            plan['post_migration'] = True
        
        return plan
    
    async def _run_pre_migration_validation(self) -> PreMigrationReport:
        """Run pre-migration validation"""
        validator = PreMigrationValidator(self.config.backup_directory)
        return validator.validate_system_readiness()
    
    async def _run_post_migration_validation(self):
        """Run post-migration validation"""
        # Import here to avoid circular import issues
        try:
            from backend.post_migration_validator import PostMigrationValidator
            validator = PostMigrationValidator()
            return validator.validate_migration_success()
        except ImportError as e:
            # Fallback if post-migration validator is not available
            logger.warning(f"Post-migration validator not available: {e}")
            return None
    
    async def _run_integrity_check(self) -> Dict[str, Any]:
        """Run integrity check"""
        try:
            with SessionLocal() as session:
                validator = AuthMigrationValidator(session)
                
                # Run all validation types
                pre_result = validator.validate_pre_migration()
                post_result = validator.validate_post_migration()
                integrity_result = validator.validate_migration_integrity()
                
                # Combine results
                all_errors = pre_result.errors + post_result.errors + integrity_result.errors
                all_warnings = pre_result.warnings + post_result.warnings + integrity_result.warnings
                all_info = pre_result.info + post_result.info + integrity_result.info
                
                return {
                    'passed': len(all_errors) == 0,
                    'errors': all_errors,
                    'warnings': all_warnings,
                    'info': all_info,
                    'pre_validation': {
                        'passed': pre_result.is_valid,
                        'errors': pre_result.errors,
                        'warnings': pre_result.warnings
                    },
                    'post_validation': {
                        'passed': post_result.is_valid,
                        'errors': post_result.errors,
                        'warnings': post_result.warnings
                    },
                    'integrity_validation': {
                        'passed': integrity_result.is_valid,
                        'errors': integrity_result.errors,
                        'warnings': integrity_result.warnings
                    }
                }
                
        except Exception as e:
            return {
                'passed': False,
                'errors': [f"Integrity check failed: {str(e)}"],
                'warnings': [],
                'info': []
            }
    
    async def _save_validation_reports(self, result: ComprehensiveValidationResult):
        """Save validation reports to files"""
        report_dir = Path(self.config.report_directory)
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save comprehensive result
        comprehensive_file = report_dir / f"comprehensive_validation_{timestamp}.json"
        with open(comprehensive_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        result.report_files.append(str(comprehensive_file))
        
        # Save individual reports
        if result.pre_migration_report:
            pre_file = report_dir / f"pre_migration_validation_{timestamp}.json"
            with open(pre_file, 'w') as f:
                json.dump(result.pre_migration_report.to_dict(), f, indent=2)
            result.report_files.append(str(pre_file))
        
        if result.post_migration_report:
            post_file = report_dir / f"post_migration_validation_{timestamp}.json"
            with open(post_file, 'w') as f:
                json.dump(result.post_migration_report.to_dict(), f, indent=2)
            result.report_files.append(str(post_file))
        
        if result.integrity_check_result:
            integrity_file = report_dir / f"integrity_check_{timestamp}.json"
            with open(integrity_file, 'w') as f:
                json.dump(result.integrity_check_result, f, indent=2)
            result.report_files.append(str(integrity_file))
        
        logger.info(f"Validation reports saved to {len(result.report_files)} files")
    
    def _generate_final_recommendations(self, result: ComprehensiveValidationResult):
        """Generate final recommendations based on all validation results"""
        if result.overall_success:
            result.recommendations.insert(0, "✅ All validations passed successfully")
            
            # Get current migration state for context
            current_status = self.status_tracker.get_current_status()
            
            if current_status.migration_state == MigrationState.NOT_STARTED:
                result.recommendations.append("System is ready for migration")
                result.recommendations.append("Consider running a dry-run migration first")
            elif current_status.migration_state == MigrationState.COMPLETED:
                result.recommendations.append("Migration appears to be completed successfully")
                result.recommendations.append("Consider running application tests")
            
        else:
            result.recommendations.insert(0, "❌ Validation issues found that need attention")
            
            if result.failed_checks > 0:
                result.recommendations.append(f"Address {result.failed_checks} failed validation checks")
            
            if len(result.critical_issues) > 0:
                result.recommendations.append(f"Fix {len(result.critical_issues)} critical issues")
        
        # Add specific recommendations based on validation types
        if not result.pre_migration_passed and result.pre_migration_report:
            if result.pre_migration_report.overall_status == 'not_ready':
                result.recommendations.append("System is not ready for migration - fix critical issues first")
            elif result.pre_migration_report.overall_status == 'warning':
                result.recommendations.append("System can proceed with migration but review warnings")
        
        if not result.post_migration_passed and result.post_migration_report:
            if result.post_migration_report.data_integrity_score < 0.9:
                score_pct = result.post_migration_report.data_integrity_score * 100
                result.recommendations.append(f"Improve data integrity (current: {score_pct:.1f}%)")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in result.recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        result.recommendations = unique_recommendations

def create_validation_suite_from_args(args) -> ValidationSuite:
    """Create validation suite configuration from command line arguments"""
    return ValidationSuite(
        run_pre_migration=not args.skip_pre,
        run_post_migration=not args.skip_post,
        run_integrity_check=not args.skip_integrity,
        save_reports=not args.no_save,
        detailed_output=args.detailed,
        backup_directory=args.backup_dir,
        report_directory=args.report_dir
    )

async def run_validation_command(args):
    """Run validation command"""
    suite_config = create_validation_suite_from_args(args)
    runner = MigrationValidationRunner(suite_config)
    
    result = await runner.run_comprehensive_validation()
    
    # Print summary
    print("\n" + "="*70)
    print("COMPREHENSIVE MIGRATION VALIDATION RESULTS")
    print("="*70)
    print(f"Overall Success: {'✅ YES' if result.overall_success else '❌ NO'}")
    print(f"Validation Time: {result.validation_time}")
    print(f"Total Checks: {result.total_checks}")
    print(f"Passed: {result.passed_checks}")
    print(f"Failed: {result.failed_checks}")
    print(f"Warnings: {result.warnings_count}")
    
    print(f"\nVALIDATION BREAKDOWN:")
    if suite_config.run_pre_migration:
        status = "✅ PASS" if result.pre_migration_passed else "❌ FAIL"
        print(f"  Pre-migration validation: {status}")
    
    if suite_config.run_post_migration:
        status = "✅ PASS" if result.post_migration_passed else "❌ FAIL"
        print(f"  Post-migration validation: {status}")
    
    if suite_config.run_integrity_check:
        status = "✅ PASS" if result.integrity_check_passed else "❌ FAIL"
        print(f"  Integrity check: {status}")
    
    # Show critical issues
    if result.critical_issues:
        print(f"\nCRITICAL ISSUES:")
        for issue in result.critical_issues[:10]:  # Show first 10
            print(f"  ❌ {issue}")
        if len(result.critical_issues) > 10:
            print(f"  ... and {len(result.critical_issues) - 10} more issues")
    
    # Show warnings if detailed
    if args.detailed and result.warnings:
        print(f"\nWARNINGS:")
        for warning in result.warnings[:10]:  # Show first 10
            print(f"  ⚠️  {warning}")
        if len(result.warnings) > 10:
            print(f"  ... and {len(result.warnings) - 10} more warnings")
    
    # Show recommendations
    if result.recommendations:
        print(f"\nRECOMMENDATIONS:")
        for rec in result.recommendations[:10]:  # Show first 10
            print(f"  💡 {rec}")
        if len(result.recommendations) > 10:
            print(f"  ... and {len(result.recommendations) - 10} more recommendations")
    
    # Show report files
    if result.report_files:
        print(f"\nREPORT FILES:")
        for report_file in result.report_files:
            print(f"  📄 {report_file}")
    
    return 0 if result.overall_success else 1

def main():
    """Main CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Comprehensive Migration Validation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all validations
  python migration_validation_runner.py
  
  # Run only pre-migration validation
  python migration_validation_runner.py --skip-post --skip-integrity
  
  # Run with detailed output and save reports
  python migration_validation_runner.py --detailed
  
  # Run without saving reports
  python migration_validation_runner.py --no-save
        """
    )
    
    parser.add_argument('--skip-pre', action='store_true', help='Skip pre-migration validation')
    parser.add_argument('--skip-post', action='store_true', help='Skip post-migration validation')
    parser.add_argument('--skip-integrity', action='store_true', help='Skip integrity check')
    parser.add_argument('--no-save', action='store_true', help='Do not save validation reports')
    parser.add_argument('--detailed', action='store_true', help='Show detailed output')
    parser.add_argument('--backup-dir', default='migration_backups', help='Backup directory')
    parser.add_argument('--report-dir', default='migration_reports', help='Report directory')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.detailed else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    return asyncio.run(run_validation_command(args))

if __name__ == '__main__':
    sys.exit(main())