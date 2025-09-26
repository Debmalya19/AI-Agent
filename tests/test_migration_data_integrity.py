#!/usr/bin/env python3
"""
PostgreSQL Migration Data Integrity Tests

Comprehensive data integrity validation tests for the migration process.
Tests data consistency, referential integrity, and migration accuracy.

Requirements: 5.4 (Data integrity validation tests)
"""

import os
import sys
import pytest
import tempfile
import shutil
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple, Optional
from decimal import Decimal

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect, func
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Import application modules
from backend.database import create_database_engine, Base
from backend.unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedTicketComment, UnifiedUserSession,
    UnifiedChatSession, UnifiedChatMessage, TicketStatus, TicketPriority, UserRole
)
from scripts.migrate_to_postgresql import DatabaseMigrator, MigrationConfig

load_dotenv()

class DataIntegrityValidator:
    """Data integrity validation utility"""
    
    def __init__(self, source_engine, target_engine):
        self.source_engine = source_engine
        self.target_engine = target_engine
        self.validation_results = {}
    
    def validate_table_counts(self, table_name: str) -> Dict[str, Any]:
        """Validate record counts between source and target"""
        try:
            # Get source count
            with self.source_engine.connect() as conn:
                source_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                source_count = source_result.fetchone()[0]
            
            # Get target count
            with self.target_engine.connect() as conn:
                target_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                target_count = target_result.fetchone()[0]
            
            return {
                'table_name': table_name,
                'source_count': source_count,
                'target_count': target_count,
                'count_match': source_count == target_count,
                'difference': target_count - source_count
            }
            
        except Exception as e:
            return {
                'table_name': table_name,
                'source_count': None,
                'target_count': None,
                'count_match': False,
                'error': str(e)
            }
    
    def validate_data_checksums(self, table_name: str, key_column: str = 'id') -> Dict[str, Any]:
        """Validate data integrity using checksums"""
        try:
            # Get source data checksums
            source_checksums = self._calculate_table_checksums(self.source_engine, table_name, key_column)
            
            # Get target data checksums
            target_checksums = self._calculate_table_checksums(self.target_engine, table_name, key_column)
            
            # Compare checksums
            matching_records = 0
            mismatched_records = []
            missing_in_target = []
            extra_in_target = []
            
            for key, source_checksum in source_checksums.items():
                if key in target_checksums:
                    if source_checksum == target_checksums[key]:
                        matching_records += 1
                    else:
                        mismatched_records.append({
                            'key': key,
                            'source_checksum': source_checksum,
                            'target_checksum': target_checksums[key]
                        })
                else:
                    missing_in_target.append(key)
            
            # Find extra records in target
            for key in target_checksums:
                if key not in source_checksums:
                    extra_in_target.append(key)
            
            return {
                'table_name': table_name,
                'total_source_records': len(source_checksums),
                'total_target_records': len(target_checksums),
                'matching_records': matching_records,
                'mismatched_records': len(mismatched_records),
                'missing_in_target': len(missing_in_target),
                'extra_in_target': len(extra_in_target),
                'integrity_score': (matching_records / len(source_checksums) * 100) if source_checksums else 100,
                'mismatched_details': mismatched_records[:10],  # First 10 mismatches
                'missing_details': missing_in_target[:10],  # First 10 missing
                'extra_details': extra_in_target[:10]  # First 10 extra
            }
            
        except Exception as e:
            return {
                'table_name': table_name,
                'error': str(e),
                'integrity_score': 0
            }
    
    def _calculate_table_checksums(self, engine, table_name: str, key_column: str) -> Dict[Any, str]:
        """Calculate checksums for all records in a table"""
        checksums = {}
        
        try:
            with engine.connect() as conn:
                # Get all records
                result = conn.execute(text(f"SELECT * FROM {table_name} ORDER BY {key_column}"))
                columns = list(result.keys())
                
                for row in result:
                    # Create a normalized representation of the row
                    row_dict = {}
                    for i, value in enumerate(row):
                        column_name = columns[i]
                        
                        # Normalize values for consistent checksums
                        if value is None:
                            row_dict[column_name] = "NULL"
                        elif isinstance(value, datetime):
                            # Normalize datetime to ISO format
                            row_dict[column_name] = value.isoformat()
                        elif isinstance(value, (int, float, Decimal)):
                            row_dict[column_name] = str(value)
                        else:
                            row_dict[column_name] = str(value)
                    
                    # Create checksum from sorted row data
                    row_string = json.dumps(row_dict, sort_keys=True)
                    checksum = hashlib.md5(row_string.encode()).hexdigest()
                    
                    # Use the key column value as the dictionary key
                    key_value = row_dict[key_column]
                    checksums[key_value] = checksum
            
            return checksums
            
        except Exception as e:
            print(f"Error calculating checksums for {table_name}: {e}")
            return {}
    
    def validate_foreign_key_integrity(self, table_name: str, foreign_key_column: str, 
                                     referenced_table: str, referenced_column: str = 'id') -> Dict[str, Any]:
        """Validate foreign key integrity"""
        try:
            with self.target_engine.connect() as conn:
                # Find orphaned records
                orphaned_query = text(f"""
                    SELECT COUNT(*) FROM {table_name} t1
                    LEFT JOIN {referenced_table} t2 ON t1.{foreign_key_column} = t2.{referenced_column}
                    WHERE t1.{foreign_key_column} IS NOT NULL AND t2.{referenced_column} IS NULL
                """)
                
                result = conn.execute(orphaned_query)
                orphaned_count = result.fetchone()[0]
                
                # Get total records with non-null foreign keys
                total_query = text(f"""
                    SELECT COUNT(*) FROM {table_name}
                    WHERE {foreign_key_column} IS NOT NULL
                """)
                
                result = conn.execute(total_query)
                total_with_fk = result.fetchone()[0]
                
                return {
                    'table_name': table_name,
                    'foreign_key_column': foreign_key_column,
                    'referenced_table': referenced_table,
                    'referenced_column': referenced_column,
                    'total_records_with_fk': total_with_fk,
                    'orphaned_records': orphaned_count,
                    'integrity_valid': orphaned_count == 0,
                    'integrity_percentage': ((total_with_fk - orphaned_count) / total_with_fk * 100) if total_with_fk > 0 else 100
                }
                
        except Exception as e:
            return {
                'table_name': table_name,
                'foreign_key_column': foreign_key_column,
                'error': str(e),
                'integrity_valid': False
            }
    
    def validate_data_types(self, table_name: str) -> Dict[str, Any]:
        """Validate data types between source and target"""
        try:
            # Get source schema
            source_inspector = inspect(self.source_engine)
            source_columns = {col['name']: str(col['type']) for col in source_inspector.get_columns(table_name)}
            
            # Get target schema
            target_inspector = inspect(self.target_engine)
            target_columns = {col['name']: str(col['type']) for col in target_inspector.get_columns(table_name)}
            
            # Compare schemas
            type_mismatches = []
            missing_columns = []
            extra_columns = []
            
            for col_name, source_type in source_columns.items():
                if col_name in target_columns:
                    target_type = target_columns[col_name]
                    if not self._types_compatible(source_type, target_type):
                        type_mismatches.append({
                            'column': col_name,
                            'source_type': source_type,
                            'target_type': target_type
                        })
                else:
                    missing_columns.append(col_name)
            
            for col_name in target_columns:
                if col_name not in source_columns:
                    extra_columns.append(col_name)
            
            return {
                'table_name': table_name,
                'type_mismatches': type_mismatches,
                'missing_columns': missing_columns,
                'extra_columns': extra_columns,
                'schema_compatible': len(type_mismatches) == 0 and len(missing_columns) == 0
            }
            
        except Exception as e:
            return {
                'table_name': table_name,
                'error': str(e),
                'schema_compatible': False
            }
    
    def _types_compatible(self, source_type: str, target_type: str) -> bool:
        """Check if data types are compatible"""
        # Normalize type names
        source_type = source_type.upper()
        target_type = target_type.upper()
        
        # Define compatible type mappings
        compatible_mappings = {
            'INTEGER': ['INTEGER', 'BIGINT', 'INT', 'SERIAL', 'BIGSERIAL'],
            'TEXT': ['TEXT', 'VARCHAR', 'CHAR', 'CHARACTER VARYING'],
            'REAL': ['REAL', 'FLOAT', 'DOUBLE', 'NUMERIC', 'DECIMAL'],
            'BOOLEAN': ['BOOLEAN', 'BOOL'],
            'DATETIME': ['TIMESTAMP', 'DATETIME', 'TIMESTAMP WITH TIME ZONE'],
            'JSON': ['JSON', 'JSONB']
        }
        
        # Check direct match
        if source_type == target_type:
            return True
        
        # Check compatible mappings
        for base_type, compatible_types in compatible_mappings.items():
            if any(source_type.startswith(ct) for ct in compatible_types) and \
               any(target_type.startswith(ct) for ct in compatible_types):
                return True
        
        return False


