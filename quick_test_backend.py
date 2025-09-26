#!/usr/bin/env python3
import requests
import json

try:
    # Test the login endpoint
    response = requests.post(
        'http://localhost:8000/api/auth/login',
        json={'email': 'admin@example.com', 'password': 'admin123'},
        headers={'Content-Type': 'application/json'},
        timeout=5
    )
    
    print(f'Status Code: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'Success: {data.get("success", False)}')
        print(f'Has Token: {"token" in data or "access_token" in data}')
        print(f'Has User: {"user" in data}')
        print('✅ Backend authentication is working!')
    else:
        print(f'❌ Backend error: {response.text}')
        
except requests.exceptions.ConnectionError:
    print('❌ Cannot connect to backend - make sure the server is running on localhost:8000')
except Exception as e:
    print(f'❌ Test error: {e}')