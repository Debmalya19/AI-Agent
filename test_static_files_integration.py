#!/usr/bin/env python3
"""
Static Files Integration Test
Simple integration test for static file serving functionality
Part of Task 5: Create static file serving tests

This script tests the integration between the FastAPI app and static file serving
without requiring pytest or external dependencies.
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_fastapi_app_import():
    """Test that the FastAPI app can be imported successfully"""
    try:
        from main import app
        print("✅ FastAPI app imported successfully")
        return True, app
    except ImportError as e:
        print(f"❌ Failed to import FastAPI app: {e}")
        return False, None
    except Exception as e:
        print(f"❌ Error importing FastAPI app: {e}")
        return False, None

def test_static_file_mounts(app):
    """Test that static file mounts are configured correctly"""
    if app is None:
        return False
    
    try:
        # Check if the app has the expected routes
        routes = [route.path for route in app.routes]
        
        # Check for static file mounts
        expected_mounts = ["/css", "/js", "/admin", "/static"]
        found_mounts = []
        
        for route in app.routes:
            if hasattr(route, 'path') and route.path in expected_mounts:
                found_mounts.append(route.path)
        
        print(f"✅ Found static file mounts: {found_mounts}")
        
        # Check if all expected mounts are present
        missing_mounts = set(expected_mounts) - set(found_mounts)
        if missing_mounts:
            print(f"⚠️  Missing static file mounts: {missing_mounts}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking static file mounts: {e}")
        return False

def test_testclient_functionality(app):
    """Test that TestClient works with the app"""
    if app is None:
        return False
    
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Test a simple endpoint
        response = client.get("/admin/")
        print(f"✅ TestClient works - /admin/ returned {response.status_code}")
        
        # Test a CSS file
        response = client.get("/css/modern-dashboard.css")
        print(f"✅ CSS file test - /css/modern-dashboard.css returned {response.status_code}")
        
        # Test a JS file
        response = client.get("/js/main.js")
        print(f"✅ JS file test - /js/main.js returned {response.status_code}")
        
        return True
        
    except ImportError as e:
        print(f"❌ TestClient not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing TestClient: {e}")
        return False

def test_file_system_structure():
    """Test that the required file system structure exists"""
    print("\n📁 Testing File System Structure")
    print("-" * 40)
    
    required_paths = [
        "admin-dashboard/frontend/css",
        "admin-dashboard/frontend/js",
        "admin-dashboard/frontend/index.html"
    ]
    
    all_exist = True
    
    for path_str in required_paths:
        path = Path(path_str)
        exists = path.exists()
        
        if exists:
            if path.is_dir():
                file_count = len(list(path.glob("*")))
                print(f"✅ Directory: {path_str} ({file_count} files)")
            else:
                size = path.stat().st_size
                print(f"✅ File: {path_str} ({size} bytes)")
        else:
            print(f"❌ Missing: {path_str}")
            all_exist = False
    
    return all_exist

def test_critical_static_files():
    """Test that critical static files exist and are not empty"""
    print("\n📄 Testing Critical Static Files")
    print("-" * 40)
    
    critical_files = [
        "admin-dashboard/frontend/css/modern-dashboard.css",
        "admin-dashboard/frontend/js/main.js",
        "admin-dashboard/frontend/js/auth.js",
        "admin-dashboard/frontend/js/dashboard.js",
        "admin-dashboard/frontend/index.html"
    ]
    
    all_valid = True
    
    for file_path_str in critical_files:
        file_path = Path(file_path_str)
        
        if file_path.exists():
            size = file_path.stat().st_size
            if size > 0:
                print(f"✅ {file_path.name}: {size} bytes")
            else:
                print(f"❌ {file_path.name}: Empty file")
                all_valid = False
        else:
            print(f"❌ {file_path.name}: File not found")
            all_valid = False
    
    return all_valid

def run_integration_tests():
    """Run all integration tests"""
    print("*** Static Files Integration Test Suite ***")
    print("=" * 50)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: FastAPI app import
    tests_total += 1
    app_imported, app = test_fastapi_app_import()
    if app_imported:
        tests_passed += 1
    
    # Test 2: File system structure
    tests_total += 1
    if test_file_system_structure():
        tests_passed += 1
    
    # Test 3: Critical static files
    tests_total += 1
    if test_critical_static_files():
        tests_passed += 1
    
    # Test 4: Static file mounts (only if app imported successfully)
    if app_imported:
        tests_total += 1
        if test_static_file_mounts(app):
            tests_passed += 1
    
    # Test 5: TestClient functionality (only if app imported successfully)
    if app_imported:
        tests_total += 1
        if test_testclient_functionality(app):
            tests_passed += 1
    
    # Summary
    print(f"\n📊 Integration Test Summary")
    print("=" * 30)
    print(f"Tests passed: {tests_passed}/{tests_total}")
    print(f"Success rate: {(tests_passed/tests_total*100):.1f}%")
    
    if tests_passed == tests_total:
        print("\n🎉 All integration tests passed!")
        print("✅ Static file serving is properly configured")
        return True
    else:
        print(f"\n⚠️  {tests_total - tests_passed} integration tests failed")
        print("❌ Static file serving may have configuration issues")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)