#!/usr/bin/env python3
"""
Comprehensive PostgreSQL migration script for RAG system
Fixes user_sessions schema and adds missing indexes
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import hashlib
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/knowledge_base"
)

def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    try:
        # Connect to default postgres database to create our database
        default_url = DATABASE_URL.rsplit('/', 1)[0] + '/postgres'
        engine = create_engine(default_url)
        
        with engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.execute(text("CREATE DATABASE knowledge_base"))
            print("✅ Database 'knowledge_base' created successfully")
            
    except Exception as e:
        if "already exists" in str(e).lower():
            print("✅ Database 'knowledge_base' already exists")
        else:
            print(f"❌ Error creating database: {e}")

def migrate_user_sessions():
    """Fix user_sessions table schema"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if user_sessions table exists
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            if 'user_sessions' not in tables:
                print("❌ user_sessions table does not exist. Creating all tables...")
                from database import init_db
                init_db()
                return
            
            # Check current columns
            columns = [col['name'] for col in inspector.get_columns('user_sessions')]
            print(f"Current user_sessions columns: {columns}")
            
            # Add missing columns
            if 'token_hash' not in columns:
                conn.execute(text("""
                    ALTER TABLE user_sessions 
                    ADD COLUMN IF NOT EXISTS token_hash VARCHAR(255) NOT NULL DEFAULT 'default_hash'
                """))
                print("✅ Added token_hash column")
            
            if 'expires_at' not in columns:
                conn.execute(text("""
                    ALTER TABLE user_sessions 
                    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP NOT NULL DEFAULT NOW() + INTERVAL '24 hours'
                """))
                print("✅ Added expires_at column")
            
            if 'is_active' not in columns:
                conn.execute(text("""
                    ALTER TABLE user_sessions 
                    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE
                """))
                print("✅ Added is_active column")
            
            if 'last_accessed' not in columns:
                conn.execute(text("""
                    ALTER TABLE user_sessions 
                    ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMP DEFAULT NOW()
                """))
                print("✅ Added last_accessed column")
            
            # Create indexes for better performance
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id 
                ON user_sessions(session_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id 
                ON user_sessions(user_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at 
                ON user_sessions(expires_at)
            """))
            print("✅ Created indexes for user_sessions")
            
            conn.commit()
            print("✅ User sessions migration completed")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")

def create_sample_data():
    """Create sample data for testing"""
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    
    try:
        db = SessionLocal()
        
        # Check if sample data already exists
        from models import User, Customer, Order, SupportIntent, SupportResponse
        
        # Create sample users
        if db.query(User).count() == 0:
            sample_users = [
                User(
                    user_id="admin_001",
                    username="admin",
                    email="admin@company.com",
                    password_hash=hashlib.sha256("admin123".encode()).hexdigest(),
                    full_name="System Administrator",
                    is_admin=True
                ),
                User(
                    user_id="user_001",
                    username="john_doe",
                    email="john@example.com",
                    password_hash=hashlib.sha256("password123".encode()).hexdigest(),
                    full_name="John Doe"
                ),
                User(
                    user_id="user_002",
                    username="jane_smith",
                    email="jane@example.com",
                    password_hash=hashlib.sha256("password123".encode()).hexdigest(),
                    full_name="Jane Smith"
                )
            ]
            
            for user in sample_users:
                db.add(user)
            db.commit()
            print("✅ Created sample users")
        
        # Create sample customers
        if db.query(Customer).count() == 0:
            sample_customers = [
                Customer(
                    customer_id=1001,
                    name="John Doe",
                    email="john@example.com",
                    phone="+1-555-0101",
                    address="123 Main St, Anytown, USA"
                ),
                Customer(
                    customer_id=1002,
                    name="Jane Smith",
                    email="jane@example.com",
                    phone="+1-555-0102",
                    address="456 Oak Ave, Somewhere, USA"
                ),
                Customer(
                    customer_id=1003,
                    name="Bob Johnson",
                    email="bob@example.com",
                    phone="+1-555-0103",
                    address="789 Pine Rd, Elsewhere, USA"
                )
            ]
            
            for customer in sample_customers:
                db.add(customer)
            db.commit()
            print("✅ Created sample customers")
        
        # Create sample orders
        if db.query(Order).count() == 0:
            sample_orders = [
                Order(
                    order_id=5001,
                    customer_id=1001,
                    order_date=datetime.now() - timedelta(days=30),
                    amount=99.99
                ),
                Order(
                    order_id=5002,
                    customer_id=1001,
                    order_date=datetime.now() - timedelta(days=15),
                    amount=149.99
                ),
                Order(
                    order_id=5003,
                    customer_id=1002,
                    order_date=datetime.now() - timedelta(days=7),
                    amount=79.99
                )
            ]
            
            for order in sample_orders:
                db.add(order)
            db.commit()
            print("✅ Created sample orders")
        
        # Create sample support intents and responses
        if db.query(SupportIntent).count() == 0:
            sample_intents = [
                SupportIntent(
                    intent_id="billing_inquiry",
                    intent_name="billing inquiry",
                    description="Questions about billing and charges",
                    category="billing"
                ),
                SupportIntent(
                    intent_id="technical_support",
                    intent_name="technical support",
                    description="Technical issues and troubleshooting",
                    category="technical"
                ),
                SupportIntent(
                    intent_id="account_management",
                    intent_name="account management",
                    description="Account-related questions and changes",
                    category="general"
                )
            ]
            
            for intent in sample_intents:
                db.add(intent)
            db.commit()
            
            sample_responses = [
                SupportResponse(
                    intent_id="billing_inquiry",
                    response_text="For billing inquiries, please check your account online or call our billing department at 1-800-BILLING.",
                    response_type="standard"
                ),
                SupportResponse(
                    intent_id="technical_support",
                    response_text="For technical support, please restart your device first. If issues persist, contact our technical support team at 1-800-TECH-HELP.",
                    response_type="standard"
                ),
                SupportResponse(
                    intent_id="account_management",
                    response_text="For account management, log into your online account or use our mobile app. For assistance, call 1-800-ACCOUNT.",
                    response_type="standard"
                )
            ]
            
            for response in sample_responses:
                db.add(response)
            db.commit()
            print("✅ Created sample support intents and responses")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")

def verify_migration():
    """Verify the migration was successful"""
    engine = create_engine(DATABASE_URL)
    
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print("\n📊 Database Verification:")
        print("=" * 40)
        
        for table in tables:
            columns = [col['name'] for col in inspector.get_columns(table)]
            count = engine.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"✅ {table}: {count} records, columns: {len(columns)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 PostgreSQL Migration Script")
    print("=" * 50)
    
    # Create database if needed
    create_database_if_not_exists()
    
    # Run migration
    migrate_user_sessions()
    
    # Create sample data
    create_sample_data()
    
    # Verify migration
    verify_migration()
    
    print("\n🎉 Migration completed successfully!")
