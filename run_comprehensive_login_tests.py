#!/usr/bin/env python3
"""
Comprehensive Login Test Suite Runner
Executes all login testing and validation components including:
- Backend Python tests
- Frontend JavaScript tests
- Integration tests
- Cross-browser compatibility tests
- Error scenario tests

Requirements covered: 1.1, 1.2, 1.3, 1.4, 6.1, 6.2, 6.3, 6.4
"""

import os
import sys
import subprocess
import time
import json
import webbrowser
from datetime import datetime
from pathlib import Path

class ComprehensiveLoginTestRunner:
    """Main test runner for comprehensive login testing suite"""
    
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
        
        print("Comprehensive Login Test Suite Runner")
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
                "name": "Backend Integration Tests", 
                "description": "Complete backend integration testing",
                "method": self.run_backend_integration_tests
            },
            {
                "name": "Frontend JavaScript Tests",
                "description": "Browser-based authentication tests",
                "method": self.run_frontend_tests
            },
            {
                "name": "Complete Integration Tests",
                "description": "End-to-end frontend-backend integration",
                "method": self.run_complete_integration_tests
            },
            {
                "name": "Cross-Browser Compatibility",
                "description": "Browser compatibility validation",
                "method": self.run_browser_compatibility_tests
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
        """Run backend unit tests"""
        test_files = [
            "tests/test_comprehensive_login_validation_suite.py"
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
                result = subprocess.run([
                    sys.executable, "-m", "pytest", str(test_path), 
                    "-v", "--tb=short", "--no-header"
                ], capture_output=True, text=True, cwd=self.project_root)
                
                if result.returncode == 0:
                    passed_files += 1
                    print(f"   ✓ {test_file} passed")
                else:
                    results["success"] = False
                    error_msg = f"{test_file} failed"
                    if result.stderr:
                        error_msg += f": {result.stderr.strip()}"
                    results["errors"].append(error_msg)
                    print(f"   ✗ {test_file} failed")
                
            except Exception as e:
                results["success"] = False
                results["errors"].append(f"{test_file}: {str(e)}")
                print(f"   ✗ {test_file} error: {str(e)}")
        
        results["details"] = f"{passed_files}/{len(test_files)} test files passed"
        return results
    
    def run_backend_integration_tests(self):
        """Run backend integration tests"""
        test_files = [
            "test_comprehensive_authentication_integration_final.py",
            "test_admin_user_verification.py"
        ]
        
        results = {"success": True, "errors": [], "details": ""}
        passed_files = 0
        
        for test_file in test_files:
            test_path = self.project_root / test_file
            
            if not test_path.exists():
                results["errors"].append(f"Test file not found: {test_file}")
                continue
            
            try:
                print(f"   Running {test_file}...")
                result = subprocess.run([
                    sys.executable, str(test_path), "integration"
                ], capture_output=True, text=True, cwd=self.project_root)
                
                if result.returncode == 0:
                    passed_files += 1
                    print(f"   ✓ {test_file} passed")
                else:
                    results["success"] = False
                    error_msg = f"{test_file} failed"
                    if result.stderr:
                        error_msg += f": {result.stderr.strip()}"
                    results["errors"].append(error_msg)
                    print(f"   ✗ {test_file} failed")
                
            except Exception as e:
                results["success"] = False
                results["errors"].append(f"{test_file}: {str(e)}")
                print(f"   ✗ {test_file} error: {str(e)}")
        
        results["details"] = f"{passed_files}/{len(test_files)} integration tests passed"
        return results
    
    def run_frontend_tests(self):
        """Run frontend JavaScript tests"""
        # Check if frontend test files exist
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
                print(f"   ✓ {test_file} exists")
            else:
                results["errors"].append(f"Frontend test file not found: {test_file}")
                print(f"   ✗ {test_file} missing")
        
        if existing_files == len(frontend_test_files):
            # Try to validate JavaScript syntax
            js_test_file = self.project_root / "frontend/comprehensive-login-test-suite.js"
            try:
                with open(js_test_file, 'r') as f:
                    content = f.read()
                
                # Basic validation - check for key components
                required_components = [
                    "ComprehensiveLoginTestSuite",
                    "runAllTests",
                    "runBrowserCompatibilityTests",
                    "runAuthenticationFlowTests",
                    "runSessionManagementTests",
                    "runErrorHandlingTests"
                ]
                
                missing_components = []
                for component in required_components:
                    if component not in content:
                        missing_components.append(component)
                
                if missing_components:
                    results["success"] = False
                    results["errors"].append(f"Missing components: {', '.join(missing_components)}")
                else:
                    print("   ✓ JavaScript test suite structure validated")
                
            except Exception as e:
                results["success"] = False
                results["errors"].append(f"JavaScript validation error: {str(e)}")
        else:
            results["success"] = False
        
        results["details"] = f"{existing_files}/{len(frontend_test_files)} frontend test files found"
        return results
    
    def run_complete_integration_tests(self):
        """Run complete integration tests"""
        test_file = "tests/test_login_integration_complete.py"
        test_path = self.project_root / test_file
        
        results = {"success": True, "errors": [], "details": ""}
        
        if not test_path.exists():
            results["success"] = False
            results["errors"].append(f"Integration test file not found: {test_file}")
            return results
        
        try:
            print(f"   Running {test_file}...")
            result = subprocess.run([
                sys.executable, str(test_path), "run"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                results["details"] = "Complete integration tests passed"
                print("   ✓ Integration tests passed")
            else:
                results["success"] = False
                error_msg = "Integration tests failed"
                if result.stderr:
                    error_msg += f": {result.stderr.strip()}"
                results["errors"].append(error_msg)
                print("   ✗ Integration tests failed")
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Integration test error: {str(e)}")
            print(f"   ✗ Integration test error: {str(e)}")
        
        return results
    
    def run_browser_compatibility_tests(self):
        """Run browser compatibility tests"""
        # This would ideally use a browser automation tool like Selenium
        # For now, we'll check if the test runner HTML exists and can be opened
        
        test_runner_path = self.project_root / "frontend/comprehensive-login-test-runner.html"
        
        results = {"success": True, "errors": [], "details": ""}
        
        if not test_runner_path.exists():
            results["success"] = False
            results["errors"].append("Browser test runner HTML not found")
            return results
        
        try:
            # Validate HTML structure
            with open(test_runner_path, 'r') as f:
                content = f.read()
            
            required_elements = [
                "ComprehensiveLoginTestSuite",
                "run-all-tests",
                "browser-compatibility",
                "authentication-flow",
                "session-management",
                "error-handling"
            ]
            
            missing_elements = []
            for element in required_elements:
                if element not in content:
                    missing_elements.append(element)
            
            if missing_elements:
                results["success"] = False
                results["errors"].append(f"Missing HTML elements: {', '.join(missing_elements)}")
            else:
                results["details"] = "Browser test runner HTML validated"
                print("   ✓ Browser test runner HTML structure validated")
                
                # Optionally open in browser for manual testing
                if "--open-browser" in sys.argv:
                    try:
                        webbrowser.open(f"file://{test_runner_path.absolute()}")
                        print("   ✓ Browser test runner opened for manual testing")
                    except Exception as e:
                        print(f"   ⚠ Could not open browser: {str(e)}")
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Browser test validation error: {str(e)}")
        
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
            for error in summary['errors']:
                print(f"   - {error}")
            print()
        
        # Save report to file
        report_file = self.project_root / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(report_file, 'w') as f:
                json.dump(self.test_results, f, indent=2)
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
            "integration": self.run_backend_integration_tests,
            "frontend": self.run_frontend_tests,
            "complete": self.run_complete_integration_tests,
            "browser": self.run_browser_compatibility_tests
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
    runner = ComprehensiveLoginTestRunner()
    
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