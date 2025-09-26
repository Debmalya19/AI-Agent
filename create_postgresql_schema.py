#!/usr/bin/env python3
"""
Create PostgreSQL database schema from SQLAlchemy models
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import create_database_engine, Base
from backend.unified_models import *
from backend.models import *
from backend.memory_models import *

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_schema():
    """Create all database tables"""
    try:
        load_dotenv()
        
        # Get database engine
        engine = create_database_engine()
        
        logger.info("Creating PostgreSQL database schema...")
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        logger.info("Database schema created successfully!")
        
        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info(f"Created {len(tables)} tables:")
        for table in sorted(tables):
            logger.info(f"  - {table}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create schema: {e}")
        return False

if __name__ == "__main__":
    success = create_schema()
    sys.exit(0 if success else 1)