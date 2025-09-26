from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import (
    SQLAlchemyError, DisconnectionError, OperationalError, 
    DatabaseError, TimeoutError, InvalidRequestError,
    IntegrityError, DataError, ProgrammingError
)
from sqlalchemy.pool import QueuePool
import os
import time
import logging
import random
from typing import Optional, Dict, Any, Callable, Union
from dotenv import load_dotenv
import psycopg2
from psycopg2 import OperationalError as PsycopgOperationalError
from psycopg2 import DatabaseError as PsycopgDatabaseError

# Import configuration validation
from .config_validation import (
    DatabaseConfigValidator, 
    ConfigValidationError,
    get_validated_db_params
)

load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

# Import database logging utilities
from .database_logging import (
    log_database_operation, log_connection_event, log_error_with_context,
    log_performance_metrics, log_health_check, DatabaseOperationLogger
)

class PostgreSQLErrorHandler:
    """PostgreSQL-specific error handling with categorization and retry logic"""
    
    # Error categories for different handling strategies
    TRANSIENT_ERRORS = (
        OperationalError,
        DisconnectionError,
        TimeoutError,
        PsycopgOperationalError,
    )
    
    PERMANENT_ERRORS = (
        ProgrammingError,
        DataError,
        IntegrityError,
    )
    
    CONNECTION_ERRORS = (
        "connection to server",
        "server closed the connection",
        "connection not open",
        "connection already closed",
        "could not connect to server",
        "timeout expired",
        "connection timed out",
    )
    
    @staticmethod
    def is_transient_error(error: Exception) -> bool:
        """Check if error is transient and should be retried"""
        if isinstance(error, PostgreSQLErrorHandler.TRANSIENT_ERRORS):
            return True
        
        error_msg = str(error).lower()
        return any(conn_err in error_msg for conn_err in PostgreSQLErrorHandler.CONNECTION_ERRORS)
    
    @staticmethod
    def is_connection_error(error: Exception) -> bool:
        """Check if error is specifically a connection error"""
        error_msg = str(error).lower()
        return any(conn_err in error_msg for conn_err in PostgreSQLErrorHandler.CONNECTION_ERRORS)
    
    @staticmethod
    def get_error_category(error: Exception) -> str:
        """Categorize error for appropriate handling"""
        if isinstance(error, PostgreSQLErrorHandler.PERMANENT_ERRORS):
            return "permanent"
        elif PostgreSQLErrorHandler.is_transient_error(error):
            return "transient"
        elif PostgreSQLErrorHandler.is_connection_error(error):
            return "connection"
        else:
            return "unknown"
    
    @staticmethod
    def get_retry_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0, jitter: bool = True) -> float:
        """Calculate retry delay with exponential backoff and jitter"""
        delay = min(base_delay * (2 ** attempt), max_delay)
        if jitter:
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
        return delay

