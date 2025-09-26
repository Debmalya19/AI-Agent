#!/usr/bin/env python3
"""
Debug Session Authentication

Debug script to check session authentication issues.
"""

import sys
import os
import logging

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Depends, Cookie
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_session_authentication():
    """Debug session authentication"""
    logger.info("🔍 Debugging session authentication...")
    
    try:
        # Initialize database and auth service
        from backend.database import get_db, init_db
        from backend.unified_auth import auth_service, get_current_user_flexible
        from backend.unified_models import UnifiedUser, UserRole
        
        init_db()
        
        # Create test user
        db = next(get_db())
        
        try:
            # Create admin user
            admin_password = "debug_admin_password"
            
            existing_admin = db.query(UnifiedUser).filter(
                UnifiedUser.user_id == "debug_admin_user"
            ).first()
            
            if existing_admin:
                admin_user = existing_admin
                logger.info("Using existing debug admin user")
            else:
                admin_user = UnifiedUser(
                    user_id="debug_admin_user",
                    username="debug_admin",
                    email="debug_admin@example.com",
                    full_name="Debug Admin User",
                    password_hash=auth_service.hash_password(admin_password),
                    role=UserRole.ADMIN,
                    is_admin=True,
                    is_active=True
                )
                
                db.add(admin_user)
                db.commit()
                db.refresh(admin_user)
                logger.info("Created new debug admin user")
            
            # Create session token
            session_token = auth_service.create_user_session(admin_user, db)
            logger.info(f"Created session token: {session_token[:10]}...")
            
            # Test session validation directly
            authenticated_user = auth_service.get_user_from_session(session_token, db)
            
            if authenticated_user:
                logger.info("✅ Session token validation works directly")
                logger.info(f"  User ID: {authenticated_user.user_id}")
                logger.info(f"  Username: {authenticated_user.username}")
                logger.info(f"  Is Admin: {authenticated_user.is_admin}")
                logger.info(f"  Role: {authenticated_user.role}")
                logger.info(f"  Permissions: {len(authenticated_user.permissions)}")
            else:
                logger.error("❌ Session token validation failed directly")
                return False
            
            # Test with FastAPI dependency
            app = FastAPI()
            
            @app.get("/test-auth")
            async def test_auth_endpoint(
                current_user = Depends(get_current_user_flexible)
            ):
                return {
                    "authenticated": True,
                    "user_id": current_user.user_id,
                    "username": current_user.username,
                    "is_admin": current_user.is_admin
                }
            
            client = TestClient(app)
            
            # Test with session token in cookie
            headers = {"Cookie": f"session_token={session_token}"}
            response = client.get("/test-auth", headers=headers)
            
            logger.info(f"FastAPI dependency test response: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("✅ FastAPI dependency authentication works")
                response_data = response.json()
                logger.info(f"  Response: {response_data}")
                return True
            else:
                logger.error("❌ FastAPI dependency authentication failed")
                logger.error(f"  Response: {response.text}")
                
                # Test with different cookie format
                response2 = client.get("/test-auth", cookies={"session_token": session_token})
                logger.info(f"Alternative cookie format response: {response2.status_code}")
                
                if response2.status_code == 200:
                    logger.info("✅ Alternative cookie format works")
                    return True
                else:
                    logger.error(f"❌ Alternative cookie format also failed: {response2.text}")
                
                return False
        
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error during session authentication debug: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    logger.info("🚀 Debugging Session Authentication...")
    
    success = debug_session_authentication()
    
    if success:
        logger.info("🎉 Session authentication is working correctly!")
        return 0
    else:
        logger.error("❌ Session authentication has issues!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)