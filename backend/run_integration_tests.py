#!/usr/bin/env python3
"""
Integration Test Runner

Comprehensive test runner for all admin dashboard integration tests.
Executes all test suites and provides detailed reporting.

Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3
"""

import sys
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Add the parent directory to sys.path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

class IntegrationTestRunner:
    """Comprehensive integration test runner"""
    
    def __init__(self):
        self.test_files = [
            "test_unified_models.py",
            "test_auth_integration.py", 
            "test_integration_validation.py",  # Core validation tests
            "test_admin_integration.py",
            "test_data_sync_service.py",
            "test_comprehensive_integration.py",
            "test_api_integration_endpoints.py",
            "test_end_to_end_workflows.py"
        ]
        
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_single_test(self, test_file):
        """Run a single test file and capture results"""
        print(f"\n{'='*60}")
        print(f"Running {test_file}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Run pytest on the specific file
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                test_file, 
                "-v", 
                "--tb=short",
                "--no-header",
                "--disable-warnings"
            ], 
            capture_output=True, 
            text=True,
            cwd=os.path.dirname(__file__)
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            self.results[test_file] = {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': duration,
                'success': result.returncode == 0
            }
            
            # Print results
            if result.returncode == 0:
                print(f"✅ {test_file} PASSED ({duration:.2f}s)")
            else:
                print(f"❌ {test_file} FAILED ({duration:.2f}s)")
            
            # Print output
            if result.stdout:
                print("\nSTDOUT:")
                print(result.stdout)
            
            if result.stderr:
                print("\nSTDERR:")
                print(result.stderr)
                
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            self.results[test_file] = {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'duration': duration,
                'success': False
            }
            
            print(f"❌ {test_file} ERROR ({duration:.2f}s): {e}")
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Admin Dashboard Integration Test Suite")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Python: {sys.version}")
        print(f"Working Directory: {os.getcwd()}")
        
        self.start_time = time.time()
        
        # Check if test files exist
        missing_files = []
        for test_file in self.test_files:
            if not os.path.exists(os.path.join(os.path.dirname(__file__), test_file)):
                missing_files.append(test_file)
        
        if missing_files:
            print(f"\n⚠️ Warning: Missing test files: {missing_files}")
            # Remove missing files from test list
            self.test_files = [f for f in self.test_files if f not in missing_files]
        
        # Run each test file
        for test_file in self.test_files:
            self.run_single_test(test_file)
        
        self.end_time = time.time()
        
        # Generate summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        print(f"\n{'='*80}")
        print("INTEGRATION TEST SUMMARY REPORT")
        print(f"{'='*80}")
        
        total_duration = self.end_time - self.start_time
        passed_tests = sum(1 for result in self.results.values() if result['success'])
        failed_tests = len(self.results) - passed_tests
        
        print(f"Total Duration: {total_duration:.2f} seconds")
        print(f"Tests Run: {len(self.results)}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/len(self.results)*100):.1f}%")
        
        print(f"\n{'Test File':<40} {'Status':<10} {'Duration':<10}")
        print("-" * 60)
        
        for test_file, result in self.results.items():
            status = "PASS" if result['success'] else "FAIL"
            duration = f"{result['duration']:.2f}s"
            print(f"{test_file:<40} {status:<10} {duration:<10}")
        
        # Detailed failure analysis
        failed_results = {k: v for k, v in self.results.items() if not v['success']}
        if failed_results:
            print(f"\n{'='*60}")
            print("FAILURE ANALYSIS")
            print(f"{'='*60}")
            
            for test_file, result in failed_results.items():
                print(f"\n❌ {test_file}")
                print("-" * 40)
                if result['stderr']:
                    print("Error Output:")
                    print(result['stderr'][:500])  # Limit output length
                    if len(result['stderr']) > 500:
                        print("... (truncated)")
        
        # Test coverage analysis
        print(f"\n{'='*60}")
        print("TEST COVERAGE ANALYSIS")
        print(f"{'='*60}")
        
        coverage_areas = {
            "Database Integration": ["test_unified_models.py"],
            "Authentication Integration": ["test_auth_integration.py"],
            "Admin API Integration": ["test_admin_integration.py", "test_api_integration_endpoints.py"],
            "Data Synchronization": ["test_data_sync_service.py"],
            "End-to-End Workflows": ["test_end_to_end_workflows.py"],
            "Comprehensive Integration": ["test_comprehensive_integration.py"]
        }
        
        for area, test_files in coverage_areas.items():
            area_results = [self.results.get(f, {'success': False}) for f in test_files if f in self.results]
            if area_results:
                area_success = all(r['success'] for r in area_results)
                status = "✅ PASS" if area_success else "❌ FAIL"
                print(f"{area:<30} {status}")
            else:
                print(f"{area:<30} ⚠️ NO TESTS")
        
        # Requirements coverage
        print(f"\n{'='*60}")
        print("REQUIREMENTS COVERAGE")
        print(f"{'='*60}")
        
        requirements_coverage = {
            "2.1 - Customer data synchronization": ["test_data_sync_service.py", "test_comprehensive_integration.py"],
            "2.2 - Support ticket synchronization": ["test_data_sync_service.py", "test_end_to_end_workflows.py"],
            "2.3 - Real-time data updates": ["test_data_sync_service.py", "test_comprehensive_integration.py"],
            "2.4 - Data consistency": ["test_data_sync_service.py", "test_end_to_end_workflows.py"],
            "3.1 - Unified authentication": ["test_auth_integration.py", "test_comprehensive_integration.py"],
            "3.2 - Session management": ["test_auth_integration.py", "test_comprehensive_integration.py"],
            "3.3 - Role-based access": ["test_auth_integration.py", "test_comprehensive_integration.py"],
            "4.1 - API integration": ["test_admin_integration.py", "test_api_integration_endpoints.py"],
            "4.2 - Endpoint compatibility": ["test_api_integration_endpoints.py", "test_comprehensive_integration.py"],
            "4.3 - Error handling": ["test_api_integration_endpoints.py", "test_comprehensive_integration.py"]
        }
        
        for requirement, test_files in requirements_coverage.items():
            req_results = [self.results.get(f, {'success': False}) for f in test_files if f in self.results]
            if req_results:
                req_success = any(r['success'] for r in req_results)  # At least one test passes
                status = "✅ COVERED" if req_success else "❌ NOT COVERED"
                print(f"{requirement:<40} {status}")
        
        # Final verdict
        print(f"\n{'='*80}")
        if failed_tests == 0:
            print("🎉 ALL INTEGRATION TESTS PASSED!")
            print("The admin dashboard integration is working correctly.")
        else:
            print(f"⚠️ {failed_tests} TEST(S) FAILED")
            print("Please review the failures above and fix the issues.")
        print(f"{'='*80}")
        
        return failed_tests == 0
    
    def run_specific_test_category(self, category):
        """Run tests for a specific category"""
        category_tests = {
            "database": ["test_unified_models.py"],
            "auth": ["test_auth_integration.py"],
            "api": ["test_admin_integration.py", "test_api_integration_endpoints.py"],
            "sync": ["test_data_sync_service.py"],
            "e2e": ["test_end_to_end_workflows.py"],
            "comprehensive": ["test_comprehensive_integration.py"]
        }
        
        if category not in category_tests:
            print(f"❌ Unknown category: {category}")
            print(f"Available categories: {list(category_tests.keys())}")
            return False
        
        self.test_files = category_tests[category]
        return self.run_all_tests()


def main():
    """Main entry point"""
    runner = IntegrationTestRunner()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        category = sys.argv[1]
        success = runner.run_specific_test_category(category)
    else:
        success = runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()