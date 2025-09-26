# PostgreSQL Schema Optimization Documentation

This document describes the PostgreSQL schema optimizations implemented for the AI agent application as part of the database migration from SQLite to PostgreSQL.

## Overview

The schema optimization includes:
1. **PostgreSQL-specific data types** (JSONB, TIMESTAMP WITH TIME ZONE)
2. **Optimized indexes** for common query patterns
3. **Database-level constraints** and validations
4. **PostgreSQL sequences** for auto-incrementing fields
5. **Performance optimizations** and monitoring

## Requirements Addressed

- **Requirement 3.1**: Update model definitions to use PostgreSQL-specific data types
- **Requirement 3.2**: Create optimized indexes for user lookup, session management, chat history, and ticket operations
- **Requirement 3.3**: Implement proper foreign key constraints and database-level validations
- **Requirement 3.4**: Add PostgreSQL sequences for auto-incrementing fields

## PostgreSQL-Specific Data Types

### JSONB Columns
The following columns have been optimized to use JSONB instead of JSON for better performance:

#### Enhanced Chat History
- `user_message_encrypted`: Encrypted user message with metadata
- `bot_response_encrypted`: Encrypted bot response with metadata
- `tools_used`: List of tool names used
- `tool_performance`: Tool performance metrics
- `context_used`: List of context entries used
- `semantic_features`: Extracted semantic features for similarity

#### Memory Context Cache
- `context_data`: The actual context content
- `context_data_encrypted`: Encrypted context data with metadata
- `access_control`: Access control metadata

#### Voice Analytics
- `analytics_metadata`: Voice assistant usage analytics metadata

#### Knowledge Entries
- `embedding`: Vector embeddings for semantic search

#### Chat History
- `tools_used`: List of tools used in conversation
- `sources`: Information sources used

### TIMESTAMP WITH TIME ZONE Columns
All datetime columns have been updated to use `TIMESTAMP WITH TIME ZONE` for proper timezone handling:

- `created_at`: Record creation timestamp
- `updated_at`: Record update timestamp
- `expires_at`: Expiration timestamp for sessions and cache entries
- `last_accessed`: Last access timestamp
- `resolved_at`: Ticket resolution timestamp
- `ended_at`: Session end timestamp

## Optimized Indexes

### User Management Indexes
```sql
-- Active user lookups
CREATE INDEX CONCURRENTLY idx_unified_users_email_active ON unified_users(email) WHERE is_active = true;
CREATE INDEX CONCURRENTLY idx_unified_users_username_active ON unified_users(username) WHERE is_active = true;
CREATE INDEX CONCURRENTLY idx_unified_users_role ON unified_users(role);
CREATE INDEX CONCURRENTLY idx_unified_users_created_at ON unified_users(created_at);
```

### Session Management Indexes
```sql
-- Active session lookups
CREATE INDEX CONCURRENTLY idx_unified_user_sessions_token ON unified_user_sessions(session_id) WHERE is_active = true;
CREATE INDEX CONCURRENTLY idx_unified_user_sessions_user_active ON unified_user_sessions(user_id) WHERE is_active = true;
CREATE INDEX CONCURRENTLY idx_unified_user_sessions_expires ON unified_user_sessions(expires_at) WHERE is_active = true;
```

### Chat History Indexes
```sql
-- Chat history queries
CREATE INDEX CONCURRENTLY idx_unified_chat_history_user_created ON unified_chat_history(user_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_unified_chat_history_session ON unified_chat_history(session_id);
CREATE INDEX CONCURRENTLY idx_enhanced_chat_history_user_session ON enhanced_chat_history(user_id, session_id);
CREATE INDEX CONCURRENTLY idx_enhanced_chat_history_quality ON enhanced_chat_history(response_quality_score) WHERE response_quality_score IS NOT NULL;
```

### Ticket Management Indexes
```sql
-- Ticket operations
CREATE INDEX CONCURRENTLY idx_unified_tickets_customer_status ON unified_tickets(customer_id, status);
CREATE INDEX CONCURRENTLY idx_unified_tickets_assigned_status ON unified_tickets(assigned_agent_id, status) WHERE assigned_agent_id IS NOT NULL;
CREATE INDEX CONCURRENTLY idx_unified_tickets_priority_created ON unified_tickets(priority, created_at DESC);
CREATE INDEX CONCURRENTLY idx_unified_tickets_category ON unified_tickets(category);
CREATE INDEX CONCURRENTLY idx_unified_tickets_updated_at ON unified_tickets(updated_at DESC);
```

