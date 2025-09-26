# Unified Error Handling and Logging System

This document describes the comprehensive error handling and logging system implemented for the AI Agent Customer Support application, providing unified error management across both FastAPI and admin dashboard components.

## Overview

The unified error handling system provides:

- **Comprehensive Error Categorization**: Automatic classification of errors into categories (authentication, database, sync, integration, etc.)
- **Intelligent Recovery Mechanisms**: Automatic retry with backoff, circuit breaker patterns, and graceful degradation
- **Unified Logging**: Centralized logging system that captures errors from all components
- **Real-time Monitoring**: Health checks, metrics collection, and monitoring endpoints
- **Integration Support**: Seamless integration with existing admin dashboard, sync, and authentication components

## Architecture

### Core Components

1. **UnifiedErrorHandler** (`unified_error_handler.py`)
   - Central error handling logic
   - Error categorization and severity determination
   - Recovery strategy implementation
   - Circuit breaker management

2. **ErrorHandlingMiddleware** (`error_middleware.py`)
   - FastAPI middleware for automatic error handling
   - Request/response error processing
   - Admin-specific error handling

3. **Error Integration Utilities** (`error_integration_utils.py`)
   - Integration with admin dashboard components
   - Data synchronization error handling
   - Database and authentication error management

4. **Monitoring Routes** (`error_monitoring_routes.py`)
   - Health check endpoints
   - Error metrics and dashboard data
   - Circuit breaker management

## Error Categories

The system categorizes errors into the following types:

- **AUTHENTICATION**: JWT token errors, login failures, expired sessions
- **AUTHORIZATION**: Permission denied, insufficient privileges
- **DATABASE**: Connection failures, query errors, integrity violations
- **SYNC**: Data synchronization failures, conflict resolution
- **INTEGRATION**: Admin dashboard integration issues
- **VALIDATION**: Input validation errors, bad requests
- **EXTERNAL_API**: Third-party service failures
- **NETWORK**: Connection timeouts, network issues
- **CONFIGURATION**: Missing environment variables, config errors
- **SYSTEM**: General system errors

## Error Severity Levels

- **CRITICAL**: System-threatening errors requiring immediate attention
- **HIGH**: Important errors affecting functionality
- **MEDIUM**: Moderate errors with available workarounds
- **LOW**: Minor errors with minimal impact

## Recovery Strategies

### 1. Retry with Backoff
- Automatic retry with exponential backoff
- Configurable max retries and timeout
- Used for transient network and database issues

### 2. Circuit Breaker
- Prevents cascading failures
- Automatic recovery detection
- Configurable failure thresholds

### 3. Graceful Degradation
- Fallback to limited functionality
- Cache-based responses when database unavailable
- Reduced feature set during integration failures

### 4. Fail Fast
- Immediate failure for authentication errors
- Quick response for unrecoverable errors

## Usage Examples

### Basic Error Handling

```python
from backend.unified_error_handler import get_error_handler, ErrorContext

error_handler = get_error_handler()

# Create error context
context = ErrorContext(
    user_id="user123",
    component="admin_api",
    operation="create_ticket"
)

# Handle error
try:
    # Your operation here
    pass
except Exception as e:
    error_result = await error_handler.handle_error(e, context)
    # Error is automatically logged and recovery attempted
```

### Using Error Decorator

```python
from backend.unified_error_handler import get_error_handler

error_handler = get_error_handler()

@error_handler.error_handler_decorator(component="admin_api", operation="get_users")
async def get_admin_users():
    # Function automatically wrapped with error handling
    # Errors are caught, logged, and recovery attempted
    pass
```

### Using Error Context Manager

```python
from backend.unified_error_handler import get_error_handler, ErrorContext

error_handler = get_error_handler()
context = ErrorContext(component="data_sync", operation="sync_tickets")

async with error_handler.error_context(context):
    # Operations within this block are automatically error-handled
    await sync_tickets()
```

### Circuit Breaker Usage

