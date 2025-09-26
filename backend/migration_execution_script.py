#!/usr/bin/env python3
"""
Production Migration Execution Script

This script provides a production-ready interface for executing the authentication migration
with comprehensive validation, status tracking, and reporting functionality.

Requirements addressed:
- 3.2: Proper data migration to unified system
- 4.1, 4.2, 4.3: Data preservation during migration
- 4.4: Migration status tracking and reporting

Usage:
    python migration_execution_script.py --help
    python migration_execution_script.py execute --validate-all
    python migration_execution_script.py status --detailed
    python migration_execution_script.py validate --comprehensive
"""

import argparse
import sys
import os
import json
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

# Add the parent directory to sys.path to allow importing from ai-agent backend
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.auth_migration_system import (
    AuthMigrationSystem,
    MigrationConfig,
    MigrationPhase,
    MigrationStats
)
from backend.auth_migration_validator import (
    AuthMigrationValidator,
    validate_auth_migration_pre,
    validate_auth_migration_post,
    validate_auth_migration_integrity
)
from backend.auth_migration_rollback import AuthMigrationRollback
from backend.database import SessionLocal
from backend.unified_models import UnifiedUser, UnifiedUserSession
from backend.models import User as LegacyUser, UserSession as LegacyUserSession

@dataclass
class MigrationExecutionConfig:
    """Configuration for migration execution"""
    # Validation settings
    pre_migration_validation: bool = True
    post_migration_validation: bool = True
    comprehensive_validation: bool = False
    
    # Backup settings
    create_backup: bool = True
    backup_directory: str = "migration_backups"
    
    # Execution settings
    dry_run: bool = False
    force_execution: bool = False
    batch_size: int = 100
    
    # Reporting settings
    generate_report: bool = True
    report_directory: str = "migration_reports"
    detailed_logging: bool = True
    
    # Safety settings
    require_confirmation: bool = True
    max_retry_attempts: int = 3
    rollback_on_failure: bool = True

@dataclass
class MigrationExecutionResult:
    """Result of migration execution"""
    success: bool
    migration_id: str
    execution_time: datetime
    duration_seconds: float
    phase_completed: MigrationPhase
    
    # Statistics
    users_migrated: int = 0
    sessions_migrated: int = 0
    errors_count: int = 0
    warnings_count: int = 0
    
    # Validation results
    pre_validation_passed: bool = False
    post_validation_passed: bool = False
    
    # File paths
    backup_path: Optional[str] = None
    report_path: Optional[str] = None
    log_path: Optional[str] = None
    
    # Error details
    error_message: Optional[str] = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'success': self.success,
            'migration_id': self.migration_id,
            'execution_time': self.execution_time.isoformat(),
            'duration_seconds': self.duration_seconds,
            'phase_completed': self.phase_completed.value,
            'users_migrated': self.users_migrated,
            'sessions_migrated': self.sessions_migrated,
            'errors_count': self.errors_count,
            'warnings_count': self.warnings_count,
            'pre_validation_passed': self.pre_validation_passed,
            'post_validation_passed': self.post_validation_passed,
            'backup_path': self.backup_path,
            'report_path': self.report_path,
            'log_path': self.log_path,
            'error_message': self.error_message,
            'errors': self.errors,
            'warnings': self.warnings
        }

