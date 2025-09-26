#!/usr/bin/env python3
"""
Database Switching Utility

This script helps switch between SQLite and PostgreSQL configurations.
"""

import os
import sys
import shutil
from pathlib import Path

def backup_env_file():
    """Create a backup of the current .env file"""
    env_path = Path(".env")
    if env_path.exists():
        backup_path = Path(f".env.backup.{int(time.time())}")
        shutil.copy2(env_path, backup_path)
        print(f"✅ Backed up .env to {backup_path}")
        return backup_path
    return None

def switch_to_postgresql():
    """Switch configuration to PostgreSQL"""
    env_content = """# Database Configuration
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

GOOGLE_API_KEY="AIzaSyDeiOQQB9fHDHtsczKxqWcEqN9B5tDGCZE"

# Application Settings
DEBUG=True
HOST=127.0.0.1
PORT=8080

LOG_LEVEL=INFO
LOG_FILE=admin_dashboard.log
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✅ Switched to PostgreSQL configuration")
    print("📝 Make sure to run: python scripts/setup_postgresql.py")

def switch_to_sqlite():
    """Switch configuration to SQLite"""
    env_content = """# Database Configuration
# Use SQLite for development/testing when PostgreSQL is not available
DATABASE_URL=sqlite:///ai_agent.db

# PostgreSQL Configuration (uncomment when PostgreSQL is available)
# DATABASE_URL=postgresql://ai_agent_user:ai_agent_password@localhost:5432/ai_agent

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

GOOGLE_API_KEY="AIzaSyDeiOQQB9fHDHtsczKxqWcEqN9B5tDGCZE"

# Application Settings
DEBUG=True
HOST=127.0.0.1
PORT=8080

LOG_LEVEL=INFO
LOG_FILE=admin_dashboard.log
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✅ Switched to SQLite configuration")

def show_current_config():
    """Show current database configuration"""
    try:
        with open(".env", "r") as f:
            content = f.read()
            
        for line in content.split('\n'):
            if line.startswith('DATABASE_URL=') and not line.startswith('#'):
                db_url = line.split('=', 1)[1]
                if db_url.startswith('postgresql'):
                    print("📊 Current configuration: PostgreSQL")
                    print(f"   URL: {db_url}")
                elif db_url.startswith('sqlite'):
                    print("📊 Current configuration: SQLite")
                    print(f"   URL: {db_url}")
                else:
                    print(f"📊 Current configuration: Unknown ({db_url})")
                return
        
        print("❓ No active DATABASE_URL found in .env")
        
    except FileNotFoundError:
        print("❌ .env file not found")

def main():
    """Main function"""
    import time
    
    if len(sys.argv) < 2:
        print("Database Switching Utility")
        print("Usage: python scripts/switch_database.py [postgresql|sqlite|status]")
        print("")
        print("Commands:")
        print("  postgresql  - Switch to PostgreSQL configuration")
        print("  sqlite      - Switch to SQLite configuration")
        print("  status      - Show current database configuration")
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        show_current_config()
    elif command == "postgresql":
        backup_env_file()
        switch_to_postgresql()
    elif command == "sqlite":
        backup_env_file()
        switch_to_sqlite()
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: postgresql, sqlite, status")

if __name__ == "__main__":
    main()