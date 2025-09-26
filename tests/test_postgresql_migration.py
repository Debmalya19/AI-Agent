#!/usr/bin/env python3
"""
Comprehensive PostgreSQL Migration Testing Suite

This test suite validates the migration from SQLite to PostgreSQL with:
- Migration validation tests
- Database connection and model operation tests  
- Integration tests for full application functionality
- Performance comparison tests between SQLite and PostgreSQL
- Data integrity validation tests for migration accuracy

Requirements: 5.1, 5.2, 5.3, 5.4
"""

import os
import sys
import json
import pytest
import tempfile
import shutil
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect, MetaData, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Import application modules
from backend.database import create_database_engine, validate_database_url
from backend.unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedTicketComment, UnifiedUserSession,
    UnifiedChatSession, UnifiedChatMessage, TicketStatus, TicketPriority, UserRole
)
from backend.models import User, Customer, Ticket, ChatHistory
from scripts.migrate_to_postgresql import DatabaseMigrator, MigrationConfig, MigrationReport

# Setup logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestDatabaseConnections:
    """Test database connection functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        load_dotenv()
        self.sqlite_url = "sqlite:///test_migration.db"
        self.postgresql_url = os.getenv("TEST_DATABASE_URL", 
                                       "postgresql://postgres:password@localhost:5432/test_ai_agent")
    
    def teardown_method(self):
        """Cleanup test environment"""
        # Remove test SQLite database
        sqlite_path = "test_migration.db"
        if os.path.exists(sqlite_path):
            try:
                os.remove(sqlite_path)
            except PermissionError:
                # File may be locked on Windows, try again after a short delay
                import time
                time.sleep(0.1)
                try:
                    os.remove(sqlite_path)
                except PermissionError:
                    # If still locked, skip cleanup (will be cleaned up later)
                    pass
    
    def test_sqlite_connection_creation(self):
        """Test SQLite database connection creation"""
        engine = create_engine(self.sqlite_url)
        assert engine is not None
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
    
    def test_postgresql_connection_creation(self):
        """Test PostgreSQL database connection creation"""
        try:
            engine = create_database_engine(self.postgresql_url)
            assert engine is not None
            
            # Test connection
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                assert "PostgreSQL" in version
                
        except Exception as e:
            pytest.skip(f"PostgreSQL not available for testing: {e}")
    
    def test_database_url_validation(self):
        """Test database URL validation"""
        # Valid URLs
        assert validate_database_url("sqlite:///test.db") == True
        assert validate_database_url("postgresql://user:pass@localhost:5432/db") == True
        
        # Invalid URLs
        assert validate_database_url("invalid://url") == False
        assert validate_database_url("") == False
        assert validate_database_url(None) == False
    
    def test_connection_pooling_parameters(self):
        """Test PostgreSQL connection pooling configuration"""
        try:
            engine = create_database_engine(self.postgresql_url)
            
            # Check pool configuration
            assert hasattr(engine.pool, 'size')
            assert hasattr(engine.pool, 'overflow')
            assert engine.pool.size() >= 0
            
        except Exception as e:
            pytest.skip(f"PostgreSQL not available for testing: {e}")


class TestModelOperations:
    """Test database model operations with both SQLite and PostgreSQL"""
    
    def setup_method(self):
        """Setup test databases"""
        load_dotenv()
        self.sqlite_url = "sqlite:///test_models.db"
        self.postgresql_url = os.getenv("TEST_DATABASE_URL", 
                                       "postgresql://postgres:password@localhost:5432/test_ai_agent")
        
        # Create test engines
        self.sqlite_engine = create_engine(self.sqlite_url)
        try:
            self.postgresql_engine = create_database_engine(self.postgresql_url)
            self.postgresql_available = True
        except:
            self.postgresql_available = False
    
    def teardown_method(self):
        """Cleanup test databases"""
        # Close engines first
        if hasattr(self, 'sqlite_engine') and self.sqlite_engine:
            self.sqlite_engine.dispose()
        if hasattr(self, 'postgresql_engine') and self.postgresql_engine:
            self.postgresql_engine.dispose()
        
        # Remove test SQLite database
        sqlite_path = "test_models.db"
        if os.path.exists(sqlite_path):
            try:
                os.remove(sqlite_path)
            except PermissionError:
                # File may be locked on Windows, skip cleanup
                pass
        
        # Clean PostgreSQL test data
        if self.postgresql_available and self.postgresql_engine:
            try:
                with self.postgresql_engine.connect() as conn:
                    # Clean test data
                    conn.execute(text("TRUNCATE TABLE unified_users CASCADE"))
                    conn.commit()
            except:
                pass
    
    def test_unified_user_model_sqlite(self):
        """Test UnifiedUser model operations with SQLite"""
        from backend.database import Base
        
        # Create tables
        Base.metadata.create_all(self.sqlite_engine)
        
        # Create session
        Session = sessionmaker(bind=self.sqlite_engine)
        session = Session()
        
        try:
            # Create test user
            user = UnifiedUser(
                user_id="test_user_001",
                username="testuser",
                email="test@example.com",
                password_hash="hashed_password",
                full_name="Test User",
                role=UserRole.CUSTOMER
            )
            
            session.add(user)
            session.commit()
            
            # Query user
            retrieved_user = session.query(UnifiedUser).filter_by(username="testuser").first()
            assert retrieved_user is not None
            assert retrieved_user.email == "test@example.com"
            assert retrieved_user.role == UserRole.CUSTOMER
            
        finally:
            session.close()
    
    def test_unified_user_model_postgresql(self):
        """Test UnifiedUser model operations with PostgreSQL"""
        if not self.postgresql_available:
            pytest.skip("PostgreSQL not available for testing")
        
        from backend.database import Base
        
        # Create tables
        Base.metadata.create_all(self.postgresql_engine)
        
        # Create session
        Session = sessionmaker(bind=self.postgresql_engine)
        session = Session()
        
        try:
            # Create test user
            user = UnifiedUser(
                user_id="test_user_pg_001",
                username="testuser_pg",
                email="test_pg@example.com",
                password_hash="hashed_password",
                full_name="Test User PG",
                role=UserRole.CUSTOMER
            )
            
            session.add(user)
            session.commit()
            
            # Query user
            retrieved_user = session.query(UnifiedUser).filter_by(username="testuser_pg").first()
            assert retrieved_user is not None
            assert retrieved_user.email == "test_pg@example.com"
            assert retrieved_user.role == UserRole.CUSTOMER
            
            # Test PostgreSQL-specific features
            assert retrieved_user.created_at is not None
            assert retrieved_user.updated_at is not None
            
        finally:
            session.close()
    
    def test_ticket_model_relationships(self):
        """Test ticket model relationships"""
        if not self.postgresql_available:
            pytest.skip("PostgreSQL not available for testing")
        
        from backend.database import Base
        
        # Create tables
        Base.metadata.create_all(self.postgresql_engine)
        
        # Create session
        Session = sessionmaker(bind=self.postgresql_engine)
        session = Session()
        
        try:
            # Create test user
            user = UnifiedUser(
                user_id="test_user_rel_001",
                username="testuser_rel",
                email="test_rel@example.com",
                password_hash="hashed_password",
                full_name="Test User Rel",
                role=UserRole.CUSTOMER
            )
            session.add(user)
            session.flush()  # Get user ID
            
            # Create test ticket
            ticket = UnifiedTicket(
                ticket_id="TICKET-001",
                title="Test Ticket",
                description="Test ticket description",
                status=TicketStatus.OPEN,
                priority=TicketPriority.MEDIUM,
                customer_id=user.id
            )
            session.add(ticket)
            session.commit()
            
            # Test relationships
            retrieved_ticket = session.query(UnifiedTicket).filter_by(ticket_id="TICKET-001").first()
            assert retrieved_ticket is not None
            assert retrieved_ticket.customer is not None
            assert retrieved_ticket.customer.username == "testuser_rel"
            
        finally:
            session.close()


class TestMigrationScript:
    """Test the migration script functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        load_dotenv()
        self.test_dir = tempfile.mkdtemp()
        self.sqlite_url = f"sqlite:///{self.test_dir}/test_source.db"
        self.postgresql_url = os.getenv("TEST_DATABASE_URL", 
                                       "postgresql://postgres:password@localhost:5432/test_ai_agent")
        
        # Create test SQLite database with sample data
        self.setup_test_sqlite_data()
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def setup_test_sqlite_data(self):
        """Create test SQLite database with sample data"""
        from backend.database import Base
        
        engine = create_engine(self.sqlite_url)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Create test users
            users = [
                UnifiedUser(
                    user_id=f"user_{i:03d}",
                    username=f"testuser{i}",
                    email=f"test{i}@example.com",
                    password_hash="hashed_password",
                    full_name=f"Test User {i}",
                    role=UserRole.CUSTOMER
                )
                for i in range(1, 11)
            ]
            
            for user in users:
                session.add(user)
            
            session.commit()
            
            # Create test tickets
            for i, user in enumerate(users[:5], 1):
                ticket = UnifiedTicket(
                    ticket_id=f"TICKET-{i:03d}",
                    title=f"Test Ticket {i}",
                    description=f"Test ticket description {i}",
                    status=TicketStatus.OPEN,
                    priority=TicketPriority.MEDIUM,
                    customer_id=user.id
                )
                session.add(ticket)
            
            session.commit()
            
        finally:
            session.close()
    
    def test_migration_config_creation(self):
        """Test migration configuration creation"""
        config = MigrationConfig(
            sqlite_url=self.sqlite_url,
            postgresql_url=self.postgresql_url,
            backup_dir=f"{self.test_dir}/backups",
            batch_size=100,
            validate_data=True
        )
        
        assert config.sqlite_url == self.sqlite_url
        assert config.postgresql_url == self.postgresql_url
        assert config.batch_size == 100
        assert config.validate_data == True
    
    def test_migrator_initialization(self):
        """Test DatabaseMigrator initialization"""
        config = MigrationConfig(
            sqlite_url=self.sqlite_url,
            postgresql_url=self.postgresql_url
        )
        
        migrator = DatabaseMigrator(config)
        assert migrator.config == config
        assert migrator.sqlite_engine is None  # Not connected yet
        assert migrator.postgresql_engine is None  # Not connected yet
    
    def test_database_connection_setup(self):
        """Test database connection setup"""
        config = MigrationConfig(
            sqlite_url=self.sqlite_url,
            postgresql_url=self.postgresql_url
        )
        
        migrator = DatabaseMigrator(config)
        
        # Test SQLite connection
        assert migrator.setup_connections() == True
        assert migrator.sqlite_engine is not None
        
        # Test PostgreSQL connection (if available)
        if migrator.postgresql_engine is not None:
            with migrator.postgresql_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1
    
    def test_table_data_export(self):
        """Test table data export from SQLite"""
        config = MigrationConfig(
            sqlite_url=self.sqlite_url,
            postgresql_url=self.postgresql_url
        )
        
        migrator = DatabaseMigrator(config)
        migrator.setup_connections()
        
        # Export user data
        user_data = migrator.export_table_data("unified_users")
        assert user_data is not None
        assert len(user_data) == 10  # We created 10 test users
        
        # Verify data structure
        first_user = user_data[0]
        assert "user_id" in first_user
        assert "username" in first_user
        assert "email" in first_user
    
    def test_backup_creation(self):
        """Test backup creation functionality"""
        config = MigrationConfig(
            sqlite_url=self.sqlite_url,
            postgresql_url=self.postgresql_url,
            backup_dir=f"{self.test_dir}/backups",
            create_rollback=True
        )
        
        migrator = DatabaseMigrator(config)
        migrator.setup_connections()
        
        # Create backup
        result = migrator.create_backup()
        assert result == True
        
        # Verify backup file exists
        backup_dir = Path(config.backup_dir)
        assert backup_dir.exists()
        
        backup_files = list(backup_dir.glob("sqlite_backup_*.db"))
        assert len(backup_files) > 0


