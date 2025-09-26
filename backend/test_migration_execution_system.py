#!/usr/bin/env python3
"""
Test Migration Execution System

This script tests the migration execution system components to ensure
they work correctly together.

Requirements addressed:
- 3.2: Proper data migration validation
- 4.1, 4.2, 4.3: Data preservation validation
- 4.4: Migration status tracking and reporting
"""

import asyncio
import logging
import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.pre_migration_validator import PreMigrationValidator
from backend.post_migration_validator import PostMigrationValidator
from backend.migration_status_tracker import MigrationStatusTracker, MigrationPhase, MigrationState
from backend.migration_validation_runner import MigrationValidationRunner, ValidationSuite
from backend.database import SessionLocal
from backend.models import User as LegacyUser
from backend.unified_models import UnifiedUser

logger = logging.getLogger(__name__)

class MigrationExecutionSystemTest:
    """Test suite for migration execution system"""
    
    def __init__(self):
        self.temp_dir = None
        self.test_results = []
    
    def setup_test_environment(self):
        """Setup temporary test environment"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="migration_test_"))
        logger.info(f"Created test environment: {self.temp_dir}")
        
        # Create test directories
        (self.temp_dir / "migration_backups").mkdir()
        (self.temp_dir / "migration_reports").mkdir()
        (self.temp_dir / "migration_logs").mkdir()
    
    def cleanup_test_environment(self):
        """Cleanup test environment"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up test environment: {self.temp_dir}")
    
    def test_pre_migration_validator(self) -> bool:
        """Test pre-migration validator"""
        logger.info("🧪 Testing pre-migration validator...")
        
        try:
            backup_dir = str(self.temp_dir / "migration_backups")
            validator = PreMigrationValidator(backup_dir)
            
            # Run validation
            report = validator.validate_system_readiness()
            
            # Check report structure
            assert hasattr(report, 'validation_time')
            assert hasattr(report, 'overall_status')
            assert hasattr(report, 'legacy_users_count')
            assert hasattr(report, 'critical_issues')
            assert hasattr(report, 'recommendations')
            
            # Save report
            report_file = validator.save_report(report, "test_pre_migration_report.json")
            assert report_file.exists()
            
            logger.info("✅ Pre-migration validator test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Pre-migration validator test failed: {e}")
            return False
    
    def test_post_migration_validator(self) -> bool:
        """Test post-migration validator"""
        logger.info("🧪 Testing post-migration validator...")
        
        try:
            validator = PostMigrationValidator()
            
            # Run validation
            report = validator.validate_migration_success()
            
            # Check report structure
            assert hasattr(report, 'validation_time')
            assert hasattr(report, 'migration_success')
            assert hasattr(report, 'data_integrity_score')
            assert hasattr(report, 'legacy_users_count')
            assert hasattr(report, 'unified_users_count')
            assert hasattr(report, 'integrity_checks')
            
            # Save report
            report_file = validator.save_report(report, "test_post_migration_report.json")
            assert report_file.exists()
            
            logger.info("✅ Post-migration validator test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Post-migration validator test failed: {e}")
            return False
    
    def test_migration_status_tracker(self) -> bool:
        """Test migration status tracker"""
        logger.info("🧪 Testing migration status tracker...")
        
        try:
            status_file = str(self.temp_dir / "test_migration_status.json")
            tracker = MigrationStatusTracker(status_file)
            
            # Test starting migration
            migration_id = f"test_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            config = {'dry_run': True, 'validation_enabled': True}
            
            execution = tracker.start_migration(migration_id, config)
            assert execution.migration_id == migration_id
            assert execution.state == MigrationState.IN_PROGRESS
            
            # Test updating phase
            tracker.update_migration_phase(migration_id, MigrationPhase.USER_MIGRATION, {
                'users_processed': 10,
                'sessions_processed': 5
            })
            
            # Test completing migration
            tracker.complete_migration(migration_id, True, {
                'users_processed': 20,
                'sessions_processed': 15
            })
            
            # Test getting status
            current_status = tracker.get_current_status()
            assert hasattr(current_status, 'migration_state')
            assert hasattr(current_status, 'legacy_users')
            assert hasattr(current_status, 'unified_users')
            
            # Test getting history
            history = tracker.get_migration_history()
            assert len(history) > 0
            assert history[-1].migration_id == migration_id
            
            # Test statistics
            stats = tracker.get_migration_statistics()
            assert 'total_executions' in stats
            assert 'successful_executions' in stats
            
            # Test report generation
            report = tracker.generate_status_report(detailed=True)
            assert 'current_status' in report
            assert 'statistics' in report
            
            logger.info("✅ Migration status tracker test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration status tracker test failed: {e}")
            return False
    
    async def test_migration_validation_runner(self) -> bool:
        """Test migration validation runner"""
        logger.info("🧪 Testing migration validation runner...")
        
        try:
            # Create validation suite configuration
            suite_config = ValidationSuite(
                run_pre_migration=True,
                run_post_migration=True,
                run_integrity_check=True,
                save_reports=True,
                detailed_output=True,
                backup_directory=str(self.temp_dir / "migration_backups"),
                report_directory=str(self.temp_dir / "migration_reports")
            )
            
            # Create validation runner
            runner = MigrationValidationRunner(suite_config)
            
            # Run comprehensive validation
            result = await runner.run_comprehensive_validation()
            
            # Check result structure
            assert hasattr(result, 'validation_time')
            assert hasattr(result, 'overall_success')
            assert hasattr(result, 'total_checks')
            assert hasattr(result, 'passed_checks')
            assert hasattr(result, 'failed_checks')
            assert hasattr(result, 'recommendations')
            
            # Check that reports were saved
            assert len(result.report_files) > 0
            for report_file in result.report_files:
                assert Path(report_file).exists()
            
            logger.info("✅ Migration validation runner test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration validation runner test failed: {e}")
            return False
    
    def test_database_connectivity(self) -> bool:
        """Test database connectivity"""
        logger.info("🧪 Testing database connectivity...")
        
        try:
            with SessionLocal() as session:
                # Test basic query
                session.execute("SELECT 1")
                
                # Test legacy table access
                legacy_count = session.query(LegacyUser).count()
                logger.info(f"Legacy users count: {legacy_count}")
                
                # Test unified table access
                unified_count = session.query(UnifiedUser).count()
                logger.info(f"Unified users count: {unified_count}")
            
            logger.info("✅ Database connectivity test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connectivity test failed: {e}")
            return False
    
    def test_file_operations(self) -> bool:
        """Test file operations"""
        logger.info("🧪 Testing file operations...")
        
        try:
            # Test backup directory creation and write
            backup_dir = self.temp_dir / "migration_backups"
            test_file = backup_dir / "test_backup.txt"
            test_file.write_text("test backup content")
            assert test_file.exists()
            
            # Test report directory creation and write
            report_dir = self.temp_dir / "migration_reports"
            test_report = report_dir / "test_report.json"
            test_report.write_text('{"test": "report"}')
            assert test_report.exists()
            
            # Test log directory creation and write
            log_dir = self.temp_dir / "migration_logs"
            test_log = log_dir / "test_log.log"
            test_log.write_text("test log content")
            assert test_log.exists()
            
            logger.info("✅ File operations test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ File operations test failed: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all tests"""
        logger.info("🚀 Starting migration execution system tests...")
        
        self.setup_test_environment()
        
        try:
            tests = [
                ("Database Connectivity", self.test_database_connectivity()),
                ("File Operations", self.test_file_operations()),
                ("Pre-Migration Validator", self.test_pre_migration_validator()),
                ("Post-Migration Validator", self.test_post_migration_validator()),
                ("Migration Status Tracker", self.test_migration_status_tracker()),
                ("Migration Validation Runner", await self.test_migration_validation_runner()),
            ]
            
            passed_tests = 0
            total_tests = len(tests)
            
            print("\n" + "="*60)
            print("MIGRATION EXECUTION SYSTEM TEST RESULTS")
            print("="*60)
            
            for test_name, result in tests:
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"{test_name:<30} {status}")
                if result:
                    passed_tests += 1
                self.test_results.append((test_name, result))
            
            print("="*60)
            print(f"Tests passed: {passed_tests}/{total_tests}")
            print(f"Success rate: {passed_tests/total_tests:.1%}")
            
            overall_success = passed_tests == total_tests
            
            if overall_success:
                print("🎉 All tests passed! Migration execution system is working correctly.")
            else:
                print("⚠️  Some tests failed. Please review the issues above.")
            
            return overall_success
            
        finally:
            self.cleanup_test_environment()
    
    def generate_test_report(self) -> dict:
        """Generate test report"""
        return {
            'test_time': datetime.now().isoformat(),
            'total_tests': len(self.test_results),
            'passed_tests': sum(1 for _, result in self.test_results if result),
            'failed_tests': sum(1 for _, result in self.test_results if not result),
            'test_results': [
                {'test_name': name, 'passed': result}
                for name, result in self.test_results
            ]
        }

async def main():
    """Main test runner"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    test_suite = MigrationExecutionSystemTest()
    success = await test_suite.run_all_tests()
    
    # Generate report
    report = test_suite.generate_test_report()
    
    # Save test report
    report_file = Path("migration_execution_test_report.json")
    import json
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nTest report saved to: {report_file}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))