#!/usr/bin/env python3
"""
Comprehensive Voice Tests Runner
Runs all voice-related tests including backend integration tests and frontend test coordination
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import argparse

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ComprehensiveVoiceTestRunner:
    def __init__(self):
        self.project_root = project_root
        self.test_results = {
            'backend_tests': {},
            'frontend_tests': {},
            'integration_tests': {},
            'performance_tests': {},
            'summary': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'success_rate': 0.0,
                'duration': 0.0
            }
        }
        self.start_time = None
        self.end_time = None

    def run_all_tests(self, test_categories: List[str] = None):
        """Run all comprehensive voice tests"""
        print("🧪 Starting Comprehensive Voice Feature Tests")
        print("=" * 60)
        
        self.start_time = time.time()
        
        if not test_categories:
            test_categories = ['backend', 'integration', 'performance']
        
        try:
            if 'backend' in test_categories:
                self.run_backend_tests()
            
            if 'integration' in test_categories:
                self.run_integration_tests()
            
            if 'performance' in test_categories:
                self.run_performance_tests()
            
            # Frontend tests would be run separately via browser
            self.print_frontend_instructions()
            
        except Exception as e:
            print(f"❌ Error during test execution: {e}")
            return False
        
        finally:
            self.end_time = time.time()
            self.calculate_summary()
            self.print_results()
        
        return self.test_results['summary']['failed_tests'] == 0

    def run_backend_tests(self):
        """Run backend voice API tests"""
        print("\n📋 Running Backend Voice Tests")
        print("-" * 40)
        
        backend_test_files = [
            'tests/test_voice_models.py',
            'tests/test_voice_api.py',
            'tests/test_voice_endpoints_basic.py',
            'tests/test_voice_integration.py',
            'tests/test_voice_analytics.py',
            'tests/test_voice_error_handling.py',
            'tests/test_comprehensive_voice_suite.py'
        ]
        
        for test_file in backend_test_files:
            test_path = self.project_root / test_file
            if test_path.exists():
                print(f"\n🔍 Running {test_file}...")
                result = self.run_pytest(test_path)
                self.test_results['backend_tests'][test_file] = result
            else:
                print(f"⚠️  Test file not found: {test_file}")

    def run_integration_tests(self):
        """Run integration tests that test voice features with the full system"""
        print("\n📋 Running Integration Tests")
        print("-" * 40)
        
        integration_tests = [
            'tests/test_voice_integration.py',
            'tests/test_comprehensive_voice_suite.py'
        ]
        
        for test_file in integration_tests:
            test_path = self.project_root / test_file
            if test_path.exists():
                print(f"\n🔍 Running integration test {test_file}...")
                result = self.run_pytest(test_path, extra_args=['-v', '--tb=short'])
                self.test_results['integration_tests'][test_file] = result

    def run_performance_tests(self):
        """Run performance-specific tests"""
        print("\n📋 Running Performance Tests")
        print("-" * 40)
        
        # Run backend performance tests
        performance_test_path = self.project_root / 'tests/test_comprehensive_voice_suite.py'
        if performance_test_path.exists():
            print("\n🔍 Running backend performance tests...")
            result = self.run_pytest(
                performance_test_path, 
                extra_args=['-v', '-k', 'performance', '--tb=short']
            )
            self.test_results['performance_tests']['backend_performance'] = result

    def run_pytest(self, test_path: Path, extra_args: List[str] = None) -> Dict[str, Any]:
        """Run a pytest test file and return results"""
        cmd = ['python', '-m', 'pytest', str(test_path), '--json-report', '--json-report-file=/tmp/pytest_report.json']
        
        if extra_args:
            cmd.extend(extra_args)
        
        try:
            # Change to project directory
            original_cwd = os.getcwd()
            os.chdir(self.project_root)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Try to load JSON report
            report_data = {}
            try:
                with open('/tmp/pytest_report.json', 'r') as f:
                    report_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            
            return {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0,
                'report': report_data
            }
            
        except subprocess.TimeoutExpired:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': 'Test timed out after 5 minutes',
                'success': False,
                'report': {}
            }
        except Exception as e:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'success': False,
                'report': {}
            }
        finally:
            os.chdir(original_cwd)

    def print_frontend_instructions(self):
        """Print instructions for running frontend tests"""
        print("\n📋 Frontend Tests")
        print("-" * 40)
        print("Frontend tests should be run in a browser environment.")
        print("To run frontend tests:")
        print("1. Start a local web server in the ai-agent/frontend directory")
        print("2. Open: http://localhost:8000/tests/comprehensive-voice-tests.html")
        print("3. Click 'Run All Tests' to execute the comprehensive test suite")
        print("4. The browser will run:")
        print("   - Unit tests for voice JavaScript classes")
        print("   - End-to-end voice conversation flow tests")
        print("   - Accessibility tests for screen reader compatibility")
        print("   - Performance tests for various network conditions")

    def calculate_summary(self):
        """Calculate overall test summary"""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        # Count backend tests
        for test_file, result in self.test_results['backend_tests'].items():
            if result.get('report') and 'summary' in result['report']:
                summary = result['report']['summary']
                total_tests += summary.get('total', 0)
                passed_tests += summary.get('passed', 0)
                failed_tests += summary.get('failed', 0)
            elif result.get('success'):
                # Fallback if no detailed report
                total_tests += 1
                passed_tests += 1
            else:
                total_tests += 1
                failed_tests += 1
        
        # Count integration tests
        for test_file, result in self.test_results['integration_tests'].items():
            if result.get('report') and 'summary' in result['report']:
                summary = result['report']['summary']
                total_tests += summary.get('total', 0)
                passed_tests += summary.get('passed', 0)
                failed_tests += summary.get('failed', 0)
            elif result.get('success'):
                total_tests += 1
                passed_tests += 1
            else:
                total_tests += 1
                failed_tests += 1
        
        # Count performance tests
        for test_file, result in self.test_results['performance_tests'].items():
            if result.get('report') and 'summary' in result['report']:
                summary = result['report']['summary']
                total_tests += summary.get('total', 0)
                passed_tests += summary.get('passed', 0)
                failed_tests += summary.get('failed', 0)
            elif result.get('success'):
                total_tests += 1
                passed_tests += 1
            else:
                total_tests += 1
                failed_tests += 1
        
        duration = (self.end_time - self.start_time) if self.end_time and self.start_time else 0
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        self.test_results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': success_rate,
            'duration': duration
        }

    def print_results(self):
        """Print comprehensive test results"""
        print("\n" + "=" * 60)
        print("🏁 COMPREHENSIVE VOICE TEST RESULTS")
        print("=" * 60)
        
        summary = self.test_results['summary']
        
        print(f"\n📊 Overall Summary:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']} ✅")
        print(f"   Failed: {summary['failed_tests']} ❌")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Duration: {summary['duration']:.2f}s")
        
        # Backend test results
        if self.test_results['backend_tests']:
            print(f"\n📋 Backend Test Results:")
            for test_file, result in self.test_results['backend_tests'].items():
                status = "✅" if result['success'] else "❌"
                print(f"   {status} {test_file}")
                if not result['success'] and result['stderr']:
                    print(f"      Error: {result['stderr'][:100]}...")
        
        # Integration test results
        if self.test_results['integration_tests']:
            print(f"\n📋 Integration Test Results:")
            for test_file, result in self.test_results['integration_tests'].items():
                status = "✅" if result['success'] else "❌"
                print(f"   {status} {test_file}")
        
        # Performance test results
        if self.test_results['performance_tests']:
            print(f"\n📋 Performance Test Results:")
            for test_file, result in self.test_results['performance_tests'].items():
                status = "✅" if result['success'] else "❌"
                print(f"   {status} {test_file}")
        
        # Final status
        overall_status = "PASSED" if summary['failed_tests'] == 0 else "FAILED"
        status_icon = "🎉" if summary['failed_tests'] == 0 else "💥"
        
        print(f"\n{status_icon} Overall Status: {overall_status}")
        
        if summary['failed_tests'] > 0:
            print(f"\n⚠️  {summary['failed_tests']} test(s) failed. Review the results above for details.")
        else:
            print(f"\n🎊 All backend tests passed! Voice features are working correctly.")
        
        print("=" * 60)

    def export_results(self, output_file: str = None):
        """Export test results to JSON file"""
        if not output_file:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"voice_test_results_{timestamp}.json"
        
        output_path = self.project_root / output_file
        
        with open(output_path, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n📄 Test results exported to: {output_path}")
        return output_path

def main():
    parser = argparse.ArgumentParser(description='Run comprehensive voice feature tests')
    parser.add_argument(
        '--categories',
        nargs='+',
        choices=['backend', 'integration', 'performance'],
        default=['backend', 'integration', 'performance'],
        help='Test categories to run'
    )
    parser.add_argument(
        '--export',
        type=str,
        help='Export results to JSON file'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    runner = ComprehensiveVoiceTestRunner()
    
    try:
        success = runner.run_all_tests(args.categories)
        
        if args.export:
            runner.export_results(args.export)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()