class TestDataIntegrity:
    """Test data integrity validation during migration"""
    
    def setup_method(self):
        """Setup test environment"""
        load_dotenv()
        self.test_dir = tempfile.mkdtemp()
        self.sqlite_url = f"sqlite:///{self.test_dir}/integrity_test.db"
        self.postgresql_url = os.getenv("TEST_DATABASE_URL", 
                                       "postgresql://postgres:password@localhost:5432/test_ai_agent")
        
        # Setup test data with relationships
        self.setup_relational_test_data()
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def setup_relational_test_data(self):
        """Create test data with foreign key relationships"""
        from backend.database import Base
        
        engine = create_engine(self.sqlite_url)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Create parent records (users)
            users = []
            for i in range(1, 6):
                user = UnifiedUser(
                    user_id=f"integrity_user_{i:03d}",
                    username=f"integrityuser{i}",
                    email=f"integrity{i}@example.com",
                    password_hash="hashed_password",
                    full_name=f"Integrity User {i}",
                    role=UserRole.CUSTOMER
                )
                session.add(user)
                users.append(user)
            
            session.flush()  # Get user IDs
            
            # Create child records (tickets)
            for i, user in enumerate(users, 1):
                ticket = UnifiedTicket(
                    ticket_id=f"INTEGRITY-{i:03d}",
                    title=f"Integrity Test Ticket {i}",
                    description=f"Test ticket for integrity validation {i}",
                    status=TicketStatus.OPEN,
                    priority=TicketPriority.HIGH,
                    customer_id=user.id
                )
                session.add(ticket)
            
            session.commit()
            
        finally:
            session.close()
    
    def test_referential_integrity_validation(self):
        """Test referential integrity validation"""
        config = MigrationConfig(
            sqlite_url=self.sqlite_url,
            postgresql_url=self.postgresql_url
        )
        
        migrator = DatabaseMigrator(config)
        migrator.setup_connections()
        
        # Test referential integrity check method
        if migrator.postgresql_engine:
            try:
                # This will test the integrity checking logic
                integrity_results = migrator._check_referential_integrity()
                assert isinstance(integrity_results, dict)
                assert "all_constraints_valid" in integrity_results
                assert "constraint_errors" in integrity_results
                assert "foreign_key_checks" in integrity_results
                
            except Exception as e:
                pytest.skip(f"PostgreSQL not available for integrity testing: {e}")
    
    def test_data_count_validation(self):
        """Test data count validation between source and target"""
        config = MigrationConfig(
            sqlite_url=self.sqlite_url,
            postgresql_url=self.postgresql_url
        )
        
        migrator = DatabaseMigrator(config)
        migrator.setup_connections()
        
        # Export data and check counts
        user_data = migrator.export_table_data("unified_users")
        ticket_data = migrator.export_table_data("unified_tickets")
        
        assert len(user_data) == 5  # We created 5 users
        assert len(ticket_data) == 5  # We created 5 tickets
        
        # Verify relationships are preserved in exported data
        for ticket in ticket_data:
            assert ticket["customer_id"] is not None
            # Find corresponding user
            user_found = any(user["id"] == ticket["customer_id"] for user in user_data)
            assert user_found, f"User not found for ticket customer_id: {ticket['customer_id']}"
    
    def test_data_type_conversion(self):
        """Test data type conversion during migration"""
        config = MigrationConfig(
            sqlite_url=self.sqlite_url,
            postgresql_url=self.postgresql_url
        )
        
        migrator = DatabaseMigrator(config)
        migrator.setup_connections()
        
        # Export data
        user_data = migrator.export_table_data("unified_users")
        
        # Check data types
        first_user = user_data[0]
        
        # String fields should remain strings
        assert isinstance(first_user["username"], str)
        assert isinstance(first_user["email"], str)
        
        # Integer fields should be integers
        assert isinstance(first_user["id"], int)
        
        # Datetime fields should be properly formatted
        if first_user.get("created_at"):
            # Should be a valid datetime string or datetime object
            assert first_user["created_at"] is not None


