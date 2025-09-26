#!/usr/bin/env python3
"""
Comprehensive test for Task 3: Update admin dashboard HTML file serving
Tests all requirements: 3.1, 3.2, 3.3
"""

import requests
import sys
import time

def test_requirement_3_1():
    """Test Requirement 3.1: Admin dashboard root serves index.html correctly"""
    print("📋 Testing Requirement 3.1: Admin dashboard root endpoint")
    
    try:
        response = requests.get('http://localhost:8000/admin/', timeout=10)
        
        if response.status_code == 200:
            content = response.text
            
            # Check for key elements that should be in index.html
            required_elements = [
                'Admin Dashboard',
                'Support Tickets',
                'User Management',
                'Settings',
                'Integration',
                'System Logs',
                'css/modern-dashboard.css',
                'js/main.js'
            ]
            
            missing_elements = []
            for element in required_elements:
                if element not in content:
                    missing_elements.append(element)
            
            if not missing_elements:
                print("✅ Requirement 3.1 PASSED: Admin dashboard root serves index.html correctly")
                return True
            else:
                print(f"❌ Requirement 3.1 FAILED: Missing elements: {missing_elements}")
                return False
        else:
            print(f"❌ Requirement 3.1 FAILED: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Requirement 3.1 FAILED: {e}")
        return False

def test_requirement_3_2():
    """Test Requirement 3.2: Proper endpoints for serving other admin HTML files"""
    print("\n📋 Testing Requirement 3.2: Other admin HTML file endpoints")
    
    admin_pages = [
        'tickets.html',
        'users.html', 
        'settings.html',
        'integration.html',
        'logs.html'
    ]
    
    results = []
    
    for page in admin_pages:
        try:
            url = f'http://localhost:8000/admin/{page}'
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                # Check that it's actually HTML content
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type:
                    print(f"✅ {page}: Status 200, HTML content")
                    results.append(True)
                else:
                    print(f"❌ {page}: Status 200 but wrong content type: {content_type}")
                    results.append(False)
            else:
                print(f"❌ {page}: HTTP {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"❌ {page}: Error - {e}")
            results.append(False)
    
    if all(results):
        print("✅ Requirement 3.2 PASSED: All admin HTML files are properly served")
        return True
    else:
        failed_count = len([r for r in results if not r])
        print(f"❌ Requirement 3.2 FAILED: {failed_count}/{len(results)} pages failed")
        return False

def test_requirement_3_3():
    """Test Requirement 3.3: HTML files reference static assets with correct paths"""
    print("\n📋 Testing Requirement 3.3: Static asset references and accessibility")
    
    # Test that static assets referenced in HTML are accessible
    static_assets = [
        'http://localhost:8000/css/modern-dashboard.css',
        'http://localhost:8000/js/main.js',
        'http://localhost:8000/js/auth.js',
        'http://localhost:8000/js/dashboard.js',
        'http://localhost:8000/js/session-manager.js'
    ]
    
    results = []
    
    for asset_url in static_assets:
        try:
            response = requests.get(asset_url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {asset_url.split('/')[-1]}: Accessible")
                results.append(True)
            else:
                print(f"❌ {asset_url.split('/')[-1]}: HTTP {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ {asset_url.split('/')[-1]}: Error - {e}")
            results.append(False)
    
    # Test that HTML files contain correct static asset references
    try:
        response = requests.get('http://localhost:8000/admin/', timeout=5)
        if response.status_code == 200:
            content = response.text
            
            # Check for relative path references (which should work with our static file mounting)
            static_refs = [
                'css/modern-dashboard.css',
                'js/main.js',
                'js/auth.js'
            ]
            
            ref_results = []
            for ref in static_refs:
                if ref in content:
                    print(f"✅ HTML contains reference: {ref}")
                    ref_results.append(True)
                else:
                    print(f"❌ HTML missing reference: {ref}")
                    ref_results.append(False)
            
            results.extend(ref_results)
    
    except Exception as e:
        print(f"❌ Error checking HTML references: {e}")
        results.append(False)
    
    if all(results):
        print("✅ Requirement 3.3 PASSED: Static assets are correctly referenced and accessible")
        return True
    else:
        failed_count = len([r for r in results if not r])
        print(f"❌ Requirement 3.3 FAILED: {failed_count}/{len(results)} checks failed")
        return False

def test_dashboard_loads_properly():
    """Additional test: Verify /admin/ loads the dashboard properly"""
    print("\n📋 Additional Test: Dashboard loads properly")
    
    try:
        response = requests.get('http://localhost:8000/admin/', timeout=10)
        
        if response.status_code == 200:
            content = response.text
            
            # Check for key dashboard elements
            dashboard_elements = [
                'dashboard-container',
                'sidebar',
                'main-content',
                'stats-grid',
                'recent-tickets-table'
            ]
            
            found_elements = []
            for element in dashboard_elements:
                if element in content:
                    found_elements.append(element)
            
            if len(found_elements) >= 4:  # Most elements should be present
                print(f"✅ Dashboard loads properly with {len(found_elements)}/{len(dashboard_elements)} key elements")
                return True
            else:
                print(f"❌ Dashboard incomplete: only {len(found_elements)}/{len(dashboard_elements)} elements found")
                return False
        else:
            print(f"❌ Dashboard not accessible: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        return False

def main():
    print("🧪 Task 3 Comprehensive Test: Update admin dashboard HTML file serving")
    print("=" * 70)
    print("Testing Requirements: 3.1, 3.2, 3.3")
    print()
    
    # Wait a moment for server to be ready
    time.sleep(1)
    
    # Run all requirement tests
    req_3_1 = test_requirement_3_1()
    req_3_2 = test_requirement_3_2()
    req_3_3 = test_requirement_3_3()
    dashboard_test = test_dashboard_loads_properly()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TASK 3 TEST SUMMARY")
    print("=" * 50)
    
    results = {
        "Requirement 3.1 (Admin root endpoint)": req_3_1,
        "Requirement 3.2 (Other HTML endpoints)": req_3_2, 
        "Requirement 3.3 (Static asset references)": req_3_3,
        "Dashboard functionality": dashboard_test
    }
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 TASK 3 IMPLEMENTATION SUCCESSFUL!")
        print("All requirements have been met:")
        print("- ✅ Admin dashboard root endpoint serves index.html correctly")
        print("- ✅ Proper endpoints for serving other admin HTML files")
        print("- ✅ HTML files reference static assets with correct paths")
        print("- ✅ /admin/ loads the dashboard properly")
        return True
    else:
        print(f"\n❌ TASK 3 NEEDS ATTENTION: {total - passed} requirements failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)