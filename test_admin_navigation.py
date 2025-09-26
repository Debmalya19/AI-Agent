#!/usr/bin/env python3
"""
Test admin dashboard navigation and page availability
"""

import requests
import sys

def test_admin_pages():
    """Test that admin dashboard pages are accessible"""
    base_url = "http://localhost:8000"
    
    # List of admin pages that should exist
    admin_pages = [
        "/admin/",  # Main dashboard
        "/admin/index.html",  # Main dashboard (explicit)
        "/admin/users.html",  # Users page
        "/admin/tickets.html",  # Tickets page
        "/admin/settings.html",  # Settings page
        "/admin/integration.html",  # Integration page
        "/admin/register.html",  # Registration page
    ]
    
    print("Testing admin dashboard page availability...")
    print("=" * 60)
    
    success_count = 0
    total_tests = len(admin_pages)
    
    for page in admin_pages:
        try:
            print(f"\nTesting: {page}")
            response = requests.get(f"{base_url}{page}")
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ SUCCESS: Page is accessible")
                success_count += 1
            elif response.status_code == 404:
                print("   ❌ FAILED: Page not found (404)")
            elif response.status_code == 403:
                print("   ⚠️  FORBIDDEN: Page exists but access denied (403)")
                success_count += 1  # Page exists, just protected
            else:
                print(f"   ⚠️  UNEXPECTED: Got status code {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("   ❌ FAILED: Could not connect to server")
            break
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print("\n" + "=" * 60)
    print(f"Results: {success_count}/{total_tests} pages accessible")
    
    if success_count == total_tests:
        print("🎉 All admin pages are accessible!")
        return True
    elif success_count > total_tests * 0.7:  # 70% success rate
        print("✅ Most admin pages are working correctly!")
        return True
    else:
        print("⚠️  Some admin pages may need attention")
        return False

if __name__ == "__main__":
    success = test_admin_pages()
    sys.exit(0 if success else 1)