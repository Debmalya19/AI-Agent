#!/usr/bin/env python3
"""
Database migration script for memory layer enhancement.
This script creates the new tables required for the memory layer functionality
while preserving existing data.
"""

import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Base, DATABASE_URL, engine
from memory_models import (
    EnhancedChatHistory,
    MemoryContextCache,
    ToolUsageMetrics,
    ConversationSummary,
    MemoryConfiguration,
    MemoryHealthMetrics
)

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

def check_existing_tables():
    """Check which tables already exist in the database"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    memory_tables = [
        'enhanced_chat_history',
        'memory_context_cache',
        'tool_usage_metrics',
        'conversation_summaries',
        'memory_configuration',
        'memory_health_metrics'
    ]
    
    existing_memory_tables = [table for table in memory_tables if table in existing_tables]
    missing_memory_tables = [table for table in memory_tables if table not in existing_tables]
    
    print(f"📊 Existing tables: {len(existing_tables)}")
    print(f"📊 Existing memory tables: {existing_memory_tables}")
    print(f"📊 Missing memory tables: {missing_memory_tables}")
    
    return existing_tables, existing_memory_tables, missing_memory_tables

def create_memory_tables():
    """Create the new memory layer tables"""
    try:
        print("🔧 Creating memory layer tables...")
        
        # Create all tables defined in memory_models
        Base.metadata.create_all(bind=engine, tables=[
            EnhancedChatHistory.__table__,
            MemoryContextCache.__table__,
            ToolUsageMetrics.__table__,
            ConversationSummary.__table__,
            MemoryConfiguration.__table__,
            MemoryHealthMetrics.__table__
        ])
        
        print("✅ Memory layer tables created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create memory tables: {e}")
        return False

def migrate_existing_chat_history():
    """Migrate existing chat_history data to enhanced_chat_history"""
    try:
        print("🔄 Migrating existing chat history...")
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Check if there's existing chat history to migrate
        result = db.execute(text("SELECT COUNT(*) FROM chat_history"))
        count = result.scalar()
        
        if count == 0:
            print("📝 No existing chat history to migrate")
            db.close()
            return True
        
        print(f"📝 Found {count} chat history entries to migrate")
        
        # Migrate data from chat_history to enhanced_chat_history
        migrate_query = text("""
            INSERT INTO enhanced_chat_history 
            (session_id, user_id, user_message, bot_response, tools_used, created_at)
            SELECT 
                session_id,
                COALESCE(session_id, 'unknown') as user_id,
                user_message,
                bot_response,
                tools_used,
                created_at
            FROM chat_history
            WHERE NOT EXISTS (
                SELECT 1 FROM enhanced_chat_history ech 
                WHERE ech.session_id = chat_history.session_id 
                AND ech.created_at = chat_history.created_at
            )
        """)
        
        result = db.execute(migrate_query)
        db.commit()
        
        migrated_count = result.rowcount
        print(f"✅ Migrated {migrated_count} chat history entries")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to migrate chat history: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
        return False

def create_default_configurations():
    """Create default memory configuration entries"""
    try:
        print("⚙️ Creating default memory configurations...")
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        default_configs = [
            {
                'config_key': 'retention_policy',
                'config_value': {
                    'chat_history_days': 90,
                    'context_cache_hours': 24,
                    'tool_metrics_days': 30,
                    'conversation_summaries_days': 365
                },
                'config_type': 'retention',
                'description': 'Data retention policies for memory components'
            },
            {
                'config_key': 'performance_settings',
                'config_value': {
                    'max_context_entries': 50,
                    'cache_size_mb': 100,
                    'similarity_threshold': 0.7,
                    'max_conversation_length': 1000
                },
                'config_type': 'performance',
                'description': 'Performance optimization settings'
            },
            {
                'config_key': 'quality_thresholds',
                'config_value': {
                    'min_response_quality': 0.6,
                    'tool_success_threshold': 0.8,
                    'context_relevance_threshold': 0.5
                },
                'config_type': 'quality',
                'description': 'Quality thresholds for memory operations'
            }
        ]
        
        from memory_models import MemoryConfiguration
        
        for config in default_configs:
            # Check if config already exists
            existing = db.query(MemoryConfiguration).filter(
                MemoryConfiguration.config_key == config['config_key']
            ).first()
            
            if not existing:
                new_config = MemoryConfiguration(**config)
                db.add(new_config)
        
        db.commit()
        print("✅ Default configurations created")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to create default configurations: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
        return False

def create_initial_health_metrics():
    """Create initial health metrics entries"""
    try:
        print("📊 Creating initial health metrics...")
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        from memory_models import MemoryHealthMetrics
        
        initial_metrics = [
            {
                'metric_name': 'memory_system_initialized',
                'metric_value': 1.0,
                'metric_unit': 'boolean',
                'metric_category': 'system'
            },
            {
                'metric_name': 'database_tables_created',
                'metric_value': 6.0,  # Number of memory tables created
                'metric_unit': 'count',
                'metric_category': 'system'
            }
        ]
        
        for metric in initial_metrics:
            new_metric = MemoryHealthMetrics(**metric)
            db.add(new_metric)
        
        db.commit()
        print("✅ Initial health metrics created")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to create initial health metrics: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
        return False

def verify_migration():
    """Verify that the migration was successful"""
    try:
        print("🔍 Verifying migration...")
        
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        required_tables = [
            'enhanced_chat_history',
            'memory_context_cache',
            'tool_usage_metrics',
            'conversation_summaries',
            'memory_configuration',
            'memory_health_metrics'
        ]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
        
        # Check table structures
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Verify we can query each table
        for table in required_tables:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"✅ {table}: {count} records")
            except Exception as e:
                print(f"❌ Error querying {table}: {e}")
                db.close()
                return False
        
        db.close()
        print("✅ Migration verification successful")
        return True
        
    except Exception as e:
        print(f"❌ Migration verification failed: {e}")
        return False

def main():
    """Main migration process"""
    print("🚀 Memory Layer Database Migration")
    print("=" * 50)
    
    # Check database connection
    if not check_database_connection():
        print("❌ Cannot proceed without database connection")
        sys.exit(1)
    
    # Check existing tables
    existing_tables, existing_memory_tables, missing_memory_tables = check_existing_tables()
    
    if not missing_memory_tables:
        print("✅ All memory tables already exist")
    else:
        # Create memory tables
        if not create_memory_tables():
            print("❌ Failed to create memory tables")
            sys.exit(1)
    
    # Migrate existing data
    if not migrate_existing_chat_history():
        print("❌ Failed to migrate existing chat history")
        sys.exit(1)
    
    # Create default configurations
    if not create_default_configurations():
        print("❌ Failed to create default configurations")
        sys.exit(1)
    
    # Create initial health metrics
    if not create_initial_health_metrics():
        print("❌ Failed to create initial health metrics")
        sys.exit(1)
    
    # Verify migration
    if not verify_migration():
        print("❌ Migration verification failed")
        sys.exit(1)
    
    print("\n🎉 Memory layer migration completed successfully!")
    print("📝 Next steps:")
    print("   1. Update your application to use the new memory models")
    print("   2. Implement the Memory Layer Manager")
    print("   3. Test the enhanced memory functionality")

if __name__ == "__main__":
    main()