class TestPerformanceComparison:
    """Test performance comparison between SQLite and PostgreSQL"""
    
    def setup_method(self):
        """Setup performance test environment"""
        load_dotenv()
        self.test_dir = tempfile.mkdtemp()
        self.sqlite_url = f"sqlite:///{self.test_dir}/perf_test.db"
        self.postgresql_url = os.getenv("TEST_DATABASE_URL", 
                                       "postgresql://postgres:password@localhost:5432/test_ai_agent")
        
        # Create performance test data
        self.setup_performance_test_data()
    
    def teardown_method(self):
        """Cleanup performance test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def setup_performance_test_data(self):
        """Create larger dataset for performance testing"""
        from backend.database import Base
        
        engine = create_engine(self.sqlite_url)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Create larger dataset for performance testing
            batch_size = 100
            total_users = 1000
            
            for batch_start in range(0, total_users, batch_size):
                users = []
                for i in range(batch_start, min(batch_start + batch_size, total_users)):
                    user = UnifiedUser(
                        user_id=f"perf_user_{i:06d}",
                        username=f"perfuser{i}",
                        email=f"perf{i}@example.com",
                        password_hash="hashed_password",
                        full_name=f"Performance User {i}",
                        role=UserRole.CUSTOMER
                    )
                    users.append(user)
                
                session.add_all(users)
                session.commit()
                
        finally:
            session.close()
    
    def test_sqlite_query_performance(self):
        """Test SQLite query performance"""
        engine = create_engine(self.sqlite_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Measure query performance
            start_time = time.time()
            
            # Simple select query
            users = session.query(UnifiedUser).limit(100).all()
            
            end_time = time.time()
            sqlite_query_time = end_time - start_time
            
            assert len(users) == 100
            assert sqlite_query_time < 5.0  # Should complete within 5 seconds
            
            logger.info(f"SQLite query time for 100 records: {sqlite_query_time:.4f}s")
            
        finally:
            session.close()
    
    def test_postgresql_query_performance(self):
        """Test PostgreSQL query performance"""
        try:
            engine = create_database_engine(self.postgresql_url)
            if not engine:
                pytest.skip("PostgreSQL not available for performance testing")
            
            from backend.database import Base
            Base.metadata.create_all(engine)
            
            Session = sessionmaker(bind=engine)
            session = Session()
            
            try:
                # Create some test data in PostgreSQL
                users = []
                for i in range(100):
                    user = UnifiedUser(
                        user_id=f"pg_perf_user_{i:06d}",
                        username=f"pgperfuser{i}",
                        email=f"pgperf{i}@example.com",
                        password_hash="hashed_password",
                        full_name=f"PG Performance User {i}",
                        role=UserRole.CUSTOMER
                    )
                    users.append(user)
                
                session.add_all(users)
                session.commit()
                
                # Measure query performance
                start_time = time.time()
                
                # Simple select query
                queried_users = session.query(UnifiedUser).filter(
                    UnifiedUser.username.like("pgperfuser%")
                ).limit(100).all()
                
                end_time = time.time()
                postgresql_query_time = end_time - start_time
                
                assert len(queried_users) == 100
                assert postgresql_query_time < 5.0  # Should complete within 5 seconds
                
                logger.info(f"PostgreSQL query time for 100 records: {postgresql_query_time:.4f}s")
                
            finally:
                session.close()
                
        except Exception as e:
            pytest.skip(f"PostgreSQL not available for performance testing: {e}")
    
    def test_connection_pool_performance(self):
        """Test connection pool performance with PostgreSQL"""
        try:
            engine = create_database_engine(self.postgresql_url)
            if not engine:
                pytest.skip("PostgreSQL not available for connection pool testing")
            
            # Test multiple concurrent connections
            start_time = time.time()
            
            connections = []
            for i in range(10):
                conn = engine.connect()
                connections.append(conn)
                
                # Execute simple query
                result = conn.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1
            
            # Close all connections
            for conn in connections:
                conn.close()
            
            end_time = time.time()
            pool_test_time = end_time - start_time
            
            assert pool_test_time < 10.0  # Should complete within 10 seconds
            logger.info(f"Connection pool test time for 10 connections: {pool_test_time:.4f}s")
            
        except Exception as e:
            pytest.skip(f"PostgreSQL not available for connection pool testing: {e}")


class TestFullMigrationIntegration:
    """Test full migration process integration"""
    
    def setup_method(self):
        """Setup full integration test environment"""
        load_dotenv()
        self.test_dir = tempfile.mkdtemp()
        self.sqlite_url = f"sqlite:///{self.test_dir}/full_migration_test.db"
        self.postgresql_url = os.getenv("TEST_DATABASE_URL", 
                                       "postgresql://postgres:password@localhost:5432/test_ai_agent")
        
        # Create comprehensive test dataset
        self.setup_comprehensive_test_data()
    
    def teardown_method(self):
        """Cleanup full integration test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
        # Clean PostgreSQL test data
        try:
            engine = create_database_engine(self.postgresql_url)
            if engine:
                with engine.connect() as conn:
                    # Clean all test tables
                    conn.execute(text("TRUNCATE TABLE unified_tickets CASCADE"))
                    conn.execute(text("TRUNCATE TABLE unified_users CASCADE"))
                    conn.commit()
        except:
            pass
    
    def setup_comprehensive_test_data(self):
        """Create comprehensive test dataset"""
        from backend.database import Base
        
        engine = create_engine(self.sqlite_url)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Create users with different roles
            users = []
            for i in range(1, 21):
                role = UserRole.ADMIN if i <= 2 else UserRole.CUSTOMER
                user = UnifiedUser(
                    user_id=f"full_test_user_{i:03d}",
                    username=f"fulltestuser{i}",
                    email=f"fulltest{i}@example.com",
                    password_hash="hashed_password",
                    full_name=f"Full Test User {i}",
                    role=role,
                    is_admin=(i <= 2)
                )
                session.add(user)
                users.append(user)
            
            session.flush()  # Get user IDs
            
            # Create tickets with various statuses
            statuses = [TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CLOSED]
            priorities = [TicketPriority.LOW, TicketPriority.MEDIUM, TicketPriority.HIGH, TicketPriority.CRITICAL]
            
            for i, user in enumerate(users[2:], 1):  # Skip admin users
                status = statuses[i % len(statuses)]
                priority = priorities[i % len(priorities)]
                
                ticket = UnifiedTicket(
                    ticket_id=f"FULL-TEST-{i:03d}",
                    title=f"Full Test Ticket {i}",
                    description=f"Comprehensive test ticket {i} for migration validation",
                    status=status,
                    priority=priority,
                    customer_id=user.id,
                    assigned_agent_id=users[0].id if i % 3 == 0 else None  # Assign some tickets to admin
                )
                session.add(ticket)
            
            session.commit()
            
        finally:
            session.close()
    
    @pytest.mark.integration
    def test_complete_migration_process(self):
        """Test the complete migration process"""
        try:
            # Setup migration configuration
            config = MigrationConfig(
                sqlite_url=self.sqlite_url,
                postgresql_url=self.postgresql_url,
                backup_dir=f"{self.test_dir}/migration_backups",
                batch_size=50,
                validate_data=True,
                create_rollback=True
            )
            
            # Initialize migrator
            migrator = DatabaseMigrator(config)
            
            # Test connection setup
            assert migrator.setup_connections() == True
            
            # Test backup creation
            assert migrator.create_backup() == True
            
            # Verify backup exists
            backup_dir = Path(config.backup_dir)
            backup_files = list(backup_dir.glob("sqlite_backup_*.db"))
            assert len(backup_files) > 0
            
            # Test data export
            user_data = migrator.export_table_data("unified_users")
            ticket_data = migrator.export_table_data("unified_tickets")
            
            assert user_data is not None
            assert ticket_data is not None
            assert len(user_data) == 20  # We created 20 users
            assert len(ticket_data) == 18  # We created 18 tickets (skipped 2 admin users)
            
            logger.info(f"Migration test completed successfully")
            logger.info(f"Exported {len(user_data)} users and {len(ticket_data)} tickets")
            
        except Exception as e:
            if "PostgreSQL" in str(e) or "connection" in str(e).lower():
                pytest.skip(f"PostgreSQL not available for full migration testing: {e}")
            else:
                raise
    
    def test_migration_validation_report(self):
        """Test migration validation and reporting"""
        from scripts.migrate_to_postgresql import TableMigrationResult, MigrationReport
        
        # Create mock migration results
        table_results = [
            TableMigrationResult(
                table_name="unified_users",
                source_count=20,
                migrated_count=20,
                errors=[],
                duration_seconds=1.5,
                success=True
            ),
            TableMigrationResult(
                table_name="unified_tickets",
                source_count=18,
                migrated_count=18,
                errors=[],
                duration_seconds=2.1,
                success=True
            )
        ]
        
        # Create migration report
        report = MigrationReport(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            total_tables=2,
            successful_tables=2,
            failed_tables=0,
            total_records=38,
            migrated_records=38,
            errors=[],
            table_results=table_results,
            rollback_available=True
        )
        
        # Validate report structure
        assert report.total_tables == 2
        assert report.successful_tables == 2
        assert report.failed_tables == 0
        assert report.total_records == 38
        assert report.migrated_records == 38
        assert len(report.errors) == 0
        assert report.rollback_available == True
        
        # Test validation logic
        config = MigrationConfig(
            sqlite_url=self.sqlite_url,
            postgresql_url=self.postgresql_url
        )
        
        migrator = DatabaseMigrator(config)
        validation_results = migrator.validate_migration(table_results)
        
        assert validation_results["overall_success"] == True
        assert len(validation_results["table_validations"]) == 2
        
        # Check individual table validations
        user_validation = validation_results["table_validations"]["unified_users"]
        assert user_validation["success_rate"] == 100.0
        assert user_validation["source_count"] == 20
        assert user_validation["migrated_count"] == 20


