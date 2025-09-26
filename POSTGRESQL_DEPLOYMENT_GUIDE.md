# PostgreSQL Deployment Guide

## Overview
This guide provides comprehensive instructions for deploying the AI Agent application with PostgreSQL as the database backend.

## Prerequisites

### System Requirements
- PostgreSQL 12+ (recommended: PostgreSQL 17.5)
- Python 3.8+
- Minimum 4GB RAM
- 20GB available disk space

### Required Software
- PostgreSQL server
- Python with pip
- Git (for deployment)

## PostgreSQL Setup

### 1. Install PostgreSQL

#### Windows
```bash
# Download and install from https://www.postgresql.org/download/windows/
# Or using chocolatey:
choco install postgresql
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

#### macOS
```bash
# Using Homebrew:
brew install postgresql
brew services start postgresql
```

### 2. Create Database and User

```sql
-- Connect to PostgreSQL as superuser
sudo -u postgres psql

-- Create database
CREATE DATABASE ai_agent;

-- Create user with password
CREATE USER ai_agent_user WITH PASSWORD 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ai_agent TO ai_agent_user;

-- Grant schema privileges
\c ai_agent
GRANT ALL ON SCHEMA public TO ai_agent_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_agent_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_agent_user;

-- Exit PostgreSQL
\q
```

### 3. Configure PostgreSQL

Edit PostgreSQL configuration files:

#### postgresql.conf
```ini
# Connection settings
listen_addresses = '*'
port = 5432
max_connections = 100

# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# Logging
log_statement = 'all'
log_duration = on
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '

# Performance
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

#### pg_hba.conf
```ini
# Add authentication rules
local   ai_agent        ai_agent_user                     md5
host    ai_agent        ai_agent_user   127.0.0.1/32      md5
host    ai_agent        ai_agent_user   ::1/128           md5
```

Restart PostgreSQL after configuration changes:
```bash
# Linux
sudo systemctl restart postgresql

# Windows
net stop postgresql-x64-17
net start postgresql-x64-17

# macOS
brew services restart postgresql
```

## Application Deployment

### 1. Environment Configuration

Create or update `.env` file:
```env
# Database Configuration
DATABASE_URL=postgresql://ai_agent_user:your_secure_password@localhost:5432/ai_agent

# Application Configuration
SECRET_KEY=your_secret_key_here
DEBUG=False
ENVIRONMENT=production

# Optional: Test Database (for running tests)
TEST_DATABASE_URL=postgresql://ai_agent_user:your_secure_password@localhost:5432/test_ai_agent
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Schema Creation

```bash
# Create database schema
python create_postgresql_schema.py

# Verify schema creation
python -c "from backend.database import create_database_engine; engine = create_database_engine(); print('Schema created successfully')"
```

## Data Migration

### 1. Pre-Migration Checklist

- [ ] PostgreSQL server is running and accessible
- [ ] Database and user are created with proper permissions
- [ ] Application dependencies are installed
- [ ] Environment variables are configured
- [ ] SQLite database backup is created

### 2. Execute Migration

```bash
# Run complete migration with validation
python execute_complete_migration.py
```

The migration script will:
1. Validate prerequisites
2. Clean target database
3. Migrate all data from SQLite to PostgreSQL
4. Validate data integrity
5. Test application functionality
6. Generate comprehensive reports

### 3. Verify Migration Success

Check the migration output for:
- ✅ All tables migrated successfully
- ✅ All records migrated correctly
- ✅ Data integrity validation passed
- ✅ Application functionality tests passed

## Post-Migration Validation

### 1. Database Connectivity Test

```bash
python -c "
from backend.database import create_database_engine
engine = create_database_engine()
with engine.connect() as conn:
    result = conn.execute('SELECT version()')
    print('PostgreSQL version:', result.fetchone()[0])
"
```

### 2. Application Functionality Test

```bash
# Run comprehensive tests
python -m pytest tests/test_postgresql_migration.py -v

# Test specific functionality
python -c "
from backend.unified_models import UnifiedUser
from backend.database import get_db
db = next(get_db())
users = db.query(UnifiedUser).all()
print(f'Found {len(users)} users in PostgreSQL')
"
```

### 3. Performance Validation

```bash
# Run performance tests
python -m pytest tests/test_migration_performance_benchmarks.py -v
```

## Production Configuration

### 1. Security Hardening

#### Database Security
```sql
-- Revoke unnecessary privileges
REVOKE ALL ON SCHEMA information_schema FROM PUBLIC;
REVOKE ALL ON SCHEMA pg_catalog FROM PUBLIC;

-- Create read-only user for monitoring
CREATE USER monitoring_user WITH PASSWORD 'monitoring_password';
GRANT CONNECT ON DATABASE ai_agent TO monitoring_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO monitoring_user;
```

#### Application Security
```env
# Use strong passwords
DATABASE_URL=postgresql://ai_agent_user:very_strong_password@localhost:5432/ai_agent

# Disable debug mode
DEBUG=False

# Use secure secret key
SECRET_KEY=generate_a_very_long_random_secret_key_here
```

### 2. Performance Optimization

#### Connection Pooling
The application is configured with optimized connection pooling:
- Base pool size: 20 connections
- Max overflow: 30 connections
- Connection recycling: 3600 seconds

#### Database Indexes
Ensure all performance indexes are created:
```sql
-- User lookup indexes
CREATE INDEX IF NOT EXISTS idx_unified_users_username ON unified_users(username);
CREATE INDEX IF NOT EXISTS idx_unified_users_email ON unified_users(email);

