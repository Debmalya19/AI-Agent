#!/usr/bin/env python3
"""
Authentication Migration CLI Script

This script provides a command-line interface for running the authentication migration
from legacy User/UserSession models to the unified authentication system.

Usage:
    python run_auth_migration.py migrate [options]
    python run_auth_migration.py validate [options]
    python run_auth_migration.py rollback [options]
    python run_auth_migration.py status

Requirements addressed:
- 1.3: Consistent authentication method migration
- 3.1, 3.2: Single user model migration
- 4.1, 4.2, 4.3: Data preservation during migration
"""

import argparse
import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# Add the parent directory to sys.path to allow importing from ai-agent backend
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.auth_migration_system import (
    AuthMigrationSystem,
    MigrationConfig,
    MigrationPhase,
    run_authentication_migration
)
from backend.auth_migration_validator import (
    AuthMigrationValidator,
    validate_auth_migration_pre,
    validate_auth_migration_post,
    validate_auth_migration_integrity
)
from backend.auth_migration_rollback import (
    AuthMigrationRollback,
    rollback_auth_migration,
    validate_rollback_backup
)
from backend.database import SessionLocal
from backend.unified_models import UnifiedUser, UnifiedUserSession
from backend.models import User as LegacyUser, UserSession as LegacyUserSession

def setup_logging(log_level: str = 'INFO', log_file: str = None):
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)

