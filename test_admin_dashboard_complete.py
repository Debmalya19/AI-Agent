#!/usr/bin/env python3
"""
Complete Admin Dashboard Authentication Test
Tests the full authentication flow for the admin dashboard
"""

import requests
import json
import time
import sys

def test_admin_dashboard_complete():
    """Test the complete admin dashboard authentication flow"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Admin Dashboard Complete Authentication Flow")
    print("=" * 60)
    
    # Test 1: Check if admin dashboard is accessible
    print("\n1. Testing admin dashboard accessibility...")
    try:
        response = requests.get(f"{base_url}/admin", timeout=10)
        if response.status_code == 200:
            print("✅ Admin dashboard is accessible")
        else:
            print(f"❌ Admin dashboard returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error accessing admin dashboard: {e}")
        return False
    
    # Test 2: Check if register page is accessible
    print("\n2. Testing admin register page accessibility...")
    try:
        response = requests.get(f"{base_url}/admin/register.html", timeout=10)
        if response.status_code == 200:
            print("✅ Admin register page is accessible")
        else:
            print(f"❌ Admin register page returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error accessing admin register page: {e}")
        return False
    
    # Test 3: Test admin registration
    print("\n3. Testing admin registration...")
    register_data = {
        'username': 'testadmin',
        'email': 'testadmin@example.com',
        'full_name': 'Test Admin User',
        'password': 'testadmin123'
    }
    
    try:
        response = requests.post(f"{base_url}/api/auth/register", 
                               json=register_data, 
                               timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Admin registration successful")
                print(f"   User ID: {data['user']['id']}")
                print(f"   Username: {data['user']['username']}")
                print(f"   Is Admin: {data['user']['is_admin']}")
                print(f"   Role: {data['user']['role']}")
            else:
                print(f"❌ Registration failed: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ Registration request failed with status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error during registration: {e}")
        return False
    
    # Test 4: Test admin login
    print("\n4. Testing admin login...")
    login_data = {
        'email': 'testadmin@example.com',
        'password': 'testadmin123'
    }
    
    try:
        response = requests.post(f"{base_url}/api/auth/login",
                               json=login_data,
                               timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Admin login successful")
                print(f"   Token received: {'Yes' if data.get('token') else 'No'}")
                print(f"   User ID: {data['user']['id']}")
                print(f"   Username: {data['user']['username']}")
                print(f"   Is Admin: {data['user']['is_admin']}")
                print(f"   Permissions: {len(data['user']['permissions'])} permissions")
                
                # Store token for further tests
                auth_token = data.get('token')
                session_cookies = response.cookies
                
            else:
                print(f"❌ Login failed: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ Login request failed with status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error during login: {e}")
        return False
    
    # Test 5: Test authenticated access to admin API
    print("\n5. Testing authenticated admin API access...")
    try:
        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
        
        # Test getting current user info
        response = requests.get(f"{base_url}/api/auth/me", 
                              headers=headers,
                              cookies=session_cookies,
                              timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('authenticated'):
                print("✅ Authenticated API access successful")
                print(f"   User: {data['user']['username']}")
                print(f"   Role: {data['user']['role']}")
            else:
                print("❌ User not authenticated according to API")
                return False
        else:
            print(f"❌ Authenticated API access failed with status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error during authenticated API access: {e}")
        return False
    
    # Test 6: Test logout
    print("\n6. Testing admin logout...")
    try:
        response = requests.post(f"{base_url}/api/auth/logout",
                               headers=headers,
                               cookies=session_cookies,
                               timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Admin logout successful")
            else:
                print(f"❌ Logout failed: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ Logout request failed with status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error during logout: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All admin dashboard authentication tests passed!")
    print("✅ Admin dashboard login and registration are working correctly")
    return True

if __name__ == "__main__":
    print("Starting admin dashboard authentication tests...")
    print("Make sure the server is running on http://localhost:8000")
    
    # Wait a moment for server to be ready
    time.sleep(2)
    
    success = test_admin_dashboard_complete()
    
    if success:
        print("\n🎯 SUMMARY: Admin dashboard authentication is fully functional!")
        print("   - Admin registration: ✅ Working")
        print("   - Admin login: ✅ Working") 
        print("   - Register page access: ✅ Working")
        print("   - Authenticated API access: ✅ Working")
        print("   - Admin logout: ✅ Working")
        sys.exit(0)
    else:
        print("\n❌ SUMMARY: Some tests failed. Please check the issues above.")
        sys.exit(1)