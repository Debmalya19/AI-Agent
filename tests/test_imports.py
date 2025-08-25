#!/usr/bin/env python3
"""
Test script to isolate import issues
"""

import time
import sys

def test_import(module_name):
    """Test importing a specific module"""
    print(f"Testing import of {module_name}...")
    start_time = time.time()
    try:
        __import__(module_name)
        elapsed = time.time() - start_time
        print(f"✓ {module_name} imported successfully in {elapsed:.2f}s")
        return True
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"✗ {module_name} import failed in {elapsed:.2f}s: {e}")
        return False

def main():
    """Test all imports step by step"""
    # Test the remaining modules that weren't tested before
    modules_to_test = [
        "database",
        "models", 
        "db_utils",
        "enhanced_rag_orchestrator",
        "tools",
        "customer_db_tool"
    ]
    
    print("Testing remaining imports...")
    print("=" * 50)
    
    for module in modules_to_test:
        if not test_import(module):
            print(f"Stopping at failed import: {module}")
            break
        time.sleep(0.1)  # Small delay between imports
    
    print("=" * 50)
    print("Import testing completed.")

if __name__ == "__main__":
    main()
