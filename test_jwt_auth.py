#!/usr/bin/env python3
"""Test JWT authentication functionality"""

import os
import sys

# Set environment variables
os.environ['JWT_SECRET_KEY'] = 'ai_agent_jwt_secret_key_2024_production_change_this_in_real_deployment_32chars_minimum'
os.environ['DATABASE_URL'] = 'sqlite:///test_auth.db'

try:
    from backend.unified_auth import auth_service
    print('✓ Auth service initialized successfully')
    print(f'JWT Secret length: {len(auth_service.jwt_secret)}')
    print(f'JWT Algorithm: {auth_service.jwt_algorithm}')

    # Create a test user object
    from backend.unified_models import UnifiedUser, UserRole
    test_user = UnifiedUser(
        user_id='test_user_123',
        username='test_user',
        email='test@example.com',
        full_name='Test User',
        role=UserRole.CUSTOMER
    )
    
    # Test token generation
    test_token = auth_service.create_jwt_token(test_user)
    print(f'Generated token: {test_token[:50]}...')
    print(f'Token segments: {len(test_token.split("."))}')

    # Test token verification
    payload = auth_service.verify_jwt_token(test_token)
    print(f'Token verification result: {payload}')
    
    if payload:
        print('✓ JWT authentication is working correctly')
    else:
        print('✗ JWT token verification failed')
        
except Exception as e:
    print(f'✗ Error testing JWT auth: {e}')
    import traceback
    traceback.print_exc()