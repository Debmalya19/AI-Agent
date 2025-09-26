#!/usr/bin/env python3
"""
Comprehensive PostgreSQL Migration Script

This script migrates data from SQLite to PostgreSQL database with:
- Data export from SQLite with proper data type handling
- PostgreSQL data import with referential integrity preservation
- Data validation and integrity checking
- Migration rollback capabilities
- Detailed logging and progress tracking

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import os
import sys
import json
import logging
import hashlib
import shutil
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from dotenv import load_dotenv

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MigrationConfig:
    """Configuration for database migration"""
    sqlite_url: str
    postgresql_url: str
    backup_dir: str = "migration_backups"
    batch_size: int = 1000
    validate_data: bool = True
    create_rollback: bool = True
    preserve_ids: bool = True
    
@dataclass
class TableMigrationResult:
    """Result of migrating a single table"""
    table_name: str
    source_count: int
    migrated_count: int
    errors: List[str]
    duration_seconds: float
    success: bool
    
@dataclass
class MigrationReport:
    """Complete migration report"""
    start_time: datetime
    end_time: Optional[datetime]
    total_tables: int
    successful_tables: int
    failed_tables: int
    total_records: int
    migrated_records: int
    errors: List[str]
    table_results: List[TableMigrationResult]
    rollback_available: bool

class DatabaseMigrator:
    """Comprehensive database migration handler"""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.sqlite_engine = None
        self.postgresql_engine = None
        self.backup_path = None
        self.migration_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Data type mappings from SQLite to PostgreSQL
        self.type_mappings = {
            'INTEGER': 'INTEGER',
            'TEXT': 'TEXT',
            'REAL': 'REAL',
            'BLOB': 'BYTEA',
            'NUMERIC': 'NUMERIC',
            'VARCHAR': 'VARCHAR',
            'CHAR': 'CHAR',
            'BOOLEAN': 'BOOLEAN',
            'DATETIME': 'TIMESTAMP WITH TIME ZONE',
            'DATE': 'DATE',
            'TIME': 'TIME',
            'JSON': 'JSONB',  # Use JSONB for better performance
        }
        
        # Tables to migrate in dependency order (to handle foreign keys)
        self.migration_order = [
            # Legacy models first
            'knowledge_entries',
            'customers', 
            'users',
            'user_sessions',
            'voice_settings',
            'voice_analytics',
            'tickets',
            'ticket_comments',
            'ticket_activities',
            'orders',
            'support_intents',
            'support_responses',
            'chat_history',
            
            # Unified models
            'unified_users',
            'unified_user_sessions',
            'unified_tickets',
            'unified_ticket_comments',
            'unified_ticket_activities',
            'unified_chat_sessions',
            'unified_chat_messages',
            'unified_performance_metrics',
            'unified_customer_satisfaction',
            'unified_voice_settings',
            'unified_voice_analytics',
            'unified_knowledge_entries',
            'unified_orders',
            'unified_support_intents',
            'unified_support_responses',
            'unified_chat_history',
            'diagnostic_error_logs',
            
            # Memory models
            'enhanced_chat_history',
            'memory_context_cache',
            'tool_usage_metrics',
            'conversation_summaries',
            'memory_configuration',
            'memory_health_metrics',
            'enhanced_user_sessions',
            'data_processing_consent',
            'data_subject_rights',
        ]
    
    def setup_connections(self) -> bool:
        """Setup database connections with validation"""
        try:
            logger.info("Setting up database connections...")
            
            # Setup SQLite connection
            self.sqlite_engine = create_engine(
                self.config.sqlite_url,
                connect_args={"check_same_thread": False}
            )
            
            # Test SQLite connection
            with self.sqlite_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("SQLite connection established")
            
            # Setup PostgreSQL connection
            self.postgresql_engine = create_engine(
                self.config.postgresql_url,
                pool_size=20,
                max_overflow=30,
                pool_pre_ping=True,
                connect_args={
                    "connect_timeout": 10,
                    "application_name": "migration_script"
                }
            )
            
            # Test PostgreSQL connection
            with self.postgresql_engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"PostgreSQL connection established: {version}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup database connections: {e}")
            return False
    
    def create_backup(self) -> bool:
        """Create backup of SQLite database"""
        try:
            if not self.config.create_rollback:
                logger.info("Backup creation disabled")
                return True
                
            logger.info("Creating database backup...")
            
            # Create backup directory
            backup_dir = Path(self.config.backup_dir)
            backup_dir.mkdir(exist_ok=True)
            
            # Create timestamped backup
            sqlite_path = self.config.sqlite_url.replace("sqlite:///", "")
            if os.path.exists(sqlite_path):
                backup_filename = f"sqlite_backup_{self.migration_id}.db"
                self.backup_path = backup_dir / backup_filename
                shutil.copy2(sqlite_path, self.backup_path)
                logger.info(f"Backup created: {self.backup_path}")
                return True
            else:
                logger.warning(f"SQLite database file not found: {sqlite_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    def get_table_schema(self, engine, table_name: str) -> Optional[Dict]:
        """Get table schema information"""
        try:
            inspector = inspect(engine)
            
            if table_name not in inspector.get_table_names():
                return None
                
            columns = inspector.get_columns(table_name)
            primary_keys = inspector.get_pk_constraint(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            indexes = inspector.get_indexes(table_name)
            
            return {
                'columns': columns,
                'primary_keys': primary_keys,
                'foreign_keys': foreign_keys,
                'indexes': indexes
            }
            
        except Exception as e:
            logger.error(f"Failed to get schema for table {table_name}: {e}")
            return None
    
    def export_table_data(self, table_name: str) -> Optional[List[Dict]]:
        """Export data from SQLite table with proper type handling"""
        try:
            logger.info(f"Exporting data from table: {table_name}")
            
            with self.sqlite_engine.connect() as conn:
                # Check if table exists
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
                ), {"table_name": table_name})
                
                if not result.fetchone():
                    logger.info(f"Table {table_name} does not exist in SQLite, skipping")
                    return []
                
                # Get table data
                result = conn.execute(text(f"SELECT * FROM {table_name}"))
                columns = list(result.keys())
                rows = result.fetchall()
                
                # Convert to list of dictionaries with proper type handling
                data = []
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        column_name = columns[i]
                        
                        # Handle special data types
                        if value is not None:
                            # Convert datetime strings to proper format
                            if isinstance(value, str) and self._is_datetime_string(value):
                                try:
                                    # Parse and convert to ISO format
                                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                    row_dict[column_name] = dt.isoformat()
                                except:
                                    row_dict[column_name] = value
                            else:
                                row_dict[column_name] = value
                        else:
                            row_dict[column_name] = None
                            
                    data.append(row_dict)
                
                logger.info(f"Exported {len(data)} records from {table_name}")
                return data
                
        except Exception as e:
            logger.error(f"Failed to export data from table {table_name}: {e}")
            return None
    
    def _is_datetime_string(self, value: str) -> bool:
        """Check if string looks like a datetime"""
        datetime_patterns = [
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
        ]
        import re
        return any(re.match(pattern, value) for pattern in datetime_patterns)
    
    def import_table_data(self, table_name: str, data: List[Dict]) -> TableMigrationResult:
        """Import data to PostgreSQL table with integrity preservation"""
        start_time = datetime.now()
        errors = []
        migrated_count = 0
        
        try:
            logger.info(f"Importing {len(data)} records to table: {table_name}")
            
            if not data:
                return TableMigrationResult(
                    table_name=table_name,
                    source_count=0,
                    migrated_count=0,
                    errors=[],
                    duration_seconds=0.0,
                    success=True
                )
            
            with self.postgresql_engine.connect() as conn:
                # Check if table exists
                inspector = inspect(self.postgresql_engine)
                if table_name not in inspector.get_table_names():
                    logger.warning(f"Table {table_name} does not exist in PostgreSQL, skipping")
                    return TableMigrationResult(
                        table_name=table_name,
                        source_count=len(data),
                        migrated_count=0,
                        errors=[f"Table {table_name} does not exist in PostgreSQL"],
                        duration_seconds=(datetime.now() - start_time).total_seconds(),
                        success=False
                    )
                
                # Get table metadata
                metadata = MetaData()
                table = Table(table_name, metadata, autoload_with=self.postgresql_engine)
                
                # Process data in batches
                batch_size = self.config.batch_size
                total_batches = (len(data) + batch_size - 1) // batch_size
                
                with conn.begin() as trans:
                    for batch_num in range(total_batches):
                        start_idx = batch_num * batch_size
                        end_idx = min(start_idx + batch_size, len(data))
                        batch_data = data[start_idx:end_idx]
                        
                        try:
                            # Prepare batch for insertion
                            processed_batch = []
                            for row in batch_data:
                                processed_row = self._process_row_for_postgresql(row, table)
                                if processed_row:
                                    processed_batch.append(processed_row)
                            
                            if processed_batch:
                                # Insert batch
                                conn.execute(table.insert(), processed_batch)
                                migrated_count += len(processed_batch)
                                
                                logger.info(f"Imported batch {batch_num + 1}/{total_batches} "
                                          f"({len(processed_batch)} records) for table {table_name}")
                            
                        except Exception as batch_error:
                            error_msg = f"Batch {batch_num + 1} failed: {batch_error}"
                            errors.append(error_msg)
                            logger.error(error_msg)
                            
                            # Try individual row insertion for failed batch
                            for row in batch_data:
                                try:
                                    processed_row = self._process_row_for_postgresql(row, table)
                                    if processed_row:
                                        conn.execute(table.insert(), [processed_row])
                                        migrated_count += 1
                                except Exception as row_error:
                                    error_msg = f"Row insertion failed: {row_error}"
                                    errors.append(error_msg)
                                    logger.warning(error_msg)
                
                # Update sequences for auto-increment columns
                self._update_sequences(conn, table_name, data)
                
            duration = (datetime.now() - start_time).total_seconds()
            success = migrated_count > 0 or len(data) == 0
            
            logger.info(f"Completed importing table {table_name}: "
                       f"{migrated_count}/{len(data)} records in {duration:.2f}s")
            
            return TableMigrationResult(
                table_name=table_name,
                source_count=len(data),
                migrated_count=migrated_count,
                errors=errors,
                duration_seconds=duration,
                success=success
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = f"Failed to import table {table_name}: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
            
            return TableMigrationResult(
                table_name=table_name,
                source_count=len(data),
                migrated_count=migrated_count,
                errors=errors,
                duration_seconds=duration,
                success=False
            )
    
    def _process_row_for_postgresql(self, row: Dict, table: Table) -> Optional[Dict]:
        """Process row data for PostgreSQL compatibility"""
        try:
            processed_row = {}
            
            for column in table.columns:
                column_name = column.name
                value = row.get(column_name)
                
                if value is None:
                    processed_row[column_name] = None
                    continue
                
                # Handle different data types
                column_type = str(column.type)
                
                if 'TIMESTAMP' in column_type.upper():
                    # Handle datetime conversion
                    if isinstance(value, str):
                        try:
                            # Parse datetime string
                            if 'T' in value:
                                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            else:
                                dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                                dt = dt.replace(tzinfo=timezone.utc)
                            processed_row[column_name] = dt
                        except:
                            processed_row[column_name] = value
                    else:
                        processed_row[column_name] = value
                        
                elif 'JSONB' in column_type.upper() or 'JSON' in column_type.upper():
                    # Handle JSON data
                    if isinstance(value, str):
                        try:
                            processed_row[column_name] = json.loads(value)
                        except:
                            processed_row[column_name] = value
                    else:
                        processed_row[column_name] = value
                        
                elif 'BOOLEAN' in column_type.upper():
                    # Handle boolean conversion
                    if isinstance(value, str):
                        processed_row[column_name] = value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        processed_row[column_name] = bool(value)
                        
                else:
                    processed_row[column_name] = value
            
            return processed_row
            
        except Exception as e:
            logger.warning(f"Failed to process row: {e}")
            return None
    
    def _update_sequences(self, conn, table_name: str, data: List[Dict]):
        """Update PostgreSQL sequences for auto-increment columns"""
        try:
            if not data:
                return
                
            # Get table schema to find auto-increment columns
            inspector = inspect(self.postgresql_engine)
            columns = inspector.get_columns(table_name)
            
            for column in columns:
                if column.get('autoincrement') or 'nextval' in str(column.get('default', '')):
                    column_name = column['name']
                    
                    # Find maximum value in the imported data
                    max_value = 0
                    for row in data:
                        if column_name in row and row[column_name] is not None:
                            try:
                                max_value = max(max_value, int(row[column_name]))
                            except (ValueError, TypeError):
                                continue
                    
                    if max_value > 0:
                        # Update sequence
                        sequence_name = f"{table_name}_{column_name}_seq"
                        try:
                            conn.execute(text(
                                f"SELECT setval('{sequence_name}', {max_value}, true)"
                            ))
                            logger.info(f"Updated sequence {sequence_name} to {max_value}")
                        except Exception as seq_error:
                            logger.warning(f"Failed to update sequence {sequence_name}: {seq_error}")
                            
        except Exception as e:
            logger.warning(f"Failed to update sequences for table {table_name}: {e}")
    
    def validate_migration(self, table_results: List[TableMigrationResult]) -> Dict[str, Any]:
        """Validate migration results and data integrity"""
        logger.info("Validating migration results...")
        
        validation_results = {
            'overall_success': True,
            'table_validations': {},
            'integrity_checks': {},
            'errors': []
        }
        
        try:
            for result in table_results:
                if not result.success:
                    validation_results['overall_success'] = False
                    validation_results['errors'].extend(result.errors)
                
                # Validate record counts
                table_validation = {
                    'source_count': result.source_count,
                    'migrated_count': result.migrated_count,
                    'success_rate': (result.migrated_count / result.source_count * 100) 
                                   if result.source_count > 0 else 100,
                    'errors': result.errors
                }
                
                validation_results['table_validations'][result.table_name] = table_validation
                
                # Check for significant data loss
                if result.source_count > 0:
                    success_rate = result.migrated_count / result.source_count
                    if success_rate < 0.95:  # Less than 95% success rate
                        validation_results['overall_success'] = False
                        validation_results['errors'].append(
                            f"Table {result.table_name} has low success rate: {success_rate:.2%}"
                        )
            
            # Perform referential integrity checks
            integrity_results = self._check_referential_integrity()
            validation_results['integrity_checks'] = integrity_results
            
            if not integrity_results.get('all_constraints_valid', True):
                validation_results['overall_success'] = False
                validation_results['errors'].extend(
                    integrity_results.get('constraint_errors', [])
                )
            
            logger.info(f"Migration validation completed. Overall success: {validation_results['overall_success']}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            validation_results['overall_success'] = False
            validation_results['errors'].append(f"Validation error: {e}")
            return validation_results
    
    def _check_referential_integrity(self) -> Dict[str, Any]:
        """Check referential integrity constraints"""
        try:
            logger.info("Checking referential integrity...")
            
            integrity_results = {
                'all_constraints_valid': True,
                'constraint_errors': [],
                'foreign_key_checks': {}
            }
            
            with self.postgresql_engine.connect() as conn:
                # Get all foreign key constraints
                result = conn.execute(text("""
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
                
                for fk in foreign_keys:
                    table_name = fk[0]
                    column_name = fk[1]
                    foreign_table = fk[2]
                    foreign_column = fk[3]
                    constraint_name = fk[4]
                    
                    # Check for orphaned records
                    check_query = text(f"""
                        SELECT COUNT(*) FROM {table_name} t1
                        LEFT JOIN {foreign_table} t2 ON t1.{column_name} = t2.{foreign_column}
                        WHERE t1.{column_name} IS NOT NULL AND t2.{foreign_column} IS NULL
                    """)
                    
                    try:
                        result = conn.execute(check_query)
                        orphaned_count = result.fetchone()[0]
                        
                        integrity_results['foreign_key_checks'][constraint_name] = {
                            'table': table_name,
                            'column': column_name,
                            'foreign_table': foreign_table,
                            'foreign_column': foreign_column,
                            'orphaned_records': orphaned_count,
                            'valid': orphaned_count == 0
                        }
                        
                        if orphaned_count > 0:
                            integrity_results['all_constraints_valid'] = False
                            error_msg = (f"Foreign key constraint {constraint_name} violated: "
                                       f"{orphaned_count} orphaned records in {table_name}.{column_name}")
                            integrity_results['constraint_errors'].append(error_msg)
                            logger.warning(error_msg)
                            
                    except Exception as check_error:
                        error_msg = f"Failed to check constraint {constraint_name}: {check_error}"
                        integrity_results['constraint_errors'].append(error_msg)
                        logger.warning(error_msg)
            
            return integrity_results
            
        except Exception as e:
            logger.error(f"Referential integrity check failed: {e}")
            return {
                'all_constraints_valid': False,
                'constraint_errors': [f"Integrity check error: {e}"],
                'foreign_key_checks': {}
            }
    
    def create_rollback_script(self, migration_report: MigrationReport) -> bool:
        """Create rollback script for migration reversal"""
        try:
            if not self.config.create_rollback:
                logger.info("Rollback script creation disabled")
                return True
                
            logger.info("Creating rollback script...")
            
            rollback_dir = Path(self.config.backup_dir)
            rollback_dir.mkdir(exist_ok=True)
            
            rollback_script_path = rollback_dir / f"rollback_{self.migration_id}.sql"
            
            with open(rollback_script_path, 'w') as f:
                f.write("-- PostgreSQL Migration Rollback Script\n")
                f.write(f"-- Generated: {datetime.now().isoformat()}\n")
                f.write(f"-- Migration ID: {self.migration_id}\n\n")
                
                # Add commands to truncate tables in reverse order
                f.write("-- Truncate tables in reverse dependency order\n")
                for table_name in reversed(self.migration_order):
                    # Only include tables that were successfully migrated
                    table_result = next((r for r in migration_report.table_results 
                                       if r.table_name == table_name), None)
                    if table_result and table_result.success and table_result.migrated_count > 0:
                        f.write(f"TRUNCATE TABLE {table_name} CASCADE;\n")
                
                f.write("\n-- Reset sequences\n")
                for table_name in self.migration_order:
                    table_result = next((r for r in migration_report.table_results 
                                       if r.table_name == table_name), None)
                    if table_result and table_result.success:
                        f.write(f"-- Reset sequences for {table_name}\n")
                        f.write(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), 1, false);\n")
                
                f.write(f"\n-- Restore from backup: {self.backup_path}\n")
                f.write("-- Use appropriate tools to restore SQLite data\n")
            
            logger.info(f"Rollback script created: {rollback_script_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create rollback script: {e}")
            return False
    
    def migrate_data(self) -> MigrationReport:
        """Execute complete data migration"""
        start_time = datetime.now()
        logger.info(f"Starting database migration at {start_time}")
        
        # Initialize report
        report = MigrationReport(
            start_time=start_time,
            end_time=None,
            total_tables=0,
            successful_tables=0,
            failed_tables=0,
            total_records=0,
            migrated_records=0,
            errors=[],
            table_results=[],
            rollback_available=False
        )
        
        try:
            # Setup connections
            if not self.setup_connections():
                report.errors.append("Failed to setup database connections")
                return report
            
            # Create backup
            if not self.create_backup():
                report.errors.append("Failed to create backup")
                if self.config.create_rollback:
                    return report
            else:
                report.rollback_available = True
            
            # Migrate tables in dependency order
            for table_name in self.migration_order:
                logger.info(f"Processing table: {table_name}")
                
                # Export data from SQLite
                data = self.export_table_data(table_name)
                if data is None:
                    error_msg = f"Failed to export data from table {table_name}"
                    report.errors.append(error_msg)
                    continue
                
                # Import data to PostgreSQL
                result = self.import_table_data(table_name, data)
                report.table_results.append(result)
                report.total_tables += 1
                report.total_records += result.source_count
                report.migrated_records += result.migrated_count
                
                if result.success:
                    report.successful_tables += 1
                else:
                    report.failed_tables += 1
                    report.errors.extend(result.errors)
            
            # Validate migration
            if self.config.validate_data:
                validation_results = self.validate_migration(report.table_results)
                if not validation_results['overall_success']:
                    report.errors.extend(validation_results['errors'])
            
            # Create rollback script
            if self.config.create_rollback:
                if not self.create_rollback_script(report):
                    report.errors.append("Failed to create rollback script")
            
            report.end_time = datetime.now()
            duration = (report.end_time - report.start_time).total_seconds()
            
            logger.info(f"Migration completed in {duration:.2f} seconds")
            logger.info(f"Tables: {report.successful_tables}/{report.total_tables} successful")
            logger.info(f"Records: {report.migrated_records}/{report.total_records} migrated")
            
            return report
            
        except Exception as e:
            report.end_time = datetime.now()
            error_msg = f"Migration failed with error: {e}"
            report.errors.append(error_msg)
            logger.error(error_msg)
            return report
    
    def generate_migration_report(self, report: MigrationReport) -> str:
        """Generate detailed migration report"""
        report_lines = [
            "=" * 80,
            "DATABASE MIGRATION REPORT",
            "=" * 80,
            f"Migration ID: {self.migration_id}",
            f"Start Time: {report.start_time}",
            f"End Time: {report.end_time}",
            f"Duration: {(report.end_time - report.start_time).total_seconds():.2f} seconds" if report.end_time else "N/A",
            "",
            "SUMMARY:",
            f"  Total Tables: {report.total_tables}",
            f"  Successful Tables: {report.successful_tables}",
            f"  Failed Tables: {report.failed_tables}",
            f"  Total Records: {report.total_records}",
            f"  Migrated Records: {report.migrated_records}",
            f"  Success Rate: {(report.migrated_records / report.total_records * 100):.2f}%" if report.total_records > 0 else "N/A",
            f"  Rollback Available: {'Yes' if report.rollback_available else 'No'}",
            "",
            "TABLE RESULTS:",
        ]
        
        for result in report.table_results:
            status = "SUCCESS" if result.success else "FAILED"
            success_rate = (result.migrated_count / result.source_count * 100) if result.source_count > 0 else 100
            
            report_lines.extend([
                f"  {result.table_name}:",
                f"    Status: {status}",
                f"    Records: {result.migrated_count}/{result.source_count} ({success_rate:.1f}%)",
                f"    Duration: {result.duration_seconds:.2f}s",
                f"    Errors: {len(result.errors)}",
            ])
            
            if result.errors:
                for error in result.errors[:3]:  # Show first 3 errors
                    report_lines.append(f"      - {error}")
                if len(result.errors) > 3:
                    report_lines.append(f"      ... and {len(result.errors) - 3} more errors")
            
            report_lines.append("")
        
        if report.errors:
            report_lines.extend([
                "OVERALL ERRORS:",
                *[f"  - {error}" for error in report.errors],
                ""
            ])
        
        report_lines.extend([
            "BACKUP INFORMATION:",
            f"  Backup Path: {self.backup_path}" if self.backup_path else "  No backup created",
            f"  Rollback Script: migration_backups/rollback_{self.migration_id}.sql" if self.config.create_rollback else "  No rollback script created",
            "",
            "=" * 80
        ])
        
        return "\n".join(report_lines)

