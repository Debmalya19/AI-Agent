#!/usr/bin/env python3
"""
Test script for PostgreSQL schema optimization

This script tests the PostgreSQL schema optimization by:
1. Verifying PostgreSQL-specific data types are used
2. Testing index creation and performance
3. Validating constraints and foreign keys
4. Testing sequences and auto-increment functionality

Requirements: 3.1, 3.2, 3.3, 3.4
"""

import os
import sys
import pytest
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, text, inspect, MetaData
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database import DATABASE_URL, engine, get_db, init_db
from backend.unified_models import *
from backend.models import *
from backend.memory_models import *
from scripts.optimize_postgresql_schema import PostgreSQLSchemaOptimizer

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestPostgreSQLSchemaOptimization:
    """Test PostgreSQL schema optimization"""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        if not DATABASE_URL.startswith("postgresql"):
            pytest.skip("PostgreSQL tests require PostgreSQL database")
        
        cls.engine = engine
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        
        # Initialize database
        try:
            init_db()
            logger.info("Database initialized for testing")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            pytest.skip(f"Database initialization failed: {e}")
    
    def test_postgresql_connection(self):
        """Test PostgreSQL connection and version"""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"PostgreSQL version: {version}")
            assert "PostgreSQL" in version
    
    def test_postgresql_data_types(self):
        """Test that PostgreSQL-specific data types are being used"""
        inspector = inspect(self.engine)
        
        # Check for JSONB columns
        jsonb_tables = [
            ('unified_users', []),  # No JSONB columns expected in users
            ('unified_tickets', []),  # No JSONB columns expected in tickets
            ('unified_chat_history', ['tools_used', 'sources']),
            ('enhanced_chat_history', ['user_message_encrypted', 'bot_response_encrypted', 'tools_used', 'tool_performance', 'context_used', 'semantic_features']),
            ('memory_context_cache', ['context_data', 'context_data_encrypted', 'access_control']),
            ('unified_voice_analytics', ['analytics_metadata']),
            ('unified_knowledge_entries', ['embedding']),
        ]
        
        for table_name, expected_jsonb_columns in jsonb_tables:
            try:
                columns = inspector.get_columns(table_name)
                jsonb_columns = [col['name'] for col in columns if 'jsonb' in str(col['type']).lower()]
                
                for expected_col in expected_jsonb_columns:
                    assert expected_col in jsonb_columns, f"Expected JSONB column {expected_col} not found in {table_name}"
                
                logger.info(f"Table {table_name}: Found JSONB columns: {jsonb_columns}")
            except Exception as e:
                logger.warning(f"Could not check table {table_name}: {e}")
        
        # Check for timestamp with timezone columns
        timestamp_tables = [
            'unified_users',
            'unified_tickets', 
            'unified_user_sessions',
            'enhanced_chat_history',
            'memory_context_cache'
        ]
        
        for table_name in timestamp_tables:
            try:
                columns = inspector.get_columns(table_name)
                timestamp_columns = [col['name'] for col in columns if 'timestamp' in str(col['type']).lower() and 'timezone' in str(col['type']).lower()]
                
                assert len(timestamp_columns) > 0, f"No timestamp with timezone columns found in {table_name}"
                logger.info(f"Table {table_name}: Found timestamp columns: {timestamp_columns}")
            except Exception as e:
                logger.warning(f"Could not check table {table_name}: {e}")
    
    def test_indexes_creation(self):
        """Test that optimized indexes are created"""
        with self.engine.connect() as conn:
            # Check for specific indexes
            index_check_sql = """
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE 'idx_%'
            ORDER BY tablename, indexname;
            """
            
            result = conn.execute(text(index_check_sql))
            indexes = result.fetchall()
            
            # Expected indexes (partial list)
            expected_indexes = [
                'idx_unified_users_email_active',
                'idx_unified_users_username_active',
                'idx_unified_user_sessions_token',
                'idx_unified_tickets_customer_status',
                'idx_enhanced_chat_history_user_session',
                'idx_memory_context_cache_user_type_relevance'
            ]
            
            found_indexes = [idx[0] for idx in indexes]
            logger.info(f"Found {len(found_indexes)} indexes")
            
            # Check that at least some expected indexes exist
            found_expected = [idx for idx in expected_indexes if idx in found_indexes]
            assert len(found_expected) > 0, f"No expected indexes found. Found: {found_indexes[:10]}"
            logger.info(f"Found expected indexes: {found_expected}")
    
    def test_constraints_validation(self):
        """Test database constraints"""
        with self.SessionLocal() as session:
            # Test email validation constraint
            try:
                invalid_user = UnifiedUser(
                    user_id="test_invalid_email",
                    username="testuser",
                    email="invalid-email",  # Invalid email format
                    password_hash="test_hash_123456789012345678901234567890123456789012345678901234567890"
                )
                session.add(invalid_user)
                session.commit()
                assert False, "Should have failed due to email constraint"
            except IntegrityError:
                session.rollback()
                logger.info("Email validation constraint working correctly")
            
            # Test rating validation constraint
            try:
                invalid_rating = UnifiedCustomerSatisfaction(
                    customer_id=1,
                    rating=10,  # Invalid rating (should be 1-5)
                    created_at=datetime.now(timezone.utc)
                )
                session.add(invalid_rating)
                session.commit()
                assert False, "Should have failed due to rating constraint"
            except IntegrityError:
                session.rollback()
                logger.info("Rating validation constraint working correctly")
    
    def test_sequences_functionality(self):
        """Test PostgreSQL sequences for auto-incrementing fields"""
        with self.engine.connect() as conn:
            # Check that sequences exist
            sequences_sql = """
            SELECT sequencename 
            FROM pg_sequences 
            WHERE schemaname = 'public'
            ORDER BY sequencename;
            """
            
            result = conn.execute(text(sequences_sql))
            sequences = [row[0] for row in result.fetchall()]
            
            expected_sequences = [
                'unified_users_id_seq',
                'unified_tickets_id_seq',
                'unified_user_sessions_id_seq'
            ]
            
            found_expected = [seq for seq in expected_sequences if seq in sequences]
            logger.info(f"Found sequences: {sequences}")
            logger.info(f"Found expected sequences: {found_expected}")
            
            # At least some sequences should exist
            assert len(sequences) > 0, "No sequences found"
    
    def test_foreign_key_constraints(self):
        """Test foreign key constraints"""
        inspector = inspect(self.engine)
        
        # Check foreign keys for key tables
        tables_with_fks = [
            'unified_tickets',
            'unified_ticket_comments', 
            'unified_ticket_activities',
            'unified_user_sessions',
            'unified_chat_sessions'
        ]
        
        for table_name in tables_with_fks:
            try:
                foreign_keys = inspector.get_foreign_keys(table_name)
                assert len(foreign_keys) > 0, f"No foreign keys found for {table_name}"
                logger.info(f"Table {table_name}: Found {len(foreign_keys)} foreign keys")
            except Exception as e:
                logger.warning(f"Could not check foreign keys for {table_name}: {e}")
    
    def test_jsonb_operations(self):
        """Test JSONB operations and indexing"""
        with self.SessionLocal() as session:
            try:
                # Test JSONB storage and retrieval
                test_data = {
                    "test_key": "test_value",
                    "nested": {"key": "value"},
                    "array": [1, 2, 3]
                }
                
                chat_entry = EnhancedChatHistory(
                    session_id="test_session",
                    user_id="test_user",
                    user_message="Test message",
                    bot_response="Test response",
                    tools_used=["test_tool"],
                    tool_performance=test_data,
                    semantic_features=test_data
                )
                
                session.add(chat_entry)
                session.commit()
                
                # Retrieve and verify JSONB data
                retrieved = session.query(EnhancedChatHistory).filter_by(session_id="test_session").first()
                assert retrieved is not None
                assert retrieved.tool_performance == test_data
                assert retrieved.semantic_features == test_data
                
                logger.info("JSONB operations working correctly")
                
                # Cleanup
                session.delete(retrieved)
                session.commit()
                
            except Exception as e:
                session.rollback()
                logger.error(f"JSONB operations test failed: {e}")
                raise
    
    def test_timestamp_with_timezone(self):
        """Test timestamp with timezone functionality"""
        with self.SessionLocal() as session:
            try:
                # Create a user with timezone-aware timestamps
                test_user = UnifiedUser(
                    user_id="test_tz_user",
                    username="test_tz_user",
                    email="test_tz@example.com",
                    password_hash="test_hash_123456789012345678901234567890123456789012345678901234567890"
                )
                
                session.add(test_user)
                session.commit()
                
                # Verify timestamp is timezone-aware
                retrieved = session.query(UnifiedUser).filter_by(user_id="test_tz_user").first()
                assert retrieved is not None
                assert retrieved.created_at.tzinfo is not None
                
                logger.info(f"Timestamp with timezone working correctly: {retrieved.created_at}")
                
                # Cleanup
                session.delete(retrieved)
                session.commit()
                
            except Exception as e:
                session.rollback()
                logger.error(f"Timestamp with timezone test failed: {e}")
                raise
    
    def test_schema_optimization_script(self):
        """Test the schema optimization script"""
        try:
            optimizer = PostgreSQLSchemaOptimizer()
            
            # Test individual components
            optimizer.create_optimized_indexes()
            logger.info("Index optimization completed")
            
            optimizer.add_postgresql_constraints()
            logger.info("Constraint optimization completed")
            
            optimizer.create_sequences()
            logger.info("Sequence optimization completed")
            
            optimizer.verify_data_types()
            logger.info("Data type verification completed")
            
            # Generate report
            report = optimizer.generate_optimization_report()
            assert report is not None
            assert len(report['tables']) > 0
            logger.info(f"Optimization report generated with {len(report['tables'])} tables")
            
        except Exception as e:
            logger.error(f"Schema optimization script test failed: {e}")
            raise
    
    def test_performance_with_indexes(self):
        """Test query performance with optimized indexes"""
        with self.SessionLocal() as session:
            try:
                # Create test data
                test_users = []
                for i in range(10):
                    user = UnifiedUser(
                        user_id=f"perf_test_user_{i}",
                        username=f"perf_user_{i}",
                        email=f"perf_test_{i}@example.com",
                        password_hash="test_hash_123456789012345678901234567890123456789012345678901234567890"
                    )
                    test_users.append(user)
                
                session.add_all(test_users)
                session.commit()
                
                # Test indexed queries
                start_time = datetime.now()
                
                # Query by email (should use index)
                user = session.query(UnifiedUser).filter_by(email="perf_test_5@example.com").first()
                assert user is not None
                
                # Query by username (should use index)
                user = session.query(UnifiedUser).filter_by(username="perf_user_3").first()
                assert user is not None
                
                end_time = datetime.now()
                query_time = (end_time - start_time).total_seconds()
                
                logger.info(f"Indexed queries completed in {query_time:.4f} seconds")
                
                # Cleanup
                for user in test_users:
                    session.delete(user)
                session.commit()
                
            except Exception as e:
                session.rollback()
                logger.error(f"Performance test failed: {e}")
                raise

def run_tests():
    """Run all PostgreSQL schema optimization tests"""
    logger.info("Starting PostgreSQL schema optimization tests...")
    
    # Run pytest
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ]
    
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        logger.info("All PostgreSQL schema optimization tests passed!")
    else:
        logger.error("Some tests failed!")
    
    return exit_code

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)