```python
from backend.unified_error_handler import get_error_handler

error_handler = get_error_handler()
database_breaker = error_handler.get_circuit_breaker('database')

@database_breaker
async def database_operation():
    # Function protected by circuit breaker
    # Automatic failure detection and recovery
    pass
```

## Integration with Existing Components

### Admin Dashboard Integration

```python
from backend.error_integration_utils import get_admin_error_integration

admin_integration = get_admin_error_integration()

# Wrap admin API calls
@admin_integration.wrap_admin_api_call
async def admin_api_function():
    # Automatic error handling for admin operations
    pass

# Handle authentication errors
auth_result = admin_integration.handle_admin_auth_error(auth_error, user_id)
```

### Data Sync Integration

```python
from backend.error_integration_utils import get_sync_error_integration

sync_integration = get_sync_error_integration()

# Handle sync errors
sync_result = await sync_integration.handle_sync_error(
    error, "ticket_sync", entity_id=123, entity_type="ticket"
)

# Retry failed operations
retry_results = await sync_integration.retry_failed_sync_operations()
```

### Database Integration

```python
from backend.error_integration_utils import get_db_error_integration

db_integration = get_db_error_integration()

# Handle database errors
db_result = await db_integration.handle_database_error(
    error, "user_query", table_name="users"
)

# Check database health
health = db_integration.check_database_health()
```

## FastAPI Integration

### Setup Middleware

```python
from fastapi import FastAPI
from backend.error_middleware import setup_error_middleware
from backend.unified_error_handler import setup_error_handler

app = FastAPI()

# Setup error handler
error_handler = setup_error_handler()

# Setup middleware
setup_error_middleware(app, error_handler)
```

### Monitoring Endpoints

```python
from backend.error_monitoring_routes import setup_error_monitoring_routes

# Add monitoring routes
setup_error_monitoring_routes(app)
```

## Monitoring and Health Checks

### Available Endpoints

- `GET /api/error-monitoring/health` - System health report
- `GET /api/error-monitoring/metrics` - Error metrics
- `GET /api/error-monitoring/circuit-breakers` - Circuit breaker status
- `GET /api/error-monitoring/dashboard` - Comprehensive dashboard data
- `POST /api/error-monitoring/circuit-breakers/{name}/reset` - Reset circuit breaker
- `POST /api/error-monitoring/metrics/reset` - Reset error metrics

### Health Check Response

```json
{
  "is_healthy": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "error_metrics": {
    "authentication": {
      "error_count": 5,
      "last_occurrence": "2024-01-15T10:25:00Z",
      "success_rate": 0.95
    }
  },
  "circuit_breakers": {
    "database": {
      "is_open": false,
      "failure_count": 0,
      "success_count": 150
    }
  },
  "health_score": 95
}
```

## Configuration

### Environment Variables

```bash
# Logging configuration
ERROR_LOG_LEVEL=INFO
ERROR_LOG_FILE=/var/log/ai-agent/errors.log

# Circuit breaker settings
DB_CIRCUIT_BREAKER_THRESHOLD=3
DB_CIRCUIT_BREAKER_TIMEOUT=30

# Retry settings
MAX_RETRY_ATTEMPTS=3
RETRY_BACKOFF_MULTIPLIER=2
```

### Programmatic Configuration

```python
from backend.unified_error_handler import UnifiedErrorHandler

# Custom error handler configuration
error_handler = UnifiedErrorHandler(
    logger=custom_logger,
    log_file_path="/custom/path/errors.log"
)

# Configure circuit breakers
error_handler.circuit_breakers['custom_service'] = CircuitBreaker(
    name='custom_service',
    failure_threshold=5,
    recovery_timeout=60
)
```

## Logging Format

### Log Entry Structure

```
2024-01-15 10:30:00,123 - unified_error_handler - ERROR - handle_error:245 - Error handled - DATABASE/HIGH: Connection timeout
```

### Structured Log Data

