#!/usr/bin/env python3
"""
Simple script to run the memory layer database migration.
This script can be executed to set up the enhanced memory layer tables.
"""

import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Run the memory layer migration"""
    try:
        from memory_migration import main as run_migration
        run_migration()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required dependencies are installed:")
        print("pip install sqlalchemy psycopg2-binary python-dotenv")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()