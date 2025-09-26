#!/usr/bin/env python3
"""
Schema Optimization Validation Script

This script validates that PostgreSQL schema optimizations have been properly implemented
by checking model definitions, data types, and optimization features.

Requirements: 3.1, 3.2, 3.3, 3.4
"""

import os
import sys
import logging
import inspect
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON, Enum, Boolean
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID, ARRAY

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import unified_models, models, memory_models
from backend.database import DATABASE_URL

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SchemaOptimizationValidator:
    """Validates PostgreSQL schema optimizations"""
    
    def __init__(self):
        self.validation_results = {
            "postgresql_data_types": [],
            "jsonb_columns": [],
            "timestamp_columns": [],
            "model_optimizations": [],
            "issues": []
        }
    
    def validate_model_data_types(self, model_class, model_name):
        """Validate data types used in a model"""
        logger.info(f"Validating model: {model_name}")
        
        jsonb_columns = []
        timestamp_columns = []
        issues = []
        
        # Get all columns from the model
        if hasattr(model_class, '__table__'):
            for column in model_class.__table__.columns:
                column_name = column.name
                column_type = str(column.type)
                
                # Check for JSONB usage
                if 'JSONB' in column_type:
                    jsonb_columns.append(f"{model_name}.{column_name}")
                elif 'JSON' in column_type and not 'JSONB' in column_type:
                    issues.append(f"{model_name}.{column_name} uses JSON instead of JSONB")
                
                # Check for TIMESTAMP WITH TIME ZONE usage
                if 'TIMESTAMP' in column_type and 'timezone=True' in column_type:
                    timestamp_columns.append(f"{model_name}.{column_name}")
                elif 'DateTime' in column_type or ('TIMESTAMP' in column_type and 'timezone=True' not in column_type):
                    if column_name in ['created_at', 'updated_at', 'expires_at', 'last_accessed', 'resolved_at', 'ended_at', 'last_login']:
                        issues.append(f"{model_name}.{column_name} should use TIMESTAMP WITH TIME ZONE")
        
        return {
            "jsonb_columns": jsonb_columns,
            "timestamp_columns": timestamp_columns,
            "issues": issues
        }
    
    def validate_all_models(self):
        """Validate all model classes"""
        logger.info("Validating all model classes for PostgreSQL optimizations...")
        
        # Models to validate
        model_modules = [
            (unified_models, "unified_models"),
            (models, "models"),
            (memory_models, "memory_models")
        ]
        
        for module, module_name in model_modules:
            logger.info(f"Checking module: {module_name}")
            
            # Get all classes from the module
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and hasattr(obj, '__table__'):
                    try:
                        result = self.validate_model_data_types(obj, f"{module_name}.{name}")
                        
                        self.validation_results["jsonb_columns"].extend(result["jsonb_columns"])
                        self.validation_results["timestamp_columns"].extend(result["timestamp_columns"])
                        self.validation_results["issues"].extend(result["issues"])
                        
                        if result["jsonb_columns"] or result["timestamp_columns"]:
                            self.validation_results["model_optimizations"].append({
                                "model": f"{module_name}.{name}",
                                "jsonb_columns": len(result["jsonb_columns"]),
                                "timestamp_columns": len(result["timestamp_columns"])
                            })
                    
                    except Exception as e:
                        logger.warning(f"Could not validate model {module_name}.{name}: {e}")
    
    def check_postgresql_imports(self):
        """Check if PostgreSQL-specific imports are present"""
        logger.info("Checking PostgreSQL-specific imports...")
        
        modules_to_check = [unified_models, models, memory_models]
        
        for module in modules_to_check:
            module_source = inspect.getsource(module)
            
            if 'from sqlalchemy.dialects.postgresql import' in module_source:
                self.validation_results["postgresql_data_types"].append(f"{module.__name__} has PostgreSQL imports")
                
                # Check for specific imports
                if 'JSONB' in module_source:
                    self.validation_results["postgresql_data_types"].append(f"{module.__name__} imports JSONB")
                if 'TIMESTAMP' in module_source:
                    self.validation_results["postgresql_data_types"].append(f"{module.__name__} imports TIMESTAMP")
                if 'UUID' in module_source:
                    self.validation_results["postgresql_data_types"].append(f"{module.__name__} imports UUID")
                if 'ARRAY' in module_source:
                    self.validation_results["postgresql_data_types"].append(f"{module.__name__} imports ARRAY")
            else:
                self.validation_results["issues"].append(f"{module.__name__} missing PostgreSQL imports")
    
    def validate_optimization_script_exists(self):
        """Check if optimization scripts exist"""
        logger.info("Checking for optimization scripts...")
        
        script_files = [
            "scripts/optimize_postgresql_schema.py",
            "test_postgresql_schema_optimization.py",
            "POSTGRESQL_SCHEMA_OPTIMIZATION.md"
        ]
        
        for script_file in script_files:
            if os.path.exists(script_file):
                self.validation_results["model_optimizations"].append(f"Found: {script_file}")
            else:
                self.validation_results["issues"].append(f"Missing: {script_file}")
    
    def generate_validation_report(self):
        """Generate a comprehensive validation report"""
        logger.info("Generating validation report...")
        
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_url": DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else DATABASE_URL,
            "summary": {
                "total_jsonb_columns": len(self.validation_results["jsonb_columns"]),
                "total_timestamp_columns": len(self.validation_results["timestamp_columns"]),
                "optimized_models": len(self.validation_results["model_optimizations"]),
                "total_issues": len(self.validation_results["issues"])
            },
            "details": self.validation_results
        }
        
        return report
    
    def print_validation_summary(self):
        """Print a summary of validation results"""
        print("\n" + "="*80)
        print("POSTGRESQL SCHEMA OPTIMIZATION VALIDATION SUMMARY")
        print("="*80)
        
        print(f"\nDatabase URL: {DATABASE_URL}")
        
        print(f"\n📊 OPTIMIZATION STATISTICS:")
        print(f"   • JSONB Columns: {len(self.validation_results['jsonb_columns'])}")
        print(f"   • Timestamp Columns: {len(self.validation_results['timestamp_columns'])}")
        print(f"   • Optimized Models: {len(self.validation_results['model_optimizations'])}")
        print(f"   • Issues Found: {len(self.validation_results['issues'])}")
        
        if self.validation_results["postgresql_data_types"]:
            print(f"\n✅ POSTGRESQL IMPORTS:")
            for item in self.validation_results["postgresql_data_types"]:
                print(f"   • {item}")
        
        if self.validation_results["jsonb_columns"]:
            print(f"\n📋 JSONB COLUMNS ({len(self.validation_results['jsonb_columns'])}):")
            for column in self.validation_results["jsonb_columns"][:10]:  # Show first 10
                print(f"   • {column}")
            if len(self.validation_results["jsonb_columns"]) > 10:
                print(f"   • ... and {len(self.validation_results['jsonb_columns']) - 10} more")
        
        if self.validation_results["timestamp_columns"]:
            print(f"\n🕐 TIMESTAMP WITH TIMEZONE COLUMNS ({len(self.validation_results['timestamp_columns'])}):")
            for column in self.validation_results["timestamp_columns"][:10]:  # Show first 10
                print(f"   • {column}")
            if len(self.validation_results["timestamp_columns"]) > 10:
                print(f"   • ... and {len(self.validation_results['timestamp_columns']) - 10} more")
        
        if self.validation_results["issues"]:
            print(f"\n⚠️  ISSUES FOUND ({len(self.validation_results['issues'])}):")
            for issue in self.validation_results["issues"]:
                print(f"   • {issue}")
        
        print(f"\n🎯 OPTIMIZATION STATUS:")
        if len(self.validation_results["issues"]) == 0:
            print("   ✅ All PostgreSQL optimizations are properly implemented!")
        elif len(self.validation_results["issues"]) <= 3:
            print("   ⚠️  Minor issues found - optimizations mostly complete")
        else:
            print("   ❌ Multiple issues found - optimizations need attention")
        
        print("\n" + "="*80)

def main():
    """Main validation function"""
    logger.info("Starting PostgreSQL schema optimization validation...")
    
    try:
        validator = SchemaOptimizationValidator()
        
        # Run all validations
        validator.check_postgresql_imports()
        validator.validate_all_models()
        validator.validate_optimization_script_exists()
        
        # Generate and display report
        report = validator.generate_validation_report()
        validator.print_validation_summary()
        
        # Save detailed report
        import json
        report_file = f"schema_optimization_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Detailed validation report saved to: {report_file}")
        
        # Return success/failure based on issues
        if len(validator.validation_results["issues"]) == 0:
            logger.info("✅ All PostgreSQL schema optimizations validated successfully!")
            return 0
        else:
            logger.warning(f"⚠️  Found {len(validator.validation_results['issues'])} issues")
            return 1
            
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)