#!/usr/bin/env python3
"""
Manual test script for admin dashboard login
Run this when the server is running to test the login functionality
"""

import requests
import json
import sys

def test_admin_login():
    """Test admin login functionality"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Admin Dashboard Login Functionality")
    print("=" * 50)
    
    # Test data
    test_credentials = {
        "email": "admin@example.com",
        "password": "admin123"
    }
    
    # Test 1: Check if server is running
    print("1. Testing server connectivity...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"   ✅ Server is running (Status: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Server is not running: {e}")
        print("   Please start the server with: python ai-agent/main.py")
        return False
    
    # Test 2: Test CORS preflight
    print("2. Testing CORS configuration...")
    try:
        response = requests.options(
            f"{base_url}/api/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            },
            timeout=5
        )
        
        cors_headers = response.headers
        if "access-control-allow-credentials" in cors_headers:
            print(f"   ✅ CORS configured correctly")
        else:
            print(f"   ⚠️ CORS might need adjustment")
    except Exception as e:
        print(f"   ❌ CORS test failed: {e}")
    
    # Test 3: Test main auth endpoint
    print("3. Testing main authentication endpoint...")
    try:
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=test_credentials,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"   ✅ Main auth endpoint working")
                print(f"   Token received: {'Yes' if data.get('token') else 'No'}")
            else:
                print(f"   ⚠️ Login failed: {data.get('message', 'Unknown error')}")
        elif response.status_code == 401:
            print(f"   ⚠️ Invalid credentials (expected for test)")
        else:
            print(f"   ❌ Unexpected response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Main auth test failed: {e}")
    
    # Test 4: Test admin auth endpoint
    print("4. Testing admin authentication endpoint...")
    try:
        response = requests.post(
            f"{base_url}/admin/auth/login",
            json=test_credentials,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"   ✅ Admin auth endpoint working")
                print(f"   Token received: {'Yes' if data.get('token') else 'No'}")
            else:
                print(f"   ⚠️ Admin login failed: {data.get('message', 'Unknown error')}")
        elif response.status_code == 401:
            print(f"   ⚠️ Invalid credentials (expected for test)")
        elif response.status_code == 403:
            print(f"   ⚠️ Admin privileges required (expected for test)")
        else:
            print(f"   ❌ Unexpected response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Admin auth test failed: {e}")
    
    # Test 5: Test admin compatibility endpoint
    print("5. Testing admin compatibility endpoint...")
    try:
        response = requests.post(
            f"{base_url}/admin/auth/login",
            json=test_credentials,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code in [200, 401, 403]:
            print(f"   ✅ Admin compatibility endpoint responding")
        else:
            print(f"   ❌ Unexpected response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Admin compatibility test failed: {e}")
    
    # Test 6: Test request validation
    print("6. Testing request validation...")
    try:
        # Test with malicious input
        malicious_data = {
            "email": "<script>alert('xss')</script>@example.com",
            "password": "test"
        }
        
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=malicious_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code < 500:
            print(f"   ✅ Request validation working (no server crash)")
        else:
            print(f"   ❌ Server error on malicious input: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Request validation test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 MANUAL TEST SUMMARY")
    print("=" * 50)
    print("If you see mostly ✅ marks above, the API communication fixes are working!")
    print("If you see ⚠️ marks, that's expected for invalid test credentials.")
    print("If you see ❌ marks, there might be issues that need attention.")
    print("\nTo test with real credentials:")
    print("1. Create an admin user in the database")
    print("2. Update the test_credentials in this script")
    print("3. Run this test again")
    
    return True

if __name__ == "__main__":
    test_admin_login()