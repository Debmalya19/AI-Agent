#!/usr/bin/env python3
"""
Admin Dashboard Diagnostic Script

This script diagnoses common issues with the admin dashboard functionality.
"""

import os
import json
from pathlib import Path

def check_file_structure():
    """Check if all required files exist"""
    print("=" * 50)
    print("CHECKING FILE STRUCTURE")
    print("=" * 50)
    
    base_path = "admin-dashboard/frontend"
    
    required_files = {
        "HTML Pages": [
            "index.html",
            "tickets.html", 
            "users.html",
            "integration.html",
            "settings.html",
            "logs.html"
        ],
        "JavaScript Files": [
            "js/dashboard.js",
            "js/main.js",
            "js/auth.js",
            "js/navigation.js",
            "js/ui-feedback.js",
            "js/simple-auth-fix.js",
            "js/unified_api.js",
            "js/session-manager.js"
        ],
        "CSS Files": [
            "css/modern-dashboard.css"
        ]
    }
    
    issues = []
    
    for category, files in required_files.items():
        print(f"\n{category}:")
        for file_path in files:
            full_path = os.path.join(base_path, file_path)
            if os.path.exists(full_path):
                size = os.path.getsize(full_path)
                print(f"  ✅ {file_path} ({size} bytes)")
            else:
                print(f"  ❌ {file_path} - MISSING")
                issues.append(f"Missing file: {file_path}")
    
    return issues

def check_html_structure():
    """Check HTML files for common issues"""
    print("\n" + "=" * 50)
    print("CHECKING HTML STRUCTURE")
    print("=" * 50)
    
    base_path = "admin-dashboard/frontend"
    html_files = ["index.html", "tickets.html", "users.html", "integration.html", "settings.html", "logs.html"]
    
    issues = []
    
    for html_file in html_files:
        file_path = os.path.join(base_path, html_file)
        if not os.path.exists(file_path):
            continue
            
        print(f"\nChecking {html_file}:")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for common issues
            checks = {
                "DOCTYPE": content.strip().startswith('<!DOCTYPE html>'),
                "Title tag": '<title>' in content,
                "Bootstrap CSS": 'bootstrap' in content.lower(),
                "Modern CSS": 'modern-dashboard.css' in content,
                "Bootstrap JS": 'bootstrap' in content and 'script' in content.lower(),
                "Proper closing tags": content.count('<html') == content.count('</html>'),
                "No /admin/ paths": '/admin/' not in content
            }
            
            for check, passed in checks.items():
                if passed:
                    print(f"  ✅ {check}")
                else:
                    print(f"  ❌ {check}")
                    issues.append(f"{html_file}: {check} failed")
                    
        except Exception as e:
            print(f"  ❌ Error reading file: {e}")
            issues.append(f"{html_file}: Cannot read file - {e}")
    
    return issues

def check_javascript_syntax():
    """Check JavaScript files for basic syntax issues"""
    print("\n" + "=" * 50)
    print("CHECKING JAVASCRIPT FILES")
    print("=" * 50)
    
    base_path = "admin-dashboard/frontend"
    js_files = [
        "js/dashboard.js",
        "js/main.js", 
        "js/auth.js",
        "js/navigation.js",
        "js/simple-auth-fix.js"
    ]
    
    issues = []
    
    for js_file in js_files:
        file_path = os.path.join(base_path, js_file)
        if not os.path.exists(file_path):
            continue
            
        print(f"\nChecking {js_file}:")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic syntax checks
            checks = {
                "Has content": len(content.strip()) > 0,
                "No /admin/ paths": '/admin/' not in content,
                "Proper function syntax": 'function' in content or '=>' in content,
                "Event listeners": 'addEventListener' in content or 'onclick' in content,
                "No obvious syntax errors": content.count('{') == content.count('}')
            }
            
            for check, passed in checks.items():
                if passed:
                    print(f"  ✅ {check}")
                else:
                    print(f"  ❌ {check}")
                    issues.append(f"{js_file}: {check} failed")
                    
        except Exception as e:
            print(f"  ❌ Error reading file: {e}")
            issues.append(f"{js_file}: Cannot read file - {e}")
    
    return issues

