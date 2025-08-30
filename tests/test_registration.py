#!/usr/bin/env python3
"""
Test script for user registration endpoint
"""
import requests
import json

def test_registration():
    url = "http://127.0.0.1:8000/register"
    
    # Test data with unique values
    import time
    timestamp = int(time.time())
    test_user = {
        "user_id": f"testuser{timestamp}",
        "username": f"TestUser{timestamp}",
        "email": f"test{timestamp}@example.com",
        "password": "TestPass123",
        "full_name": "Test User"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("Testing user registration...")
        print(f"URL: {url}")
        print(f"Data: {json.dumps(test_user, indent=2)}")
        
        response = requests.post(url, json=test_user, headers=headers)
        
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"Response Body: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
        
        if response.status_code == 201:
            print("✅ Registration successful!")
        else:
            print(f"❌ Registration failed with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    test_registration()