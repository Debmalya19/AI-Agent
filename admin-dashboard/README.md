# Admin Dashboard

A comprehensive customer support and administration dashboard integrated with the AI Agent backend system.

## Overview

This admin dashboard provides a complete interface for managing customer support tickets, user accounts, and system administration. It seamlessly integrates with the AI Agent backend system to provide a unified experience for support agents and administrators.

## Features

- **User Authentication**: Secure login and registration system with role-based access control
- **Ticket Management**: Create, update, and track support tickets with priority, category, and status
- **Admin Dashboard**: View system statistics, user management, and performance metrics
- **AI Agent Integration**: Seamless integration with the AI Agent backend for enhanced support capabilities
- **Performance Metrics**: Track support team performance and customer satisfaction

## Integration with AI Agent Backend

This dashboard is designed to work seamlessly with the AI Agent backend system. The integration provides the following capabilities:

- **Ticket Synchronization**: Support tickets are automatically synced between the admin dashboard and AI Agent backend
- **Customer Data Sharing**: Customer information is shared between systems to provide a unified view
- **Status Monitoring**: Real-time monitoring of the AI Agent backend status
- **Enhanced Analytics**: Combined analytics from both systems for comprehensive reporting

## Directory Structure

```
admin-dashboard/
├── backend/            # Flask backend API
│   ├── app.py          # Main application entry point
│   ├── models.py       # Database models for users
│   ├── models_support.py # Database models for support system
│   ├── auth.py         # Authentication routes and middleware
│   ├── admin.py        # Admin dashboard routes
│   ├── support.py      # Support ticket management routes
│   ├── integration.py  # Integration with AI Agent backend
│   └── config.py       # Application configuration
└── frontend/          # Frontend assets
    ├── admin/          # Admin dashboard interface
    ├── css/            # Stylesheets
    └── js/             # JavaScript files
```

## Setup and Installation

1. Ensure the AI Agent backend is properly set up and running
2. Configure the integration settings in `config.py`
3. Install dependencies: `pip install -r requirements.txt`
4. Initialize the database: `flask db upgrade`
5. Start the application: `python app.py`

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/profile` - Get current user profile

### Support
- `GET /support/tickets` - Get all tickets (with filtering)
- `POST /support/tickets` - Create a new ticket
- `GET /support/tickets/<id>` - Get a specific ticket
- `PUT /support/tickets/<id>` - Update a ticket
- `POST /support/tickets/<id>/comments` - Add a comment to a ticket

### Admin
- `GET /admin/dashboard` - Get admin dashboard statistics
- `GET /admin/users` - Get all users (admin only)
- `GET /admin/system/status` - Get system status information
- `POST /admin/system/sync-with-ai-agent` - Manually trigger synchronization

## Integration Configuration

The integration with the AI Agent backend is configured in `config.py`. The following settings are available:

- `AI_AGENT_BACKEND_URL` - The URL of the AI Agent backend API
- `AI_AGENT_BACKEND_AVAILABLE` - Flag indicating if the integration is available

## Development

- Run in development mode: `FLASK_ENV=development python app.py`
- Run tests: `pytest`

## License

This project is proprietary and confidential.