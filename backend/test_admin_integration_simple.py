"""
Simple test to verify admin dashboard integration works
"""

from fastapi import FastAPI
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.admin_integration import setup_admin_dashboard_integration, get_admin_route_list

def test_basic_integration():
    """Test basic integration functionality"""
    print("🚀 Testing Admin Dashboard Integration...")
    
    # Create a test FastAPI app
    app = FastAPI(title="Test App")
    
    # Setup admin dashboard integration
    try:
        admin_integration = setup_admin_dashboard_integration(app, enable_compatibility=True)
        
        if admin_integration.is_initialized:
            print("✅ Admin dashboard integration successful!")
            
            # Get router info
            router_info = admin_integration.get_router_info()
            print(f"📋 Registered {len(router_info)} router groups:")
            
            for router in router_info:
                print(f"  - {router['prefix']} ({router['routes_count']} routes)")
            
            # Get all routes
            all_routes = get_admin_route_list()
            print(f"🔗 Total admin routes available: {len(all_routes)}")
            
            # Show some example routes
            print("\n📝 Example routes:")
            for route in all_routes[:5]:  # Show first 5 routes
                print(f"  {route['method']} {route['path']} - {route['description']}")
            
            return True
        else:
            print("❌ Admin dashboard integration failed")
            return False
            
    except Exception as e:
        print(f"❌ Integration error: {e}")
        return False

if __name__ == "__main__":
    success = test_basic_integration()
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n💥 Tests failed!")