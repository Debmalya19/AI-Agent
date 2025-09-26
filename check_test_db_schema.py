#!/usr/bin/env python3
"""
Check the current schema of the test database
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

def check_database_schema():
    """Check what tables and columns exist in the test database"""
    load_dotenv()
    
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'password',
        'database': 'test_ai_agent'
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        print("Tables in test database:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check unified_tickets table specifically
        if any('unified_tickets' in str(table) for table in tables):
            print("\nColumns in unified_tickets table:")
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'unified_tickets'
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_database_schema()