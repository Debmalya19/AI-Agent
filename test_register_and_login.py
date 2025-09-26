#!/usr/bin/env python3
"""
Test script to register a new admin user and then login
"""

import requests
import json
import time

def test_register_and_login():
    """Test admin registration and login"""
    base_url = "http://localhost:8000"
    
    # Generate unique credentials
    timestamp = str(int(time.time()))
    register_data = {
        "username": f"testuser{timestamp}",
        "email": f"testuser{timestamp}@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    
    print("Testing admin registration and login...")
    print(f"Registration data: {register_data}")
    
    try:
        # Test registration
        print("\n1. Testing registration...")
        register_response = requests.post(
            f"{base_url}/api/auth/register",
            json=register_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Registration Status: {register_response.status_code}")
        
        if register_response.status_code == 200:
            register_result = register_response.json()
            print(f"Registration Response: {json.dumps(register_result, indent=2)}")
            
            if register_result.get('success'):
                print("✅ Registration successful!")
                
                # Test login with the same credentials
                print("\n2. Testing login...")
                login_data = {
                    "email": register_data["email"],
                    "password": register_data["password"]
                }
                
                login_response = requests.post(
                    f"{base_url}/api/auth/login",
                    json=login_data,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"Login Status: {login_response.status_code}")
                
                if login_response.status_code == 200:
                    login_result = login_response.json()
                    print(f"Login Response: {json.dumps(login_result, indent=2)}")
                    
                    if login_result.get('success'):
                        print("✅ Login successful!")
                        token = login_result.get('token')
                        print(f"Token field exists: {'token' in login_result}")
                        print(f"Token value: {token}")
                        if token:
                            print(f"Token received: {token[:20]}...")
                            
                            # Test session verification
                            print("\n3. Testing session verification...")
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
                                print("\n🎉 All tests passed! Admin authentication is working correctly.")
                            else:
                                print("❌ Session verification failed!")
                                print(f"Error: {verify_response.text}")
                        else:
                            print("❌ No token in login response!")
                    else:
                        print("❌ Login failed!")
                        print(f"Error: {login_result.get('message', 'Unknown error')}")
                else:
                    print("❌ Login HTTP Error!")
                    print(f"Error: {login_response.text}")
            else:
                print("❌ Registration failed!")
                print(f"Error: {register_result.get('message', 'Unknown error')}")
        else:
            print("❌ Registration HTTP Error!")
            print(f"Error: {register_response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed! Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_register_and_login()