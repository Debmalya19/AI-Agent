"""
Database migration script for security and privacy features
Adds encryption fields and security tables to existing memory layer schema
"""

import logging
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, DateTime, Boolean, JSON, Text, Integer, Float, Index
from sqlalchemy.exc import SQLAlchemyError
from backend.database import get_database_url
from backend.memory_models import Base, UserSession, DataProcessingConsent, DataSubjectRights

logger = logging.getLogger(__name__)

class SecurityMigration:
    """Handles database migrations for security features"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or get_database_url()
        self.engine = create_engine(self.database_url)
        self.metadata = MetaData()
    
    def run_migration(self):
        """Run the complete security migration"""
        try:
            logger.info("Starting security migration...")
            
            # Step 1: Add encryption fields to existing tables
            self._add_encryption_fields()
            
            # Step 2: Create new security tables
            self._create_security_tables()
            
            # Step 3: Create indexes for performance
            self._create_security_indexes()
            
            logger.info("Security migration completed successfully")
            
        except Exception as e:
            logger.error(f"Security migration failed: {e}")
            raise
    
    def _add_encryption_fields(self):
        """Add encryption and security fields to existing tables"""
        logger.info("Adding encryption fields to existing tables...")
        
        with self.engine.connect() as conn:
            # Add fields to enhanced_chat_history
            try:
                conn.execute(text("""
                    ALTER TABLE enhanced_chat_history 
                    ADD COLUMN user_message_encrypted JSON
                """))
                logger.info("Added user_message_encrypted to enhanced_chat_history")
            except SQLAlchemyError as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Could not add user_message_encrypted: {e}")
            
            try:
                conn.execute(text("""
                    ALTER TABLE enhanced_chat_history 
                    ADD COLUMN bot_response_encrypted JSON
                """))
                logger.info("Added bot_response_encrypted to enhanced_chat_history")
            except SQLAlchemyError as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Could not add bot_response_encrypted: {e}")
            
            try:
                conn.execute(text("""
                    ALTER TABLE enhanced_chat_history 
                    ADD COLUMN data_classification VARCHAR(50) DEFAULT 'internal'
                """))
                logger.info("Added data_classification to enhanced_chat_history")
            except SQLAlchemyError as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Could not add data_classification: {e}")
            
            try:
                conn.execute(text("""
                    ALTER TABLE enhanced_chat_history 
                    ADD COLUMN retention_policy VARCHAR(100)
                """))
                logger.info("Added retention_policy to enhanced_chat_history")
            except SQLAlchemyError as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Could not add retention_policy: {e}")
            
            try:
                conn.execute(text("""
                    ALTER TABLE enhanced_chat_history 
                    ADD COLUMN deleted_at TIMESTAMP
                """))
                logger.info("Added deleted_at to enhanced_chat_history")
            except SQLAlchemyError as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Could not add deleted_at: {e}")
            
            try:
                conn.execute(text("""
                    ALTER TABLE enhanced_chat_history 
                    ADD COLUMN anonymized_at TIMESTAMP
                """))
                logger.info("Added anonymized_at to enhanced_chat_history")
            except SQLAlchemyError as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Could not add anonymized_at: {e}")
            
            # Add fields to memory_context_cache
            try:
                conn.execute(text("""
                    ALTER TABLE memory_context_cache 
                    ADD COLUMN context_data_encrypted JSON
                """))
                logger.info("Added context_data_encrypted to memory_context_cache")
            except SQLAlchemyError as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Could not add context_data_encrypted: {e}")
            
            try:
                conn.execute(text("""
                    ALTER TABLE memory_context_cache 
                    ADD COLUMN data_classification VARCHAR(50) DEFAULT 'internal'
                """))
                logger.info("Added data_classification to memory_context_cache")
            except SQLAlchemyError as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Could not add data_classification: {e}")
            
            try:
                conn.execute(text("""
                    ALTER TABLE memory_context_cache 
                    ADD COLUMN access_control JSON
                """))
                logger.info("Added access_control to memory_context_cache")
            except SQLAlchemyError as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Could not add access_control: {e}")
            
            conn.commit()
    
    def _create_security_tables(self):
        """Create new security-related tables"""
        logger.info("Creating security tables...")
        
        with self.engine.connect() as conn:
            # Create user_sessions table
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(50) NOT NULL,
                        session_id VARCHAR(255) UNIQUE NOT NULL,
                        session_token_hash VARCHAR(128),
                        is_active BOOLEAN DEFAULT TRUE,
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        session_metadata JSON,
                        last_activity TIMESTAMP DEFAULT NOW(),
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                logger.info("Created user_sessions table")
            except SQLAlchemyError as e:
                logger.warning(f"Could not create user_sessions table: {e}")
            
            # Create data_processing_consent table
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS data_processing_consent (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(50) NOT NULL,
                        consent_id VARCHAR(255) UNIQUE NOT NULL,
                        purpose VARCHAR(100) NOT NULL,
                        consent_given BOOLEAN NOT NULL,
                        consent_timestamp TIMESTAMP NOT NULL,
                        consent_method VARCHAR(50),
                        consent_version VARCHAR(20),
                        withdrawal_timestamp TIMESTAMP,
                        legal_basis VARCHAR(50) DEFAULT 'consent',
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                logger.info("Created data_processing_consent table")
            except SQLAlchemyError as e:
                logger.warning(f"Could not create data_processing_consent table: {e}")
            
            # Create data_subject_rights table
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS data_subject_rights (
                        id SERIAL PRIMARY KEY,
                        request_id VARCHAR(255) UNIQUE NOT NULL,
                        user_id VARCHAR(50) NOT NULL,
                        request_type VARCHAR(50) NOT NULL,
                        status VARCHAR(50) DEFAULT 'pending',
                        requested_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP,
                        request_details JSON,
                        response_data JSON,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                logger.info("Created data_subject_rights table")
            except SQLAlchemyError as e:
                logger.warning(f"Could not create data_subject_rights table: {e}")
            
            conn.commit()
    
    def _create_security_indexes(self):
        """Create indexes for security tables"""
        logger.info("Creating security indexes...")
        
        with self.engine.connect() as conn:
            # Indexes for user_sessions
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_active ON user_sessions(user_id, is_active)",
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at)",
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_activity ON user_sessions(last_activity)",
                
                # Indexes for data_processing_consent
                "CREATE INDEX IF NOT EXISTS idx_consent_user_id ON data_processing_consent(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_consent_consent_id ON data_processing_consent(consent_id)",
                "CREATE INDEX IF NOT EXISTS idx_consent_user_purpose ON data_processing_consent(user_id, purpose)",
                "CREATE INDEX IF NOT EXISTS idx_consent_given ON data_processing_consent(consent_given)",
                "CREATE INDEX IF NOT EXISTS idx_consent_timestamp ON data_processing_consent(consent_timestamp)",
                
                # Indexes for data_subject_rights
                "CREATE INDEX IF NOT EXISTS idx_dsr_request_id ON data_subject_rights(request_id)",
                "CREATE INDEX IF NOT EXISTS idx_dsr_user_id ON data_subject_rights(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_dsr_user_type ON data_subject_rights(user_id, request_type)",
                "CREATE INDEX IF NOT EXISTS idx_dsr_status ON data_subject_rights(status)",
                "CREATE INDEX IF NOT EXISTS idx_dsr_requested ON data_subject_rights(requested_at)",
                
                # Additional indexes for security fields in existing tables
                "CREATE INDEX IF NOT EXISTS idx_enhanced_chat_deleted ON enhanced_chat_history(deleted_at)",
                "CREATE INDEX IF NOT EXISTS idx_enhanced_chat_classification ON enhanced_chat_history(data_classification)",
                "CREATE INDEX IF NOT EXISTS idx_context_cache_classification ON memory_context_cache(data_classification)",
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    logger.debug(f"Created index: {index_sql}")
                except SQLAlchemyError as e:
                    logger.warning(f"Could not create index: {e}")
            
            conn.commit()
    
    def rollback_migration(self):
        """Rollback security migration (for testing/development)"""
        logger.warning("Rolling back security migration...")
        
        with self.engine.connect() as conn:
            # Drop new tables
            tables_to_drop = [
                "data_subject_rights",
                "data_processing_consent", 
                "user_sessions"
            ]
            
            for table in tables_to_drop:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    logger.info(f"Dropped table: {table}")
                except SQLAlchemyError as e:
                    logger.warning(f"Could not drop table {table}: {e}")
            
            # Remove added columns (PostgreSQL specific)
            columns_to_remove = [
                ("enhanced_chat_history", "user_message_encrypted"),
                ("enhanced_chat_history", "bot_response_encrypted"),
                ("enhanced_chat_history", "data_classification"),
                ("enhanced_chat_history", "retention_policy"),
                ("enhanced_chat_history", "deleted_at"),
                ("enhanced_chat_history", "anonymized_at"),
                ("memory_context_cache", "context_data_encrypted"),
                ("memory_context_cache", "data_classification"),
                ("memory_context_cache", "access_control"),
            ]
            
            for table, column in columns_to_remove:
                try:
                    conn.execute(text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}"))
                    logger.info(f"Dropped column {column} from {table}")
                except SQLAlchemyError as e:
                    logger.warning(f"Could not drop column {column} from {table}: {e}")
            
            conn.commit()
    
    def verify_migration(self):
        """Verify that the migration was successful"""
        logger.info("Verifying security migration...")
        
        with self.engine.connect() as conn:
            # Check that new tables exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('user_sessions', 'data_processing_consent', 'data_subject_rights')
            """))
            
            existing_tables = [row[0] for row in result]
            expected_tables = ['user_sessions', 'data_processing_consent', 'data_subject_rights']
            
            for table in expected_tables:
                if table in existing_tables:
                    logger.info(f"✓ Table {table} exists")
                else:
                    logger.error(f"✗ Table {table} missing")
            
            # Check that new columns exist
            result = conn.execute(text("""
                SELECT table_name, column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name IN ('enhanced_chat_history', 'memory_context_cache')
                AND column_name LIKE '%encrypted%' OR column_name = 'data_classification'
            """))
            
            existing_columns = [(row[0], row[1]) for row in result]
            expected_columns = [
                ('enhanced_chat_history', 'user_message_encrypted'),
                ('enhanced_chat_history', 'bot_response_encrypted'),
                ('enhanced_chat_history', 'data_classification'),
                ('memory_context_cache', 'context_data_encrypted'),
                ('memory_context_cache', 'data_classification'),
            ]
            
            for table, column in expected_columns:
                if (table, column) in existing_columns:
                    logger.info(f"✓ Column {table}.{column} exists")
                else:
                    logger.warning(f"✗ Column {table}.{column} missing")
        
        logger.info("Migration verification completed")

def run_security_migration():
    """Main function to run security migration"""
    migration = SecurityMigration()
    migration.run_migration()
    migration.verify_migration()

def rollback_security_migration():
    """Main function to rollback security migration"""
    migration = SecurityMigration()
    migration.rollback_migration()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_security_migration()
    else:
        run_security_migration()