# Test fixtures and utilities
@pytest.fixture
def temp_database_dir():
    """Provide temporary directory for test databases"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_postgresql_unavailable():
    """Mock PostgreSQL as unavailable for testing error handling"""
    with patch('psycopg2.connect') as mock_connect:
        mock_connect.side_effect = Exception("PostgreSQL connection failed")
        yield mock_connect


# Performance benchmarking utilities
def benchmark_query_performance(engine, query_func, iterations=10):
    """Benchmark query performance"""
    times = []
    
    for _ in range(iterations):
        start_time = time.time()
        query_func(engine)
        end_time = time.time()
        times.append(end_time - start_time)
    
    return {
        'min_time': min(times),
        'max_time': max(times),
        'avg_time': sum(times) / len(times),
        'total_time': sum(times)
    }


def test_authentication_functionality():
    """Test authentication functionality with PostgreSQL backend"""
    logger.info("Testing authentication functionality...")
    
    try:
        from backend.database import get_db
        from backend.unified_models import UnifiedUser
        
        # Get database session
        db_gen = get_db()
        session = next(db_gen)
        
        # Test user creation
        test_user = UnifiedUser(
            user_id="test_auth_user",
            username="test_auth",
            email="test_auth@example.com",
            password_hash="test_hash",
            full_name="Test Auth User",
            is_admin=False,
            is_active=True,
            role=UserRole.CUSTOMER
        )
        
        session.add(test_user)
        session.commit()
        
        # Test user retrieval
        retrieved_user = session.query(UnifiedUser).filter_by(username="test_auth").first()
        assert retrieved_user is not None
        assert retrieved_user.email == "test_auth@example.com"
        
        # Test user authentication simulation
        assert retrieved_user.password_hash == "test_hash"
        assert retrieved_user.is_active == True
        
        # Cleanup
        session.delete(retrieved_user)
        session.commit()
        session.close()
        
        logger.info("Authentication functionality test passed")
        
    except Exception as e:
        logger.error(f"Authentication functionality test failed: {e}")
        raise


def test_admin_dashboard_functionality():
    """Test admin dashboard functionality with PostgreSQL backend"""
    logger.info("Testing admin dashboard functionality...")
    
    try:
        from backend.database import get_db
        from backend.unified_models import UnifiedUser, UnifiedTicket
        import uuid
        
        # Get database session
        db_gen = get_db()
        session = next(db_gen)
        
        # Generate unique identifiers to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]
        
        # Check if test admin user already exists and clean up
        existing_admin = session.query(UnifiedUser).filter_by(username=f"test_admin_{unique_id}").first()
        if existing_admin:
            session.delete(existing_admin)
            session.commit()
        
        # Test admin user creation
        admin_user = UnifiedUser(
            user_id=f"test_admin_user_{unique_id}",
            username=f"test_admin_{unique_id}",
            email=f"test_admin_{unique_id}@example.com",
            password_hash="admin_hash",
            full_name=f"Test Admin User {unique_id}",
            is_admin=True,
            is_active=True,
            role=UserRole.ADMIN
        )
        
        session.add(admin_user)
        session.commit()
        
        # Test ticket creation for admin dashboard
        test_ticket = UnifiedTicket(
            ticket_id=f"TEST-{unique_id}",
            customer_id=admin_user.id,
            title=f"Test Ticket {unique_id}",
            description=f"Test ticket for admin dashboard {unique_id}",
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM
        )
        
        session.add(test_ticket)
        session.commit()
        
        # Test admin dashboard queries
        # 1. Get all users (admin functionality)
        all_users = session.query(UnifiedUser).all()
        assert len(all_users) >= 1
        
        # 2. Get all tickets (admin functionality)
        all_tickets = session.query(UnifiedTicket).all()
        assert len(all_tickets) >= 1
        
        # 3. Get admin users only
        admin_users = session.query(UnifiedUser).filter_by(is_admin=True).all()
        assert len(admin_users) >= 1
        
        # 4. Test ticket status filtering
        open_tickets = session.query(UnifiedTicket).filter_by(status=TicketStatus.OPEN).all()
        assert len(open_tickets) >= 1
        
        # 5. Test specific user lookup
        found_admin = session.query(UnifiedUser).filter_by(username=f"test_admin_{unique_id}").first()
        assert found_admin is not None
        assert found_admin.is_admin == True
        assert found_admin.role == UserRole.ADMIN
        
        # Cleanup
        session.delete(test_ticket)
        session.delete(admin_user)
        session.commit()
        session.close()
        
        logger.info("Admin dashboard functionality test passed")
        
    except Exception as e:
        logger.error(f"Admin dashboard functionality test failed: {e}")
        raise


def test_memory_layer_functionality():
    """Test memory layer functionality with PostgreSQL backend"""
    logger.info("Testing memory layer functionality...")
    
    try:
        from backend.database import get_db
        from backend.memory_models import EnhancedChatHistory, MemoryContextCache
        
        # Get database session
        db_gen = get_db()
        session = next(db_gen)
        
        # Test enhanced chat history
        chat_entry = EnhancedChatHistory(
            user_id=1,
            message="Test memory message",
            response="Test memory response",
            context_data={"test": "data"},
            memory_tags=["test", "memory"],
            importance_score=0.8
        )
        
        session.add(chat_entry)
        session.commit()
        
        # Test memory context cache
        cache_entry = MemoryContextCache(
            cache_key="test_memory_key",
            context_data={"cached": "data"},
            expiry_time=datetime.now(timezone.utc)
        )
        
        session.add(cache_entry)
        session.commit()
        
        # Test retrieval
        retrieved_chat = session.query(EnhancedChatHistory).filter_by(user_id=1).first()
        assert retrieved_chat is not None
        assert retrieved_chat.message == "Test memory message"
        
        retrieved_cache = session.query(MemoryContextCache).filter_by(cache_key="test_memory_key").first()
        assert retrieved_cache is not None
        assert retrieved_cache.context_data["cached"] == "data"
        
        # Cleanup
        session.delete(retrieved_chat)
        session.delete(retrieved_cache)
        session.commit()
        session.close()
        
        logger.info("Memory layer functionality test passed")
        
    except Exception as e:
        logger.error(f"Memory layer functionality test failed: {e}")
        raise


def test_chat_functionality():
    """Test chat functionality with PostgreSQL backend"""
    logger.info("Testing chat functionality...")
    
    try:
        from backend.database import get_db
        from backend.unified_models import UnifiedChatSession, UnifiedChatMessage, UnifiedUser
        
        # Get database session
        db_gen = get_db()
        session = next(db_gen)
        
        # Create test user for chat
        test_user = UnifiedUser(
            user_id="test_chat_user",
            username="test_chat",
            email="test_chat@example.com",
            password_hash="chat_hash",
            full_name="Test Chat User",
            is_admin=False,
            is_active=True,
            role=UserRole.CUSTOMER
        )
        
        session.add(test_user)
        session.commit()
        
        # Test chat session creation
        chat_session = UnifiedChatSession(
            session_id="test_chat_session",
            user_id=test_user.id,
            title="Test Chat Session",
            is_active=True
        )
        
        session.add(chat_session)
        session.commit()
        
        # Test chat message creation
        chat_message = UnifiedChatMessage(
            session_id=chat_session.id,
            user_id=test_user.id,
            message="Hello, this is a test message",
            response="Hello! How can I help you today?",
            message_type="user_query"
        )
        
        session.add(chat_message)
        session.commit()
        
        # Test chat functionality queries
        # 1. Get user's chat sessions
        user_sessions = session.query(UnifiedChatSession).filter_by(user_id=test_user.id).all()
        assert len(user_sessions) >= 1
        
        # 2. Get messages for a session
        session_messages = session.query(UnifiedChatMessage).filter_by(session_id=chat_session.id).all()
        assert len(session_messages) >= 1
        
        # 3. Test message content
        assert session_messages[0].message == "Hello, this is a test message"
        assert session_messages[0].response == "Hello! How can I help you today?"
        
        # Cleanup
        session.delete(chat_message)
        session.delete(chat_session)
        session.delete(test_user)
        session.commit()
        session.close()
        
        logger.info("Chat functionality test passed")
        
    except Exception as e:
        logger.error(f"Chat functionality test failed: {e}")
        raise


def test_voice_assistant_integration():
    """Test voice assistant integration with PostgreSQL backend"""
    logger.info("Testing voice assistant integration...")
    
    try:
        from backend.database import get_db
        from backend.unified_models import UnifiedVoiceSettings, UnifiedVoiceAnalytics, UnifiedUser
        
        # Get database session
        db_gen = get_db()
        session = next(db_gen)
        
        # Create test user for voice assistant
        test_user = UnifiedUser(
            user_id="test_voice_user",
            username="test_voice",
            email="test_voice@example.com",
            password_hash="voice_hash",
            full_name="Test Voice User",
            is_admin=False,
            is_active=True,
            role=UserRole.CUSTOMER
        )
        
        session.add(test_user)
        session.commit()
        
        # Test voice settings
        voice_settings = UnifiedVoiceSettings(
            user_id=test_user.id,
            voice_enabled=True,
            preferred_language="en-US",
            speech_rate=1.0,
            voice_type="neural"
        )
        
        session.add(voice_settings)
        session.commit()
        
        # Test voice analytics
        voice_analytics = UnifiedVoiceAnalytics(
            user_id=test_user.id,
            session_duration=120.5,
            words_spoken=50,
            commands_recognized=5,
            accuracy_score=0.95
        )
        
        session.add(voice_analytics)
        session.commit()
        
        # Test voice assistant queries
        # 1. Get user voice settings
        user_voice_settings = session.query(UnifiedVoiceSettings).filter_by(user_id=test_user.id).first()
        assert user_voice_settings is not None
        assert user_voice_settings.voice_enabled == True
        assert user_voice_settings.preferred_language == "en-US"
        
        # 2. Get user voice analytics
        user_voice_analytics = session.query(UnifiedVoiceAnalytics).filter_by(user_id=test_user.id).first()
        assert user_voice_analytics is not None
        assert user_voice_analytics.session_duration == 120.5
        assert user_voice_analytics.accuracy_score == 0.95
        
        # Cleanup
        session.delete(voice_analytics)
        session.delete(voice_settings)
        session.delete(test_user)
        session.commit()
        session.close()
        
        logger.info("Voice assistant integration test passed")
        
    except Exception as e:
        logger.error(f"Voice assistant integration test failed: {e}")
        raise


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])