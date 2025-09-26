#!/usr/bin/env python3
"""
Check PostgreSQL enum values
"""

import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    # Check if ticketstatus enum exists and get its values
    cur.execute("""
        SELECT enumlabel 
        FROM pg_enum 
        WHERE enumtypid = (
            SELECT oid 
            FROM pg_type 
            WHERE typname = 'ticketstatus'
        )
        ORDER BY enumsortorder
    """)
    
    enum_values = [row[0] for row in cur.fetchall()]
    print("Current ticketstatus enum values:", enum_values)
    
    # Also check what values are in the SQLite data
    import sqlite3
    sqlite_conn = sqlite3.connect('ai_agent.db')
    sqlite_cur = sqlite_conn.cursor()
    
    sqlite_cur.execute("SELECT DISTINCT status FROM unified_tickets")
    sqlite_values = [row[0] for row in sqlite_cur.fetchall()]
    print("SQLite ticket status values:", sqlite_values)
    
    # Find missing values
    missing = set(sqlite_values) - set(enum_values)
    if missing:
        print("Missing enum values:", missing)
        
        # Add missing enum values
        for value in missing:
            try:
                cur.execute(f"ALTER TYPE ticketstatus ADD VALUE '{value}'")
                print(f"Added enum value: {value}")
            except Exception as e:
                print(f"Failed to add {value}: {e}")
        
        conn.commit()
    
    cur.close()
    conn.close()
    sqlite_cur.close()
    sqlite_conn.close()
    
except Exception as e:
    print(f"Error: {e}")