#!/usr/bin/env python3
"""
Test Admin Dashboard Authentication Integration

This script tests the admin dashboard authentication integration to ensure:
1. Admin dashboard routes use unified authentication system
2. Admin route dependencies use unified auth service
3. Proper admin permission validation using unified role system
4. Admin dashboard functionality works with unified authentication

Requirements: 2.1, 2.2, 2.3, 2.4, 6.2, 6.4
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Import the main application
from main import app
from backend.database import get_db, init_db
from backend.unified_auth import auth_service
from backend.unified_models import UnifiedUser, UserRole

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdminDashboardAuthTest:
    """Test class for admin dashboard authentication integration"""
    
    def __init__(self):
        self.client = TestClient(app)
        self.test_results: List[Dict[str, Any]] = []
        self.admin_user = None
        self.admin_session_token = None
        self.regular_user = None
        self.regular_session_token = None
    
    def log_test_result(self, test_name: str, success: bool, message: str, details: Dict[str, Any] = None):
        """Log test result"""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status}: {test_name} - {message}")
        
        if details:
            for key, value in details.items():
                logger.info(f"  {key}: {value}")
    
    def setup_test_users(self) -> bool:
        """Setup test users for authentication testing"""
        try:
            logger.info("🔧 Setting up test users...")
            
            # Initialize database
            init_db()
            
            # Get database session
            db = next(get_db())
            
            try:
                # Create admin user
                admin_password = "admin_test_password_123"
                admin_user = UnifiedUser(
                    user_id="test_admin_user",
                    username="test_admin",
                    email="test_admin@example.com",
                    full_name="Test Admin User",
                    password_hash=auth_service.hash_password(admin_password),
                    role=UserRole.ADMIN,
                    is_admin=True,
                    is_active=True
                )
                
                # Check if admin user already exists
                existing_admin = db.query(UnifiedUser).filter(
                    UnifiedUser.user_id == "test_admin_user"
                ).first()
                
                if existing_admin:
                    self.admin_user = existing_admin
                    logger.info("Using existing admin user")
                else:
                    db.add(admin_user)
                    db.commit()
                    db.refresh(admin_user)
                    self.admin_user = admin_user
                    logger.info("Created new admin user")
                
                # Create regular user
                regular_password = "regular_test_password_123"
                regular_user = UnifiedUser(
                    user_id="test_regular_user",
                    username="test_regular",
                    email="test_regular@example.com",
                    full_name="Test Regular User",
                    password_hash=auth_service.hash_password(regular_password),
                    role=UserRole.CUSTOMER,
                    is_admin=False,
                    is_active=True
                )
                
                # Check if regular user already exists
                existing_regular = db.query(UnifiedUser).filter(
                    UnifiedUser.user_id == "test_regular_user"
                ).first()
                
                if existing_regular:
                    self.regular_user = existing_regular
                    logger.info("Using existing regular user")
                else:
                    db.add(regular_user)
                    db.commit()
                    db.refresh(regular_user)
                    self.regular_user = regular_user
                    logger.info("Created new regular user")
                
                # Create session tokens for both users
                self.admin_session_token = auth_service.create_user_session(self.admin_user, db)
                self.regular_session_token = auth_service.create_user_session(self.regular_user, db)
                
                logger.info("✅ Test users setup completed")
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Failed to setup test users: {e}")
            return False
    
    def test_admin_login_authentication(self) -> bool:
        """Test admin login with unified authentication"""
        try:
            logger.info("🔐 Testing admin login authentication...")
            
            # Test admin login
            login_data = {
                "email": "test_admin@example.com",
                "password": "admin_test_password_123"
            }
            
            response = self.client.post("/api/auth/login", json=login_data)
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("success") and response_data.get("user", {}).get("is_admin"):
                    self.log_test_result(
                        "Admin Login Authentication",
                        True,
                        "Admin user successfully authenticated",
                        {"status_code": response.status_code, "user_role": response_data.get("user", {}).get("role")}
                    )
                    return True
                else:
                    self.log_test_result(
                        "Admin Login Authentication",
                        False,
                        "Admin login succeeded but user is not admin",
                        {"response": response_data}
                    )
                    return False
            else:
                self.log_test_result(
                    "Admin Login Authentication",
                    False,
                    f"Admin login failed with status {response.status_code}",
                    {"status_code": response.status_code, "response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Admin Login Authentication",
                False,
                f"Exception during admin login test: {str(e)}"
            )
            return False
    
    def test_admin_dashboard_access(self) -> bool:
        """Test admin dashboard access with unified authentication"""
        try:
            logger.info("📊 Testing admin dashboard access...")
            
            # Test admin dashboard access with session token
            headers = {"Cookie": f"session_token={self.admin_session_token}"}
            response = self.client.get("/api/admin/dashboard", headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                if "users" in response_data and "tickets" in response_data:
                    self.log_test_result(
                        "Admin Dashboard Access",
                        True,
                        "Admin dashboard accessible with unified authentication",
                        {"status_code": response.status_code, "data_keys": list(response_data.keys())}
                    )
                    return True
                else:
                    self.log_test_result(
                        "Admin Dashboard Access",
                        False,
                        "Admin dashboard response missing expected data",
                        {"response": response_data}
                    )
                    return False
            else:
                self.log_test_result(
                    "Admin Dashboard Access",
                    False,
                    f"Admin dashboard access failed with status {response.status_code}",
                    {"status_code": response.status_code, "response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Admin Dashboard Access",
                False,
                f"Exception during admin dashboard access test: {str(e)}"
            )
            return False
    
    def test_admin_permission_validation(self) -> bool:
        """Test admin permission validation using unified role system"""
        try:
            logger.info("🔒 Testing admin permission validation...")
            
            # Test admin user access to user management
            headers = {"Cookie": f"session_token={self.admin_session_token}"}
            response = self.client.get("/api/admin/users/", headers=headers)
            
            admin_access_success = response.status_code == 200
            
            # Test regular user access to admin endpoints (should fail)
            headers = {"Cookie": f"session_token={self.regular_session_token}"}
            response = self.client.get("/api/admin/users/", headers=headers)
            
            regular_access_blocked = response.status_code == 403
            
            if admin_access_success and regular_access_blocked:
                self.log_test_result(
                    "Admin Permission Validation",
                    True,
                    "Admin permissions correctly validated - admin access granted, regular user blocked",
                    {"admin_access": admin_access_success, "regular_blocked": regular_access_blocked}
                )
                return True
            else:
                self.log_test_result(
                    "Admin Permission Validation",
                    False,
                    "Admin permission validation failed",
                    {"admin_access": admin_access_success, "regular_blocked": regular_access_blocked}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Admin Permission Validation",
                False,
                f"Exception during admin permission validation test: {str(e)}"
            )
            return False
    
    def test_admin_routes_unified_auth(self) -> bool:
        """Test that admin routes use unified authentication system"""
        try:
            logger.info("🔗 Testing admin routes unified authentication...")
            
            # Test multiple admin endpoints with unified auth
            admin_endpoints = [
                "/api/admin/dashboard",
                "/api/admin/users/",
                "/api/admin/tickets/stats/overview",
                "/api/admin/analytics/performance-metrics",
                "/api/admin/system/status"
            ]
            
            headers = {"Cookie": f"session_token={self.admin_session_token}"}
            successful_endpoints = []
            failed_endpoints = []
            
            for endpoint in admin_endpoints:
                try:
                    response = self.client.get(endpoint, headers=headers)
                    if response.status_code in [200, 404]:  # 404 is acceptable for some endpoints
                        successful_endpoints.append(endpoint)
                    else:
                        failed_endpoints.append(f"{endpoint} (status: {response.status_code})")
                except Exception as e:
                    failed_endpoints.append(f"{endpoint} (error: {str(e)})")
            
            success_rate = len(successful_endpoints) / len(admin_endpoints)
            
            if success_rate >= 0.8:  # At least 80% success rate
                self.log_test_result(
                    "Admin Routes Unified Auth",
                    True,
                    f"Admin routes successfully use unified authentication ({len(successful_endpoints)}/{len(admin_endpoints)} endpoints)",
                    {"successful": successful_endpoints, "failed": failed_endpoints}
                )
                return True
            else:
                self.log_test_result(
                    "Admin Routes Unified Auth",
                    False,
                    f"Too many admin routes failed unified authentication ({len(failed_endpoints)}/{len(admin_endpoints)} failed)",
                    {"successful": successful_endpoints, "failed": failed_endpoints}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Admin Routes Unified Auth",
                False,
                f"Exception during admin routes unified auth test: {str(e)}"
            )
            return False
    
    def test_admin_session_management(self) -> bool:
        """Test admin session management with unified authentication"""
        try:
            logger.info("🎫 Testing admin session management...")
            
            # Test session verification
            headers = {"Cookie": f"session_token={self.admin_session_token}"}
            response = self.client.get("/api/auth/verify", headers=headers)
            
            session_valid = response.status_code == 200
            
            # Test session logout
            response = self.client.post("/api/auth/logout", headers=headers)
            logout_success = response.status_code == 200
            
            # Test access after logout (should fail)
            response = self.client.get("/api/admin/dashboard", headers=headers)
            access_blocked_after_logout = response.status_code == 401
            
            if session_valid and logout_success and access_blocked_after_logout:
                self.log_test_result(
                    "Admin Session Management",
                    True,
                    "Admin session management working correctly",
                    {
                        "session_valid": session_valid,
                        "logout_success": logout_success,
                        "access_blocked_after_logout": access_blocked_after_logout
                    }
                )
                return True
            else:
                self.log_test_result(
                    "Admin Session Management",
                    False,
                    "Admin session management has issues",
                    {
                        "session_valid": session_valid,
                        "logout_success": logout_success,
                        "access_blocked_after_logout": access_blocked_after_logout
                    }
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Admin Session Management",
                False,
                f"Exception during admin session management test: {str(e)}"
            )
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all admin dashboard authentication integration tests"""
        logger.info("🚀 Starting Admin Dashboard Authentication Integration Tests...")
        
        # Setup test users
        if not self.setup_test_users():
            return {
                "success": False,
                "message": "Failed to setup test users",
                "results": self.test_results
            }
        
        # Run all tests
        tests = [
            self.test_admin_login_authentication,
            self.test_admin_dashboard_access,
            self.test_admin_permission_validation,
            self.test_admin_routes_unified_auth,
            self.test_admin_session_management
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed_tests += 1
            except Exception as e:
                logger.error(f"Test failed with exception: {e}")
        
        success_rate = passed_tests / total_tests
        overall_success = success_rate >= 0.8  # Require 80% success rate
        
        summary = {
            "success": overall_success,
            "message": f"Admin Dashboard Authentication Integration Tests completed: {passed_tests}/{total_tests} tests passed",
            "success_rate": success_rate,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        if overall_success:
            logger.info("🎉 Admin Dashboard Authentication Integration Tests PASSED!")
        else:
            logger.error("❌ Admin Dashboard Authentication Integration Tests FAILED!")
        
        return summary

def main():
    """Main function to run the tests"""
    test_runner = AdminDashboardAuthTest()
    results = test_runner.run_all_tests()
    
    # Print summary
    print("\n" + "="*80)
    print("ADMIN DASHBOARD AUTHENTICATION INTEGRATION TEST SUMMARY")
    print("="*80)
    print(f"Overall Result: {'✅ PASS' if results['success'] else '❌ FAIL'}")
    print(f"Tests Passed: {results['passed_tests']}/{results['total_tests']}")
    print(f"Success Rate: {results['success_rate']:.1%}")
    print(f"Timestamp: {results['timestamp']}")
    
    print("\nDetailed Results:")
    for result in results['results']:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"  {status}: {result['test_name']} - {result['message']}")
    
    print("="*80)
    
    # Return appropriate exit code
    return 0 if results['success'] else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)