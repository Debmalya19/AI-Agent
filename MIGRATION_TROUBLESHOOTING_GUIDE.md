# PostgreSQL Migration Troubleshooting Guide

## Overview
This guide provides solutions to common issues encountered during the SQLite to PostgreSQL migration process.

## Pre-Migration Issues

### 1. PostgreSQL Connection Failures

#### Symptoms
- "Connection refused" errors
- "Authentication failed" errors
- "Database does not exist" errors

#### Solutions

**Check PostgreSQL Service Status**
```bash
# Linux
sudo systemctl status postgresql
sudo systemctl start postgresql

# Windows
net start postgresql-x64-17

# macOS
brew services status postgresql
brew services start postgresql
```

**Verify Database and User Creation**
```sql
-- Connect as superuser
sudo -u postgres psql

-- Check if database exists
\l ai_agent

-- Check if user exists
\du ai_agent_user

-- Create if missing
CREATE DATABASE ai_agent;
CREATE USER ai_agent_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE ai_agent TO ai_agent_user;
```

**Check Connection Parameters**
```bash
# Test connection manually
psql -h localhost -U ai_agent_user -d ai_agent -c "SELECT 1;"

# Verify environment variables
echo $DATABASE_URL
```

### 2. Environment Configuration Issues

#### Symptoms
- "Environment variable not found" errors
- "Invalid database URL" errors

#### Solutions

**Verify .env File**
```env
# Ensure proper format
DATABASE_URL=postgresql://username:password@host:port/database

# Example
DATABASE_URL=postgresql://ai_agent_user:password123@localhost:5432/ai_agent
```

**Check File Permissions**
```bash
# Ensure .env file is readable
chmod 644 .env

# Verify file exists
ls -la .env
```

### 3. Schema Creation Failures

#### Symptoms
- "Table already exists" errors
- "Permission denied" errors
- "Schema creation failed" errors

#### Solutions

**Grant Proper Permissions**
```sql
-- Connect to target database
\c ai_agent

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO ai_agent_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_agent_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_agent_user;

-- For future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ai_agent_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ai_agent_user;
```

**Clean Existing Schema**
```sql
-- Drop all tables if needed (CAUTION: This deletes all data)
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO ai_agent_user;
```

## Migration Execution Issues

### 1. Data Export Failures

#### Symptoms
- "SQLite database locked" errors
- "Table not found" errors
- "Export timeout" errors

#### Solutions

**Check SQLite Database**
```bash
# Verify SQLite database exists and is accessible
sqlite3 ai_agent.db ".tables"

# Check for locks
lsof ai_agent.db

# Create backup before migration
cp ai_agent.db ai_agent_backup.db
```

**Fix Database Locks**
```bash
# Stop application that might be using SQLite
pkill -f "python.*main.py"

# Wait for locks to clear
sleep 5

# Retry migration
python execute_complete_migration.py
```

### 2. Data Import Failures

#### Symptoms
- "Constraint violation" errors
- "Data type conversion" errors
- "Foreign key constraint" errors

#### Solutions

**Handle Constraint Violations**
```sql
-- Temporarily disable constraints during import
SET session_replication_role = replica;

-- Re-enable after import
SET session_replication_role = DEFAULT;
```

**Fix Data Type Issues**
```python
# Check data types in migration script
# Ensure proper type conversion for:
# - DateTime fields
# - JSON fields
# - Enum fields
# - Boolean fields
```

**Resolve Foreign Key Issues**
```sql
-- Check foreign key constraints
SELECT conname, conrelid::regclass, confrelid::regclass 
FROM pg_constraint 
WHERE contype = 'f';

-- Temporarily drop and recreate if needed
ALTER TABLE child_table DROP CONSTRAINT fk_constraint_name;
-- Import data
ALTER TABLE child_table ADD CONSTRAINT fk_constraint_name 
    FOREIGN KEY (column) REFERENCES parent_table(id);
```

### 3. Sequence Reset Issues

#### Symptoms
- "Duplicate key value violates unique constraint" errors
- Auto-increment fields not working properly

#### Solutions

**Reset Sequences Manually**
```sql
-- Find sequences that need reset
SELECT schemaname, tablename, attname, seq_name
FROM (
    SELECT schemaname, tablename, attname,
           pg_get_serial_sequence(schemaname||'.'||tablename, attname) AS seq_name
    FROM pg_attribute a
    JOIN pg_class c ON a.attrelid = c.oid
    JOIN pg_namespace n ON c.relnamespace = n.oid
    WHERE a.attnum > 0 AND NOT a.attisdropped
    AND pg_get_serial_sequence(schemaname||'.'||tablename, attname) IS NOT NULL
) AS sequences;

-- Reset specific sequence
SELECT setval('unified_users_id_seq', (SELECT MAX(id) FROM unified_users));

-- Reset all sequences
SELECT setval(seq_name, COALESCE(max_val, 1))
FROM (
    SELECT seq_name, MAX(id_val) as max_val
    FROM (
        SELECT 'unified_users_id_seq' as seq_name, MAX(id) as id_val FROM unified_users
        UNION ALL
        SELECT 'unified_tickets_id_seq', MAX(id) FROM unified_tickets
        -- Add other sequences as needed
    ) AS seq_data
    GROUP BY seq_name
) AS reset_data;
```

