#!/usr/bin/env python3
"""
Utility script to verify the memory layer database schema.
This script checks that all required tables and indexes are properly created.
"""

import sys
import os
from sqlalchemy import inspect, text

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal

def check_table_exists(table_name):
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def get_table_info(table_name):
    """Get detailed information about a table"""
    inspector = inspect(engine)
    
    if not check_table_exists(table_name):
        return None
    
    columns = inspector.get_columns(table_name)
    indexes = inspector.get_indexes(table_name)
    
    return {
        'columns': columns,
        'indexes': indexes,
        'column_count': len(columns),
        'index_count': len(indexes)
    }

def get_table_row_count(table_name):
    """Get the number of rows in a table"""
    try:
        db = SessionLocal()
        result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        count = result.scalar()
        db.close()
        return count
    except Exception as e:
        return f"Error: {e}"

def verify_memory_schema():
    """Verify the complete memory layer schema"""
    print("🔍 Memory Layer Schema Verification")
    print("=" * 60)
    
    # Define expected tables and their key characteristics
    expected_tables = {
        'enhanced_chat_history': {
            'required_columns': ['id', 'session_id', 'user_id', 'user_message', 'bot_response', 'tools_used'],
            'required_indexes': ['idx_enhanced_chat_user_session', 'idx_enhanced_chat_created']
        },
        'memory_context_cache': {
            'required_columns': ['id', 'cache_key', 'context_data', 'context_type', 'expires_at'],
            'required_indexes': ['idx_context_cache_user_type', 'idx_context_cache_expires']
        },
        'tool_usage_metrics': {
            'required_columns': ['id', 'tool_name', 'success_rate', 'usage_count'],
            'required_indexes': ['idx_tool_metrics_name_type', 'idx_tool_metrics_success']
        },
        'conversation_summaries': {
            'required_columns': ['id', 'user_id', 'summary_text', 'key_topics'],
            'required_indexes': ['idx_conversation_summary_user']
        },
        'memory_configuration': {
            'required_columns': ['id', 'config_key', 'config_value', 'config_type'],
            'required_indexes': []
        },
        'memory_health_metrics': {
            'required_columns': ['id', 'metric_name', 'metric_value', 'metric_category'],
            'required_indexes': ['idx_health_metrics_name_time']
        }
    }
    
    # Check database connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful\n")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Verify each table
    table_status = []
    all_tables_ok = True
    
    for table_name, requirements in expected_tables.items():
        print(f"📊 Checking table: {table_name}")
        
        # Check if table exists
        if not check_table_exists(table_name):
            print(f"❌ Table {table_name} does not exist")
            table_status.append([table_name, "❌ Missing", 0, 0, 0])
            all_tables_ok = False
            continue
        
        # Get table info
        table_info = get_table_info(table_name)
        row_count = get_table_row_count(table_name)
        
        # Check required columns
        existing_columns = [col['name'] for col in table_info['columns']]
        missing_columns = [col for col in requirements['required_columns'] if col not in existing_columns]
        
        # Check required indexes
        existing_indexes = [idx['name'] for idx in table_info['indexes']]
        missing_indexes = [idx for idx in requirements['required_indexes'] if idx not in existing_indexes]
        
        # Report status
        status = "✅ OK"
        if missing_columns or missing_indexes:
            status = "⚠️ Issues"
            all_tables_ok = False
            
            if missing_columns:
                print(f"   ❌ Missing columns: {missing_columns}")
            if missing_indexes:
                print(f"   ❌ Missing indexes: {missing_indexes}")
        
        table_status.append([
            table_name,
            status,
            table_info['column_count'],
            table_info['index_count'],
            row_count
        ])
        
        print(f"   📈 Columns: {table_info['column_count']}, Indexes: {table_info['index_count']}, Rows: {row_count}")
        print()
    
    # Summary table
    print("📋 Summary")
    print("-" * 60)
    print(f"{'Table':<25} {'Status':<12} {'Columns':<8} {'Indexes':<8} {'Rows':<8}")
    print("-" * 60)
    for row in table_status:
        print(f"{row[0]:<25} {row[1]:<12} {row[2]:<8} {row[3]:<8} {row[4]:<8}")
    
    # Overall status
    print("\n🎯 Overall Status")
    print("-" * 60)
    if all_tables_ok:
        print("✅ All memory layer tables are properly configured")
        print("🚀 Memory layer is ready for use")
        return True
    else:
        print("❌ Some issues found with memory layer schema")
        print("🔧 Run the migration script to fix issues")
        return False

def show_sample_data():
    """Show sample data from memory tables"""
    print("\n📄 Sample Data")
    print("-" * 60)
    
    sample_tables = ['memory_configuration', 'memory_health_metrics']
    
    for table_name in sample_tables:
        if not check_table_exists(table_name):
            continue
            
        print(f"\n📊 Sample from {table_name}:")
        try:
            db = SessionLocal()
            result = db.execute(text(f"SELECT * FROM {table_name} LIMIT 3"))
            rows = result.fetchall()
            
            if rows:
                # Get column names
                columns = list(result.keys())
                print(f"   Columns: {', '.join(columns)}")
                for i, row in enumerate(rows[:3]):  # Show first 3 rows
                    print(f"   Row {i+1}: {dict(zip(columns, row))}")
            else:
                print("   (No data)")
                
            db.close()
        except Exception as e:
            print(f"   Error: {e}")

def main():
    """Main verification process"""
    try:
        success = verify_memory_schema()
        
        if success:
            show_sample_data()
            print("\n🎉 Schema verification completed successfully!")
        else:
            print("\n⚠️ Schema verification found issues")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()