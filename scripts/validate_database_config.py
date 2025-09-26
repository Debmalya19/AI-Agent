#!/usr/bin/env python3
"""
Database Configuration Validation Script

This script validates the database configuration and tests connectivity.
It can be used to verify that the environment is properly configured
before starting the application.
"""

import sys
import os
import argparse
from pathlib import Path

# Add the parent directory to the path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config_validation import (
    DatabaseConfigValidator,
    ConfigValidationError,
    generate_config_report
)

def main():
    """Main function for configuration validation"""
    parser = argparse.ArgumentParser(
        description="Validate database configuration and test connectivity"
    )
    parser.add_argument(
        "--env-file",
        type=str,
        help="Path to .env file (default: .env in current directory)"
    )
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test database connection"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize validator
        validator = DatabaseConfigValidator(args.env_file)
        
        if args.format == "json":
            import json
            
            # JSON output
            result = {
                "validation_status": "unknown",
                "configuration": {},
                "connection_test": {}
            }
            
            try:
                # Validate configuration
                config = validator.validate_environment_config()
                db_params = validator.get_database_connection_params()
                
                result["validation_status"] = "success"
                result["configuration"] = {
                    "database_type": db_params["database_type"],
                    "url_masked": db_params["url"].split("@")[1] if "@" in db_params["url"] else db_params["url"],
                    "parameters": {k: v for k, v in db_params.items() if k not in ["url", "password"]}
                }
                
                # Test connection if requested
                if args.test_connection:
                    is_healthy, health_msg = validator.validate_connection_health(db_params["url"])
                    result["connection_test"] = {
                        "status": "success" if is_healthy else "failed",
                        "message": health_msg
                    }
                
            except ConfigValidationError as e:
                result["validation_status"] = "failed"
                result["error"] = str(e)
            
            print(json.dumps(result, indent=2))
            
        else:
            # Text output
            print("Database Configuration Validation")
            print("=" * 50)
            
            try:
                # Generate comprehensive report
                report = validator.generate_config_report()
                print(report)
                
                if args.test_connection:
                    print("\nConnection Test")
                    print("-" * 20)
                    
                    config = validator.validate_environment_config()
                    is_healthy, health_msg = validator.validate_connection_health(config["DATABASE_URL"])
                    
                    if is_healthy:
                        print(f"✓ {health_msg}")
                    else:
                        print(f"✗ {health_msg}")
                        sys.exit(1)
                
                if args.verbose:
                    print("\nDetailed Configuration")
                    print("-" * 25)
                    
                    config = validator.validate_environment_config()
                    db_params = validator.get_database_connection_params()
                    
                    for key, value in config.items():
                        if "password" not in key.lower():
                            print(f"{key}: {value}")
                
            except ConfigValidationError as e:
                print(f"✗ Configuration validation failed:")
                print(f"  {e}")
                sys.exit(1)
            except Exception as e:
                print(f"✗ Unexpected error: {e}")
                sys.exit(1)
        
        print("\n✓ Configuration validation completed successfully")
        
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()