#!/usr/bin/env python3
"""
Complete Migration Execution Script

This script executes the complete migration from SQLite to PostgreSQL and validates
all application functionality. It handles existing data conflicts and ensures a
clean migration.

Requirements: 2.1, 2.2, 2.3, 5.1, 5.2
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from scripts.migrate_to_postgresql import DatabaseMigrator, MigrationConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('complete_migration_execution.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CompleteMigrationExecutor:
    """Executes complete migration and validation process"""
    
    def __init__(self):
        load_dotenv()
        self.sqlite_url = "sqlite:///ai_agent.db"
        self.postgresql_url = os.getenv("DATABASE_URL")
        self.migration_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if not self.postgresql_url:
            raise ValueError("DATABASE_URL environment variable not set")
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met for migration"""
        logger.info("Checking migration prerequisites...")
        
        # Check if SQLite database exists
        if not os.path.exists("ai_agent.db"):
            logger.error("SQLite database 'ai_agent.db' not found")
            return False
        
        # Check PostgreSQL connection
        try:
            engine = create_engine(self.postgresql_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"PostgreSQL connection successful: {version}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False
        
        # Check if migration script exists
        if not os.path.exists("scripts/migrate_to_postgresql.py"):
            logger.error("Migration script not found")
            return False
        
        logger.info("All prerequisites met")
        return True
    
    def clean_postgresql_database(self) -> bool:
        """Clean PostgreSQL database for fresh migration"""
        logger.info("Cleaning PostgreSQL database for fresh migration...")
        
        try:
            # Use autocommit mode for cleaning operations
            engine = create_engine(self.postgresql_url, isolation_level="AUTOCOMMIT")
            
            # Get all table names
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename NOT LIKE 'pg_%'
                    AND tablename NOT LIKE 'sql_%'
                """))
                tables = [row[0] for row in result.fetchall()]
                
                if tables:
                    logger.info(f"Found {len(tables)} tables to clean")
                    
                    # Truncate all tables in reverse order to handle dependencies
                    for table in reversed(tables):
                        try:
                            conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                            logger.info(f"Truncated table: {table}")
                        except Exception as e:
                            logger.warning(f"Failed to truncate table {table}: {e}")
                    
                    # Reset sequences
                    for table in tables:
                        try:
                            # Check if table has an id column with sequence
                            seq_result = conn.execute(text(f"""
                                SELECT pg_get_serial_sequence('{table}', 'id')
                            """))
                            sequence_name = seq_result.fetchone()
                            if sequence_name and sequence_name[0]:
                                conn.execute(text(f"SELECT setval('{sequence_name[0]}', 1, false)"))
                                logger.info(f"Reset sequence for table: {table}")
                        except Exception as e:
                            logger.warning(f"Failed to reset sequence for table {table}: {e}")
                
                logger.info("PostgreSQL database cleaned successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to clean PostgreSQL database: {e}")
            return False
    
    def execute_migration(self) -> dict:
        """Execute the complete data migration"""
        logger.info("Starting complete data migration...")
        
        try:
            # Setup migration configuration
            config = MigrationConfig(
                sqlite_url=self.sqlite_url,
                postgresql_url=self.postgresql_url,
                backup_dir="migration_backups",
                batch_size=100,  # Smaller batch size for better error handling
                validate_data=True,
                create_rollback=True,
                preserve_ids=True
            )
            
            # Create migrator instance
            migrator = DatabaseMigrator(config)
            
            # Execute migration
            migration_report = migrator.migrate_data()
            
            # Save migration report
            report_file = f"migration_execution_report_{self.migration_id}.json"
            with open(report_file, 'w') as f:
                # Convert datetime objects to strings for JSON serialization
                report_dict = {
                    'start_time': migration_report.start_time.isoformat() if migration_report.start_time else None,
                    'end_time': migration_report.end_time.isoformat() if migration_report.end_time else None,
                    'total_tables': migration_report.total_tables,
                    'successful_tables': migration_report.successful_tables,
                    'failed_tables': migration_report.failed_tables,
                    'total_records': migration_report.total_records,
                    'migrated_records': migration_report.migrated_records,
                    'errors': migration_report.errors,
                    'rollback_available': migration_report.rollback_available,
                    'table_results': [
                        {
                            'table_name': result.table_name,
                            'source_count': result.source_count,
                            'migrated_count': result.migrated_count,
                            'errors': result.errors,
                            'duration_seconds': result.duration_seconds,
                            'success': result.success
                        }
                        for result in migration_report.table_results
                    ]
                }
                json.dump(report_dict, f, indent=2)
            
            logger.info(f"Migration report saved to: {report_file}")
            return report_dict
            
        except Exception as e:
            logger.error(f"Migration execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_tables': 0,
                'successful_tables': 0,
                'failed_tables': 0,
                'total_records': 0,
                'migrated_records': 0
            }
    
    def validate_data_integrity(self) -> dict:
        """Validate data integrity after migration"""
        logger.info("Validating data integrity after migration...")
        
        validation_results = {
            'overall_success': True,
            'table_comparisons': {},
            'integrity_checks': {},
            'errors': []
        }
        
        try:
            sqlite_engine = create_engine(self.sqlite_url)
            postgresql_engine = create_engine(self.postgresql_url)
            
            # Get list of tables to validate
            with sqlite_engine.connect() as sqlite_conn:
                result = sqlite_conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ))
                sqlite_tables = [row[0] for row in result.fetchall()]
            
            with postgresql_engine.connect() as pg_conn:
                result = pg_conn.execute(text("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public'
                """))
                pg_tables = [row[0] for row in result.fetchall()]
            
            # Compare record counts for common tables
            common_tables = set(sqlite_tables) & set(pg_tables)
            logger.info(f"Validating {len(common_tables)} common tables")
            
            for table in common_tables:
                try:
                    # Get SQLite count
                    with sqlite_engine.connect() as sqlite_conn:
                        result = sqlite_conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        sqlite_count = result.fetchone()[0]
                    
                    # Get PostgreSQL count
                    with postgresql_engine.connect() as pg_conn:
                        result = pg_conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        pg_count = result.fetchone()[0]
                    
                    validation_results['table_comparisons'][table] = {
                        'sqlite_count': sqlite_count,
                        'postgresql_count': pg_count,
                        'match': sqlite_count == pg_count,
                        'difference': abs(sqlite_count - pg_count)
                    }
                    
                    if sqlite_count != pg_count:
                        validation_results['overall_success'] = False
                        error_msg = f"Table {table}: SQLite has {sqlite_count} records, PostgreSQL has {pg_count}"
                        validation_results['errors'].append(error_msg)
                        logger.warning(error_msg)
                    else:
                        logger.info(f"Table {table}: Record counts match ({sqlite_count})")
                        
                except Exception as e:
                    error_msg = f"Failed to validate table {table}: {e}"
                    validation_results['errors'].append(error_msg)
                    logger.error(error_msg)
            
            # Check referential integrity
            logger.info("Checking referential integrity...")
            try:
                with postgresql_engine.connect() as pg_conn:
                    # Check for foreign key constraint violations
                    result = pg_conn.execute(text("""
                        SELECT 
                            tc.table_name,
                            kcu.column_name,
                            ccu.table_name AS foreign_table_name,
                            ccu.column_name AS foreign_column_name,
                            tc.constraint_name
                        FROM 
                            information_schema.table_constraints AS tc 
                            JOIN information_schema.key_column_usage AS kcu
                              ON tc.constraint_name = kcu.constraint_name
                            JOIN information_schema.constraint_column_usage AS ccu
                              ON ccu.constraint_name = tc.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = 'public'
                    """))
                    
                    foreign_keys = result.fetchall()
                    integrity_issues = 0
                    
                    for fk in foreign_keys:
                        table_name, column_name, foreign_table, foreign_column, constraint_name = fk
                        
                        # Check for orphaned records
                        check_query = text(f"""
                            SELECT COUNT(*) FROM {table_name} t1
                            LEFT JOIN {foreign_table} t2 ON t1.{column_name} = t2.{foreign_column}
                            WHERE t1.{column_name} IS NOT NULL AND t2.{foreign_column} IS NULL
                        """)
                        
                        try:
                            result = pg_conn.execute(check_query)
                            orphaned_count = result.fetchone()[0]
                            
                            if orphaned_count > 0:
                                integrity_issues += 1
                                error_msg = f"Foreign key constraint {constraint_name} violated: {orphaned_count} orphaned records"
                                validation_results['errors'].append(error_msg)
                                logger.warning(error_msg)
                        except Exception as check_error:
                            logger.warning(f"Failed to check constraint {constraint_name}: {check_error}")
                    
                    validation_results['integrity_checks'] = {
                        'foreign_keys_checked': len(foreign_keys),
                        'integrity_issues': integrity_issues,
                        'all_constraints_valid': integrity_issues == 0
                    }
                    
                    if integrity_issues > 0:
                        validation_results['overall_success'] = False
                        
            except Exception as e:
                error_msg = f"Referential integrity check failed: {e}"
                validation_results['errors'].append(error_msg)
                logger.error(error_msg)
            
            logger.info(f"Data integrity validation completed. Overall success: {validation_results['overall_success']}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Data integrity validation failed: {e}")
            return {
                'overall_success': False,
                'errors': [f"Validation error: {e}"],
                'table_comparisons': {},
                'integrity_checks': {}
            }
    
    def test_application_functionality(self) -> dict:
        """Test all application endpoints and functionality"""
        logger.info("Testing application functionality with PostgreSQL backend...")
        
        test_results = {
            'overall_success': True,
            'test_categories': {},
            'errors': []
        }
        
        try:
            # Test database connection
            logger.info("Testing database connection...")
            try:
                from backend.database import get_db
                db_gen = get_db()
                session = next(db_gen)
                # Simple query to test connection
                result = session.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1
                session.close()
                    
                test_results['test_categories']['database_connection'] = {
                    'success': True,
                    'message': 'Database connection successful'
                }
                logger.info("Database connection test passed")
            except Exception as e:
                test_results['overall_success'] = False
                error_msg = f"Database connection test failed: {e}"
                test_results['errors'].append(error_msg)
                test_results['test_categories']['database_connection'] = {
                    'success': False,
                    'message': error_msg
                }
                logger.error(error_msg)
            
            # Test model operations
            logger.info("Testing model operations...")
            try:
                from backend.unified_models import UnifiedUser
                from backend.database import get_db
                
                db_gen = get_db()
                session = next(db_gen)
                # Test query
                users = session.query(UnifiedUser).limit(5).all()
                user_count = session.query(UnifiedUser).count()
                session.close()
                    
                test_results['test_categories']['model_operations'] = {
                    'success': True,
                    'message': f'Model operations successful. Found {user_count} users'
                }
                logger.info(f"Model operations test passed. Found {user_count} users")
            except Exception as e:
                test_results['overall_success'] = False
                error_msg = f"Model operations test failed: {e}"
                test_results['errors'].append(error_msg)
                test_results['test_categories']['model_operations'] = {
                    'success': False,
                    'message': error_msg
                }
                logger.error(error_msg)
            
            # Test authentication functionality
            logger.info("Testing authentication functionality...")
            try:
                # Run authentication tests
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    "tests/test_postgresql_migration.py::test_authentication_functionality",
                    "-v", "--tb=short"
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    test_results['test_categories']['authentication'] = {
                        'success': True,
                        'message': 'Authentication tests passed'
                    }
                    logger.info("Authentication functionality test passed")
                else:
                    test_results['overall_success'] = False
                    error_msg = f"Authentication tests failed: {result.stderr}"
                    test_results['errors'].append(error_msg)
                    test_results['test_categories']['authentication'] = {
                        'success': False,
                        'message': error_msg
                    }
                    logger.error(error_msg)
                    
            except subprocess.TimeoutExpired:
                test_results['overall_success'] = False
                error_msg = "Authentication tests timed out"
                test_results['errors'].append(error_msg)
                test_results['test_categories']['authentication'] = {
                    'success': False,
                    'message': error_msg
                }
                logger.error(error_msg)
            except Exception as e:
                test_results['overall_success'] = False
                error_msg = f"Authentication test execution failed: {e}"
                test_results['errors'].append(error_msg)
                test_results['test_categories']['authentication'] = {
                    'success': False,
                    'message': error_msg
                }
                logger.error(error_msg)
            
            # Test admin dashboard functionality
            logger.info("Testing admin dashboard functionality...")
            try:
                # Run admin dashboard tests
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    "tests/test_postgresql_migration.py::test_admin_dashboard_functionality",
                    "-v", "--tb=short"
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    test_results['test_categories']['admin_dashboard'] = {
                        'success': True,
                        'message': 'Admin dashboard tests passed'
                    }
                    logger.info("Admin dashboard functionality test passed")
                else:
                    test_results['overall_success'] = False
                    error_msg = f"Admin dashboard tests failed: {result.stderr}"
                    test_results['errors'].append(error_msg)
                    test_results['test_categories']['admin_dashboard'] = {
                        'success': False,
                        'message': error_msg
                    }
                    logger.error(error_msg)
                    
            except subprocess.TimeoutExpired:
                test_results['overall_success'] = False
                error_msg = "Admin dashboard tests timed out"
                test_results['errors'].append(error_msg)
                test_results['test_categories']['admin_dashboard'] = {
                    'success': False,
                    'message': error_msg
                }
                logger.error(error_msg)
            except Exception as e:
                test_results['overall_success'] = False
                error_msg = f"Admin dashboard test execution failed: {e}"
                test_results['errors'].append(error_msg)
                test_results['test_categories']['admin_dashboard'] = {
                    'success': False,
                    'message': error_msg
                }
                logger.error(error_msg)
            
            logger.info(f"Application functionality testing completed. Overall success: {test_results['overall_success']}")
            return test_results
            
        except Exception as e:
            logger.error(f"Application functionality testing failed: {e}")
            return {
                'overall_success': False,
                'errors': [f"Testing error: {e}"],
                'test_categories': {}
            }
    
    def generate_final_report(self, migration_report: dict, validation_results: dict, test_results: dict) -> dict:
        """Generate final migration execution report"""
        logger.info("Generating final migration execution report...")
        
        final_report = {
            'migration_id': self.migration_id,
            'execution_time': datetime.now().isoformat(),
            'overall_success': (
                migration_report.get('successful_tables', 0) > 0 and
                migration_report.get('failed_tables', 0) == 0 and
                validation_results.get('overall_success', False) and
                test_results.get('overall_success', False)
            ),
            'migration_summary': {
                'total_tables': migration_report.get('total_tables', 0),
                'successful_tables': migration_report.get('successful_tables', 0),
                'failed_tables': migration_report.get('failed_tables', 0),
                'total_records': migration_report.get('total_records', 0),
                'migrated_records': migration_report.get('migrated_records', 0),
                'migration_success': migration_report.get('successful_tables', 0) > 0 and migration_report.get('failed_tables', 0) == 0
            },
            'validation_summary': {
                'data_integrity_valid': validation_results.get('overall_success', False),
                'table_comparisons': len(validation_results.get('table_comparisons', {})),
                'integrity_checks': validation_results.get('integrity_checks', {})
            },
            'functionality_summary': {
                'all_tests_passed': test_results.get('overall_success', False),
                'test_categories': test_results.get('test_categories', {})
            },
            'detailed_results': {
                'migration_report': migration_report,
                'validation_results': validation_results,
                'test_results': test_results
            },
            'recommendations': []
        }
        
        # Add recommendations based on results
        if not final_report['overall_success']:
            if migration_report.get('failed_tables', 0) > 0:
                final_report['recommendations'].append(
                    "Review migration errors and re-run migration for failed tables"
                )
            
            if not validation_results.get('overall_success', False):
                final_report['recommendations'].append(
                    "Investigate data integrity issues and fix inconsistencies"
                )
            
            if not test_results.get('overall_success', False):
                final_report['recommendations'].append(
                    "Fix application functionality issues before deploying to production"
                )
        else:
            final_report['recommendations'].append(
                "Migration completed successfully. Application is ready for PostgreSQL deployment."
            )
        
        # Save final report
        report_file = f"final_migration_execution_report_{self.migration_id}.json"
        with open(report_file, 'w') as f:
            json.dump(final_report, f, indent=2)
        
        logger.info(f"Final migration execution report saved to: {report_file}")
        return final_report
    
    def execute_complete_migration(self) -> dict:
        """Execute the complete migration process"""
        logger.info("Starting complete migration execution process...")
        
        try:
            # Check prerequisites
            if not self.check_prerequisites():
                return {
                    'success': False,
                    'error': 'Prerequisites not met',
                    'migration_id': self.migration_id
                }
            
            # Clean PostgreSQL database
            if not self.clean_postgresql_database():
                return {
                    'success': False,
                    'error': 'Failed to clean PostgreSQL database',
                    'migration_id': self.migration_id
                }
            
            # Execute migration
            migration_report = self.execute_migration()
            
            # Validate data integrity
            validation_results = self.validate_data_integrity()
            
            # Test application functionality
            test_results = self.test_application_functionality()
            
            # Generate final report
            final_report = self.generate_final_report(
                migration_report, validation_results, test_results
            )
            
            logger.info(f"Complete migration execution finished. Success: {final_report['overall_success']}")
            return final_report
            
        except Exception as e:
            logger.error(f"Complete migration execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'migration_id': self.migration_id
            }

