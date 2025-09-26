#!/usr/bin/env python3
"""
Migration Test Suite Validation Script

This script validates that all migration tests can be imported and executed
without errors. It performs basic validation of the test suite structure.
"""

import os
import sys
import importlib
import traceback
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def validate_test_imports():
    """Validate that all test modules can be imported"""
    test_modules = [
        'tests.test_postgresql_migration',
        'tests.test_migration_performance_benchmarks',
        'tests.test_migration_data_integrity',
        'tests.conftest'
    ]
    
    results = {}
    
    for module_name in test_modules:
        try:
            module = importlib.import_module(module_name)
            results[module_name] = {
                'success': True,
                'error': None,
                'classes': []
            }
            
            # Get test classes
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    attr_name.startswith('Test') and 
                    attr.__module__ == module_name):
                    results[module_name]['classes'].append(attr_name)
                    
        except Exception as e:
            results[module_name] = {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    return results

def validate_test_structure():
    """Validate test file structure and dependencies"""
    required_files = [
        'tests/test_postgresql_migration.py',
        'tests/test_migration_performance_benchmarks.py',
        'tests/test_migration_data_integrity.py',
        'tests/conftest.py',
        'tests/MIGRATION_TESTING_README.md',
        'run_migration_tests.py'
    ]
    
    missing_files = []
    existing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            existing_files.append(file_path)
        else:
            missing_files.append(file_path)
    
    return {
        'existing_files': existing_files,
        'missing_files': missing_files,
        'all_files_present': len(missing_files) == 0
    }

def validate_dependencies():
    """Validate required dependencies are available"""
    required_modules = [
        'pytest',
        'sqlalchemy',
        'psycopg2',
        'dotenv'
    ]
    
    available_modules = []
    missing_modules = []
    
    for module_name in required_modules:
        try:
            importlib.import_module(module_name)
            available_modules.append(module_name)
        except ImportError:
            # Try alternative names
            alternatives = {
                'dotenv': 'python-dotenv',
                'psycopg2': 'psycopg2-binary'
            }
            
            if module_name in alternatives:
                try:
                    importlib.import_module(alternatives[module_name])
                    available_modules.append(f"{module_name} (as {alternatives[module_name]})")
                except ImportError:
                    missing_modules.append(module_name)
            else:
                missing_modules.append(module_name)
    
    return {
        'available_modules': available_modules,
        'missing_modules': missing_modules,
        'all_dependencies_available': len(missing_modules) == 0
    }

def validate_backend_imports():
    """Validate backend module imports"""
    backend_modules = [
        'backend.database',
        'backend.unified_models',
        'backend.models',
        'scripts.migrate_to_postgresql'
    ]
    
    results = {}
    
    for module_name in backend_modules:
        try:
            importlib.import_module(module_name)
            results[module_name] = {'success': True, 'error': None}
        except Exception as e:
            results[module_name] = {'success': False, 'error': str(e)}
    
    return results

def main():
    """Main validation function"""
    print("Migration Test Suite Validation")
    print("=" * 40)
    
    # Validate file structure
    print("\n1. Validating file structure...")
    structure_results = validate_test_structure()
    
    if structure_results['all_files_present']:
        print("✓ All required files present")
        for file_path in structure_results['existing_files']:
            print(f"  ✓ {file_path}")
    else:
        print("✗ Missing required files:")
        for file_path in structure_results['missing_files']:
            print(f"  ✗ {file_path}")
    
    # Validate dependencies
    print("\n2. Validating dependencies...")
    dep_results = validate_dependencies()
    
    if dep_results['all_dependencies_available']:
        print("✓ All dependencies available")
        for module in dep_results['available_modules']:
            print(f"  ✓ {module}")
    else:
        print("✗ Missing dependencies:")
        for module in dep_results['missing_modules']:
            print(f"  ✗ {module}")
        print("\nInstall missing dependencies with:")
        print("pip install pytest sqlalchemy psycopg2-binary python-dotenv")
    
    # Validate backend imports
    print("\n3. Validating backend module imports...")
    backend_results = validate_backend_imports()
    
    backend_success = all(result['success'] for result in backend_results.values())
    
    if backend_success:
        print("✓ All backend modules importable")
        for module in backend_results:
            print(f"  ✓ {module}")
    else:
        print("✗ Backend module import issues:")
        for module, result in backend_results.items():
            if result['success']:
                print(f"  ✓ {module}")
            else:
                print(f"  ✗ {module}: {result['error']}")
    
    # Validate test imports
    print("\n4. Validating test module imports...")
    import_results = validate_test_imports()
    
    import_success = all(result['success'] for result in import_results.values())
    
    if import_success:
        print("✓ All test modules importable")
        for module, result in import_results.items():
            print(f"  ✓ {module}")
            if result['classes']:
                for class_name in result['classes']:
                    print(f"    - {class_name}")
    else:
        print("✗ Test module import issues:")
        for module, result in import_results.items():
            if result['success']:
                print(f"  ✓ {module}")
                if result['classes']:
                    for class_name in result['classes']:
                        print(f"    - {class_name}")
            else:
                print(f"  ✗ {module}: {result['error']}")
    
    # Overall validation result
    print("\n" + "=" * 40)
    overall_success = (
        structure_results['all_files_present'] and
        dep_results['all_dependencies_available'] and
        backend_success and
        import_success
    )
    
    if overall_success:
        print("✓ Migration test suite validation PASSED")
        print("\nYou can now run the tests with:")
        print("  python run_migration_tests.py --quick")
        print("  python run_migration_tests.py --postgresql-only")
        print("  python run_migration_tests.py --performance")
        return 0
    else:
        print("✗ Migration test suite validation FAILED")
        print("\nPlease fix the issues above before running tests.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)