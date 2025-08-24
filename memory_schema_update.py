#!/usr/bin/env python3
"""
Database schema update script for memory layer enhancements.
This script adds missing columns to existing memory tables.
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect, Column, String, DateTime, JSON, Boolean
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine

load_dotenv()

def check_database_connection():
    """Check if database connection is available"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_table_columns(table_name):
    """Check which columns exist in a table"""
    inspector = inspect(engine)
    try:
        columns = inspector.get_columns(table_name)
        column_names = [col['name'] for col in columns]
        print(f"📊 {table_name} existing columns: {column_names}")
        return column_names
    except Exception as e:
        print(f"❌ Error checking columns for {table_name}: {e}")
        return []

def add_missing_columns():
    """Add missing columns to existing tables"""
    try:
        print("🔧 Adding missing columns to memory tables...")
        
        with engine.connect() as conn:
            # Add missing columns to enhanced_chat_history
            enhanced_chat_columns = check_table_columns('enhanced_chat_history')
            
            missing_enhanced_columns = [
                ('user_message_encrypted', 'JSON'),
                ('bot_response_encrypted', 'JSON'),
                ('data_classification', 'VARCHAR(50) DEFAULT \'internal\''),
                ('retention_policy', 'VARCHAR(100)'),
                ('deleted_at', 'TIMESTAMP'),
                ('anonymized_at', 'TIMESTAMP')
            ]
            
            for col_name, col_type in missing_enhanced_columns:
                if col_name not in enhanced_chat_columns:
                    try:
                        alter_sql = f"ALTER TABLE enhanced_chat_history ADD COLUMN {col_name} {col_type}"
                        conn.execute(text(alter_sql))
                        print(f"✅ Added column {col_name} to enhanced_chat_history")
                    except Exception as e:
                        print(f"⚠️ Could not add column {col_name}: {e}")
            
            # Add missing columns to memory_context_cache
            context_cache_columns = check_table_columns('memory_context_cache')
            
            missing_context_columns = [
                ('context_data_encrypted', 'JSON'),
                ('data_classification', 'VARCHAR(50) DEFAULT \'internal\''),
                ('access_control', 'JSON')
            ]
            
            for col_name, col_type in missing_context_columns:
                if col_name not in context_cache_columns:
                    try:
                        alter_sql = f"ALTER TABLE memory_context_cache ADD COLUMN {col_name} {col_type}"
                        conn.execute(text(alter_sql))
                        print(f"✅ Added column {col_name} to memory_context_cache")
                    except Exception as e:
                        print(f"⚠️ Could not add column {col_name}: {e}")
            
            # Check if enhanced_user_sessions table exists, if not create it
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            
            if 'enhanced_user_sessions' not in existing_tables:
                create_enhanced_user_sessions_sql = """
                CREATE TABLE enhanced_user_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    session_id VARCHAR(255) UNIQUE NOT NULL,
                    session_token_hash VARCHAR(128),
                    is_active BOOLEAN DEFAULT TRUE,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    session_metadata JSON,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                conn.execute(text(create_enhanced_user_sessions_sql))
                print("✅ Created enhanced_user_sessions table")
                
                # Create indexes
                indexes = [
                    "CREATE INDEX idx_enhanced_user_sessions_user_active ON enhanced_user_sessions(user_id, is_active)",
                    "CREATE INDEX idx_enhanced_user_sessions_expires ON enhanced_user_sessions(expires_at)",
                    "CREATE INDEX idx_enhanced_user_sessions_activity ON enhanced_user_sessions(last_activity)",
                    "CREATE INDEX idx_enhanced_user_sessions_user_id ON enhanced_user_sessions(user_id)",
                    "CREATE INDEX idx_enhanced_user_sessions_session_id ON enhanced_user_sessions(session_id)"
                ]
                
                for index_sql in indexes:
                    try:
                        conn.execute(text(index_sql))
                    except Exception as e:
                        print(f"⚠️ Could not create index: {e}")
            
            # Check if data_processing_consent table exists, if not create it
            if 'data_processing_consent' not in existing_tables:
                create_consent_sql = """
                CREATE TABLE data_processing_consent (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    consent_id VARCHAR(255) UNIQUE NOT NULL,
                    purpose VARCHAR(100) NOT NULL,
                    consent_given BOOLEAN NOT NULL,
                    consent_timestamp TIMESTAMP NOT NULL,
                    consent_method VARCHAR(50),
                    consent_version VARCHAR(20),
                    withdrawal_timestamp TIMESTAMP,
                    legal_basis VARCHAR(50) DEFAULT 'consent',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                conn.execute(text(create_consent_sql))
                print("✅ Created data_processing_consent table")
                
                # Create indexes
                consent_indexes = [
                    "CREATE INDEX idx_consent_user_purpose ON data_processing_consent(user_id, purpose)",
                    "CREATE INDEX idx_consent_given ON data_processing_consent(consent_given)",
                    "CREATE INDEX idx_consent_timestamp ON data_processing_consent(consent_timestamp)",
                    "CREATE INDEX idx_consent_user_id ON data_processing_consent(user_id)",
                    "CREATE INDEX idx_consent_purpose ON data_processing_consent(purpose)"
                ]
                
                for index_sql in consent_indexes:
                    try:
                        conn.execute(text(index_sql))
                    except Exception as e:
                        print(f"⚠️ Could not create consent index: {e}")
            
            # Check if data_subject_rights table exists, if not create it
            if 'data_subject_rights' not in existing_tables:
                create_dsr_sql = """
                CREATE TABLE data_subject_rights (
                    id SERIAL PRIMARY KEY,
                    request_id VARCHAR(255) UNIQUE NOT NULL,
                    user_id VARCHAR(50) NOT NULL,
                    request_type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    requested_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    request_details JSON,
                    response_data JSON,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                conn.execute(text(create_dsr_sql))
                print("✅ Created data_subject_rights table")
                
                # Create indexes
                dsr_indexes = [
                    "CREATE INDEX idx_dsr_user_type ON data_subject_rights(user_id, request_type)",
                    "CREATE INDEX idx_dsr_status ON data_subject_rights(status)",
                    "CREATE INDEX idx_dsr_requested ON data_subject_rights(requested_at)",
                    "CREATE INDEX idx_dsr_user_id ON data_subject_rights(user_id)",
                    "CREATE INDEX idx_dsr_request_type ON data_subject_rights(request_type)"
                ]
                
                for index_sql in dsr_indexes:
                    try:
                        conn.execute(text(index_sql))
                    except Exception as e:
                        print(f"⚠️ Could not create DSR index: {e}")
            
            conn.commit()
            print("✅ Schema update completed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Failed to update schema: {e}")
        return False

def verify_schema_update():
    """Verify that the schema update was successful"""
    try:
        print("🔍 Verifying schema update...")
        
        # Check enhanced_chat_history columns
        enhanced_columns = check_table_columns('enhanced_chat_history')
        required_enhanced_columns = [
            'user_message_encrypted', 'bot_response_encrypted', 
            'data_classification', 'retention_policy', 
            'deleted_at', 'anonymized_at'
        ]
        
        missing_enhanced = [col for col in required_enhanced_columns if col not in enhanced_columns]
        if missing_enhanced:
            print(f"❌ Missing enhanced_chat_history columns: {missing_enhanced}")
            return False
        
        # Check memory_context_cache columns
        context_columns = check_table_columns('memory_context_cache')
        required_context_columns = [
            'context_data_encrypted', 'data_classification', 'access_control'
        ]
        
        missing_context = [col for col in required_context_columns if col not in context_columns]
        if missing_context:
            print(f"❌ Missing memory_context_cache columns: {missing_context}")
            return False
        
        # Check if new tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        required_tables = ['enhanced_user_sessions', 'data_processing_consent', 'data_subject_rights']
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
        
        print("✅ Schema verification successful")
        return True
        
    except Exception as e:
        print(f"❌ Schema verification failed: {e}")
        return False

def main():
    """Main schema update process"""
    print("🚀 Memory Layer Schema Update")
    print("=" * 50)
    
    # Check database connection
    if not check_database_connection():
        print("❌ Cannot proceed without database connection")
        sys.exit(1)
    
    # Add missing columns
    if not add_missing_columns():
        print("❌ Failed to update schema")
        sys.exit(1)
    
    # Verify schema update
    if not verify_schema_update():
        print("❌ Schema verification failed")
        sys.exit(1)
    
    print("\n🎉 Memory layer schema update completed successfully!")
    print("📝 The application should now work with the enhanced memory models.")

if __name__ == "__main__":
    main()