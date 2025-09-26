#!/usr/bin/env python3
"""
Fix PostgreSQL enum values to match SQLite data
"""

import psycopg2
import sqlite3
from dotenv import load_dotenv
import os

load_dotenv()

def fix_enum_values():
    try:
        # Connect to both databases
        pg_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        pg_cur = pg_conn.cursor()
        
        sqlite_conn = sqlite3.connect('ai_agent.db')
        sqlite_cur = sqlite_conn.cursor()
        
        # Check ticket priority enum
        pg_cur.execute("""
            SELECT enumlabel 
            FROM pg_enum 
            WHERE enumtypid = (
                SELECT oid 
                FROM pg_type 
                WHERE typname = 'ticketpriority'
            )
            ORDER BY enumsortorder
        """)
        
        pg_priority_values = [row[0] for row in pg_cur.fetchall()]
        print("Current ticketpriority enum values:", pg_priority_values)
        
        sqlite_cur.execute("SELECT DISTINCT priority FROM unified_tickets WHERE priority IS NOT NULL")
        sqlite_priority_values = [row[0] for row in sqlite_cur.fetchall()]
        print("SQLite ticket priority values:", sqlite_priority_values)
        
        # Add missing priority values
        missing_priority = set(sqlite_priority_values) - set(pg_priority_values)
        if missing_priority:
            print("Missing priority enum values:", missing_priority)
            for value in missing_priority:
                try:
                    pg_cur.execute(f"ALTER TYPE ticketpriority ADD VALUE '{value}'")
                    print(f"Added priority enum value: {value}")
                except Exception as e:
                    print(f"Failed to add priority {value}: {e}")
        
        # Check ticket category enum if it exists
        try:
            pg_cur.execute("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid 
                    FROM pg_type 
                    WHERE typname = 'ticketcategory'
                )
                ORDER BY enumsortorder
            """)
            
            pg_category_values = [row[0] for row in pg_cur.fetchall()]
            print("Current ticketcategory enum values:", pg_category_values)
            
            sqlite_cur.execute("SELECT DISTINCT category FROM unified_tickets WHERE category IS NOT NULL")
            sqlite_category_values = [row[0] for row in sqlite_cur.fetchall()]
            print("SQLite ticket category values:", sqlite_category_values)
            
            # Add missing category values
            missing_category = set(sqlite_category_values) - set(pg_category_values)
            if missing_category:
                print("Missing category enum values:", missing_category)
                for value in missing_category:
                    try:
                        pg_cur.execute(f"ALTER TYPE ticketcategory ADD VALUE '{value}'")
                        print(f"Added category enum value: {value}")
                    except Exception as e:
                        print(f"Failed to add category {value}: {e}")
        except:
            print("No ticketcategory enum found")
        
        pg_conn.commit()
        pg_cur.close()
        pg_conn.close()
        sqlite_cur.close()
        sqlite_conn.close()
        
        print("Enum values fixed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_enum_values()