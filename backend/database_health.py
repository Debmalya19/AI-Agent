"""
Database Health Check Module

Provides health check functionality for database monitoring and diagnostics.
"""

import time
import logging
from typing import Dict, Any
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from .database import engine, health_check_database, get_database_info

logger = logging.getLogger(__name__)

class DatabaseHealthChecker:
    """Database health checker with comprehensive diagnostics"""
    
    def __init__(self):
        self.last_check_time = None
        self.last_check_result = None
        self.check_interval = 30  # seconds
    
    def quick_health_check(self) -> Dict[str, Any]:
        """Perform a quick health check"""
        start_time = time.time()
        
        try:
            if not engine:
                return {
                    "status": "unhealthy",
                    "error": "Database engine not available",
                    "response_time": 0,
                    "timestamp": time.time()
                }
            
            # Simple connection test
            healthy = health_check_database(engine)
            response_time = time.time() - start_time
            
            result = {
                "status": "healthy" if healthy else "unhealthy",
                "response_time": round(response_time * 1000, 2),  # ms
                "timestamp": time.time()
            }
            
            if not healthy:
                result["error"] = "Database connection failed"
            
            return result
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time": round((time.time() - start_time) * 1000, 2),
                "timestamp": time.time()
            }
    
    def comprehensive_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check with detailed diagnostics"""
        start_time = time.time()
        
        try:
            if not engine:
                return {
                    "status": "unhealthy",
                    "error": "Database engine not available",
                    "checks": {},
                    "response_time": 0,
                    "timestamp": time.time()
                }
            
            checks = {}
            overall_healthy = True
            
            # 1. Basic connectivity check
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                checks["connectivity"] = {"status": "pass", "message": "Database connection successful"}
            except Exception as e:
                checks["connectivity"] = {"status": "fail", "message": f"Connection failed: {e}"}
                overall_healthy = False
            
            # 2. Database version check
            try:
                with engine.connect() as conn:
                    if engine.url.drivername.startswith('postgresql'):
                        result = conn.execute(text("SELECT version()"))
                        version = result.fetchone()[0]
                        checks["version"] = {"status": "pass", "message": f"PostgreSQL version: {version.split()[1]}"}
                    else:
                        checks["version"] = {"status": "pass", "message": "SQLite database"}
            except Exception as e:
                checks["version"] = {"status": "fail", "message": f"Version check failed: {e}"}
            
            # 3. Connection pool status
            try:
                pool_info = get_database_info()
                if pool_info.get("status") == "connected":
                    pool_status = f"Pool: {pool_info.get('checked_out', 'N/A')}/{pool_info.get('pool_size', 'N/A')} active"
                    checks["connection_pool"] = {"status": "pass", "message": pool_status}
                else:
                    checks["connection_pool"] = {"status": "fail", "message": "Pool status unavailable"}
            except Exception as e:
                checks["connection_pool"] = {"status": "fail", "message": f"Pool check failed: {e}"}
            
            # 4. Table existence check
            try:
                with engine.connect() as conn:
                    if engine.url.drivername.startswith('postgresql'):
                        result = conn.execute(text("""
                            SELECT COUNT(*) FROM information_schema.tables 
                            WHERE table_schema = 'public'
                        """))
                        table_count = result.fetchone()[0]
                        checks["tables"] = {"status": "pass", "message": f"{table_count} tables found"}
                    else:
                        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                        tables = result.fetchall()
                        checks["tables"] = {"status": "pass", "message": f"{len(tables)} tables found"}
            except Exception as e:
                checks["tables"] = {"status": "fail", "message": f"Table check failed: {e}"}
            
            # 5. Write/Read test (optional, can be disabled in production)
            try:
                with engine.connect() as conn:
                    # Create a temporary test table
                    conn.execute(text("CREATE TEMPORARY TABLE health_check_test (id INTEGER, test_data TEXT)"))
                    conn.execute(text("INSERT INTO health_check_test (id, test_data) VALUES (1, 'test')"))
                    result = conn.execute(text("SELECT test_data FROM health_check_test WHERE id = 1"))
                    test_data = result.fetchone()[0]
                    conn.commit()
                    
                    if test_data == 'test':
                        checks["read_write"] = {"status": "pass", "message": "Read/write operations successful"}
                    else:
                        checks["read_write"] = {"status": "fail", "message": "Data integrity check failed"}
                        overall_healthy = False
            except Exception as e:
                checks["read_write"] = {"status": "fail", "message": f"Read/write test failed: {e}"}
            
            response_time = time.time() - start_time
            
            result = {
                "status": "healthy" if overall_healthy else "unhealthy",
                "checks": checks,
                "response_time": round(response_time * 1000, 2),  # ms
                "timestamp": time.time(),
                "database_info": get_database_info()
            }
            
            # Cache the result
            self.last_check_time = time.time()
            self.last_check_result = result
            
            return result
            
        except Exception as e:
            logger.error(f"Comprehensive health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "checks": {},
                "response_time": round((time.time() - start_time) * 1000, 2),
                "timestamp": time.time()
            }
    
    def get_cached_health_check(self) -> Dict[str, Any]:
        """Get cached health check result if recent enough"""
        if (self.last_check_result and 
            self.last_check_time and 
            time.time() - self.last_check_time < self.check_interval):
            return self.last_check_result
        
        # Cache is stale, perform new check
        return self.comprehensive_health_check()

# Global health checker instance
health_checker = DatabaseHealthChecker()

def get_health_status() -> Dict[str, Any]:
    """Get current database health status"""
    return health_checker.quick_health_check()

def get_detailed_health_status() -> Dict[str, Any]:
    """Get detailed database health status"""
    return health_checker.comprehensive_health_check()

def get_cached_health_status() -> Dict[str, Any]:
    """Get cached database health status"""
    return health_checker.get_cached_health_check()