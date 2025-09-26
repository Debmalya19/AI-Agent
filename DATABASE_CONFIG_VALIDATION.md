# Database Configuration Validation

This document describes the database configuration validation system implemented for the AI agent application. The validation system ensures that database configuration is properly validated and that connection pooling is handled gracefully.

## Overview

The database configuration validation system provides:

- **Environment Variable Validation**: Comprehensive validation of all database-related environment variables
- **Database URL Parsing**: Robust parsing and validation of PostgreSQL and SQLite database URLs
- **Connection Pool Management**: Optimized connection pooling with proper timeout handling
- **Configuration Reporting**: Detailed reporting of configuration status and health checks
- **Error Handling**: Graceful handling of configuration errors and connection issues

## Components

### 1. Configuration Validation Module (`backend/config_validation.py`)

The main validation module provides:

- `DatabaseConfigValidator`: Main class for configuration validation
- `ConfigValidationError`: Custom exception for validation errors
- Utility functions for common validation tasks

### 2. Updated Database Module (`backend/database.py`)

Enhanced database module with:

- Integrated configuration validation
- Improved connection pool management
- Enhanced error handling and monitoring
- Configuration health checks

### 3. Validation Scripts

- `scripts/validate_database_config.py`: CLI tool for configuration validation
- `test_database_config_validation.py`: Comprehensive test suite
- `test_connection_pool_handling.py`: Connection pool behavior tests

## Environment Variables

### Required Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `DATABASE_URL` | string | Database connection URL | `postgresql://user:pass@localhost:5432/dbname` |

### Optional Variables

| Variable | Type | Default | Min | Max | Description |
|----------|------|---------|-----|-----|-------------|
| `DB_POOL_SIZE` | integer | 20 | 1 | 100 | Connection pool size |
| `DB_MAX_OVERFLOW` | integer | 30 | 0 | 200 | Maximum pool overflow |
| `DB_POOL_RECYCLE` | integer | 3600 | 300 | 86400 | Connection recycle time (seconds) |
| `DB_POOL_TIMEOUT` | integer | 30 | 5 | 300 | Pool timeout (seconds) |
| `DB_CONNECT_TIMEOUT` | integer | 10 | 1 | 60 | Connection timeout (seconds) |
| `DATABASE_ECHO` | boolean | false | - | - | Enable SQL query logging |
| `POSTGRES_ADMIN_PASSWORD` | string | postgres | - | - | PostgreSQL admin password |

## Database URL Formats

### PostgreSQL
```
postgresql://username:password@hostname:port/database_name
```

Example:
```
postgresql://ai_agent_user:ai_agent_password@localhost:5432/ai_agent
```

### SQLite
```
sqlite:///path/to/database.db
```

Example:
```
sqlite:///ai_agent.db
```

## Usage

### Programmatic Validation

```python
from backend.config_validation import DatabaseConfigValidator, ConfigValidationError

# Initialize validator
validator = DatabaseConfigValidator()

try:
    # Validate configuration
    config = validator.validate_environment_config()
    print("Configuration is valid")
    
    # Get connection parameters
    db_params = validator.get_database_connection_params()
    print(f"Database type: {db_params['database_type']}")
    
except ConfigValidationError as e:
    print(f"Configuration error: {e}")
```

### CLI Validation

```bash
# Basic validation
python scripts/validate_database_config.py

# Test connection
python scripts/validate_database_config.py --test-connection

# JSON output
python scripts/validate_database_config.py --format json

# Custom .env file
python scripts/validate_database_config.py --env-file /path/to/.env
```

### Database Information

```python
from backend.database import get_database_info, validate_current_config

# Get current database status
db_info = get_database_info()
print(f"Status: {db_info['status']}")
print(f"Health: {db_info['health']}")

# Validate current configuration
config_status = validate_current_config()
print(f"Validation: {config_status['validation_status']}")
```

## Connection Pool Management

The system implements production-ready connection pooling with the following features:

### Pool Configuration

