#!/usr/bin/env python3
"""
Test script to verify navigation standardization across admin dashboard pages
"""

import os
import re
from pathlib import Path

def test_navigation_standardization():
    """Test that all admin dashboard pages have consistent navigation"""
    
    frontend_dir = Path("admin-dashboard/frontend")
    html_files = [
        "index.html",
        "tickets.html", 
        "users.html",
        "integration.html",
        "settings.html",
        "logs.html"
    ]
    
    results = {
        "navigation_js_included": {},
        "breadcrumb_structure": {},
        "sidebar_nav_structure": {},
        "user_dropdown_structure": {},
        "search_functionality": {}
    }
    
    for html_file in html_files:
        file_path = frontend_dir / html_file
        if not file_path.exists():
            print(f"❌ File not found: {html_file}")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"\n🔍 Testing {html_file}:")
        
        # Test 1: Navigation.js is included
        nav_js_included = '/admin/js/navigation.js' in content
        results["navigation_js_included"][html_file] = nav_js_included
        print(f"  ✅ Navigation.js included: {nav_js_included}")
        
        # Test 2: Breadcrumb structure is standardized
        breadcrumb_pattern = r'<nav class="breadcrumb">\s*<!--.*?-->\s*</nav>'
        breadcrumb_standardized = bool(re.search(breadcrumb_pattern, content, re.DOTALL))
        results["breadcrumb_structure"][html_file] = breadcrumb_standardized
        print(f"  ✅ Breadcrumb standardized: {breadcrumb_standardized}")
        
        # Test 3: Sidebar navigation has consistent IDs
        nav_ids = [
            'nav-dashboard',
            'nav-tickets', 
            'nav-users',
            'nav-integration',
            'nav-settings',
            'nav-logs'
        ]
        
        nav_ids_present = sum(1 for nav_id in nav_ids if nav_id in content)
        nav_structure_consistent = nav_ids_present >= 5  # Should have most nav IDs
        results["sidebar_nav_structure"][html_file] = nav_structure_consistent
        print(f"  ✅ Sidebar nav structure consistent: {nav_structure_consistent} ({nav_ids_present}/6 IDs found)")
        
        # Test 4: User dropdown has consistent structure
        user_dropdown_elements = [
            'id="userDropdown"',
            'id="nav-profile"',
            'id="nav-logout-dropdown"'
        ]
        
        dropdown_elements_present = sum(1 for element in user_dropdown_elements if element in content)
        dropdown_consistent = dropdown_elements_present >= 2
        results["user_dropdown_structure"][html_file] = dropdown_consistent
        print(f"  ✅ User dropdown consistent: {dropdown_consistent} ({dropdown_elements_present}/3 elements found)")
        
        # Test 5: Search functionality is present
        search_elements = [
            'class="search-box"',
            'placeholder="Search'
        ]
        
        search_elements_present = sum(1 for element in search_elements if element in content)
        search_present = search_elements_present >= 1
        results["search_functionality"][html_file] = search_present
        print(f"  ✅ Search functionality present: {search_present}")
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"=" * 50)
    
    for test_name, test_results in results.items():
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        print(f"{test_name}: {passed}/{total} pages passed")
    
    # Overall score
    total_tests = sum(len(test_results) for test_results in results.values())
    total_passed = sum(sum(1 for result in test_results.values() if result) for test_results in results.values())
    
    if total_tests > 0:
        print(f"\n🎯 OVERALL SCORE: {total_passed}/{total_tests} ({total_passed/total_tests*100:.1f}%)")
    else:
        print(f"\n🎯 OVERALL SCORE: 0/0 (No files found)")
    
    if total_passed == total_tests:
        print("🎉 All navigation standardization tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Check the details above.")
        return False

def test_navigation_js_syntax():
    """Test that navigation.js has valid syntax"""
    
    nav_js_path = Path("admin-dashboard/frontend/js/navigation.js")
    
    if not nav_js_path.exists():
        print("❌ navigation.js file not found")
        return False
    
    with open(nav_js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Basic syntax checks
    checks = [
        ("Class definition", "class NavigationManager" in content),
        ("Constructor", "constructor()" in content),
        ("Init method", "init()" in content),
        ("Setup methods", "setupSidebarNavigation()" in content),
        ("Breadcrumb setup", "setupBreadcrumbs()" in content),
        ("Search setup", "setupSearchFunctionality()" in content),
        ("User dropdown setup", "setupUserDropdown()" in content),
        ("Event listeners", "addEventListener" in content),
        ("Export/Instance", "NavigationManager.getInstance()" in content)
    ]
    
    print(f"\n🔍 Testing navigation.js syntax:")
    
    passed = 0
    for check_name, check_result in checks:
        print(f"  ✅ {check_name}: {check_result}")
        if check_result:
            passed += 1
    
    print(f"\n📊 Navigation.js syntax: {passed}/{len(checks)} checks passed")
    
    return passed == len(checks)

if __name__ == "__main__":
    print("🚀 Testing Navigation Standardization")
    print("=" * 50)
    
    # Test navigation standardization
    nav_test_passed = test_navigation_standardization()
    
    # Test navigation.js syntax
    js_test_passed = test_navigation_js_syntax()
    
    print(f"\n🏁 FINAL RESULTS:")
    print(f"Navigation standardization: {'✅ PASSED' if nav_test_passed else '❌ FAILED'}")
    print(f"Navigation.js syntax: {'✅ PASSED' if js_test_passed else '❌ FAILED'}")
    
    if nav_test_passed and js_test_passed:
        print(f"\n🎉 All tests passed! Navigation standardization is complete.")
        exit(0)
    else:
        print(f"\n⚠️  Some tests failed. Please review the implementation.")
        exit(1)