# PostgreSQL Migration Testing Suite

This comprehensive testing suite validates the migration from SQLite to PostgreSQL for the AI agent application. The test suite covers all aspects of the migration process including functionality, performance, and data integrity.

## Test Structure

### Core Test Files

1. **`test_postgresql_migration.py`** - Main migration test suite
   - Database connection tests
   - Model operation tests
   - Migration script functionality tests
   - Full integration tests

2. **`test_migration_performance_benchmarks.py`** - Performance comparison tests
   - Query performance benchmarks
   - Connection overhead tests
   - Bulk operation performance
   - Comprehensive performance reporting

3. **`test_migration_data_integrity.py`** - Data integrity validation tests
   - Record count validation
   - Data checksum verification
   - Foreign key integrity checks
   - Schema compatibility validation

4. **`conftest.py`** - Pytest configuration and fixtures
   - Database connection fixtures
   - Test environment setup
   - Custom markers and configuration

### Test Runner Scripts

1. **`run_migration_tests.py`** - Comprehensive test runner
   - Automated test execution
   - Environment validation
   - Detailed reporting
   - Flexible test selection

## Requirements Coverage

The test suite addresses all requirements from the specification:

### Requirement 5.1 - Migration Validation Tests
- ✅ Migration script functionality validation
- ✅ Data export/import process testing
- ✅ Backup and rollback capability testing
- ✅ Migration configuration validation

### Requirement 5.2 - Database Connection and Model Tests
- ✅ SQLite and PostgreSQL connection testing
- ✅ Model operation validation
- ✅ Schema compatibility testing
- ✅ Connection pooling validation

### Requirement 5.3 - Performance Comparison Tests
- ✅ Query performance benchmarking
- ✅ Connection overhead measurement
- ✅ Bulk operation performance testing
- ✅ Comprehensive performance reporting

### Requirement 5.4 - Data Integrity Validation
- ✅ Record count verification
- ✅ Data checksum validation
- ✅ Foreign key integrity checks
- ✅ Special character handling validation

## Test Categories

### Unit Tests
- Database connection creation
- Model instantiation and validation
- Migration script component testing
- Configuration validation

### Integration Tests
- Full migration process testing
- Application functionality with PostgreSQL
- End-to-end data flow validation
- Cross-system compatibility testing

### Performance Tests
- Query execution benchmarks
- Connection pool performance
- Bulk operation efficiency
- Resource utilization measurement

### Data Integrity Tests
- Data consistency validation
- Referential integrity verification
- Type conversion accuracy
- Character encoding preservation

## Running the Tests

### Prerequisites

1. **Python Environment**
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-benchmark
   ```

2. **Database Setup**
   - SQLite: Automatically created for tests
   - PostgreSQL: Set `TEST_DATABASE_URL` environment variable
   ```bash
   export TEST_DATABASE_URL="postgresql://postgres:password@localhost:5432/test_ai_agent"
   ```

### Quick Test Run
```bash
# Run all basic tests (SQLite only)
python run_migration_tests.py --quick

# Run with verbose output
python run_migration_tests.py --quick --verbose
```

### PostgreSQL Tests
```bash
# Run PostgreSQL-specific tests
python run_migration_tests.py --postgresql-only

# Run all tests including PostgreSQL
python run_migration_tests.py
```

### Performance Tests
```bash
# Run performance benchmarks
python run_migration_tests.py --performance

# Run performance tests with reporting
python run_migration_tests.py --performance --report
```

### Integration Tests
```bash
# Run full integration tests
python run_migration_tests.py --integration

# Run comprehensive test suite
python run_migration_tests.py --integration --performance --report
```

### Individual Test Files
```bash
# Run specific test file
pytest tests/test_postgresql_migration.py -v

# Run specific test class
pytest tests/test_postgresql_migration.py::TestDatabaseConnections -v

