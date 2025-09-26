#!/usr/bin/env python3
"""
Validation script for API communication fixes
Validates the code structure and configuration without requiring a running server
"""

import os
import sys
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIFixValidator:
    """Validator for API communication fixes"""
    
    def __init__(self):
        self.base_path = Path("ai-agent")
        self.validation_results = []
    
    def run_all_validations(self):
        """Run all validation checks"""
        logger.info("🔍 Validating API Communication Fixes")
        
        validations = [
            ("Authentication Routes Structure", self.validate_auth_routes),
            ("CORS Configuration", self.validate_cors_config),
            ("Request Validation Middleware", self.validate_request_middleware),
            ("Admin Endpoint Registration", self.validate_admin_endpoints),
            ("Frontend API Compatibility", self.validate_frontend_api),
        ]
        
        for validation_name, validation_func in validations:
            try:
                logger.info(f"🔍 Validating: {validation_name}")
                result = validation_func()
                self.validation_results.append({
                    "validation": validation_name,
                    "status": "PASS" if result else "FAIL"
                })
                logger.info(f"{'✅' if result else '❌'} {validation_name}: {'PASS' if result else 'FAIL'}")
            except Exception as e:
                logger.error(f"❌ {validation_name}: ERROR - {e}")
                self.validation_results.append({
                    "validation": validation_name,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        self.print_summary()
    
    def validate_auth_routes(self) -> bool:
        """Validate authentication routes structure"""
        try:
            auth_routes_path = self.base_path / "backend" / "auth_routes.py"
            
            if not auth_routes_path.exists():
                logger.error("auth_routes.py not found")
                return False
            
            content = auth_routes_path.read_text()
            
            # Check for required endpoints
            required_endpoints = [
                "@auth_router.post(\"/login\"",
                "@admin_auth_router.post(\"/login\"",
                "@auth_router.get(\"/verify\"",
                "@auth_router.post(\"/logout\")"
            ]
            
            for endpoint in required_endpoints:
                if endpoint not in content:
                    logger.warning(f"Missing endpoint: {endpoint}")
                    return False
            
            # Check for enhanced validation
            validation_checks = [
                "Enhanced input validation",
                "Sanitize input data",
                "Rate limiting",
                "Admin privileges required"
            ]
            
            for check in validation_checks:
                if check not in content:
                    logger.warning(f"Missing validation: {check}")
                    return False
            
            logger.info("Authentication routes structure is valid")
            return True
            
        except Exception as e:
            logger.error(f"Auth routes validation failed: {e}")
            return False
    
    def validate_cors_config(self) -> bool:
        """Validate CORS configuration"""
        try:
            startup_path = self.base_path / "backend" / "unified_startup.py"
            
            if not startup_path.exists():
                logger.error("unified_startup.py not found")
                return False
            
            content = startup_path.read_text()
            
            # Check for CORS middleware
            cors_checks = [
                "CORSMiddleware",
                "allow_credentials=True",
                "allow_methods=",
                "allow_headers=",
                "expose_headers="
            ]
            
            for check in cors_checks:
                if check not in content:
                    logger.warning(f"Missing CORS config: {check}")
                    return False
            
            # Check for enhanced headers
            enhanced_headers = [
                "Authorization",
                "X-Requested-With",
                "X-Request-Format"
            ]
            
            for header in enhanced_headers:
                if header not in content:
                    logger.warning(f"Missing CORS header: {header}")
                    return False
            
            logger.info("CORS configuration is valid")
            return True
            
        except Exception as e:
            logger.error(f"CORS validation failed: {e}")
            return False
    
    def validate_request_middleware(self) -> bool:
        """Validate request validation middleware"""
        try:
            middleware_path = self.base_path / "backend" / "request_validation_middleware.py"
            
            if not middleware_path.exists():
                logger.error("request_validation_middleware.py not found")
                return False
            
            content = middleware_path.read_text()
            
            # Check for required components
            middleware_checks = [
                "class RequestValidationMiddleware",
                "BaseHTTPMiddleware",
                "_validate_request",
                "_sanitize_string",
                "_check_rate_limit",
                "_add_security_headers"
            ]
            
            for check in middleware_checks:
                if check not in content:
                    logger.warning(f"Missing middleware component: {check}")
                    return False
            
            # Check for security patterns
            security_checks = [
                "security_patterns",
                "html.escape",
                "X-Content-Type-Options",
                "X-Frame-Options"
            ]
            
            for check in security_checks:
                if check not in content:
                    logger.warning(f"Missing security feature: {check}")
                    return False
            
            logger.info("Request validation middleware is valid")
            return True
            
        except Exception as e:
            logger.error(f"Request middleware validation failed: {e}")
            return False
    
    def validate_admin_endpoints(self) -> bool:
        """Validate admin endpoint registration"""
        try:
            main_path = self.base_path / "main.py"
            
            if not main_path.exists():
                logger.error("main.py not found")
                return False
            
            content = main_path.read_text()
            
            # Check for router includes
            router_checks = [
                "app.include_router(auth_router)",
                "app.include_router(admin_auth_router)",
                "app.include_router(admin_router)"
            ]
            
            for check in router_checks:
                if check not in content:
                    logger.warning(f"Missing router include: {check}")
                    return False
            
            # Check for admin compatibility endpoint
            if "@app.post(\"/admin/auth/login\")" not in content:
                logger.warning("Missing admin compatibility endpoint")
                return False
            
            logger.info("Admin endpoint registration is valid")
            return True
            
        except Exception as e:
            logger.error(f"Admin endpoints validation failed: {e}")
            return False
    
    def validate_frontend_api(self) -> bool:
        """Validate frontend API compatibility"""
        try:
            api_path = self.base_path / "admin-dashboard" / "frontend" / "js" / "unified_api.js"
            
            if not api_path.exists():
                logger.error("unified_api.js not found")
                return False
            
            content = api_path.read_text()
            
            # Check for required API methods
            api_methods = [
                "async login(",
                "async logout(",
                "async verifySession(",
                "getAuthHeader(",
                "getTokenFromCookies("
            ]
            
            for method in api_methods:
                if method not in content:
                    logger.warning(f"Missing API method: {method}")
                    return False
            
            # Check for proper endpoint URLs
            endpoint_checks = [
                "/api/auth/login",
                "/api/auth/verify",
                "/api/auth/logout"
            ]
            
            for endpoint in endpoint_checks:
                if endpoint not in content:
                    logger.warning(f"Missing endpoint reference: {endpoint}")
                    return False
            
            logger.info("Frontend API compatibility is valid")
            return True
            
        except Exception as e:
            logger.error(f"Frontend API validation failed: {e}")
            return False
    
    def print_summary(self):
        """Print validation summary"""
        logger.info("\n" + "="*50)
        logger.info("🔍 API COMMUNICATION VALIDATION SUMMARY")
        logger.info("="*50)
        
        passed = sum(1 for result in self.validation_results if result["status"] == "PASS")
        failed = sum(1 for result in self.validation_results if result["status"] == "FAIL")
        errors = sum(1 for result in self.validation_results if result["status"] == "ERROR")
        
        logger.info(f"Total Validations: {len(self.validation_results)}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Errors: {errors}")
        
        if failed > 0 or errors > 0:
            logger.info("\n❌ FAILED/ERROR VALIDATIONS:")
            for result in self.validation_results:
                if result["status"] in ["FAIL", "ERROR"]:
                    logger.info(f"  - {result['validation']}: {result['status']}")
                    if "error" in result:
                        logger.info(f"    Error: {result['error']}")
        
        success_rate = (passed / len(self.validation_results)) * 100
        logger.info(f"\n✅ Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            logger.info("🎉 API communication fixes are properly implemented!")
        else:
            logger.warning("⚠️ Some API communication fixes need attention")


def main():
    """Main validation function"""
    validator = APIFixValidator()
    validator.run_all_validations()


if __name__ == "__main__":
    main()