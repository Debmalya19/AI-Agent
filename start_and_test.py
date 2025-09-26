#!/usr/bin/env python3
"""Start server and test authentication"""

import os
import sys
import subprocess
import time
import requests
import signal
import threading

# Set environment variables
os.environ['JWT_SECRET_KEY'] = 'ai_agent_jwt_secret_key_2024_production_change_this_in_real_deployment_32chars_minimum'

def start_server():
    """Start the server in a subprocess"""
    try:
        print("🚀 Starting server...")
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Wait for server to start
        print("⏳ Waiting for server to start...")
        time.sleep(5)
        
        # Test if server is running
        try:
            response = requests.get("http://127.0.0.1:8000/health", timeout=5)
            if response.status_code == 200:
                print("✅ Server started successfully!")
                return process
        except:
            pass
            
        # Check if server is on port 8080 instead
        try:
            response = requests.get("http://127.0.0.1:8080/health", timeout=5)
            if response.status_code == 200:
                print("✅ Server started on port 8080!")
                return process
        except:
            pass
            
        print("❌ Server failed to start or is not responding")
        process.terminate()
        return None
        
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return None

def test_authentication(base_url="http://127.0.0.1:8000"):
    """Test authentication flow"""
    print(f"\n🔐 Testing authentication on {base_url}...")
    
    # Test login
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
        
        print(f"Login status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            result = login_response.json()
            token = result.get('access_token')
            
            if token:
                print(f"✅ Login successful, token: {token[:30]}...")
                
                # Test verify endpoint
                headers = {'Authorization': f'Bearer {token}'}
                verify_response = requests.get(
                    f"{base_url}/api/auth/verify",
                    headers=headers,
                    timeout=5
                )
                
                print(f"Verify status: {verify_response.status_code}")
                if verify_response.status_code == 200:
                    print("✅ Authentication working correctly!")
                    return True
                else:
                    print(f"❌ Verify failed: {verify_response.text}")
            else:
                print("❌ No token in response")
        else:
            print(f"❌ Login failed: {login_response.text}")
            
    except Exception as e:
        print(f"❌ Authentication test error: {e}")
    
    return False

def main():
    """Main function"""
    print("🔧 JWT Authentication Fix Test")
    print("=" * 40)
    
    # Start server
    server_process = start_server()
    if not server_process:
        return
    
    try:
        # Test on both possible ports
        success = False
        for port in [8000, 8080]:
            base_url = f"http://127.0.0.1:{port}"
            try:
                requests.get(f"{base_url}/health", timeout=2)
                success = test_authentication(base_url)
                if success:
                    break
            except:
                continue
        
        if success:
            print("\n✅ JWT authentication is working correctly!")
            print("The original error was likely due to malformed tokens from the frontend.")
            print("Make sure the frontend properly stores and sends JWT tokens.")
        else:
            print("\n❌ Authentication test failed")
            
    finally:
        # Clean up
        print("\n🛑 Stopping server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    main()