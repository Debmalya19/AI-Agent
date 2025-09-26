#!/usr/bin/env python3
"""Test authentication endpoint with proper JWT token"""

import os
import sys
import requests
import json
from datetime import datetime, timezone, timedelta

# Set environment variables
os.environ['JWT_SECRET_KEY'] = 'ai_agent_jwt_secret_key_2024_production_change_this_in_real_deployment_32chars_minimum'
os.environ['DATABASE_URL'] = 'sqlite:///test_auth.db'

def test_auth_endpoint():
    """Test the auth endpoint with a valid JWT token"""
    try:
        from backend.unified_auth import auth_service
        from backend.unified_models import UnifiedUser, UserRole
        
        # Create a test user object
        test_user = UnifiedUser(
            user_id='test_user_123',
            username='test_user',
            email='test@example.com',
            full_name='Test User',
            role=UserRole.CUSTOMER
        )
        
        # Generate a valid JWT token
        jwt_token = auth_service.create_jwt_token(test_user)
        print(f'Generated JWT token: {jwt_token[:50]}...')
        
        # Test the token locally first
        payload = auth_service.verify_jwt_token(jwt_token)
        print(f'Local token verification: {payload}')
        
        # Test with the server (if running)
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get('http://127.0.0.1:8000/api/auth/verify', 
                                  headers=headers, timeout=5)
            print(f'Server response status: {response.status_code}')
            print(f'Server response: {response.text}')
        except requests.exceptions.ConnectionError:
            print('Server is not running - testing locally only')
            
        # Test with malformed token (to reproduce the original error)
        malformed_token = "invalid.token"
        malformed_payload = auth_service.verify_jwt_token(malformed_token)
        print(f'Malformed token verification: {malformed_payload}')
        
    except Exception as e:
        print(f'Error testing auth: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auth_endpoint()