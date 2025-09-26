#!/usr/bin/env python3
"""
Simple Migration System Test

A simplified test to verify the core migration execution components work.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def test_imports():
    """Test that all migration components can be imported"""
    print("🧪 Testing imports...")
    
    try:
        # Test basic imports
        from backend.database import SessionLocal
        print("✅ Database import successful")
        
        from backend.migration_status_tracker import MigrationStatusTracker
        print("✅ Migration status tracker import successful")
        
        from backend.pre_migration_validator import PreMigrationValidator
        print("✅ Pre-migration validator import successful")
        
        # Test if we can create instances
        tracker = MigrationStatusTracker("test_status.json")
        print("✅ Status tracker instance created")
        
        validator = PreMigrationValidator("test_backups")
        print("✅ Pre-migration validator instance created")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_database_connection():
    """Test database connectivity"""
    print("\n🧪 Testing database connection...")
    
    try:
        from backend.database import SessionLocal
        
        with SessionLocal() as session:
            result = session.execute("SELECT 1").scalar()
            if result == 1:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection failed - unexpected result")
                return False
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_status_tracker():
    """Test migration status tracker"""
    print("\n🧪 Testing migration status tracker...")
    
    try:
        from backend.migration_status_tracker import MigrationStatusTracker, MigrationPhase, MigrationState
        from datetime import datetime
        
        # Create temporary status file
        status_file = "test_migration_status.json"
        tracker = MigrationStatusTracker(status_file)
        
        # Test getting current status
        status = tracker.get_current_status()
        print(f"✅ Current status retrieved: {status.migration_state.value}")
        
        # Test starting migration
        migration_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        config = {'dry_run': True}
        execution = tracker.start_migration(migration_id, config)
        print(f"✅ Migration started: {execution.migration_id}")
        
        # Test updating phase
        tracker.update_migration_phase(migration_id, MigrationPhase.USER_MIGRATION)
        print("✅ Migration phase updated")
        
        # Test completing migration
        tracker.complete_migration(migration_id, True)
        print("✅ Migration completed")
        
        # Cleanup
        if Path(status_file).exists():
            Path(status_file).unlink()
        
        return True
        
    except Exception as e:
        print(f"❌ Status tracker test failed: {e}")
        return False

def test_pre_migration_validator():
    """Test pre-migration validator"""
    print("\n🧪 Testing pre-migration validator...")
    
    try:
        from backend.pre_migration_validator import PreMigrationValidator
        import tempfile
        import shutil
        
        # Create temporary backup directory
        temp_dir = Path(tempfile.mkdtemp(prefix="test_backup_"))
        
        try:
            validator = PreMigrationValidator(str(temp_dir))
            
            # Test system readiness check
            report = validator.validate_system_readiness()
            print(f"✅ System readiness check completed: {report.overall_status}")
            
            # Test report structure
            assert hasattr(report, 'validation_time')
            assert hasattr(report, 'overall_status')
            assert hasattr(report, 'legacy_users_count')
            print("✅ Report structure validated")
            
            return True
            
        finally:
            # Cleanup
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        
    except Exception as e:
        print(f"❌ Pre-migration validator test failed: {e}")
        return False

def test_production_runner_help():
    """Test that production runner shows help"""
    print("\n🧪 Testing production runner help...")
    
    try:
        import subprocess
        
        result = subprocess.run([
            sys.executable, 
            "backend/production_migration_runner.py", 
            "--help"
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0 and "Production Authentication Migration System" in result.stdout:
            print("✅ Production runner help displayed correctly")
            return True
        else:
            print(f"❌ Production runner help failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Production runner test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting simple migration system tests...\n")
    
    tests = [
        ("Import Test", test_imports),
        ("Database Connection", test_database_connection),
        ("Status Tracker", test_status_tracker),
        ("Pre-Migration Validator", test_pre_migration_validator),
        ("Production Runner Help", test_production_runner_help),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            print(f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"❌ {test_name}: FAILED - {e}")
    
    print(f"\n{'='*50}")
    print(f"SIMPLE MIGRATION SYSTEM TEST RESULTS")
    print(f"{'='*50}")
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {passed/total:.1%}")
    
    if passed == total:
        print("🎉 All tests passed! Core migration system is working.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())