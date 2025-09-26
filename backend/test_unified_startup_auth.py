"""
Test script to verify unified startup system with authentication integration.

This test verifies that:
1. Unified configuration loads correctly
2. Database initialization creates unified tables
3. Authentication system initializes properly
4. All components work together

Requirements: 3.1, 3.3, 6.1, 6.4
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.unified_startup import UnifiedApplicationManager
from backend.unified_config import get_config_manager
from backend.database import engine, SessionLocal
from backend.unified_models import UnifiedUser, UnifiedUserSession
from backend.unified_auth import auth_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_unified_startup_authentication():
    """Test the unified startup system with authentication"""
    
    logger.info("🧪 Starting unified startup authentication test...")
    
    try:
        # Test 1: Configuration initialization
        logger.info("📋 Testing configuration initialization...")
        app_manager = UnifiedApplicationManager()
        
        config_success = await app_manager.initialize_configuration()
        if not config_success:
            logger.error("❌ Configuration initialization failed")
            return False
        
        logger.info("✅ Configuration initialization successful")
        
        # Test 2: Database initialization
        logger.info("🗄️ Testing database initialization...")
        
        db_success = await app_manager.initialize_database()
        if not db_success:
            logger.error("❌ Database initialization failed")
            return False
        
        logger.info("✅ Database initialization successful")
        
        # Test 3: Authentication system initialization
        logger.info("🔐 Testing authentication system initialization...")
        
        auth_success = await app_manager.initialize_authentication()
        if not auth_success:
            logger.error("❌ Authentication initialization failed")
            return False
        
        logger.info("✅ Authentication system initialization successful")
        
        # Test 4: Verify unified tables exist
        logger.info("🔍 Verifying unified database tables...")
        
        try:
            with SessionLocal() as db:
                # Check if unified tables exist by querying them
                user_count = db.query(UnifiedUser).count()
                session_count = db.query(UnifiedUserSession).count()
                
                logger.info(f"✅ Unified tables verified - Users: {user_count}, Sessions: {session_count}")
                
        except Exception as table_error:
            logger.error(f"❌ Unified table verification failed: {table_error}")
            return False
        
        # Test 5: Test authentication service functionality
        logger.info("🔑 Testing authentication service functionality...")
        
        try:
            # Test password hashing
            test_password = "test_password_123"
            password_hash = auth_service.hash_password(test_password)
            
            if not password_hash or len(password_hash) < 10:
                logger.error("❌ Password hashing failed")
                return False
            
            # Test password verification
            is_valid = auth_service.verify_password(test_password, password_hash)
            if not is_valid:
                logger.error("❌ Password verification failed")
                return False
            
            logger.info("✅ Authentication service functionality verified")
            
        except Exception as auth_test_error:
            logger.error(f"❌ Authentication service test failed: {auth_test_error}")
            return False
        
        # Test 6: Check startup errors
        if app_manager.startup_errors:
            logger.warning(f"⚠️ Startup completed with {len(app_manager.startup_errors)} warnings:")
            for error in app_manager.startup_errors:
                logger.warning(f"  - {error}")
        
        # Test 7: Verify initialized services
        expected_services = ["database", "authentication"]
        for service in expected_services:
            if service not in app_manager.initialized_services:
                logger.error(f"❌ Expected service '{service}' not initialized")
                return False
        
        logger.info(f"✅ All expected services initialized: {app_manager.initialized_services}")
        
        logger.info("🎉 Unified startup authentication test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Unified startup authentication test failed: {e}")
        return False


async def test_configuration_validation():
    """Test configuration validation"""
    
    logger.info("🔧 Testing configuration validation...")
    
    try:
        config_manager = get_config_manager()
        
        # Test configuration validation
        is_valid = config_manager.validate_config()
        validation_errors = config_manager.get_validation_errors()
        
        if validation_errors:
            logger.warning(f"⚠️ Configuration validation found {len(validation_errors)} issues:")
            for error in validation_errors:
                logger.warning(f"  - {error}")
        
        # In development, warnings are acceptable
        if config_manager.config.is_development():
            logger.info("✅ Configuration validation completed (development mode)")
            return True
        elif is_valid:
            logger.info("✅ Configuration validation passed")
            return True
        else:
            logger.error("❌ Configuration validation failed in production mode")
            return False
            
    except Exception as e:
        logger.error(f"❌ Configuration validation test failed: {e}")
        return False


async def main():
    """Run all tests"""
    
    logger.info("🚀 Starting unified startup authentication tests...")
    
    # Test 1: Configuration validation
    config_test = await test_configuration_validation()
    
    # Test 2: Unified startup with authentication
    startup_test = await test_unified_startup_authentication()
    
    # Summary
    if config_test and startup_test:
        logger.info("🎉 All tests passed! Unified startup system with authentication is working correctly.")
        return True
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)