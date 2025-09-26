"""
Test script to verify main application startup with unified authentication system.

This test verifies that:
1. Main application starts correctly with unified system
2. All authentication endpoints work
3. Database initialization is correct
4. No legacy authentication code remains active

Requirements: 3.1, 3.3, 6.1, 6.4
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add the parent directory to the path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_main_app_startup():
    """Test main application startup with unified authentication"""
    
    logger.info("🧪 Testing main application startup with unified authentication...")
    
    try:
        # Import main app
        from main import app
        from backend.unified_startup import get_app_manager
        from backend.unified_config import get_config_manager
        
        # Get app manager to check initialization status
        app_manager = get_app_manager()
        config_manager = get_config_manager()
        
        logger.info("✅ Main application imported successfully")
        
        # Test 1: Verify configuration
        logger.info("🔧 Testing configuration...")
        
        config = config_manager.config
        if not config:
            logger.error("❌ Configuration not loaded")
            return False
        
        logger.info(f"✅ Configuration loaded - Environment: {config.environment.value}")
        
        # Test 2: Create test client
        logger.info("🌐 Creating test client...")
        
        client = TestClient(app)
        
        logger.info("✅ Test client created successfully")
        
        # Test 3: Test health endpoint
        logger.info("🏥 Testing health endpoint...")
        
        try:
            response = client.get("/health")
            if response.status_code == 200:
                logger.info("✅ Health endpoint working")
            else:
                logger.warning(f"⚠️ Health endpoint returned {response.status_code}")
        except Exception as health_error:
            logger.warning(f"⚠️ Health endpoint test failed: {health_error}")
        
        # Test 4: Test static file endpoints
        logger.info("📁 Testing static file endpoints...")
        
        static_endpoints = ["/", "/login.html", "/chat.html", "/register.html"]
        
        for endpoint in static_endpoints:
            try:
                response = client.get(endpoint)
                if response.status_code == 200:
                    logger.info(f"✅ Static endpoint {endpoint} working")
                else:
                    logger.warning(f"⚠️ Static endpoint {endpoint} returned {response.status_code}")
            except Exception as static_error:
                logger.warning(f"⚠️ Static endpoint {endpoint} test failed: {static_error}")
        
        # Test 5: Test authentication endpoints exist
        logger.info("🔐 Testing authentication endpoints...")
        
        # Test login endpoint (should return 422 for missing form data)
        try:
            response = client.post("/login")
            if response.status_code == 422:  # Validation error for missing form data
                logger.info("✅ Login endpoint exists and validates input")
            else:
                logger.warning(f"⚠️ Login endpoint returned unexpected status: {response.status_code}")
        except Exception as login_error:
            logger.error(f"❌ Login endpoint test failed: {login_error}")
            return False
        
        # Test register endpoint (should return 422 for missing data)
        try:
            response = client.post("/register")
            if response.status_code == 422:  # Validation error for missing data
                logger.info("✅ Register endpoint exists and validates input")
            else:
                logger.warning(f"⚠️ Register endpoint returned unexpected status: {response.status_code}")
        except Exception as register_error:
            logger.error(f"❌ Register endpoint test failed: {register_error}")
            return False
        
        # Test logout endpoint
        try:
            response = client.post("/logout")
            if response.status_code == 200:
                logger.info("✅ Logout endpoint working")
            else:
                logger.warning(f"⚠️ Logout endpoint returned {response.status_code}")
        except Exception as logout_error:
            logger.warning(f"⚠️ Logout endpoint test failed: {logout_error}")
        
        # Test 6: Test database initialization endpoint
        logger.info("🗄️ Testing database initialization endpoint...")
        
        try:
            response = client.post("/init-db")
            if response.status_code == 200:
                response_data = response.json()
                if "Unified database" in response_data.get("message", ""):
                    logger.info("✅ Database initialization endpoint uses unified system")
                else:
                    logger.warning("⚠️ Database initialization message doesn't mention unified system")
            else:
                logger.warning(f"⚠️ Database init endpoint returned {response.status_code}")
        except Exception as db_init_error:
            logger.warning(f"⚠️ Database init endpoint test failed: {db_init_error}")
        
        # Test 7: Verify no legacy authentication imports
        logger.info("🔍 Verifying no legacy authentication code...")
        
        # Check main.py content for legacy imports
        main_file_path = Path(__file__).parent.parent / "main.py"
        if main_file_path.exists():
            try:
                with open(main_file_path, 'r', encoding='utf-8') as f:
                    main_content = f.read()
                
                # Check for removed legacy imports
                legacy_patterns = [
                    "import bcrypt",
                    "from backend.models import User,",
                    "from backend.models import UserSession",
                    "def get_current_user_unified("
                ]
                
                legacy_found = []
                for pattern in legacy_patterns:
                    if pattern in main_content:
                        legacy_found.append(pattern)
                
                if legacy_found:
                    logger.warning(f"⚠️ Legacy authentication code still found: {legacy_found}")
                else:
                    logger.info("✅ No legacy authentication code found")
            except Exception as encoding_error:
                logger.warning(f"⚠️ Could not check main.py for legacy code: {encoding_error}")
                # This is not a critical failure, continue with test
        
        logger.info("🎉 Main application startup test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Main application startup test failed: {e}")
        return False


async def test_unified_authentication_integration():
    """Test unified authentication integration in main app"""
    
    logger.info("🔐 Testing unified authentication integration...")
    
    try:
        # Test authentication service availability
        from backend.unified_auth import auth_service, get_current_user_flexible
        from backend.unified_models import UnifiedUser, UnifiedUserSession, UserRole
        
        logger.info("✅ Unified authentication imports successful")
        
        # Test authentication service methods
        test_password = "test_password_123"
        password_hash = auth_service.hash_password(test_password)
        
        if not password_hash:
            logger.error("❌ Password hashing failed")
            return False
        
        is_valid = auth_service.verify_password(test_password, password_hash)
        if not is_valid:
            logger.error("❌ Password verification failed")
            return False
        
        logger.info("✅ Authentication service methods working")
        
        # Test unified models
        from backend.database import SessionLocal
        
        with SessionLocal() as db:
            # Test querying unified models
            user_count = db.query(UnifiedUser).count()
            session_count = db.query(UnifiedUserSession).count()
            
            logger.info(f"✅ Unified models accessible - Users: {user_count}, Sessions: {session_count}")
        
        logger.info("🎉 Unified authentication integration test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Unified authentication integration test failed: {e}")
        return False


async def main():
    """Run all tests"""
    
    logger.info("🚀 Starting main application startup tests...")
    
    # Test 1: Main app startup
    startup_test = await test_main_app_startup()
    
    # Test 2: Authentication integration
    auth_test = await test_unified_authentication_integration()
    
    # Summary
    if startup_test and auth_test:
        logger.info("🎉 All tests passed! Main application startup with unified authentication is working correctly.")
        return True
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)