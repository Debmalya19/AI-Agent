# PostgreSQL Setup Guide

This guide covers the setup and configuration of PostgreSQL for the AI Agent application.

## Prerequisites

1. **PostgreSQL Server**: Install PostgreSQL 12 or later
   - Ubuntu/Debian: `sudo apt-get install postgresql postgresql-contrib`
   - macOS: `brew install postgresql`
   - Windows: Download from https://www.postgresql.org/download/

2. **Python Dependencies**: Install required packages
   ```bash
   pip install psycopg2-binary sqlalchemy python-dotenv
   ```

## Quick Setup

### 1. Start PostgreSQL Service

```bash
# Ubuntu/Debian
sudo systemctl start postgresql
sudo systemctl enable postgresql

# macOS
brew services start postgresql

# Windows
# Use PostgreSQL Service Manager or pg_ctl
```

### 2. Configure Environment Variables

Update your `.env` file with PostgreSQL configuration:

```env
# Database Configuration
DATABASE_URL=postgresql://ai_agent_user:ai_agent_password@localhost:5432/ai_agent

# PostgreSQL Connection Pool Configuration
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_RECYCLE=3600
DB_POOL_TIMEOUT=30
DB_CONNECT_TIMEOUT=10

# Database Debugging (set to true for development)
DATABASE_ECHO=false

# PostgreSQL Admin Configuration (for setup script)
POSTGRES_ADMIN_PASSWORD=postgres
```

### 3. Run Database Setup Script

```bash
cd ai-agent
python scripts/setup_postgresql.py
```

This script will:
- Create the `ai_agent` database
- Create the `ai_agent_user` user account
- Grant necessary privileges
- Test the connection

### 4. Initialize Database Tables

```bash
python -c "from backend.database import init_db; init_db()"
```

### 5. Verify Setup

```bash
python test_postgresql_setup.py
```

## Manual Setup (Alternative)

If the automated setup script doesn't work, you can set up PostgreSQL manually:

### 1. Connect to PostgreSQL as superuser

```bash
sudo -u postgres psql
```

### 2. Create database and user

```sql
-- Create database
CREATE DATABASE ai_agent;

-- Create user
CREATE USER ai_agent_user WITH PASSWORD 'ai_agent_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ai_agent TO ai_agent_user;
ALTER USER ai_agent_user CREATEDB;

-- Exit
\q
```

### 3. Test connection

```bash
psql -h localhost -U ai_agent_user -d ai_agent
```

## Configuration Details

### Connection Pool Settings

The application uses optimized connection pooling for production:

- **Pool Size**: 20 connections (configurable via `DB_POOL_SIZE`)
- **Max Overflow**: 30 additional connections (configurable via `DB_MAX_OVERFLOW`)
- **Pool Recycle**: 3600 seconds (1 hour) - connections are recycled
- **Pool Timeout**: 30 seconds - maximum wait time for connection
- **Connect Timeout**: 10 seconds - connection establishment timeout

### Health Checks

The application includes comprehensive health checking:

- **Connection Health**: Automatic connection validation before use
- **Pool Monitoring**: Real-time connection pool status
- **Database Diagnostics**: Comprehensive health check endpoints

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | PostgreSQL connection string |
| `DB_POOL_SIZE` | 20 | Base connection pool size |
| `DB_MAX_OVERFLOW` | 30 | Maximum overflow connections |
| `DB_POOL_RECYCLE` | 3600 | Connection recycle time (seconds) |
| `DB_POOL_TIMEOUT` | 30 | Pool checkout timeout (seconds) |
| `DB_CONNECT_TIMEOUT` | 10 | Connection timeout (seconds) |
| `DATABASE_ECHO` | false | Enable SQL query logging |
| `POSTGRES_ADMIN_PASSWORD` | postgres | Admin password for setup |

## Monitoring and Health Checks

### Health Check Endpoints

The application provides health check functionality:

```python
from backend.database_health import get_health_status, get_detailed_health_status

# Quick health check
status = get_health_status()
print(f"Database status: {status['status']}")

# Detailed health check
detailed = get_detailed_health_status()
for check_name, result in detailed['checks'].items():
    print(f"{check_name}: {result['status']} - {result['message']}")
```

### Connection Pool Monitoring

```python
from backend.database import get_database_info

info = get_database_info()
print(f"Pool status: {info['checked_out']}/{info['pool_size']} active connections")
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure PostgreSQL service is running
   - Check if PostgreSQL is listening on the correct port (5432)
   - Verify firewall settings

2. **Authentication Failed**
   - Check username and password in `DATABASE_URL`
   - Verify user exists and has correct privileges
   - Check `pg_hba.conf` for authentication method

3. **Database Does Not Exist**
   - Run the setup script: `python scripts/setup_postgresql.py`
   - Or create manually: `createdb -U postgres ai_agent`

4. **Permission Denied**
   - Ensure user has necessary privileges
   - Grant privileges: `GRANT ALL PRIVILEGES ON DATABASE ai_agent TO ai_agent_user;`

5. **Connection Pool Exhausted**
   - Increase `DB_POOL_SIZE` and `DB_MAX_OVERFLOW`
   - Check for connection leaks in application code
   - Monitor connection usage patterns

### Diagnostic Commands

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# Test connection
psql -h localhost -U ai_agent_user -d ai_agent -c "SELECT version();"

# Check active connections
psql -U postgres -c "SELECT * FROM pg_stat_activity WHERE datname = 'ai_agent';"
```

### Performance Tuning

For production environments, consider these PostgreSQL settings:

```sql
-- In postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

## Migration from SQLite

If migrating from SQLite, see the migration documentation and use the migration scripts provided in the `scripts/` directory.

## Security Considerations

1. **Use strong passwords** for database users
2. **Enable SSL/TLS** for database connections in production
3. **Restrict network access** to PostgreSQL server
4. **Regular security updates** for PostgreSQL
5. **Monitor database access** and audit logs
6. **Use connection encryption** in production environments

## Backup and Recovery

Set up regular backups:

```bash
# Create backup
pg_dump -U ai_agent_user -h localhost ai_agent > backup.sql

# Restore backup
psql -U ai_agent_user -h localhost ai_agent < backup.sql
```

For automated backups, consider using `pg_basebackup` or third-party tools like `pgBackRest`.