## Post-Migration Issues

### 1. Application Connectivity Issues

#### Symptoms
- Application fails to start
- "Database connection failed" errors
- Timeout errors

#### Solutions

**Check Connection Pool Configuration**
```python
# In backend/database.py, verify pool settings
engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

**Test Database Connection**
```python
# Test script
from backend.database import create_database_engine

try:
    engine = create_database_engine()
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print("Connection successful:", result.fetchone()[0])
except Exception as e:
    print("Connection failed:", str(e))
```

### 2. Authentication Issues

#### Symptoms
- User login failures
- "User not found" errors
- Password validation failures

#### Solutions

**Verify User Data Migration**
```sql
-- Check user count
SELECT COUNT(*) FROM unified_users;

-- Check specific user
SELECT id, username, email, is_active FROM unified_users WHERE username = 'admin';

-- Verify password hashes
SELECT username, LENGTH(password_hash) as hash_length FROM unified_users;
```

**Test Authentication Flow**
```python
# Test authentication
from backend.unified_models import UnifiedUser
from backend.database import get_db

db = next(get_db())
user = db.query(UnifiedUser).filter_by(username='admin').first()
if user:
    print(f"User found: {user.username}, Active: {user.is_active}")
else:
    print("User not found")
```

### 3. Admin Dashboard Issues

#### Symptoms
- Admin pages not loading
- "Permission denied" errors
- Data not displaying correctly

#### Solutions

**Check Admin User Permissions**
```sql
-- Verify admin users
SELECT username, is_admin, role FROM unified_users WHERE is_admin = true;

-- Check admin user data
SELECT u.username, u.is_admin, u.role, COUNT(t.id) as ticket_count
FROM unified_users u
LEFT JOIN unified_tickets t ON u.id = t.customer_id
WHERE u.is_admin = true
GROUP BY u.id, u.username, u.is_admin, u.role;
```

**Test Admin Functionality**
```python
# Test admin queries
from backend.unified_models import UnifiedUser, UnifiedTicket
from backend.database import get_db

db = next(get_db())

# Test admin user query
admin_users = db.query(UnifiedUser).filter_by(is_admin=True).all()
print(f"Admin users: {len(admin_users)}")

# Test ticket query
all_tickets = db.query(UnifiedTicket).all()
print(f"Total tickets: {len(all_tickets)}")
```

## Performance Issues

### 1. Slow Query Performance

#### Symptoms
- Application response times increased
- Database queries taking too long
- Connection pool exhaustion

#### Solutions

**Check Missing Indexes**
```sql
-- Find tables without indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
AND n_distinct > 100
AND correlation < 0.1;

-- Create missing indexes
CREATE INDEX CONCURRENTLY idx_unified_users_username ON unified_users(username);
CREATE INDEX CONCURRENTLY idx_unified_users_email ON unified_users(email);
CREATE INDEX CONCURRENTLY idx_unified_tickets_status ON unified_tickets(status);
CREATE INDEX CONCURRENTLY idx_unified_user_sessions_user_id ON unified_user_sessions(user_id);
```

**Analyze Query Performance**
```sql
-- Enable query statistics
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Analyze specific query
EXPLAIN ANALYZE SELECT * FROM unified_users WHERE username = 'admin';
```

### 2. Connection Pool Issues

#### Symptoms
- "Connection pool exhausted" errors
- "Too many connections" errors
- Application hanging

#### Solutions

**Adjust Pool Settings**
```python
# Increase pool size if needed
engine = create_engine(
    database_url,
    pool_size=30,  # Increased from 20
    max_overflow=50,  # Increased from 30
    pool_timeout=30,
    pool_recycle=1800
)
```

**Monitor Connections**
```sql
-- Check current connections
SELECT count(*) as connections, state
FROM pg_stat_activity
WHERE datname = 'ai_agent'
GROUP BY state;

-- Check connection limits
SHOW max_connections;

-- Kill idle connections if needed
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'ai_agent'
AND state = 'idle'
AND state_change < now() - interval '1 hour';
```

## Data Integrity Issues

### 1. Missing Data

#### Symptoms
- Record counts don't match
- Some data missing after migration
- Referential integrity violations

#### Solutions

**Compare Record Counts**
```python
# Run data validation script
python validate_complete_migration.py

# Manual count comparison
import sqlite3
import psycopg2

