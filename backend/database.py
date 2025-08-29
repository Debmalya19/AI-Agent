from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration - use PostgreSQL with fallback
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/knowledge_base"
)

# Create engine with connection pooling
try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,  # Set to False in production
        connect_args={"connect_timeout": 5}  # 5 second timeout
    )
except Exception as e:
    print(f"Warning: Failed to create database engine: {e}")
    print("Database functionality will be limited")
    engine = None

# Create session factory
if engine:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # Create a dummy session factory that raises an error when used
    def SessionLocal():
        raise RuntimeError("Database not available")

# Create base class for models
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database function
def init_db():
    """Initialize database by creating all tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
