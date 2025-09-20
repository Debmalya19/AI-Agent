"""
Initialize social media integration
Creates necessary database tables and updates existing ones
"""

import logging
from sqlalchemy import inspect
from backend.database import engine, Base, init_db
from backend.social_media_models import SocialMediaMention, SocialMediaResponse, update_customer_model, update_ticket_model
from backend.models import Customer, Ticket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_social_media_integration():
    """Initialize the social media integration system"""
    
    logger.info("Initializing social media integration...")
    
    # Update existing models with social media fields
    update_customer_model()
    update_ticket_model()
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    logger.info("Social media integration initialized successfully!")

def verify_social_media_tables():
    """Verify that all social media related tables are created properly"""
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    logger.info(f"Available tables: {tables}")
    
    expected_tables = [
        'social_media_mentions',
        'social_media_responses'
    ]
    
    for table in expected_tables:
        if table in tables:
            logger.info(f"✓ {table} table exists")
            # Verify columns
            columns = [col['name'] for col in inspector.get_columns(table)]
            logger.info(f"  Columns: {', '.join(columns)}")
        else:
            logger.warning(f"✗ {table} table missing")
    
    # Verify customer table updates
    if 'customers' in tables:
        customer_columns = [col['name'] for col in inspector.get_columns('customers')]
        if 'twitter_handle' in customer_columns:
            logger.info("✓ Customer table updated with social media fields")
        else:
            logger.warning("✗ Customer table missing social media fields")

def main():
    """Main initialization function"""
    try:
        init_social_media_integration()
        verify_social_media_tables()
        logger.info("Social media integration setup completed successfully!")
    except Exception as e:
        logger.error(f"Error during social media integration setup: {e}")
        raise

if __name__ == "__main__":
    main()