# SQLite counts
sqlite_conn = sqlite3.connect('ai_agent.db')
sqlite_cursor = sqlite_conn.cursor()
sqlite_cursor.execute("SELECT COUNT(*) FROM unified_users")
sqlite_count = sqlite_cursor.fetchone()[0]

# PostgreSQL counts
pg_conn = psycopg2.connect("postgresql://user:pass@localhost/ai_agent")
pg_cursor = pg_conn.cursor()
pg_cursor.execute("SELECT COUNT(*) FROM unified_users")
pg_count = pg_cursor.fetchone()[0]

print(f"SQLite: {sqlite_count}, PostgreSQL: {pg_count}")
```

**Re-run Migration for Specific Tables**
```python
# Re-migrate specific table
from scripts.migrate_to_postgresql import DatabaseMigrator, MigrationConfig

config = MigrationConfig(
    sqlite_url="sqlite:///ai_agent.db",
    postgresql_url="postgresql://user:pass@localhost/ai_agent"
)

migrator = DatabaseMigrator(config)
migrator.setup_connections()

# Re-migrate specific table
migrator.migrate_table("unified_users")
```

### 2. Corrupted Data

#### Symptoms
- Invalid data types
- Encoding issues
- Malformed JSON data

#### Solutions

**Check Data Integrity**
```sql
-- Check for NULL values in required fields
SELECT COUNT(*) FROM unified_users WHERE username IS NULL;

-- Check JSON data validity
SELECT id, user_id FROM unified_chat_history 
WHERE NOT (metadata::text)::json IS NOT NULL;

-- Check date formats
SELECT id, created_at FROM unified_users 
WHERE created_at IS NULL OR created_at > now();
```

**Fix Data Issues**
```sql
-- Fix NULL usernames (example)
UPDATE unified_users 
SET username = 'user_' || id::text 
WHERE username IS NULL;

-- Fix invalid JSON
UPDATE unified_chat_history 
SET metadata = '{}' 
WHERE metadata IS NULL OR metadata = '';

-- Fix date issues
UPDATE unified_users 
SET created_at = now() 
WHERE created_at IS NULL;
```

## Recovery Procedures

### 1. Rollback to SQLite

If migration fails completely:

```bash
# Stop application
sudo systemctl stop ai-agent

# Restore SQLite backup
cp migration_backups/sqlite_backup_*.db ai_agent.db

# Update environment
sed -i 's/DATABASE_URL=postgresql/#DATABASE_URL=postgresql/' .env
echo "DATABASE_URL=sqlite:///ai_agent.db" >> .env

# Start application
sudo systemctl start ai-agent
```

### 2. Partial Recovery

If only some data is corrupted:

```sql
-- Use rollback script for specific tables
\i migration_backups/rollback_20250926_155508.sql

-- Or restore from backup
pg_restore -h localhost -U ai_agent_user -d ai_agent \
    --table=unified_users backup_file.sql
```

### 3. Complete PostgreSQL Reset

If PostgreSQL database is corrupted:

```sql
-- Drop and recreate database
DROP DATABASE ai_agent;
CREATE DATABASE ai_agent OWNER ai_agent_user;

-- Re-run schema creation
python create_postgresql_schema.py

-- Re-run migration
python execute_complete_migration.py
```

## Prevention Strategies

### 1. Pre-Migration Validation

Always run these checks before migration:

```bash
# Check SQLite database integrity
sqlite3 ai_agent.db "PRAGMA integrity_check;"

# Verify PostgreSQL connectivity
psql -h localhost -U ai_agent_user -d ai_agent -c "SELECT 1;"

# Check disk space
df -h

# Verify backup exists
ls -la migration_backups/
```

### 2. Monitoring During Migration

```bash
# Monitor migration progress
tail -f migration.log

# Monitor PostgreSQL logs
tail -f /var/log/postgresql/postgresql-17-main.log

# Monitor system resources
htop
```

### 3. Post-Migration Validation

```bash
# Run comprehensive tests
python -m pytest tests/test_postgresql_migration.py -v

# Validate data integrity
python validate_complete_migration.py

# Test application functionality
curl http://localhost:8000/health
```

## Getting Help

### Log Files to Check
1. `migration.log` - Migration execution log
2. `logs/ai_agent.log` - Application log
3. `logs/database.log` - Database operation log
4. `/var/log/postgresql/postgresql-*.log` - PostgreSQL server log

### Information to Collect
- Migration execution output
- Error messages and stack traces
- Database connection parameters (without passwords)
- System resource usage
- PostgreSQL version and configuration

### Contact Information
- System Administrator: [contact info]
- Development Team: [contact info]
- Database Team: [contact info]

## Conclusion

This troubleshooting guide covers the most common issues encountered during PostgreSQL migration. Always create backups before attempting fixes, and test solutions in a development environment first when possible.