#!/usr/bin/env python3
"""Test the complete login flow and JWT authentication"""

import os
import sys
import requests
import json

# Set environment variables
os.environ['JWT_SECRET_KEY'] = 'ai_agent_jwt_secret_key_2024_production_change_this_in_real_deployment_32chars_minimum'

def test_login_and_auth():
    """Test login and authentication flow"""
    base_url = "http://127.0.0.1:8000"
    
    # Test server availability
    try:
        health_response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ Server is running: {health_response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running on port 8000")
        return
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return
    
    # Test login endpoint
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        login_response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            timeout=10
        )
        print(f"Login response status: {login_response.status_code}")
        print(f"Login response: {login_response.text}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            
            # Extract JWT token
            jwt_token = login_result.get('access_token')
            if jwt_token:
                print(f"✅ JWT token received: {jwt_token[:50]}...")
                
                # Test auth verify endpoint with JWT token
                headers = {
                    'Authorization': f'Bearer {jwt_token}',
                    'Content-Type': 'application/json'
                }
                
                verify_response = requests.get(
                    f"{base_url}/api/auth/verify",
                    headers=headers,
                    timeout=5
                )
                print(f"Verify response status: {verify_response.status_code}")
                print(f"Verify response: {verify_response.text}")
                
                if verify_response.status_code == 200:
                    print("✅ Authentication is working correctly!")
                else:
                    print("❌ Authentication verification failed")
            else:
                print("❌ No JWT token in login response")
        else:
            print("❌ Login failed")
            
    except Exception as e:
        print(f"❌ Error during login test: {e}")

if __name__ == "__main__":
    test_login_and_auth()