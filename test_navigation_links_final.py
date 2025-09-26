#!/usr/bin/env python3
"""
Final comprehensive test for navigation links and routing
"""

import os
import re
from pathlib import Path

def test_navigation_links_final():
    """Final comprehensive test for navigation links and routing"""
    
    frontend_dir = Path("ai-agent/admin-dashboard/frontend")
    
    print("🔍 Final Navigation Links and Routing Test")
    print("=" * 50)
    
    # All expected files and their navigation links
    expected_files = {
        "index.html": "Dashboard",
        "tickets.html": "Support Tickets", 
        "users.html": "User Management",
        "integration.html": "AI Integration",
        "settings.html": "Settings",
        "logs.html": "System Logs"
    }
    
    # Navigation links that should exist in all files
    expected_nav_links = [
        ("/admin/index.html", "nav-dashboard", "Dashboard"),
        ("/admin/tickets.html", "nav-tickets", "Support Tickets"),
        ("/admin/users.html", "nav-users", "User Management"),
        ("/admin/integration.html", "nav-integration", "AI Integration"),
        ("/admin/settings.html", "nav-settings", "Settings"),
        ("/admin/logs.html", "nav-logs", "System Logs")
    ]
    
    issues_found = []
    
    print("📋 Testing file existence...")
    for filename, page_name in expected_files.items():
        file_path = frontend_dir / filename
        if file_path.exists():
            print(f"  ✅ {filename} exists")
        else:
            issues_found.append(f"❌ Missing file: {filename}")
    
    print("\n📋 Testing navigation link consistency...")
    for filename in expected_files.keys():
        file_path = frontend_dir / filename
        if not file_path.exists():
            continue
            
        print(f"\n  📄 {filename}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check each expected navigation link
        for href, nav_id, link_text in expected_nav_links:
            # Check if link exists with correct href and id
            link_pattern = rf'<a[^>]*href="{re.escape(href)}"[^>]*id="{re.escape(nav_id)}"[^>]*>'
            if re.search(link_pattern, content):
                print(f"    ✅ {nav_id} link found")
                
                # Check if link text is correct
                text_pattern = rf'<a[^>]*id="{re.escape(nav_id)}"[^>]*>.*?{re.escape(link_text)}.*?</a>'
                if not re.search(text_pattern, content, re.DOTALL):
                    issues_found.append(f"❌ {filename}: {nav_id} has incorrect text (expected: {link_text})")
            else:
                issues_found.append(f"❌ {filename}: Missing navigation link {nav_id}")
    
    print("\n📋 Testing navigation active states...")
    active_state_map = {
        "index.html": "nav-dashboard",
        "tickets.html": "nav-tickets",
        "users.html": "nav-users", 
        "integration.html": "nav-integration",
        "settings.html": "nav-settings",
        "logs.html": "nav-logs"
    }
    
    for filename, expected_active in active_state_map.items():
        file_path = frontend_dir / filename
        if not file_path.exists():
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the correct nav item has active class
        active_patterns = [
            rf'<a[^>]*id="{re.escape(expected_active)}"[^>]*class="active"[^>]*>',
            rf'<a[^>]*id="{re.escape(expected_active)}"[^>]*class="[^"]*active[^"]*"[^>]*>',
            rf'<a[^>]*class="active"[^>]*id="{re.escape(expected_active)}"[^>]*>',
            rf'<a[^>]*class="[^"]*active[^"]*"[^>]*id="{re.escape(expected_active)}"[^>]*>'
        ]
        
        found_active = any(re.search(pattern, content) for pattern in active_patterns)
        
        if found_active:
            print(f"  ✅ {filename}: Correct active state ({expected_active})")
        else:
            issues_found.append(f"❌ {filename}: Missing active state on {expected_active}")
    
    print("\n📋 Testing page titles...")
    for filename, expected_page_name in expected_files.items():
        file_path = frontend_dir / filename
        if not file_path.exists():
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract page title
        title_match = re.search(r'<title>([^<]+)</title>', content)
        if title_match:
            title = title_match.group(1)
            if expected_page_name in title or "Admin Dashboard" in title:
                print(f"  ✅ {filename}: Good page title - '{title}'")
            else:
                issues_found.append(f"❌ {filename}: Unexpected page title - '{title}'")
        else:
            issues_found.append(f"❌ {filename}: No page title found")
    
    print("\n📋 Testing navigation.js integration...")
    nav_js_path = frontend_dir / "js" / "navigation.js"
    if nav_js_path.exists():
        print(f"  ✅ navigation.js exists")
        
        # Check if all pages include navigation.js
        for filename in expected_files.keys():
            file_path = frontend_dir / filename
            if not file_path.exists():
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'navigation.js' in content:
                print(f"  ✅ {filename}: Includes navigation.js")
            else:
                issues_found.append(f"❌ {filename}: Does not include navigation.js")
    else:
        issues_found.append(f"❌ navigation.js file not found")
    
    print("\n📋 Testing breadcrumb containers...")
    for filename in expected_files.keys():
        file_path = frontend_dir / filename
        if not file_path.exists():
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'class="breadcrumb"' in content:
            print(f"  ✅ {filename}: Has breadcrumb container")
        else:
            issues_found.append(f"❌ {filename}: Missing breadcrumb container")
    
    # Summary
    print("\n" + "=" * 50)
    if issues_found:
        print(f"❌ FINAL NAVIGATION TEST FAILED - {len(issues_found)} issues found:")
        for issue in issues_found:
            print(f"  {issue}")
        
        print(f"\n📋 Recommendations:")
        print(f"  1. Fix all missing navigation links")
        print(f"  2. Ensure all pages have correct active states")
        print(f"  3. Verify all files include navigation.js")
        print(f"  4. Add missing breadcrumb containers")
        return False
    else:
        print("✅ ALL FINAL NAVIGATION TESTS PASSED!")
        print("\n📋 Summary of successful tests:")
        print(f"  ✅ All {len(expected_files)} pages exist")
        print(f"  ✅ All navigation links are present and consistent")
        print(f"  ✅ All active states are correctly set")
        print(f"  ✅ All page titles are appropriate")
        print(f"  ✅ All pages include navigation.js")
        print(f"  ✅ All pages have breadcrumb containers")
        print(f"\n🎉 Navigation system is fully functional!")
        return True

if __name__ == "__main__":
    success = test_navigation_links_final()
    exit(0 if success else 1)