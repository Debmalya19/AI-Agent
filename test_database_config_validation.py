#!/usr/bin/env python3
"""
Test suite for database configuration validation

This test suite validates the database configuration validation functionality
and ensures that environment variables are properly validated and parsed.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the current directory to the path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent))

from backend.config_validation import (
    DatabaseConfigValidator,
    ConfigValidationError,
    validate_database_config,
    get_validated_db_params,
    generate_config_report
)

class TestDatabaseConfigValidator(unittest.TestCase):
    """Test cases for DatabaseConfigValidator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = DatabaseConfigValidator()
    
    def test_validate_postgresql_url_valid(self):
        """Test validation of valid PostgreSQL URLs"""
        valid_urls = [
            "postgresql://user:pass@localhost:5432/dbname",
            "postgresql://user:pass@localhost/dbname",
            "postgresql://user:pass@example.com:5432/dbname",
            "postgresql://user:pass@192.168.1.1:5432/dbname"
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                is_valid, db_type, components = self.validator.validate_database_url(url)
                self.assertTrue(is_valid, f"URL should be valid: {url}")
                self.assertEqual(db_type, "postgresql")
                self.assertIn("user", components)
                self.assertIn("password", components)
                self.assertIn("host", components)
                self.assertIn("database", components)
    
    def test_validate_postgresql_url_invalid(self):
        """Test validation of invalid PostgreSQL URLs"""
        invalid_urls = [
            "postgresql://user@localhost:5432/dbname",  # Missing password
            "postgresql://user:pass@/dbname",  # Missing host
            "postgresql://user:pass@localhost:5432/",  # Missing database
            "postgresql://user:pass@localhost:99999/dbname",  # Invalid port
            "postgresql://",  # Incomplete URL
            ""  # Empty string
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                is_valid, db_type, components = self.validator.validate_database_url(url)
                self.assertFalse(is_valid, f"URL should be invalid: {url}")
    
    def test_validate_sqlite_url_valid(self):
        """Test validation of valid SQLite URLs"""
        valid_urls = [
            "sqlite:///test.db",
            "sqlite:///path/to/database.db",
            "sqlite:////absolute/path/to/database.db"
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                is_valid, db_type, components = self.validator.validate_database_url(url)
                self.assertTrue(is_valid, f"URL should be valid: {url}")
                self.assertEqual(db_type, "sqlite")
                self.assertIn("path", components)
    
    def test_validate_sqlite_url_invalid(self):
        """Test validation of invalid SQLite URLs"""
        invalid_urls = [
            "sqlite:///",  # Empty path
            "sqlite://",  # Wrong format
            "sqlite:"  # Incomplete
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                is_valid, db_type, components = self.validator.validate_database_url(url)
                self.assertFalse(is_valid, f"URL should be invalid: {url}")
    
    def test_parse_database_url_postgresql(self):
        """Test parsing PostgreSQL database URL"""
        url = "postgresql://testuser:testpass@localhost:5432/testdb"
        
        result = self.validator.parse_database_url(url)
        
        expected = {
            'database_type': 'postgresql',
            'user': 'testuser',
            'password': 'testpass',
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'url': url
        }
        
        self.assertEqual(result, expected)
    
    def test_parse_database_url_sqlite(self):
        """Test parsing SQLite database URL"""
        url = "sqlite:///test.db"
        
        result = self.validator.parse_database_url(url)
        
        expected = {
            'database_type': 'sqlite',
            'path': 'test.db',
            'url': url
        }
        
        self.assertEqual(result, expected)
    
    def test_parse_database_url_invalid(self):
        """Test parsing invalid database URL"""
        with self.assertRaises(ConfigValidationError):
            self.validator.parse_database_url("invalid://url")
    
    def test_validate_config_value_integer(self):
        """Test validation of integer configuration values"""
        schema = {
            'type': int,
            'min_value': 1,
            'max_value': 100,
            'default': 20
        }
        
        # Valid values
        is_valid, value, error = self.validator.validate_config_value("TEST_INT", "25", schema)
        self.assertTrue(is_valid)
        self.assertEqual(value, 25)
        self.assertEqual(error, "")
        
        # Invalid - too low
        is_valid, value, error = self.validator.validate_config_value("TEST_INT", "0", schema)
        self.assertFalse(is_valid)
        self.assertIn("must be >=", error)
        
        # Invalid - too high
        is_valid, value, error = self.validator.validate_config_value("TEST_INT", "150", schema)
        self.assertFalse(is_valid)
        self.assertIn("must be <=", error)
        
        # Invalid - not a number
        is_valid, value, error = self.validator.validate_config_value("TEST_INT", "not_a_number", schema)
        self.assertFalse(is_valid)
        self.assertIn("Invalid", error)
    
    def test_validate_config_value_boolean(self):
        """Test validation of boolean configuration values"""
        schema = {'type': bool, 'default': False}
        
        # True values
        for true_val in ['true', 'True', '1', 'yes', 'on']:
            is_valid, value, error = self.validator.validate_config_value("TEST_BOOL", true_val, schema)
            self.assertTrue(is_valid)
            self.assertTrue(value)
        
        # False values
        for false_val in ['false', 'False', '0', 'no', 'off']:
            is_valid, value, error = self.validator.validate_config_value("TEST_BOOL", false_val, schema)
            self.assertTrue(is_valid)
            self.assertFalse(value)
    
    @patch.dict(os.environ, {
        'DATABASE_URL': 'postgresql://user:pass@localhost:5432/testdb',
        'DB_POOL_SIZE': '25',
        'DB_MAX_OVERFLOW': '35',
        'DB_POOL_RECYCLE': '7200',
        'DB_POOL_TIMEOUT': '45',
        'DB_CONNECT_TIMEOUT': '15',
        'DATABASE_ECHO': 'true'
    })
    def test_validate_environment_config_valid(self):
        """Test validation of valid environment configuration"""
        config = self.validator.validate_environment_config()
        
        self.assertEqual(config['DATABASE_URL'], 'postgresql://user:pass@localhost:5432/testdb')
        self.assertEqual(config['DB_POOL_SIZE'], 25)
        self.assertEqual(config['DB_MAX_OVERFLOW'], 35)
        self.assertEqual(config['DB_POOL_RECYCLE'], 7200)
        self.assertEqual(config['DB_POOL_TIMEOUT'], 45)
        self.assertEqual(config['DB_CONNECT_TIMEOUT'], 15)
        self.assertTrue(config['DATABASE_ECHO'])
    
    @patch.dict(os.environ, {
        'DATABASE_URL': 'invalid://url',
        'DB_POOL_SIZE': '0',  # Too low
        'DB_MAX_OVERFLOW': '300'  # Too high
    })
    def test_validate_environment_config_invalid(self):
        """Test validation of invalid environment configuration"""
        with self.assertRaises(ConfigValidationError) as context:
            self.validator.validate_environment_config()
        
        error_message = str(context.exception)
        self.assertIn("DATABASE_URL", error_message)
        self.assertIn("DB_POOL_SIZE", error_message)
        self.assertIn("DB_MAX_OVERFLOW", error_message)
    
    @patch.dict(os.environ, {
        'DATABASE_URL': 'postgresql://user:pass@localhost:5432/testdb'
    })
    def test_get_database_connection_params_postgresql(self):
        """Test getting PostgreSQL connection parameters"""
        params = self.validator.get_database_connection_params()
        
        self.assertEqual(params['database_type'], 'postgresql')
        self.assertEqual(params['user'], 'user')
        self.assertEqual(params['password'], 'pass')
        self.assertEqual(params['host'], 'localhost')
        self.assertEqual(params['port'], 5432)
        self.assertEqual(params['database'], 'testdb')
        self.assertIn('pool_size', params)
        self.assertIn('max_overflow', params)
    
    @patch.dict(os.environ, {
        'DATABASE_URL': 'sqlite:///test.db'
    })
    def test_get_database_connection_params_sqlite(self):
        """Test getting SQLite connection parameters"""
        params = self.validator.get_database_connection_params()
        
        self.assertEqual(params['database_type'], 'sqlite')
        self.assertEqual(params['path'], 'test.db')
        self.assertNotIn('pool_size', params)  # SQLite doesn't support pooling
    
    def test_generate_config_report(self):
        """Test configuration report generation"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/testdb'
        }):
            report = self.validator.generate_config_report()
            
            self.assertIn("Database Configuration Validation Report", report)
            self.assertIn("POSTGRESQL", report)
            self.assertIn("localhost:5432", report)

class TestConfigValidationFunctions(unittest.TestCase):
    """Test cases for module-level functions"""
    
    @patch.dict(os.environ, {
        'DATABASE_URL': 'postgresql://user:pass@localhost:5432/testdb'
    })
    def test_validate_database_config(self):
        """Test validate_database_config function"""
        config = validate_database_config()
        self.assertIn('DATABASE_URL', config)
        self.assertEqual(config['DATABASE_URL'], 'postgresql://user:pass@localhost:5432/testdb')
    
    @patch.dict(os.environ, {
        'DATABASE_URL': 'postgresql://user:pass@localhost:5432/testdb'
    })
    def test_get_validated_db_params(self):
        """Test get_validated_db_params function"""
        params = get_validated_db_params()
        self.assertEqual(params['database_type'], 'postgresql')
        self.assertIn('pool_size', params)
    
    @patch.dict(os.environ, {
        'DATABASE_URL': 'postgresql://user:pass@localhost:5432/testdb'
    })
    def test_generate_config_report_function(self):
        """Test generate_config_report function"""
        report = generate_config_report()
        self.assertIn("Database Configuration Validation Report", report)

class TestConfigValidationWithEnvFile(unittest.TestCase):
    """Test cases for configuration validation with .env files"""
    
    def test_validate_with_env_file(self):
        """Test validation with custom .env file"""
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("DATABASE_URL=postgresql://testuser:testpass@localhost:5432/testdb\n")
            f.write("DB_POOL_SIZE=15\n")
            f.write("DATABASE_ECHO=false\n")
            env_file_path = f.name
        
        try:
            # Clear existing environment variables that might interfere
            with patch.dict(os.environ, {}, clear=True):
                validator = DatabaseConfigValidator(env_file_path)
                config = validator.validate_environment_config()
                
                self.assertEqual(config['DATABASE_URL'], 'postgresql://testuser:testpass@localhost:5432/testdb')
                self.assertEqual(config['DB_POOL_SIZE'], 15)
                self.assertFalse(config['DATABASE_ECHO'])
            
        finally:
            os.unlink(env_file_path)

def run_tests():
    """Run all configuration validation tests"""
    print("Running Database Configuration Validation Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseConfigValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigValidationFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigValidationWithEnvFile))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\nTest Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)