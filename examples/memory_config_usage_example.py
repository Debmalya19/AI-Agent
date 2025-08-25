"""
Example usage of the enhanced memory configuration system.
Demonstrates configuration loading, validation, policy management, and cleanup strategies.
"""

import logging
from datetime import datetime
from memory_config import (
    MemoryConfig, ConfigurationManager, PolicyManager, CleanupStrategy,
    load_config, save_default_config
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demonstrate_basic_configuration():
    """Demonstrate basic configuration operations"""
    print("=== Basic Configuration Operations ===")
    
    # Create default configuration
    config = MemoryConfig()
    print(f"Default retention days: {config.retention.conversation_retention_days}")
    print(f"Default cache size: {config.performance.cache_size_mb} MB")
    print(f"Configuration is valid: {config.is_valid()}")
    
    # Validate configuration
    errors = config.validate()
    if errors:
        print(f"Validation errors: {errors}")
    else:
        print("Configuration validation passed")
    
    print()


def demonstrate_configuration_manager():
    """Demonstrate configuration manager usage"""
    print("=== Configuration Manager Usage ===")
    
    # Create configuration manager
    manager = ConfigurationManager()
    
    # Load configuration
    config = manager.load_configuration()
    print(f"Loaded configuration with retention: {config.retention.conversation_retention_days} days")
    
    # Get configuration summary
    summary = manager.get_configuration_summary()
    print("Configuration Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Update configuration
    updates = {
        "retention": {
            "conversation_retention_days": 120
        },
        "performance": {
            "cache_size_mb": 512
        }
    }
    
    success = manager.update_configuration(updates, save=False)
    print(f"Configuration update successful: {success}")
    print(f"New retention days: {manager.config.retention.conversation_retention_days}")
    
    print()


def demonstrate_policy_management():
    """Demonstrate policy management and cleanup strategies"""
    print("=== Policy Management and Cleanup Strategies ===")
    
    # Create configuration with custom cleanup policy
    config = MemoryConfig()
    config.retention.storage_limits.max_conversations_per_user = 1000
    config.retention.cleanup_policy.strategy = CleanupStrategy.OLDEST_FIRST
    config.retention.cleanup_policy.trigger_threshold = 0.8
    config.retention.cleanup_policy.target_threshold = 0.6
    
    # Create policy manager
    policy_manager = PolicyManager(config)
    
    # Check if cleanup is needed
    current_count = 900  # Simulate 900 conversations
    cleanup_info = policy_manager.get_cleanup_candidates("conversations", current_count)
    
    print(f"Current conversation count: {current_count}")
    print(f"Should cleanup: {cleanup_info['should_cleanup']}")
    print(f"Items to remove: {cleanup_info['items_to_remove']}")
    print(f"Cleanup strategy: {cleanup_info['strategy'].value}")
    
    # Get cleanup filter parameters
    if cleanup_info['should_cleanup']:
        filter_params = policy_manager.create_cleanup_filter(
            "conversations", 
            cleanup_info['strategy']
        )
        print("Cleanup filter parameters:")
        for key, value in filter_params.items():
            print(f"  {key}: {value}")
        
        # Estimate cleanup impact
        impact = policy_manager.estimate_cleanup_impact(
            "conversations", 
            cleanup_info['items_to_remove']
        )
        print("Estimated cleanup impact:")
        print(f"  Items to remove: {impact['items_to_remove']}")
        print(f"  Estimated size: {impact['estimated_size_mb']:.2f} MB")
        print(f"  Estimated time: {impact['estimated_time_seconds']:.1f} seconds")
    
    print()


def demonstrate_cleanup_strategies():
    """Demonstrate different cleanup strategies"""
    print("=== Cleanup Strategies Comparison ===")
    
    config = MemoryConfig()
    policy_manager = PolicyManager(config)
    
    strategies = [
        CleanupStrategy.OLDEST_FIRST,
        CleanupStrategy.LEAST_ACCESSED,
        CleanupStrategy.LOWEST_QUALITY,
        CleanupStrategy.SIZE_BASED
    ]
    
    for strategy in strategies:
        filter_params = policy_manager.create_cleanup_filter("conversations", strategy)
        print(f"Strategy: {strategy.value}")
        print(f"  Order by: {filter_params.get('order_by', 'N/A')}")
        print(f"  Special handling: {filter_params.get('exclude_high_quality', 'None')}")
    
    print()


def demonstrate_retention_policies():
    """Demonstrate retention policy calculations"""
    print("=== Retention Policy Calculations ===")
    
    config = MemoryConfig()
    
    # Show retention cutoff dates for different data types
    data_types = ["conversations", "context_cache", "tool_metrics", "summaries"]
    
    for data_type in data_types:
        cutoff_date = config.get_retention_cutoff_date(data_type)
        print(f"{data_type.replace('_', ' ').title()}: Delete before {cutoff_date.strftime('%Y-%m-%d %H:%M')}")
    
    # Show preserve cutoff date
    preserve_date = config.get_preserve_cutoff_date()
    print(f"Always preserve data after: {preserve_date.strftime('%Y-%m-%d %H:%M')}")
    
    # Show cleanup thresholds
    print(f"Cleanup trigger threshold: {config.retention.cleanup_policy.trigger_threshold * 100}%")
    print(f"Cleanup target threshold: {config.retention.cleanup_policy.target_threshold * 100}%")
    print(f"Emergency cleanup threshold: {config.retention.emergency_cleanup_threshold * 100}%")
    
    print()


def demonstrate_environment_overrides():
    """Demonstrate environment variable overrides"""
    print("=== Environment Variable Overrides ===")
    
    import os
    
    # Set some environment variables
    os.environ['MEMORY_CONVERSATION_RETENTION_DAYS'] = '150'
    os.environ['MEMORY_CACHE_SIZE_MB'] = '1024'
    os.environ['MEMORY_ENCRYPT_SENSITIVE_DATA'] = 'false'
    
    config = MemoryConfig()
    print("Before environment overrides:")
    print(f"  Retention days: {config.retention.conversation_retention_days}")
    print(f"  Cache size: {config.performance.cache_size_mb} MB")
    print(f"  Encryption enabled: {config.security.encrypt_sensitive_data}")
    
    # Apply environment overrides
    config.apply_environment_overrides()
    
    print("After environment overrides:")
    print(f"  Retention days: {config.retention.conversation_retention_days}")
    print(f"  Cache size: {config.performance.cache_size_mb} MB")
    print(f"  Encryption enabled: {config.security.encrypt_sensitive_data}")
    
    # Clean up environment variables
    for key in ['MEMORY_CONVERSATION_RETENTION_DAYS', 'MEMORY_CACHE_SIZE_MB', 'MEMORY_ENCRYPT_SENSITIVE_DATA']:
        if key in os.environ:
            del os.environ[key]
    
    print()


def demonstrate_configuration_validation():
    """Demonstrate configuration validation with various scenarios"""
    print("=== Configuration Validation Scenarios ===")
    
    # Valid configuration
    config = MemoryConfig()
    errors = config.validate()
    print(f"Valid configuration errors: {len(errors)}")
    
    # Invalid retention days
    config.retention.conversation_retention_days = -1
    errors = config.validate()
    print(f"Invalid retention days errors: {len(errors)}")
    print(f"  First error: {errors[0] if errors else 'None'}")
    
    # Reset and test invalid quality weights
    config = MemoryConfig()
    config.quality.response_quality_weights = {'relevance': 0.5, 'completeness': 0.3}  # Missing accuracy, doesn't sum to 1.0
    errors = config.validate()
    print(f"Invalid quality weights errors: {len(errors)}")
    for error in errors:
        if 'quality' in error.lower():
            print(f"  Quality error: {error}")
    
    # Reset and test invalid cleanup thresholds
    config = MemoryConfig()
    config.retention.cleanup_policy.trigger_threshold = 0.5
    config.retention.cleanup_policy.target_threshold = 0.8  # Should be less than trigger
    errors = config.validate()
    print(f"Invalid cleanup thresholds errors: {len(errors)}")
    for error in errors:
        if 'threshold' in error.lower():
            print(f"  Threshold error: {error}")
    
    print()


def main():
    """Run all demonstration functions"""
    print("Memory Configuration System Demonstration")
    print("=" * 50)
    print()
    
    demonstrate_basic_configuration()
    demonstrate_configuration_manager()
    demonstrate_policy_management()
    demonstrate_cleanup_strategies()
    demonstrate_retention_policies()
    demonstrate_environment_overrides()
    demonstrate_configuration_validation()
    
    print("Demonstration completed successfully!")


if __name__ == "__main__":
    main()