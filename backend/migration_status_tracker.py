#!/usr/bin/env python3
"""
Migration Status Tracking System

This module provides comprehensive migration status tracking and reporting
functionality to monitor migration progress and maintain execution history.

Requirements addressed:
- 4.4: Migration status tracking and reporting functionality
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.database import SessionLocal
from backend.models import User as LegacyUser, UserSession as LegacyUserSession
from backend.unified_models import UnifiedUser, UnifiedUserSession

logger = logging.getLogger(__name__)

class MigrationPhase(Enum):
    """Migration phases for tracking progress"""
    NOT_STARTED = "not_started"
    PRE_VALIDATION = "pre_validation"
    BACKUP_CREATION = "backup_creation"
    USER_MIGRATION = "user_migration"
    SESSION_MIGRATION = "session_migration"
    POST_VALIDATION = "post_validation"
    CLEANUP = "cleanup"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class MigrationState(Enum):
    """Overall migration states"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    ROLLED_BACK = "rolled_back"

@dataclass
class MigrationExecution:
    """Represents a single migration execution"""
    migration_id: str
    start_time: datetime
    end_time: Optional[datetime]
    phase: MigrationPhase
    state: MigrationState
    success: bool
    
    # Statistics
    users_processed: int = 0
    sessions_processed: int = 0
    errors_count: int = 0
    warnings_count: int = 0
    
    # Configuration
    dry_run: bool = False
    backup_created: bool = False
    validation_enabled: bool = True
    
    # Results
    backup_path: Optional[str] = None
    report_path: Optional[str] = None
    log_path: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'migration_id': self.migration_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'phase': self.phase.value,
            'state': self.state.value,
            'success': self.success,
            'users_processed': self.users_processed,
            'sessions_processed': self.sessions_processed,
            'errors_count': self.errors_count,
            'warnings_count': self.warnings_count,
            'dry_run': self.dry_run,
            'backup_created': self.backup_created,
            'validation_enabled': self.validation_enabled,
            'backup_path': self.backup_path,
            'report_path': self.report_path,
            'log_path': self.log_path,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MigrationExecution':
        """Create from dictionary"""
        return cls(
            migration_id=data['migration_id'],
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']) if data['end_time'] else None,
            phase=MigrationPhase(data['phase']),
            state=MigrationState(data['state']),
            success=data['success'],
            users_processed=data.get('users_processed', 0),
            sessions_processed=data.get('sessions_processed', 0),
            errors_count=data.get('errors_count', 0),
            warnings_count=data.get('warnings_count', 0),
            dry_run=data.get('dry_run', False),
            backup_created=data.get('backup_created', False),
            validation_enabled=data.get('validation_enabled', True),
            backup_path=data.get('backup_path'),
            report_path=data.get('report_path'),
            log_path=data.get('log_path'),
            error_message=data.get('error_message')
        )

@dataclass
class SystemStatus:
    """Current system status"""
    timestamp: datetime
    
    # Database counts
    legacy_users: int
    legacy_sessions: int
    unified_users: int
    unified_sessions: int
    migrated_users: int
    migrated_sessions: int
    
    # Migration state
    migration_state: MigrationState
    current_phase: MigrationPhase
    last_migration_id: Optional[str]
    
    # System health
    database_accessible: bool
    tables_exist: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'legacy_users': self.legacy_users,
            'legacy_sessions': self.legacy_sessions,
            'unified_users': self.unified_users,
            'unified_sessions': self.unified_sessions,
            'migrated_users': self.migrated_users,
            'migrated_sessions': self.migrated_sessions,
            'migration_state': self.migration_state.value,
            'current_phase': self.current_phase.value,
            'last_migration_id': self.last_migration_id,
            'database_accessible': self.database_accessible,
            'tables_exist': self.tables_exist
        }

