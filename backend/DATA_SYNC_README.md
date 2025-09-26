# Data Synchronization Service

This document describes the data synchronization service that provides real-time sync between AI agent conversations and support tickets, background tasks for data consistency checks, and utilities for converting conversations to tickets.

## Overview

The data synchronization service ensures that customer data, support tickets, and AI agent conversations remain consistent across the integrated system. It implements the requirements:

- **2.1**: Same information visible in both admin dashboard and main backend
- **2.2**: Support tickets created in either system visible in both
- **2.3**: Customer data updated in one system reflected in other immediately  
- **2.4**: Search results include data from all integrated sources

## Architecture

### Core Components

1. **DataSyncService** (`data_sync_service.py`)
   - Main synchronization service
   - Handles real-time sync operations
   - Manages background consistency checks
   - Provides conflict resolution

2. **EventDrivenSyncManager** (`sync_events.py`)
   - Event-driven synchronization using database triggers
   - SQLAlchemy event listeners
   - Application-level event handling

3. **ConversationAnalyzer** (`conversation_to_ticket_utils.py`)
   - Analyzes AI conversations for ticket creation potential
   - Extracts metadata and categorizes conversations
   - Provides intelligent ticket creation recommendations

4. **DataSyncIntegration** (`data_sync_integration.py`)
   - Integration with main FastAPI application
   - API endpoints for monitoring and control
   - Startup/shutdown lifecycle management

## Features

### Real-time Synchronization

- **Conversation to Ticket Linking**: Automatically links AI conversations to support tickets
- **Ticket Creation**: Creates support tickets from AI conversations when needed
- **User Data Sync**: Synchronizes user data across systems
- **Status Updates**: Propagates ticket status changes to related conversations

### Background Tasks

- **Consistency Checks**: Periodic validation of data integrity
- **Conflict Resolution**: Automatic resolution of data conflicts
- **Event Processing**: Background processing of synchronization events
- **Cleanup**: Removal of old sync events and temporary data

### Event-Driven Architecture

- **Database Triggers**: PostgreSQL triggers for real-time data change detection
- **SQLAlchemy Events**: Application-level event handling
- **Custom Event Handlers**: Extensible event handling system
- **Automatic Actions**: Smart automation based on conversation content

## Usage

### Starting the Service

```python
from backend.data_sync_integration import startup_data_sync, shutdown_data_sync

# In your FastAPI lifespan function
async def lifespan(app: FastAPI):
    # Startup
    await startup_data_sync()
    
    yield
    
    # Shutdown
    await shutdown_data_sync()
```

### API Endpoints

The service provides REST API endpoints for monitoring and control:

- `GET /api/sync/status` - Get service status
- `POST /api/sync/consistency-check` - Trigger manual consistency check
- `POST /api/sync/conversations/{id}/analyze` - Analyze conversation for ticket potential
- `POST /api/sync/conversations/{id}/create-ticket` - Create ticket from conversation
- `POST /api/sync/conversations/{id}/link-ticket/{ticket_id}` - Link conversation to existing ticket
- `POST /api/sync/tickets/{id}/status` - Update ticket status
- `GET /api/sync/users/{id}/sync` - Sync user data
- `GET /api/sync/events/recent` - Get recent sync events

### Programmatic Usage

```python
from backend.data_sync_service import (
    sync_conversation_to_ticket,
    create_ticket_from_conversation,
    sync_user_data,
    handle_ticket_status_change
)

# Create ticket from conversation
result = create_ticket_from_conversation(conversation_id)
if result.success:
    print(f"Created ticket {result.entity_id}")

# Link existing conversation to ticket
result = sync_conversation_to_ticket(conversation_id, ticket_id)

# Sync user data
result = sync_user_data(user_id)

# Handle ticket status change
result = handle_ticket_status_change(ticket_id, TicketStatus.RESOLVED, user_id)
```

### Conversation Analysis

```python
from backend.conversation_to_ticket_utils import (
    analyze_conversation_for_ticket,
    should_create_ticket_from_conversation
)

# Analyze conversation
analysis = analyze_conversation_for_ticket(conversation_id)
print(f"Analysis result: {analysis.analysis_result}")
print(f"Confidence: {analysis.confidence_score}")

# Check if ticket should be created
if should_create_ticket_from_conversation(conversation_id, threshold=0.7):
    # Create ticket
    result = create_ticket_from_conversation(conversation_id)
```

## Configuration

### Environment Variables

- `DATABASE_URL` - PostgreSQL database connection string
- `SYNC_CONSISTENCY_CHECK_INTERVAL` - Hours between consistency checks (default: 1)
- `SYNC_EVENT_CLEANUP_INTERVAL` - Hours between event cleanup (default: 6)
- `SYNC_AUTO_TICKET_THRESHOLD` - Confidence threshold for auto ticket creation (default: 0.7)