# Run specific test method
pytest tests/test_postgresql_migration.py::TestDatabaseConnections::test_sqlite_connection_creation -v
```

### Test Markers
```bash
# Run tests by marker
pytest -m "postgresql" -v          # PostgreSQL-specific tests
pytest -m "performance" -v         # Performance tests
pytest -m "integration" -v         # Integration tests
```

## Test Environment Configuration

### Environment Variables

- `TEST_DATABASE_URL`: PostgreSQL connection string for testing
- `DATABASE_URL`: Main database connection (for integration tests)
- `PYTHONPATH`: Should include the project root directory

### Test Database Setup

The test suite automatically handles database setup and cleanup:

1. **SQLite**: Creates temporary databases for each test
2. **PostgreSQL**: Uses the configured test database with automatic cleanup

### Docker Setup (Optional)

For consistent testing environment:

```yaml
# docker-compose.test.yml
version: '3.8'
services:
  postgres-test:
    image: postgres:13
    environment:
      POSTGRES_DB: test_ai_agent
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5433:5432"
    volumes:
      - postgres_test_data:/var/lib/postgresql/data

volumes:
  postgres_test_data:
```

```bash
# Start test database
docker-compose -f docker-compose.test.yml up -d

# Set test database URL
export TEST_DATABASE_URL="postgresql://postgres:password@localhost:5433/test_ai_agent"

# Run tests
python run_migration_tests.py
```

## Test Reports

### Automated Reports

The test runner generates detailed reports:

1. **Test Execution Report**: Overall test results and timing
2. **Performance Report**: Benchmark results and comparisons
3. **Data Integrity Report**: Validation results and integrity scores

### Report Files

- `migration_test_report_YYYYMMDD_HHMMSS.json`: Test execution results
- `performance_benchmark_report_YYYYMMDD_HHMMSS.json`: Performance benchmarks
- `data_integrity_report_YYYYMMDD_HHMMSS.json`: Data integrity validation

### Sample Report Structure

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "total_tests": 25,
  "successful_tests": 24,
  "failed_tests": 1,
  "total_duration": 45.67,
  "results": [
    {
      "test_name": "Database Connection Tests",
      "success": true,
      "duration": 2.34
    }
  ]
}
```

## Troubleshooting

### Common Issues

1. **PostgreSQL Connection Failed**
   - Verify PostgreSQL is running
   - Check connection string format
   - Ensure test database exists
   - Verify user permissions

2. **Import Errors**
   - Check PYTHONPATH includes project root
   - Verify all dependencies are installed
   - Ensure backend modules are accessible

3. **Test Data Issues**
   - Check database permissions
   - Verify table creation rights
   - Ensure cleanup processes work

4. **Performance Test Variations**
   - Run tests multiple times for consistency
   - Consider system load during testing
   - Use dedicated test environment

### Debug Mode

Enable debug logging:

```bash
export PYTHONPATH=/path/to/project
export LOG_LEVEL=DEBUG
python run_migration_tests.py --verbose
```

### Manual Test Execution

For debugging specific issues:

```python
# Run individual test components
from tests.test_postgresql_migration import TestDatabaseConnections

test_instance = TestDatabaseConnections()
test_instance.setup_method()
test_instance.test_sqlite_connection_creation()
test_instance.teardown_method()
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Migration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: password
          POSTGRES_DB: test_ai_agent
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-benchmark
    
    - name: Run migration tests
      env:
        TEST_DATABASE_URL: postgresql://postgres:password@localhost:5432/test_ai_agent
      run: |
        python run_migration_tests.py --report
    
    - name: Upload test reports
      uses: actions/upload-artifact@v2
      with:
        name: test-reports
        path: "*_report_*.json"
```

## Best Practices

### Test Development

1. **Isolation**: Each test should be independent
2. **Cleanup**: Always clean up test data
3. **Assertions**: Use descriptive assertion messages
4. **Documentation**: Document complex test scenarios

### Performance Testing

1. **Consistency**: Run multiple iterations
2. **Environment**: Use consistent test environment
3. **Baselines**: Establish performance baselines
4. **Monitoring**: Track performance over time

### Data Integrity

1. **Comprehensive**: Test all data types and edge cases
2. **Validation**: Use multiple validation methods
3. **Reporting**: Generate detailed integrity reports
4. **Automation**: Automate integrity checks

## Contributing

When adding new tests:

1. Follow existing naming conventions
2. Add appropriate markers (@pytest.mark.*)
3. Include docstrings and comments
4. Update this README if needed
5. Ensure tests are independent and clean up properly

## Support

For issues with the migration testing suite:

1. Check the troubleshooting section
2. Review test logs and reports
3. Verify environment configuration
4. Test individual components in isolation