def check_path_issues():
    """Check for common path issues"""
    print("\n" + "=" * 50)
    print("CHECKING PATH ISSUES")
    print("=" * 50)
    
    base_path = "admin-dashboard/frontend"
    
    issues = []
    
    # Check index.html for path issues
    index_path = os.path.join(base_path, "index.html")
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("Checking index.html paths:")
        
        # Check CSS paths
        if 'href="css/modern-dashboard.css"' in content:
            print("  ✅ CSS path is correct")
        elif '/admin/css/modern-dashboard.css' in content:
            print("  ❌ CSS path uses /admin/ prefix")
            issues.append("index.html: CSS path uses incorrect /admin/ prefix")
        else:
            print("  ⚠️ CSS path not found or unusual format")
        
        # Check JS paths
        if 'src="js/' in content:
            print("  ✅ JS paths are correct")
        elif 'src="/admin/js/' in content:
            print("  ❌ JS paths use /admin/ prefix")
            issues.append("index.html: JS paths use incorrect /admin/ prefix")
        else:
            print("  ⚠️ JS paths not found or unusual format")
        
        # Check navigation links
        if 'href="tickets.html"' in content:
            print("  ✅ Navigation links are correct")
        elif 'href="/admin/tickets.html"' in content:
            print("  ❌ Navigation links use /admin/ prefix")
            issues.append("index.html: Navigation links use incorrect /admin/ prefix")
        else:
            print("  ⚠️ Navigation links not found or unusual format")
    
    return issues

def generate_fix_recommendations(all_issues):
    """Generate recommendations to fix identified issues"""
    print("\n" + "=" * 50)
    print("FIX RECOMMENDATIONS")
    print("=" * 50)
    
    if not all_issues:
        print("🎉 No issues found! The admin dashboard should be functioning correctly.")
        return
    
    print("Issues found that may prevent the admin dashboard from functioning:")
    print()
    
    for i, issue in enumerate(all_issues, 1):
        print(f"{i}. {issue}")
    
    print("\nRecommended fixes:")
    print()
    
    # Group issues by type and provide specific fixes
    path_issues = [issue for issue in all_issues if '/admin/' in issue]
    missing_files = [issue for issue in all_issues if 'Missing file' in issue]
    html_issues = [issue for issue in all_issues if any(x in issue for x in ['DOCTYPE', 'Title', 'Bootstrap', 'Modern CSS'])]
    
    if path_issues:
        print("📁 PATH ISSUES:")
        print("   - Remove /admin/ prefixes from all file paths")
        print("   - Update navigation links to use relative paths")
        print("   - Fix CSS and JS file references")
        print()
    
    if missing_files:
        print("📄 MISSING FILES:")
        print("   - Ensure all required files are present")
        print("   - Check file permissions")
        print("   - Verify file names are correct")
        print()
    
    if html_issues:
        print("🏗️ HTML STRUCTURE:")
        print("   - Add missing DOCTYPE declarations")
        print("   - Include proper title tags")
        print("   - Ensure Bootstrap CSS/JS are included")
        print("   - Include modern-dashboard.css")
        print()
    
    print("🔧 QUICK FIX STEPS:")
    print("1. Open index.html and replace all '/admin/' paths with relative paths")
    print("2. Check that css/modern-dashboard.css exists and is accessible")
    print("3. Verify all JavaScript files are present in the js/ directory")
    print("4. Test the page by opening index.html in a web browser")
    print("5. Check browser console for any JavaScript errors")

def main():
    """Main diagnostic function"""
    print("ADMIN DASHBOARD DIAGNOSTIC TOOL")
    print("=" * 60)
    
    all_issues = []
    
    # Run all checks
    all_issues.extend(check_file_structure())
    all_issues.extend(check_html_structure())
    all_issues.extend(check_javascript_syntax())
    all_issues.extend(check_path_issues())
    
    # Generate recommendations
    generate_fix_recommendations(all_issues)
    
    # Save diagnostic report
    report = {
        "timestamp": "2025-09-19T23:30:00",
        "total_issues": len(all_issues),
        "issues": all_issues,
        "status": "PASS" if len(all_issues) == 0 else "FAIL"
    }
    
    with open("admin_diagnostic_report.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📊 Diagnostic complete. Found {len(all_issues)} issues.")
    print("📄 Report saved to: admin_diagnostic_report.json")
    
    return len(all_issues)

if __name__ == "__main__":
    exit_code = main()
    exit(0 if exit_code == 0 else 1)