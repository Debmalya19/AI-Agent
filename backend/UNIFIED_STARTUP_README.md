# Unified Application Startup and Configuration

This document describes the unified startup system that manages the initialization and configuration of both the AI Agent backend and admin dashboard components.

## Overview

The unified startup system provides:

- **Centralized Configuration Management**: Single configuration system for all components
- **Ordered Initialization**: Proper startup sequence ensuring dependencies are initialized correctly
- **Health Monitoring**: Comprehensive health checks for all integrated services
- **Error Handling**: Unified error handling across all components
- **Graceful Degradation**: System continues to operate even if some components fail

## Architecture

### Components

1. **UnifiedConfig** (`unified_config.py`): Centralized configuration management
2. **UnifiedApplicationManager** (`unified_startup.py`): Manages application lifecycle
3. **HealthChecker** (`health_checks.py`): Monitors component health
4. **UnifiedErrorHandler** (`unified_error_handler.py`): Handles errors across components

### Startup Sequence

The application follows this initialization order:

1. **Configuration**: Load and validate all configuration settings
2. **Error Handling**: Initialize unified error handling system
3. **Database**: Initialize database connection and tables
4. **AI Agent**: Initialize AI components (LLM, memory, tools)
5. **Admin Dashboard**: Initialize admin dashboard integration
6. **Data Synchronization**: Initialize data sync service
7. **Voice Assistant**: Initialize voice components
8. **Analytics**: Initialize analytics service
9. **Background Tasks**: Start background processing tasks
10. **Middleware**: Setup FastAPI middleware
11. **Static Files**: Configure static file serving
12. **Health Checks**: Setup health monitoring endpoints

## Configuration

### Environment Variables

The system uses environment variables for configuration:

#### Core Settings
- `ENVIRONMENT`: Deployment environment (development, staging, production, testing)
- `DATABASE_URL`: PostgreSQL database connection string
- `JWT_SECRET_KEY`: Secret key for JWT token signing
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)

#### AI Agent Settings
- `GOOGLE_API_KEY`: Google Gemini API key
- `AI_MODEL_NAME`: AI model name (default: gemini-2.0-flash)
- `AI_TEMPERATURE`: AI model temperature (default: 0.3)
- `MEMORY_CLEANUP_INTERVAL_HOURS`: Memory cleanup interval (default: 24)
- `MEMORY_RETENTION_DAYS`: Memory retention period (default: 30)

#### Admin Dashboard Settings
- `ADMIN_DASHBOARD_ENABLED`: Enable admin dashboard (default: true)
- `ADMIN_FRONTEND_PATH`: Path to admin frontend files (default: admin-dashboard/frontend)
- `ADMIN_API_PREFIX`: API prefix for admin endpoints (default: /api/admin)
- `ADMIN_SESSION_TIMEOUT_MINUTES`: Admin session timeout (default: 60)

#### Data Synchronization Settings
- `DATA_SYNC_ENABLED`: Enable data sync service (default: true)
- `DATA_SYNC_INTERVAL_SECONDS`: Sync interval (default: 30)
- `DATA_SYNC_BATCH_SIZE`: Sync batch size (default: 100)

#### Voice Assistant Settings
- `VOICE_ENABLED`: Enable voice assistant (default: true)
- `VOICE_MAX_RECORDING_MS`: Max recording duration (default: 30000)
- `VOICE_RATE_LIMIT_PER_MINUTE`: Rate limit (default: 60)

#### Analytics Settings
- `ANALYTICS_ENABLED`: Enable analytics (default: true)
- `ANALYTICS_RETENTION_DAYS`: Analytics data retention (default: 90)
- `ANALYTICS_REAL_TIME_UPDATES`: Enable real-time updates (default: true)

#### Error Handling Settings
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_FILE`: Log file path (optional)
- `ERROR_REPORTING_ENABLED`: Enable error reporting (default: true)

### Configuration Validation

The system validates configuration on startup:

- **Development**: Warnings for missing configuration, continues with defaults
- **Production**: Strict validation, fails startup if critical configuration is missing

## Health Checks

### Endpoints

- `GET /health/`: Basic health check
- `GET /health/detailed`: Comprehensive health check of all components
- `GET /health/database`: Database-specific health check
- `GET /health/config`: Configuration validation health check

### Component Health

The system monitors:

- **Database**: Connection, query performance, table access
- **AI Agent**: API key configuration, memory manager status
- **Admin Dashboard**: Integration status, frontend availability
- **Data Sync**: Service status, sync performance
- **Voice Assistant**: Configuration, rate limiting
- **Analytics**: Service status, data processing

### Health Status Levels

- **HEALTHY**: Component is fully operational
- **DEGRADED**: Component is operational but has issues
- **UNHEALTHY**: Component is not operational
- **UNKNOWN**: Component status cannot be determined

## Usage

### Basic Usage

```python
from backend.unified_startup import create_unified_app

# Create the unified application
app = create_unified_app()

# The app is now ready to run with all components initialized
```

### Custom Configuration

```python
from backend.unified_config import UnifiedConfig, ConfigManager
from backend.unified_startup import UnifiedApplicationManager

# Create custom configuration
config = UnifiedConfig.from_env()
config_manager = ConfigManager(config)

# Create application manager with custom config
app_manager = UnifiedApplicationManager()
app_manager.config_manager = config_manager

