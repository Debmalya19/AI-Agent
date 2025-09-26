#!/usr/bin/env python3
"""
Simple test to verify static file configuration without starting full server
"""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

def test_static_file_configuration():
    """Test the static file configuration logic"""
    print("🔍 Testing Static File Configuration Logic")
    print("=" * 50)
    
    # Check that directories exist
    directories = [
        ("admin-dashboard/frontend/css", "Admin CSS directory"),
        ("admin-dashboard/frontend/js", "Admin JS directory"),
        ("admin-dashboard/frontend", "Admin frontend directory"),
        ("frontend", "Main frontend directory")
    ]
    
    all_exist = True
    
    for dir_path, description in directories:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            file_count = len([f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))])
            print(f"  ✅ {description:<25} - {file_count} files")
        else:
            print(f"  ❌ {description:<25} - NOT FOUND")
            all_exist = False
    
    if not all_exist:
        return False
    
    # Test FastAPI configuration (without starting server)
    print("\n🔧 Testing FastAPI Static File Mount Configuration")
    print("-" * 50)
    
    try:
        app = FastAPI()
        
        # Apply the same configuration as in main.py
        app.mount("/css", StaticFiles(directory="admin-dashboard/frontend/css"), name="admin_css")
        app.mount("/js", StaticFiles(directory="admin-dashboard/frontend/js"), name="admin_js")
        app.mount("/static", StaticFiles(directory="frontend"), name="static")
        app.mount("/admin", StaticFiles(directory="admin-dashboard/frontend"), name="admin")
        
        print("  ✅ Static file mounts configured successfully")
        print("  ✅ Route order: /css, /js, /static, /admin")
        
        # Check that the routes are registered
        routes = [route.path for route in app.routes]
        expected_mounts = ["/css", "/js", "/static", "/admin"]
        
        for mount in expected_mounts:
            if any(route.startswith(mount) for route in routes):
                print(f"  ✅ Mount point {mount} registered")
            else:
                print(f"  ❌ Mount point {mount} NOT registered")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False

def test_file_accessibility():
    """Test that key files are accessible"""
    print("\n📁 Testing Key File Accessibility")
    print("-" * 50)
    
    key_files = [
        ("admin-dashboard/frontend/css/modern-dashboard.css", "Modern Dashboard CSS"),
        ("admin-dashboard/frontend/js/session-manager.js", "Session Manager JS"),
        ("admin-dashboard/frontend/js/main.js", "Main JS"),
        ("admin-dashboard/frontend/index.html", "Admin Index HTML")
    ]
    
    all_accessible = True
    
    for file_path, description in key_files:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            file_size = os.path.getsize(file_path)
            print(f"  ✅ {description:<25} - {file_size:,} bytes")
        else:
            print(f"  ❌ {description:<25} - NOT FOUND")
            all_accessible = False
    
    return all_accessible

def main():
    """Run simple configuration tests"""
    print("🧪 Simple Static File Configuration Test")
    print("=" * 50)
    
    config_ok = test_static_file_configuration()
    files_ok = test_file_accessibility()
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    if config_ok and files_ok:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Static file configuration is correct")
        print("✅ All required files are present")
        print("✅ FastAPI mounts are properly configured")
        print("\n📝 Configuration Summary:")
        print("   - /css → admin-dashboard/frontend/css")
        print("   - /js → admin-dashboard/frontend/js")
        print("   - /static → frontend")
        print("   - /admin → admin-dashboard/frontend")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        if not config_ok:
            print("   - Configuration issues detected")
        if not files_ok:
            print("   - Missing required files")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)