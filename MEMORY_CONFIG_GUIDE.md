# Memory Configuration Management Guide

This guide explains how to use the enhanced memory configuration system for the AI agent's memory layer.

## Overview

The memory configuration system provides comprehensive management of:
- Data retention policies and cleanup strategies
- Performance settings and resource limits
- Security and privacy configurations
- Quality thresholds and scoring weights
- Storage limits and cleanup triggers

## Key Components

### 1. MemoryConfig Class

The main configuration class that holds all memory-related settings:

```python
from memory_config import MemoryConfig

# Create default configuration
config = MemoryConfig()

# Validate configuration
if config.is_valid():
    print("Configuration is valid")
else:
    errors = config.validate()
    print(f"Validation errors: {errors}")
```

### 2. ConfigurationManager Class

Manages configuration loading, validation, and updates:

```python
from memory_config import ConfigurationManager

# Create manager and load configuration
manager = ConfigurationManager("path/to/config.json")
config = manager.load_configuration()

# Update configuration
updates = {
    "retention": {
        "conversation_retention_days": 120
    }
}
manager.update_configuration(updates, save=True)
```

### 3. PolicyManager Class

Handles cleanup policies and retention strategies:

```python
from memory_config import PolicyManager

policy_manager = PolicyManager(config)

# Check if cleanup is needed
cleanup_info = policy_manager.get_cleanup_candidates("conversations", 900)
if cleanup_info["should_cleanup"]:
    print(f"Need to remove {cleanup_info['items_to_remove']} items")
```

## Configuration Structure

### Retention Policy

Controls data retention and cleanup behavior:

```json
{
  "retention": {
    "conversation_retention_days": 90,
    "context_cache_retention_hours": 24,
    "tool_metrics_retention_days": 365,
    "summary_retention_days": 730,
    "cleanup_interval_hours": 6,
    "auto_cleanup_enabled": true,
    "emergency_cleanup_threshold": 0.95,
    "storage_limits": {
      "max_conversations_per_user": 10000,
      "max_context_cache_entries": 50000,
      "max_tool_metrics_entries": 100000,
      "max_total_storage_mb": 1024,
      "max_conversation_length": 50000,
      "max_context_size_kb": 100
    },
    "cleanup_policy": {
      "strategy": "oldest_first",
      "trigger_threshold": 0.8,
      "target_threshold": 0.6,
      "batch_size": 100,
      "max_cleanup_time_seconds": 300,
      "preserve_recent_days": 7,
      "preserve_high_quality": true
    }
  }
}
```

### Performance Configuration

Controls system performance and resource usage:

```json
{
  "performance": {
    "max_context_entries": 50,
    "max_conversation_history": 100,
    "cache_size_mb": 256,
    "query_timeout_seconds": 30,
    "batch_size": 100,
    "enable_caching": true,
    "connection_pool_size": 10,
    "max_concurrent_operations": 50,
    "cache_ttl_seconds": 3600,
    "enable_query_optimization": true,
    "enable_background_cleanup": true,
    "cleanup_worker_threads": 2,
    "memory_usage_check_interval": 300
  }
}
```

### Security Configuration

Controls security and privacy settings:

```json
{
  "security": {
    "encrypt_sensitive_data": true,
    "enable_data_anonymization": true,
    "require_user_consent": true,
    "audit_data_access": true,
    "max_failed_attempts": 3
  }
}
```

### Quality Configuration

Controls response quality thresholds and scoring:

```json
{
  "quality": {
    "min_relevance_score": 0.3,
    "context_similarity_threshold": 0.7,
    "tool_success_threshold": 0.8,
    "response_quality_weights": {
      "relevance": 0.4,
      "completeness": 0.3,
      "accuracy": 0.3
    }
  }
}
```

## Cleanup Strategies

The system supports four cleanup strategies:

### 1. Oldest First (`oldest_first`)
Removes the oldest conversations first. Good for general cleanup.

### 2. Least Accessed (`least_accessed`)
Removes conversations that haven't been accessed recently. Preserves frequently used data.

### 3. Lowest Quality (`lowest_quality`)
Removes conversations with the lowest quality scores first. Preserves high-quality interactions.

### 4. Size Based (`size_based`)
Removes the largest conversations first. Good for freeing up storage space quickly.

## Environment Variable Overrides

You can override configuration settings using environment variables:

```bash
export MEMORY_CONVERSATION_RETENTION_DAYS=120
export MEMORY_CACHE_SIZE_MB=512
export MEMORY_ENCRYPT_SENSITIVE_DATA=true
```

The system will automatically apply these overrides when loading configuration.

## Usage Examples

### Basic Configuration Loading

```python
from memory_config import load_config

# Load configuration from default locations
config = load_config()

# Load from specific file
config = load_config("custom_config.json")
```

### Policy Management

```python
from memory_config import ConfigurationManager

manager = ConfigurationManager()
config = manager.load_configuration()
policy_manager = manager.get_policy_manager()

# Check cleanup requirements
current_count = 1500
cleanup_info = policy_manager.get_cleanup_candidates("conversations", current_count)

if cleanup_info["should_cleanup"]:
    # Get cleanup parameters
    filter_params = policy_manager.create_cleanup_filter(
        "conversations", 
        cleanup_info["strategy"]
    )
    
    # Estimate impact
    impact = policy_manager.estimate_cleanup_impact(
        "conversations",
        cleanup_info["items_to_remove"]
    )
    
    print(f"Will remove {impact['items_to_remove']} items")
    print(f"Estimated time: {impact['estimated_time_seconds']} seconds")
```

### Configuration Updates

```python
manager = ConfigurationManager()
manager.load_configuration()

# Update retention settings
updates = {
    "retention": {
        "conversation_retention_days": 180,
        "cleanup_policy": {
            "strategy": "least_accessed",
            "trigger_threshold": 0.85
        }
    }
}

success = manager.update_configuration(updates, save=True)
if success:
    print("Configuration updated successfully")
```

## Validation Rules

The system validates configuration settings:

1. **Positive Values**: Retention days, cache sizes, and limits must be positive
2. **Threshold Ranges**: Thresholds must be between 0.0 and 1.0
3. **Threshold Logic**: Trigger threshold must be greater than target threshold
4. **Quality Weights**: Must sum to 1.0 and include required keys
5. **Required Fields**: All essential configuration fields must be present

## Error Handling

The system provides graceful error handling:

- Invalid configurations fall back to defaults with warnings
- Missing configuration files use default settings
- Environment variable parsing errors are logged but don't break the system
- Validation errors are collected and reported comprehensively

## Best Practices

1. **Start with Defaults**: Use default configuration as a baseline
2. **Validate Changes**: Always validate configuration after updates
3. **Monitor Usage**: Use configuration summary to monitor settings
4. **Test Cleanup**: Test cleanup policies with small datasets first
5. **Backup Configs**: Keep backups of working configurations
6. **Use Environment Overrides**: Use environment variables for deployment-specific settings

## Configuration Files

- `config/memory_config_example.json`: Example configuration file
- `memory_config_usage_example.py`: Usage examples and demonstrations
- `test_memory_config.py`: Comprehensive test suite

## Integration with Memory Layer

The configuration system integrates with other memory layer components:

- **Memory Layer Manager**: Uses configuration for operational settings
- **Context Retrieval Engine**: Uses quality and performance settings
- **Conversation History Store**: Uses retention and storage settings
- **Tool Usage Analytics**: Uses quality and performance thresholds

This configuration system ensures that the memory layer operates efficiently while maintaining data quality and respecting storage constraints.