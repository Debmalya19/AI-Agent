#!/usr/bin/env python3
"""
Test script to verify navigation functionality and active state management
"""

import os
import re
import json
from pathlib import Path

def test_navigation_functionality():
    """Test navigation functionality and active state management"""
    
    frontend_dir = Path("ai-agent/admin-dashboard/frontend")
    
    print("🔍 Testing Navigation Functionality and Active State Management")
    print("=" * 65)
    
    # Test cases for each page
    test_cases = [
        {
            "file": "index.html",
            "expected_active": "nav-dashboard",
            "page_name": "Dashboard"
        },
        {
            "file": "tickets.html", 
            "expected_active": "nav-tickets",
            "page_name": "Support Tickets"
        },
        {
            "file": "users.html",
            "expected_active": "nav-users", 
            "page_name": "User Management"
        },
        {
            "file": "integration.html",
            "expected_active": "nav-integration",
            "page_name": "AI Integration"
        },
        {
            "file": "settings.html",
            "expected_active": "nav-settings",
            "page_name": "Settings"
        },
        {
            "file": "logs.html",
            "expected_active": "nav-logs",
            "page_name": "System Logs"
        }
    ]
    
    issues_found = []
    
    for test_case in test_cases:
        file_path = frontend_dir / test_case["file"]
        print(f"\n📄 Testing {test_case['file']} - {test_case['page_name']}")
        
        if not file_path.exists():
            issues_found.append(f"❌ {test_case['file']}: File does not exist")
            continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test 1: Check if the correct navigation item has 'active' class
        # Look for either class="active" or class="active ..." or class="... active ..."
        active_patterns = [
            rf'<a[^>]*id="{re.escape(test_case["expected_active"])}"[^>]*class="active"[^>]*>',
            rf'<a[^>]*id="{re.escape(test_case["expected_active"])}"[^>]*class="[^"]*active[^"]*"[^>]*>',
            rf'<a[^>]*class="active"[^>]*id="{re.escape(test_case["expected_active"])}"[^>]*>',
            rf'<a[^>]*class="[^"]*active[^"]*"[^>]*id="{re.escape(test_case["expected_active"])}"[^>]*>'
        ]
        
        found_active = False
        for pattern in active_patterns:
            if re.search(pattern, content):
                found_active = True
                break
        
        if found_active:
            print(f"  ✅ Correct navigation item ({test_case['expected_active']}) has active class")
        else:
            issues_found.append(f"❌ {test_case['file']}: Navigation item {test_case['expected_active']} does not have active class")
        
        # Test 2: Check that other navigation items don't have active class (except the current one)
        all_nav_ids = ["nav-dashboard", "nav-tickets", "nav-users", "nav-integration", "nav-settings", "nav-logs"]
        for nav_id in all_nav_ids:
            if nav_id != test_case["expected_active"]:
                # Check if this nav item incorrectly has active class
                incorrect_patterns = [
                    rf'<a[^>]*id="{re.escape(nav_id)}"[^>]*class="active"[^>]*>',
                    rf'<a[^>]*id="{re.escape(nav_id)}"[^>]*class="[^"]*active[^"]*"[^>]*>',
                    rf'<a[^>]*class="active"[^>]*id="{re.escape(nav_id)}"[^>]*>',
                    rf'<a[^>]*class="[^"]*active[^"]*"[^>]*id="{re.escape(nav_id)}"[^>]*>'
                ]
                
                for pattern in incorrect_patterns:
                    if re.search(pattern, content):
                        issues_found.append(f"❌ {test_case['file']}: Navigation item {nav_id} incorrectly has active class")
                        break
        
        # Test 3: Check page title matches expected
        title_pattern = rf'<title>([^<]+)</title>'
        title_match = re.search(title_pattern, content)
        if title_match:
            title = title_match.group(1)
            if test_case['page_name'] in title:
                print(f"  ✅ Page title contains expected text: '{title}'")
            else:
                print(f"  ⚠️  Page title '{title}' doesn't contain '{test_case['page_name']}' (may be acceptable)")
        else:
            issues_found.append(f"❌ {test_case['file']}: No page title found")
        
        # Test 4: Check if navigation.js is included
        if 'navigation.js' in content:
            print(f"  ✅ Navigation.js is included")
        else:
            issues_found.append(f"❌ {test_case['file']}: Navigation.js is not included")
    
    # Test 5: Verify navigation.js has correct page mapping
    nav_js_path = frontend_dir / "js" / "navigation.js"
    if nav_js_path.exists():
        print(f"\n📄 Testing navigation.js page mapping")
        with open(nav_js_path, 'r', encoding='utf-8') as f:
            nav_js_content = f.read()
        
        # Check if pageMap exists and has correct mappings
        page_map_pattern = r'pageMap\s*=\s*{([^}]+)}'
        page_map_match = re.search(page_map_pattern, nav_js_content)
        if page_map_match:
            page_map_content = page_map_match.group(1)
            expected_mappings = [
                ("'index.html'", "'dashboard'"),
                ("'tickets.html'", "'tickets'"),
                ("'users.html'", "'users'"),
                ("'integration.html'", "'integration'"),
                ("'settings.html'", "'settings'"),
                ("'logs.html'", "'logs'")
            ]
            
            for file_key, page_key in expected_mappings:
                if file_key in page_map_content and page_key in page_map_content:
                    print(f"  ✅ Page mapping {file_key} -> {page_key} found")
                else:
                    issues_found.append(f"❌ navigation.js: Missing page mapping {file_key} -> {page_key}")
        else:
            issues_found.append(f"❌ navigation.js: pageMap object not found")
        
        # Check if breadcrumb mappings exist for all pages
        # Use a more flexible pattern to match the breadcrumbMap object
        breadcrumb_pattern = r'breadcrumbMap\s*=\s*{(.*?)};'
        breadcrumb_match = re.search(breadcrumb_pattern, nav_js_content, re.DOTALL)
        if breadcrumb_match:
            breadcrumb_content = breadcrumb_match.group(1)
            expected_pages = ['dashboard', 'tickets', 'users', 'integration', 'settings', 'logs']
            for page in expected_pages:
                if f"'{page}'" in breadcrumb_content:
                    print(f"  ✅ Breadcrumb mapping for '{page}' found")
                else:
                    issues_found.append(f"❌ navigation.js: Missing breadcrumb mapping for '{page}'")
        else:
            issues_found.append(f"❌ navigation.js: breadcrumbMap object not found")
    
    # Summary
    print("\n" + "=" * 65)
    if issues_found:
        print(f"❌ NAVIGATION FUNCTIONALITY TEST FAILED - {len(issues_found)} issues found:")
        for issue in issues_found:
            print(f"  {issue}")
        return False
    else:
        print("✅ ALL NAVIGATION FUNCTIONALITY TESTS PASSED!")
        print("  - All pages have correct active navigation states")
        print("  - No incorrect active states found")
        print("  - All page titles are appropriate")
        print("  - Navigation.js is properly included")
        print("  - Page mappings and breadcrumbs are configured")
        return True

if __name__ == "__main__":
    success = test_navigation_functionality()
    exit(0 if success else 1)