class MigrationStatusTracker:
    """Comprehensive migration status tracking system"""
    
    def __init__(self, status_file: str = "migration_status.json"):
        self.status_file = Path(status_file)
        self.status_data = self._load_status_data()
    
    def _load_status_data(self) -> Dict[str, Any]:
        """Load existing status data"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load status file: {e}")
        
        return {
            'version': '1.0',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'current_phase': MigrationPhase.NOT_STARTED.value,
            'current_state': MigrationState.NOT_STARTED.value,
            'executions': [],
            'last_updated': None
        }
    
    def _save_status_data(self):
        """Save status data to file"""
        try:
            self.status_data['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            # Ensure directory exists
            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.status_file, 'w') as f:
                json.dump(self.status_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save status file: {e}")
    
    def start_migration(self, migration_id: str, config: Dict[str, Any]) -> MigrationExecution:
        """Start tracking a new migration"""
        execution = MigrationExecution(
            migration_id=migration_id,
            start_time=datetime.now(timezone.utc),
            end_time=None,
            phase=MigrationPhase.PRE_VALIDATION,
            state=MigrationState.IN_PROGRESS,
            success=False,
            dry_run=config.get('dry_run', False),
            validation_enabled=config.get('validation_enabled', True)
        )
        
        # Update status
        self.status_data['current_phase'] = execution.phase.value
        self.status_data['current_state'] = execution.state.value
        self.status_data['executions'].append(execution.to_dict())
        
        self._save_status_data()
        
        logger.info(f"Started tracking migration: {migration_id}")
        return execution
    
    def update_migration_phase(self, migration_id: str, phase: MigrationPhase, 
                             details: Optional[Dict[str, Any]] = None):
        """Update migration phase"""
        execution = self._find_execution(migration_id)
        if execution:
            execution['phase'] = phase.value
            
            if details:
                execution.update(details)
            
            # Update current status
            self.status_data['current_phase'] = phase.value
            
            self._save_status_data()
            logger.info(f"Migration {migration_id} phase updated to: {phase.value}")
    
    def complete_migration(self, migration_id: str, success: bool, 
                         final_stats: Optional[Dict[str, Any]] = None):
        """Complete migration tracking"""
        execution = self._find_execution(migration_id)
        if execution:
            execution['end_time'] = datetime.now(timezone.utc).isoformat()
            execution['success'] = success
            execution['state'] = MigrationState.COMPLETED.value if success else MigrationState.FAILED.value
            execution['phase'] = MigrationPhase.COMPLETED.value if success else MigrationPhase.FAILED.value
            
            if final_stats:
                execution.update(final_stats)
            
            # Update current status
            self.status_data['current_state'] = execution['state']
            self.status_data['current_phase'] = execution['phase']
            
            self._save_status_data()
            
            status = "completed successfully" if success else "failed"
            logger.info(f"Migration {migration_id} {status}")
    
    def rollback_migration(self, migration_id: str, rollback_details: Dict[str, Any]):
        """Mark migration as rolled back"""
        execution = self._find_execution(migration_id)
        if execution:
            execution['state'] = MigrationState.ROLLED_BACK.value
            execution['phase'] = MigrationPhase.ROLLED_BACK.value
            execution.update(rollback_details)
            
            # Update current status
            self.status_data['current_state'] = MigrationState.ROLLED_BACK.value
            self.status_data['current_phase'] = MigrationPhase.ROLLED_BACK.value
            
            self._save_status_data()
            logger.info(f"Migration {migration_id} marked as rolled back")
    
    def get_current_status(self) -> SystemStatus:
        """Get comprehensive current system status"""
        try:
            with SessionLocal() as session:
                # Get database counts
                legacy_users = session.query(LegacyUser).count()
                legacy_sessions = session.query(LegacyUserSession).count()
                unified_users = session.query(UnifiedUser).count()
                unified_sessions = session.query(UnifiedUserSession).count()
                
                # Count migrated items
                migrated_users = session.query(UnifiedUser).filter(
                    UnifiedUser.migrated_from_legacy == True
                ).count()
                
                migrated_sessions = session.query(UnifiedUserSession).filter(
                    UnifiedUserSession.migrated_from_legacy == True
                ).count()
                
                database_accessible = True
                tables_exist = True
                
        except Exception as e:
            logger.error(f"Failed to get database status: {e}")
            legacy_users = legacy_sessions = unified_users = unified_sessions = 0
            migrated_users = migrated_sessions = 0
            database_accessible = False
            tables_exist = False
        
        # Determine migration state
        migration_state = self._determine_migration_state(
            legacy_users, unified_users, migrated_users
        )
        
        # Get current phase
        current_phase = MigrationPhase(self.status_data.get('current_phase', MigrationPhase.NOT_STARTED.value))
        
        # Get last migration ID
        last_migration_id = None
        if self.status_data['executions']:
            last_migration_id = self.status_data['executions'][-1]['migration_id']
        
        return SystemStatus(
            timestamp=datetime.now(timezone.utc),
            legacy_users=legacy_users,
            legacy_sessions=legacy_sessions,
            unified_users=unified_users,
            unified_sessions=unified_sessions,
            migrated_users=migrated_users,
            migrated_sessions=migrated_sessions,
            migration_state=migration_state,
            current_phase=current_phase,
            last_migration_id=last_migration_id,
            database_accessible=database_accessible,
            tables_exist=tables_exist
        )
    
    def get_migration_history(self, limit: Optional[int] = None) -> List[MigrationExecution]:
        """Get migration execution history"""
        executions = []
        
        execution_data = self.status_data['executions']
        if limit:
            execution_data = execution_data[-limit:]
        
        for data in execution_data:
            try:
                executions.append(MigrationExecution.from_dict(data))
            except Exception as e:
                logger.warning(f"Failed to parse execution data: {e}")
        
        return executions
    
    def get_migration_statistics(self) -> Dict[str, Any]:
        """Get migration statistics"""
        executions = self.get_migration_history()
        
        stats = {
            'total_executions': len(executions),
            'successful_executions': sum(1 for e in executions if e.success),
            'failed_executions': sum(1 for e in executions if not e.success),
            'dry_run_executions': sum(1 for e in executions if e.dry_run),
            'total_users_processed': sum(e.users_processed for e in executions),
            'total_sessions_processed': sum(e.sessions_processed for e in executions),
            'total_errors': sum(e.errors_count for e in executions),
            'total_warnings': sum(e.warnings_count for e in executions)
        }
        
        if executions:
            # Calculate success rate
            stats['success_rate'] = stats['successful_executions'] / stats['total_executions']
            
            # Get last execution info
            last_execution = executions[-1]
            stats['last_execution'] = {
                'migration_id': last_execution.migration_id,
                'success': last_execution.success,
                'start_time': last_execution.start_time.isoformat(),
                'phase': last_execution.phase.value,
                'state': last_execution.state.value
            }
        else:
            stats['success_rate'] = 0.0
            stats['last_execution'] = None
        
        return stats
    
    def _find_execution(self, migration_id: str) -> Optional[Dict[str, Any]]:
        """Find execution by migration ID"""
        for execution in self.status_data['executions']:
            if execution['migration_id'] == migration_id:
                return execution
        return None
    
    def _determine_migration_state(self, legacy_users: int, unified_users: int, 
                                 migrated_users: int) -> MigrationState:
        """Determine current migration state based on counts"""
        if unified_users == 0:
            return MigrationState.NOT_STARTED
        elif migrated_users == 0 and unified_users > 0:
            return MigrationState.NOT_STARTED  # Unified users exist but not from migration
        elif migrated_users < legacy_users:
            return MigrationState.PARTIAL
        elif migrated_users >= legacy_users:
            return MigrationState.COMPLETED
        else:
            return MigrationState.PARTIAL
    
    def generate_status_report(self, detailed: bool = False) -> Dict[str, Any]:
        """Generate comprehensive status report"""
        current_status = self.get_current_status()
        statistics = self.get_migration_statistics()
        
        report = {
            'report_generated': datetime.now(timezone.utc).isoformat(),
            'current_status': current_status.to_dict(),
            'statistics': statistics
        }
        
        if detailed:
            # Add execution history
            history = self.get_migration_history(limit=10)  # Last 10 executions
            report['recent_executions'] = [exec.to_dict() for exec in history]
            
            # Add system health checks
            report['system_health'] = {
                'database_accessible': current_status.database_accessible,
                'tables_exist': current_status.tables_exist,
                'data_consistency': self._check_data_consistency()
            }
        
        return report
    
    def _check_data_consistency(self) -> Dict[str, Any]:
        """Basic data consistency check"""
        try:
            with SessionLocal() as session:
                # Check for orphaned sessions
                orphaned_legacy_sessions = session.query(LegacyUserSession).filter(
                    ~LegacyUserSession.user_id.in_(
                        session.query(LegacyUser.user_id)
                    )
                ).count()
                
                orphaned_unified_sessions = session.query(UnifiedUserSession).filter(
                    ~UnifiedUserSession.user_id.in_(
                        session.query(UnifiedUser.id)
                    )
                ).count()
                
                return {
                    'orphaned_legacy_sessions': orphaned_legacy_sessions,
                    'orphaned_unified_sessions': orphaned_unified_sessions,
                    'consistency_ok': orphaned_legacy_sessions == 0 and orphaned_unified_sessions == 0
                }
                
        except Exception as e:
            return {
                'error': str(e),
                'consistency_ok': False
            }
    
    def save_report(self, report: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """Save status report to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"migration_status_report_{timestamp}.json"
        
        report_dir = Path("migration_reports")
        report_dir.mkdir(exist_ok=True)
        report_file = report_dir / filename
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Status report saved to {report_file}")
        return report_file

