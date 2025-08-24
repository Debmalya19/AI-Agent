# Memory Error Handling Guide

This guide explains how to use the comprehensive error handling and recovery mechanisms implemented for the memory layer system.

## Overview

The memory error handling system provides:

- **Graceful Error Handling**: Automatic error detection and classification
- **Fallback Strategies**: Multiple recovery options for different error types
- **Circuit Breaker Pattern**: Protection against cascading failures
- **Retry Mechanisms**: Exponential backoff for transient failures
- **Error Monitoring**: Comprehensive metrics and health reporting

## Core Components

### 1. MemoryErrorHandler

The central error handler that manages all error scenarios:

```python
from memory_error_handler import MemoryErrorHandler
import logging

# Initialize with custom logger
logger = logging.getLogger(__name__)
error_handler = MemoryErrorHandler(logger)
```

### 2. Error Types

The system recognizes these error categories:

- `DATABASE_CONNECTION`: Database connectivity issues
- `DATABASE_QUERY`: SQL query errors
- `CACHE_CONNECTION`: Cache connectivity issues
- `CACHE_OPERATION`: Cache operation failures
- `CONTEXT_RETRIEVAL`: Context search failures
- `TOOL_ANALYTICS`: Tool analysis errors
- `MEMORY_STORAGE`: Memory storage issues
- `CONFIGURATION`: Configuration errors

### 3. Fallback Strategies

Available recovery strategies:

- `RETRY_WITH_BACKOFF`: Retry with exponential backoff
- `USE_CACHE`: Fall back to cache storage/retrieval
- `USE_DATABASE`: Fall back to database operations
- `RETURN_EMPTY`: Return empty results gracefully
- `USE_DEFAULT`: Return default values
- `FAIL_GRACEFULLY`: Log error and continue

## Usage Examples

### Basic Error Handling

```python
from memory_error_handler import MemoryErrorHandler, FallbackStrategy

error_handler = MemoryErrorHandler()

# Handle database errors
try:
    # Database operation that might fail
    result = database_operation()
except Exception as e:
    fallback = error_handler.handle_database_error(e, "user_query")
    
    if fallback == FallbackStrategy.USE_CACHE:
        result = cache_operation()
    elif fallback == FallbackStrategy.RETURN_EMPTY:
        result = []
```

### Using the Decorator

```python
from memory_error_handler import handle_memory_errors

@handle_memory_errors(error_handler, "store_conversation")
def store_conversation(user_id, message, response):
    # This function will automatically handle errors
    # and apply appropriate fallback strategies
    return database.store(user_id, message, response)

# Usage
result = store_conversation("user123", "Hello", "Hi there!")
# Returns None if error occurs and fallback is applied
```

### Circuit Breaker Pattern

```python
# Get circuit breaker for database operations
db_breaker = error_handler.get_circuit_breaker('database')

@db_breaker
def database_operation():
    # This operation is protected by circuit breaker
    return perform_database_query()

try:
    result = database_operation()
except Exception as e:
    if "Circuit breaker is OPEN" in str(e):
        # Use alternative approach
        result = fallback_operation()
```

### Retry Operations

```python
def unreliable_operation():
    # Operation that might fail temporarily
    if random.random() < 0.7:
        raise Exception("Temporary failure")
    return "success"

# Retry with exponential backoff
result = error_handler.retry_operation(
    unreliable_operation,
    "test_operation",
    max_retries=3
)
```

### Error Recovery Context

```python
# Simple retry context
with error_handler.error_recovery_context("data_processing", max_retries=3):
    # Code that might fail and should be retried
    process_data()
```

## Integration with Memory Layer

### Enhanced Memory Manager

```python
from memory_error_handler_integration_example import EnhancedMemoryLayerManager
from memory_config import MemoryConfig

# Initialize enhanced manager with error handling
config = MemoryConfig()
memory_manager = EnhancedMemoryLayerManager(config)

# Store conversation with automatic error handling
success = memory_manager.store_conversation_safe(
    user_id="user123",
    user_message="How do I handle errors?",
    bot_response="Here's how to handle errors properly...",
    tools_used=["documentation", "examples"]
)

# Retrieve context with fallback strategies
context = memory_manager.retrieve_context_safe(
    query="error handling",
    user_id="user123",
    limit=10
)
```

### Health Monitoring

```python
# Get comprehensive health report
health_report = memory_manager.get_system_health()

print(f"System healthy: {health_report['is_healthy']}")
print(f"Error metrics: {health_report['error_metrics']}")
print(f"Circuit breakers: {health_report['circuit_breakers']}")
```

## Configuration

### Circuit Breaker Settings

