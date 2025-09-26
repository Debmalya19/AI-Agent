"""
Test Main Application Integration

Simple test to verify the updated main application works correctly.
"""

import os
import sys
from pathlib import Path

# Add the ai-agent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_main_app_import():
    """Test that the main app can be imported successfully"""
    try:
        # Set minimal environment for testing
        os.environ["ENVIRONMENT"] = "testing"
        os.environ["DATABASE_URL"] = "sqlite:///test.db"
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-purposes-only"
        
        # Import the main app
        import main
        
        print("✅ Main application imported successfully")
        print(f"✅ App title: {main.app.title}")
        print(f"✅ App version: {main.app.version}")
        
        # Check that the app has the expected attributes
        assert hasattr(main.app, 'title')
        assert hasattr(main.app, 'version')
        assert main.app.title == "AI Agent Customer Support"
        
        print("✅ All basic checks passed")
        return True
        
    except Exception as e:
        print(f"❌ Error importing main app: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up environment variables
        for key in ["ENVIRONMENT", "DATABASE_URL", "JWT_SECRET_KEY"]:
            if key in os.environ:
                del os.environ[key]

def test_health_endpoints():
    """Test that health endpoints are available"""
    try:
        from fastapi.testclient import TestClient
        from backend.health_checks import create_health_check_router
        from fastapi import FastAPI
        
        # Create a simple app with health router
        app = FastAPI()
        health_router = create_health_check_router()
        app.include_router(health_router)
        
        # Test the endpoints
        with TestClient(app) as client:
            # Test basic health check
            response = client.get("/health/")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            
            print("✅ Basic health check endpoint works")
            
            # Test config health check
            response = client.get("/health/config")
            # This might fail due to missing config, but should not crash
            assert response.status_code in [200, 500]
            
            print("✅ Config health check endpoint accessible")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing health endpoints: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing main application integration...")
    
    success = True
    
    print("\n1. Testing main app import...")
    if not test_main_app_import():
        success = False
    
    print("\n2. Testing health endpoints...")
    if not test_health_endpoints():
        success = False
    
    if success:
        print("\n🎉 All integration tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some integration tests failed!")
        sys.exit(1)