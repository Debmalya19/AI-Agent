#!/usr/bin/env python3
"""
Test Database Setup Script

This script creates the test database for PostgreSQL migration testing.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

def setup_test_database():
    """Create the test database if it doesn't exist"""
    load_dotenv()
    
    # Try different common passwords
    passwords_to_try = [
        os.getenv('POSTGRES_ADMIN_PASSWORD', 'postgres'),
        'postgres',
        'password',
        'admin',
        '123456',
        ''  # No password
    ]
    
    test_db_name = 'test_ai_agent'
    conn = None
    
    # Try to connect with different passwords
    for password in passwords_to_try:
        admin_db_config = {
            'host': 'localhost',
            'port': 5432,
            'user': 'postgres',
            'password': password,
            'database': 'postgres'  # Connect to default postgres database
        }
        
        try:
            print(f"Trying to connect with password: {'(empty)' if not password else '***'}")
            conn = psycopg2.connect(**admin_db_config)
            print("✓ Successfully connected to PostgreSQL server")
            break
        except psycopg2.Error as e:
            print(f"✗ Failed with password {'(empty)' if not password else '***'}: {e}")
            continue
    
    if not conn:
        print("✗ Could not connect to PostgreSQL with any common password")
        print("Please check your PostgreSQL installation and credentials")
        return False
    
    try:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if test database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (test_db_name,)
        )
        
        if cursor.fetchone():
            print(f"Test database '{test_db_name}' already exists")
        else:
            # Create test database
            print(f"Creating test database '{test_db_name}'...")
            cursor.execute(f'CREATE DATABASE "{test_db_name}"')
            print(f"✓ Test database '{test_db_name}' created successfully")
        
        cursor.close()
        conn.close()
        
        # Test connection to new database
        test_db_config = admin_db_config.copy()
        test_db_config['database'] = test_db_name
        
        print(f"Testing connection to '{test_db_name}'...")
        test_conn = psycopg2.connect(**test_db_config)
        test_cursor = test_conn.cursor()
        test_cursor.execute("SELECT version()")
        version = test_cursor.fetchone()[0]
        print(f"✓ Successfully connected to test database")
        print(f"  PostgreSQL version: {version}")
        
        test_cursor.close()
        test_conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"✗ PostgreSQL error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def drop_test_database():
    """Drop the test database"""
    load_dotenv()
    
    admin_db_config = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': os.getenv('POSTGRES_ADMIN_PASSWORD', 'password'),
        'database': 'postgres'
    }
    
    test_db_name = 'test_ai_agent'
    
    try:
        print("Connecting to PostgreSQL server...")
        conn = psycopg2.connect(**admin_db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Terminate existing connections to the test database
        cursor.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
        """, (test_db_name,))
        
        # Drop test database
        print(f"Dropping test database '{test_db_name}'...")
        cursor.execute(f'DROP DATABASE IF EXISTS "{test_db_name}"')
        print(f"✓ Test database '{test_db_name}' dropped successfully")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"✗ PostgreSQL error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Database Setup")
    parser.add_argument("--drop", action="store_true", help="Drop test database")
    parser.add_argument("--recreate", action="store_true", help="Drop and recreate test database")
    
    args = parser.parse_args()
    
    if args.drop or args.recreate:
        print("Dropping test database...")
        drop_test_database()
    
    if not args.drop:
        print("Setting up test database...")
        success = setup_test_database()
        
        if success:
            print("\n✓ Test database setup completed successfully!")
            print("You can now run migration tests with:")
            print("  python run_migration_tests.py")
        else:
            print("\n✗ Test database setup failed!")
            sys.exit(1)

if __name__ == "__main__":
    main()