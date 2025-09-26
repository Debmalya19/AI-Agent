#!/usr/bin/env python3
"""
PostgreSQL Setup Test Script

This script tests the PostgreSQL database setup and connection configuration.
"""

import sys
import os
import logging
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_configuration():
    """Test database configuration and connection"""
    try:
        from backend.database import engine, health_check_database, get_database_info, init_db
        from backend.database_health import get_health_status, get_detailed_health_status
        
        logger.info("Testing PostgreSQL database configuration...")
        
        # Test 1: Engine creation
        if engine is None:
            logger.error("❌ Database engine creation failed")
            return False
        else:
            logger.info("✅ Database engine created successfully")
        
        # Test 2: Basic health check
        if health_check_database(engine):
            logger.info("✅ Database health check passed")
        else:
            logger.error("❌ Database health check failed")
            return False
        
        # Test 3: Database info
        db_info = get_database_info()
        logger.info(f"✅ Database info: {db_info}")
        
        # Test 4: Health status endpoints
        health_status = get_health_status()
        logger.info(f"✅ Quick health check: {health_status['status']} ({health_status['response_time']}ms)")
        
        # Test 5: Detailed health check
        detailed_health = get_detailed_health_status()
        logger.info(f"✅ Detailed health check: {detailed_health['status']}")
        
        for check_name, check_result in detailed_health.get('checks', {}).items():
            status_icon = "✅" if check_result['status'] == 'pass' else "❌"
            logger.info(f"  {status_icon} {check_name}: {check_result['message']}")
        
        # Test 6: Database initialization
        try:
            init_db()
            logger.info("✅ Database initialization completed")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
        
        logger.info("🎉 All PostgreSQL setup tests passed!")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def test_connection_pooling():
    """Test connection pooling functionality"""
    try:
        from backend.database import engine, SessionLocal
        
        logger.info("Testing connection pooling...")
        
        # Test multiple concurrent connections
        sessions = []
        for i in range(5):
            try:
                session = SessionLocal()
                sessions.append(session)
                logger.info(f"✅ Created session {i+1}")
            except Exception as e:
                logger.error(f"❌ Failed to create session {i+1}: {e}")
                return False
        
        # Close all sessions
        for i, session in enumerate(sessions):
            try:
                session.close()
                logger.info(f"✅ Closed session {i+1}")
            except Exception as e:
                logger.error(f"❌ Failed to close session {i+1}: {e}")
        
        logger.info("✅ Connection pooling test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection pooling test failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("Starting PostgreSQL setup tests...")
    
    # Test database configuration
    if not test_database_configuration():
        logger.error("Database configuration tests failed")
        return False
    
    # Test connection pooling
    if not test_connection_pooling():
        logger.error("Connection pooling tests failed")
        return False
    
    logger.info("🎉 All tests passed! PostgreSQL setup is working correctly.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)