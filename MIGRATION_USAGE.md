# PostgreSQL Migration Script Usage

This document provides instructions for using the comprehensive PostgreSQL migration script.

## Overview

The migration script (`scripts/migrate_to_postgresql.py`) provides:
- Complete data export from SQLite with proper data type handling
- PostgreSQL data import with referential integrity preservation
- Data validation and integrity checking
- Migration rollback capabilities
- Detailed logging and progress tracking

## Prerequisites

1. **PostgreSQL Database Setup**
   - PostgreSQL server running and accessible
   - Database created for the application
   - User with appropriate permissions

2. **Environment Configuration**
   - Update `DATABASE_URL` in `.env` file to point to PostgreSQL
   - Example: `DATABASE_URL=postgresql://username:password@localhost:5432/ai_agent`

3. **Dependencies**
   - All required Python packages installed (`pip install -r requirements.txt`)
   - `psycopg2` for PostgreSQL connectivity

## Usage

### 1. Validate Migration Script

Before running the actual migration, validate the script:

```bash
python validate_migration_script.py
```

This will:
- Check database connections
- Test data export functionality
- Validate data type processing
- Verify backup functionality

### 2. Run Migration

Execute the migration script:

```bash
python scripts/migrate_to_postgresql.py
```

The script will:
1. Create a backup of the SQLite database
2. Export data from all SQLite tables
3. Import data to PostgreSQL with proper type conversion
4. Validate data integrity and referential constraints
5. Generate detailed migration report
6. Create rollback script for emergency recovery

### 3. Monitor Progress

The script provides detailed logging:
- Console output shows real-time progress
- `migration.log` file contains detailed logs
- Migration report saved as `migration_report_YYYYMMDD_HHMMSS.txt`
- JSON report saved as `migration_report_YYYYMMDD_HHMMSS.json`

## Configuration Options

The migration can be customized by modifying the `MigrationConfig` in the script:

```python
config = MigrationConfig(
    sqlite_url="sqlite:///ai_agent.db",
    postgresql_url=os.getenv("DATABASE_URL"),
    backup_dir="migration_backups",      # Backup directory
    batch_size=1000,                     # Records per batch
    validate_data=True,                  # Enable data validation
    create_rollback=True,                # Create rollback script
    preserve_ids=True                    # Preserve original IDs
)
```

## Migration Process

### Tables Migrated (in dependency order)

1. **Legacy Models**
   - knowledge_entries
   - customers
   - users, user_sessions
   - voice_settings, voice_analytics
   - tickets, ticket_comments, ticket_activities
   - orders
   - support_intents, support_responses
   - chat_history

2. **Unified Models**
   - unified_users, unified_user_sessions
   - unified_tickets, unified_ticket_comments, unified_ticket_activities
   - unified_chat_sessions, unified_chat_messages
   - unified_performance_metrics, unified_customer_satisfaction
   - unified_voice_settings, unified_voice_analytics
   - unified_knowledge_entries, unified_orders
   - unified_support_intents, unified_support_responses
   - unified_chat_history
   - diagnostic_error_logs

3. **Memory Models**
   - enhanced_chat_history
   - memory_context_cache
   - tool_usage_metrics
   - conversation_summaries
   - memory_configuration, memory_health_metrics
   - enhanced_user_sessions
   - data_processing_consent, data_subject_rights

### Data Type Conversions

- `INTEGER` → `INTEGER`
- `TEXT` → `TEXT`
- `REAL` → `REAL`
- `BLOB` → `BYTEA`
- `DATETIME` → `TIMESTAMP WITH TIME ZONE`
- `JSON` → `JSONB` (for better performance)
- `BOOLEAN` → `BOOLEAN`

## Rollback Procedure

If migration needs to be reversed:

1. **Automatic Rollback Script**
   ```bash
   psql -d ai_agent -f migration_backups/rollback_YYYYMMDD_HHMMSS.sql
   ```

2. **Manual Rollback**
   - Truncate PostgreSQL tables
   - Restore SQLite database from backup
   - Update `DATABASE_URL` back to SQLite

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Verify PostgreSQL is running
   - Check DATABASE_URL format
   - Ensure user has proper permissions

2. **Data Type Errors**
   - Review migration logs for specific errors
   - Check for incompatible data in source tables
   - Verify PostgreSQL schema matches expectations

3. **Foreign Key Violations**
   - Migration handles dependencies automatically
   - Check for orphaned records in source data
   - Review referential integrity validation results

4. **Memory Issues**
   - Reduce batch_size in configuration
   - Ensure sufficient system memory
   - Monitor PostgreSQL memory usage

### Log Analysis

Check these log files for detailed information:
- `migration.log` - Detailed migration logs
- `migration_report_*.txt` - Human-readable report
- `migration_report_*.json` - Machine-readable report

### Validation Failures

If validation fails:
1. Review validation results in migration report
2. Check referential integrity issues
3. Verify record counts match between databases
4. Examine specific error messages in logs

## Post-Migration Steps

1. **Update Application Configuration**
   - Ensure `DATABASE_URL` points to PostgreSQL
   - Restart application services
   - Verify all functionality works

2. **Performance Optimization**
   - Run `ANALYZE` on PostgreSQL tables
   - Monitor query performance
   - Adjust connection pool settings if needed

3. **Backup Strategy**
   - Set up regular PostgreSQL backups
   - Archive SQLite backup files
   - Document recovery procedures

## Support

For issues or questions:
1. Check migration logs for specific error messages
2. Review this documentation
3. Validate script functionality with test script
4. Check PostgreSQL and application logs

## Files Created

- `migration_backups/sqlite_backup_*.db` - SQLite backup
- `migration_backups/rollback_*.sql` - Rollback script
- `migration.log` - Detailed migration logs
- `migration_report_*.txt` - Human-readable report
- `migration_report_*.json` - JSON report for automation