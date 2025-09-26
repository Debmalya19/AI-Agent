#!/usr/bin/env python3
"""
PostgreSQL Migration Test Runner

This script runs the comprehensive migration testing suite with proper
environment setup and reporting.

Usage:
    python run_migration_tests.py [options]
    
Options:
    --postgresql-only    Run only PostgreSQL-specific tests
    --performance        Run performance comparison tests
    --integration        Run full integration tests
    --quick             Run quick tests only (skip performance and integration)
    --verbose           Verbose output
    --report            Generate detailed test report
"""

import os
import sys
import argparse
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_postgresql_availability():
    """Check if PostgreSQL is available for testing"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from backend.database import create_database_engine
        postgresql_url = os.getenv("TEST_DATABASE_URL", 
                                  "postgresql://postgres:password@localhost:5432/test_ai_agent")
        
        engine = create_database_engine(postgresql_url)
        if engine:
            with engine.connect() as conn:
                from sqlalchemy import text
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                print(f"✓ PostgreSQL available: {version}")
                return True
    except Exception as e:
        print(f"✗ PostgreSQL not available: {e}")
        return False
    
    return False

def run_pytest_command(args: List[str], test_name: str) -> Dict[str, Any]:
    """Run pytest command and capture results"""
    print(f"\n{'='*60}")
    print(f"Running {test_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Run pytest with JSON report
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Parse output
        success = result.returncode == 0
        
        return {
            'test_name': test_name,
            'success': success,
            'duration': duration,
            'return_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            'test_name': test_name,
            'success': False,
            'duration': duration,
            'return_code': -1,
            'stdout': '',
            'stderr': str(e)
        }

def generate_test_report(results: List[Dict[str, Any]], output_file: str = None):
    """Generate detailed test report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_tests': len(results),
        'successful_tests': sum(1 for r in results if r['success']),
        'failed_tests': sum(1 for r in results if not r['success']),
        'total_duration': sum(r['duration'] for r in results),
        'results': results
    }
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests: {report['total_tests']}")
    print(f"Successful: {report['successful_tests']}")
    print(f"Failed: {report['failed_tests']}")
    print(f"Total Duration: {report['total_duration']:.2f}s")
    print(f"Success Rate: {(report['successful_tests']/report['total_tests']*100):.1f}%")
    
    # Print individual results
    for result in results:
        status = "✓" if result['success'] else "✗"
        print(f"{status} {result['test_name']}: {result['duration']:.2f}s")
        
        if not result['success'] and result['stderr']:
            print(f"  Error: {result['stderr'][:200]}...")
    
    # Save report to file
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nDetailed report saved to: {output_file}")
    
    return report

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="PostgreSQL Migration Test Runner")
    parser.add_argument("--postgresql-only", action="store_true", 
                       help="Run only PostgreSQL-specific tests")
    parser.add_argument("--performance", action="store_true", 
                       help="Run performance comparison tests")
    parser.add_argument("--integration", action="store_true", 
                       help="Run full integration tests")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick tests only")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Verbose output")
    parser.add_argument("--report", action="store_true", 
                       help="Generate detailed test report")
    
    args = parser.parse_args()
    
    print("PostgreSQL Migration Test Runner")
    print("=" * 40)
    
    # Check PostgreSQL availability
    postgresql_available = check_postgresql_availability()
    
    if args.postgresql_only and not postgresql_available:
        print("ERROR: PostgreSQL tests requested but PostgreSQL is not available")
        sys.exit(1)
    
    # Build test commands
    test_results = []
    base_pytest_args = ["python", "-m", "pytest", "tests/test_postgresql_migration.py"]
    
    if args.verbose:
        base_pytest_args.append("-v")
    
    # Quick tests (basic functionality)
    if not args.postgresql_only and not args.performance and not args.integration:
        quick_args = base_pytest_args + [
            "-k", "not (performance or integration or postgresql)",
            "--tb=short"
        ]
        result = run_pytest_command(quick_args, "Quick Tests (SQLite)")
        test_results.append(result)
    
    # PostgreSQL-specific tests
    if postgresql_available and (args.postgresql_only or not args.quick):
        postgresql_args = base_pytest_args + [
            "-m", "postgresql",
            "--tb=short"
        ]
        result = run_pytest_command(postgresql_args, "PostgreSQL Tests")
        test_results.append(result)
    
    # Performance tests
    if args.performance or (not args.quick and not args.postgresql_only):
        if postgresql_available:
            performance_args = base_pytest_args + [
                "-m", "performance",
                "--tb=short"
            ]
            result = run_pytest_command(performance_args, "Performance Tests")
            test_results.append(result)
        else:
            print("Skipping performance tests - PostgreSQL not available")
    
    # Integration tests
    if args.integration or (not args.quick and not args.postgresql_only):
        if postgresql_available:
            integration_args = base_pytest_args + [
                "-m", "integration",
                "--tb=short"
            ]
            result = run_pytest_command(integration_args, "Integration Tests")
            test_results.append(result)
        else:
            print("Skipping integration tests - PostgreSQL not available")
    
    # Database connection tests
    if not args.performance and not args.integration:
        connection_args = base_pytest_args + [
            "-k", "TestDatabaseConnections",
            "--tb=short"
        ]
        result = run_pytest_command(connection_args, "Database Connection Tests")
        test_results.append(result)
    
    # Model operation tests
    if not args.performance and not args.integration:
        model_args = base_pytest_args + [
            "-k", "TestModelOperations",
            "--tb=short"
        ]
        result = run_pytest_command(model_args, "Model Operation Tests")
        test_results.append(result)
    
    # Migration script tests
    if not args.performance and not args.integration:
        migration_args = base_pytest_args + [
            "-k", "TestMigrationScript",
            "--tb=short"
        ]
        result = run_pytest_command(migration_args, "Migration Script Tests")
        test_results.append(result)
    
    # Data integrity tests
    if not args.performance and not args.integration:
        integrity_args = base_pytest_args + [
            "-k", "TestDataIntegrity",
            "--tb=short"
        ]
        result = run_pytest_command(integrity_args, "Data Integrity Tests")
        test_results.append(result)
    
    # Generate report
    report_file = None
    if args.report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"migration_test_report_{timestamp}.json"
    
    report = generate_test_report(test_results, report_file)
    
    # Exit with appropriate code
    if report['failed_tests'] > 0:
        print(f"\n{report['failed_tests']} test(s) failed!")
        sys.exit(1)
    else:
        print(f"\nAll {report['successful_tests']} test(s) passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()