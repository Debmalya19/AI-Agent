# Admin Dashboard API Integration Layer

This module provides a complete integration layer that wraps existing admin dashboard Flask routes into FastAPI, creating a unified API interface while maintaining backward compatibility.

## Overview

The admin dashboard integration consists of several key components:

1. **FastAPI Routers** - Modern FastAPI endpoints with proper type hints and validation
2. **Request/Response Adapters** - Convert between FastAPI and Flask formats
3. **Backward Compatibility Layer** - Maintains existing Flask API contracts
4. **Integration Manager** - Manages the lifecycle and health of the integration

## Features

### ✅ Implemented Features

- **Admin Dashboard Statistics** - Get user counts, ticket counts, recent activity
- **User Management** - List, view, create, update users with pagination and search
- **Ticket Management** - Full CRUD operations for tickets with filtering and comments
- **Analytics** - Performance metrics and customer satisfaction data
- **System Status** - Health checks and system information
- **Backward Compatibility** - Flask-style endpoints for existing integrations
- **Authentication Integration** - Uses unified authentication system
- **Database Integration** - Uses unified models and database connections

### 🔧 Technical Implementation

#### FastAPI Routers
```python
# Modern FastAPI endpoints with proper typing
@router.get("/dashboard", response_model=AdminDashboardStats)
async def get_admin_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Implementation with proper error handling and validation
```

#### Request/Response Adapters
```python
class AdminAPIAdapter:
    @staticmethod
    def adapt_user_to_dict(user: User, minimal: bool = False) -> Dict[str, Any]:
        # Convert User model to dictionary format
    
    @staticmethod
    def adapt_ticket_to_dict(ticket: Ticket, include_relations: bool = True) -> Dict[str, Any]:
        # Convert Ticket model to dictionary format
```

#### Backward Compatibility
```python
# Flask-style endpoints that maintain existing API contracts
@router.get("/api/admin/dashboard")
async def flask_compatible_dashboard():
    return JSONResponse(content={
        'success': True,
        'stats': {...}
    })
```

## Usage

### Basic Integration

```python
from fastapi import FastAPI
from backend.admin_integration import setup_admin_dashboard_integration

app = FastAPI()

# Setup complete admin dashboard integration
admin_integration = setup_admin_dashboard_integration(
    app, 
    enable_compatibility=True  # Enable Flask compatibility layer
)
```

### Advanced Integration

```python
from backend.admin_integration import AdminDashboardIntegration

# Create custom integration
admin_integration = AdminDashboardIntegration()

# Initialize with custom settings
success = admin_integration.initialize(app, enable_compatibility=False)

if success:
    print("Admin integration successful!")
    print(f"Registered {len(admin_integration.routers)} routers")
```

### Routes Only (No Management)

```python
from backend.admin_integration import add_admin_routes_only, add_compatibility_routes_only

# Add only modern FastAPI routes
add_admin_routes_only(app)

# Or add only Flask compatibility routes
add_compatibility_routes_only(app)
```

## API Endpoints

### Modern FastAPI Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/dashboard` | Admin dashboard statistics |
| GET | `/api/admin/users/` | Get all users with pagination |
| GET | `/api/admin/users/{user_id}` | Get user by ID |
| GET | `/api/admin/tickets/` | Get all tickets with filtering |
| GET | `/api/admin/tickets/{ticket_id}` | Get ticket by ID |
| POST | `/api/admin/tickets/` | Create new ticket |
| PUT | `/api/admin/tickets/{ticket_id}` | Update ticket |
| POST | `/api/admin/tickets/{ticket_id}/comments` | Add comment to ticket |
| GET | `/api/admin/tickets/stats/overview` | Get ticket statistics |
| GET | `/api/admin/analytics/performance-metrics` | Get performance metrics |
| GET | `/api/admin/analytics/customer-satisfaction` | Get satisfaction ratings |
| GET | `/api/admin/system/status` | Get system status |

