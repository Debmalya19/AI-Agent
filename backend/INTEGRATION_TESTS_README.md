# Integration Tests Documentation

This document describes the comprehensive integration test suite for the Admin Dashboard Integration project.

## Overview

The integration test suite validates that the unified admin dashboard integration works correctly across all systems. It covers database integration, authentication, API endpoints, data synchronization, and complete end-to-end workflows.

## Test Coverage

### Requirements Coverage

The test suite covers all specified requirements:

- **2.1** - Customer data synchronization between systems
- **2.2** - Support ticket synchronization and real-time updates  
- **2.3** - Real-time data updates across AI agent and admin dashboard
- **2.4** - Data consistency maintenance and conflict resolution
- **3.1** - Unified authentication system with JWT token sharing
- **3.2** - Session management compatibility between systems
- **3.3** - Role-based access control (RBAC) integration
- **4.1** - API integration layer for admin dashboard endpoints
- **4.2** - Endpoint compatibility and request/response adaptation
- **4.3** - Error handling and logging across integrated systems

## Test Files

### 1. `test_unified_models.py`
**Purpose**: Tests unified database models and schema integration

**Coverage**:
- Model creation and validation
- Relationship integrity
- Database constraints
- Data validation utilities
- Migration compatibility

**Key Tests**:
- `test_create_tables()` - Verifies unified schema creation
- `test_create_user()` - Tests user model with validation
- `test_create_ticket()` - Tests ticket model integration
- `test_relationships()` - Validates model relationships

### 2. `test_auth_integration.py`
**Purpose**: Tests unified authentication system integration

**Coverage**:
- JWT token creation and validation
- Session management across systems
- Role-based permissions
- Password hashing and verification
- Cross-system authentication flow

**Key Tests**:
- `test_basic_auth_functionality()` - Core authentication features
- `test_role_permissions()` - RBAC system validation
- `test_admin_user_workflow()` - Admin-specific authentication

### 3. `test_admin_integration.py`
**Purpose**: Tests admin dashboard API integration layer

**Coverage**:
- FastAPI router integration
- Admin dashboard endpoint setup
- API adapter functionality
- Compatibility layer testing
- Error handling integration

**Key Tests**:
- `test_setup_admin_dashboard_integration()` - Integration setup
- `test_admin_api_adapter()` - Data adaptation between systems
- `test_admin_endpoints()` - Endpoint functionality

### 4. `test_data_sync_service.py`
**Purpose**: Tests data synchronization between AI agent and admin dashboard

**Coverage**:
- Real-time conversation to ticket sync
- Data consistency checks
- Event-driven synchronization
- Conflict resolution
- Background sync tasks

**Key Tests**:
- `test_sync_conversation_to_ticket()` - Conversation linking
- `test_consistency_check()` - Data integrity validation
- `test_event_driven_sync()` - Real-time sync events

### 5. `test_comprehensive_integration.py`
**Purpose**: Comprehensive integration tests covering all systems

**Coverage**:
- Database integration with all models
- Authentication integration across systems
- API integration with full workflow
- End-to-end data flow
- Performance and scalability

**Key Test Classes**:
- `TestDatabaseIntegration` - Complete database testing
- `TestAuthenticationIntegration` - Full auth system testing
- `TestAPIIntegration` - Complete API integration
- `TestDataSynchronization` - Full sync system testing

### 6. `test_api_integration_endpoints.py`
**Purpose**: Specific API endpoint integration testing

**Coverage**:
- Individual endpoint functionality
- Request/response format validation
- Authentication header handling
- Error response testing
- Performance benchmarks

**Key Tests**:
- `test_admin_dashboard_endpoints()` - Dashboard API testing
- `test_ticket_management_endpoints()` - Ticket API testing
- `test_error_handling()` - API error scenarios

### 7. `test_end_to_end_workflows.py`
**Purpose**: Complete end-to-end workflow testing

**Coverage**:
- Customer support workflows
- Admin management workflows
- Cross-system integration scenarios
- Data consistency across workflows

**Key Test Classes**:
- `TestCustomerSupportWorkflow` - Complete support scenarios
- `TestAdminWorkflows` - Admin dashboard workflows
- `TestCrossSystemIntegration` - System integration scenarios

## Running Tests

### Run All Tests
```bash
cd ai-agent/backend
python run_integration_tests.py
```