# Initialize application
app = FastAPI()
await app_manager.startup_sequence(app)
```

### Health Check Integration

```python
from fastapi.testclient import TestClient

# Test health endpoints
with TestClient(app) as client:
    # Basic health check
    response = client.get("/health/")
    assert response.status_code == 200
    
    # Detailed health check
    response = client.get("/health/detailed")
    health_data = response.json()
    
    print(f"System status: {health_data['status']}")
    for component in health_data['components']:
        print(f"  {component['name']}: {component['status']}")
```

## Error Handling

### Startup Errors

The system handles startup errors gracefully:

- **Non-critical errors**: Logged as warnings, system continues
- **Critical errors**: In production, system fails to start
- **Development mode**: System continues with degraded functionality

### Runtime Errors

The unified error handler provides:

- **Error categorization**: Authentication, database, sync, integration errors
- **Automatic retry**: For transient errors
- **Circuit breaker**: Prevents cascading failures
- **Comprehensive logging**: All errors are logged with context

## Monitoring and Observability

### Logging

The system provides structured logging:

```
2024-01-15 10:30:00 - INFO - 🚀 Starting AI Agent Customer Support application...
2024-01-15 10:30:01 - INFO - ✅ Configuration initialized for production environment
2024-01-15 10:30:02 - INFO - ✅ Database initialized successfully
2024-01-15 10:30:03 - INFO - ✅ AI Agent components initialized
2024-01-15 10:30:04 - INFO - ✅ Admin dashboard integration initialized
2024-01-15 10:30:05 - INFO - 🎉 Application started successfully!
```

### Metrics

Health checks provide metrics for:

- Response times for each component
- Error counts and rates
- Resource utilization
- Service availability

### Alerts

The system can be configured to alert on:

- Component failures
- Performance degradation
- Configuration errors
- Resource exhaustion

## Deployment

### Development

```bash
# Set environment variables
export ENVIRONMENT=development
export DATABASE_URL=postgresql://localhost/ai_agent_dev
export GOOGLE_API_KEY=your_api_key

# Run the application
python main.py
```

### Production

```bash
# Set production environment variables
export ENVIRONMENT=production
export DATABASE_URL=postgresql://prod_host/ai_agent
export JWT_SECRET_KEY=your_secure_secret_key
export GOOGLE_API_KEY=your_api_key

# Additional production settings
export LOG_LEVEL=WARNING
export CORS_ORIGINS=https://yourdomain.com

# Run with production server
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker

```dockerfile
FROM python:3.11

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Set default environment
ENV ENVIRONMENT=production
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Testing

### Unit Tests

```bash
# Run unified startup tests
python -m pytest backend/test_unified_startup.py -v

# Run configuration tests
python -m pytest backend/test_unified_config.py -v

# Run health check tests
python -m pytest backend/test_health_checks.py -v
```

### Integration Tests

```bash
# Run main application integration test
python test_main_integration.py

# Run with pytest
python -m pytest test_main_integration.py -v
```

### Health Check Testing

```bash
# Test health endpoints
curl http://localhost:8000/health/
curl http://localhost:8000/health/detailed
curl http://localhost:8000/health/database
curl http://localhost:8000/health/config
```

## Troubleshooting

### Common Issues

1. **Configuration Validation Errors**
   - Check environment variables are set correctly
   - Verify database URL format
   - Ensure JWT secret key is set in production

2. **Database Connection Issues**
   - Verify database is running and accessible
   - Check database URL and credentials
   - Ensure database tables are created

3. **AI Agent Initialization Failures**
   - Verify Google API key is valid
   - Check network connectivity to Google services
   - Ensure memory manager configuration is correct

4. **Admin Dashboard Integration Issues**
   - Verify admin dashboard files exist
   - Check file permissions
   - Ensure admin routes are properly configured

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

### Health Check Debugging

Use health endpoints to diagnose issues:

```bash
# Check overall system health
curl http://localhost:8000/health/detailed | jq

# Check specific component
curl http://localhost:8000/health/database | jq
```

## Migration from Legacy System

### Steps

1. **Backup existing configuration**: Save current environment variables and settings
2. **Update main.py**: Replace old startup logic with unified system
3. **Set new environment variables**: Configure unified system settings
4. **Test health endpoints**: Verify all components are working
5. **Monitor startup logs**: Check for any warnings or errors

### Compatibility

The unified system is backward compatible with:

- Existing database schema
- Current API endpoints
- Frontend applications
- Authentication tokens

## Future Enhancements

### Planned Features

- **Configuration hot-reload**: Update configuration without restart
- **Advanced metrics**: Prometheus/Grafana integration
- **Distributed tracing**: OpenTelemetry support
- **Auto-scaling**: Dynamic resource allocation
- **Service mesh**: Istio/Linkerd integration

### Extension Points

The system is designed to be extensible:

- **Custom health checks**: Add component-specific health checks
- **Custom middleware**: Add application-specific middleware
- **Custom configuration**: Extend configuration schema
- **Custom error handlers**: Add specialized error handling

## Requirements Satisfied

This implementation satisfies the following requirements:

- **6.1**: Main application includes admin dashboard routers and middleware
- **6.2**: Unified configuration system manages settings for both components
- **6.3**: Application startup sequence initializes all integrated services
- **6.4**: Health check endpoints monitor both AI agent and admin dashboard components