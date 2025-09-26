#!/usr/bin/env python3
"""
Test script for PostgreSQL migration functionality

This script tests the migration components without performing actual migration.
"""

import os
import sys
import tempfile
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import text

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scripts.migrate_to_postgresql import DatabaseMigrator, MigrationConfig

def create_test_sqlite_db(db_path: str):
    """Create a test SQLite database with sample data"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create test tables
    cursor.execute("""
        CREATE TABLE test_users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    
    cursor.execute("""
        CREATE TABLE test_posts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            title TEXT,
            content TEXT,
            metadata TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES test_users (id)
        )
    """)
    
    # Insert test data
    test_users = [
        (1, 'alice', 'alice@example.com', datetime.now(timezone.utc).isoformat(), 1),
        (2, 'bob', 'bob@example.com', datetime.now(timezone.utc).isoformat(), 1),
        (3, 'charlie', 'charlie@example.com', datetime.now(timezone.utc).isoformat(), 0),
    ]
    
    cursor.executemany(
        "INSERT INTO test_users (id, username, email, created_at, is_active) VALUES (?, ?, ?, ?, ?)",
        test_users
    )
    
    test_posts = [
        (1, 1, 'First Post', 'This is Alice\'s first post', '{"tags": ["intro"]}', datetime.now(timezone.utc).isoformat()),
        (2, 1, 'Second Post', 'Alice\'s second post', '{"tags": ["update"]}', datetime.now(timezone.utc).isoformat()),
        (3, 2, 'Bob\'s Post', 'Hello from Bob', '{"tags": ["greeting"]}', datetime.now(timezone.utc).isoformat()),
    ]
    
    cursor.executemany(
        "INSERT INTO test_posts (id, user_id, title, content, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        test_posts
    )
    
    conn.commit()
    conn.close()
    print(f"Created test SQLite database: {db_path}")

def test_migration_components():
    """Test migration components"""
    print("Testing migration components...")
    
    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test SQLite database
        sqlite_path = temp_path / "test.db"
        create_test_sqlite_db(str(sqlite_path))
        
        # Create migration config
        config = MigrationConfig(
            sqlite_url=f"sqlite:///{sqlite_path}",
            postgresql_url="postgresql://test:test@localhost:5432/test_db",  # This won't connect
            backup_dir=str(temp_path / "backups"),
            batch_size=10,
            validate_data=True,
            create_rollback=True,
            preserve_ids=True
        )
        
        # Create migrator
        migrator = DatabaseMigrator(config)
        
        # Test SQLite connection setup (only SQLite, skip PostgreSQL)
        print("Testing SQLite connection...")
        try:
            from sqlalchemy import create_engine
            migrator.sqlite_engine = create_engine(
                config.sqlite_url,
                connect_args={"check_same_thread": False}
            )
            
            with migrator.sqlite_engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM test_users"))
                count = result.fetchone()[0]
                print(f"✓ SQLite connection successful, found {count} test users")
        except Exception as e:
            print(f"✗ SQLite connection failed: {e}")
        
        # Test data export
        print("Testing data export...")
        try:
            data = migrator.export_table_data("test_users")
            if data is not None:
                print(f"✓ Data export successful, exported {len(data)} records")
                print(f"  Sample record: {data[0] if data else 'No data'}")
            else:
                print("✗ Data export failed")
        except Exception as e:
            print(f"✗ Data export failed: {e}")
        
        # Close SQLite connection to avoid file lock
        if migrator.sqlite_engine:
            migrator.sqlite_engine.dispose()
        
        # Test backup creation
        print("Testing backup creation...")
        try:
            if migrator.create_backup():
                print(f"✓ Backup creation successful: {migrator.backup_path}")
            else:
                print("✗ Backup creation failed")
        except Exception as e:
            print(f"✗ Backup creation failed: {e}")
        
        # Test data type processing
        print("Testing data type processing...")
        try:
            test_row = {
                'id': 1,
                'username': 'test',
                'email': 'test@example.com',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'is_active': True,
                'metadata': '{"key": "value"}'
            }
            
            # Create a mock table for testing
            from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Boolean, JSON
            metadata = MetaData()
            mock_table = Table('test_table', metadata,
                Column('id', Integer, primary_key=True),
                Column('username', String(100)),
                Column('email', String(255)),
                Column('created_at', DateTime),
                Column('is_active', Boolean),
                Column('metadata', JSON)
            )
            
            processed_row = migrator._process_row_for_postgresql(test_row, mock_table)
            if processed_row:
                print("✓ Data type processing successful")
                print(f"  Processed row: {processed_row}")
            else:
                print("✗ Data type processing failed")
        except Exception as e:
            print(f"✗ Data type processing failed: {e}")
        
        print("Component testing completed!")

def test_migration_config():
    """Test migration configuration"""
    print("Testing migration configuration...")
    
    try:
        config = MigrationConfig(
            sqlite_url="sqlite:///test.db",
            postgresql_url="postgresql://user:pass@localhost:5432/db"
        )
        
        print("✓ Migration config creation successful")
        print(f"  SQLite URL: {config.sqlite_url}")
        print(f"  PostgreSQL URL: {config.postgresql_url}")
        print(f"  Batch size: {config.batch_size}")
        print(f"  Validate data: {config.validate_data}")
        print(f"  Create rollback: {config.create_rollback}")
        
    except Exception as e:
        print(f"✗ Migration config creation failed: {e}")

def main():
    """Main test function"""
    print("=" * 60)
    print("PostgreSQL Migration Script Test")
    print("=" * 60)
    
    test_migration_config()
    print()
    test_migration_components()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()