#!/usr/bin/env python3
"""
Test script to manually trigger admin dashboard startup and check routes
"""

import sys
import os
import asyncio
sys.path.append('.')

from backend.unified_startup import create_unified_app, get_app_manager
from backend.unified_config import get_config_manager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_admin_startup():
    """Test admin dashboard startup sequence"""
    print("=" * 60)
    print("Admin Dashboard Startup Test")
    print("=" * 60)
    
    try:
        # Create the app
        app = create_unified_app()
        app_manager = get_app_manager()
        
        print("App created, running startup sequence...")
        
        # Manually run the startup sequence
        await app_manager.startup_sequence(app)
        
        print(f"Initialized Services: {app_manager.initialized_services}")
        print(f"Startup Errors: {app_manager.startup_errors}")
        
        # Check registered routes after startup
        print("\nRegistered Routes After Startup:")
        admin_routes = []
        all_routes = []
        
        for route in app.routes:
            route_info = {
                'path': getattr(route, 'path', 'N/A'),
                'methods': getattr(route, 'methods', 'N/A'),
                'name': getattr(route, 'name', 'N/A')
            }
            all_routes.append(route_info)
            
            if hasattr(route, 'path') and '/admin' in route.path:
                admin_routes.append(route_info)
        
        print(f"Total Routes: {len(all_routes)}")
        print(f"Admin Routes: {len(admin_routes)}")
        
        if admin_routes:
            print("\nAdmin Routes Found:")
            for route in admin_routes:
                print(f"  - {route['methods']} {route['path']} ({route['name']})")
        else:
            print("\n❌ No admin routes found after startup!")
            
        # Test route access
        print("\nTesting Route Access:")
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        response = client.get("/admin")
        print(f"GET /admin: {response.status_code}")
        
        response = client.get("/api/admin/dashboard")
        print(f"GET /api/admin/dashboard: {response.status_code}")
        
        return len(admin_routes) > 0
        
    except Exception as e:
        print(f"❌ Error during startup test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_manual_admin_integration():
    """Test manual admin integration setup"""
    print("\n" + "=" * 60)
    print("Manual Admin Integration Test")
    print("=" * 60)
    
    try:
        from fastapi import FastAPI
        from backend.admin_integration_manager import AdminIntegrationManager
        
        # Create a fresh app
        app = FastAPI()
        
        # Manually set up admin integration
        admin_manager = AdminIntegrationManager(app)
        success = admin_manager.initialize()
        
        print(f"Manual admin integration success: {success}")
        
        # Check routes
        admin_routes = []
        for route in app.routes:
            if hasattr(route, 'path') and '/admin' in route.path:
                admin_routes.append({
                    'path': route.path,
                    'methods': getattr(route, 'methods', 'N/A'),
                    'name': getattr(route, 'name', 'N/A')
                })
        
        print(f"Admin routes after manual setup: {len(admin_routes)}")
        for route in admin_routes:
            print(f"  - {route['methods']} {route['path']} ({route['name']})")
            
        return len(admin_routes) > 0
        
    except Exception as e:
        print(f"❌ Error during manual integration test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    async def main():
        startup_success = await test_admin_startup()
        manual_success = await test_manual_admin_integration()
        
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        
        if startup_success:
            print("✅ Admin dashboard startup sequence works")
        else:
            print("❌ Admin dashboard startup sequence failed")
            
        if manual_success:
            print("✅ Manual admin integration works")
        else:
            print("❌ Manual admin integration failed")
            
        if startup_success or manual_success:
            print("\n🔧 Solution: The admin dashboard needs the startup sequence to run")
            print("   This happens automatically when you start the server with uvicorn")
        else:
            print("\n❌ Admin dashboard integration has deeper issues")
    
    asyncio.run(main())