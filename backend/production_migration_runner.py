#!/usr/bin/env python3
"""
Production Migration Runner

This is the main production-ready script for executing authentication migration
with comprehensive validation, status tracking, and reporting functionality.

This script serves as the primary entry point for production migration execution
and integrates all migration components.

Requirements addressed:
- 3.2: Proper data migration to unified system
- 4.1, 4.2, 4.3: Data preservation during migration
- 4.4: Migration status tracking and reporting

Usage:
    python production_migration_runner.py --help
    python production_migration_runner.py execute --validate-all
    python production_migration_runner.py status --detailed
    python production_migration_runner.py validate --comprehensive
"""

import argparse
import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.migration_execution_script import (
    ProductionMigrationExecutor,
    MigrationExecutionConfig,
    execute_migration_command,
    show_migration_status,
    validate_migration_command
)
from backend.migration_validation_runner import (
    MigrationValidationRunner,
    ValidationSuite,
    run_validation_command
)
from backend.migration_status_tracker import MigrationStatusTracker
from backend.pre_migration_validator import PreMigrationValidator

def setup_logging(verbose: bool = False, log_file: str = None):
    """Setup comprehensive logging"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_dir = Path("migration_logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_dir / log_file)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

def print_banner():
    """Print application banner"""
    print("\n" + "="*70)
    print("🚀 PRODUCTION AUTHENTICATION MIGRATION SYSTEM")
    print("="*70)
    print("A comprehensive migration system for authentication consolidation")
    print("with validation, status tracking, and rollback capabilities.")
    print("="*70)

async def execute_command(args):
    """Execute migration with comprehensive validation and tracking"""
    print_banner()
    
    # Setup logging
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"migration_execution_{timestamp}.log" if args.verbose else None
    setup_logging(args.verbose, log_file)
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting production migration execution")
    
    try:
        # Run pre-execution validation if not skipped
        if not args.skip_pre_validation:
            print("\n🔍 Running pre-execution validation...")
            
            validation_suite = ValidationSuite(
                run_pre_migration=True,
                run_post_migration=False,
                run_integrity_check=True,
                save_reports=True,
                detailed_output=args.verbose,
                backup_directory=args.backup_dir,
                report_directory=args.report_dir
            )
            
            validator = MigrationValidationRunner(validation_suite)
            validation_result = await validator.run_comprehensive_validation()
            
            if not validation_result.overall_success and not args.force:
                print("❌ Pre-execution validation failed. Use --force to proceed anyway.")
                print("\nCritical Issues:")
                for issue in validation_result.critical_issues[:5]:
                    print(f"  - {issue}")
                return 1
            elif not validation_result.overall_success:
                print("⚠️  Pre-execution validation failed but proceeding due to --force flag")
        
        # Execute migration using the existing execution script
        result = await execute_migration_command(args)
        
        # Run post-execution validation if migration succeeded
        if result == 0 and not args.skip_post_validation:
            print("\n🔍 Running post-execution validation...")
            
            validation_suite = ValidationSuite(
                run_pre_migration=False,
                run_post_migration=True,
                run_integrity_check=True,
                save_reports=True,
                detailed_output=args.verbose,
                backup_directory=args.backup_dir,
                report_directory=args.report_dir
            )
            
            validator = MigrationValidationRunner(validation_suite)
            validation_result = await validator.run_comprehensive_validation()
            
            if not validation_result.overall_success:
                print("⚠️  Post-execution validation found issues")
                print("Migration completed but with validation warnings")
                return 2  # Different exit code for validation warnings
        
        return result
        
    except Exception as e:
        logger.error(f"Migration execution failed: {e}")
        print(f"\n❌ Migration execution failed: {e}")
        return 1

def status_command(args):
    """Show comprehensive migration status"""
    print_banner()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Use existing status command but with enhanced output
    result = show_migration_status(args)
    
    # Add additional status information
    if args.detailed:
        print("\n" + "="*60)
        print("ADDITIONAL STATUS INFORMATION")
        print("="*60)
        
        try:
            # Show validation status
            tracker = MigrationStatusTracker()
            status_report = tracker.generate_status_report(detailed=True)
            
            if 'system_health' in status_report:
                health = status_report['system_health']
                print(f"\nSYSTEM HEALTH:")
                print(f"  Database accessible: {'✅' if health['database_accessible'] else '❌'}")
                print(f"  Tables exist: {'✅' if health['tables_exist'] else '❌'}")
                print(f"  Data consistency: {'✅' if health['data_consistency']['consistency_ok'] else '❌'}")
                
                if not health['data_consistency']['consistency_ok']:
                    dc = health['data_consistency']
                    print(f"    Orphaned legacy sessions: {dc.get('orphaned_legacy_sessions', 0)}")
                    print(f"    Orphaned unified sessions: {dc.get('orphaned_unified_sessions', 0)}")
            
        except Exception as e:
            print(f"\n⚠️  Could not retrieve additional status: {e}")
    
    return result

async def validate_command(args):
    """Run comprehensive validation"""
    print_banner()
    
    # Setup logging
    setup_logging(args.verbose)
    
    if args.comprehensive:
        # Use the comprehensive validation runner
        return await run_validation_command(args)
    else:
        # Use existing validation command
        return await validate_migration_command(args)

def check_system_command(args):
    """Run system readiness check"""
    print_banner()
    print("\n🔍 Running system readiness check...")
    
    setup_logging(args.verbose)
    
    try:
        # Run pre-migration validation
        validator = PreMigrationValidator(args.backup_dir)
        report = validator.validate_system_readiness()
        
        print(f"\nSYSTEM READINESS: {report.overall_status.upper()}")
        print(f"Validation Time: {report.validation_time}")
        
        print(f"\nSYSTEM CHECKS:")
        print(f"  Database connectivity: {'✅' if report.database_connectivity else '❌'}")
        print(f"  Disk space sufficient: {'✅' if report.disk_space_sufficient else '❌'}")
        print(f"  Backup directory writable: {'✅' if report.backup_directory_writable else '❌'}")
        print(f"  Legacy data valid: {'✅' if report.legacy_data_valid else '❌'}")
        print(f"  No data conflicts: {'✅' if report.no_data_conflicts else '❌'}")
        print(f"  Password hashes supported: {'✅' if report.password_hashes_supported else '❌'}")
        
        print(f"\nDATA COUNTS:")
        print(f"  Legacy users: {report.legacy_users_count}")
        print(f"  Legacy sessions: {report.legacy_sessions_count}")
        print(f"  Unified users: {report.unified_users_count}")
        print(f"  Unified sessions: {report.unified_sessions_count}")
        
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
            print(f"\nReadiness report saved to: {report_file}")
        
        return 0 if report.overall_status == 'ready' else 1
        
    except Exception as e:
        print(f"❌ System check failed: {e}")
        return 1

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Production Authentication Migration System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  execute    Execute migration with comprehensive validation
  status     Show current migration status
  validate   Run migration validation checks
  check      Run system readiness check

Examples:
  # Execute migration with all safety checks
  python production_migration_runner.py execute
  
  # Execute migration with comprehensive validation
  python production_migration_runner.py execute --comprehensive-validation
  
  # Dry run to see what would happen
  python production_migration_runner.py execute --dry-run
  
  # Force execution without confirmation
  python production_migration_runner.py execute --force --yes
  
  # Check migration status
  python production_migration_runner.py status --detailed
  
  # Run comprehensive validation
  python production_migration_runner.py validate --comprehensive
  
  # Check system readiness
  python production_migration_runner.py check --save-report
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Execute command
    execute_parser = subparsers.add_parser('execute', help='Execute migration')
    execute_parser.add_argument('--dry-run', action='store_true', help='Perform dry run without making changes')
    execute_parser.add_argument('--force', action='store_true', help='Force execution even if validation fails')
    execute_parser.add_argument('--yes', action='store_true', help='Skip confirmation prompts')
    execute_parser.add_argument('--skip-backup', action='store_true', help='Skip backup creation')
    execute_parser.add_argument('--skip-pre-validation', action='store_true', help='Skip pre-migration validation')
    execute_parser.add_argument('--skip-post-validation', action='store_true', help='Skip post-migration validation')
    execute_parser.add_argument('--comprehensive-validation', action='store_true', help='Run comprehensive validation')
    execute_parser.add_argument('--skip-report', action='store_true', help='Skip report generation')
    execute_parser.add_argument('--no-rollback', action='store_true', help='Disable automatic rollback on failure')
    execute_parser.add_argument('--backup-dir', default='migration_backups', help='Backup directory')
    execute_parser.add_argument('--report-dir', default='migration_reports', help='Report directory')
    execute_parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    execute_parser.add_argument('--retry-attempts', type=int, default=3, help='Maximum retry attempts')
    execute_parser.add_argument('--verbose', action='store_true', help='Enable detailed logging')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show migration status')
    status_parser.add_argument('--detailed', action='store_true', help='Show detailed status information')
    status_parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Run migration validation')
    validate_parser.add_argument('--comprehensive', action='store_true', help='Run comprehensive validation')
    validate_parser.add_argument('--show-details', action='store_true', help='Show detailed error information')
    validate_parser.add_argument('--skip-pre', action='store_true', help='Skip pre-migration validation')
    validate_parser.add_argument('--skip-post', action='store_true', help='Skip post-migration validation')
    validate_parser.add_argument('--skip-integrity', action='store_true', help='Skip integrity check')
    validate_parser.add_argument('--no-save', action='store_true', help='Do not save validation reports')
    validate_parser.add_argument('--detailed', action='store_true', help='Show detailed output')
    validate_parser.add_argument('--backup-dir', default='migration_backups', help='Backup directory')
    validate_parser.add_argument('--report-dir', default='migration_reports', help='Report directory')
    validate_parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Run system readiness check')
    check_parser.add_argument('--backup-dir', default='migration_backups', help='Backup directory to check')
    check_parser.add_argument('--save-report', action='store_true', help='Save readiness report to file')
    check_parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.command == 'execute':
        return asyncio.run(execute_command(args))
    elif args.command == 'status':
        return status_command(args)
    elif args.command == 'validate':
        return asyncio.run(validate_command(args))
    elif args.command == 'check':
        return check_system_command(args)
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())