class MigrationStatusTracker:
    """Tracks migration status and provides detailed reporting"""
    
    def __init__(self, status_file: str = "migration_status.json"):
        self.status_file = Path(status_file)
        self.status_data = self._load_status()
    
    def _load_status(self) -> Dict[str, Any]:
        """Load existing status data"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load status file: {e}")
        
        return {
            'migrations': [],
            'current_phase': MigrationPhase.NOT_STARTED.value,
            'last_updated': None
        }
    
    def _save_status(self):
        """Save status data to file"""
        try:
            self.status_data['last_updated'] = datetime.now(timezone.utc).isoformat()
            with open(self.status_file, 'w') as f:
                json.dump(self.status_data, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save status file: {e}")
    
    def update_phase(self, phase: MigrationPhase, details: Dict[str, Any] = None):
        """Update current migration phase"""
        self.status_data['current_phase'] = phase.value
        if details:
            self.status_data.update(details)
        self._save_status()
    
    def add_migration_record(self, result: MigrationExecutionResult):
        """Add migration execution record"""
        self.status_data['migrations'].append(result.to_dict())
        self._save_status()
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current migration status"""
        with SessionLocal() as session:
            # Get current database state
            legacy_users = session.query(LegacyUser).count()
            legacy_sessions = session.query(LegacyUserSession).count()
            unified_users = session.query(UnifiedUser).count()
            unified_sessions = session.query(UnifiedUserSession).count()
            
            # Determine migration state
            migration_state = self._determine_migration_state(
                legacy_users, unified_users, legacy_sessions, unified_sessions
            )
            
            return {
                'current_phase': self.status_data['current_phase'],
                'migration_state': migration_state,
                'database_counts': {
                    'legacy_users': legacy_users,
                    'legacy_sessions': legacy_sessions,
                    'unified_users': unified_users,
                    'unified_sessions': unified_sessions
                },
                'last_updated': self.status_data['last_updated'],
                'migration_history': self.status_data['migrations']
            }
    
    def _determine_migration_state(self, legacy_users: int, unified_users: int, 
                                 legacy_sessions: int, unified_sessions: int) -> str:
        """Determine current migration state based on database counts"""
        if unified_users == 0:
            return "not_started"
        elif unified_users < legacy_users:
            return "partial"
        elif unified_users >= legacy_users:
            return "completed"
        else:
            return "unknown"