def retry_on_database_error(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for database operations with retry logic"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_category = PostgreSQLErrorHandler.get_error_category(e)
                    
                    # Don't retry permanent errors
                    if error_category == "permanent":
                        logger.error(f"Permanent database error in {func.__name__}: {e}")
                        raise
                    
                    # Don't retry on last attempt
                    if attempt >= max_retries:
                        break
                    
                    # Only retry transient and connection errors
                    if error_category in ["transient", "connection"]:
                        delay = PostgreSQLErrorHandler.get_retry_delay(attempt, base_delay)
                        logger.warning(
                            f"Database operation {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        # Unknown error category, don't retry
                        break
            
            # All retries exhausted
            logger.error(f"Database operation {func.__name__} failed after {max_retries + 1} attempts: {last_error}")
            raise last_error
        
        return wrapper
    return decorator

# Initialize configuration validator
config_validator = DatabaseConfigValidator()

# Get validated database configuration
try:
    db_config = config_validator.get_database_connection_params()
    DATABASE_URL = db_config['url']
    logger.info(f"Using validated {db_config['database_type'].upper()} database configuration")
except ConfigValidationError as e:
    logger.error(f"Database configuration validation failed: {e}")
    # Fallback to basic configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/ai_agent")
    logger.warning("Using fallback database configuration - validation may fail at runtime")

def validate_database_url(url: str) -> bool:
    """Validate database URL format using the configuration validator"""
    try:
        is_valid, db_type, components = config_validator.validate_database_url(url)
        return is_valid
    except Exception as e:
        logger.error(f"Error validating database URL: {e}")
        return False

@retry_on_database_error(max_retries=3, base_delay=1.0)
def create_database_engine(database_url: str = None, max_retries: int = 3) -> Optional[object]:
    """Create database engine with validated configuration and retry logic"""
    
    # Use provided URL or get from validated configuration
    if database_url is None:
        try:
            db_params = config_validator.get_database_connection_params()
            database_url = db_params['url']
        except ConfigValidationError as e:
            logger.error(f"Failed to get validated database configuration: {e}")
            return None
    
    # Validate URL format
    is_valid, db_type, components = config_validator.validate_database_url(database_url)
    if not is_valid:
        logger.error(f"Invalid database URL format: {database_url}")
        return None
    
    for attempt in range(max_retries):
        try:
            # Get validated configuration parameters
            try:
                db_params = config_validator.get_database_connection_params()
            except ConfigValidationError as e:
                logger.error(f"Configuration validation failed: {e}")
                return None
            
            # Configure connection args based on database type
            connect_args = {}
            engine_kwargs = {
                "echo": db_params.get('echo', False),
                "future": True,  # Use SQLAlchemy 2.0 style
            }
            
            if db_type == "postgresql":
                # PostgreSQL-optimized configuration with validated parameters
                connect_args = {
                    "connect_timeout": db_params.get('connect_timeout', 10),
                    "application_name": "ai_agent",
                    "options": "-c timezone=UTC"
                }
                
                # Production-ready connection pooling parameters
                engine_kwargs.update({
                    "pool_size": db_params.get('pool_size', 20),
                    "max_overflow": db_params.get('max_overflow', 30),
                    "pool_pre_ping": True,  # Enable connection health checks
                    "pool_recycle": db_params.get('pool_recycle', 3600),
                    "pool_timeout": db_params.get('pool_timeout', 30),
                    "poolclass": QueuePool,
                })
                
            elif db_type == "sqlite":
                connect_args = {"check_same_thread": False}
                # SQLite doesn't support connection pooling
            
            engine_kwargs["connect_args"] = connect_args
            
            # Create engine
            engine = create_engine(database_url, **engine_kwargs)
            
            # Test connection with logging
            with DatabaseOperationLogger("engine_connection_test") as op_logger:
                with engine.connect() as conn:
                    if db_type == "postgresql":
                        result = conn.execute(text("SELECT version()"))
                        version = result.fetchone()[0]
                        logger.info(f"Connected to PostgreSQL: {version}")
                        log_connection_event("postgresql_connected", {
                            "version": version.split()[1] if len(version.split()) > 1 else "unknown",
                            "attempt": attempt + 1
                        })
                    else:
                        conn.execute(text("SELECT 1"))
                        logger.info("Connected to SQLite database")
                        log_connection_event("sqlite_connected", {"attempt": attempt + 1})
            
            logger.info(f"Database engine created successfully (attempt {attempt + 1})")
            log_database_operation("engine_creation", success=True, details={
                "database_type": db_type,
                "attempt": attempt + 1,
                "pool_size": engine_kwargs.get("pool_size"),
                "max_overflow": engine_kwargs.get("max_overflow")
            })
            return engine
            
        except Exception as e:
            log_error_with_context(e, "engine_creation", {
                "database_url": database_url.split("@")[1] if "@" in database_url else "local",
                "attempt": attempt + 1,
                "max_retries": max_retries
            }, retry_count=attempt)
            
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("All database connection attempts failed")
                log_database_operation("engine_creation", success=False, details={
                    "total_attempts": max_retries,
                    "final_error": str(e)
                }, error=e)
                return None

def health_check_database(engine) -> bool:
    """Perform database health check with enhanced logging"""
    if not engine:
        log_health_check("unhealthy", {"reason": "engine_unavailable"})
        return False
    
    try:
        with DatabaseOperationLogger("health_check") as op_logger:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        
        log_health_check("healthy")
        return True
    except Exception as e:
        log_error_with_context(e, "health_check")
        log_health_check("unhealthy", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        logger.error(f"Database health check failed: {e}")
        return False

# Create engine with optimized configuration
engine = create_database_engine(DATABASE_URL)

# Create session factory with retry logic
def create_session_factory(engine):
    """Create session factory with proper configuration"""
    if engine:
        return sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=engine,
            expire_on_commit=False  # Prevent lazy loading issues
        )
    else:
        # Create a dummy session factory that raises an error when used
        def dummy_session():
            raise RuntimeError("Database not available - check connection configuration")
        return dummy_session

SessionLocal = create_session_factory(engine)

# Create base class for models
Base = declarative_base()

# Dependency to get database session with retry logic
def get_db():
    """Database session dependency with enhanced PostgreSQL error handling"""
    max_retries = 3
    base_delay = 1.0
    
    for attempt in range(max_retries):
        db = None
        try:
            db = SessionLocal()
            
            # Test the connection with a simple query
            db.execute(text("SELECT 1"))
            db.commit()
            
            try:
                yield db
                return
            except Exception as session_error:
                # Handle errors during session usage
                error_category = PostgreSQLErrorHandler.get_error_category(session_error)
                logger.error(f"Database session error ({error_category}): {session_error}")
                
                # Rollback transaction on error
                try:
                    db.rollback()
                except Exception as rollback_error:
                    logger.warning(f"Failed to rollback transaction: {rollback_error}")
                
                raise session_error
                
        except Exception as e:
            if db:
                try:
                    db.close()
                except Exception as close_error:
                    logger.warning(f"Failed to close database session: {close_error}")
            
            error_category = PostgreSQLErrorHandler.get_error_category(e)
            
            # Don't retry permanent errors
            if error_category == "permanent":
                logger.error(f"Permanent database error, not retrying: {e}")
                raise RuntimeError("Database operation failed with permanent error") from e
            
            # Retry transient and connection errors
            if attempt < max_retries - 1 and error_category in ["transient", "connection"]:
                delay = PostgreSQLErrorHandler.get_retry_delay(attempt, base_delay)
                logger.warning(
                    f"Database session creation failed ({error_category}), retrying in {delay:.2f}s "
                    f"(attempt {attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(delay)
                continue
            else:
                logger.error(f"Failed to create database session after {max_retries} attempts: {e}")
                raise RuntimeError("Database session unavailable after retries") from e
        finally:
            if db:
                try:
                    db.close()
                except Exception as close_error:
                    logger.warning(f"Failed to close database session in finally block: {close_error}")

def get_db_with_graceful_degradation():
    """Get database session with graceful degradation for unavailable database"""
    try:
        return get_db()
    except Exception as e:
        logger.error(f"Database completely unavailable: {e}")
        # Return a mock session that raises informative errors
        class UnavailableDBSession:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def __getattr__(self, name):
                raise RuntimeError(
                    "Database is currently unavailable. Please try again later or contact support."
                )
        
        yield UnavailableDBSession()

def get_db_with_health_check():
    """Get database session with health check"""
    if not health_check_database(engine):
        raise RuntimeError("Database health check failed")
    
    return get_db()

# Initialize database function
def init_db():
    """Initialize database by creating all unified tables with proper error handling"""
    if not engine:
        logger.error("Cannot initialize database: engine not available")
        raise RuntimeError("Database engine not available")
    
    try:
        logger.info("Initializing database tables...")
        
        # Perform health check before initialization
        if not health_check_database(engine):
            raise RuntimeError("Database health check failed before initialization")
        
        # Import unified models to ensure they are registered with Base
        from . import unified_models
        from . import models  # Keep legacy models for migration compatibility
        
        # Create all tables (both legacy and unified)
        Base.metadata.create_all(bind=engine)
        
        # Verify tables were created
        with engine.connect() as conn:
            if DATABASE_URL.startswith("postgresql"):
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                table_count = result.fetchone()[0]
                logger.info(f"Database initialization completed successfully. Created {table_count} tables.")
            else:
                logger.info("Database initialization completed successfully.")
                
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def get_database_info():
    """Get database connection information for monitoring with configuration validation"""
    if not engine:
        return {"status": "unavailable", "engine": None}
    
    try:
        # Get validated configuration information
        try:
            db_params = config_validator.get_database_connection_params()
            config_status = "validated"
        except ConfigValidationError as e:
            db_params = {"database_type": "unknown", "error": str(e)}
            config_status = "validation_failed"
        
        info = {
            "status": "connected",
            "config_status": config_status,
            "database_type": db_params.get('database_type', 'unknown'),
            "url": DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else "local",  # Hide credentials
        }
        
        # Add pool information for PostgreSQL
        if hasattr(engine, 'pool') and engine.pool:
            info.update({
                "pool_size": getattr(engine.pool, 'size', lambda: 'N/A')(),
                "checked_out": getattr(engine.pool, 'checkedout', lambda: 'N/A')(),
                "overflow": getattr(engine.pool, 'overflow', lambda: 'N/A')(),
                "checked_in": getattr(engine.pool, 'checkedin', lambda: 'N/A')(),
            })
        
        # Test connection
        if health_check_database(engine):
            info["health"] = "healthy"
        else:
            info["health"] = "unhealthy"
        
        # Add configuration parameters if available
        if config_status == "validated" and db_params.get('database_type') == 'postgresql':
            info["config_params"] = {
                "pool_size": db_params.get('pool_size'),
                "max_overflow": db_params.get('max_overflow'),
                "pool_recycle": db_params.get('pool_recycle'),
                "pool_timeout": db_params.get('pool_timeout'),
                "connect_timeout": db_params.get('connect_timeout')
            }
            
        return info
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def validate_current_config() -> Dict[str, Any]:
    """
    Validate current database configuration and return detailed report
    
    Returns:
        Dictionary with validation results and configuration details
    """
    try:
        # Generate comprehensive validation report
        report = config_validator.generate_config_report()
        
        # Get validated parameters
        db_params = config_validator.get_database_connection_params()
        
        return {
            "validation_status": "success",
            "database_type": db_params['database_type'],
            "configuration": db_params,
            "report": report
        }
        
    except ConfigValidationError as e:
        return {
            "validation_status": "failed",
            "error": str(e),
            "report": config_validator.generate_config_report()
        }
    except Exception as e:
        return {
            "validation_status": "error",
            "error": f"Unexpected error: {str(e)}",
            "report": "Unable to generate validation report"
        }