def main():
    """Main migration execution function"""
    load_dotenv()
    
    # Configuration
    config = MigrationConfig(
        sqlite_url="sqlite:///ai_agent.db",
        postgresql_url=os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/ai_agent"),
        backup_dir="migration_backups",
        batch_size=1000,
        validate_data=True,
        create_rollback=True,
        preserve_ids=True
    )
    
    # Create migrator
    migrator = DatabaseMigrator(config)
    
    # Execute migration
    logger.info("Starting PostgreSQL migration...")
    report = migrator.migrate_data()
    
    # Generate and save report
    report_text = migrator.generate_migration_report(report)
    
    # Save report to file
    report_path = f"migration_report_{migrator.migration_id}.txt"
    with open(report_path, 'w') as f:
        f.write(report_text)
    
    # Print report
    print(report_text)
    
    # Save JSON report for programmatic access
    json_report_path = f"migration_report_{migrator.migration_id}.json"
    with open(json_report_path, 'w') as f:
        json.dump(asdict(report), f, indent=2, default=str)
    
    logger.info(f"Migration report saved to: {report_path}")
    logger.info(f"JSON report saved to: {json_report_path}")
    
    # Exit with appropriate code
    if report.successful_tables == report.total_tables and not report.errors:
        logger.info("Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("Migration completed with errors!")
        sys.exit(1)

if __name__ == "__main__":
    main()