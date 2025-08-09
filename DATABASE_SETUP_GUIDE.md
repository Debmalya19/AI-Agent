# Knowledge Base Database Setup Guide

## Overview
This guide provides step-by-step instructions for setting up a PostgreSQL database for the knowledge base system, migrating existing data, and integrating with the existing application.

## Architecture
- **Database**: PostgreSQL with connection pooling
- **ORM**: SQLAlchemy with declarative models
- **Migration**: Automated data migration from Excel/txt files
- **Storage**: Persistent storage replacing in-memory FAISS

## Database Schema
- `knowledge_entries`: Text knowledge with embeddings
- `customers`: Customer information
- `orders`: Order data
- `support_intents`: Support intents and categories
- `support_responses`: Support response templates
- `chat_history`: Conversation history

## Setup Instructions

### 1. Prerequisites
- PostgreSQL server running locally or remotely
- Python 3.8+ with pip

### 2. Environment Setup
```bash
# Install PostgreSQL (if not already installed)
# Create database: knowledge_base

# Update .env file with your credentials
cp .env.example .env
# Edit .env with your database connection details
```

### 3. Install Dependencies
```bash
pip install -r requirement.txt
```

### 4. Database Setup
```bash
# Run the complete setup
python setup_database.py
```

### 5. Manual Setup (Alternative)
```bash
# Create database tables
python database_init.py

# Migrate existing data
python migrate_data.py
```

## Usage Examples

### Basic CRUD Operations
```python
from database import SessionLocal
from db_utils import create_knowledge_entry, get_knowledge_entries

# Create a new knowledge entry
db = SessionLocal()
entry = create_knowledge_entry(db, "FAQ", "This is the answer", "manual")
db.close()

# Get all knowledge entries
db = SessionLocal()
entries = get_knowledge_entries(db)
db.close()
```

### Database Connection
```python
from database import get_db

# Use in FastAPI endpoints
@app.get("/knowledge")
def get_knowledge(db: Session = Depends(get_db)):
    return db.query(KnowledgeEntry).all()
```

## Migration Status
- ✅ Knowledge.txt → knowledge_entries table
- ✅ customer_knowledge_base.xlsx → customers & orders tables
- ✅ customer_support_knowledge_base.xlsx → support_intents & support_responses tables

## Integration with Main Application
To integrate with the existing main.py, you'll need to:
1. Replace FAISS vector store with database queries
2. Update knowledge retrieval to use database
3. Update chat history storage to use database

## Troubleshooting
- **Connection Issues**: Check DATABASE_URL in .env file
- **Migration Errors**: Ensure Excel files exist in data/ directory
- **Permission Errors**: Ensure PostgreSQL user has correct permissions

## Performance Tips
- Use connection pooling for production
- Add indexes on frequently queried columns
- Consider partitioning for large datasets
