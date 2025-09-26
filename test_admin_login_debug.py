#!/usr/bin/env python3
"""
Test script to debug admin login functionality
"""

import requests
import json

def test_admin_login():
    """Test admin login functionality"""
    base_url = "http://localhost:8000"
    
    # Test credentials
    login_data = {
        "email": "admin1@example.com",
        "password": "password123"  # Assuming this is the password used during registration
    }
    
    print("Testing admin login...")
    print(f"URL: {base_url}/api/auth/login")
    print(f"Data: {login_data}")
    
    try:
        # Test login
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Data: {json.dumps(data, indent=2)}")
            
            if data.get('success'):
                print("✅ Login successful!")
                token = data.get('token')
                if token:
                    print(f"Token received: {token[:20]}...")
                    
                    # Test session verification
                    print("\nTesting session verification...")
                    verify_response = requests.get(
                        f"{base_url}/api/auth/verify",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        }
                    )
                    
                    print(f"Verify Status: {verify_response.status_code}")
                    if verify_response.status_code == 200:
                        verify_data = verify_response.json()
                        print(f"Verify Data: {json.dumps(verify_data, indent=2)}")
                        print("✅ Session verification successful!")
                    else:
                        print("❌ Session verification failed!")
                        print(f"Error: {verify_response.text}")
                else:
                    print("❌ No token in response!")
            else:
                print("❌ Login failed!")
                print(f"Error: {data.get('message', 'Unknown error')}")
        else:
            print("❌ HTTP Error!")
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed! Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_admin_login()