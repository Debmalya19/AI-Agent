"""
Comprehensive integration test runner for intelligent chat UI.

Runs all integration tests and generates performance benchmarks and reports.
"""

import pytest
import time
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any
import psutil


class IntegrationTestRunner:
    """Runner for comprehensive integration tests."""
    
    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
        self.start_time = None
        self.end_time = None
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests and collect results."""
        print("🚀 Starting Comprehensive Integration Tests")
        print("=" * 60)
        
        self.start_time = time.time()
        initial_memory = self._get_memory_usage()
        
        # Test suites to run
        test_suites = [
            {
                "name": "Complete Conversation Flows",
                "file": "test_comprehensive_integration.py",
                "classes": [
                    "TestCompleteConversationFlows",
                    "TestToolChainExecution", 
                    "TestContextContinuity",
                    "TestPerformanceBenchmarks"
                ]
            },
            {
                "name": "Response Rendering Integration",
                "file": "test_response_rendering_integration.py",
                "classes": [
                    "TestResponseRenderingIntegration",
                    "TestUIStateTransitions",
                    "TestRenderingPerformance"
                ]
            },
            {
                "name": "Context & Performance Integration",
                "file": "test_context_performance_integration.py",
                "classes": [
                    "TestContextWindowManagement",
                    "TestPerformanceOptimization",
                    "TestMemoryUsageOptimization",
                    "TestCachingPerformance"
                ]
            }
        ]
        
        # Run each test suite
        for suite in test_suites:
            print(f"\n📋 Running {suite['name']}")
            print("-" * 40)
            
            suite_results = self._run_test_suite(suite)
            self.test_results[suite['name']] = suite_results
            
            # Print suite summary
            self._print_suite_summary(suite['name'], suite_results)
        
        self.end_time = time.time()
        final_memory = self._get_memory_usage()
        
        # Collect overall performance metrics
        self.performance_metrics = {
            "total_execution_time": self.end_time - self.start_time,
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": final_memory - initial_memory,
            "timestamp": datetime.now().isoformat()
        }
        
        # Generate comprehensive report
        report = self._generate_report()
        
        print("\n" + "=" * 60)
        print("🎉 Integration Tests Complete!")
        self._print_overall_summary()
        
        return report
    
    def _run_test_suite(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        """Run a specific test suite."""
        suite_start_time = time.time()
        
        results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "execution_time": 0,
            "class_results": {}
        }
        
        for test_class in suite["classes"]:
            print(f"  🧪 Testing {test_class}")
            
            # Run specific test class
            class_results = self._run_test_class(suite["file"], test_class)
            results["class_results"][test_class] = class_results
            
            # Aggregate results
            results["passed"] += class_results.get("passed", 0)
            results["failed"] += class_results.get("failed", 0)
            results["skipped"] += class_results.get("skipped", 0)
            results["errors"].extend(class_results.get("errors", []))
        
        results["execution_time"] = time.time() - suite_start_time
        return results
    
    def _run_test_class(self, test_file: str, test_class: str) -> Dict[str, Any]:
        """Run a specific test class."""
        try:
            # Use pytest to run specific test class
            test_path = f"{test_file}::{test_class}"
            
            # Capture pytest results
            result = pytest.main([
                test_path,
                "-v",
                "--tb=short",
                "-q",
                "--disable-warnings"
            ])
            
            # Parse result code
            if result == 0:
                return {"passed": 1, "failed": 0, "skipped": 0, "errors": []}
            elif result == 1:
                return {"passed": 0, "failed": 1, "skipped": 0, "errors": [f"Test failures in {test_class}"]}
            elif result == 2:
                return {"passed": 0, "failed": 0, "skipped": 0, "errors": [f"Test interrupted in {test_class}"]}
            elif result == 3:
                return {"passed": 0, "failed": 0, "skipped": 0, "errors": [f"Internal error in {test_class}"]}
            elif result == 4:
                return {"passed": 0, "failed": 0, "skipped": 0, "errors": [f"Usage error in {test_class}"]}
            elif result == 5:
                return {"passed": 0, "failed": 0, "skipped": 1, "errors": []}
            else:
                return {"passed": 0, "failed": 1, "skipped": 0, "errors": [f"Unknown result code {result} for {test_class}"]}
                
        except Exception as e:
            return {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "errors": [f"Exception running {test_class}: {str(e)}"]
            }
    
    def _print_suite_summary(self, suite_name: str, results: Dict[str, Any]):
        """Print summary for a test suite."""
        total_tests = results["passed"] + results["failed"] + results["skipped"]
        
        print(f"    ✅ Passed: {results['passed']}")
        print(f"    ❌ Failed: {results['failed']}")
        print(f"    ⏭️  Skipped: {results['skipped']}")
        print(f"    ⏱️  Time: {results['execution_time']:.2f}s")
        
        if results["errors"]:
            print(f"    🚨 Errors: {len(results['errors'])}")
            for error in results["errors"][:3]:  # Show first 3 errors
                print(f"       - {error}")
            if len(results["errors"]) > 3:
                print(f"       ... and {len(results['errors']) - 3} more")
    
    def _print_overall_summary(self):
        """Print overall test summary."""
        total_passed = sum(suite["passed"] for suite in self.test_results.values())
        total_failed = sum(suite["failed"] for suite in self.test_results.values())
        total_skipped = sum(suite["skipped"] for suite in self.test_results.values())
        total_tests = total_passed + total_failed + total_skipped
        
        print(f"📊 Overall Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {total_passed}")
        print(f"   ❌ Failed: {total_failed}")
        print(f"   ⏭️  Skipped: {total_skipped}")
        print(f"   ⏱️  Total Time: {self.performance_metrics['total_execution_time']:.2f}s")
        print(f"   💾 Memory Usage: {self.performance_metrics['memory_increase_mb']:.1f}MB increase")
        
        # Success rate
        if total_tests > 0:
            success_rate = (total_passed / total_tests) * 100
            print(f"   📈 Success Rate: {success_rate:.1f}%")
            
            if success_rate >= 90:
                print("   🎉 Excellent test coverage!")
            elif success_rate >= 75:
                print("   👍 Good test coverage")
            else:
                print("   ⚠️  Test coverage needs improvement")
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        return {
            "summary": {
                "total_execution_time": self.performance_metrics["total_execution_time"],
                "memory_usage": {
                    "initial_mb": self.performance_metrics["initial_memory_mb"],
                    "final_mb": self.performance_metrics["final_memory_mb"],
                    "increase_mb": self.performance_metrics["memory_increase_mb"]
                },
                "timestamp": self.performance_metrics["timestamp"]
            },
            "test_results": self.test_results,
            "performance_metrics": self.performance_metrics,
            "system_info": self._get_system_info()
        }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        return {
            "python_version": sys.version,
            "platform": sys.platform,
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
            "memory_available_gb": psutil.virtual_memory().available / 1024 / 1024 / 1024
        }
    
    def save_report(self, filename: str = None) -> str:
        """Save test report to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"integration_test_report_{timestamp}.json"
        
        report = self._generate_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 Report saved to: {filename}")
        return filename


