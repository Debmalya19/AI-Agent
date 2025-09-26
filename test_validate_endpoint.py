#!/usr/bin/env python3
"""
Quick test to verify the /api/auth/validate and /api/auth/refresh endpoints are working
"""

import requests
import time
import sys

def test_auth_endpoints():
    """Test the auth endpoints"""
    base_url = "http://localhost:8000"
    
    print("Testing authentication endpoints...")
    print("=" * 50)
    
    success_count = 0
    total_tests = 2
    
    # Test 1: validate endpoint
    try:
        print("\n1. Testing /api/auth/validate endpoint...")
        response = requests.get(f"{base_url}/api/auth/validate")
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("   ✅ SUCCESS: Endpoint exists and correctly returns 401 for unauthenticated requests")
            success_count += 1
        elif response.status_code == 404:
            print("   ❌ FAILED: Endpoint not found (404)")
        else:
            print(f"   ⚠️  UNEXPECTED: Got status code {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ FAILED: Could not connect to server. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    # Test 2: refresh endpoint
    try:
        print("\n2. Testing /api/auth/refresh endpoint...")
        response = requests.post(f"{base_url}/api/auth/refresh")
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("   ✅ SUCCESS: Endpoint exists and correctly returns 401 for unauthenticated requests")
            success_count += 1
        elif response.status_code == 404:
            print("   ❌ FAILED: Endpoint not found (404)")
        else:
            print(f"   ⚠️  UNEXPECTED: Got status code {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ FAILED: Could not connect to server. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All endpoints are working correctly!")
        return True
    else:
        print("⚠️  Some endpoints may need attention")
        return False

if __name__ == "__main__":
    success = test_auth_endpoints()
    sys.exit(0 if success else 1)