#!/usr/bin/env python3
"""
PostgreSQL Migration Performance Benchmarks

Detailed performance comparison tests between SQLite and PostgreSQL
for various database operations relevant to the AI agent application.

Requirements: 5.3 (Performance comparison tests)
"""

import os
import sys
import time
import statistics
import pytest
import tempfile
import shutil
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
from contextlib import contextmanager

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Import application modules
from backend.database import create_database_engine, Base
from backend.unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedTicketComment, UnifiedUserSession,
    UnifiedChatSession, UnifiedChatMessage, TicketStatus, TicketPriority, UserRole
)

load_dotenv()

class PerformanceBenchmark:
    """Performance benchmarking utility for database operations"""
    
    def __init__(self, sqlite_engine, postgresql_engine=None):
        self.sqlite_engine = sqlite_engine
        self.postgresql_engine = postgresql_engine
        self.results = {}
    
    @contextmanager
    def timer(self, operation_name: str):
        """Context manager for timing operations"""
        start_time = time.perf_counter()
        yield
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        if operation_name not in self.results:
            self.results[operation_name] = []
        self.results[operation_name].append(duration)
    
    def benchmark_operation(self, operation_func, operation_name: str, iterations: int = 5):
        """Benchmark a database operation multiple times"""
        sqlite_times = []
        postgresql_times = []
        
        # Benchmark SQLite
        for _ in range(iterations):
            with self.timer(f"{operation_name}_sqlite"):
                operation_func(self.sqlite_engine)
            sqlite_times.append(self.results[f"{operation_name}_sqlite"][-1])
        
        # Benchmark PostgreSQL (if available)
        if self.postgresql_engine:
            for _ in range(iterations):
                with self.timer(f"{operation_name}_postgresql"):
                    operation_func(self.postgresql_engine)
                postgresql_times.append(self.results[f"{operation_name}_postgresql"][-1])
        
        return {
            'sqlite': {
                'times': sqlite_times,
                'avg': statistics.mean(sqlite_times),
                'min': min(sqlite_times),
                'max': max(sqlite_times),
                'stdev': statistics.stdev(sqlite_times) if len(sqlite_times) > 1 else 0
            },
            'postgresql': {
                'times': postgresql_times,
                'avg': statistics.mean(postgresql_times) if postgresql_times else None,
                'min': min(postgresql_times) if postgresql_times else None,
                'max': max(postgresql_times) if postgresql_times else None,
                'stdev': statistics.stdev(postgresql_times) if len(postgresql_times) > 1 else 0
            } if postgresql_times else None
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate performance comparison report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'benchmarks': {},
            'summary': {}
        }
        
        # Process results
        for operation, times in self.results.items():
            if times:
                report['benchmarks'][operation] = {
                    'times': times,
                    'avg': statistics.mean(times),
                    'min': min(times),
                    'max': max(times),
                    'stdev': statistics.stdev(times) if len(times) > 1 else 0,
                    'total': sum(times)
                }
        
        # Generate summary comparisons
        sqlite_ops = {k: v for k, v in report['benchmarks'].items() if 'sqlite' in k}
        postgresql_ops = {k: v for k, v in report['benchmarks'].items() if 'postgresql' in k}
        
        report['summary'] = {
            'sqlite_total_time': sum(op['total'] for op in sqlite_ops.values()),
            'postgresql_total_time': sum(op['total'] for op in postgresql_ops.values()) if postgresql_ops else None,
            'sqlite_avg_time': statistics.mean([op['avg'] for op in sqlite_ops.values()]) if sqlite_ops else None,
            'postgresql_avg_time': statistics.mean([op['avg'] for op in postgresql_ops.values()]) if postgresql_ops else None
        }
        
        return report


