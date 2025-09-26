#!/usr/bin/env python3
"""Create a test admin user for authentication testing"""

import os
import sys
from sqlalchemy.orm import Session

# Set environment variables
os.environ['JWT_SECRET_KEY'] = 'ai_agent_jwt_secret_key_2024_production_change_this_in_real_deployment_32chars_minimum'
os.environ['DATABASE_URL'] = 'postgresql://postgres:password@localhost:5432/ai_agent'

def create_test_admin():
    """Create a test admin user"""
    try:
        from backend.database import get_db, SessionLocal
        from backend.unified_models import UnifiedUser, UserRole
        from backend.unified_auth import auth_service
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Check if admin user already exists
            existing_admin = db.query(UnifiedUser).filter(
                UnifiedUser.username == 'admin'
            ).first()
            
            if existing_admin:
                print(f'Admin user already exists: {existing_admin.username} ({existing_admin.email})')
                return existing_admin
            
            # Create new admin user
            admin_user = UnifiedUser(
                user_id='admin_001',
                username='admin',
                email='admin@example.com',
                full_name='Admin User',
                password_hash=auth_service.hash_password('admin123'),
                role=UserRole.AGENT,
                is_admin=True,
                is_active=True
            )
            
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            print(f'✅ Created admin user: {admin_user.username} ({admin_user.email})')
            print(f'   Password: admin123')
            print(f'   Role: {admin_user.role.value}')
            print(f'   Is Admin: {admin_user.is_admin}')
            
            return admin_user
            
        finally:
            db.close()
            
    except Exception as e:
        print(f'Error creating admin user: {e}')
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    create_test_admin()