#!/usr/bin/env python3
"""
Master Test Runner for Static File Serving Tests
Task 5: Create static file serving tests

This script runs all available test suites for static file serving functionality
and provides a comprehensive report.
"""

import sys
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")

def run_integration_tests():
    """Run the integration test suite"""
    print_section("Integration Tests")
    
    try:
        result = subprocess.run([
            sys.executable, "test_static_files_integration.py"
        ], capture_output=True, text=True, timeout=60)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        print(f"✅ Integration tests: {'PASSED' if success else 'FAILED'}")
        return success
        
    except subprocess.TimeoutExpired:
        print("❌ Integration tests: TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ Integration tests: ERROR - {e}")
        return False

def run_unittest_suite():
    """Run the unittest-based test suite"""
    print_section("Unittest Test Suite")
    
    try:
        result = subprocess.run([
            sys.executable, "test_static_files_unittest.py"
        ], capture_output=True, text=True, timeout=120)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        print(f"✅ Unittest suite: {'PASSED' if success else 'FAILED'}")
        return success
        
    except subprocess.TimeoutExpired:
        print("❌ Unittest suite: TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ Unittest suite: ERROR - {e}")
        return False

def run_standalone_tests():
    """Run the standalone test runner"""
    print_section("Standalone Test Runner")
    
    try:
        result = subprocess.run([
            sys.executable, "run_static_file_tests.py", "--save"
        ], capture_output=True, text=True, timeout=60)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        print(f"✅ Standalone tests: {'PASSED' if success else 'FAILED'}")
        return success
        
    except subprocess.TimeoutExpired:
        print("❌ Standalone tests: TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ Standalone tests: ERROR - {e}")
        return False

def run_pytest_suite():
    """Run the pytest-based test suite if pytest is available"""
    print_section("Pytest Test Suite")
    
    try:
        # Check if pytest is available
        result = subprocess.run([
            sys.executable, "-c", "import pytest"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print("⚠️  Pytest not available, skipping pytest tests")
            return None
        
        # Run pytest tests
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "test_static_file_serving_comprehensive.py", 
            "-v", "--tb=short"
        ], capture_output=True, text=True, timeout=120)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        print(f"✅ Pytest suite: {'PASSED' if success else 'FAILED'}")
        return success
        
    except subprocess.TimeoutExpired:
        print("❌ Pytest suite: TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ Pytest suite: ERROR - {e}")
        return False

def check_file_structure():
    """Check that all required test files exist"""
    print_section("Test File Structure Check")
    
    required_files = [
        "test_static_file_serving_comprehensive.py",
        "test_static_files_unittest.py", 
        "test_static_files_integration.py",
        "run_static_file_tests.py",
        "STATIC_FILE_TESTS_README.md"
    ]
    
    all_exist = True
    
    for file_name in required_files:
        file_path = Path(file_name)
        exists = file_path.exists()
        size = file_path.stat().st_size if exists else 0
        
        status = "✅" if exists else "❌"
        print(f"  {status} {file_name} ({size} bytes)")
        
        if not exists:
            all_exist = False
    
    print(f"\n✅ File structure: {'COMPLETE' if all_exist else 'INCOMPLETE'}")
    return all_exist

def check_static_files():
    """Quick check of static file availability"""
    print_section("Static Files Quick Check")
    
    css_dir = Path("admin-dashboard/frontend/css")
    js_dir = Path("admin-dashboard/frontend/js")
    
    css_count = len(list(css_dir.glob("*.css"))) if css_dir.exists() else 0
    js_count = len(list(js_dir.glob("*.js"))) if js_dir.exists() else 0
    
    print(f"  📄 CSS files: {css_count}")
    print(f"  📜 JS files: {js_count}")
    
    if css_count > 0 and js_count > 0:
        print("✅ Static files: AVAILABLE")
        return True
    else:
        print("❌ Static files: MISSING")
        return False

def generate_summary_report(results):
    """Generate a summary report of all test results"""
    print_header("TEST EXECUTION SUMMARY")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Execution Time: {timestamp}")
    print(f"Working Directory: {os.getcwd()}")
    
    print(f"\n📊 Test Results:")
    
    total_suites = 0
    passed_suites = 0
    
    for test_name, result in results.items():
        if result is not None:
            total_suites += 1
            if result:
                passed_suites += 1
            
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"  {test_name:<25} {status}")
        else:
            print(f"  {test_name:<25} ⚠️  SKIPPED")
    
    if total_suites > 0:
        success_rate = (passed_suites / total_suites) * 100
        print(f"\nOverall Success Rate: {success_rate:.1f}% ({passed_suites}/{total_suites})")
        
        if passed_suites == total_suites:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Static file serving is working correctly")
            return True
        else:
            print(f"\n⚠️  {total_suites - passed_suites} test suite(s) failed")
            print("❌ Static file serving may have issues")
            return False
    else:
        print("\n❌ No test suites could be executed")
        return False

def main():
    """Main test execution function"""
    print_header("Static File Serving - Comprehensive Test Suite")
    print("Task 5: Create static file serving tests")
    print(f"Execution started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check prerequisites
    file_structure_ok = check_file_structure()
    static_files_ok = check_static_files()
    
    if not file_structure_ok:
        print("\n❌ Test file structure is incomplete. Cannot proceed.")
        sys.exit(1)
    
    if not static_files_ok:
        print("\n⚠️  Static files may be missing. Tests may fail.")
    
    # Run all test suites
    results = {}
    
    print_header("EXECUTING TEST SUITES")
    
    # Run integration tests (fastest)
    results["Integration Tests"] = run_integration_tests()
    
    # Run unittest suite (comprehensive)
    results["Unittest Suite"] = run_unittest_suite()
    
    # Run standalone tests (practical)
    results["Standalone Tests"] = run_standalone_tests()
    
    # Run pytest suite (if available)
    results["Pytest Suite"] = run_pytest_suite()
    
    # Generate summary
    overall_success = generate_summary_report(results)
    
    # Additional information
    print_header("ADDITIONAL INFORMATION")
    print("📚 Documentation: STATIC_FILE_TESTS_README.md")
    print("🔧 Test Files Created:")
    print("  - test_static_file_serving_comprehensive.py (pytest)")
    print("  - test_static_files_unittest.py (unittest)")
    print("  - test_static_files_integration.py (integration)")
    print("  - run_static_file_tests.py (standalone)")
    print("  - run_all_static_file_tests.py (this file)")
    
    print("\n💡 Usage Examples:")
    print("  python test_static_files_integration.py")
    print("  python test_static_files_unittest.py")
    print("  python run_static_file_tests.py")
    print("  python run_all_static_file_tests.py")
    
    # Exit with appropriate code
    sys.exit(0 if overall_success else 1)

if __name__ == "__main__":
    main()