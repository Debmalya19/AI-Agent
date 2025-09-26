# Unified Database Models and Migration System

This document describes the unified database models and migration system that merges the admin dashboard and main backend databases into a single, cohesive system.

## Overview

The unified database system provides:
- **Single source of truth** for all user, ticket, and system data
- **Seamless integration** between AI agent backend and admin dashboard
- **Data preservation** during migration from legacy systems
- **Comprehensive validation** to ensure data integrity
- **Backward compatibility** with existing systems during transition

## Architecture

### Unified Models

The unified models are located in `backend/unified_models.py` and include:

#### Core Models
- **UnifiedUser**: Combines backend User and Customer models with admin dashboard User
- **UnifiedTicket**: Enhanced ticket model with features from both systems
- **UnifiedTicketComment**: Unified comment system supporting both manual and AI interactions
- **UnifiedTicketActivity**: Comprehensive activity tracking across all systems

#### Extended Models
- **UnifiedUserSession**: Session management for authentication
- **UnifiedChatSession/UnifiedChatMessage**: Real-time chat functionality
- **UnifiedPerformanceMetric**: Agent performance tracking
- **UnifiedCustomerSatisfaction**: Customer feedback and ratings
- **UnifiedVoiceSettings/UnifiedVoiceAnalytics**: Voice assistant integration
- **UnifiedKnowledgeEntry**: Knowledge base management
- **UnifiedSupportIntent/UnifiedSupportResponse**: AI support system

### Key Features

#### 1. Enhanced User Model
```python
class UnifiedUser(Base):
    # Core identification
    user_id = Column(String(50), unique=True, index=True)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    
    # Role-based access control
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER)
    is_admin = Column(Boolean, default=False)
    
    # Migration tracking
    legacy_customer_id = Column(Integer, nullable=True)
    legacy_admin_user_id = Column(Integer, nullable=True)
```

#### 2. Enhanced Ticket Model
```python
class UnifiedTicket(Base):
    # Enhanced status tracking
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM)
    category = Column(Enum(TicketCategory), default=TicketCategory.GENERAL)
    
    # Flexible assignment
    customer_id = Column(Integer, ForeignKey("unified_users.id"))
    assigned_agent_id = Column(Integer, ForeignKey("unified_users.id"))
    
    # Migration tracking
    legacy_backend_ticket_id = Column(Integer, nullable=True)
    legacy_admin_ticket_id = Column(Integer, nullable=True)
```

## Migration System

### Components

#### 1. Model Adapters (`backend/model_adapters.py`)
- **UserAdapter**: Converts between legacy User/Customer models and UnifiedUser
- **TicketAdapter**: Handles ticket model conversion with enum mapping
- **CommentAdapter**: Manages comment field mapping (comment vs content)
- **ActivityAdapter**: Converts activity models with proper relationships

#### 2. Migration System (`backend/migration_system.py`)
- **DataMigrator**: Main migration orchestrator
- **DatabaseConnector**: Handles connections to different database types
- **MigrationStats**: Tracks migration progress and results

#### 3. Data Validation (`backend/data_validation.py`)
- **ModelValidator**: Validates individual model instances
- **DatabaseValidator**: Validates database-wide integrity
- **MigrationValidator**: Validates migration-specific integrity

### Migration Process

1. **Backup Creation**: Optional backup of existing databases
2. **Table Creation**: Create unified database schema
3. **User Migration**: Migrate and merge users from both systems
4. **Ticket Migration**: Convert tickets with proper relationship mapping
5. **Comment/Activity Migration**: Preserve all historical data
6. **Validation**: Comprehensive integrity checks
7. **Cleanup**: Remove temporary migration artifacts

### Running Migration

#### Command Line Interface
```bash
# Run migration with backup
python backend/migrate_database.py migrate --backup

# Run migration without backup (faster)
python backend/migrate_database.py migrate --no-backup

# Dry run to see what would be migrated
python backend/migrate_database.py migrate --dry-run

# Validate database after migration
python backend/migrate_database.py validate --migration

# Check migration status
python backend/migrate_database.py status
```

#### Programmatic Usage
```python
from backend.migration_system import run_migration, validate_migration

# Run migration
stats = run_migration(backup=True)
print(f"Migrated {stats.users_migrated} users, {stats.tickets_migrated} tickets")

# Validate results
validation_result = validate_migration()
if validation_result['valid']:
    print("Migration successful!")
```

## Data Validation

### Validation Levels

#### 1. Field Validation
- Email format validation
- Phone number format checking
- Username format requirements
- Text length constraints
- Datetime range validation

#### 2. Model Validation
- Required field checking
- Enum value validation
- Business rule enforcement
- Cross-field consistency

#### 3. Database Validation
- Foreign key integrity
- Duplicate detection
- Orphaned record identification
- Relationship consistency

#### 4. Migration Validation
- Legacy ID preservation
- Data completeness checking
- Conflict detection
- Statistics verification

