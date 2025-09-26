#!/usr/bin/env python3
"""
Check existing users in the database
"""

import sqlite3
import os

def check_users():
    """Check users in the database"""
    db_path = "ai_agent.db"
    
    if not os.path.exists(db_path):
        print("Database file not found!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check unified_users table
        cursor.execute("SELECT id, user_id, username, email, is_admin, created_at FROM unified_users ORDER BY id DESC")
        users = cursor.fetchall()
        
        print("Users in unified_users table:")
        print("ID | User ID | Username | Email | Is Admin | Created At")
        print("-" * 80)
        
        for user in users:
            print(f"{user[0]} | {user[1]} | {user[2]} | {user[3]} | {user[4]} | {user[5]}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_users()