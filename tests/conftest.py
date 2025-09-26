"""
Pytest configuration and fixtures for PostgreSQL migration tests
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@pytest.fixture(scope="session")
def test_database_urls():
    """Provide test database URLs"""
    return {
        'sqlite': "sqlite:///test_migration_session.db",
        'postgresql': os.getenv("TEST_DATABASE_URL", 
                               "postgresql://postgres:password@localhost:5432/test_ai_agent")
    }

@pytest.fixture(scope="session")
def postgresql_available(test_database_urls):
    """Check if PostgreSQL is available for testing"""
    try:
        from backend.database import create_database_engine
        engine = create_database_engine(test_database_urls['postgresql'])
        if engine:
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
    except:
        return False
    return False

@pytest.fixture
def temp_dir():
    """Provide temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def test_sqlite_engine(temp_dir):
    """Provide SQLite engine for testing"""
    sqlite_url = f"sqlite:///{temp_dir}/test.db"
    engine = create_engine(sqlite_url)
    yield engine
    engine.dispose()

@pytest.fixture
def test_postgresql_engine(test_database_urls, postgresql_available):
    """Provide PostgreSQL engine for testing"""
    if not postgresql_available:
        pytest.skip("PostgreSQL not available for testing")
    
    from backend.database import create_database_engine
    engine = create_database_engine(test_database_urls['postgresql'])
    yield engine
    
    # Cleanup test data
    if engine:
        try:
            with engine.connect() as conn:
                conn.execute("TRUNCATE TABLE unified_tickets CASCADE")
                conn.execute("TRUNCATE TABLE unified_users CASCADE")
                conn.commit()
        except:
            pass
        engine.dispose()

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "postgresql: mark test as requiring PostgreSQL"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names"""
    for item in items:
        # Add postgresql marker to tests that need PostgreSQL
        if "postgresql" in item.name.lower() or "pg" in item.name.lower():
            item.add_marker(pytest.mark.postgresql)
        
        # Add performance marker to performance tests
        if "performance" in item.name.lower() or "benchmark" in item.name.lower():
            item.add_marker(pytest.mark.performance)
        
        # Add integration marker to integration tests
        if "integration" in item.name.lower() or "full" in item.name.lower():
            item.add_marker(pytest.mark.integration)