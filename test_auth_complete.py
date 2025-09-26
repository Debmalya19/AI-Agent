#!/usr/bin/env python3
"""
Complete authentication test script
Tests registration, login, and session management
"""

import requests
import time
import subprocess
import sys
import json

def start_server():
    """Start the FastAPI server"""
    print("🚀 Starting server...")
    proc = subprocess.Popen(
        ['python', '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8001'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(8)  # Give server time to start
    return proc

def test_registration():
    """Test user registration"""
    print("\n📝 Testing user registration...")
    
    reg_data = {
        'user_id': 'demo_user_001',
        'username': 'demouser',
        'email': 'demo@example.com',
        'full_name': 'Demo User',
        'password': 'DemoPass123'
    }
    
    try:
        response = requests.post('http://127.0.0.1:8001/register', json=reg_data, timeout=10)
        
        if response.status_code == 201:
            print("✅ Registration successful!")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return False

def test_login():
    """Test user login"""
    print("\n🔐 Testing user login...")
    
    login_data = {
        'username': 'demo_user_001',
        'password': 'DemoPass123'
    }
    
    try:
        response = requests.post('http://127.0.0.1:8001/login', data=login_data, timeout=10)
        
        if response.status_code == 200:
            print("✅ Login successful!")
            data = response.json()
            print(f"   User: {data['user']['username']} ({data['user']['email']})")
            print(f"   Token: {data['access_token'][:20]}...")
            return data['access_token']
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_authenticated_endpoint(token):
    """Test accessing authenticated endpoint"""
    print("\n🔒 Testing authenticated endpoint...")
    
    try:
        cookies = {'session_token': token}
        response = requests.get('http://127.0.0.1:8001/me', cookies=cookies, timeout=10)
        
        if response.status_code == 200:
            print("✅ Authenticated access successful!")
            data = response.json()
            print(f"   Current user: {data.get('username', 'Unknown')}")
            return True
        else:
            print(f"❌ Authenticated access failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Authenticated access error: {e}")
        return False

def test_static_files():
    """Test static file serving"""
    print("\n📁 Testing static file serving...")
    
    files_to_test = [
        '/static/login.js',
        '/static/register.js',
        '/login.html',
        '/register.html'
    ]
    
    all_good = True
    for file_path in files_to_test:
        try:
            response = requests.get(f'http://127.0.0.1:8001{file_path}', timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {file_path}")
            else:
                print(f"   ❌ {file_path} - Status: {response.status_code}")
                all_good = False
        except Exception as e:
            print(f"   ❌ {file_path} - Error: {e}")
            all_good = False
    
    return all_good

def main():
    """Main test function"""
    print("🧪 AI Agent Authentication Test Suite")
    print("=" * 50)
    
    # Start server
    server_proc = start_server()
    
    try:
        # Test static files
        static_ok = test_static_files()
        
        # Test registration
        reg_ok = test_registration()
        
        # Test login
        token = test_login()
        login_ok = token is not None
        
        # Test authenticated endpoint
        auth_ok = test_authenticated_endpoint(token) if token else False
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        print(f"   Static Files: {'✅ PASS' if static_ok else '❌ FAIL'}")
        print(f"   Registration: {'✅ PASS' if reg_ok else '❌ FAIL'}")
        print(f"   Login:        {'✅ PASS' if login_ok else '❌ FAIL'}")
        print(f"   Auth Access:  {'✅ PASS' if auth_ok else '❌ FAIL'}")
        
        if all([static_ok, reg_ok, login_ok, auth_ok]):
            print("\n🎉 All tests passed! Authentication system is working correctly.")
            print("\n💡 You can now:")
            print("   1. Open http://127.0.0.1:8001 in your browser")
            print("   2. Register a new account")
            print("   3. Login with your credentials")
            print("   4. Access the chat interface")
            return 0
        else:
            print("\n⚠️  Some tests failed. Check the errors above.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        return 1
    finally:
        print("\n🛑 Stopping server...")
        server_proc.terminate()
        server_proc.wait()

if __name__ == "__main__":
    sys.exit(main())