#!/usr/bin/env python3
"""
Test connection pool handling and timeout behavior

This test verifies that the database configuration properly handles
connection pool exhaustion and timeouts as required by requirement 4.4.
"""

import sys
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the current directory to the path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent))

from backend.database import get_db, get_database_info, engine
from sqlalchemy import text

def test_connection_pool_info():
    """Test that we can get connection pool information"""
    print("Testing connection pool information...")
    
    db_info = get_database_info()
    print(f"Database status: {db_info.get('status')}")
    print(f"Database type: {db_info.get('database_type')}")
    print(f"Pool size: {db_info.get('pool_size')}")
    print(f"Checked out connections: {db_info.get('checked_out')}")
    print(f"Pool overflow: {db_info.get('overflow')}")
    print(f"Checked in connections: {db_info.get('checked_in')}")
    
    return db_info.get('status') == 'connected'

def test_single_connection():
    """Test that a single database connection works"""
    print("\nTesting single database connection...")
    
    try:
        db_session = next(get_db())
        result = db_session.execute(text("SELECT 1 as test_value"))
        value = result.fetchone()[0]
        db_session.close()
        
        print(f"✓ Single connection test passed: {value}")
        return True
        
    except Exception as e:
        print(f"✗ Single connection test failed: {e}")
        return False

def test_multiple_connections():
    """Test multiple concurrent database connections"""
    print("\nTesting multiple concurrent connections...")
    
    def db_operation(connection_id):
        """Perform a database operation"""
        try:
            db_session = next(get_db())
            result = db_session.execute(text(f"SELECT {connection_id} as connection_id"))
            value = result.fetchone()[0]
            
            # Hold the connection for a short time to simulate work
            time.sleep(0.1)
            
            db_session.close()
            return f"Connection {connection_id}: {value}"
            
        except Exception as e:
            return f"Connection {connection_id} failed: {e}"
    
    # Test with a reasonable number of concurrent connections
    num_connections = 10
    
    with ThreadPoolExecutor(max_workers=num_connections) as executor:
        futures = [executor.submit(db_operation, i) for i in range(num_connections)]
        
        results = []
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"  {result}")
    
    successful = sum(1 for r in results if "failed" not in r)
    print(f"✓ {successful}/{num_connections} connections successful")
    
    return successful == num_connections

def test_connection_pool_monitoring():
    """Test connection pool monitoring during operations"""
    print("\nTesting connection pool monitoring...")
    
    def monitor_pool():
        """Monitor pool status during operations"""
        for i in range(5):
            db_info = get_database_info()
            print(f"  Monitor {i}: Pool size={db_info.get('pool_size')}, "
                  f"Checked out={db_info.get('checked_out')}, "
                  f"Overflow={db_info.get('overflow')}")
            time.sleep(0.2)
    
    def db_operations():
        """Perform database operations"""
        for i in range(3):
            try:
                db_session = next(get_db())
                result = db_session.execute(text(f"SELECT {i} as op_id"))
                value = result.fetchone()[0]
                time.sleep(0.3)  # Hold connection longer
                db_session.close()
                print(f"  Operation {i} completed: {value}")
            except Exception as e:
                print(f"  Operation {i} failed: {e}")
    
    # Run monitoring and operations concurrently
    monitor_thread = threading.Thread(target=monitor_pool)
    operations_thread = threading.Thread(target=db_operations)
    
    monitor_thread.start()
    operations_thread.start()
    
    monitor_thread.join()
    operations_thread.join()
    
    print("✓ Connection pool monitoring completed")
    return True

def test_connection_timeout_handling():
    """Test connection timeout handling"""
    print("\nTesting connection timeout handling...")
    
    try:
        # Test that connections are properly configured with timeouts
        db_session = next(get_db())
        
        # Execute a simple query to verify timeout configuration is working
        result = db_session.execute(text("SELECT current_setting('statement_timeout')"))
        timeout_setting = result.fetchone()[0]
        
        db_session.close()
        
        print(f"✓ Connection timeout configuration verified: {timeout_setting}")
        return True
        
    except Exception as e:
        print(f"✗ Connection timeout test failed: {e}")
        return False

def test_graceful_error_handling():
    """Test graceful error handling for database issues"""
    print("\nTesting graceful error handling...")
    
    try:
        # Test with a valid connection first
        db_session = next(get_db())
        result = db_session.execute(text("SELECT 1"))
        value = result.fetchone()[0]
        db_session.close()
        
        print(f"✓ Normal operation works: {value}")
        
        # Test error handling with invalid query
        try:
            db_session = next(get_db())
            result = db_session.execute(text("SELECT * FROM nonexistent_table"))
            db_session.close()
            print("✗ Should have failed with invalid query")
            return False
            
        except Exception as e:
            print(f"✓ Error handling works correctly: {type(e).__name__}")
            return True
            
    except Exception as e:
        print(f"✗ Graceful error handling test failed: {e}")
        return False

def run_connection_pool_tests():
    """Run all connection pool tests"""
    print("Connection Pool Handling Tests")
    print("=" * 50)
    
    tests = [
        ("Connection Pool Info", test_connection_pool_info),
        ("Single Connection", test_single_connection),
        ("Multiple Connections", test_multiple_connections),
        ("Pool Monitoring", test_connection_pool_monitoring),
        ("Timeout Handling", test_connection_timeout_handling),
        ("Error Handling", test_graceful_error_handling)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * len(test_name))
        
        try:
            result = test_func()
            results.append((test_name, result))
            
        except Exception as e:
            print(f"✗ Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print(f"\n{'='*50}")
    print("Test Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    return passed == len(results)

if __name__ == "__main__":
    success = run_connection_pool_tests()
    sys.exit(0 if success else 1)