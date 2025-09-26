#!/usr/bin/env python3
"""
Test Script for Comprehensive Error Handling Integration

This script tests the authentication error handling, security logging,
and migration error recovery mechanisms.

Requirements: 1.3, 5.1, 5.2, 5.3, 5.4
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add the parent directory to the path so we can import backend modules
sys.path.append(str(Path(__file__).parent.parent))

from backend.comprehensive_error_integration import (
    ComprehensiveErrorManager, get_error_manager
)
from backend.auth_error_handler import AuthEventType, SecurityLevel
from backend.migration_error_handler import MigrationPhase, MigrationErrorType


async def test_authentication_error_handling():
    """Test authentication error handling and security logging"""
    print("\n🔐 Testing Authentication Error Handling...")
    
    error_manager = get_error_manager()
    
    # Test 1: Simulate login failure
    print("  Test 1: Simulating login failure...")
    try:
        raise Exception("Invalid username or password")
    except Exception as e:
        result = await error_manager.handle_authentication_error(
            error=e,
            user_identifier="test_user",
            auth_type="login"
        )
        print(f"    ✅ Login failure handled: {result['message']}")
    
    # Test 2: Check account lockout after multiple failures
    print("  Test 2: Testing account lockout mechanism...")
    for i in range(6):  # Exceed the default limit of 5
        try:
            raise Exception("Invalid password")
        except Exception as e:
            result = await error_manager.handle_authentication_error(
                error=e,
                user_identifier="lockout_test_user",
                auth_type="login"
            )
            if result.get('should_lock_account'):
                print(f"    ✅ Account locked after {i+1} attempts")
                break
    
    # Test 3: Check if account is locked
    is_locked = error_manager.is_account_locked("lockout_test_user")
    print(f"    ✅ Account lock status: {'LOCKED' if is_locked else 'UNLOCKED'}")
    
    # Test 4: Unlock account
    if is_locked:
        error_manager.unlock_account("lockout_test_user")
        print("    ✅ Account manually unlocked")
    
    # Test 5: Log security events
    print("  Test 5: Logging security events...")
    await error_manager.log_security_event(
        event_type=AuthEventType.ADMIN_ACCESS_GRANTED,
        user_identifier="admin_user",
        user_id=1,
        success=True,
        security_level=SecurityLevel.MEDIUM
    )
    print("    ✅ Security event logged")


async def test_migration_error_handling():
    """Test migration error handling and recovery"""
    print("\n🔄 Testing Migration Error Handling...")
    
    error_manager = get_error_manager()
    
    # Test 1: Simulate migration validation error
    print("  Test 1: Simulating migration validation error...")
    try:
        raise ValueError("Duplicate user_id found during validation")
    except Exception as e:
        result = await error_manager.handle_migration_error(
            error=e,
            phase=MigrationPhase.VALIDATION,
            affected_records=5
        )
        print(f"    ✅ Validation error handled: {result['message']}")
    
    # Test 2: Simulate data migration error
    print("  Test 2: Simulating data migration error...")
    try:
        raise Exception("Database connection lost during user migration")
    except Exception as e:
        result = await error_manager.handle_migration_error(
            error=e,
            phase=MigrationPhase.USER_MIGRATION,
            affected_records=150
        )
        print(f"    ✅ Migration error handled: {result['message']}")
        print(f"    Recovery possible: {result['recovery_possible']}")
        print(f"    Rollback required: {result['rollback_required']}")


def test_error_statistics():
    """Test error statistics and monitoring"""
    print("\n📊 Testing Error Statistics...")
    
    error_manager = get_error_manager()
    
    # Get comprehensive status
    status = error_manager.get_comprehensive_status()
    print(f"  ✅ Total authentication errors: {status['error_statistics']['auth_errors']}")
    print(f"  ✅ Total migration errors: {status['error_statistics']['migration_errors']}")
    print(f"  ✅ Recovery attempts: {status['error_statistics']['recovery_attempts']}")
    
    # Get security report
    security_report = error_manager.get_security_report()
    print(f"  ✅ Security report generated at: {security_report['report_timestamp']}")
    print(f"  ✅ Locked accounts: {security_report['authentication_security']['locked_accounts']}")


async def test_error_recovery():
    """Test error recovery mechanisms"""
    print("\n🔧 Testing Error Recovery Mechanisms...")
    
    error_manager = get_error_manager()
    
    # Test circuit breaker functionality
    print("  Test 1: Testing circuit breaker status...")
    status = error_manager.get_comprehensive_status()
    circuit_breakers = status.get('circuit_breakers', {})
    
    for name, breaker_status in circuit_breakers.items():
        state = "OPEN" if breaker_status.get('is_open', False) else "CLOSED"
        print(f"    Circuit breaker '{name}': {state}")
    
    print("  ✅ Circuit breaker status checked")


async def test_logging_system():
    """Test the logging system"""
    print("\n📝 Testing Logging System...")
    
    # Check if log files are created
    log_dir = Path("logs")
    
    expected_logs = [
        "security_events.log",
        "migration_errors.log",
        "unified_errors.log"
    ]
    
    for log_file in expected_logs:
        log_path = log_dir / log_file
        if log_path.exists():
            print(f"  ✅ Log file exists: {log_file}")
        else:
            print(f"  ⚠️ Log file missing: {log_file}")


async def main():
    """Run all error handling tests"""
    print("🚀 Starting Comprehensive Error Handling Tests")
    print("=" * 60)
    
    try:
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Run tests
        await test_authentication_error_handling()
        await test_migration_error_handling()
        test_error_statistics()
        await test_error_recovery()
        await test_logging_system()
        
        print("\n" + "=" * 60)
        print("✅ All error handling tests completed successfully!")
        
        # Display final statistics
        error_manager = get_error_manager()
        final_status = error_manager.get_comprehensive_status()
        
        print(f"\n📈 Final Statistics:")
        print(f"  Authentication errors: {final_status['error_statistics']['auth_errors']}")
        print(f"  Migration errors: {final_status['error_statistics']['migration_errors']}")
        print(f"  System errors: {final_status['error_statistics']['system_errors']}")
        print(f"  Recovery attempts: {final_status['error_statistics']['recovery_attempts']}")
        print(f"  Successful recoveries: {final_status['error_statistics']['successful_recoveries']}")
        
        recovery_rate = 0
        if final_status['error_statistics']['recovery_attempts'] > 0:
            recovery_rate = (
                final_status['error_statistics']['successful_recoveries'] / 
                final_status['error_statistics']['recovery_attempts']
            )
        
        print(f"  Recovery success rate: {recovery_rate:.2%}")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)