### JSONB Indexes
```sql
-- JSONB content indexes using GIN
CREATE INDEX CONCURRENTLY idx_unified_voice_analytics_metadata ON unified_voice_analytics USING gin(analytics_metadata);
CREATE INDEX CONCURRENTLY idx_memory_context_cache_data ON memory_context_cache USING gin(context_data);
CREATE INDEX CONCURRENTLY idx_enhanced_chat_history_tools ON enhanced_chat_history USING gin(tools_used);
```

### Text Search Indexes
```sql
-- Full-text search using pg_trgm extension
CREATE INDEX CONCURRENTLY idx_unified_knowledge_entries_title_trgm ON unified_knowledge_entries USING gin(title gin_trgm_ops);
CREATE INDEX CONCURRENTLY idx_unified_knowledge_entries_content_trgm ON unified_knowledge_entries USING gin(content gin_trgm_ops);
```

## Database Constraints

### Data Validation Constraints
```sql
-- Email format validation
ALTER TABLE unified_users ADD CONSTRAINT chk_unified_users_email_format 
CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$');

-- Phone format validation
ALTER TABLE unified_users ADD CONSTRAINT chk_unified_users_phone_format 
CHECK (phone IS NULL OR phone ~* '^[+]?[0-9\\s\\-\\(\\)]{10,20}$');

-- Username length validation
ALTER TABLE unified_users ADD CONSTRAINT chk_unified_users_username_length 
CHECK (length(username) >= 3 AND length(username) <= 100);

-- Password hash validation
ALTER TABLE unified_users ADD CONSTRAINT chk_unified_users_password_hash_length 
CHECK (length(password_hash) >= 60);

-- Rating range validation
ALTER TABLE unified_customer_satisfaction ADD CONSTRAINT chk_unified_customer_satisfaction_rating_range 
CHECK (rating >= 1 AND rating <= 5);

-- Voice settings validation
ALTER TABLE unified_voice_settings ADD CONSTRAINT chk_unified_voice_settings_speech_rate 
CHECK (speech_rate >= 0.1 AND speech_rate <= 3.0);

-- Quality score validation
ALTER TABLE enhanced_chat_history ADD CONSTRAINT chk_enhanced_chat_history_quality_score 
CHECK (response_quality_score IS NULL OR (response_quality_score >= 0.0 AND response_quality_score <= 1.0));
```

### Enum Constraints
```sql
-- Ticket status validation
ALTER TABLE unified_tickets ADD CONSTRAINT chk_unified_tickets_status_valid 
CHECK (status IN ('open', 'in_progress', 'pending', 'resolved', 'closed'));

-- Ticket priority validation
ALTER TABLE unified_tickets ADD CONSTRAINT chk_unified_tickets_priority_valid 
CHECK (priority IN ('low', 'medium', 'high', 'critical'));
```

## PostgreSQL Sequences

### Auto-incrementing Field Sequences
```sql
-- User ID sequence
CREATE SEQUENCE unified_users_id_seq OWNED BY unified_users.id;
ALTER TABLE unified_users ALTER COLUMN id SET DEFAULT nextval('unified_users_id_seq');

-- Ticket ID sequence
CREATE SEQUENCE unified_tickets_id_seq OWNED BY unified_tickets.id;
ALTER TABLE unified_tickets ALTER COLUMN id SET DEFAULT nextval('unified_tickets_id_seq');

-- Session ID sequence
CREATE SEQUENCE unified_user_sessions_id_seq OWNED BY unified_user_sessions.id;
ALTER TABLE unified_user_sessions ALTER COLUMN id SET DEFAULT nextval('unified_user_sessions_id_seq');

-- Chat session ID sequence
CREATE SEQUENCE unified_chat_sessions_id_seq OWNED BY unified_chat_sessions.id;
ALTER TABLE unified_chat_sessions ALTER COLUMN id SET DEFAULT nextval('unified_chat_sessions_id_seq');
```

## Database Triggers

