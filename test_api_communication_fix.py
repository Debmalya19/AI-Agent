#!/usr/bin/env python3
"""
Test script for API communication and endpoint routing fixes
Tests the authentication endpoints and CORS configuration
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any

import httpx
import pytest
from sqlalchemy.orm import Session

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_ADMIN_USER = {
    "email": "admin@test.com",
    "username": "testadmin",
    "password": "testpassword123",
    "full_name": "Test Admin User"
}

class APITestSuite:
    """Test suite for API communication fixes"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.session_token = None
        self.test_results = []
    
    async def run_all_tests(self):
        """Run all API communication tests"""
        logger.info("🧪 Starting API Communication Test Suite")
        
        tests = [
            ("CORS Configuration", self.test_cors_configuration),
            ("Authentication Endpoint Registration", self.test_auth_endpoints),
            ("Request Format Compatibility", self.test_request_formats),
            ("Admin Login Endpoint", self.test_admin_login),
            ("Session Management", self.test_session_management),
            ("Error Handling", self.test_error_handling),
            ("Request Validation", self.test_request_validation),
        ]
        
        for test_name, test_func in tests:
            try:
                logger.info(f"🔍 Running test: {test_name}")
                result = await test_func()
                self.test_results.append({
                    "test": test_name,
                    "status": "PASS" if result else "FAIL",
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"✅ {test_name}: {'PASS' if result else 'FAIL'}")
            except Exception as e:
                logger.error(f"❌ {test_name}: ERROR - {e}")
                self.test_results.append({
                    "test": test_name,
                    "status": "ERROR",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        await self.client.aclose()
        self.print_summary()
    
    async def test_cors_configuration(self) -> bool:
        """Test CORS configuration"""
        try:
            # Test preflight request
            response = await self.client.options(
                f"{BASE_URL}/api/auth/login",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type, Authorization"
                }
            )
            
            # Check CORS headers
            cors_headers = [
                "access-control-allow-origin",
                "access-control-allow-methods",
                "access-control-allow-headers",
                "access-control-allow-credentials"
            ]
            
            for header in cors_headers:
                if header not in response.headers:
                    logger.warning(f"Missing CORS header: {header}")
                    return False
            
            # Check credentials are allowed
            if response.headers.get("access-control-allow-credentials") != "true":
                logger.warning("CORS credentials not allowed")
                return False
            
            logger.info("CORS configuration is correct")
            return True
            
        except Exception as e:
            logger.error(f"CORS test failed: {e}")
            return False
    
    async def test_auth_endpoints(self) -> bool:
        """Test authentication endpoint registration"""
        try:
            endpoints_to_test = [
                "/api/auth/login",
                "/admin/auth/login",
                "/api/auth/verify",
                "/api/auth/logout"
            ]
            
            for endpoint in endpoints_to_test:
                try:
                    # Test that endpoint exists (should not return 404)
                    response = await self.client.post(f"{BASE_URL}{endpoint}")
                    
                    if response.status_code == 404:
                        logger.error(f"Endpoint not found: {endpoint}")
                        return False
                    
                    logger.info(f"Endpoint registered: {endpoint}")
                    
                except Exception as e:
                    logger.error(f"Error testing endpoint {endpoint}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Endpoint registration test failed: {e}")
            return False
    
    async def test_request_formats(self) -> bool:
        """Test different request format compatibility"""
        try:
            # Test JSON format
            json_response = await self.client.post(
                f"{BASE_URL}/api/auth/login",
                headers={"Content-Type": "application/json"},
                json={
                    "email": "test@example.com",
                    "password": "wrongpassword"
                }
            )
            
            # Should return 401 (not 400 for format error)
            if json_response.status_code not in [401, 422]:
                logger.warning(f"Unexpected status for JSON format: {json_response.status_code}")
                return False
            
            # Test alternative JSON format
            alt_json_response = await self.client.post(
                f"{BASE_URL}/api/auth/login",
                headers={"Content-Type": "application/json"},
                json={
                    "username": "test@example.com",
                    "password": "wrongpassword"
                }
            )
            
            # Should also return 401 (not 400 for format error)
            if alt_json_response.status_code not in [401, 422]:
                logger.warning(f"Unexpected status for alternative JSON format: {alt_json_response.status_code}")
                return False
            
            logger.info("Request format compatibility working")
            return True
            
        except Exception as e:
            logger.error(f"Request format test failed: {e}")
            return False
    
    async def test_admin_login(self) -> bool:
        """Test admin login endpoint"""
        try:
            # First, try to create a test admin user (this might fail if user exists)
            try:
                await self.client.post(
                    f"{BASE_URL}/api/auth/register",
                    json=TEST_ADMIN_USER
                )
            except:
                pass  # User might already exist
            
            # Test admin login
            response = await self.client.post(
                f"{BASE_URL}/admin/auth/login",
                headers={"Content-Type": "application/json"},
                json={
                    "email": TEST_ADMIN_USER["email"],
                    "password": TEST_ADMIN_USER["password"]
                }
            )
            
            # Check response format
            if response.status_code == 200:
                data = response.json()
                required_fields = ["success", "token", "user"]
                
                for field in required_fields:
                    if field not in data:
                        logger.warning(f"Missing field in admin login response: {field}")
                        return False
                
                # Store token for other tests
                self.session_token = data.get("token")
                logger.info("Admin login endpoint working correctly")
                return True
            else:
                logger.warning(f"Admin login failed with status: {response.status_code}")
                logger.warning(f"Response: {response.text}")
                return False
            
        except Exception as e:
            logger.error(f"Admin login test failed: {e}")
            return False
    
    async def test_session_management(self) -> bool:
        """Test session management"""
        try:
            if not self.session_token:
                logger.warning("No session token available for session test")
                return False
            
            # Test session verification
            response = await self.client.get(
                f"{BASE_URL}/api/auth/verify",
                headers={"Authorization": f"Bearer {self.session_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("authenticated"):
                    logger.info("Session management working correctly")
                    return True
                else:
                    logger.warning("Session verification returned not authenticated")
                    return False
            else:
                logger.warning(f"Session verification failed: {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"Session management test failed: {e}")
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling"""
        try:
            # Test invalid JSON
            response = await self.client.post(
                f"{BASE_URL}/api/auth/login",
                headers={"Content-Type": "application/json"},
                content="invalid json"
            )
            
            if response.status_code != 400:
                logger.warning(f"Invalid JSON should return 400, got: {response.status_code}")
                return False
            
            # Test missing credentials
            response = await self.client.post(
                f"{BASE_URL}/api/auth/login",
                headers={"Content-Type": "application/json"},
                json={}
            )
            
            if response.status_code != 400:
                logger.warning(f"Missing credentials should return 400, got: {response.status_code}")
                return False
            
            logger.info("Error handling working correctly")
            return True
            
        except Exception as e:
            logger.error(f"Error handling test failed: {e}")
            return False
    
    async def test_request_validation(self) -> bool:
        """Test request validation and sanitization"""
        try:
            # Test XSS attempt
            response = await self.client.post(
                f"{BASE_URL}/api/auth/login",
                headers={"Content-Type": "application/json"},
                json={
                    "email": "<script>alert('xss')</script>@example.com",
                    "password": "password"
                }
            )
            
            # Should not crash the server
            if response.status_code >= 500:
                logger.warning("XSS attempt caused server error")
                return False
            
            # Test SQL injection attempt
            response = await self.client.post(
                f"{BASE_URL}/api/auth/login",
                headers={"Content-Type": "application/json"},
                json={
                    "email": "admin'; DROP TABLE users; --",
                    "password": "password"
                }
            )
            
            # Should not crash the server
            if response.status_code >= 500:
                logger.warning("SQL injection attempt caused server error")
                return False
            
            logger.info("Request validation working correctly")
            return True
            
        except Exception as e:
            logger.error(f"Request validation test failed: {e}")
            return False
    
    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "="*50)
        logger.info("🧪 API COMMUNICATION TEST SUMMARY")
        logger.info("="*50)
        
        passed = sum(1 for result in self.test_results if result["status"] == "PASS")
        failed = sum(1 for result in self.test_results if result["status"] == "FAIL")
        errors = sum(1 for result in self.test_results if result["status"] == "ERROR")
        
        logger.info(f"Total Tests: {len(self.test_results)}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Errors: {errors}")
        
        if failed > 0 or errors > 0:
            logger.info("\n❌ FAILED/ERROR TESTS:")
            for result in self.test_results:
                if result["status"] in ["FAIL", "ERROR"]:
                    logger.info(f"  - {result['test']}: {result['status']}")
                    if "error" in result:
                        logger.info(f"    Error: {result['error']}")
        
        success_rate = (passed / len(self.test_results)) * 100
        logger.info(f"\n✅ Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            logger.info("🎉 API communication fixes are working well!")
        else:
            logger.warning("⚠️ Some API communication issues remain")


async def main():
    """Main test function"""
    test_suite = APITestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())