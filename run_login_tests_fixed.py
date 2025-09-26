#!/usr/bin/env python3
"""
Fixed Comprehensive Login Test Suite Runner
Executes all login testing and validation components without Unicode characters
for Windows compatibility.

Requirements covered: 1.1, 1.2, 1.3, 1.4, 6.1, 6.2, 6.3, 6.4
"""

import os
import sys
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path

class FixedLoginTestRunner:
    """Fixed test runner for comprehensive login testing suite"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "test_suites": {},
            "summary": {
                "total_suites": 0,
                "passed_suites": 0,
                "failed_suites": 0,
                "errors": []
            }
        }
        
        print("Comprehensive Login Test Suite Runner (Fixed)")
        print("=" * 50)
        print(f"Project root: {self.project_root}")
        print(f"Test execution started: {self.test_results['timestamp']}")
        print()
    
    def run_all_tests(self):
        """Run all test suites"""
        test_suites = [
            {
                "name": "Backend Unit Tests",
                "description": "Python backend authentication tests",
                "method": self.run_backend_unit_tests
            },
            {
                "name": "Admin User Verification Tests", 
                "description": "Admin user verification and management",
                "method": self.run_admin_verification_tests
            },
            {
                "name": "Frontend JavaScript Tests",
                "description": "Browser-based authentication tests",
                "method": self.run_frontend_tests
            },
            {
                "name": "API Validation Tests",
                "description": "API endpoint validation",
                "method": self.run_api_validation_tests
            }
        ]
        
        for suite in test_suites:
            self.run_test_suite(suite)
        
        self.generate_final_report()
        return self.test_results
    
    def run_test_suite(self, suite):
        """Run a specific test suite"""
        suite_name = suite["name"]
        print(f"Running {suite_name}")
        print(f"   {suite['description']}")
        print("-" * 50)
        
        self.test_results["summary"]["total_suites"] += 1
        
        try:
            start_time = time.time()
            result = suite["method"]()
            end_time = time.time()
            
            duration = end_time - start_time
            
            if result["success"]:
                self.test_results["summary"]["passed_suites"] += 1
                status = "PASSED"
            else:
                self.test_results["summary"]["failed_suites"] += 1
                status = "FAILED"
                self.test_results["summary"]["errors"].extend(result.get("errors", []))
            
            result["duration"] = duration
            result["status"] = status
            self.test_results["test_suites"][suite_name] = result
            
            print(f"{status} ({duration:.2f}s)")
            if result.get("details"):
                print(f"   Details: {result['details']}")
            if result.get("errors"):
                for error in result["errors"]:
                    print(f"   Error: {error}")
            
        except Exception as e:
            self.test_results["summary"]["failed_suites"] += 1
            self.test_results["summary"]["errors"].append(f"{suite_name}: {str(e)}")
            
            error_result = {
                "success": False,
                "status": "ERROR",
                "error": str(e),
                "duration": 0
            }
            self.test_results["test_suites"][suite_name] = error_result
            
            print(f"ERROR: {str(e)}")
        
        print()
    
    def run_backend_unit_tests(self):
        """Run backend unit tests with pytest"""
        test_files = [
            "tests/test_login_basic_validation.py"
        ]
        
        results = {"success": True, "errors": [], "details": ""}
        passed_files = 0
        
        for test_file in test_files:
            test_path = self.project_root / test_file
            
            if not test_path.exists():
                results["errors"].append(f"Test file not found: {test_file}")
                results["success"] = False
                continue
            
            try:
                print(f"   Running {test_file}...")
                
                # Use a simpler pytest command
                result = subprocess.run([
                    sys.executable, "-m", "pytest", str(test_path), 
                    "-v", "--tb=short", "--no-header", "--disable-warnings"
                ], capture_output=True, text=True, cwd=self.project_root, 
                   encoding='utf-8', errors='replace')
                
                if result.returncode == 0:
                    passed_files += 1
                    print(f"   PASS {test_file}")
                else:
                    results["success"] = False
                    error_msg = f"{test_file} failed"
                    if result.stdout:
                        # Get last few lines of output for error summary
                        lines = result.stdout.strip().split('\n')
                        error_lines = [line for line in lines[-10:] if 'FAILED' in line or 'ERROR' in line]
                        if error_lines:
                            error_msg += f": {error_lines[0]}"
                    results["errors"].append(error_msg)
                    print(f"   FAIL {test_file}")
                
            except Exception as e:
                results["success"] = False
                results["errors"].append(f"{test_file}: {str(e)}")
                print(f"   ERROR {test_file}: {str(e)}")
        
        results["details"] = f"{passed_files}/{len(test_files)} test files passed"
        return results
    
    def run_admin_verification_tests(self):
        """Run admin user verification tests"""
        test_file = "test_admin_user_verification.py"
        test_path = self.project_root / test_file
        
        results = {"success": True, "errors": [], "details": ""}
        
        if not test_path.exists():
            results["success"] = False
            results["errors"].append(f"Test file not found: {test_file}")
            return results
        
        try:
            print(f"   Running {test_file}...")
            result = subprocess.run([
                sys.executable, str(test_path), "integration"
            ], capture_output=True, text=True, cwd=self.project_root,
               encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                results["details"] = "Admin verification tests passed"
                print(f"   PASS {test_file}")
            else:
                results["success"] = False
                error_msg = f"{test_file} failed"
                if result.stderr:
                    error_msg += f": {result.stderr.strip()[:200]}"  # Limit error message length
                results["errors"].append(error_msg)
                print(f"   FAIL {test_file}")
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Admin verification test error: {str(e)}")
            print(f"   ERROR {test_file}: {str(e)}")
        
        return results
    
    def run_frontend_tests(self):
        """Run frontend JavaScript tests validation"""
        frontend_test_files = [
            "frontend/comprehensive-login-test-suite.js",
            "frontend/comprehensive-login-test-runner.html"
        ]
        
        results = {"success": True, "errors": [], "details": ""}
        existing_files = 0
        
        for test_file in frontend_test_files:
            test_path = self.project_root / test_file
            
            if test_path.exists():
                existing_files += 1
                print(f"   PASS {test_file} exists")
            else:
                results["errors"].append(f"Frontend test file not found: {test_file}")
                print(f"   FAIL {test_file} missing")
        
        if existing_files == len(frontend_test_files):
            # Validate JavaScript syntax
            js_test_file = self.project_root / "frontend/comprehensive-login-test-suite.js"
            try:
                with open(js_test_file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Basic validation - check for key components
                required_components = [
                    "ComprehensiveLoginTestSuite",
                    "runAllTests",
                    "runBrowserCompatibilityTests",
                    "runAuthenticationFlowTests"
                ]
                
                missing_components = []
                for component in required_components:
                    if component not in content:
                        missing_components.append(component)
                
                if missing_components:
                    results["success"] = False
                    results["errors"].append(f"Missing components: {', '.join(missing_components)}")
                else:
                    print("   PASS JavaScript test suite structure validated")
                
            except Exception as e:
                results["success"] = False
                results["errors"].append(f"JavaScript validation error: {str(e)}")
        else:
            results["success"] = False
        
        results["details"] = f"{existing_files}/{len(frontend_test_files)} frontend test files found"
        return results
    
    def run_api_validation_tests(self):
        """Run API validation tests"""
        test_file = "validate_api_fixes.py"
        test_path = self.project_root / test_file
        
        results = {"success": True, "errors": [], "details": ""}
        
        if not test_path.exists():
            results["success"] = False
            results["errors"].append(f"API validation file not found: {test_file}")
            return results
        
        try:
            print(f"   Running {test_file}...")
            result = subprocess.run([
                sys.executable, str(test_path)
            ], capture_output=True, text=True, cwd=self.project_root,
               encoding='utf-8', errors='replace', timeout=30)
            
            if result.returncode == 0:
                results["details"] = "API validation tests passed"
                print(f"   PASS {test_file}")
            else:
                results["success"] = False
                error_msg = f"{test_file} failed"
                if result.stderr:
                    error_msg += f": {result.stderr.strip()[:200]}"
                results["errors"].append(error_msg)
                print(f"   FAIL {test_file}")
            
        except subprocess.TimeoutExpired:
            results["success"] = False
            results["errors"].append(f"{test_file} timed out")
            print(f"   TIMEOUT {test_file}")
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"API validation error: {str(e)}")
            print(f"   ERROR {test_file}: {str(e)}")
        
        return results
    
    def generate_final_report(self):
        """Generate final test report"""
        print("FINAL TEST REPORT")
        print("=" * 50)
        
        summary = self.test_results["summary"]
        print(f"Total Test Suites: {summary['total_suites']}")
        print(f"Passed: {summary['passed_suites']}")
        print(f"Failed: {summary['failed_suites']}")
        
        if summary['total_suites'] > 0:
            success_rate = (summary['passed_suites'] / summary['total_suites']) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        print()
        
        # Detailed results
        for suite_name, result in self.test_results["test_suites"].items():
            print(f"{result['status']} {suite_name}")
            if result.get("details"):
                print(f"   {result['details']}")
            if result.get("duration"):
                print(f"   Duration: {result['duration']:.2f}s")
        
        print()
        
        # Errors summary
        if summary['errors']:
            print("ERRORS ENCOUNTERED:")
            for i, error in enumerate(summary['errors'][:10]):  # Limit to first 10 errors
                print(f"   {i+1}. {error}")
            if len(summary['errors']) > 10:
                print(f"   ... and {len(summary['errors']) - 10} more errors")
            print()
        
        # Save report to file
        report_file = self.project_root / f"test_report_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, indent=2, ensure_ascii=False)
            print(f"Detailed report saved to: {report_file}")
        except Exception as e:
            print(f"Could not save report: {str(e)}")
        
        # Overall result
        if summary['failed_suites'] == 0:
            print("ALL TESTS PASSED!")
            return True
        else:
            print("SOME TESTS FAILED!")
            return False
    
    def run_specific_suite(self, suite_name):
        """Run a specific test suite by name"""
        suite_map = {
            "backend": self.run_backend_unit_tests,
            "admin": self.run_admin_verification_tests,
            "frontend": self.run_frontend_tests,
            "api": self.run_api_validation_tests
        }
        
        if suite_name not in suite_map:
            print(f"Unknown test suite: {suite_name}")
            print(f"Available suites: {', '.join(suite_map.keys())}")
            return False
        
        suite = {
            "name": suite_name.title() + " Tests",
            "description": f"Running {suite_name} test suite",
            "method": suite_map[suite_name]
        }
        
        self.run_test_suite(suite)
        self.generate_final_report()
        
        return self.test_results["summary"]["failed_suites"] == 0

def main():
    """Main entry point"""
    runner = FixedLoginTestRunner()
    
    if len(sys.argv) > 1:
        # Run specific test suite
        suite_name = sys.argv[1].lower()
        success = runner.run_specific_suite(suite_name)
    else:
        # Run all tests
        runner.run_all_tests()
        success = runner.test_results["summary"]["failed_suites"] == 0
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()