```python
from memory_error_handler import CircuitBreaker

# Custom circuit breaker
custom_breaker = CircuitBreaker(
    failure_threshold=3,      # Open after 3 failures
    recovery_timeout=30,      # Try again after 30 seconds
    expected_exception=(ConnectionError, TimeoutError)
)
```

### Error Handler Configuration

```python
# Initialize with custom settings
error_handler = MemoryErrorHandler(logger)

# Add custom circuit breakers
error_handler.circuit_breakers['custom_service'] = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60
)
```

## Best Practices

### 1. Error Classification

Always classify errors appropriately:

```python
# Good: Specific error handling
if "connection" in str(error).lower():
    fallback = error_handler.handle_database_error(error, operation)
elif "timeout" in str(error).lower():
    fallback = error_handler.handle_database_error(error, operation)

# Avoid: Generic error handling for all cases
```

### 2. Fallback Strategies

Choose appropriate fallback strategies:

```python
# For critical data storage
if fallback == FallbackStrategy.USE_CACHE:
    # Store in cache as backup
    cache_store(data)
elif fallback == FallbackStrategy.RETRY_WITH_BACKOFF:
    # Retry important operations
    retry_operation()

# For non-critical operations
if fallback == FallbackStrategy.RETURN_EMPTY:
    # Gracefully return empty results
    return []
```

### 3. Monitoring and Alerting

Regularly check system health:

```python
# Check health periodically
health = error_handler.get_health_report()

if not health['is_healthy']:
    # Send alerts or take corrective action
    send_alert(f"Memory system unhealthy: {health}")

# Reset metrics periodically
error_handler.reset_error_metrics()
```

### 4. Logging

Use structured logging for better monitoring:

```python
import logging

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# The error handler will automatically log errors with context
```

## Testing Error Scenarios

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch

def test_database_error_handling():
    error_handler = MemoryErrorHandler()
    
    # Test connection error
    error = Exception("connection refused")
    strategy = error_handler.handle_database_error(error, "test")
    assert strategy == FallbackStrategy.USE_CACHE
    
    # Test query error
    error = Exception("syntax error")
    strategy = error_handler.handle_database_error(error, "test")
    assert strategy == FallbackStrategy.RETURN_EMPTY
```

### Integration Testing

```python
def test_memory_manager_with_errors():
    # Test with simulated database failures
    with patch('database.connection') as mock_db:
        mock_db.side_effect = ConnectionError("Database down")
        
        manager = EnhancedMemoryLayerManager(config)
        result = manager.store_conversation_safe("user", "msg", "resp")
        
        # Should handle error gracefully
        assert result is not None
```

## Troubleshooting

### Common Issues

1. **Circuit Breaker Stuck Open**
   ```python
   # Check circuit breaker state
   breaker = error_handler.get_circuit_breaker('database')
   if breaker.state.is_open:
       # Wait for recovery timeout or reset manually
       breaker.state.is_open = False
       breaker.state.failure_count = 0
   ```

2. **High Error Rates**
   ```python
   # Check error metrics
   metrics = error_handler.get_error_metrics()
   for error_type, metric in metrics.items():
       if metric.error_count > threshold:
           # Investigate specific error type
           print(f"High error rate for {error_type}: {metric.error_count}")
   ```

3. **Memory Leaks in Error Tracking**
   ```python
   # Periodically reset metrics
   error_handler.reset_error_metrics()
   
   # Or reset specific error types
   error_handler.reset_error_metrics(ErrorType.DATABASE_CONNECTION)
   ```

## Performance Considerations

- Circuit breakers add minimal overhead (~1-2ms per operation)
- Error metrics are stored in memory - reset periodically
- Retry operations use exponential backoff to avoid overwhelming systems
- Fallback strategies should be faster than primary operations

## Security Considerations

- Error messages are logged but sensitive data is not exposed
- Circuit breaker states don't leak internal system information
- Fallback operations maintain the same security constraints as primary operations

## Migration Guide

To integrate error handling into existing code:

1. **Add Error Handler**
   ```python
   from memory_error_handler import MemoryErrorHandler
   error_handler = MemoryErrorHandler()
   ```

2. **Wrap Critical Operations**
   ```python
   @handle_memory_errors(error_handler, "operation_name")
   def critical_operation():
       # Existing code
       pass
   ```

3. **Add Health Monitoring**
   ```python
   # Add to monitoring endpoints
   health = error_handler.get_health_report()
   ```

4. **Update Error Handling**
   ```python
   # Replace generic try/catch with specific error handling
   try:
       operation()
   except Exception as e:
       fallback = error_handler.handle_database_error(e, "operation")
       # Apply fallback strategy
   ```

This comprehensive error handling system ensures your memory layer remains resilient and provides graceful degradation under various failure scenarios.