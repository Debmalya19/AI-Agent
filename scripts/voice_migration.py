#!/usr/bin/env python3
"""
Voice Assistant Database Migration Script
Creates voice_settings and voice_analytics tables with proper foreign key relationships.
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text, MetaData, Table, Column, Integer, String, Boolean, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from dotenv import load_dotenv

# Add backend directory to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend'))

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/knowledge_base"
)


def check_database_connection():
    """Check if database connection is available"""
    try:
        engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        return engine
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None


def check_prerequisites(engine):
    """Check if prerequisite tables exist"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    required_tables = ['users']
    missing_tables = [table for table in required_tables if table not in tables]
    
    if missing_tables:
        print(f"❌ Missing prerequisite tables: {missing_tables}")
        print("Please run the main database initialization first.")
        return False
    
    print("✅ All prerequisite tables exist")
    return True


def create_voice_settings_table(engine):
    """Create voice_settings table"""
    try:
        with engine.connect() as conn:
            # Check if table already exists
            inspector = inspect(engine)
            if 'voice_settings' in inspector.get_table_names():
                print("✅ voice_settings table already exists")
                return True
            
            # Create voice_settings table
            conn.execute(text("""
                CREATE TABLE voice_settings (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
                    auto_play_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                    voice_name VARCHAR(100) NOT NULL DEFAULT 'default',
                    speech_rate FLOAT NOT NULL DEFAULT 1.0,
                    speech_pitch FLOAT NOT NULL DEFAULT 1.0,
                    speech_volume FLOAT NOT NULL DEFAULT 1.0,
                    language VARCHAR(10) NOT NULL DEFAULT 'en-US',
                    microphone_sensitivity FLOAT NOT NULL DEFAULT 0.5,
                    noise_cancellation BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create indexes for performance
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_voice_settings_user_id 
                ON voice_settings(user_id)
            """))
            
            # Create trigger for updated_at
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION update_voice_settings_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """))
            
            conn.execute(text("""
                CREATE TRIGGER trigger_voice_settings_updated_at
                    BEFORE UPDATE ON voice_settings
                    FOR EACH ROW
                    EXECUTE FUNCTION update_voice_settings_updated_at()
            """))
            
            conn.commit()
            print("✅ voice_settings table created successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error creating voice_settings table: {e}")
        return False


def create_voice_analytics_table(engine):
    """Create voice_analytics table"""
    try:
        with engine.connect() as conn:
            # Check if table already exists
            inspector = inspect(engine)
            if 'voice_analytics' in inspector.get_table_names():
                print("✅ voice_analytics table already exists")
                return True
            
            # Create voice_analytics table
            conn.execute(text("""
                CREATE TABLE voice_analytics (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    session_id VARCHAR(255),
                    action_type VARCHAR(50) NOT NULL,
                    duration_ms INTEGER,
                    text_length INTEGER,
                    accuracy_score FLOAT,
                    error_message TEXT,
                    analytics_metadata JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create indexes for performance
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_voice_analytics_user_id 
                ON voice_analytics(user_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_voice_analytics_session_id 
                ON voice_analytics(session_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_voice_analytics_action_type 
                ON voice_analytics(action_type)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_voice_analytics_created_at 
                ON voice_analytics(created_at)
            """))
            
            # Create composite index for common queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_voice_analytics_user_action_time 
                ON voice_analytics(user_id, action_type, created_at)
            """))
            
            conn.commit()
            print("✅ voice_analytics table created successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error creating voice_analytics table: {e}")
        return False


def add_constraints_and_validations(engine):
    """Add additional constraints and validations"""
    try:
        with engine.connect() as conn:
            # Check if constraints already exist and add them if they don't
            constraints_to_add = [
                ("voice_settings", "chk_speech_rate", "speech_rate >= 0.1 AND speech_rate <= 3.0"),
                ("voice_settings", "chk_speech_pitch", "speech_pitch >= 0.0 AND speech_pitch <= 2.0"),
                ("voice_settings", "chk_speech_volume", "speech_volume >= 0.0 AND speech_volume <= 1.0"),
                ("voice_settings", "chk_microphone_sensitivity", "microphone_sensitivity >= 0.0 AND microphone_sensitivity <= 1.0"),
                ("voice_analytics", "chk_duration_ms", "duration_ms IS NULL OR duration_ms >= 0"),
                ("voice_analytics", "chk_text_length", "text_length IS NULL OR text_length >= 0"),
                ("voice_analytics", "chk_accuracy_score", "accuracy_score IS NULL OR (accuracy_score >= 0.0 AND accuracy_score <= 1.0)")
            ]
            
            for table_name, constraint_name, constraint_condition in constraints_to_add:
                # Check if constraint exists
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM information_schema.table_constraints 
                    WHERE table_name = :table_name AND constraint_name = :constraint_name
                """), {"table_name": table_name, "constraint_name": constraint_name})
                
                if result.scalar() == 0:
                    # Constraint doesn't exist, add it
                    conn.execute(text(f"""
                        ALTER TABLE {table_name} 
                        ADD CONSTRAINT {constraint_name} 
                        CHECK ({constraint_condition})
                    """))
                    print(f"✅ Added constraint {constraint_name} to {table_name}")
                else:
                    print(f"✅ Constraint {constraint_name} already exists on {table_name}")
            
            conn.commit()
            print("✅ Constraints and validations processed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error adding constraints: {e}")
        return False


def create_sample_voice_data(engine):
    """Create sample voice data for testing"""
    try:
        with engine.connect() as conn:
            # Check if sample data already exists
            result = conn.execute(text("SELECT COUNT(*) FROM voice_settings")).scalar()
            if result > 0:
                print("✅ Sample voice data already exists")
                return True
            
            # Get existing users to create sample voice settings
            users_result = conn.execute(text("SELECT user_id FROM users LIMIT 3"))
            users = users_result.fetchall()
            
            if not users:
                print("⚠️ No users found, skipping sample voice data creation")
                return True
            
            # Create sample voice settings for existing users
            for user in users:
                user_id = user[0]
                conn.execute(text("""
                    INSERT INTO voice_settings (
                        user_id, auto_play_enabled, voice_name, speech_rate, 
                        speech_pitch, speech_volume, language, 
                        microphone_sensitivity, noise_cancellation
                    ) VALUES (
                        :user_id, :auto_play, :voice_name, :speech_rate,
                        :speech_pitch, :speech_volume, :language,
                        :mic_sensitivity, :noise_cancellation
                    )
                """), {
                    'user_id': user_id,
                    'auto_play': False,
                    'voice_name': 'default',
                    'speech_rate': 1.0,
                    'speech_pitch': 1.0,
                    'speech_volume': 1.0,
                    'language': 'en-US',
                    'mic_sensitivity': 0.5,
                    'noise_cancellation': True
                })
                
                # Create sample analytics data
                conn.execute(text("""
                    INSERT INTO voice_analytics (
                        user_id, session_id, action_type, duration_ms, 
                        text_length, accuracy_score, analytics_metadata
                    ) VALUES (
                        :user_id, :session_id, :action_type, :duration_ms,
                        :text_length, :accuracy_score, :analytics_metadata
                    )
                """), {
                    'user_id': user_id,
                    'session_id': f'session_{user_id}_001',
                    'action_type': 'stt_complete',
                    'duration_ms': 1500,
                    'text_length': 25,
                    'accuracy_score': 0.95,
                    'analytics_metadata': '{"test": true, "sample_data": true}'
                })
            
            conn.commit()
            print(f"✅ Created sample voice data for {len(users)} users")
            return True
            
    except Exception as e:
        print(f"❌ Error creating sample voice data: {e}")
        return False


def verify_migration(engine):
    """Verify the migration was successful"""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print("\n📊 Voice Migration Verification:")
        print("=" * 50)
        
        # Check voice_settings table
        if 'voice_settings' in tables:
            columns = [col['name'] for col in inspector.get_columns('voice_settings')]
            with engine.connect() as conn:
                count = conn.execute(text("SELECT COUNT(*) FROM voice_settings")).scalar()
            print(f"✅ voice_settings: {count} records, {len(columns)} columns")
            print(f"   Columns: {', '.join(columns)}")
        else:
            print("❌ voice_settings table not found")
            return False
        
        # Check voice_analytics table
        if 'voice_analytics' in tables:
            columns = [col['name'] for col in inspector.get_columns('voice_analytics')]
            with engine.connect() as conn:
                count = conn.execute(text("SELECT COUNT(*) FROM voice_analytics")).scalar()
            print(f"✅ voice_analytics: {count} records, {len(columns)} columns")
            print(f"   Columns: {', '.join(columns)}")
        else:
            print("❌ voice_analytics table not found")
            return False
        
        # Check foreign key relationships
        voice_settings_fks = inspector.get_foreign_keys('voice_settings')
        voice_analytics_fks = inspector.get_foreign_keys('voice_analytics')
        
        print(f"✅ voice_settings foreign keys: {len(voice_settings_fks)}")
        print(f"✅ voice_analytics foreign keys: {len(voice_analytics_fks)}")
        
        # Check indexes
        voice_settings_indexes = inspector.get_indexes('voice_settings')
        voice_analytics_indexes = inspector.get_indexes('voice_analytics')
        
        print(f"✅ voice_settings indexes: {len(voice_settings_indexes)}")
        print(f"✅ voice_analytics indexes: {len(voice_analytics_indexes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def main():
    """Main migration function"""
    print("🎤 Voice Assistant Database Migration")
    print("=" * 50)
    
    # Check database connection
    engine = check_database_connection()
    if not engine:
        sys.exit(1)
    
    # Check prerequisites
    if not check_prerequisites(engine):
        sys.exit(1)
    
    # Create voice tables
    success = True
    success &= create_voice_settings_table(engine)
    success &= create_voice_analytics_table(engine)
    success &= add_constraints_and_validations(engine)
    
    if not success:
        print("❌ Migration failed")
        sys.exit(1)
    
    # Create sample data
    create_sample_voice_data(engine)
    
    # Verify migration
    if verify_migration(engine):
        print("\n🎉 Voice assistant migration completed successfully!")
    else:
        print("\n❌ Migration verification failed")
        sys.exit(1)


if __name__ == "__main__":
    main()