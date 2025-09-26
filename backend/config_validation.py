"""
Environment Configuration Validation Module

This module provides comprehensive validation for database configuration
and environment variables used by the AI agent application.
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger(__name__)

class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors"""
    pass

class DatabaseConfigValidator:
    """Validator for database configuration parameters"""
    
    # Database URL patterns
    POSTGRESQL_URL_PATTERN = re.compile(
        r'^postgresql://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<database>[^?]+)(?:\?.*)?$'
    )
    
    SQLITE_URL_PATTERN = re.compile(
        r'^sqlite:///(?P<path>.+)$'
    )
    
    # Valid configuration parameters with their types and constraints
    CONFIG_SCHEMA = {
        'DATABASE_URL': {
            'type': str,
            'required': True,
            'validator': 'validate_database_url'
        },
        'DB_POOL_SIZE': {
            'type': int,
            'required': False,
            'default': 20,
            'min_value': 1,
            'max_value': 100
        },
        'DB_MAX_OVERFLOW': {
            'type': int,
            'required': False,
            'default': 30,
            'min_value': 0,
            'max_value': 200
        },
        'DB_POOL_RECYCLE': {
            'type': int,
            'required': False,
            'default': 3600,
            'min_value': 300,  # 5 minutes minimum
            'max_value': 86400  # 24 hours maximum
        },
        'DB_POOL_TIMEOUT': {
            'type': int,
            'required': False,
            'default': 30,
            'min_value': 5,
            'max_value': 300
        },
        'DB_CONNECT_TIMEOUT': {
            'type': int,
            'required': False,
            'default': 10,
            'min_value': 1,
            'max_value': 60
        },
        'DATABASE_ECHO': {
            'type': bool,
            'required': False,
            'default': False
        },
        'POSTGRES_ADMIN_PASSWORD': {
            'type': str,
            'required': False,
            'default': 'postgres'
        }
    }
    
    def __init__(self, env_file_path: Optional[str] = None):
        """Initialize validator and optionally load environment file"""
        if env_file_path:
            load_dotenv(env_file_path)
        else:
            load_dotenv()
    
    def validate_database_url(self, url: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate database URL format and extract components
        
        Returns:
            Tuple of (is_valid, database_type, parsed_components)
        """
        if not url or not isinstance(url, str):
            return False, 'unknown', {}
        
        url = url.strip()
        
        # Check PostgreSQL URL
        pg_match = self.POSTGRESQL_URL_PATTERN.match(url)
        if pg_match:
            components = pg_match.groupdict()
            
            # Validate port if provided
            if components.get('port'):
                port = int(components['port'])
                if not (1 <= port <= 65535):
                    return False, 'postgresql', {}
            else:
                components['port'] = '5432'  # Default PostgreSQL port
            
            # Validate required components
            required_fields = ['user', 'password', 'host', 'database']
            for field in required_fields:
                if not components.get(field):
                    return False, 'postgresql', {}
            
            return True, 'postgresql', components
        
        # Check SQLite URL
        sqlite_match = self.SQLITE_URL_PATTERN.match(url)
        if sqlite_match:
            components = sqlite_match.groupdict()
            path = components['path']
            
            # Validate path is not empty
            if not path:
                return False, 'sqlite', {}
            
            return True, 'sqlite', components
        
        return False, 'unknown', {}
    
    def parse_database_url(self, url: str) -> Dict[str, Any]:
        """
        Parse database URL and return connection parameters
        
        Args:
            url: Database URL string
            
        Returns:
            Dictionary with parsed connection parameters
            
        Raises:
            ConfigValidationError: If URL is invalid
        """
        is_valid, db_type, components = self.validate_database_url(url)
        
        if not is_valid:
            raise ConfigValidationError(f"Invalid database URL format: {url}")
        
        if db_type == 'postgresql':
            return {
                'database_type': 'postgresql',
                'user': components['user'],
                'password': components['password'],
                'host': components['host'],
                'port': int(components['port']),
                'database': components['database'],
                'url': url
            }
        elif db_type == 'sqlite':
            return {
                'database_type': 'sqlite',
                'path': components['path'],
                'url': url
            }
        
        raise ConfigValidationError(f"Unsupported database type: {db_type}")
    
    def validate_config_value(self, key: str, value: Any, schema: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """
        Validate a single configuration value against its schema
        
        Returns:
            Tuple of (is_valid, processed_value, error_message)
        """
        try:
            # Handle None values
            if value is None:
                if schema.get('required', False):
                    return False, None, f"{key} is required but not provided"
                else:
                    return True, schema.get('default'), ""
            
            # Type conversion and validation
            expected_type = schema['type']
            
            if expected_type == bool:
                if isinstance(value, str):
                    processed_value = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    processed_value = bool(value)
            elif expected_type == int:
                processed_value = int(value)
                
                # Check min/max constraints
                if 'min_value' in schema and processed_value < schema['min_value']:
                    return False, processed_value, f"{key} must be >= {schema['min_value']}"
                if 'max_value' in schema and processed_value > schema['max_value']:
                    return False, processed_value, f"{key} must be <= {schema['max_value']}"
            elif expected_type == str:
                processed_value = str(value)
            else:
                processed_value = value
            
            # Custom validator
            if 'validator' in schema:
                validator_method = getattr(self, schema['validator'])
                is_valid, db_type, components = validator_method(processed_value)
                if not is_valid:
                    return False, processed_value, f"Invalid {key} format"
            
            return True, processed_value, ""
            
        except (ValueError, TypeError) as e:
            return False, value, f"Invalid {key} value: {str(e)}"
    
    def validate_environment_config(self) -> Dict[str, Any]:
        """
        Validate all database-related environment configuration
        
        Returns:
            Dictionary with validated configuration values
            
        Raises:
            ConfigValidationError: If validation fails
        """
        validated_config = {}
        errors = []
        
        for key, schema in self.CONFIG_SCHEMA.items():
            env_value = os.getenv(key)
            
            is_valid, processed_value, error_msg = self.validate_config_value(key, env_value, schema)
            
            if not is_valid:
                errors.append(f"{key}: {error_msg}")
            else:
                validated_config[key] = processed_value
        
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ConfigValidationError(error_message)
        
        return validated_config
    
    def get_database_connection_params(self) -> Dict[str, Any]:
        """
        Get validated database connection parameters
        
        Returns:
            Dictionary with connection parameters ready for SQLAlchemy
        """
        config = self.validate_environment_config()
        
        # Parse database URL
        db_params = self.parse_database_url(config['DATABASE_URL'])
        
        # Add connection pool parameters for PostgreSQL
        if db_params['database_type'] == 'postgresql':
            db_params.update({
                'pool_size': config['DB_POOL_SIZE'],
                'max_overflow': config['DB_MAX_OVERFLOW'],
                'pool_recycle': config['DB_POOL_RECYCLE'],
                'pool_timeout': config['DB_POOL_TIMEOUT'],
                'connect_timeout': config['DB_CONNECT_TIMEOUT'],
                'echo': config['DATABASE_ECHO']
            })
        else:
            # SQLite doesn't support connection pooling
            db_params.update({
                'echo': config['DATABASE_ECHO']
            })
        
        return db_params
    
    def validate_connection_health(self, url: str) -> Tuple[bool, str]:
        """
        Validate that a database connection can be established
        
        Args:
            url: Database URL to test
            
        Returns:
            Tuple of (is_healthy, status_message)
        """
        try:
            from sqlalchemy import create_engine, text
            
            # Parse URL to get connection parameters
            db_params = self.parse_database_url(url)
            
            # Create minimal engine for testing
            if db_params['database_type'] == 'postgresql':
                connect_args = {
                    'connect_timeout': 5,  # Short timeout for health check
                    'application_name': 'ai_agent_health_check'
                }
                engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
            else:
                engine = create_engine(url, connect_args={'check_same_thread': False})
            
            # Test connection
            with engine.connect() as conn:
                if db_params['database_type'] == 'postgresql':
                    result = conn.execute(text("SELECT version()"))
                    version_info = result.fetchone()[0]
                    return True, f"PostgreSQL connection successful: {version_info[:50]}..."
                else:
                    conn.execute(text("SELECT 1"))
                    return True, "SQLite connection successful"
                    
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def generate_config_report(self) -> str:
        """
        Generate a comprehensive configuration validation report
        
        Returns:
            Formatted report string
        """
        report_lines = ["Database Configuration Validation Report", "=" * 50]
        
        try:
            config = self.validate_environment_config()
            report_lines.append("✓ Configuration validation: PASSED")
            
            # Database URL analysis
            db_params = self.parse_database_url(config['DATABASE_URL'])
            report_lines.append(f"✓ Database type: {db_params['database_type'].upper()}")
            
            if db_params['database_type'] == 'postgresql':
                report_lines.extend([
                    f"✓ Host: {db_params['host']}:{db_params['port']}",
                    f"✓ Database: {db_params['database']}",
                    f"✓ User: {db_params['user']}",
                    f"✓ Pool size: {config['DB_POOL_SIZE']}",
                    f"✓ Max overflow: {config['DB_MAX_OVERFLOW']}",
                    f"✓ Pool recycle: {config['DB_POOL_RECYCLE']}s",
                    f"✓ Pool timeout: {config['DB_POOL_TIMEOUT']}s",
                    f"✓ Connect timeout: {config['DB_CONNECT_TIMEOUT']}s"
                ])
            else:
                report_lines.append(f"✓ Database file: {db_params['path']}")
            
            # Connection health check
            is_healthy, health_msg = self.validate_connection_health(config['DATABASE_URL'])
            if is_healthy:
                report_lines.append(f"✓ Connection health: {health_msg}")
            else:
                report_lines.append(f"✗ Connection health: {health_msg}")
            
        except ConfigValidationError as e:
            report_lines.extend([
                "✗ Configuration validation: FAILED",
                str(e)
            ])
        except Exception as e:
            report_lines.extend([
                "✗ Unexpected error during validation:",
                str(e)
            ])
        
        return "\n".join(report_lines)

def validate_database_config(env_file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to validate database configuration
    
    Args:
        env_file_path: Optional path to .env file
        
    Returns:
        Validated configuration dictionary
        
    Raises:
        ConfigValidationError: If validation fails
    """
    validator = DatabaseConfigValidator(env_file_path)
    return validator.validate_environment_config()

def get_validated_db_params(env_file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Get validated database connection parameters
    
    Args:
        env_file_path: Optional path to .env file
        
    Returns:
        Database connection parameters
        
    Raises:
        ConfigValidationError: If validation fails
    """
    validator = DatabaseConfigValidator(env_file_path)
    return validator.get_database_connection_params()

def generate_config_report(env_file_path: Optional[str] = None) -> str:
    """
    Generate configuration validation report
    
    Args:
        env_file_path: Optional path to .env file
        
    Returns:
        Formatted report string
    """
    validator = DatabaseConfigValidator(env_file_path)
    return validator.generate_config_report()

if __name__ == "__main__":
    # CLI interface for configuration validation
    import sys
    
    if len(sys.argv) > 1:
        env_file = sys.argv[1]
    else:
        env_file = None
    
    try:
        print(generate_config_report(env_file))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)