### Example Validation
```python
from backend.data_validation import validate_model_instance, validate_database
from backend.database import SessionLocal

# Validate a single model
user = UnifiedUser(username="test", email="test@example.com")
result = validate_model_instance(user)
if not result.is_valid:
    print("Validation errors:", result.errors)

# Validate entire database
with SessionLocal() as session:
    result = validate_database(session)
    print(f"Database valid: {result.is_valid}")
```

## Testing

### Unit Tests
Run the unified models test suite:
```bash
python backend/test_unified_models.py
```

This test suite verifies:
- Table creation
- Model instantiation
- Relationship functionality
- Validation rules
- Data persistence

### Integration Tests
The migration system includes comprehensive integration tests that:
- Test migration from sample data
- Verify data integrity after migration
- Validate relationship preservation
- Check performance under load

## Configuration

### Database Configuration
The unified models use the same database configuration as the main backend:

```python
# backend/database.py
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/knowledge_base"
)
```

### Migration Configuration
Migration behavior can be configured through environment variables:

```bash
# Enable detailed migration logging
export MIGRATION_LOG_LEVEL=DEBUG

# Specify backup directory
export MIGRATION_BACKUP_DIR=/path/to/backups

# Configure batch size for large migrations
export MIGRATION_BATCH_SIZE=1000
```

## Troubleshooting

### Common Issues

#### 1. Import Errors
If you encounter import errors when running migration:
```bash
# Ensure you're in the correct directory
cd ai-agent

# Check Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run migration
python backend/migrate_database.py migrate
```

#### 2. Database Connection Issues
- Verify PostgreSQL is running
- Check database credentials in `.env` file
- Ensure database exists and is accessible

#### 3. Migration Conflicts
If migration fails due to data conflicts:
```bash
# Run validation to identify issues
python backend/migrate_database.py validate

# Check migration logs for specific errors
python backend/migrate_database.py migrate --log-level DEBUG
```

#### 4. Performance Issues
For large datasets:
- Use `--no-backup` flag to skip backup creation
- Run migration during low-traffic periods
- Monitor database performance during migration

### Recovery Procedures

#### 1. Rollback Migration
If migration fails and you need to rollback:
1. Restore from backup (if created)
2. Drop unified tables: `DROP SCHEMA unified CASCADE;`
3. Restart original systems

#### 2. Partial Migration Recovery
If migration partially completes:
1. Run validation to assess current state
2. Use migration stats to identify completed components
3. Re-run migration with appropriate flags

## Best Practices

### Before Migration
1. **Create backups** of all databases
2. **Test migration** on a copy of production data
3. **Plan downtime** for the migration window
4. **Notify users** of the maintenance window

### During Migration
1. **Monitor progress** using migration stats
2. **Watch for errors** in migration logs
3. **Validate incrementally** if migration is large
4. **Keep original systems** running until validation completes

### After Migration
1. **Run comprehensive validation** on migrated data
2. **Test application functionality** with unified models
3. **Monitor performance** of the unified system
4. **Keep backups** until system is stable

## Performance Considerations

### Database Optimization
- **Indexes**: Unified models include appropriate indexes for common queries
- **Foreign Keys**: Proper foreign key constraints ensure referential integrity
- **Partitioning**: Consider partitioning large tables by date for better performance

### Migration Optimization
- **Batch Processing**: Large datasets are processed in batches to avoid memory issues
- **Parallel Processing**: Independent migrations can run in parallel
- **Connection Pooling**: Efficient database connection management

### Query Optimization
- **Relationship Loading**: Use appropriate loading strategies (lazy/eager) for relationships
- **Query Optimization**: Unified models support efficient queries across related data
- **Caching**: Consider implementing caching for frequently accessed data

## Security Considerations

### Data Protection
- **Password Hashing**: User passwords are properly hashed and never stored in plain text
- **PII Handling**: Personal information is handled according to privacy requirements
- **Access Control**: Role-based access control prevents unauthorized data access

### Migration Security
- **Backup Encryption**: Database backups should be encrypted
- **Secure Connections**: Use encrypted connections for database access
- **Audit Logging**: All migration activities are logged for audit purposes

## Future Enhancements

### Planned Features
1. **Real-time Sync**: Live synchronization between systems during transition
2. **Incremental Migration**: Support for migrating data in phases
3. **Advanced Validation**: Machine learning-based data quality assessment
4. **Performance Monitoring**: Built-in performance monitoring and alerting

### Extension Points
- **Custom Adapters**: Framework for adding new model adapters
- **Plugin System**: Support for custom migration plugins
- **Event Hooks**: Hooks for custom logic during migration phases
- **API Integration**: REST API for migration management and monitoring

## Support

For issues or questions regarding the unified models and migration system:

1. **Check Logs**: Review migration and application logs for error details
2. **Run Validation**: Use the validation tools to identify specific issues
3. **Consult Documentation**: Review this README and inline code documentation
4. **Test Environment**: Reproduce issues in a test environment when possible

## Changelog

### Version 1.0.0
- Initial implementation of unified models
- Complete migration system with validation
- Command-line interface for migration management
- Comprehensive test suite
- Documentation and troubleshooting guides