```json
{
  "error_type": "OperationalError",
  "error_message": "Connection timeout",
  "category": "database",
  "severity": "high",
  "strategy": "retry_with_backoff",
  "context": {
    "user_id": "user123",
    "session_id": "session456",
    "request_id": "req789",
    "endpoint": "/api/admin/users",
    "method": "GET",
    "component": "admin_api"
  },
  "traceback": "...",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Testing

### Running Tests

```bash
# Run all error handling tests
pytest backend/test_unified_error_handler.py -v

# Run specific test categories
pytest backend/test_unified_error_handler.py::TestUnifiedErrorHandler -v
pytest backend/test_unified_error_handler.py::TestCircuitBreaker -v
pytest backend/test_unified_error_handler.py::TestErrorMiddleware -v
```

### Test Coverage

The test suite covers:
- Error categorization and severity determination
- Recovery strategy selection and execution
- Circuit breaker functionality
- Middleware integration
- Error metrics and monitoring
- Integration utilities

## Best Practices

### 1. Error Context
Always provide comprehensive error context:

```python
context = ErrorContext(
    user_id=current_user.id,
    session_id=session.id,
    request_id=request.state.request_id,
    endpoint=request.url.path,
    method=request.method,
    component="admin_dashboard",
    operation="create_ticket",
    additional_data={
        "ticket_type": "support",
        "priority": "high"
    }
)
```

### 2. Component-Specific Handling
Use appropriate integration utilities for different components:

```python
# For admin operations
admin_integration = get_admin_error_integration()
result = await admin_integration.handle_admin_auth_error(error, user_id)

# For sync operations
sync_integration = get_sync_error_integration()
result = await sync_integration.handle_sync_error(error, operation, entity_id)
```

### 3. Monitoring and Alerting
Regularly monitor error metrics and set up alerts:

```python
# Check system health
health_report = error_handler.get_health_report()
if not health_report['is_healthy']:
    send_alert("System health degraded", health_report)

# Monitor circuit breakers
cb_status = error_handler.get_circuit_breaker_status()
open_breakers = [name for name, status in cb_status.items() if status['is_open']]
if open_breakers:
    send_alert(f"Circuit breakers open: {open_breakers}")
```

### 4. Graceful Degradation
Design fallback mechanisms for critical operations:

```python
try:
    # Primary operation
    result = await primary_database_operation()
except Exception as e:
    error_result = await error_handler.handle_error(e, context)
    if error_result['recovery_result']['success']:
        # Use fallback (cache, simplified response, etc.)
        result = await fallback_operation()
    else:
        # Inform user of temporary unavailability
        raise HTTPException(503, "Service temporarily unavailable")
```

## Troubleshooting

### Common Issues

1. **High Error Rates**
   - Check error metrics: `GET /api/error-monitoring/metrics`
   - Review recent logs for patterns
   - Verify external service availability

2. **Circuit Breakers Open**
   - Check circuit breaker status: `GET /api/error-monitoring/circuit-breakers`
   - Verify underlying service health
   - Reset if service is restored: `POST /api/error-monitoring/circuit-breakers/{name}/reset`

3. **Sync Failures**
   - Check sync error summary: `GET /api/error-monitoring/sync/errors`
   - Retry failed operations: `POST /api/error-monitoring/sync/retry`
   - Review sync service logs

4. **Database Connection Issues**
   - Check database health: `GET /api/error-monitoring/database/health`
   - Verify connection pool settings
   - Check database server status

### Debug Mode

Enable debug logging for detailed error information:

```python
import logging
logging.getLogger('unified_error_handler').setLevel(logging.DEBUG)
```

## Performance Considerations

- Error handling adds minimal overhead (~1-2ms per request)
- Circuit breakers prevent resource waste on failing services
- Async operations don't block request processing
- Metrics collection is optimized for high throughput
- Log rotation prevents disk space issues

## Security Considerations

- Error messages are sanitized for user responses
- Sensitive information is not logged in production
- Error IDs allow correlation without exposing details
- Authentication errors trigger appropriate security measures
- Rate limiting prevents error-based attacks

## Future Enhancements

- Machine learning-based error prediction
- Advanced anomaly detection
- Integration with external monitoring systems
- Automated recovery actions
- Enhanced error correlation and root cause analysis