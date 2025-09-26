#!/usr/bin/env python3
"""
Database migration CLI script.
Provides command-line interface for running the unified database migration.
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

from backend.migration_system import (
    run_migration,
    validate_migration,
    MigrationError,
    DatabaseConnector,
)
from backend.data_validation import (
    validate_database,
    ValidationResult,
)

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

def print_validation_result(result: ValidationResult, title: str):
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
    """Save migration results to a JSON file"""
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to {filename}")
    except Exception as e:
        print(f"Failed to save results to {filename}: {e}")

def run_migration_command(args):
    """Run the migration command"""
    print("🚀 Starting database migration...")
    print(f"Backup enabled: {args.backup}")
    print(f"Dry run: {args.dry_run}")
    
    if args.dry_run:
        print("⚠️  DRY RUN MODE - No actual changes will be made")
        # In a real implementation, we'd run validation only
        return
    
    try:
        # Run migration
        stats = run_migration(backup=args.backup)
        
        # Print results
        print(f"\n{'='*60}")
        print("MIGRATION COMPLETED")
        print(f"{'='*60}")
        
        stats_dict = stats.to_dict()
        
        print(f"Duration: {stats_dict.get('duration_seconds', 0):.2f} seconds")
        print(f"Users migrated: {stats_dict['users_migrated']}")
        print(f"Tickets migrated: {stats_dict['tickets_migrated']}")
        print(f"Comments migrated: {stats_dict['comments_migrated']}")
        print(f"Activities migrated: {stats_dict['activities_migrated']}")
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
        
        # Save results if requested
        if args.output:
            save_results_to_file(stats_dict, args.output)
        
        # Run validation if requested
        if args.validate:
            print("\n🔍 Running post-migration validation...")
            validation_result = validate_migration()
            print_validation_result(validation_result, "POST-MIGRATION VALIDATION")
        
        return 0 if not stats_dict['errors'] else 1
        
    except MigrationError as e:
        print(f"\n❌ Migration failed: {e}")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error during migration: {e}")
        return 1

def run_validation_command(args):
    """Run the validation command"""
    print("🔍 Starting database validation...")
    
    try:
        with DatabaseConnector.get_unified_session() as session:
            # Run comprehensive validation
            validation_result = validate_database(session)
            print_validation_result(validation_result, "DATABASE VALIDATION")
            
            # Run migration-specific validation if requested
            if args.migration:
                migration_result = validate_migration(session)
                print_validation_result(migration_result, "MIGRATION VALIDATION")
                validation_result.merge(migration_result)
            
            # Save results if requested
            if args.output:
                save_results_to_file(validation_result.to_dict(), args.output)
            
            return 0 if validation_result.is_valid else 1
            
    except Exception as e:
        print(f"\n💥 Validation failed: {e}")
        return 1

def run_status_command(args):
    """Run the status command"""
    print("📊 Checking migration status...")
    
    try:
        with DatabaseConnector.get_unified_session() as session:
            # Check if unified tables exist
            from backend.unified_models import UnifiedUser, UnifiedTicket
            
            try:
                user_count = session.query(UnifiedUser).count()
                ticket_count = session.query(UnifiedTicket).count()
                
                print(f"\n✅ Unified database is accessible")
                print(f"Users: {user_count}")
                print(f"Tickets: {ticket_count}")
                
                # Check for legacy data
                users_with_legacy = session.query(UnifiedUser).filter(
                    (UnifiedUser.legacy_customer_id.isnot(None)) |
                    (UnifiedUser.legacy_admin_user_id.isnot(None))
                ).count()
                
                tickets_with_legacy = session.query(UnifiedTicket).filter(
                    (UnifiedTicket.legacy_backend_ticket_id.isnot(None)) |
                    (UnifiedTicket.legacy_admin_ticket_id.isnot(None))
                ).count()
                
                print(f"Users with legacy IDs: {users_with_legacy}")
                print(f"Tickets with legacy IDs: {tickets_with_legacy}")
                
                if users_with_legacy > 0 or tickets_with_legacy > 0:
                    print("✅ Migration appears to have been completed")
                else:
                    print("⚠️  No legacy IDs found - migration may not have been run")
                
            except Exception as e:
                print(f"❌ Unified database tables not accessible: {e}")
                return 1
        
        return 0
        
    except Exception as e:
        print(f"\n💥 Status check failed: {e}")
        return 1

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Database migration tool for AI Agent admin dashboard integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run migration with backup
  python migrate_database.py migrate --backup
  
  # Run migration without backup (faster)
  python migrate_database.py migrate --no-backup
  
  # Dry run to see what would be migrated
  python migrate_database.py migrate --dry-run
  
  # Validate database after migration
  python migrate_database.py validate --migration
  
  # Check migration status
  python migrate_database.py status
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
    migrate_parser = subparsers.add_parser('migrate', help='Run database migration')
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
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without making changes'
    )
    migrate_parser.add_argument(
        '--validate',
        action='store_true',
        help='Run validation after migration'
    )
    migrate_parser.add_argument(
        '--output',
        help='Save migration results to JSON file'
    )
    
    # Validation command
    validate_parser = subparsers.add_parser('validate', help='Validate database integrity')
    validate_parser.add_argument(
        '--migration',
        action='store_true',
        help='Include migration-specific validation'
    )
    validate_parser.add_argument(
        '--output',
        help='Save validation results to JSON file'
    )
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check migration status')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    # Run appropriate command
    if args.command == 'migrate':
        return run_migration_command(args)
    elif args.command == 'validate':
        return run_validation_command(args)
    elif args.command == 'status':
        return run_status_command(args)
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())