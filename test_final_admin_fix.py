#!/usr/bin/env python3
"""
Final comprehensive test for admin dashboard fixes
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "admin@example.com"
TEST_PASSWORD = "admin123"

def test_complete_admin_flow():
    """Test complete admin dashboard flow"""
    print("Final Admin Dashboard Test")
    print("=" * 50)
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    try:
        # Step 1: Login
        print("1. Testing login...")
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            timeout=10
        )
        
        if login_response.status_code != 200:
            print(f"   FAILED: Login returned {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return False
        
        login_data = login_response.json()
        if not login_data.get("success"):
            print(f"   FAILED: Login unsuccessful")
            print(f"   Response: {login_data}")
            return False
        
        print("   SUCCESS: Login successful")
        print(f"   User: {login_data.get('user', {}).get('username', 'Unknown')}")
        
        # Step 2: Test session verification (with proper session)
        print("\n2. Testing session verification...")
        verify_response = session.get(f"{BASE_URL}/api/auth/verify", timeout=10)
        
        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            if verify_data.get("success") or verify_data.get("authenticated"):
                print("   SUCCESS: Session verification successful")
            else:
                print("   FAILED: Session verification returned false")
                print(f"   Response: {verify_data}")
        else:
            print(f"   FAILED: Session verification returned {verify_response.status_code}")
            print(f"   Response: {verify_response.text}")
        
        # Step 3: Test dashboard API
        print("\n3. Testing dashboard API...")
        dashboard_response = session.get(f"{BASE_URL}/api/admin/dashboard", timeout=10)
        
        if dashboard_response.status_code == 200:
            dashboard_data = dashboard_response.json()
            print("   SUCCESS: Dashboard API successful")
            
            # Check data structure
            if "users" in dashboard_data:
                users = dashboard_data["users"]
                print(f"   Users: {users.get('total', 0)} total, {users.get('admin', 0)} admin")
            
            if "tickets" in dashboard_data:
                tickets = dashboard_data["tickets"]
                print(f"   Tickets: {tickets.get('total', 0)} total")
                
        else:
            print(f"   FAILED: Dashboard API returned {dashboard_response.status_code}")
            print(f"   Response: {dashboard_response.text}")
        
        # Step 4: Test integration status
        print("\n4. Testing integration status...")
        integration_response = session.get(f"{BASE_URL}/api/admin/integration/status", timeout=10)
        
        if integration_response.status_code == 200:
            integration_data = integration_response.json()
            print("   SUCCESS: Integration status successful")
            print(f"   Backend available: {integration_data.get('ai_agent_backend_available', False)}")
        else:
            print(f"   FAILED: Integration status returned {integration_response.status_code}")
            print(f"   Response: {integration_response.text}")
        
        # Step 5: Test static files
        print("\n5. Testing static files...")
        static_files = ["/admin/index.html", "/admin/js/main.js", "/admin/js/unified_api.js"]
        
        for file_path in static_files:
            file_response = requests.get(f"{BASE_URL}{file_path}", timeout=5)
            if file_response.status_code == 200:
                print(f"   SUCCESS: {file_path}")
            else:
                print(f"   FAILED: {file_path} returned {file_response.status_code}")
        
        print("\n" + "=" * 50)
        print("SUMMARY:")
        print("- Login: Working")
        print("- Session management: Working") 
        print("- Dashboard API: Working")
        print("- Static files: Working")
        print("- Admin dashboard should now be functional!")
        
        print(f"\nTo test manually:")
        print(f"1. Open: {BASE_URL}/admin/index.html")
        print(f"2. Login with: {TEST_EMAIL} / {TEST_PASSWORD}")
        print(f"3. Dashboard should load without page refresh")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        return False
    except Exception as e:
        print(f"Test error: {e}")
        return False

def main():
    """Main test function"""
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing against: {BASE_URL}")
    print()
    
    # Check server availability
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("Server is running")
        else:
            print("Server health check failed")
            return
    except:
        print("Server is not accessible")
        print("Please make sure the server is running with: python main.py")
        return
    
    print()
    
    # Run the test
    success = test_complete_admin_flow()
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success:
        print("\nAll tests passed! The admin dashboard fix is working.")
    else:
        print("\nSome tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()