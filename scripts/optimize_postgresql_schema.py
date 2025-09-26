#!/usr/bin/env python3
"""
PostgreSQL Schema Optimization Script

This script optimizes the database schema for PostgreSQL by:
1. Creating PostgreSQL-specific data types and indexes
2. Adding proper foreign key constraints and validations
3. Creating sequences for auto-incrementing fields
4. Optimizing indexes for common query patterns

Requirements: 3.1, 3.2, 3.3, 3.4
"""

import os
import sys
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import DATABASE_URL, engine, Base
from backend import unified_models, models, memory_models

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PostgreSQLSchemaOptimizer:
    """PostgreSQL schema optimization manager"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.engine = engine
        
        if not self.database_url.startswith("postgresql"):
            raise ValueError("This optimizer is designed for PostgreSQL databases only")
    
    def optimize_schema(self):
        """Run complete schema optimization"""
        logger.info("Starting PostgreSQL schema optimization...")
        
        try:
            # Step 1: Create optimized indexes
            self.create_optimized_indexes()
            
            # Step 2: Add PostgreSQL-specific constraints
            self.add_postgresql_constraints()
            
            # Step 3: Create sequences for auto-incrementing fields
            self.create_sequences()
            
            # Step 4: Optimize data types (handled by model updates)
            self.verify_data_types()
            
            # Step 5: Add database-level validations
            self.add_database_validations()
            
            logger.info("PostgreSQL schema optimization completed successfully")
            
        except Exception as e:
            logger.error(f"Schema optimization failed: {e}")
            raise
    
    def create_optimized_indexes(self):
        """Create PostgreSQL-optimized indexes for common query patterns"""
        logger.info("Creating optimized indexes...")
        
        indexes = [
            # User lookup optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_users_email_active ON unified_users(email) WHERE is_active = true;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_users_username_active ON unified_users(username) WHERE is_active = true;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_users_role ON unified_users(role);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_users_created_at ON unified_users(created_at);",
            
            # Session management optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_user_sessions_token ON unified_user_sessions(session_id) WHERE is_active = true;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_user_sessions_user_active ON unified_user_sessions(user_id) WHERE is_active = true;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_user_sessions_expires ON unified_user_sessions(expires_at) WHERE is_active = true;",
            
            # Chat history optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_chat_history_user_created ON unified_chat_history(user_id, created_at DESC);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_chat_history_session ON unified_chat_history(session_id);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_enhanced_chat_history_user_session ON enhanced_chat_history(user_id, session_id);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_enhanced_chat_history_quality ON enhanced_chat_history(response_quality_score) WHERE response_quality_score IS NOT NULL;",
            
            # Ticket management optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_tickets_customer_status ON unified_tickets(customer_id, status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_tickets_assigned_status ON unified_tickets(assigned_agent_id, status) WHERE assigned_agent_id IS NOT NULL;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_tickets_priority_created ON unified_tickets(priority, created_at DESC);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_tickets_category ON unified_tickets(category);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_tickets_updated_at ON unified_tickets(updated_at DESC);",
            
            # Ticket comments optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_ticket_comments_ticket_created ON unified_ticket_comments(ticket_id, created_at DESC);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_ticket_comments_author ON unified_ticket_comments(author_id) WHERE author_id IS NOT NULL;",
            
            # Ticket activities optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_ticket_activities_ticket_created ON unified_ticket_activities(ticket_id, created_at DESC);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_ticket_activities_type ON unified_ticket_activities(activity_type);",
            
            # Chat sessions optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_chat_sessions_customer_status ON unified_chat_sessions(customer_id, status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_chat_sessions_agent_active ON unified_chat_sessions(agent_id) WHERE agent_id IS NOT NULL AND status = 'active';",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_chat_sessions_ticket ON unified_chat_sessions(ticket_id) WHERE ticket_id IS NOT NULL;",
            
            # Chat messages optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_chat_messages_session_created ON unified_chat_messages(session_id, created_at DESC);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_chat_messages_unread ON unified_chat_messages(user_id) WHERE is_read = false;",
            
            # Voice analytics optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_voice_analytics_user_action ON unified_voice_analytics(user_id, action_type);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_voice_analytics_created ON unified_voice_analytics(created_at DESC);",
            
            # Memory layer optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memory_context_cache_user_type_relevance ON memory_context_cache(user_id, context_type, relevance_score DESC);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memory_context_cache_expires_active ON memory_context_cache(expires_at) WHERE expires_at > NOW();",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tool_usage_metrics_name_quality ON tool_usage_metrics(tool_name, response_quality_score DESC);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tool_usage_metrics_usage_success ON tool_usage_metrics(usage_count DESC, success_rate DESC);",
            
            # Performance metrics optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_performance_metrics_agent_date ON unified_performance_metrics(agent_id, date DESC);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_performance_metrics_type_value ON unified_performance_metrics(metric_type, value DESC);",
            
            # Customer satisfaction optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_customer_satisfaction_ticket ON unified_customer_satisfaction(ticket_id) WHERE ticket_id IS NOT NULL;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_customer_satisfaction_agent_rating ON unified_customer_satisfaction(agent_id, rating DESC) WHERE agent_id IS NOT NULL;",
            
            # Knowledge base optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_knowledge_entries_title_trgm ON unified_knowledge_entries USING gin(title gin_trgm_ops);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_knowledge_entries_content_trgm ON unified_knowledge_entries USING gin(content gin_trgm_ops);",
            
            # JSONB indexes for metadata fields
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_voice_analytics_metadata ON unified_voice_analytics USING gin(analytics_metadata);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memory_context_cache_data ON memory_context_cache USING gin(context_data);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_enhanced_chat_history_tools ON enhanced_chat_history USING gin(tools_used);",
        ]
        
        with self.engine.connect() as conn:
            # Enable required extensions
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
                logger.info("Enabled pg_trgm extension for text search")
            except Exception as e:
                logger.warning(f"Could not enable pg_trgm extension: {e}")
            
            # Create indexes
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    logger.info(f"Created index: {index_sql.split('idx_')[1].split(' ')[0] if 'idx_' in index_sql else 'unknown'}")
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")
            
            conn.commit()
    
    def add_postgresql_constraints(self):
        """Add PostgreSQL-specific constraints and validations"""
        logger.info("Adding PostgreSQL constraints...")
        
        constraints = [
            # Email validation
            "ALTER TABLE unified_users ADD CONSTRAINT IF NOT EXISTS chk_unified_users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$');",
            
            # Phone validation (optional field)
            "ALTER TABLE unified_users ADD CONSTRAINT IF NOT EXISTS chk_unified_users_phone_format CHECK (phone IS NULL OR phone ~* '^[+]?[0-9\\s\\-\\(\\)]{10,20}$');",
            
            # Username validation
            "ALTER TABLE unified_users ADD CONSTRAINT IF NOT EXISTS chk_unified_users_username_length CHECK (length(username) >= 3 AND length(username) <= 100);",
            
            # Password hash validation
            "ALTER TABLE unified_users ADD CONSTRAINT IF NOT EXISTS chk_unified_users_password_hash_length CHECK (length(password_hash) >= 60);",
            
            # Ticket priority validation
            "ALTER TABLE unified_tickets ADD CONSTRAINT IF NOT EXISTS chk_unified_tickets_priority_valid CHECK (priority IN ('low', 'medium', 'high', 'critical'));",
            
            # Ticket status validation
            "ALTER TABLE unified_tickets ADD CONSTRAINT IF NOT EXISTS chk_unified_tickets_status_valid CHECK (status IN ('open', 'in_progress', 'pending', 'resolved', 'closed'));",
            
            # Rating validation for customer satisfaction
            "ALTER TABLE unified_customer_satisfaction ADD CONSTRAINT IF NOT EXISTS chk_unified_customer_satisfaction_rating_range CHECK (rating >= 1 AND rating <= 5);",
            
            # Voice settings validation
            "ALTER TABLE unified_voice_settings ADD CONSTRAINT IF NOT EXISTS chk_unified_voice_settings_speech_rate CHECK (speech_rate >= 0.1 AND speech_rate <= 3.0);",
            "ALTER TABLE unified_voice_settings ADD CONSTRAINT IF NOT EXISTS chk_unified_voice_settings_speech_pitch CHECK (speech_pitch >= 0.1 AND speech_pitch <= 2.0);",
            "ALTER TABLE unified_voice_settings ADD CONSTRAINT IF NOT EXISTS chk_unified_voice_settings_speech_volume CHECK (speech_volume >= 0.0 AND speech_volume <= 1.0);",
            "ALTER TABLE unified_voice_settings ADD CONSTRAINT IF NOT EXISTS chk_unified_voice_settings_microphone_sensitivity CHECK (microphone_sensitivity >= 0.0 AND microphone_sensitivity <= 1.0);",
            
            # Memory context cache validation
            "ALTER TABLE memory_context_cache ADD CONSTRAINT IF NOT EXISTS chk_memory_context_cache_relevance_score CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0);",
            
            # Tool usage metrics validation
            "ALTER TABLE tool_usage_metrics ADD CONSTRAINT IF NOT EXISTS chk_tool_usage_metrics_success_rate CHECK (success_rate >= 0.0 AND success_rate <= 1.0);",
            "ALTER TABLE tool_usage_metrics ADD CONSTRAINT IF NOT EXISTS chk_tool_usage_metrics_response_quality CHECK (response_quality_score >= 0.0 AND response_quality_score <= 1.0);",
            "ALTER TABLE tool_usage_metrics ADD CONSTRAINT IF NOT EXISTS chk_tool_usage_metrics_usage_count CHECK (usage_count >= 0);",
            
            # Enhanced chat history validation
            "ALTER TABLE enhanced_chat_history ADD CONSTRAINT IF NOT EXISTS chk_enhanced_chat_history_quality_score CHECK (response_quality_score IS NULL OR (response_quality_score >= 0.0 AND response_quality_score <= 1.0));",
        ]
        
        with self.engine.connect() as conn:
            for constraint_sql in constraints:
                try:
                    conn.execute(text(constraint_sql))
                    constraint_name = constraint_sql.split('chk_')[1].split(' ')[0] if 'chk_' in constraint_sql else 'unknown'
                    logger.info(f"Added constraint: {constraint_name}")
                except Exception as e:
                    logger.warning(f"Failed to add constraint: {e}")
            
            conn.commit()
    
    def create_sequences(self):
        """Create PostgreSQL sequences for auto-incrementing fields"""
        logger.info("Creating PostgreSQL sequences...")
        
        sequences = [
            # User ID sequence
            "CREATE SEQUENCE IF NOT EXISTS unified_users_id_seq OWNED BY unified_users.id;",
            "ALTER TABLE unified_users ALTER COLUMN id SET DEFAULT nextval('unified_users_id_seq');",
            
            # Ticket ID sequence
            "CREATE SEQUENCE IF NOT EXISTS unified_tickets_id_seq OWNED BY unified_tickets.id;",
            "ALTER TABLE unified_tickets ALTER COLUMN id SET DEFAULT nextval('unified_tickets_id_seq');",
            
            # Session ID sequence
            "CREATE SEQUENCE IF NOT EXISTS unified_user_sessions_id_seq OWNED BY unified_user_sessions.id;",
            "ALTER TABLE unified_user_sessions ALTER COLUMN id SET DEFAULT nextval('unified_user_sessions_id_seq');",
            
            # Chat session ID sequence
            "CREATE SEQUENCE IF NOT EXISTS unified_chat_sessions_id_seq OWNED BY unified_chat_sessions.id;",
            "ALTER TABLE unified_chat_sessions ALTER COLUMN id SET DEFAULT nextval('unified_chat_sessions_id_seq');",
            
            # Chat message ID sequence
            "CREATE SEQUENCE IF NOT EXISTS unified_chat_messages_id_seq OWNED BY unified_chat_messages.id;",
            "ALTER TABLE unified_chat_messages ALTER COLUMN id SET DEFAULT nextval('unified_chat_messages_id_seq');",
            
            # Enhanced chat history ID sequence
            "CREATE SEQUENCE IF NOT EXISTS enhanced_chat_history_id_seq OWNED BY enhanced_chat_history.id;",
            "ALTER TABLE enhanced_chat_history ALTER COLUMN id SET DEFAULT nextval('enhanced_chat_history_id_seq');",
        ]
        
        with self.engine.connect() as conn:
            for sequence_sql in sequences:
                try:
                    conn.execute(text(sequence_sql))
                    if 'CREATE SEQUENCE' in sequence_sql:
                        seq_name = sequence_sql.split('IF NOT EXISTS ')[1].split(' ')[0]
                        logger.info(f"Created sequence: {seq_name}")
                except Exception as e:
                    logger.warning(f"Failed to create sequence: {e}")
            
            conn.commit()
    
    def verify_data_types(self):
        """Verify PostgreSQL-specific data types are being used"""
        logger.info("Verifying PostgreSQL data types...")
        
        # Check for JSONB columns
        jsonb_check_sql = """
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND data_type = 'jsonb'
        ORDER BY table_name, column_name;
        """
        
        # Check for timestamp with timezone columns
        timestamp_check_sql = """
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND data_type = 'timestamp with time zone'
        ORDER BY table_name, column_name;
        """
        
        with self.engine.connect() as conn:
            # Check JSONB columns
            result = conn.execute(text(jsonb_check_sql))
            jsonb_columns = result.fetchall()
            logger.info(f"Found {len(jsonb_columns)} JSONB columns:")
            for row in jsonb_columns:
                logger.info(f"  {row[0]}.{row[1]}")
            
            # Check timestamp columns
            result = conn.execute(text(timestamp_check_sql))
            timestamp_columns = result.fetchall()
            logger.info(f"Found {len(timestamp_columns)} timestamp with timezone columns:")
            for row in timestamp_columns:
                logger.info(f"  {row[0]}.{row[1]}")
    
    def add_database_validations(self):
        """Add database-level validations and triggers"""
        logger.info("Adding database-level validations...")
        
        # Create function to update updated_at timestamp
        update_timestamp_function = """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
        
        # Create triggers for updated_at columns
        triggers = [
            "CREATE TRIGGER update_unified_users_updated_at BEFORE UPDATE ON unified_users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
            "CREATE TRIGGER update_unified_tickets_updated_at BEFORE UPDATE ON unified_tickets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
            "CREATE TRIGGER update_unified_chat_sessions_updated_at BEFORE UPDATE ON unified_chat_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
            "CREATE TRIGGER update_unified_voice_settings_updated_at BEFORE UPDATE ON unified_voice_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
            "CREATE TRIGGER update_enhanced_chat_history_updated_at BEFORE UPDATE ON enhanced_chat_history FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
        ]
        
        with self.engine.connect() as conn:
            # Create the function
            try:
                conn.execute(text(update_timestamp_function))
                logger.info("Created update_updated_at_column function")
            except Exception as e:
                logger.warning(f"Failed to create timestamp function: {e}")
            
            # Create triggers
            for trigger_sql in triggers:
                try:
                    conn.execute(text(trigger_sql))
                    trigger_name = trigger_sql.split('CREATE TRIGGER ')[1].split(' ')[0]
                    logger.info(f"Created trigger: {trigger_name}")
                except Exception as e:
                    logger.warning(f"Failed to create trigger: {e}")
            
            conn.commit()
    
    def generate_optimization_report(self):
        """Generate a report of the optimization results"""
        logger.info("Generating optimization report...")
        
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_url": self.database_url.split("@")[1] if "@" in self.database_url else "local",
            "tables": [],
            "indexes": [],
            "constraints": [],
            "sequences": []
        }
        
        with self.engine.connect() as conn:
            # Get table information
            tables_sql = """
            SELECT table_name, 
                   (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE table_schema = 'public'
            ORDER BY table_name;
            """
            
            result = conn.execute(text(tables_sql))
            for row in result:
                report["tables"].append({
                    "name": row[0],
                    "columns": row[1]
                })
            
            # Get index information
            indexes_sql = """
            SELECT indexname, tablename, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND indexname LIKE 'idx_%'
            ORDER BY tablename, indexname;
            """
            
            result = conn.execute(text(indexes_sql))
            for row in result:
                report["indexes"].append({
                    "name": row[0],
                    "table": row[1],
                    "definition": row[2]
                })
            
            # Get constraint information
            constraints_sql = """
            SELECT conname, conrelid::regclass as table_name, pg_get_constraintdef(oid) as definition
            FROM pg_constraint
            WHERE conname LIKE 'chk_%'
            ORDER BY conrelid::regclass, conname;
            """
            
            result = conn.execute(text(constraints_sql))
            for row in result:
                report["constraints"].append({
                    "name": row[0],
                    "table": str(row[1]),
                    "definition": row[2]
                })
            
            # Get sequence information
            sequences_sql = """
            SELECT sequencename, last_value, increment_by
            FROM pg_sequences
            WHERE schemaname = 'public'
            ORDER BY sequencename;
            """
            
            result = conn.execute(text(sequences_sql))
            for row in result:
                report["sequences"].append({
                    "name": row[0],
                    "last_value": row[1],
                    "increment": row[2]
                })
        
        # Save report to file
        import json
        report_file = f"postgresql_optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Optimization report saved to: {report_file}")
        logger.info(f"Summary: {len(report['tables'])} tables, {len(report['indexes'])} indexes, {len(report['constraints'])} constraints, {len(report['sequences'])} sequences")
        
        return report

def main():
    """Main function to run PostgreSQL schema optimization"""
    try:
        # Check if we're using PostgreSQL
        if not DATABASE_URL.startswith("postgresql"):
            logger.error("This script is designed for PostgreSQL databases only")
            logger.error(f"Current DATABASE_URL: {DATABASE_URL}")
            sys.exit(1)
        
        # Create optimizer
        optimizer = PostgreSQLSchemaOptimizer()
        
        # Run optimization
        optimizer.optimize_schema()
        
        # Generate report
        report = optimizer.generate_optimization_report()
        
        logger.info("PostgreSQL schema optimization completed successfully!")
        
    except Exception as e:
        logger.error(f"Schema optimization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()