#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script

This script creates the PostgreSQL database and user accounts for the AI agent application.
It handles database creation, user setup, and permission configuration.
"""

import os
import sys
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_database_url(database_url):
    """Parse PostgreSQL database URL into components"""
    if not database_url.startswith('postgresql://'):
        raise ValueError("Invalid PostgreSQL URL format")
    
    # Remove postgresql:// prefix
    url = database_url[13:]
    
    # Split user:password@host:port/database
    if '@' in url:
        auth_part, host_part = url.split('@', 1)
        if ':' in auth_part:
            username, password = auth_part.split(':', 1)
        else:
            username, password = auth_part, ''
    else:
        raise ValueError("No authentication information in database URL")
    
    if '/' in host_part:
        host_port, database = host_part.split('/', 1)
    else:
        raise ValueError("No database name in URL")
    
    if ':' in host_port:
        host, port = host_port.split(':', 1)
        port = int(port)
    else:
        host, port = host_port, 5432
    
    return {
        'host': host,
        'port': port,
        'username': username,
        'password': password,
        'database': database
    }

def create_database_and_user(db_config):
    """Create PostgreSQL database and user if they don't exist"""
    
    # Connect to PostgreSQL server (not to specific database)
    try:
        # Connect to default postgres database to create our database
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            user='postgres',  # Assume postgres superuser exists
            password=os.getenv('POSTGRES_ADMIN_PASSWORD', 'postgres'),
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        database_name = db_config['database'].replace('.db', '')  # Remove .db extension if present
        
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (database_name,))
        if not cursor.fetchone():
            logger.info(f"Creating database: {database_name}")
            cursor.execute(f'CREATE DATABASE "{database_name}"')
            logger.info(f"Database {database_name} created successfully")
        else:
            logger.info(f"Database {database_name} already exists")
        
        # Create user if it doesn't exist
        username = db_config['username']
        password = db_config['password']
        
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (username,))
        if not cursor.fetchone():
            logger.info(f"Creating user: {username}")
            cursor.execute(f"CREATE USER \"{username}\" WITH PASSWORD %s", (password,))
            logger.info(f"User {username} created successfully")
        else:
            logger.info(f"User {username} already exists")
        
        # Grant privileges
        logger.info(f"Granting privileges to {username} on database {database_name}")
        cursor.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{database_name}" TO "{username}"')
        cursor.execute(f'ALTER USER "{username}" CREATEDB')  # Allow creating test databases
        
        cursor.close()
        conn.close()
        
        logger.info("Database and user setup completed successfully")
        return True
        
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def test_connection(db_config):
    """Test connection to the created database"""
    try:
        database_name = db_config['database'].replace('.db', '')
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['username'],
            password=db_config['password'],
            database=database_name
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        logger.info(f"Successfully connected to PostgreSQL: {version}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        logger.error(f"Connection test failed: {e}")
        return False

def main():
    """Main setup function"""
    load_dotenv()
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    try:
        # Parse database configuration
        db_config = parse_database_url(database_url)
        logger.info(f"Setting up PostgreSQL database: {db_config['database']} on {db_config['host']}:{db_config['port']}")
        
        # Create database and user
        if create_database_and_user(db_config):
            # Test the connection
            if test_connection(db_config):
                logger.info("PostgreSQL setup completed successfully!")
                return True
            else:
                logger.error("Connection test failed")
                return False
        else:
            logger.error("Database setup failed")
            return False
            
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)