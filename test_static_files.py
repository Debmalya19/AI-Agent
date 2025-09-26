#!/usr/bin/env python3
"""
Test script to verify admin dashboard static files are accessible
"""
import requests
import sys
import os

def test_static_file_access():
    """Test that admin dashboard static files are accessible at correct paths"""
    base_url = "http://localhost:8000"
    
    # Test CSS files
    css_files = [
        "modern-dashboard.css",
        "admin.css", 
        "styles.css",
        "support.css"
    ]
    
    # Test JavaScript files
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
    
    print("Testing admin dashboard static file accessibility...")
    print("=" * 60)
    
    # Test root-level CSS paths
    print("\n🎨 Testing CSS files at root paths:")
    for css_file in css_files:
        url = f"{base_url}/css/{css_file}"
        try:
            response = requests.get(url, timeout=5)
            status = "✅ PASS" if response.status_code == 200 else f"❌ FAIL ({response.status_code})"
            print(f"  {css_file:<25} {status}")
        except requests.exceptions.RequestException as e:
            print(f"  {css_file:<25} ❌ ERROR: {e}")
    
    # Test root-level JS paths
    print("\n📜 Testing JavaScript files at root paths:")
    for js_file in js_files:
        url = f"{base_url}/js/{js_file}"
        try:
            response = requests.get(url, timeout=5)
            status = "✅ PASS" if response.status_code == 200 else f"❌ FAIL ({response.status_code})"
            print(f"  {js_file:<25} {status}")
        except requests.exceptions.RequestException as e:
            print(f"  {js_file:<25} ❌ ERROR: {e}")
    
    # Test admin-prefixed paths (should still work)
    print("\n🔧 Testing admin-prefixed paths (compatibility):")
    test_files = [
        ("/admin/css/modern-dashboard.css", "CSS via /admin"),
        ("/admin/js/session-manager.js", "JS via /admin"),
        ("/admin/index.html", "Admin dashboard root")
    ]
    
    for url_path, description in test_files:
        url = f"{base_url}{url_path}"
        try:
            response = requests.get(url, timeout=5)
            status = "✅ PASS" if response.status_code == 200 else f"❌ FAIL ({response.status_code})"
            print(f"  {description:<25} {status}")
        except requests.exceptions.RequestException as e:
            print(f"  {description:<25} ❌ ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("Test completed. If server is not running, start it with: python main.py")

if __name__ == "__main__":
    test_static_file_access()