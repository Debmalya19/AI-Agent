#!/usr/bin/env python3
"""
Comprehensive database setup script for knowledge base
This script will:
1. Install required dependencies
2. Create database tables
3. Migrate existing data
4. Verify setup
"""

import subprocess
import sys
import os
from pathlib import Path

def install_dependencies():
    """Install required database dependencies"""
    print("Installing database dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirement.text"])
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False
    return True

def setup_database():
    """Initialize database with tables"""
    print("Setting up database...")
    try:
        from database_init import init_db
        init_db()
        print("✓ Database tables created")
    except Exception as e:
        print(f"✗ Failed to create database tables: {e}")
        return False
    return True

def migrate_data():
    """Migrate existing knowledge base data"""
    print("Migrating existing data...")
    try:
        from migrate_data import migrate_all
        migrate_all()
        print("✓ Data migration completed")
    except Exception as e:
        print(f"✗ Failed to migrate data: {e}")
        return False
    return True

def verify_setup():
    """Verify database setup"""
    print("Verifying database setup...")
    try:
        from database import SessionLocal
        from models import KnowledgeEntry, Customer, SupportIntent
        
        db = SessionLocal()
        
        # Check if tables have data
        knowledge_count = db.query(KnowledgeEntry).count()
        customer_count = db.query(Customer).count()
        support_count = db.query(SupportIntent).count()
        
        print(f"✓ Knowledge entries: {knowledge_count}")
        print(f"✓ Customers: {customer_count}")
        print(f"✓ Support intents: {support_count}")
        
        db.close()
        
        if knowledge_count > 0 or customer_count > 0 or support_count > 0:
            print("✓ Database setup verified successfully")
            return True
        else:
            print("⚠ Database is empty - run migration to populate data")
            return True
            
    except Exception as e:
        print(f"✗ Failed to verify setup: {e}")
        return False

def create_env_file():
    """Create .env file from .env.example"""
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file...")
        env_example.replace(env_file)
        print("✓ .env file created - please update with your database credentials")
    elif env_file.exists():
        print("✓ .env file already exists")
    else:
        print("⚠ .env.example not found - please create .env file manually")

def main():
    """Main setup process"""
    print("=" * 50)
    print("Knowledge Base Database Setup")
    print("=" * 50)
    
    # Create .env file
    create_env_file()
    
    # Check if .env is configured
    if not os.path.exists(".env"):
        print("Please configure your .env file before proceeding")
        return
    
    # Setup steps
    steps = [
        ("Install Dependencies", install_dependencies),
        ("Setup Database", setup_database),
        ("Migrate Data", migrate_data),
        ("Verify Setup", verify_setup)
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if not step_func():
            print(f"Failed at: {step_name}")
            return
    
    print("\n" + "=" * 50)
    print("Database setup completed successfully!")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Update your .env file with correct database credentials")
    print("2. Run: python setup_database.py")
    print("3. Update main.py to use database instead of in-memory storage")

if __name__ == "__main__":
    main()
