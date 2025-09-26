#!/usr/bin/env python3
"""
Verify that all required admin dashboard static files exist in the filesystem
"""
import os
import sys

def verify_static_files():
    """Verify that all required static files exist"""
    base_dir = "admin-dashboard/frontend"
    
    # Required CSS files
    css_files = [
        "css/modern-dashboard.css",
        "css/admin.css", 
        "css/styles.css",
        "css/support.css"
    ]
    
    # Required JavaScript files
    js_files = [
        "js/session-manager.js",
        "js/auth-error-handler.js",
        "js/api-connectivity-checker.js",
        "js/admin-auth-service.js",
        "js/unified_api.js",
        "js/api.js",
        "js/navigation.js",
        "js/ui-feedback.js",
        "js/auth.js",
        "js/dashboard.js",
        "js/integration.js",
        "js/main.js",
        "js/simple-auth-fix.js"
    ]
    
    print("Verifying admin dashboard static files exist...")
    print("=" * 60)
    
    missing_files = []
    
    # Check CSS files
    print("\n🎨 CSS Files:")
    for css_file in css_files:
        file_path = os.path.join(base_dir, css_file)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"  ✅ {css_file:<30} ({file_size:,} bytes)")
        else:
            print(f"  ❌ {css_file:<30} MISSING")
            missing_files.append(file_path)
    
    # Check JavaScript files
    print("\n📜 JavaScript Files:")
    for js_file in js_files:
        file_path = os.path.join(base_dir, js_file)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"  ✅ {js_file:<30} ({file_size:,} bytes)")
        else:
            print(f"  ❌ {js_file:<30} MISSING")
            missing_files.append(file_path)
    
    # Check HTML files
    html_files = ["index.html", "tickets.html", "users.html", "settings.html", "integration.html", "logs.html"]
    print("\n📄 HTML Files:")
    for html_file in html_files:
        file_path = os.path.join(base_dir, html_file)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"  ✅ {html_file:<30} ({file_size:,} bytes)")
        else:
            print(f"  ❌ {html_file:<30} MISSING")
            missing_files.append(file_path)
    
    print("\n" + "=" * 60)
    
    if missing_files:
        print(f"❌ {len(missing_files)} files are missing:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print("\nPlease ensure all required files are present before starting the server.")
        return False
    else:
        print("✅ All required static files are present!")
        print("Static file serving configuration should work correctly.")
        return True

if __name__ == "__main__":
    success = verify_static_files()
    sys.exit(0 if success else 1)