def print_validation_result(result, title: str):
    """Print validation result in a formatted way"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    
    if result.is_valid:
        print("✅ Validation PASSED")
    else:
        print("❌ Validation FAILED")
    
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    print(f"Info messages: {len(result.info)}")
    
    if result.errors:
        print(f"\n🔴 ERRORS:")
        for error in result.errors:
            print(f"  - {error}")
    
    if result.warnings:
        print(f"\n🟡 WARNINGS:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    if result.info:
        print(f"\n🔵 INFO:")
        for info in result.info:
            print(f"  - {info}")

def save_results_to_file(results: dict, filename: str):
    """Save results to a JSON file"""
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to {filename}")
    except Exception as e:
        print(f"Failed to save results to {filename}: {e}")

def run_migrate_command(args):
    """Run the migration command"""
    print("🚀 Starting authentication migration...")
    print(f"Backup enabled: {args.backup}")
    print(f"Dry run: {args.dry_run}")
    print(f"Force bcrypt rehash: {args.force_bcrypt}")
    
    if args.dry_run:
        print("⚠️  DRY RUN MODE - No actual changes will be made")
    
    try:
        # Create migration configuration
        config = MigrationConfig(
            backup_enabled=args.backup,
            validate_before_migration=args.validate_before,
            validate_after_migration=args.validate_after,
            force_bcrypt_rehash=args.force_bcrypt,
            dry_run=args.dry_run,
            backup_directory=args.backup_dir,
            batch_size=args.batch_size
        )
        
        # Run migration
        migration_system = AuthMigrationSystem(config)
        stats = migration_system.run_migration()
        
        # Print results
        print(f"\n{'='*60}")
        print("MIGRATION COMPLETED")
        print(f"{'='*60}")
        
        stats_dict = stats.to_dict()
        
        print(f"Phase: {stats.phase.value}")
        print(f"Duration: {stats_dict.get('duration_seconds', 0):.2f} seconds")
        print(f"Users migrated: {stats_dict['users_migrated']}")
        print(f"Sessions migrated: {stats_dict['sessions_migrated']}")
        print(f"Password hashes converted: {stats_dict['password_hashes_converted']}")
        print(f"Errors: {len(stats_dict['errors'])}")
        print(f"Warnings: {len(stats_dict['warnings'])}")
        
        if stats_dict['errors']:
            print(f"\n🔴 MIGRATION ERRORS:")
            for error in stats_dict['errors']:
                print(f"  - {error}")
        
        if stats_dict['warnings']:
            print(f"\n🟡 MIGRATION WARNINGS:")
            for warning in stats_dict['warnings']:
                print(f"  - {warning}")
        
        # Print validation results
        if stats.pre_migration_validation:
            print_validation_result(stats.pre_migration_validation, "PRE-MIGRATION VALIDATION")
        
        if stats.post_migration_validation:
            print_validation_result(stats.post_migration_validation, "POST-MIGRATION VALIDATION")
        
        # Save results if requested
        if args.output:
            save_results_to_file(stats_dict, args.output)
        
        return 0 if stats.phase == MigrationPhase.COMPLETED else 1
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return 1

def run_validate_command(args):
    """Run the validation command"""
    print("🔍 Starting authentication migration validation...")
    
    try:
        with SessionLocal() as session:
            validator = AuthMigrationValidator(session)
            
            if args.pre_migration:
                print("\n📋 Running pre-migration validation...")
                result = validator.validate_pre_migration()
                print_validation_result(result, "PRE-MIGRATION VALIDATION")
            
            if args.post_migration:
                print("\n📋 Running post-migration validation...")
                result = validator.validate_post_migration()
                print_validation_result(result, "POST-MIGRATION VALIDATION")
            
            if args.integrity:
                print("\n📋 Running migration integrity validation...")
                result = validator.validate_migration_integrity()
                print_validation_result(result, "MIGRATION INTEGRITY VALIDATION")
            
            # If no specific validation requested, run all
            if not any([args.pre_migration, args.post_migration, args.integrity]):
                print("\n📋 Running comprehensive validation...")
                
                pre_result = validator.validate_pre_migration()
                print_validation_result(pre_result, "PRE-MIGRATION VALIDATION")
                
                post_result = validator.validate_post_migration()
                print_validation_result(post_result, "POST-MIGRATION VALIDATION")
                
                integrity_result = validator.validate_migration_integrity()
                print_validation_result(integrity_result, "MIGRATION INTEGRITY VALIDATION")
                
                # Combine results
                result = pre_result
                result.merge(post_result)
                result.merge(integrity_result)
            
            # Save results if requested
            if args.output:
                save_results_to_file(result.to_dict(), args.output)
            
            return 0 if result.is_valid else 1
            
    except Exception as e:
        print(f"\n💥 Validation failed: {e}")
        return 1

def run_rollback_command(args):
    """Run the rollback command"""
    print("🔄 Starting authentication migration rollback...")
    
    if not args.backup_path:
        print("❌ Backup path is required for rollback")
        return 1
    
    try:
        # Validate backup first
        print("🔍 Validating backup...")
        validation_result = validate_rollback_backup(args.backup_path)
        print_validation_result(validation_result, "BACKUP VALIDATION")
        
        if not validation_result.is_valid and not args.force:
            print("❌ Backup validation failed. Use --force to proceed anyway.")
            return 1
        
        # Confirm rollback
        if not args.yes:
            response = input("\n⚠️  This will permanently remove unified authentication data. Continue? (y/N): ")
            if response.lower() != 'y':
                print("Rollback cancelled.")
                return 0
        
        # Perform rollback
        rollback_system = AuthMigrationRollback(args.backup_path)
        stats = rollback_system.rollback_migration(preserve_unified_data=args.preserve)
        
        # Print results
        print(f"\n{'='*60}")
        print("ROLLBACK COMPLETED")
        print(f"{'='*60}")
        
        stats_dict = stats.to_dict()
        
        print(f"Success: {stats.success}")
        print(f"Duration: {stats_dict.get('duration_seconds', 0):.2f} seconds")
        print(f"Unified users removed: {stats_dict['unified_users_removed']}")
        print(f"Unified sessions removed: {stats_dict['unified_sessions_removed']}")
        print(f"Legacy users restored: {stats_dict['legacy_users_restored']}")
        print(f"Legacy sessions restored: {stats_dict['legacy_sessions_restored']}")
        print(f"Errors: {len(stats_dict['errors'])}")
        print(f"Warnings: {len(stats_dict['warnings'])}")
        
        if stats_dict['errors']:
            print(f"\n🔴 ROLLBACK ERRORS:")
            for error in stats_dict['errors']:
                print(f"  - {error}")
        
        if stats_dict['warnings']:
            print(f"\n🟡 ROLLBACK WARNINGS:")
            for warning in stats_dict['warnings']:
                print(f"  - {warning}")
        
        # Save results if requested
        if args.output:
            save_results_to_file(stats_dict, args.output)
        
        # Create rollback report
        report_path = rollback_system.create_rollback_report()
        print(f"\n📊 Rollback report saved to {report_path}")
        
        return 0 if stats.success else 1
        
    except Exception as e:
        print(f"\n❌ Rollback failed: {e}")
        return 1

def run_status_command(args):
    """Run the status command"""
    print("📊 Checking authentication migration status...")
    
    try:
        with SessionLocal() as session:
            # Check legacy data
            legacy_user_count = session.query(LegacyUser).count()
            legacy_session_count = session.query(LegacyUserSession).count()
            legacy_active_sessions = session.query(LegacyUserSession).filter(
                LegacyUserSession.is_active == True
            ).count()
            
            # Check unified data
            unified_user_count = session.query(UnifiedUser).count()
            unified_session_count = session.query(UnifiedUserSession).count()
            unified_active_sessions = session.query(UnifiedUserSession).filter(
                UnifiedUserSession.is_active == True
            ).count()
            
            # Check migration indicators
            users_with_legacy_ids = session.query(UnifiedUser).filter(
                (UnifiedUser.legacy_customer_id.isnot(None)) |
                (UnifiedUser.legacy_admin_user_id.isnot(None))
            ).count()
            
            print(f"\n{'='*60}")
            print("AUTHENTICATION SYSTEM STATUS")
            print(f"{'='*60}")
            
            print(f"\n📊 LEGACY SYSTEM:")
            print(f"  Users: {legacy_user_count}")
            print(f"  Sessions: {legacy_session_count}")
            print(f"  Active sessions: {legacy_active_sessions}")
            
            print(f"\n📊 UNIFIED SYSTEM:")
            print(f"  Users: {unified_user_count}")
            print(f"  Sessions: {unified_session_count}")
            print(f"  Active sessions: {unified_active_sessions}")
            print(f"  Users with legacy IDs: {users_with_legacy_ids}")
            
            print(f"\n🔍 MIGRATION STATUS:")
            if unified_user_count == 0:
                print("  ❌ Migration not started - no unified users found")
                migration_status = "not_started"
            elif users_with_legacy_ids == 0:
                print("  ⚠️  Migration status unclear - no legacy ID references found")
                migration_status = "unclear"
            elif users_with_legacy_ids == unified_user_count:
                print("  ✅ Migration appears complete - all unified users have legacy references")
                migration_status = "complete"
            else:
                print(f"  ⚠️  Partial migration - {users_with_legacy_ids}/{unified_user_count} users have legacy references")
                migration_status = "partial"
            
            # Recommendations
            print(f"\n💡 RECOMMENDATIONS:")
            if migration_status == "not_started":
                print("  - Run 'python run_auth_migration.py validate --pre-migration' to check readiness")
                print("  - Run 'python run_auth_migration.py migrate' to start migration")
            elif migration_status == "partial":
                print("  - Run 'python run_auth_migration.py validate --integrity' to check data consistency")
                print("  - Consider re-running migration if issues are found")
            elif migration_status == "complete":
                print("  - Run 'python run_auth_migration.py validate --post-migration' to verify integrity")
                print("  - Consider updating application to use unified authentication")
            
            return 0
        
    except Exception as e:
        print(f"\n💥 Status check failed: {e}")
        return 1

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Authentication migration tool for AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check migration status
  python run_auth_migration.py status
  
  # Run migration with backup
  python run_auth_migration.py migrate --backup
  
  # Run migration without backup (faster)
  python run_auth_migration.py migrate --no-backup
  
  # Dry run to see what would be migrated
  python run_auth_migration.py migrate --dry-run
  
  # Validate before migration
  python run_auth_migration.py validate --pre-migration
  
  # Validate after migration
  python run_auth_migration.py validate --post-migration
  
  # Rollback migration
  python run_auth_migration.py rollback --backup-path ./backups/auth_migration_backup_20241217_143022
        """
    )
    
    # Global arguments
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level'
    )
    parser.add_argument(
        '--log-file',
        help='Log to file in addition to console'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Migration command
    migrate_parser = subparsers.add_parser('migrate', help='Run authentication migration')
    migrate_parser.add_argument(
        '--backup',
        action='store_true',
        default=True,
        help='Create backup before migration (default: True)'
    )
    migrate_parser.add_argument(
        '--no-backup',
        action='store_false',
        dest='backup',
        help='Skip backup creation'
    )
    migrate_parser.add_argument(
        '--backup-dir',
        default='backups',
        help='Directory for backup files'
    )
    migrate_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without making changes'
    )
    migrate_parser.add_argument(
        '--validate-before',
        action='store_true',
        default=True,
        help='Run validation before migration (default: True)'
    )
    migrate_parser.add_argument(
        '--no-validate-before',
        action='store_false',
        dest='validate_before',
        help='Skip pre-migration validation'
    )
    migrate_parser.add_argument(
        '--validate-after',
        action='store_true',
        default=True,
        help='Run validation after migration (default: True)'
    )
    migrate_parser.add_argument(
        '--no-validate-after',
        action='store_false',
        dest='validate_after',
        help='Skip post-migration validation'
    )
    migrate_parser.add_argument(
        '--force-bcrypt',
        action='store_true',
        help='Force rehashing of all passwords to bcrypt'
    )
    migrate_parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Batch size for processing records'
    )
    migrate_parser.add_argument(
        '--output',
        help='Save migration results to JSON file'
    )
    
    # Validation command
    validate_parser = subparsers.add_parser('validate', help='Validate migration state')
    validate_parser.add_argument(
        '--pre-migration',
        action='store_true',
        help='Run pre-migration validation'
    )
    validate_parser.add_argument(
        '--post-migration',
        action='store_true',
        help='Run post-migration validation'
    )
    validate_parser.add_argument(
        '--integrity',
        action='store_true',
        help='Run migration integrity validation'
    )
    validate_parser.add_argument(
        '--output',
        help='Save validation results to JSON file'
    )
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback migration')
    rollback_parser.add_argument(
        '--backup-path',
        required=True,
        help='Path to backup directory for rollback'
    )
    rollback_parser.add_argument(
        '--preserve',
        action='store_true',
        help='Preserve unified data before rollback'
    )
    rollback_parser.add_argument(
        '--force',
        action='store_true',
        help='Force rollback even if backup validation fails'
    )
    rollback_parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt'
    )
    rollback_parser.add_argument(
        '--output',
        help='Save rollback results to JSON file'
    )
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check migration status')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    # Run appropriate command
    if args.command == 'migrate':
        return run_migrate_command(args)
    elif args.command == 'validate':
        return run_validate_command(args)
    elif args.command == 'rollback':
        return run_rollback_command(args)
    elif args.command == 'status':
        return run_status_command(args)
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())