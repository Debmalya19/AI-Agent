#!/usr/bin/env python3
"""
Migration script to fix the user_sessions table schema
Adds missing columns: token_hash, expires_at, is_active
"""

import sqlite3
import os
from datetime import datetime, timedelta

def migrate_user_sessions():
    """Add missing columns to user_sessions table"""
    db_path = "knowledge_base.db"
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found!")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current table structure
        cursor.execute("PRAGMA table_info(user_sessions)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Current columns: {columns}")
        
        # Add missing columns
        if 'token_hash' not in columns:
            cursor.execute("ALTER TABLE user_sessions ADD COLUMN token_hash TEXT")
            print("Added token_hash column")
        
        if 'expires_at' not in columns:
            cursor.execute("ALTER TABLE user_sessions ADD COLUMN expires_at TIMESTAMP")
            print("Added expires_at column")
            
        if 'is_active' not in columns:
            cursor.execute("ALTER TABLE user_sessions ADD COLUMN is_active BOOLEAN DEFAULT 1")
            print("Added is_active column")
        
        # Update existing records with default values
        cursor.execute("""
            UPDATE user_sessions 
            SET token_hash = 'default_hash', 
                expires_at = ?, 
                is_active = 1 
            WHERE token_hash IS NULL OR expires_at IS NULL
        """, (datetime.utcnow() + timedelta(days=1),))
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(user_sessions)")
        updated_columns = [col[1] for col in cursor.fetchall()]
        print(f"Updated columns: {updated_columns}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_user_sessions()