- **Pool Size**: Base number of connections maintained in the pool
- **Max Overflow**: Additional connections that can be created beyond pool size
- **Pool Recycle**: Time after which connections are recycled
- **Pool Timeout**: Maximum time to wait for a connection from the pool
- **Connect Timeout**: Maximum time to wait when establishing a connection

### Pool Monitoring

```python
from backend.database import get_database_info

db_info = get_database_info()
print(f"Pool size: {db_info['pool_size']}")
print(f"Checked out: {db_info['checked_out']}")
print(f"Overflow: {db_info['overflow']}")
print(f"Checked in: {db_info['checked_in']}")
```

### Graceful Error Handling

The system handles connection pool exhaustion gracefully:

1. **Timeout Handling**: Connections that exceed timeout limits are properly handled
2. **Retry Logic**: Automatic retry with exponential backoff for failed connections
3. **Health Checks**: Regular health checks ensure connection validity
4. **Error Reporting**: Detailed error messages for troubleshooting

## Validation Rules

### Database URL Validation

- **PostgreSQL URLs**: Must include username, password, host, and database name
- **Port Validation**: Port numbers must be between 1 and 65535
- **Component Validation**: All required URL components must be present and non-empty

### Configuration Parameter Validation

- **Type Checking**: All parameters are validated against their expected types
- **Range Validation**: Numeric parameters are checked against min/max constraints
- **Boolean Conversion**: String boolean values are properly converted
- **Required Fields**: Required configuration fields are validated for presence

### Connection Health Validation

- **Connection Testing**: Actual database connections are tested during validation
- **Version Detection**: Database version information is retrieved and reported
- **Error Classification**: Different types of connection errors are properly classified

## Error Handling

### Configuration Errors

```python
try:
    config = validator.validate_environment_config()
except ConfigValidationError as e:
    # Handle configuration validation errors
    print(f"Configuration error: {e}")
```

### Connection Errors

```python
from backend.database import get_db

try:
    db_session = next(get_db())
    # Use database session
    db_session.close()
except RuntimeError as e:
    # Handle database unavailability
    print(f"Database error: {e}")
```

## Testing

### Running Tests

```bash
# Configuration validation tests
python test_database_config_validation.py

# Connection pool tests
python test_connection_pool_handling.py
```

### Test Coverage

The test suite covers:

- Database URL validation (PostgreSQL and SQLite)
- Configuration parameter validation
- Environment variable processing
- Connection pool behavior
- Error handling scenarios
- Health check functionality

## Troubleshooting

### Common Issues

1. **Invalid Database URL**
   - Check URL format and components
   - Verify credentials and host information
   - Ensure database exists and is accessible

2. **Connection Pool Exhaustion**
   - Monitor pool usage with `get_database_info()`
   - Adjust pool size and overflow parameters
   - Check for connection leaks in application code

3. **Configuration Validation Errors**
   - Use `validate_database_config.py` script for detailed error messages
   - Check environment variable types and ranges
   - Verify .env file format and loading

### Debugging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Use validation script with verbose output:

```bash
python scripts/validate_database_config.py --verbose --test-connection
```

## Best Practices

1. **Environment Configuration**
   - Use environment-specific .env files
   - Validate configuration before application startup
   - Monitor configuration changes in production

2. **Connection Pool Management**
   - Set appropriate pool sizes based on expected load
   - Monitor pool usage and adjust parameters as needed
   - Implement proper connection cleanup in application code

3. **Error Handling**
   - Always handle configuration validation errors
   - Implement graceful degradation for database unavailability
   - Log configuration and connection errors for troubleshooting

4. **Security**
   - Never log database passwords or sensitive configuration
   - Use secure credential management in production
   - Regularly rotate database credentials

## Integration

The configuration validation system integrates with:

- **Application Startup**: Validates configuration during application initialization
- **Health Checks**: Provides endpoints for monitoring configuration health
- **Migration Scripts**: Ensures proper configuration during database migrations
- **Testing Framework**: Validates test environment configuration

This validation system ensures that the database configuration meets requirements 4.3 and 4.4:
- **4.3**: Database configuration is loaded from environment variables with proper validation
- **4.4**: Connection pool exhaustion is handled gracefully with appropriate timeouts