#!/usr/bin/env python3
"""
Comprehensive test for Task 1: Fix static file serving configuration in main.py
Tests all requirements: 1.1, 2.1, 4.1
"""
import requests
import time
import subprocess
import sys
import os
from pathlib import Path

def start_server():
    """Start the FastAPI server"""
    print("🚀 Starting FastAPI server...")
    process = subprocess.Popen([sys.executable, "main.py"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    
    # Wait for server to start
    for i in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get("http://localhost:8000", timeout=1)
            if response.status_code == 200:
                print("✅ Server started successfully")
                return process
        except:
            time.sleep(1)
    
    print("❌ Server failed to start")
    return None

def test_requirement_1_1():
    """Test Requirement 1.1: CSS files served successfully without 404 errors"""
    print("\n📋 Testing Requirement 1.1: CSS files accessibility")
    print("-" * 50)
    
    css_files = [
        "modern-dashboard.css",
        "admin.css", 
        "styles.css",
        "support.css"
    ]
    
    all_passed = True
    
    for css_file in css_files:
        url = f"http://localhost:8000/css/{css_file}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'css' in content_type.lower() or 'text' in content_type.lower():
                    print(f"  ✅ {css_file:<25} - Status: {response.status_code}, Type: {content_type}")
                else:
                    print(f"  ⚠️  {css_file:<25} - Status: {response.status_code}, Unexpected type: {content_type}")
                    all_passed = False
            else:
                print(f"  ❌ {css_file:<25} - Status: {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"  ❌ {css_file:<25} - Error: {e}")
            all_passed = False
    
    return all_passed

def test_requirement_2_1():
    """Test Requirement 2.1: JavaScript files served without 404 errors"""
    print("\n📋 Testing Requirement 2.1: JavaScript files accessibility")
    print("-" * 50)
    
    js_files = [
        "session-manager.js",
        "auth-error-handler.js",
        "api-connectivity-checker.js",
        "admin-auth-service.js",
        "unified_api.js",
        "api.js",
        "navigation.js",
        "ui-feedback.js",
        "auth.js",
        "dashboard.js",
        "integration.js",
        "main.js",
        "simple-auth-fix.js"
    ]
    
    all_passed = True
    
    for js_file in js_files:
        url = f"http://localhost:8000/js/{js_file}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'javascript' in content_type.lower() or 'text' in content_type.lower():
                    print(f"  ✅ {js_file:<25} - Status: {response.status_code}, Type: {content_type}")
                else:
                    print(f"  ⚠️  {js_file:<25} - Status: {response.status_code}, Unexpected type: {content_type}")
                    all_passed = False
            else:
                print(f"  ❌ {js_file:<25} - Status: {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"  ❌ {js_file:<25} - Error: {e}")
            all_passed = False
    
    return all_passed

def test_requirement_4_1():
    """Test Requirement 4.1: Static file serving configuration properly set up"""
    print("\n📋 Testing Requirement 4.1: Static file serving configuration")
    print("-" * 50)
    
    # Test that both root-level and admin-prefixed paths work
    test_cases = [
        ("/css/modern-dashboard.css", "Root-level CSS"),
        ("/js/session-manager.js", "Root-level JS"),
        ("/admin/css/modern-dashboard.css", "Admin-prefixed CSS"),
        ("/admin/js/session-manager.js", "Admin-prefixed JS"),
        ("/admin/", "Admin dashboard root"),
        ("/admin/index.html", "Admin index.html")
    ]
    
    all_passed = True
    
    for path, description in test_cases:
        url = f"http://localhost:8000{path}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"  ✅ {description:<25} - Status: {response.status_code}")
            else:
                print(f"  ❌ {description:<25} - Status: {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"  ❌ {description:<25} - Error: {e}")
            all_passed = False
    
    return all_passed

def test_route_ordering():
    """Test that route ordering prevents conflicts"""
    print("\n📋 Testing Route Ordering and Conflict Prevention")
    print("-" * 50)
    
    # Test that specific routes take precedence
    test_cases = [
        ("/css/modern-dashboard.css", "Should serve from admin CSS directory"),
        ("/js/main.js", "Should serve from admin JS directory"),
        ("/static/some-file.css", "Should serve from main static directory (if exists)"),
        ("/admin/css/modern-dashboard.css", "Should serve from admin mount")
    ]
    
    all_passed = True
    
    for path, description in test_cases:
        url = f"http://localhost:8000{path}"
        try:
            response = requests.get(url, timeout=5)
            # For existing files, expect 200; for non-existing, expect 404
            if path == "/static/some-file.css":
                # This file doesn't exist, so 404 is expected
                expected_status = 404
            else:
                expected_status = 200
            
            if response.status_code == expected_status:
                print(f"  ✅ {description:<40} - Status: {response.status_code}")
            else:
                print(f"  ❌ {description:<40} - Status: {response.status_code} (expected {expected_status})")
                all_passed = False
        except Exception as e:
            print(f"  ❌ {description:<40} - Error: {e}")
            all_passed = False
    
    return all_passed

def test_admin_dashboard_loading():
    """Test that admin dashboard loads with all static files"""
    print("\n📋 Testing Admin Dashboard Complete Loading")
    print("-" * 50)
    
    try:
        # Get the admin dashboard HTML
        response = requests.get("http://localhost:8000/admin/", timeout=5)
        if response.status_code != 200:
            print(f"  ❌ Admin dashboard failed to load - Status: {response.status_code}")
            return False
        
        html_content = response.text
        
        # Check that HTML references to static files are present
        expected_references = [
            'href="css/modern-dashboard.css"',
            'src="js/session-manager.js"',
            'src="js/auth.js"',
            'src="js/main.js"'
        ]
        
        all_passed = True
        
        for reference in expected_references:
            if reference in html_content:
                print(f"  ✅ Found reference: {reference}")
            else:
                print(f"  ❌ Missing reference: {reference}")
                all_passed = False
        
        print(f"  📊 HTML content size: {len(html_content):,} characters")
        
        return all_passed
        
    except Exception as e:
        print(f"  ❌ Error testing admin dashboard: {e}")
        return False

def main():
    """Run comprehensive tests for Task 1"""
    print("🧪 Comprehensive Test Suite for Task 1")
    print("Fix static file serving configuration in main.py")
    print("=" * 60)
    
    # Start server
    server_process = start_server()
    if not server_process:
        print("❌ Cannot run tests - server failed to start")
        return False
    
    try:
        # Run all tests
        results = {
            "Requirement 1.1 (CSS files)": test_requirement_1_1(),
            "Requirement 2.1 (JS files)": test_requirement_2_1(),
            "Requirement 4.1 (Configuration)": test_requirement_4_1(),
            "Route Ordering": test_route_ordering(),
            "Admin Dashboard Loading": test_admin_dashboard_loading()
        }
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        all_passed = True
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {test_name:<30} {status}")
            if not passed:
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ALL TESTS PASSED! Task 1 implementation is successful.")
            print("✅ Static file serving configuration is working correctly.")
            print("✅ All requirements (1.1, 2.1, 4.1) are satisfied.")
        else:
            print("❌ SOME TESTS FAILED! Please review the implementation.")
        
        return all_passed
        
    finally:
        # Stop server
        print("\n🛑 Stopping server...")
        server_process.terminate()
        server_process.wait()
        print("✅ Server stopped")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)