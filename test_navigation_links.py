#!/usr/bin/env python3
"""
Test script to verify navigation links and consistency across admin dashboard pages
"""

import os
import re
from pathlib import Path

def test_navigation_consistency():
    """Test navigation consistency across all admin dashboard pages"""
    
    frontend_dir = Path("ai-agent/admin-dashboard/frontend")
    html_files = [
        "index.html",
        "tickets.html", 
        "users.html",
        "integration.html",
        "settings.html",
        "logs.html"
    ]
    
    print("🔍 Testing Navigation Consistency Across Admin Dashboard Pages")
    print("=" * 60)
    
    # Expected navigation structure
    expected_nav_links = [
        ("/admin/index.html", "nav-dashboard", "Dashboard"),
        ("/admin/tickets.html", "nav-tickets", "Support Tickets"),
        ("/admin/users.html", "nav-users", "User Management"),
        ("/admin/integration.html", "nav-integration", "AI Integration"),
        ("/admin/settings.html", "nav-settings", "Settings"),
        ("/admin/logs.html", "nav-logs", "System Logs")
    ]
    
    issues_found = []
    
    for html_file in html_files:
        file_path = frontend_dir / html_file
        if not file_path.exists():
            issues_found.append(f"❌ {html_file}: File does not exist")
            continue
            
        print(f"\n📄 Testing {html_file}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test 1: Check if all navigation links are present
        for href, nav_id, text in expected_nav_links:
            # Check if navigation link exists
            nav_pattern = rf'<a[^>]*href="{re.escape(href)}"[^>]*id="{re.escape(nav_id)}"[^>]*>'
            if not re.search(nav_pattern, content):
                issues_found.append(f"❌ {html_file}: Missing navigation link {nav_id}")
            else:
                print(f"  ✅ Navigation link {nav_id} found")
        
        # Test 2: Check if page title element exists
        if 'id="page-title"' in content:
            print(f"  ✅ Page title element found")
        else:
            issues_found.append(f"❌ {html_file}: Missing page title element with id='page-title'")
        
        # Test 3: Check if breadcrumb container exists
        if 'class="breadcrumb"' in content:
            print(f"  ✅ Breadcrumb container found")
        else:
            issues_found.append(f"❌ {html_file}: Missing breadcrumb container")
        
        # Test 4: Check for consistent navigation text
        for href, nav_id, expected_text in expected_nav_links:
            # Look for the navigation link and extract its text
            nav_link_pattern = rf'<a[^>]*id="{re.escape(nav_id)}"[^>]*>.*?{re.escape(expected_text)}.*?</a>'
            if not re.search(nav_link_pattern, content, re.DOTALL):
                # Try to find what text is actually there
                actual_pattern = rf'<a[^>]*id="{re.escape(nav_id)}"[^>]*>(.*?)</a>'
                match = re.search(actual_pattern, content, re.DOTALL)
                if match:
                    actual_text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                    if expected_text not in actual_text:
                        issues_found.append(f"❌ {html_file}: Navigation text mismatch for {nav_id}. Expected: '{expected_text}', Found: '{actual_text}'")
                else:
                    issues_found.append(f"❌ {html_file}: Could not find navigation text for {nav_id}")
    
    # Test 5: Check navigation.js for page support
    nav_js_path = frontend_dir / "js" / "navigation.js"
    if nav_js_path.exists():
        print(f"\n📄 Testing navigation.js")
        with open(nav_js_path, 'r', encoding='utf-8') as f:
            nav_js_content = f.read()
        
        # Check if all pages are supported in navigation.js
        expected_pages = ['dashboard', 'tickets', 'users', 'integration', 'settings', 'logs']
        for page in expected_pages:
            if f"'{page}'" in nav_js_content:
                print(f"  ✅ Page '{page}' supported in navigation.js")
            else:
                issues_found.append(f"❌ navigation.js: Missing support for page '{page}'")
    else:
        issues_found.append(f"❌ navigation.js: File does not exist")
    
    # Summary
    print("\n" + "=" * 60)
    if issues_found:
        print(f"❌ NAVIGATION TEST FAILED - {len(issues_found)} issues found:")
        for issue in issues_found:
            print(f"  {issue}")
        return False
    else:
        print("✅ ALL NAVIGATION TESTS PASSED!")
        print("  - All navigation links are present and consistent")
        print("  - All page titles are properly configured")
        print("  - All breadcrumb containers exist")
        print("  - Navigation.js supports all pages")
        return True

if __name__ == "__main__":
    success = test_navigation_consistency()
    exit(0 if success else 1)