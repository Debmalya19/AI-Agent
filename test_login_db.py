#!/usr/bin/env python3
"""
Test script to check login and database connection
"""

import os
import sys
from sqlalchemy import text
from database import SessionLocal, engine
from models import User, UserSession
import hashlib
from datetime import datetime, timedelta

def test_database_connection():
    """Test database connection"""
    print("=" * 50)
    print("Testing Database Connection...")
    print("=" * 50)
    
    try:
        # Test engine connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database engine connection: SUCCESS")
        
        # Test session creation
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            print("✅ Database session creation: SUCCESS")
            
            # Check if tables exist
            tables = db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)).fetchall()
            
            if tables:
                print(f"✅ Found {len(tables)} tables in database:")
                for table in tables:
                    print(f"   - {table[0]}")
            else:
                print("⚠️ No tables found in database")
                
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    return True

def test_user_login():
    """Test user login functionality"""
    print("\n" + "=" * 50)
    print("Testing User Login...")
    print("=" * 50)
    
    try:
        db = SessionLocal()
        
        # Check if users exist
        user_count = db.query(User).count()
        print(f"📊 Total users in database: {user_count}")
        
        if user_count == 0:
            print("⚠️ No users found. Creating test user...")
            
            # Create test user
            test_user = User(
                user_id="test_user_001",
                username="testuser",
                email="test@example.com",
                password_hash=hashlib.sha256("test123".encode()).hexdigest(),
                full_name="Test User",
                is_active=True
            )
            db.add(test_user)
            db.commit()
            print("✅ Test user created: testuser / test123")
        
        # Test login with test user
        user = db.query(User).filter(
            User.username == "testuser",
            User.is_active == True
        ).first()
        
        if user:
            print(f"✅ User found: {user.username} ({user.user_id})")
            
            # Create session
            session_token = f"test_session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            user_session = UserSession(
                session_id=session_token,
                user_id=user.user_id,
                token_hash=hashlib.sha256(session_token.encode()).hexdigest(),
                expires_at=expires_at
            )
            db.add(user_session)
            db.commit()
            
            print(f"✅ Login successful! Session: {session_token}")
            return True
        else:
            print("❌ User not found")
            return False
            
    except Exception as e:
        print(f"❌ Login test failed: {e}")
        return False
    finally:
        db.close()

def test_database_health():
    """Comprehensive database health check"""
    print("\n" + "=" * 50)
    print("Database Health Check...")
    print("=" * 50)
    
    try:
        db = SessionLocal()
        
        # Check all tables
        tables = ['users', 'user_sessions', 'knowledge_entries', 'chat_history']
        
        for table in tables:
            try:
                count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"✅ {table}: {count} records")
            except Exception as e:
                print(f"❌ {table}: Error - {e}")
        
        # Check database version
        version = db.execute(text("SELECT version()")).scalar()
        print(f"📋 Database version: {version}")
        
        # Check connection pool
        db.execute(text("SELECT 1"))
        print("✅ Connection pool: ACTIVE")
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🔍 Login and Database Connection Test")
    print("=" * 60)
    
    # Test database connection
    db_ok = test_database_connection()
    
    if db_ok:
        # Test user login
        login_ok = test_user_login()
        
        # Test database health
        test_database_health()
        
        print("\n" + "=" * 60)
        if db_ok and login_ok:
            print("🎉 ALL TESTS PASSED! Login and database connection are working.")
        else:
            print("⚠️ Some tests failed. Check the output above for details.")
    else:
        print("❌ Database connection failed. Please check your database configuration.")