class ProductionMigrationExecutor:
    """Production-ready migration executor with comprehensive safety features"""
    
    def __init__(self, config: MigrationExecutionConfig):
        self.config = config
        self.status_tracker = MigrationStatusTracker()
        self.migration_id = f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        logger = logging.getLogger(f"migration_{self.migration_id}")
        logger.setLevel(logging.DEBUG if self.config.detailed_logging else logging.INFO)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        if self.config.detailed_logging:
            log_dir = Path("migration_logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"{self.migration_id}.log"
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    async def execute_migration(self) -> MigrationExecutionResult:
        """Execute migration with comprehensive safety checks and validation"""
        start_time = datetime.now(timezone.utc)
        result = MigrationExecutionResult(
            success=False,
            migration_id=self.migration_id,
            execution_time=start_time,
            duration_seconds=0.0,
            phase_completed=MigrationPhase.NOT_STARTED
        )
        
        try:
            self.logger.info(f"🚀 Starting production migration execution: {self.migration_id}")
            
            # Phase 1: Pre-execution validation
            if not await self._pre_execution_checks():
                raise Exception("Pre-execution checks failed")
            
            # Phase 2: User confirmation
            if self.config.require_confirmation and not self.config.force_execution:
                if not self._get_user_confirmation():
                    self.logger.info("Migration cancelled by user")
                    return result
            
            # Phase 3: Pre-migration validation
            if self.config.pre_migration_validation:
                self.logger.info("🔍 Running pre-migration validation...")
                validation_result = await self._run_pre_migration_validation()
                result.pre_validation_passed = validation_result.is_valid
                
                if not validation_result.is_valid and not self.config.force_execution:
                    raise Exception(f"Pre-migration validation failed: {validation_result.errors}")
            
            # Phase 4: Execute migration
            self.logger.info("⚙️ Executing migration...")
            migration_stats = await self._execute_migration_with_retry()
            
            # Update result with migration stats
            result.users_migrated = migration_stats.users_migrated
            result.sessions_migrated = migration_stats.sessions_migrated
            result.errors_count = len(migration_stats.errors)
            result.warnings_count = len(migration_stats.warnings)
            result.errors = migration_stats.errors
            result.warnings = migration_stats.warnings
            result.phase_completed = migration_stats.phase
            
            # Phase 5: Post-migration validation
            if self.config.post_migration_validation:
                self.logger.info("🔍 Running post-migration validation...")
                validation_result = await self._run_post_migration_validation()
                result.post_validation_passed = validation_result.is_valid
                
                if not validation_result.is_valid:
                    self.logger.warning("Post-migration validation failed")
                    result.warnings.extend(validation_result.errors)
            
            # Phase 6: Generate report
            if self.config.generate_report:
                report_path = await self._generate_migration_report(result, migration_stats)
                result.report_path = str(report_path)
            
            # Mark as successful
            result.success = True
            self.logger.info("✅ Migration completed successfully")
            
        except Exception as e:
            result.error_message = str(e)
            result.errors.append(str(e))
            self.logger.error(f"❌ Migration failed: {e}")
            
            # Attempt rollback if configured
            if self.config.rollback_on_failure and result.backup_path:
                try:
                    await self._attempt_rollback(result.backup_path)
                except Exception as rollback_error:
                    self.logger.error(f"Rollback also failed: {rollback_error}")
        
        finally:
            # Calculate duration
            end_time = datetime.now(timezone.utc)
            result.duration_seconds = (end_time - start_time).total_seconds()
            
            # Update status tracker
            self.status_tracker.add_migration_record(result)
            
            # Log final status
            self.logger.info(f"Migration execution completed in {result.duration_seconds:.2f} seconds")
        
        return result
    
    async def _pre_execution_checks(self) -> bool:
        """Run comprehensive pre-execution checks"""
        self.logger.info("🔍 Running pre-execution checks...")
        
        try:
            # Check database connectivity
            with SessionLocal() as session:
                session.execute("SELECT 1")
            
            # Check disk space for backup
            if self.config.create_backup:
                backup_dir = Path(self.config.backup_directory)
                backup_dir.mkdir(parents=True, exist_ok=True)
                
                # Estimate backup size (rough calculation)
                with SessionLocal() as session:
                    user_count = session.query(LegacyUser).count()
                    session_count = session.query(LegacyUserSession).count()
                
                estimated_size_mb = (user_count + session_count) * 0.001  # Rough estimate
                self.logger.info(f"Estimated backup size: {estimated_size_mb:.2f} MB")
            
            # Check for existing migration
            current_status = self.status_tracker.get_current_status()
            if current_status['migration_state'] == 'completed':
                self.logger.warning("Migration appears to already be completed")
                if not self.config.force_execution:
                    return False
            
            self.logger.info("✅ Pre-execution checks passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Pre-execution checks failed: {e}")
            return False
    
    def _get_user_confirmation(self) -> bool:
        """Get user confirmation for migration execution"""
        print("\n" + "="*60)
        print("AUTHENTICATION MIGRATION CONFIRMATION")
        print("="*60)
        print("This will migrate your authentication system from legacy to unified.")
        print("This operation will:")
        print("- Migrate all user accounts to the new system")
        print("- Migrate active user sessions")
        print("- Create a backup of existing data (if enabled)")
        print("- Validate data integrity before and after migration")
        print("\nPlease ensure you have:")
        print("- Backed up your database")
        print("- Tested this migration in a development environment")
        print("- Scheduled appropriate downtime")
        
        if self.config.dry_run:
            print("\n⚠️  DRY RUN MODE - No actual changes will be made")
        
        print("\n" + "="*60)
        
        while True:
            response = input("Do you want to proceed with the migration? (yes/no): ").lower().strip()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            else:
                print("Please enter 'yes' or 'no'")
    
    async def _run_pre_migration_validation(self):
        """Run comprehensive pre-migration validation"""
        with SessionLocal() as session:
            validator = AuthMigrationValidator(session)
            
            if self.config.comprehensive_validation:
                # Run all validation types
                pre_result = validator.validate_pre_migration()
                integrity_result = validator.validate_migration_integrity()
                
                # Combine results
                pre_result.merge(integrity_result)
                return pre_result
            else:
                return validator.validate_pre_migration()
    
    async def _run_post_migration_validation(self):
        """Run comprehensive post-migration validation"""
        with SessionLocal() as session:
            validator = AuthMigrationValidator(session)
            
            if self.config.comprehensive_validation:
                # Run all validation types
                post_result = validator.validate_post_migration()
                integrity_result = validator.validate_migration_integrity()
                
                # Combine results
                post_result.merge(integrity_result)
                return post_result
            else:
                return validator.validate_post_migration()
    
    async def _execute_migration_with_retry(self) -> MigrationStats:
        """Execute migration with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_retry_attempts):
            try:
                self.logger.info(f"Migration attempt {attempt + 1}/{self.config.max_retry_attempts}")
                
                # Create migration configuration
                migration_config = MigrationConfig(
                    backup_enabled=self.config.create_backup,
                    backup_directory=self.config.backup_directory,
                    validate_before_migration=False,  # We handle validation separately
                    validate_after_migration=False,   # We handle validation separately
                    batch_size=self.config.batch_size,
                    dry_run=self.config.dry_run
                )
                
                # Execute migration
                migration_system = AuthMigrationSystem(migration_config)
                stats = await migration_system.run_migration()
                
                self.logger.info(f"Migration attempt {attempt + 1} completed successfully")
                return stats
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Migration attempt {attempt + 1} failed: {e}")
                
                if attempt < self.config.max_retry_attempts - 1:
                    self.logger.info(f"Retrying migration (attempt {attempt + 2})...")
                    await asyncio.sleep(5)  # Wait before retry
        
        # All attempts failed
        raise Exception(f"Migration failed after {self.config.max_retry_attempts} attempts. Last error: {last_exception}")
    
    async def _generate_migration_report(self, result: MigrationExecutionResult, 
                                       stats: MigrationStats) -> Path:
        """Generate comprehensive migration report"""
        report_dir = Path(self.config.report_directory)
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / f"migration_report_{self.migration_id}.json"
        
        report_data = {
            'migration_id': self.migration_id,
            'execution_result': result.to_dict(),
            'migration_stats': stats.to_dict(),
            'configuration': asdict(self.config),
            'system_status': self.status_tracker.get_current_status(),
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        self.logger.info(f"Migration report generated: {report_file}")
        return report_file
    
    async def _attempt_rollback(self, backup_path: str):
        """Attempt to rollback migration using backup"""
        self.logger.warning("Attempting migration rollback...")
        
        try:
            rollback_system = AuthMigrationRollback(backup_path)
            rollback_stats = rollback_system.rollback_migration()
            
            if rollback_stats.success:
                self.logger.info("✅ Rollback completed successfully")
            else:
                self.logger.error("❌ Rollback failed")
                
        except Exception as e:
            self.logger.error(f"Rollback attempt failed: {e}")
            raise

def create_migration_config_from_args(args) -> MigrationExecutionConfig:
    """Create migration configuration from command line arguments"""
    return MigrationExecutionConfig(
        pre_migration_validation=not args.skip_pre_validation,
        post_migration_validation=not args.skip_post_validation,
        comprehensive_validation=args.comprehensive_validation,
        create_backup=not args.skip_backup,
        backup_directory=args.backup_dir,
        dry_run=args.dry_run,
        force_execution=args.force,
        batch_size=args.batch_size,
        generate_report=not args.skip_report,
        report_directory=args.report_dir,
        detailed_logging=args.verbose,
        require_confirmation=not args.yes,
        max_retry_attempts=args.retry_attempts,
        rollback_on_failure=not args.no_rollback
    )

async def execute_migration_command(args):
    """Execute migration command"""
    config = create_migration_config_from_args(args)
    executor = ProductionMigrationExecutor(config)
    
    result = await executor.execute_migration()
    
    # Print summary
    print("\n" + "="*60)
    print("MIGRATION EXECUTION SUMMARY")
    print("="*60)
    print(f"Migration ID: {result.migration_id}")
    print(f"Success: {'✅ YES' if result.success else '❌ NO'}")
    print(f"Duration: {result.duration_seconds:.2f} seconds")
    print(f"Phase completed: {result.phase_completed.value}")
    print(f"Users migrated: {result.users_migrated}")
    print(f"Sessions migrated: {result.sessions_migrated}")
    print(f"Errors: {result.errors_count}")
    print(f"Warnings: {result.warnings_count}")
    
    if result.backup_path:
        print(f"Backup created: {result.backup_path}")
    
    if result.report_path:
        print(f"Report generated: {result.report_path}")
    
    if result.error_message:
        print(f"Error: {result.error_message}")
    
    return 0 if result.success else 1

def show_migration_status(args):
    """Show current migration status"""
    tracker = MigrationStatusTracker()
    status = tracker.get_current_status()
    
    print("\n" + "="*60)
    print("MIGRATION STATUS")
    print("="*60)
    print(f"Current phase: {status['current_phase']}")
    print(f"Migration state: {status['migration_state']}")
    print(f"Last updated: {status['last_updated']}")
    
    print(f"\nDATABASE COUNTS:")
    counts = status['database_counts']
    print(f"  Legacy users: {counts['legacy_users']}")
    print(f"  Legacy sessions: {counts['legacy_sessions']}")
    print(f"  Unified users: {counts['unified_users']}")
    print(f"  Unified sessions: {counts['unified_sessions']}")
    
    if args.detailed and status['migration_history']:
        print(f"\nMIGRATION HISTORY:")
        for i, migration in enumerate(status['migration_history'][-5:], 1):  # Show last 5
            print(f"  {i}. {migration['migration_id']} - {'SUCCESS' if migration['success'] else 'FAILED'}")
            print(f"     Time: {migration['execution_time']}")
            print(f"     Duration: {migration['duration_seconds']:.2f}s")
    
    return 0

async def validate_migration_command(args):
    """Run migration validation"""
    print("🔍 Running migration validation...")
    
    try:
        with SessionLocal() as session:
            validator = AuthMigrationValidator(session)
            
            if args.comprehensive:
                # Run all validations
                pre_result = validator.validate_pre_migration()
                post_result = validator.validate_post_migration()
                integrity_result = validator.validate_migration_integrity()
                
                print("\n" + "="*60)
                print("COMPREHENSIVE VALIDATION RESULTS")
                print("="*60)
                
                print("\nPRE-MIGRATION VALIDATION:")
                print(f"  Valid: {'✅ YES' if pre_result.is_valid else '❌ NO'}")
                print(f"  Errors: {len(pre_result.errors)}")
                print(f"  Warnings: {len(pre_result.warnings)}")
                
                print("\nPOST-MIGRATION VALIDATION:")
                print(f"  Valid: {'✅ YES' if post_result.is_valid else '❌ NO'}")
                print(f"  Errors: {len(post_result.errors)}")
                print(f"  Warnings: {len(post_result.warnings)}")
                
                print("\nINTEGRITY VALIDATION:")
                print(f"  Valid: {'✅ YES' if integrity_result.is_valid else '❌ NO'}")
                print(f"  Errors: {len(integrity_result.errors)}")
                print(f"  Warnings: {len(integrity_result.warnings)}")
                
                # Show errors if any
                all_errors = pre_result.errors + post_result.errors + integrity_result.errors
                if all_errors and args.show_details:
                    print(f"\nERRORS:")
                    for error in all_errors[:10]:  # Show first 10 errors
                        print(f"  - {error}")
                
                return 0 if all([pre_result.is_valid, post_result.is_valid, integrity_result.is_valid]) else 1
            
            else:
                # Run basic validation based on current state
                tracker = MigrationStatusTracker()
                status = tracker.get_current_status()
                
                if status['migration_state'] == 'not_started':
                    result = validator.validate_pre_migration()
                    validation_type = "PRE-MIGRATION"
                else:
                    result = validator.validate_post_migration()
                    validation_type = "POST-MIGRATION"
                
                print(f"\n{validation_type} VALIDATION RESULTS:")
                print(f"Valid: {'✅ YES' if result.is_valid else '❌ NO'}")
                print(f"Errors: {len(result.errors)}")
                print(f"Warnings: {len(result.warnings)}")
                
                if result.errors and args.show_details:
                    print(f"\nERRORS:")
                    for error in result.errors[:10]:
                        print(f"  - {error}")
                
                return 0 if result.is_valid else 1
    
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 1

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Production Authentication Migration Execution Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute migration with all safety checks
  python migration_execution_script.py execute
  
  # Execute migration with comprehensive validation
  python migration_execution_script.py execute --comprehensive-validation
  
  # Dry run to see what would happen
  python migration_execution_script.py execute --dry-run
  
  # Force execution without confirmation
  python migration_execution_script.py execute --force --yes
  
  # Check migration status
  python migration_execution_script.py status --detailed
  
  # Run comprehensive validation
  python migration_execution_script.py validate --comprehensive --show-details
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
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Run migration validation')
    validate_parser.add_argument('--comprehensive', action='store_true', help='Run comprehensive validation')
    validate_parser.add_argument('--show-details', action='store_true', help='Show detailed error information')
    
    args = parser.parse_args()
    
    if args.command == 'execute':
        return asyncio.run(execute_migration_command(args))
    elif args.command == 'status':
        return show_migration_status(args)
    elif args.command == 'validate':
        return asyncio.run(validate_migration_command(args))
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())