-- Session management indexes
CREATE INDEX IF NOT EXISTS idx_unified_user_sessions_user_id ON unified_user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_unified_user_sessions_active ON unified_user_sessions(is_active);

-- Ticket management indexes
CREATE INDEX IF NOT EXISTS idx_unified_tickets_customer_id ON unified_tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_unified_tickets_status ON unified_tickets(status);

-- Chat history indexes
CREATE INDEX IF NOT EXISTS idx_unified_chat_history_user_id ON unified_chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_unified_chat_history_timestamp ON unified_chat_history(timestamp);
```

### 3. Monitoring Setup

#### Health Check Endpoint
The application includes health check endpoints:
- `/health` - Basic application health
- `/health/database` - Database connectivity check
- `/health/detailed` - Comprehensive system status

#### Logging Configuration
```python
# Configure logging for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/ai_agent.log',
        },
        'database': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'logs/database.log',
        },
    },
    'loggers': {
        'ai-agent.database': {
            'handlers': ['database'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Backup and Recovery

### 1. Database Backup

#### Automated Backup Script
```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="ai_agent_backup_${DATE}.sql"

# Create backup
pg_dump -h localhost -U ai_agent_user -d ai_agent > "${BACKUP_DIR}/${BACKUP_FILE}"

# Compress backup
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

# Keep only last 7 days of backups
find "${BACKUP_DIR}" -name "ai_agent_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

#### Schedule Backups
```bash
# Add to crontab for daily backups at 2 AM
0 2 * * * /path/to/backup_database.sh
```

### 2. Recovery Procedures

#### Full Database Restore
```bash
# Stop application
systemctl stop ai-agent

# Drop and recreate database
sudo -u postgres psql -c "DROP DATABASE ai_agent;"
sudo -u postgres psql -c "CREATE DATABASE ai_agent OWNER ai_agent_user;"

# Restore from backup
gunzip -c /path/to/backups/ai_agent_backup_YYYYMMDD_HHMMSS.sql.gz | \
    psql -h localhost -U ai_agent_user -d ai_agent

# Start application
systemctl start ai-agent
```

#### Point-in-Time Recovery
```bash
# Enable WAL archiving in postgresql.conf
archive_mode = on
archive_command = 'cp %p /path/to/wal_archive/%f'

# Create base backup
pg_basebackup -D /path/to/base_backup -Ft -z -P -U ai_agent_user

# Recovery to specific time
# (Restore base backup and configure recovery.conf)
```

## Troubleshooting

### Common Issues

#### Connection Issues
```bash
# Check PostgreSQL status
systemctl status postgresql

# Check port availability
netstat -an | grep 5432

# Test connection
psql -h localhost -U ai_agent_user -d ai_agent -c "SELECT 1;"
```

#### Permission Issues
```sql
-- Grant missing permissions
GRANT ALL PRIVILEGES ON DATABASE ai_agent TO ai_agent_user;
GRANT ALL ON SCHEMA public TO ai_agent_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_agent_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_agent_user;
```

#### Performance Issues
```sql
-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Check connection usage
SELECT count(*) as connections, state 
FROM pg_stat_activity 
GROUP BY state;
```

### Log Analysis

#### Application Logs
```bash
# Check application logs
tail -f logs/ai_agent.log

# Check database logs
tail -f logs/database.log

# Check PostgreSQL logs
tail -f /var/log/postgresql/postgresql-17-main.log
```

#### Error Patterns
- Connection timeouts: Check connection pool configuration
- Lock waits: Analyze query patterns and add indexes
- Memory issues: Adjust PostgreSQL memory settings

## Rollback Procedures

### 1. Emergency Rollback to SQLite

If critical issues occur, you can rollback to SQLite:

```bash
# Stop application
systemctl stop ai-agent

# Restore SQLite database from backup
cp migration_backups/sqlite_backup_YYYYMMDD_HHMMSS.db ai_agent.db

# Update environment to use SQLite
sed -i 's/DATABASE_URL=postgresql/# DATABASE_URL=postgresql/' .env
echo "DATABASE_URL=sqlite:///ai_agent.db" >> .env

# Start application
systemctl start ai-agent
```

### 2. PostgreSQL Rollback

Use the generated rollback script:
```bash
# Execute rollback script
psql -h localhost -U ai_agent_user -d ai_agent -f migration_backups/rollback_YYYYMMDD_HHMMSS.sql
```

## Maintenance

### Regular Maintenance Tasks

#### Weekly Tasks
- Review database performance metrics
- Check backup integrity
- Monitor disk space usage
- Review application logs for errors

#### Monthly Tasks
- Update PostgreSQL statistics: `ANALYZE;`
- Vacuum database: `VACUUM ANALYZE;`
- Review and optimize slow queries
- Update database maintenance scripts

#### Quarterly Tasks
- Review and update indexes
- Analyze growth patterns and plan capacity
- Update PostgreSQL version if needed
- Review security configurations

## Support and Documentation

### Additional Resources
- [PostgreSQL Official Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy PostgreSQL Dialect](https://docs.sqlalchemy.org/en/14/dialects/postgresql.html)
- [Application-specific documentation](README.md)

### Getting Help
- Check application logs first
- Review this deployment guide
- Consult PostgreSQL documentation
- Contact system administrator or development team

## Conclusion

This deployment guide provides comprehensive instructions for successfully deploying the AI Agent application with PostgreSQL. Follow the procedures carefully and maintain regular backups to ensure a reliable production environment.