def main():
    """Main execution function"""
    print("=" * 80)
    print("AI Agent PostgreSQL Migration - Complete Execution")
    print("=" * 80)
    
    try:
        executor = CompleteMigrationExecutor()
        result = executor.execute_complete_migration()
        
        print("\n" + "=" * 80)
        print("MIGRATION EXECUTION SUMMARY")
        print("=" * 80)
        
        if result.get('overall_success', False):
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print(f"Migration ID: {result.get('migration_id', 'N/A')}")
            
            migration_summary = result.get('migration_summary', {})
            print(f"Tables migrated: {migration_summary.get('successful_tables', 0)}/{migration_summary.get('total_tables', 0)}")
            print(f"Records migrated: {migration_summary.get('migrated_records', 0)}/{migration_summary.get('total_records', 0)}")
            
            validation_summary = result.get('validation_summary', {})
            print(f"Data integrity: {'✅ Valid' if validation_summary.get('data_integrity_valid', False) else '❌ Issues found'}")
            
            functionality_summary = result.get('functionality_summary', {})
            print(f"Application tests: {'✅ All passed' if functionality_summary.get('all_tests_passed', False) else '❌ Some failed'}")
            
        else:
            print("❌ MIGRATION FAILED OR INCOMPLETE")
            print(f"Migration ID: {result.get('migration_id', 'N/A')}")
            
            if 'error' in result:
                print(f"Error: {result['error']}")
            
            # Show recommendations
            recommendations = result.get('recommendations', [])
            if recommendations:
                print("\nRecommendations:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"{i}. {rec}")
        
        print("\n" + "=" * 80)
        return 0 if result.get('overall_success', False) else 1
        
    except Exception as e:
        print(f"❌ EXECUTION FAILED: {e}")
        logger.error(f"Main execution failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())