@pytest.mark.performance
class TestDatabasePerformanceBenchmarks:
    """Performance benchmark tests for database operations"""
    
    def setup_method(self):
        """Setup performance test environment"""
        load_dotenv()
        self.test_dir = tempfile.mkdtemp()
        self.sqlite_url = f"sqlite:///{self.test_dir}/perf_benchmark.db"
        self.postgresql_url = os.getenv("TEST_DATABASE_URL", 
                                       "postgresql://postgres:password@localhost:5432/test_ai_agent")
        
        # Create engines
        self.sqlite_engine = create_engine(self.sqlite_url)
        try:
            self.postgresql_engine = create_database_engine(self.postgresql_url)
            self.postgresql_available = True
        except:
            self.postgresql_engine = None
            self.postgresql_available = False
        
        # Create tables
        Base.metadata.create_all(self.sqlite_engine)
        if self.postgresql_engine:
            Base.metadata.create_all(self.postgresql_engine)
        
        # Initialize benchmark utility
        self.benchmark = PerformanceBenchmark(self.sqlite_engine, self.postgresql_engine)
        
        # Setup test data
        self.setup_benchmark_data()
    
    def teardown_method(self):
        """Cleanup performance test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
        # Clean PostgreSQL test data
        if self.postgresql_engine:
            try:
                with self.postgresql_engine.connect() as conn:
                    conn.execute(text("TRUNCATE TABLE unified_tickets CASCADE"))
                    conn.execute(text("TRUNCATE TABLE unified_users CASCADE"))
                    conn.commit()
            except:
                pass
    
    def setup_benchmark_data(self):
        """Setup data for benchmarking"""
        # Create data in SQLite
        self._create_test_data(self.sqlite_engine)
        
        # Create data in PostgreSQL
        if self.postgresql_engine:
            self._create_test_data(self.postgresql_engine)
    
    def _create_test_data(self, engine):
        """Create test data in the specified engine"""
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Create users for benchmarking
            users = []
            for i in range(1000):  # 1000 users for performance testing
                user = UnifiedUser(
                    user_id=f"bench_user_{i:06d}",
                    username=f"benchuser{i}",
                    email=f"bench{i}@example.com",
                    password_hash="hashed_password",
                    full_name=f"Benchmark User {i}",
                    role=UserRole.CUSTOMER
                )
                users.append(user)
                
                # Batch insert every 100 users
                if len(users) >= 100:
                    session.add_all(users)
                    session.commit()
                    users = []
            
            # Add remaining users
            if users:
                session.add_all(users)
                session.commit()
            
            # Create tickets for performance testing
            user_ids = [u.id for u in session.query(UnifiedUser).limit(100).all()]
            tickets = []
            
            for i in range(500):  # 500 tickets
                ticket = UnifiedTicket(
                    ticket_id=f"BENCH-{i:06d}",
                    title=f"Benchmark Ticket {i}",
                    description=f"Performance test ticket {i} with detailed description for benchmarking purposes",
                    status=TicketStatus.OPEN,
                    priority=TicketPriority.MEDIUM,
                    customer_id=user_ids[i % len(user_ids)]
                )
                tickets.append(ticket)
                
                # Batch insert every 50 tickets
                if len(tickets) >= 50:
                    session.add_all(tickets)
                    session.commit()
                    tickets = []
            
            # Add remaining tickets
            if tickets:
                session.add_all(tickets)
                session.commit()
                
        finally:
            session.close()
    
    def test_simple_select_performance(self):
        """Benchmark simple SELECT queries"""
        def simple_select(engine):
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                users = session.query(UnifiedUser).limit(100).all()
                return len(users)
            finally:
                session.close()
        
        results = self.benchmark.benchmark_operation(
            simple_select, "simple_select", iterations=10
        )
        
        # Verify results
        assert results['sqlite']['avg'] > 0
        if self.postgresql_available:
            assert results['postgresql']['avg'] > 0
            
            # Log performance comparison
            sqlite_avg = results['sqlite']['avg']
            postgresql_avg = results['postgresql']['avg']
            improvement = ((sqlite_avg - postgresql_avg) / sqlite_avg) * 100
            
            print(f"Simple SELECT - SQLite: {sqlite_avg:.4f}s, PostgreSQL: {postgresql_avg:.4f}s")
            print(f"Performance difference: {improvement:.1f}%")
    
    def test_complex_join_performance(self):
        """Benchmark complex JOIN queries"""
        def complex_join(engine):
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                # Complex query with joins
                results = session.query(UnifiedUser, UnifiedTicket).join(
                    UnifiedTicket, UnifiedUser.id == UnifiedTicket.customer_id
                ).filter(
                    UnifiedTicket.status == TicketStatus.OPEN
                ).limit(50).all()
                return len(results)
            finally:
                session.close()
        
        results = self.benchmark.benchmark_operation(
            complex_join, "complex_join", iterations=5
        )
        
        # Verify results
        assert results['sqlite']['avg'] > 0
        if self.postgresql_available:
            assert results['postgresql']['avg'] > 0
            
            # Log performance comparison
            sqlite_avg = results['sqlite']['avg']
            postgresql_avg = results['postgresql']['avg']
            improvement = ((sqlite_avg - postgresql_avg) / sqlite_avg) * 100
            
            print(f"Complex JOIN - SQLite: {sqlite_avg:.4f}s, PostgreSQL: {postgresql_avg:.4f}s")
            print(f"Performance difference: {improvement:.1f}%")
    
    def test_bulk_insert_performance(self):
        """Benchmark bulk INSERT operations"""
        def bulk_insert(engine):
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                # Create 100 new users
                users = []
                timestamp = int(time.time())
                for i in range(100):
                    user = UnifiedUser(
                        user_id=f"bulk_user_{timestamp}_{i:03d}",
                        username=f"bulkuser{timestamp}{i}",
                        email=f"bulk{timestamp}{i}@example.com",
                        password_hash="hashed_password",
                        full_name=f"Bulk User {timestamp} {i}",
                        role=UserRole.CUSTOMER
                    )
                    users.append(user)
                
                session.add_all(users)
                session.commit()
                return len(users)
            finally:
                session.close()
        
        results = self.benchmark.benchmark_operation(
            bulk_insert, "bulk_insert", iterations=3
        )
        
        # Verify results
        assert results['sqlite']['avg'] > 0
        if self.postgresql_available:
            assert results['postgresql']['avg'] > 0
            
            # Log performance comparison
            sqlite_avg = results['sqlite']['avg']
            postgresql_avg = results['postgresql']['avg']
            improvement = ((sqlite_avg - postgresql_avg) / sqlite_avg) * 100
            
            print(f"Bulk INSERT - SQLite: {sqlite_avg:.4f}s, PostgreSQL: {postgresql_avg:.4f}s")
            print(f"Performance difference: {improvement:.1f}%")
    
    def test_update_performance(self):
        """Benchmark UPDATE operations"""
        def bulk_update(engine):
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                # Update multiple records
                updated = session.query(UnifiedUser).filter(
                    UnifiedUser.username.like("benchuser%")
                ).limit(50).update(
                    {"full_name": f"Updated User {int(time.time())}"},
                    synchronize_session=False
                )
                session.commit()
                return updated
            finally:
                session.close()
        
        results = self.benchmark.benchmark_operation(
            bulk_update, "bulk_update", iterations=5
        )
        
        # Verify results
        assert results['sqlite']['avg'] > 0
        if self.postgresql_available:
            assert results['postgresql']['avg'] > 0
            
            # Log performance comparison
            sqlite_avg = results['sqlite']['avg']
            postgresql_avg = results['postgresql']['avg']
            improvement = ((sqlite_avg - postgresql_avg) / sqlite_avg) * 100
            
            print(f"Bulk UPDATE - SQLite: {sqlite_avg:.4f}s, PostgreSQL: {postgresql_avg:.4f}s")
            print(f"Performance difference: {improvement:.1f}%")
    
    def test_aggregation_performance(self):
        """Benchmark aggregation queries"""
        def aggregation_query(engine):
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                # Aggregation query
                from sqlalchemy import func
                results = session.query(
                    UnifiedTicket.status,
                    func.count(UnifiedTicket.id).label('count'),
                    func.avg(UnifiedTicket.id).label('avg_id')
                ).group_by(UnifiedTicket.status).all()
                return len(results)
            finally:
                session.close()
        
        results = self.benchmark.benchmark_operation(
            aggregation_query, "aggregation", iterations=10
        )
        
        # Verify results
        assert results['sqlite']['avg'] > 0
        if self.postgresql_available:
            assert results['postgresql']['avg'] > 0
            
            # Log performance comparison
            sqlite_avg = results['sqlite']['avg']
            postgresql_avg = results['postgresql']['avg']
            improvement = ((sqlite_avg - postgresql_avg) / sqlite_avg) * 100
            
            print(f"Aggregation - SQLite: {sqlite_avg:.4f}s, PostgreSQL: {postgresql_avg:.4f}s")
            print(f"Performance difference: {improvement:.1f}%")
    
    def test_connection_overhead_performance(self):
        """Benchmark connection creation overhead"""
        def connection_test(engine):
            # Create and close multiple connections
            for _ in range(10):
                conn = engine.connect()
                conn.execute(text("SELECT 1"))
                conn.close()
        
        results = self.benchmark.benchmark_operation(
            connection_test, "connection_overhead", iterations=5
        )
        
        # Verify results
        assert results['sqlite']['avg'] > 0
        if self.postgresql_available:
            assert results['postgresql']['avg'] > 0
            
            # Log performance comparison
            sqlite_avg = results['sqlite']['avg']
            postgresql_avg = results['postgresql']['avg']
            improvement = ((sqlite_avg - postgresql_avg) / sqlite_avg) * 100
            
            print(f"Connection Overhead - SQLite: {sqlite_avg:.4f}s, PostgreSQL: {postgresql_avg:.4f}s")
            print(f"Performance difference: {improvement:.1f}%")
    
    def test_generate_performance_report(self):
        """Generate comprehensive performance report"""
        # Run all benchmarks
        self.test_simple_select_performance()
        self.test_complex_join_performance()
        self.test_bulk_insert_performance()
        self.test_update_performance()
        self.test_aggregation_performance()
        self.test_connection_overhead_performance()
        
        # Generate report
        report = self.benchmark.generate_report()
        
        # Verify report structure
        assert 'timestamp' in report
        assert 'benchmarks' in report
        assert 'summary' in report
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"performance_benchmark_report_{timestamp}.json"
        
        import json
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nPerformance report saved to: {report_file}")
        
        # Print summary
        print("\nPerformance Benchmark Summary:")
        print("=" * 40)
        
        for operation, metrics in report['benchmarks'].items():
            print(f"{operation}: {metrics['avg']:.4f}s (±{metrics['stdev']:.4f}s)")
        
        if report['summary']['postgresql_total_time']:
            sqlite_total = report['summary']['sqlite_total_time']
            postgresql_total = report['summary']['postgresql_total_time']
            overall_improvement = ((sqlite_total - postgresql_total) / sqlite_total) * 100
            print(f"\nOverall Performance Improvement: {overall_improvement:.1f}%")


if __name__ == "__main__":
    # Run performance benchmarks
    pytest.main([__file__, "-v", "-m", "performance"])