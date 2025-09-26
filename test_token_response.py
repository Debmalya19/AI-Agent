#!/usr/bin/env python3
"""
Test script to check if token is in the response headers or cookies
"""

import requests
import json

def test_token_response():
    """Test if token is in response headers or cookies"""
    base_url = "http://localhost:8000"
    
    # Use the existing test user
    login_data = {
        "email": "testuser1758107530@example.com",
        "password": "testpassword123"
    }
    
    print("Testing token response...")
    
    try:
        # Test login
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Cookies: {dict(response.cookies)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response JSON keys: {list(data.keys())}")
            print(f"Response JSON: {json.dumps(data, indent=2)}")
            
            # Check if token is in cookies
            if 'session_token' in response.cookies:
                print(f"✅ Token found in cookies: {response.cookies['session_token'][:20]}...")
            else:
                print("❌ No token in cookies")
                
            # Check if token is in JSON response
            if 'token' in data:
                print(f"✅ Token found in JSON: {data['token'][:20]}...")
            elif 'session_token' in data:
                print(f"✅ Session token found in JSON: {data['session_token'][:20]}...")
            else:
                print("❌ No token in JSON response")
                
        else:
            print(f"❌ HTTP Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_token_response()