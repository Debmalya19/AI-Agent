#!/usr/bin/env python3
"""
Test Admin Routes Registration

Simple test to check if admin routes are being registered correctly.
"""

import sys
import os
import logging

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_admin_routes_registration():
    """Test if admin routes are registered in the FastAPI app"""
    logger.info("🔍 Testing admin routes registration...")
    
    # Get all routes from the FastAPI app
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                'path': route.path,
                'methods': list(route.methods) if route.methods else [],
                'name': getattr(route, 'name', 'unnamed')
            })
    
    # Filter admin routes
    admin_routes = [route for route in routes if '/admin' in route['path']]
    
    logger.info(f"Total routes found: {len(routes)}")
    logger.info(f"Admin routes found: {len(admin_routes)}")
    
    if admin_routes:
        logger.info("✅ Admin routes are registered:")
        for route in admin_routes:
            logger.info(f"  {route['methods']} {route['path']} ({route['name']})")
    else:
        logger.error("❌ No admin routes found!")
        logger.info("All routes:")
        for route in routes[:20]:  # Show first 20 routes
            logger.info(f"  {route['methods']} {route['path']} ({route['name']})")
        if len(routes) > 20:
            logger.info(f"  ... and {len(routes) - 20} more routes")
    
    return len(admin_routes) > 0

def test_admin_integration_status():
    """Test admin integration status"""
    logger.info("🔧 Testing admin integration status...")
    
    try:
        from backend.unified_startup import get_app_manager
        app_manager = get_app_manager()
        
        if 'admin_dashboard' in app_manager.initialized_services:
            logger.info("✅ Admin dashboard service is initialized")
        else:
            logger.error("❌ Admin dashboard service is not initialized")
            logger.info(f"Initialized services: {app_manager.initialized_services}")
        
        if app_manager.startup_errors:
            logger.warning("⚠️ Startup errors found:")
            for error in app_manager.startup_errors:
                logger.warning(f"  - {error}")
        
        return 'admin_dashboard' in app_manager.initialized_services
        
    except Exception as e:
        logger.error(f"❌ Error checking admin integration status: {e}")
        return False

def main():
    """Main function"""
    logger.info("🚀 Testing Admin Routes Registration...")
    
    routes_registered = test_admin_routes_registration()
    integration_initialized = test_admin_integration_status()
    
    logger.info("\n" + "="*60)
    logger.info("ADMIN ROUTES REGISTRATION TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Routes Registered: {'✅ YES' if routes_registered else '❌ NO'}")
    logger.info(f"Integration Initialized: {'✅ YES' if integration_initialized else '❌ NO'}")
    
    if routes_registered and integration_initialized:
        logger.info("🎉 Admin dashboard integration is working correctly!")
        return 0
    else:
        logger.error("❌ Admin dashboard integration has issues!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)