### Automatic Timestamp Updates
```sql
-- Function to update updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_unified_users_updated_at 
BEFORE UPDATE ON unified_users 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_unified_tickets_updated_at 
BEFORE UPDATE ON unified_tickets 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Performance Optimizations

### Connection Pooling
The database configuration includes optimized connection pooling parameters:

```python
# Production-ready connection pooling parameters
engine_kwargs.update({
    "pool_size": 20,           # Base connection pool size
    "max_overflow": 30,        # Additional connections for traffic spikes
    "pool_pre_ping": True,     # Enable connection health checks
    "pool_recycle": 3600,      # Recycle connections every hour
    "pool_timeout": 30,        # Connection timeout
    "poolclass": QueuePool,    # Use queue-based pooling
})
```

### Query Optimization
- **Partial indexes**: Indexes with WHERE clauses for active records only
- **Composite indexes**: Multi-column indexes for common query patterns
- **JSONB indexes**: GIN indexes for efficient JSONB queries
- **Text search indexes**: pg_trgm indexes for fuzzy text matching

### Memory Optimization
- **JSONB storage**: More efficient than JSON for large objects
- **Connection pooling**: Reduces connection overhead
- **Index-only scans**: Covering indexes for frequently accessed columns

## Extensions Required

### pg_trgm Extension
Required for fuzzy text search capabilities:
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

This extension enables:
- Trigram-based text similarity
- Fuzzy text matching
- Efficient LIKE queries with wildcards

## Migration Considerations

### Data Type Compatibility
- **JSON to JSONB**: Automatic conversion with improved performance
- **DateTime to TIMESTAMP WITH TIME ZONE**: Proper timezone handling
- **String lengths**: Validated with constraints

### Index Creation Strategy
- **CONCURRENTLY**: Indexes created without blocking operations
- **Conditional indexes**: WHERE clauses reduce index size
- **Composite indexes**: Optimized for specific query patterns

### Constraint Migration
- **Check constraints**: Data validation at database level
- **Foreign key constraints**: Referential integrity enforcement
- **Unique constraints**: Prevent duplicate data

## Monitoring and Maintenance

### Performance Monitoring
```sql
-- Index usage statistics
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Table statistics
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del, n_live_tup, n_dead_tup
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```

### Maintenance Tasks
- **VACUUM ANALYZE**: Regular statistics updates
- **REINDEX**: Periodic index rebuilding
- **Connection monitoring**: Pool usage tracking
- **Query performance**: Slow query identification

## Testing and Validation

### Schema Validation Tests
The `test_postgresql_schema_optimization.py` script validates:
- PostgreSQL-specific data types usage
- Index creation and performance
- Constraint functionality
- Sequence operations
- JSONB operations
- Foreign key relationships

### Performance Testing
- **Index effectiveness**: Query execution plan analysis
- **Connection pooling**: Concurrent connection testing
- **JSONB operations**: JSON query performance
- **Text search**: Full-text search performance

## Usage Instructions

### Running Schema Optimization
```bash
# Ensure PostgreSQL is configured in .env
export DATABASE_URL="postgresql://user:password@localhost:5432/ai_agent"

# Run the optimization script
python scripts/optimize_postgresql_schema.py

# Run validation tests
python test_postgresql_schema_optimization.py
```

### Switching from SQLite to PostgreSQL
1. Update `.env` file with PostgreSQL connection string
2. Run database initialization: `python -c "from backend.database import init_db; init_db()"`
3. Run schema optimization: `python scripts/optimize_postgresql_schema.py`
4. Run migration script: `python scripts/migrate_to_postgresql.py`
5. Validate with tests: `python test_postgresql_schema_optimization.py`

## Troubleshooting

### Common Issues
1. **Extension not found**: Install pg_trgm extension
2. **Permission denied**: Ensure database user has CREATE privileges
3. **Index creation timeout**: Use CONCURRENTLY option
4. **Constraint violations**: Validate existing data before adding constraints

### Performance Issues
1. **Slow queries**: Check index usage with EXPLAIN ANALYZE
2. **Connection pool exhaustion**: Increase pool_size and max_overflow
3. **Memory usage**: Monitor JSONB column sizes
4. **Lock contention**: Use CONCURRENTLY for index operations

## Future Enhancements

### Additional Optimizations
- **Partitioning**: For large tables (chat history, analytics)
- **Materialized views**: For complex aggregations
- **Custom data types**: For domain-specific data
- **Advanced indexing**: Partial and expression indexes

### Monitoring Improvements
- **Query performance tracking**: pg_stat_statements extension
- **Connection monitoring**: Real-time pool metrics
- **Index usage analysis**: Automated recommendations
- **Storage optimization**: Automated maintenance scheduling

This optimization provides a solid foundation for PostgreSQL performance while maintaining data integrity and supporting the application's query patterns.