### Flask Compatibility Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Flask-compatible login |
| POST | `/api/auth/logout` | Flask-compatible logout |
| POST | `/api/admin/register` | Flask-compatible admin registration |
| GET | `/api/admin/dashboard` | Flask-compatible dashboard |
| GET | `/api/admin/users` | Flask-compatible get users |
| GET | `/api/tickets/` | Flask-compatible get tickets |
| GET | `/api/tickets/{ticket_id}` | Flask-compatible get ticket |
| POST | `/api/tickets/` | Flask-compatible create ticket |
| GET | `/api/tickets/stats` | Flask-compatible ticket stats |

## Health and Monitoring

### Health Check Endpoints

```bash
# Check admin integration health
GET /api/admin/integration/health

# Get integration status
GET /api/admin/integration/status
```

### Response Format

```json
{
  "status": "healthy",
  "initialized": true,
  "routers_registered": 5,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Error Handling

The integration provides comprehensive error handling:

- **Authentication Errors** - 401 for unauthorized access
- **Authorization Errors** - 403 for insufficient permissions
- **Validation Errors** - 400 for invalid request data
- **Not Found Errors** - 404 for missing resources
- **Server Errors** - 500 for internal errors

### Error Response Format

```json
{
  "detail": "Error description",
  "error_code": "ADMIN_001",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Configuration

### Environment Variables

```bash
# Database configuration (uses unified database)
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Authentication configuration (uses unified auth)
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Admin-specific configuration
ADMIN_DASHBOARD_ENABLED=true
ADMIN_COMPATIBILITY_MODE=true
```

### Integration Settings

```python
# Custom integration settings
integration_config = {
    'enable_compatibility': True,
    'enable_health_checks': True,
    'enable_metrics': True,
    'log_level': 'INFO'
}
```

## Dependencies

The admin integration depends on:

- **unified_models.py** - Unified database models
- **unified_auth.py** - Unified authentication system
- **database.py** - Database connection and session management

## Testing

### Unit Tests

```python
import pytest
from fastapi.testclient import TestClient
from backend.admin_integration import setup_admin_dashboard_integration

def test_admin_dashboard():
    app = FastAPI()
    setup_admin_dashboard_integration(app)
    
    client = TestClient(app)
    response = client.get("/api/admin/dashboard")
    
    assert response.status_code == 200
```

### Integration Tests

```python
def test_ticket_creation():
    # Test ticket creation through both modern and compatibility endpoints
    pass

def test_user_management():
    # Test user CRUD operations
    pass
```

## Migration from Flask

### Step 1: Enable Compatibility Mode

```python
# Enable compatibility mode during transition
setup_admin_dashboard_integration(app, enable_compatibility=True)
```

### Step 2: Update Client Code Gradually

```javascript
// Old Flask endpoint
fetch('/api/admin/dashboard')

// New FastAPI endpoint (same response format)
fetch('/api/admin/dashboard')
```

### Step 3: Disable Compatibility Mode

```python
# Once migration is complete
setup_admin_dashboard_integration(app, enable_compatibility=False)
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```python
   # Ensure all dependencies are available
   from backend.unified_models import User, Ticket
   from backend.unified_auth import get_current_user
   ```

2. **Database Connection Issues**
   ```python
   # Check database configuration
   from backend.database import get_db
   ```

3. **Authentication Issues**
   ```python
   # Verify unified auth is properly configured
   from backend.unified_auth import setup_admin_authentication
   ```

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug logging for admin integration
logger = logging.getLogger('backend.admin_integration')
logger.setLevel(logging.DEBUG)
```

## Performance Considerations

- **Pagination** - All list endpoints support pagination
- **Filtering** - Efficient database queries with proper indexing
- **Caching** - Response caching for frequently accessed data
- **Connection Pooling** - Database connection pooling for scalability

## Security

- **Authentication Required** - All endpoints require valid JWT tokens
- **Role-Based Access** - Admin endpoints require admin privileges
- **Input Validation** - Comprehensive input validation and sanitization
- **SQL Injection Protection** - Parameterized queries and ORM usage

## Future Enhancements

- [ ] Real-time updates via WebSocket
- [ ] Advanced analytics and reporting
- [ ] Bulk operations for tickets and users
- [ ] Export functionality for data
- [ ] Advanced search and filtering
- [ ] Audit logging for admin actions