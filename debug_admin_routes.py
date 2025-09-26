#!/usr/bin/env python3
"""
Debug script to check admin dashboard route registration
"""

import sys
import os
sys.path.append('.')

from backend.unified_startup import create_unified_app, get_app_manager
from backend.unified_config import get_config_manager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_admin_routes():
    """Debug admin dashboard route registration"""
    print("=" * 60)
    print("Admin Dashboard Route Debug")
    print("=" * 60)
    
    try:
        # Get configuration
        config_manager = get_config_manager()
        config = config_manager._config
        
        print(f"Admin Dashboard Enabled: {config.admin_dashboard.enabled}")
        print(f"Admin Frontend Path: {config.admin_dashboard.frontend_path}")
        print(f"Admin API Prefix: {config.admin_dashboard.api_prefix}")
        
        # Check if frontend path exists
        from pathlib import Path
        frontend_path = Path(config.admin_dashboard.frontend_path)
        print(f"Frontend Path Exists: {frontend_path.exists()}")
        if frontend_path.exists():
            print(f"Frontend Path Contents: {list(frontend_path.iterdir())}")
        
        # Create the app
        print("\nCreating unified app...")
        app = create_unified_app()
        
        # Get app manager to check initialization
        app_manager = get_app_manager()
        print(f"Initialized Services: {app_manager.initialized_services}")
        print(f"Startup Errors: {app_manager.startup_errors}")
        
        # Check registered routes
        print("\nRegistered Routes:")
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
            print("\n❌ No admin routes found!")
            
        # Check if admin integration is in initialized services
        if 'admin_dashboard' in app_manager.initialized_services:
            print("✅ Admin dashboard service initialized")
        else:
            print("❌ Admin dashboard service NOT initialized")
            
        # Try to manually check admin integration
        try:
            from backend.admin_integration_manager import AdminIntegrationManager
            admin_manager = AdminIntegrationManager(app)
            print(f"Admin Integration Manager created: {admin_manager}")
        except Exception as e:
            print(f"❌ Failed to create AdminIntegrationManager: {e}")
            
        return len(admin_routes) > 0
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_admin_route_access():
    """Test admin route access"""
    print("\n" + "=" * 60)
    print("Testing Admin Route Access")
    print("=" * 60)
    
    try:
        from fastapi.testclient import TestClient
        app = create_unified_app()
        client = TestClient(app)
        
        # Test admin route
        response = client.get("/admin")
        print(f"GET /admin: {response.status_code}")
        
        if response.status_code == 404:
            print("❌ Admin route not found (404)")
        elif response.status_code == 200:
            print("✅ Admin route accessible")
        elif response.status_code in [401, 403]:
            print("🔒 Admin route requires authentication")
        else:
            print(f"⚠️ Unexpected status code: {response.status_code}")
            
        # Test API admin route
        response = client.get("/api/admin/dashboard")
        print(f"GET /api/admin/dashboard: {response.status_code}")
        
        return response.status_code != 404
        
    except Exception as e:
        print(f"❌ Error testing admin route access: {e}")
        return False

if __name__ == "__main__":
    routes_found = debug_admin_routes()
    access_works = test_admin_route_access()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    if routes_found and access_works:
        print("✅ Admin dashboard routes are properly configured")
    elif routes_found:
        print("⚠️ Admin routes found but access test failed")
    else:
        print("❌ Admin dashboard routes are NOT properly configured")
        print("\nPossible issues:")
        print("1. Admin dashboard not enabled in configuration")
        print("2. Admin integration failed during startup")
        print("3. Frontend files missing")
        print("4. Route registration failed")