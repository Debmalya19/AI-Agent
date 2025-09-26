import os
import sys
import unittest
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from admin_backend.app import create_app
from admin_backend.models import db, User


class BasicTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        
        # Create test admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            full_name='Admin User',
            is_admin=True,
            password=generate_password_hash('password'),
            created_at=datetime.utcnow()
        )

        # Create test regular user
        user = User(
            username='user',
            email='user@example.com',
            full_name='Regular User',
            is_admin=False,
            password=generate_password_hash('password'),
            created_at=datetime.utcnow()
        )
        
        db.session.add(admin)
        db.session.add(user)
        db.session.commit()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_app_exists(self):
        self.assertIsNotNone(self.app)
    
    def test_app_is_testing(self):
        self.assertTrue(self.app.config['TESTING'])
    
    def test_health_check(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'ok')
    
    def test_login(self):
        # Test valid login
        response = self.client.post('/api/auth/login', json={
            'email': 'admin@example.com',
            'password': 'password'
        })
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIn('token', json_data)
        self.assertIn('user', json_data)
        self.assertEqual(json_data['user']['email'], 'admin@example.com')
        
        # Test invalid login
        response = self.client.post('/api/auth/login', json={
            'email': 'admin@example.com',
            'password': 'wrong_password'
        })
        self.assertEqual(response.status_code, 401)
    
    def test_protected_route(self):
        # Login to get token
        response = self.client.post('/api/auth/login', json={
            'email': 'admin@example.com',
            'password': 'password'
        })
        token = response.get_json()['token']

        # Access protected route with token
        response = self.client.get('/api/auth/me', headers={
            'Authorization': f'Bearer {token}'
        })
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIn('user', json_data)
        self.assertEqual(json_data['user']['email'], 'admin@example.com')

        # Access protected route without token
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main()