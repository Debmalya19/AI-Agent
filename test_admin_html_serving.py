#!/usr/bin/env python3
"""
Test script to verify admin dashboard HTML file serving functionality.
This tests task 3: Update admin dashboard HTML file serving.
"""

import requests
import sys
import os
from pathlib import Path

def test_admin_html_serving():
    """Test that admin dashboard HTML files are served correctly"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Admin Dashboard HTML File Serving")
    print("=" * 50)
    
    # Test cases for admin dashboard HTML files
    test_cases = [
        {
            "url": f"{base_url}/admin/",
            "description": "Admin dashboard root (index.html)",
            "expected_content": ["Admin Dashboard", "Support Tickets", "User Management"]
        },
        {
            "url": f"{base_url}/admin/tickets.html",
            "description": "Support Tickets page",
            "expected_content": ["Support Tickets", "Admin Dashboard", "css/modern-dashboard.css"]
        },
        {
            "url": f"{base_url}/admin/users.html",
            "description": "User Management page",
            "expected_content": ["User Management", "Admin Dashboard", "css/modern-dashboard.css"]
        },
        {
            "url": f"{base_url}/admin/settings.html",
            "description": "Settings page",
            "expected_content": ["Settings", "Admin Dashboard"]
        },
        {
            "url": f"{base_url}/admin/integration.html",
            "description": "Integration page",
            "expected_content": ["Integration", "Admin Dashboard"]
        },
        {
            "url": f"{base_url}/admin/logs.html",
            "description": "Logs page",
            "expected_content": ["Logs", "Admin Dashboard"]
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n📋 Testing: {test_case['description']}")
        print(f"URL: {test_case['url']}")
        
        try:
            response = requests.get(test_case['url'], timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Status: {response.status_code} OK")
                
                # Check content type
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type:
                    print(f"✅ Content-Type: {content_type}")
                else:
                    print(f"⚠️  Content-Type: {content_type} (expected HTML)")
                
                # Check for expected content
                content = response.text
                content_checks = []
                
                for expected in test_case['expected_content']:
                    if expected in content:
                        content_checks.append(f"✅ Found: '{expected}'")
                    else:
                        content_checks.append(f"❌ Missing: '{expected}'")
                
                for check in content_checks:
                    print(f"  {check}")
                
                # Check for static asset references
                static_assets = []
                if 'css/modern-dashboard.css' in content:
                    static_assets.append("✅ CSS reference found")
                if 'js/' in content:
                    static_assets.append("✅ JS references found")
                
                for asset in static_assets:
                    print(f"  {asset}")
                
                results.append({
                    "url": test_case['url'],
                    "status": "PASS",
                    "status_code": response.status_code,
                    "content_type": content_type,
                    "content_checks": len([c for c in content_checks if c.startswith("✅")]),
                    "total_checks": len(content_checks)
                })
                
            else:
                print(f"❌ Status: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                results.append({
                    "url": test_case['url'],
                    "status": "FAIL",
                    "status_code": response.status_code,
                    "error": f"HTTP {response.status_code}"
                })
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            results.append({
                "url": test_case['url'],
                "status": "ERROR",
                "error": str(e)
            })
    
    # Test static asset accessibility from admin pages
    print(f"\n📋 Testing Static Asset Accessibility")
    static_asset_tests = [
        f"{base_url}/css/modern-dashboard.css",
        f"{base_url}/js/main.js",
        f"{base_url}/js/auth.js",
        f"{base_url}/js/dashboard.js"
    ]
    
    for asset_url in static_asset_tests:
        try:
            response = requests.get(asset_url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {asset_url} - Status: {response.status_code}")
            else:
                print(f"❌ {asset_url} - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ {asset_url} - Error: {e}")
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 30)
    
    passed = len([r for r in results if r['status'] == 'PASS'])
    failed = len([r for r in results if r['status'] in ['FAIL', 'ERROR']])
    total = len(results)
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("🎉 All admin dashboard HTML serving tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check the server configuration.")
        return False

def test_redirect_endpoints():
    """Test that redirect endpoints work correctly"""
    base_url = "http://localhost:8000"
    
    print(f"\n📋 Testing Redirect Endpoints")
    print("=" * 30)
    
    redirect_tests = [
        {"from": f"{base_url}/tickets.html", "to": "/admin/tickets.html"},
        {"from": f"{base_url}/users.html", "to": "/admin/users.html"},
        {"from": f"{base_url}/settings.html", "to": "/admin/settings.html"},
        {"from": f"{base_url}/integration.html", "to": "/admin/integration.html"},
        {"from": f"{base_url}/logs.html", "to": "/admin/logs.html"}
    ]
    
    for test in redirect_tests:
        try:
            response = requests.get(test['from'], allow_redirects=False, timeout=5)
            if response.status_code == 301:
                location = response.headers.get('location', '')
                if test['to'] in location:
                    print(f"✅ {test['from']} → {location}")
                else:
                    print(f"❌ {test['from']} → {location} (expected {test['to']})")
            else:
                print(f"❌ {test['from']} - Status: {response.status_code} (expected 301)")
        except Exception as e:
            print(f"❌ {test['from']} - Error: {e}")

if __name__ == "__main__":
    print("Starting Admin Dashboard HTML Serving Tests...")
    print("Make sure the server is running on http://localhost:8000")
    print()
    
    # Test HTML serving
    html_success = test_admin_html_serving()
    
    # Test redirects
    test_redirect_endpoints()
    
    if html_success:
        print("\n🎉 Task 3 implementation appears to be working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Task 3 implementation needs attention.")
        sys.exit(1)