### Run Specific Test Categories
```bash
# Database tests only
python run_integration_tests.py database

# Authentication tests only
python run_integration_tests.py auth

# API integration tests only
python run_integration_tests.py api

# Data synchronization tests only
python run_integration_tests.py sync

# End-to-end workflow tests only
python run_integration_tests.py e2e

# Comprehensive integration tests only
python run_integration_tests.py comprehensive
```

### Run Individual Test Files
```bash
# Run specific test file
python -m pytest test_unified_models.py -v

# Run with detailed output
python -m pytest test_auth_integration.py -v --tb=long

# Run specific test class
python -m pytest test_comprehensive_integration.py::TestDatabaseIntegration -v
```

## Test Environment Setup

### Prerequisites
- Python 3.8+
- SQLAlchemy
- FastAPI
- pytest
- All project dependencies installed

### Database Setup
Tests use in-memory SQLite databases for isolation:
```python
TEST_DATABASE_URL = "sqlite:///:memory:"
```

### Mock Services
Tests use mocking for external dependencies:
- Database session mocking
- Authentication service mocking
- API endpoint mocking

## Test Data

### Sample Users
Tests create users with different roles:
- **Customer**: Basic user with limited permissions
- **Agent**: Support agent with ticket management permissions
- **Admin**: Full administrative permissions

### Sample Tickets
Tests create tickets with various:
- Statuses (Open, In Progress, Resolved, Closed)
- Priorities (Low, Medium, High, Critical)
- Categories (Technical, Billing, Account, Support)

### Sample Conversations
Tests create AI agent conversations with:
- Different conversation types (informational, problem, escalation)
- Various tools used
- Different sentiment levels

## Expected Test Results

### Success Criteria
All tests should pass with:
- ✅ Database models create and validate correctly
- ✅ Authentication works across systems
- ✅ API endpoints respond correctly
- ✅ Data synchronization maintains consistency
- ✅ End-to-end workflows complete successfully

### Performance Benchmarks
- Individual API calls: < 1 second
- Bulk operations (10 items): < 30 seconds
- Database operations: < 100ms per query
- Authentication: < 200ms per token validation

## Troubleshooting

### Common Issues

#### Database Connection Errors
```
Error: Could not connect to database
Solution: Ensure database dependencies are installed and accessible
```

#### Authentication Failures
```
Error: JWT token validation failed
Solution: Check JWT secret configuration and token format
```

#### Import Errors
```
Error: Module not found
Solution: Ensure all dependencies are installed and PYTHONPATH is correct
```

#### Test Timeouts
```
Error: Test timed out
Solution: Check for infinite loops or blocking operations in code
```

### Debug Mode
Run tests with debug output:
```bash
python -m pytest test_file.py -v -s --tb=long --log-cli-level=DEBUG
```

### Test Isolation
Each test uses fresh database instances to ensure isolation:
- In-memory SQLite databases
- Fresh authentication services
- Clean test data for each test

## Continuous Integration

### GitHub Actions Integration
```yaml
name: Integration Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run integration tests
        run: python ai-agent/backend/run_integration_tests.py
```

### Test Reporting
The test runner generates comprehensive reports including:
- Pass/fail status for each test file
- Duration metrics
- Requirements coverage analysis
- Failure analysis with error details
- Performance benchmarks

## Maintenance

### Adding New Tests
1. Create test file following naming convention: `test_*.py`
2. Add to `run_integration_tests.py` test file list
3. Follow existing test patterns and fixtures
4. Document test purpose and coverage

### Updating Tests
1. Update tests when requirements change
2. Maintain backward compatibility where possible
3. Update documentation to reflect changes
4. Ensure all requirements remain covered

### Test Data Management
- Keep test data minimal and focused
- Use factories for complex test data creation
- Clean up test data after each test
- Avoid dependencies between tests

## Security Considerations

### Test Data Security
- Use fake/mock data only
- Never use production credentials
- Sanitize any logged output
- Use secure test database configurations

### Authentication Testing
- Test with various permission levels
- Verify unauthorized access is blocked
- Test token expiration and refresh
- Validate role-based access controls

## Performance Testing

### Load Testing
Tests include basic performance validation:
- Response time measurements
- Concurrent request handling
- Memory usage monitoring
- Database query performance

### Scalability Testing
- Bulk data operations
- Multiple user scenarios
- High-volume ticket creation
- Large conversation histories

## Documentation Updates

When modifying tests:
1. Update this README with new test descriptions
2. Update requirements coverage mapping
3. Document any new test categories
4. Update troubleshooting section as needed

## Contact

For questions about the integration tests:
- Review existing test files for examples
- Check the main project documentation
- Refer to individual test file docstrings
- Follow established testing patterns