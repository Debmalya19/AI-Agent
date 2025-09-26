#!/usr/bin/env python3
"""
Test script to verify admin dashboard fixes
"""

import sys
sys.path.append('.')
from main import app
from fastapi.testclient import TestClient

def test_admin_dashboard_fixes():
    client = TestClient(app)
    
    print("Testing Admin Dashboard Fixes")
    print("=" * 40)
    
    # Test the redirect endpoints
    print("\n1. Testing redirect endpoints:")
    
    response = client.get('/tickets.html', follow_redirects=False)
    print(f"   /tickets.html -> Status: {response.status_code}, Location: {response.headers.get('location', 'None')}")
    
    response = client.get('/users.html', follow_redirects=False)
    print(f"   /users.html -> Status: {response.status_code}, Location: {response.headers.get('location', 'None')}")
    
    response = client.get('/settings.html', follow_redirects=False)
    print(f"   /settings.html -> Status: {response.status_code}, Location: {response.headers.get('location', 'None')}")
    
    # Test admin dashboard access
    print("\n2. Testing admin dashboard access:")
    
    response = client.get('/admin/')
    print(f"   /admin/ -> Status: {response.status_code}")
    
    response = client.get('/admin/tickets.html')
    print(f"   /admin/tickets.html -> Status: {response.status_code}")
    
    response = client.get('/admin/users.html')
    print(f"   /admin/users.html -> Status: {response.status_code}")
    
    # Test API endpoints
    print("\n3. Testing API endpoints (without auth):")
    
    response = client.get('/api/tickets/stats')
    print(f"   /api/tickets/stats -> Status: {response.status_code}")
    
    response = client.get('/api/tickets')
    print(f"   /api/tickets -> Status: {response.status_code}")
    
    response = client.get('/api/admin/users')
    print(f"   /api/admin/users -> Status: {response.status_code}")
    
    print("\n" + "=" * 40)
    print("Test completed!")

if __name__ == "__main__":
    test_admin_dashboard_fixes()