@pytest.mark.integration
class TestMigrationDataIntegrity:
    """Test data integrity during migration"""
    
    def setup_method(self):
        """Setup data integrity test environment"""
        load_dotenv()
        self.test_dir = tempfile.mkdtemp()
        self.sqlite_url = f"sqlite:///{self.test_dir}/integrity_source.db"
        self.postgresql_url = os.getenv("TEST_DATABASE_URL", 
                                       "postgresql://postgres:password@localhost:5432/test_ai_agent")
        
        # Create engines
        self.sqlite_engine = create_engine(self.sqlite_url)
        try:
            self.postgresql_engine = create_database_engine(self.postgresql_url)
            self.postgresql_available = True
        except:
            self.postgresql_engine = None
            self.postgresql_available = False
        
        if not self.postgresql_available:
            pytest.skip("PostgreSQL not available for data integrity testing")
        
        # Create tables
        Base.metadata.create_all(self.sqlite_engine)
        Base.metadata.create_all(self.postgresql_engine)
        
        # Setup comprehensive test data
        self.setup_integrity_test_data()
        
        # Initialize validator
        self.validator = DataIntegrityValidator(self.sqlite_engine, self.postgresql_engine)
    
    def teardown_method(self):
        """Cleanup data integrity test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
        # Clean PostgreSQL test data
        if self.postgresql_engine:
            try:
                with self.postgresql_engine.connect() as conn:
                    conn.execute(text("TRUNCATE TABLE unified_tickets CASCADE"))
                    conn.execute(text("TRUNCATE TABLE unified_users CASCADE"))
                    conn.commit()
            except:
                pass
    
    def setup_integrity_test_data(self):
        """Setup comprehensive test data for integrity validation"""
        # Create data in SQLite
        Session = sessionmaker(bind=self.sqlite_engine)
        session = Session()
        
        try:
            # Create users with various data types
            users = []
            for i in range(50):
                user = UnifiedUser(
                    user_id=f"integrity_user_{i:03d}",
                    username=f"integrityuser{i}",
                    email=f"integrity{i}@example.com",
                    password_hash="hashed_password_with_special_chars_!@#$%",
                    full_name=f"Integrity Test User {i} with Unicode: 测试用户",
                    role=UserRole.CUSTOMER if i % 3 != 0 else UserRole.ADMIN,
                    is_admin=(i % 3 == 0),
                    phone=f"+1-555-{i:04d}" if i % 2 == 0 else None,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                users.append(user)
            
            session.add_all(users)
            session.flush()  # Get user IDs
            
            # Create tickets with foreign key relationships
            tickets = []
            for i, user in enumerate(users[:30]):  # Create tickets for first 30 users
                ticket = UnifiedTicket(
                    ticket_id=f"INTEGRITY-{i:03d}",
                    title=f"Integrity Test Ticket {i} with Special Chars: 特殊字符",
                    description=f"Test ticket {i} with detailed description including newlines\nand special characters: !@#$%^&*()",
                    status=TicketStatus.OPEN if i % 2 == 0 else TicketStatus.RESOLVED,
                    priority=TicketPriority.HIGH if i % 3 == 0 else TicketPriority.MEDIUM,
                    customer_id=user.id,
                    assigned_agent_id=users[0].id if i % 5 == 0 else None,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                tickets.append(ticket)
            
            session.add_all(tickets)
            session.commit()
            
        finally:
            session.close()
        
        # Migrate data to PostgreSQL using the migration script
        self.perform_test_migration()
    
    def perform_test_migration(self):
        """Perform migration for testing"""
        config = MigrationConfig(
            sqlite_url=self.sqlite_url,
            postgresql_url=self.postgresql_url,
            batch_size=10,
            validate_data=True
        )
        
        migrator = DatabaseMigrator(config)
        migrator.setup_connections()
        
        # Export and import data
        for table_name in ['unified_users', 'unified_tickets']:
            data = migrator.export_table_data(table_name)
            if data:
                migrator.import_table_data(table_name, data)
    
    def test_record_count_integrity(self):
        """Test that all records are migrated correctly"""
        # Validate user counts
        user_validation = self.validator.validate_table_counts('unified_users')
        assert user_validation['count_match'], f"User count mismatch: {user_validation}"
        assert user_validation['source_count'] == 50
        assert user_validation['target_count'] == 50
        
        # Validate ticket counts
        ticket_validation = self.validator.validate_table_counts('unified_tickets')
        assert ticket_validation['count_match'], f"Ticket count mismatch: {ticket_validation}"
        assert ticket_validation['source_count'] == 30
        assert ticket_validation['target_count'] == 30
    
    def test_data_checksum_integrity(self):
        """Test data integrity using checksums"""
        # Validate user data integrity
        user_integrity = self.validator.validate_data_checksums('unified_users', 'id')
        assert user_integrity['integrity_score'] >= 95, f"User data integrity too low: {user_integrity['integrity_score']}%"
        assert user_integrity['mismatched_records'] <= 2, f"Too many mismatched user records: {user_integrity['mismatched_records']}"
        
        # Validate ticket data integrity
        ticket_integrity = self.validator.validate_data_checksums('unified_tickets', 'id')
        assert ticket_integrity['integrity_score'] >= 95, f"Ticket data integrity too low: {ticket_integrity['integrity_score']}%"
        assert ticket_integrity['mismatched_records'] <= 1, f"Too many mismatched ticket records: {ticket_integrity['mismatched_records']}"
        
        # Log integrity results
        print(f"User data integrity: {user_integrity['integrity_score']:.1f}%")
        print(f"Ticket data integrity: {ticket_integrity['integrity_score']:.1f}%")
    
    def test_foreign_key_integrity(self):
        """Test foreign key relationships are preserved"""
        # Test ticket -> user relationship
        fk_validation = self.validator.validate_foreign_key_integrity(
            'unified_tickets', 'customer_id', 'unified_users', 'id'
        )
        
        assert fk_validation['integrity_valid'], f"Foreign key integrity failed: {fk_validation}"
        assert fk_validation['orphaned_records'] == 0, f"Found orphaned ticket records: {fk_validation['orphaned_records']}"
        assert fk_validation['integrity_percentage'] == 100, f"Foreign key integrity not 100%: {fk_validation['integrity_percentage']}%"
        
        # Test assigned agent relationship
        agent_fk_validation = self.validator.validate_foreign_key_integrity(
            'unified_tickets', 'assigned_agent_id', 'unified_users', 'id'
        )
        
        assert agent_fk_validation['integrity_valid'], f"Agent foreign key integrity failed: {agent_fk_validation}"
        assert agent_fk_validation['orphaned_records'] == 0, f"Found orphaned agent assignments: {agent_fk_validation['orphaned_records']}"
    
    def test_data_type_compatibility(self):
        """Test data type compatibility between source and target"""
        # Validate user table schema
        user_schema = self.validator.validate_data_types('unified_users')
        assert user_schema['schema_compatible'], f"User schema not compatible: {user_schema}"
        assert len(user_schema['type_mismatches']) == 0, f"User type mismatches: {user_schema['type_mismatches']}"
        
        # Validate ticket table schema
        ticket_schema = self.validator.validate_data_types('unified_tickets')
        assert ticket_schema['schema_compatible'], f"Ticket schema not compatible: {ticket_schema}"
        assert len(ticket_schema['type_mismatches']) == 0, f"Ticket type mismatches: {ticket_schema['type_mismatches']}"
    
    def test_special_character_handling(self):
        """Test that special characters are handled correctly"""
        with self.postgresql_engine.connect() as conn:
            # Check for users with special characters
            result = conn.execute(text("""
                SELECT COUNT(*) FROM unified_users 
                WHERE full_name LIKE '%测试用户%'
            """))
            unicode_users = result.fetchone()[0]
            assert unicode_users > 0, "Unicode characters not preserved in user names"
            
            # Check for tickets with special characters
            result = conn.execute(text("""
                SELECT COUNT(*) FROM unified_tickets 
                WHERE title LIKE '%特殊字符%'
            """))
            unicode_tickets = result.fetchone()[0]
            assert unicode_tickets > 0, "Unicode characters not preserved in ticket titles"
            
            # Check for special characters in descriptions
            result = conn.execute(text("""
                SELECT COUNT(*) FROM unified_tickets 
                WHERE description LIKE '%!@#$%^&*()%'
            """))
            special_char_tickets = result.fetchone()[0]
            assert special_char_tickets > 0, "Special characters not preserved in descriptions"
    
    def test_null_value_handling(self):
        """Test that NULL values are handled correctly"""
        with self.postgresql_engine.connect() as conn:
            # Check for NULL phone numbers (should exist)
            result = conn.execute(text("""
                SELECT COUNT(*) FROM unified_users 
                WHERE phone IS NULL
            """))
            null_phones = result.fetchone()[0]
            assert null_phones > 0, "NULL phone values not preserved"
            
            # Check for NULL assigned agents (should exist)
            result = conn.execute(text("""
                SELECT COUNT(*) FROM unified_tickets 
                WHERE assigned_agent_id IS NULL
            """))
            null_agents = result.fetchone()[0]
            assert null_agents > 0, "NULL assigned agent values not preserved"
    
    def test_datetime_precision(self):
        """Test that datetime values maintain precision"""
        # Get datetime values from both databases
        with self.sqlite_engine.connect() as sqlite_conn:
            sqlite_result = sqlite_conn.execute(text("""
                SELECT id, created_at FROM unified_users 
                WHERE created_at IS NOT NULL 
                ORDER BY id LIMIT 5
            """))
            sqlite_datetimes = {row[0]: row[1] for row in sqlite_result}
        
        with self.postgresql_engine.connect() as pg_conn:
            pg_result = pg_conn.execute(text("""
                SELECT id, created_at FROM unified_users 
                WHERE created_at IS NOT NULL 
                ORDER BY id LIMIT 5
            """))
            pg_datetimes = {row[0]: row[1] for row in pg_result}
        
        # Compare datetime values (allowing for small precision differences)
        for user_id in sqlite_datetimes:
            if user_id in pg_datetimes:
                sqlite_dt = sqlite_datetimes[user_id]
                pg_dt = pg_datetimes[user_id]
                
                # Convert to comparable format
                if isinstance(sqlite_dt, str):
                    sqlite_dt = datetime.fromisoformat(sqlite_dt.replace('Z', '+00:00'))
                if isinstance(pg_dt, str):
                    pg_dt = datetime.fromisoformat(pg_dt.replace('Z', '+00:00'))
                
                # Allow for small differences (up to 1 second)
                time_diff = abs((sqlite_dt - pg_dt).total_seconds())
                assert time_diff <= 1, f"Datetime precision lost for user {user_id}: {time_diff}s difference"
    
    def test_enum_value_preservation(self):
        """Test that enum values are preserved correctly"""
        with self.postgresql_engine.connect() as conn:
            # Check user roles
            result = conn.execute(text("""
                SELECT role, COUNT(*) FROM unified_users 
                GROUP BY role
            """))
            roles = dict(result.fetchall())
            
            assert 'CUSTOMER' in roles or 'customer' in roles, "Customer role not preserved"
            assert 'ADMIN' in roles or 'admin' in roles, "Admin role not preserved"
            
            # Check ticket statuses
            result = conn.execute(text("""
                SELECT status, COUNT(*) FROM unified_tickets 
                GROUP BY status
            """))
            statuses = dict(result.fetchall())
            
            assert 'open' in statuses or 'OPEN' in statuses, "Open status not preserved"
            assert 'resolved' in statuses or 'RESOLVED' in statuses, "Resolved status not preserved"
    
    def test_comprehensive_integrity_report(self):
        """Generate comprehensive integrity validation report"""
        integrity_report = {
            'timestamp': datetime.now().isoformat(),
            'tables': {}
        }
        
        # Test all tables
        for table_name in ['unified_users', 'unified_tickets']:
            table_report = {
                'count_validation': self.validator.validate_table_counts(table_name),
                'checksum_validation': self.validator.validate_data_checksums(table_name, 'id'),
                'schema_validation': self.validator.validate_data_types(table_name)
            }
            
            # Add foreign key validations for tickets
            if table_name == 'unified_tickets':
                table_report['fk_customer_validation'] = self.validator.validate_foreign_key_integrity(
                    table_name, 'customer_id', 'unified_users', 'id'
                )
                table_report['fk_agent_validation'] = self.validator.validate_foreign_key_integrity(
                    table_name, 'assigned_agent_id', 'unified_users', 'id'
                )
            
            integrity_report['tables'][table_name] = table_report
        
        # Calculate overall integrity score
        total_score = 0
        score_count = 0
        
        for table_data in integrity_report['tables'].values():
            if 'checksum_validation' in table_data and 'integrity_score' in table_data['checksum_validation']:
                total_score += table_data['checksum_validation']['integrity_score']
                score_count += 1
        
        overall_score = total_score / score_count if score_count > 0 else 0
        integrity_report['overall_integrity_score'] = overall_score
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"data_integrity_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(integrity_report, f, indent=2, default=str)
        
        print(f"\nData integrity report saved to: {report_file}")
        print(f"Overall integrity score: {overall_score:.1f}%")
        
        # Assert overall integrity
        assert overall_score >= 95, f"Overall data integrity too low: {overall_score:.1f}%"


if __name__ == "__main__":
    # Run data integrity tests
    pytest.main([__file__, "-v", "--tb=short"])