def run_performance_benchmarks():
    """Run specific performance benchmarks."""
    print("\n🏃‍♂️ Running Performance Benchmarks")
    print("=" * 40)
    
    benchmarks = [
        {
            "name": "Response Time Benchmark",
            "test": "test_comprehensive_integration.py::TestPerformanceBenchmarks::test_response_time_benchmarks"
        },
        {
            "name": "Memory Usage Benchmark", 
            "test": "test_comprehensive_integration.py::TestPerformanceBenchmarks::test_memory_usage_benchmarks"
        },
        {
            "name": "Concurrent Load Benchmark",
            "test": "test_comprehensive_integration.py::TestPerformanceBenchmarks::test_concurrent_load_performance"
        },
        {
            "name": "Context Performance Benchmark",
            "test": "test_context_performance_integration.py::TestPerformanceOptimization::test_concurrent_performance_optimization"
        }
    ]
    
    for benchmark in benchmarks:
        print(f"\n🎯 {benchmark['name']}")
        print("-" * 30)
        
        start_time = time.time()
        result = pytest.main([
            benchmark["test"],
            "-v",
            "--tb=short",
            "-s"  # Show print statements
        ])
        execution_time = time.time() - start_time
        
        status = "✅ PASSED" if result == 0 else "❌ FAILED"
        print(f"   {status} ({execution_time:.2f}s)")


def main():
    """Main entry point for integration tests."""
    print("🧪 Intelligent Chat UI - Integration Test Suite")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("intelligent_chat"):
        print("❌ Error: intelligent_chat directory not found")
        print("   Please run from the ai-agent directory")
        return 1
    
    # Initialize test runner
    runner = IntegrationTestRunner()
    
    try:
        # Run all integration tests
        report = runner.run_all_tests()
        
        # Save report
        report_file = runner.save_report()
        
        # Run performance benchmarks
        run_performance_benchmarks()
        
        # Determine exit code based on results
        total_failed = sum(suite["failed"] for suite in runner.test_results.values())
        total_errors = sum(len(suite["errors"]) for suite in runner.test_results.values())
        
        if total_failed > 0 or total_errors > 0:
            print(f"\n❌ Tests completed with {total_failed} failures and {total_errors} errors")
            return 1
        else:
            print(f"\n✅ All tests passed successfully!")
            return 0
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)