### Database Setup

The service requires PostgreSQL with the unified models schema. Database triggers are automatically created for real-time synchronization.

## Monitoring

### Service Status

Monitor the service status through the API:

```bash
curl http://localhost:8000/api/sync/status
```

Response:
```json
{
  "service_running": true,
  "initialized": true,
  "background_tasks": 3,
  "queued_events": 5,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Consistency Checks

Trigger manual consistency checks:

```bash
curl -X POST http://localhost:8000/api/sync/consistency-check
```

### Recent Events

View recent synchronization events:

```bash
curl http://localhost:8000/api/sync/events/recent?limit=10
```

## Data Flow

### Conversation to Ticket Flow

1. **AI Conversation Created**: User interacts with AI agent
2. **Event Detection**: SQLAlchemy event listener detects new conversation
3. **Analysis**: ConversationAnalyzer evaluates if ticket is needed
4. **Ticket Creation**: If needed, ticket is automatically created
5. **Linking**: Conversation is linked to ticket
6. **Synchronization**: Related data is synchronized across systems

### Ticket Status Change Flow

1. **Status Update**: Ticket status is changed (via API or admin dashboard)
2. **Event Trigger**: Database trigger detects status change
3. **Propagation**: Status change is propagated to related conversations
4. **Activity Logging**: Activity record is created
5. **Notification**: Relevant parties are notified of the change

## Error Handling

### Conflict Resolution Strategies

- **Latest Wins**: Most recent update takes precedence
- **Manual Review**: Conflicts flagged for human review
- **Merge Data**: Intelligent merging of conflicting data
- **Preserve Both**: Keep both versions with conflict markers

### Error Recovery

- **Automatic Retry**: Transient errors are automatically retried
- **Fallback Modes**: Service continues with reduced functionality if components fail
- **Error Logging**: Comprehensive error logging for debugging
- **Health Monitoring**: Background health checks detect and report issues

## Testing

Run the test suite:

```bash
pytest backend/test_data_sync_service.py -v
```

Test categories:
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Consistency Tests**: Data integrity validation
- **Performance Tests**: Load and stress testing

## Performance Considerations

### Optimization Strategies

- **Batch Processing**: Events processed in batches for efficiency
- **Connection Pooling**: Database connection pooling for scalability
- **Async Operations**: Non-blocking operations where possible
- **Caching**: Intelligent caching of frequently accessed data

### Scaling

- **Horizontal Scaling**: Service can run on multiple instances
- **Database Sharding**: Support for database partitioning
- **Event Queuing**: External queue systems for high-volume events
- **Load Balancing**: Distribute sync operations across instances

## Security

### Data Protection

- **Encryption**: Sensitive data encrypted in transit and at rest
- **Access Control**: Role-based access to sync operations
- **Audit Logging**: Complete audit trail of all sync operations
- **Data Validation**: Input validation and sanitization

### Authentication

- **JWT Tokens**: Secure token-based authentication
- **API Keys**: Service-to-service authentication
- **Rate Limiting**: Protection against abuse
- **CORS**: Proper cross-origin resource sharing configuration

## Troubleshooting

### Common Issues

1. **Service Not Starting**
   - Check database connectivity
   - Verify environment variables
   - Review startup logs

2. **High Memory Usage**
   - Check queued events count
   - Verify cleanup tasks are running
   - Monitor background task health

3. **Sync Delays**
   - Check database performance
   - Monitor event processing rate
   - Verify network connectivity

4. **Data Inconsistencies**
   - Run manual consistency check
   - Review conflict resolution logs
   - Check for failed sync operations

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('backend.data_sync_service').setLevel(logging.DEBUG)
```

### Health Checks

The service provides health check endpoints for monitoring:

- Service status
- Background task health
- Database connectivity
- Event queue status

## Future Enhancements

### Planned Features

- **Real-time Notifications**: WebSocket-based real-time updates
- **Advanced Analytics**: Machine learning-based sync optimization
- **Multi-tenant Support**: Tenant-aware synchronization
- **External Integrations**: Sync with external CRM/ticketing systems

### Performance Improvements

- **Streaming Processing**: Stream-based event processing
- **Distributed Caching**: Redis-based distributed caching
- **Message Queues**: RabbitMQ/Kafka for event processing
- **Database Optimization**: Advanced indexing and query optimization

## Contributing

When contributing to the data synchronization service:

1. **Follow Patterns**: Use existing patterns for new sync operations
2. **Add Tests**: Include comprehensive tests for new features
3. **Update Documentation**: Keep documentation current
4. **Performance Testing**: Validate performance impact of changes
5. **Security Review**: Ensure security best practices are followed

## Support

For issues or questions about the data synchronization service:

1. Check the troubleshooting section
2. Review the test suite for examples
3. Check application logs for error details
4. Monitor service health through API endpoints