def main():
    """CLI entry point for migration status tracking"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration status tracking tool")
    parser.add_argument('--status-file', default='migration_status.json', 
                       help='Status file path')
    parser.add_argument('--detailed', action='store_true', 
                       help='Show detailed status information')
    parser.add_argument('--save-report', action='store_true', 
                       help='Save status report to file')
    parser.add_argument('--history', type=int, metavar='N',
                       help='Show last N migration executions')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create tracker
    tracker = MigrationStatusTracker(args.status_file)
    
    # Get current status
    current_status = tracker.get_current_status()
    statistics = tracker.get_migration_statistics()
    
    # Print status
    print("\n" + "="*60)
    print("MIGRATION STATUS TRACKER")
    print("="*60)
    print(f"Timestamp: {current_status.timestamp}")
    print(f"Migration State: {current_status.migration_state.value}")
    print(f"Current Phase: {current_status.current_phase.value}")
    print(f"Database Accessible: {'✅' if current_status.database_accessible else '❌'}")
    
    print(f"\nDATA COUNTS:")
    print(f"  Legacy users: {current_status.legacy_users}")
    print(f"  Legacy sessions: {current_status.legacy_sessions}")
    print(f"  Unified users: {current_status.unified_users}")
    print(f"  Unified sessions: {current_status.unified_sessions}")
    print(f"  Migrated users: {current_status.migrated_users}")
    print(f"  Migrated sessions: {current_status.migrated_sessions}")
    
    print(f"\nSTATISTICS:")
    print(f"  Total executions: {statistics['total_executions']}")
    print(f"  Successful: {statistics['successful_executions']}")
    print(f"  Failed: {statistics['failed_executions']}")
    print(f"  Success rate: {statistics['success_rate']:.1%}")
    
    if args.detailed or args.history:
        history_limit = args.history if args.history else 5
        history = tracker.get_migration_history(limit=history_limit)
        
        if history:
            print(f"\nRECENT EXECUTIONS (last {len(history)}):")
            for i, execution in enumerate(reversed(history), 1):
                status_icon = "✅" if execution.success else "❌"
                print(f"  {i}. {execution.migration_id} {status_icon}")
                print(f"     Time: {execution.start_time}")
                print(f"     Phase: {execution.phase.value}")
                print(f"     State: {execution.state.value}")
                if execution.users_processed > 0:
                    print(f"     Processed: {execution.users_processed} users, {execution.sessions_processed} sessions")
    
    # Save report if requested
    if args.save_report:
        report = tracker.generate_status_report(detailed=args.detailed)
        report_file = tracker.save_report(report)
        print(f"\nStatus report saved to: {report_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())