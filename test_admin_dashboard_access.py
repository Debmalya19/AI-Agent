#!/usr/bin/env python3
"""
Test admin dashboard access and login flow
"""

import requests
import sys
import os
from datetime import datetime

def test_admin_dashboard_access():
    """Test accessing the admin dashboard and login flow"""
    print("🧪 Admin Dashboard Access Test")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Test server availability
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ Server is running (Status: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ Server is not accessible: {e}")
        return False
    
    # Test admin dashboard static files
    admin_files = [
        "/admin/index.html",
        "/admin/js/unified_api.js",
        "/admin/js/auth.js",
        "/admin/js/main.js"
    ]
    
    print(f"\n📁 Testing Admin Dashboard Files")
    print("-" * 30)
    
    for file_path in admin_files:
        try:
            response = requests.get(f"{base_url}{file_path}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {file_path} - OK")
            else:
                print(f"❌ {file_path} - Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {file_path} - Error: {e}")
    
    # Test login API
    print(f"\n🔐 Testing Login API")
    print("-" * 30)
    
    login_data = {
        "email": "admin@example.com",
        "password": "admin123"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            timeout=10
        )
        
        print(f"Login API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login successful!")
            print(f"   User: {data.get('user', {}).get('username', 'Unknown')}")
            print(f"   Email: {data.get('user', {}).get('email', 'Unknown')}")
            print(f"   Is Admin: {data.get('user', {}).get('is_admin', False)}")
            
            # Check for session cookie
            session_cookie = response.cookies.get('session_token')
            if session_cookie:
                print(f"   Session Cookie: {session_cookie[:20]}...")
                
                # Test session verification
                print(f"\n🔍 Testing Session Verification")
                verify_response = requests.get(
                    f"{base_url}/api/auth/verify",
                    cookies={'session_token': session_cookie},
                    timeout=5
                )
                
                if verify_response.status_code == 200:
                    print(f"✅ Session verification successful")
                    verify_data = verify_response.json()
                    print(f"   Verified User: {verify_data.get('user', {}).get('username', 'Unknown')}")
                else:
                    print(f"❌ Session verification failed: {verify_response.status_code}")
            else:
                print(f"⚠️  No session cookie received")
                
        else:
            print(f"❌ Login failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   Response: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Login API error: {e}")
    
    # Test admin dashboard routes
    print(f"\n🏠 Testing Admin Dashboard Routes")
    print("-" * 30)
    
    dashboard_routes = [
        "/admin/dashboard",
        "/admin/users",
        "/admin/integration/status"
    ]
    
    # First login to get session
    try:
        login_response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            timeout=10
        )
        
        if login_response.status_code == 200:
            session_cookie = login_response.cookies.get('session_token')
            
            for route in dashboard_routes:
                try:
                    response = requests.get(
                        f"{base_url}/api{route}",
                        cookies={'session_token': session_cookie} if session_cookie else {},
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        print(f"✅ {route} - OK")
                    else:
                        print(f"❌ {route} - Status: {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"❌ {route} - Error: {e}")
        else:
            print(f"❌ Cannot test routes - login failed")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Route testing error: {e}")
    
    return True

def main():
    """Main function"""
    print("🚀 Admin Dashboard Access Test")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = test_admin_dashboard_access()
    
    if success:
        print("\n🎉 Admin dashboard access test completed!")
        print("\nIf login is working but you can't access the dashboard:")
        print("1. Try clearing browser cache and cookies")
        print("2. Check browser console for JavaScript errors")
        print("3. Ensure you're accessing: http://localhost:8000/admin/index.html")
    else:
        print("\n❌ Admin dashboard access test failed!")
    
    print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()