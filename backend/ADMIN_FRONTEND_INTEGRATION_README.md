# Admin Dashboard Frontend Integration

This document describes the integration of the admin dashboard frontend with the main FastAPI application.

## Overview

The admin dashboard frontend integration provides:

1. **Static File Serving**: Admin dashboard assets (CSS, JS, images) served through FastAPI
2. **SPA Route Handling**: Single Page Application routing for admin dashboard pages
3. **API Proxy Layer**: Unified API endpoints that route admin dashboard calls through FastAPI
4. **Unified Authentication**: Admin dashboard uses the same authentication system as the main backend

## Components

### 1. Admin Frontend Integration (`admin_frontend_integration.py`)

**Purpose**: Configures FastAPI to serve admin dashboard frontend assets and handle SPA routing.

**Features**:
- Mounts static files for CSS, JS, and assets
- Provides routes for admin dashboard pages (`/admin`, `/admin/tickets`, `/admin/users`, etc.)
- Handles SPA routing by serving `index.html` for unknown routes
- Graceful error handling when frontend files are missing

**Routes**:
- `/admin` - Main admin dashboard
- `/admin/tickets` - Tickets management page
- `/admin/users` - User management page
- `/admin/integration` - Integration status page
- `/admin/settings` - Settings page
- `/admin/{path:path}` - Catch-all for SPA routing

### 2. Admin API Proxy (`admin_api_proxy.py`)

**Purpose**: Provides unified API endpoints for admin dashboard functionality.

**Admin API Endpoints** (`/api/admin/`):
- `GET /dashboard` - Dashboard statistics
- `GET /users` - List all users
- `GET /integration/status` - Integration status with AI Agent
- `POST /integration/sync` - Trigger synchronization
- `GET /metrics` - Performance metrics

**Support API Endpoints** (`/api/support/`):
- `GET /tickets` - List tickets with filtering
- `GET /tickets/{id}` - Get specific ticket
- `POST /tickets` - Create new ticket
- `PUT /tickets/{id}` - Update ticket
- `POST /tickets/{id}/comments` - Add comment to ticket

### 3. Admin Auth Proxy (`admin_auth_proxy.py`)

**Purpose**: Provides unified authentication endpoints for admin dashboard.

**Auth API Endpoints** (`/api/auth/`):
- `POST /login` - Admin login
- `POST /logout` - Admin logout
- `GET /profile` - Get user profile
- `PUT /profile` - Update user profile
- `POST /register` - Register new admin user
- `GET /verify` - Verify session

### 4. Unified API Client (`unified_api.js`)

**Purpose**: Frontend JavaScript client for unified API endpoints.

**Features**:
- Handles authentication with session cookies and localStorage
- Provides methods for all admin and support API endpoints
- Automatic error handling and authentication redirects
- Backward compatibility with existing admin dashboard code

## Integration Setup

The integration is automatically set up in `main.py`:

```python
# Setup admin dashboard integration
try:
    setup_admin_auth_proxy(app)
    setup_admin_api_proxy(app)
    setup_admin_frontend_integration(app)
    logger.info("✅ Admin dashboard integration setup completed")
except Exception as e:
    logger.error(f"❌ Failed to setup admin dashboard integration: {e}")
```

## Frontend Updates

### HTML Files Updated

1. **index.html** - Added `unified_api.js` script
2. **tickets.html** - Added `unified_api.js` script
3. **register.html** - New admin registration page

### JavaScript Updates

1. **auth.js** - Updated to use unified API for authentication
2. **unified_api.js** - New unified API client

## Authentication Flow

1. **Login**: Admin enters credentials on `/admin` page
2. **Authentication**: Credentials sent to `/api/auth/login`
3. **Session Creation**: Server creates session and sets cookie
4. **Token Storage**: Client stores token in localStorage for API calls
5. **API Requests**: All API requests include authentication headers
6. **Session Validation**: Server validates session for protected routes

## File Structure

```
ai-agent/
├── backend/
│   ├── admin_frontend_integration.py
│   ├── admin_api_proxy.py
│   ├── admin_auth_proxy.py
│   └── test_admin_frontend_integration.py
├── admin-dashboard/
│   └── frontend/
│       ├── index.html (updated)
│       ├── tickets.html (updated)
│       ├── register.html (new)
│       └── js/
│           ├── unified_api.js (new)
│           └── auth.js (updated)
└── main.py (updated)
```

## Testing

Run integration tests:

```bash
python -m pytest backend/test_admin_frontend_integration.py -v
```

## Security Considerations

1. **Session Management**: Uses secure session cookies with proper settings
2. **CSRF Protection**: SameSite cookie attribute prevents CSRF attacks
3. **Admin Access Control**: All admin endpoints require admin role verification
4. **Input Validation**: All API endpoints validate input data
5. **Error Handling**: Proper error responses without sensitive information

## Configuration

The integration uses existing configuration from the main application:

- **Database**: Uses the same unified database models
- **Authentication**: Uses the unified authentication system
- **Logging**: Integrated with main application logging
- **CORS**: Uses existing CORS configuration

## Troubleshooting

### Common Issues

1. **404 on Admin Routes**: Check if admin frontend files exist in `admin-dashboard/frontend/`
2. **Authentication Errors**: Verify unified authentication system is working
3. **API Errors**: Check database connection and unified models
4. **Static File Issues**: Verify file paths and permissions

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger('backend.admin_frontend_integration').setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Real-time Updates**: WebSocket integration for live updates
2. **Advanced Filtering**: Enhanced filtering and search capabilities
3. **Bulk Operations**: Bulk ticket and user management
4. **Analytics Dashboard**: Advanced analytics and reporting
5. **Mobile Responsiveness**: Enhanced mobile support

## Requirements Fulfilled

This integration fulfills the following requirements from the specification:

- ✅ **6.1**: Admin dashboard routes served through main application
- ✅ **6.2**: Unified configuration and environment variables
- ✅ **6.3**: Single deployment process for both systems
- ✅ **6.4**: Static files served through main application

The admin dashboard is now fully integrated with the main FastAPI application, providing a seamless experience for administrators while maintaining the existing functionality of both systems.