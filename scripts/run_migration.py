#!/usr/bin/env python3
# Migration script to populate database with Excel data
# This script should be run before starting the application to ensure
# all Excel data is migrated to the database

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_database_setup():
    """Check if database is properly set up"""
    try:
        from database import engine
        from models import Base
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False

def run_migrations():
    """Run all data migrations from Excel to database"""
    try:
        from migrate_data import migrate_all
        
        logger.info("Starting data migration from Excel files to database...")
        migrate_all()
        logger.info("Data migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"Data migration failed: {e}")
        return False

def verify_migration():
    """Verify that data was migrated correctly"""
    try:
        from database import SessionLocal
        from models import Customer, Order, SupportIntent, SupportResponse, KnowledgeEntry
        
        db: Session = SessionLocal()
        
        # Check customer data
        customer_count = db.query(Customer).count()
        order_count = db.query(Order).count()
        
        # Check support knowledge
        intent_count = db.query(SupportIntent).count()
        response_count = db.query(SupportResponse).count()
        
        # Check knowledge entries
        knowledge_count = db.query(KnowledgeEntry).count()
        
        db.close()
        return customer_count > 0 or intent_count > 0 or knowledge_count > 0
        
    except Exception as e:
        logger.error(f"Migration verification failed: {e}")
        return False

def main():
    """Main migration process"""
    logger.info("Starting database migration process...")
    
    # Check if Excel files exist
    excel_files = [
        'data/customer_knowledge_base.xlsx',
        'data/customer_support_knowledge_base.xlsx',
        'data/knowledge.txt'
    ]
    
    missing_files = []
    for file in excel_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Missing required files: {missing_files}")
        sys.exit(1)
    
    # Setup database
    if not check_database_setup():
        sys.exit(1)
    
    # Run migrations
    if not run_migrations():
        sys.exit(1)
    
    # Verify migrations
    if not verify_migration():
        logger.error("Migration verification failed")
        sys.exit(1)
    
    logger.info("All migrations completed successfully!")
    logger.info("You can now start the application with database queries instead of Excel files")
    
    return True

if __name__ == "__main__":
    main()
