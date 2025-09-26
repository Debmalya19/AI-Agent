#!/usr/bin/env python3
"""
Test script to verify admin login and session fixes
"""

import requests
import json
import sys
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "admin@example.com"  # Using existing admin user
TEST_PASSWORD = "admin123"

def test_admin_login():
    """Test admin login functionality"""
    print("🔐 Testing Admin Login Fix")
    print("=" * 50)
    
    # Test 1: Login API
    print("1. Testing login API...")
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=login_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("   ✅ Login successful")
                print(f"   📝 User: {data.get('user', {}).get('username', 'Unknown')}")
                print(f"   🔑 Token received: {'Yes' if data.get('token') else 'No'}")
                
                # Store session for next tests
                session_token = data.get("token")
                cookies = response.cookies
                
                # Test 2: Session verification
                print("\n2. Testing session verification...")
                
                # Create a session to maintain cookies
                session = requests.Session()
                
                # Set cookies from login response
                for cookie in response.cookies:
                    session.cookies.set(cookie.name, cookie.value)
                
                # Also try with Authorization header
                headers = {}
                if session_token:
                    headers["Authorization"] = f"Bearer {session_token}"
                
                verify_response = session.get(
                    f"{BASE_URL}/api/auth/verify",
                    headers=headers,
                    timeout=10
                )
                
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    if verify_data.get("success"):
                        print("   ✅ Session verification successful")
                        print(f"   👤 Verified user: {verify_data.get('user', {}).get('username', 'Unknown')}")
                    else:
                        print("   ❌ Session verification failed")
                        print(f"   📄 Response: {verify_data}")
                else:
                    print(f"   ❌ Session verification failed with status {verify_response.status_code}")
                    print(f"   📄 Response: {verify_response.text}")
                
                # Test 3: Dashboard API
                print("\n3. Testing dashboard API...")
                dashboard_response = session.get(
                    f"{BASE_URL}/api/admin/dashboard",
                    headers=headers,
                    timeout=10
                )
                
                if dashboard_response.status_code == 200:
                    dashboard_data = dashboard_response.json()
                    # Check if it has the expected structure (either success field or direct data)
                    if dashboard_data.get("success") or "users" in dashboard_data:
                        print("   ✅ Dashboard API successful")
                        # Handle both response formats
                        if "stats" in dashboard_data:
                            stats = dashboard_data["stats"]
                            print(f"   📊 Total tickets: {stats.get('tickets', {}).get('total', 0)}")
                            print(f"   👥 Total users: {stats.get('users', {}).get('total', 0)}")
                        else:
                            # Direct format
                            print(f"   📊 Total tickets: {dashboard_data.get('tickets', {}).get('total', 0)}")
                            print(f"   👥 Total users: {dashboard_data.get('users', {}).get('total', 0)}")
                    else:
                        print("   ❌ Dashboard API failed")
                        print(f"   📄 Response: {dashboard_data}")
                else:
                    print(f"   ❌ Dashboard API failed with status {dashboard_response.status_code}")
                    print(f"   📄 Response: {dashboard_response.text}")
                
                # Test 4: Integration status
                print("\n4. Testing integration status...")
                integration_response = session.get(
                    f"{BASE_URL}/api/admin/integration/status",
                    headers=headers,
                    timeout=10
                )
                
                if integration_response.status_code == 200:
                    integration_data = integration_response.json()
                    if integration_data.get("success"):
                        print("   ✅ Integration status successful")
                        print(f"   🔗 Backend available: {integration_data.get('ai_agent_backend_available', False)}")
                    else:
                        print("   ❌ Integration status failed")
                        print(f"   📄 Response: {integration_data}")
                else:
                    print(f"   ❌ Integration status failed with status {integration_response.status_code}")
                    print(f"   📄 Response: {integration_response.text}")
                
                return True
                
            else:
                print("   ❌ Login failed")
                print(f"   📄 Response: {data}")
                return False
        else:
            print(f"   ❌ Login failed with status {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Connection error: {e}")
        return False

def test_static_files():
    """Test static file serving"""
    print("\n📁 Testing Static File Serving")
    print("=" * 50)
    
    # Test admin dashboard files
    files_to_test = [
        "/admin/index.html",
        "/admin/js/main.js",
        "/admin/js/unified_api.js"
    ]
    
    for file_path in files_to_test:
        try:
            response = requests.get(f"{BASE_URL}{file_path}", timeout=10)
            if response.status_code == 200:
                print(f"   ✅ {file_path} - OK")
            else:
                print(f"   ❌ {file_path} - Status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ {file_path} - Error: {e}")

def main():
    """Main test function"""
    print(f"🧪 Admin Dashboard Login Fix Test")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Testing against: {BASE_URL}")
    print()
    
    # Test server availability
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print("⚠️  Server responded but health check failed")
    except requests.exceptions.RequestException:
        print("❌ Server is not accessible")
        print("   Please make sure the server is running with: python main.py")
        sys.exit(1)
    
    print()
    
    # Run tests
    login_success = test_admin_login()
    test_static_files()
    
    print("\n" + "=" * 50)
    if login_success:
        print("🎉 Admin login fix appears to be working!")
        print("   You should now be able to log into the admin dashboard.")
    else:
        print("❌ Admin login fix needs more work.")
        print("   Check the server logs for more details.")
    
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()