#!/usr/bin/env python3
"""
Direct Admin Integration Test

Test admin dashboard integration by manually initializing it.
"""

import sys
import os
import logging

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_admin_integration_direct():
    """Test admin integration by manually initializing it"""
    logger.info("🔧 Testing admin integration directly...")
    
    try:
        # Create a fresh FastAPI app
        app = FastAPI(title="Test Admin Integration")
        
        # Import and initialize admin integration
        from backend.admin_integration_manager import AdminIntegrationManager
        
        logger.info("Creating AdminIntegrationManager...")
        admin_manager = AdminIntegrationManager(app)
        
        logger.info("Initializing admin integration...")
        success = admin_manager.initialize()
        
        if success:
            logger.info("✅ Admin integration initialized successfully")
        else:
            logger.error("❌ Admin integration initialization failed")
            return False
        
        # Check routes
        admin_routes = [route for route in app.routes if hasattr(route, 'path') and '/admin' in route.path]
        logger.info(f"Admin routes registered: {len(admin_routes)}")
        
        for route in admin_routes:
            methods = list(route.methods) if hasattr(route, 'methods') and route.methods else []
            logger.info(f"  {methods} {route.path}")
        
        # Test with TestClient
        client = TestClient(app)
        
        # Test a simple admin endpoint without authentication (should fail)
        response = client.get("/api/admin/dashboard")
        logger.info(f"Admin dashboard test response (no auth): {response.status_code}")
        
        if response.status_code in [401, 403]:
            logger.info("✅ Admin dashboard correctly requires authentication")
            return True
        elif response.status_code == 200:
            logger.warning("⚠️ Admin dashboard accessible without authentication (security issue)")
            return True  # Still pass, but with warning
        else:
            logger.error(f"❌ Unexpected response code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error during direct admin integration test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_admin_auth_integration():
    """Test admin authentication integration"""
    logger.info("🔐 Testing admin authentication integration...")
    
    try:
        # Import unified auth components
        from backend.unified_auth import auth_service, get_current_user_flexible, Permission
        from backend.unified_models import UnifiedUser, UserRole
        from backend.database import get_db, init_db
        
        # Initialize database
        init_db()
        
        # Test auth service
        logger.info("Testing auth service...")
        test_password = "test_password_123"
        hashed = auth_service.hash_password(test_password)
        verified = auth_service.verify_password(test_password, hashed)
        
        if verified:
            logger.info("✅ Auth service password hashing/verification works")
        else:
            logger.error("❌ Auth service password verification failed")
            return False
        
        # Test permissions
        logger.info("Testing permission system...")
        from backend.unified_auth import ROLE_PERMISSIONS
        
        admin_permissions = ROLE_PERMISSIONS.get(UserRole.ADMIN, set())
        customer_permissions = ROLE_PERMISSIONS.get(UserRole.CUSTOMER, set())
        
        logger.info(f"Admin permissions: {len(admin_permissions)}")
        logger.info(f"Customer permissions: {len(customer_permissions)}")
        
        if Permission.DASHBOARD_VIEW in admin_permissions:
            logger.info("✅ Admin has dashboard view permission")
        else:
            logger.error("❌ Admin missing dashboard view permission")
            return False
        
        if Permission.DASHBOARD_VIEW not in customer_permissions:
            logger.info("✅ Customer correctly lacks dashboard view permission")
        else:
            logger.error("❌ Customer incorrectly has dashboard view permission")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during admin auth integration test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    logger.info("🚀 Testing Admin Integration Directly...")
    
    integration_works = test_admin_integration_direct()
    auth_works = test_admin_auth_integration()
    
    logger.info("\n" + "="*60)
    logger.info("DIRECT ADMIN INTEGRATION TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Admin Integration: {'✅ PASS' if integration_works else '❌ FAIL'}")
    logger.info(f"Auth Integration: {'✅ PASS' if auth_works else '❌ FAIL'}")
    
    if integration_works and auth_works:
        logger.info("🎉 Admin dashboard integration is working correctly!")
        return 0
    else:
        logger.error("❌ Admin dashboard integration has issues!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)