"""
Memory layer configuration management.
Handles configuration settings, policies, and validation for the memory system.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from datetime import timedelta, datetime
from enum import Enum
import json
import os
import logging
from pathlib import Path


class CleanupStrategy(Enum):
    """Available cleanup strategies"""
    OLDEST_FIRST = "oldest_first"
    LEAST_ACCESSED = "least_accessed"
    LOWEST_QUALITY = "lowest_quality"
    SIZE_BASED = "size_based"


class StorageLimit(Enum):
    """Storage limit types"""
    COUNT = "count"
    SIZE_MB = "size_mb"
    AGE_DAYS = "age_days"


@dataclass
class CleanupPolicy:
    """Configuration for data cleanup policies"""
    strategy: CleanupStrategy = CleanupStrategy.OLDEST_FIRST
    trigger_threshold: float = 0.8  # Trigger cleanup at 80% of limit
    target_threshold: float = 0.6   # Clean down to 60% of limit
    batch_size: int = 100
    max_cleanup_time_seconds: int = 300
    preserve_recent_days: int = 7   # Always preserve data from last N days
    preserve_high_quality: bool = True  # Preserve high-quality conversations


@dataclass
class StorageLimits:
    """Configuration for storage limits"""
    max_conversations_per_user: int = 10000
    max_context_cache_entries: int = 50000
    max_tool_metrics_entries: int = 100000
    max_total_storage_mb: int = 1024
    max_conversation_length: int = 50000  # characters
    max_context_size_kb: int = 100


@dataclass
class RetentionPolicy:
    """Configuration for data retention policies"""
    conversation_retention_days: int = 90
    context_cache_retention_hours: int = 24
    tool_metrics_retention_days: int = 365
    summary_retention_days: int = 730
    cleanup_interval_hours: int = 6
    
    # Enhanced retention settings
    auto_cleanup_enabled: bool = True
    emergency_cleanup_threshold: float = 0.95  # Emergency cleanup at 95% capacity
    storage_limits: StorageLimits = field(default_factory=StorageLimits)
    cleanup_policy: CleanupPolicy = field(default_factory=CleanupPolicy)


@dataclass
class PerformanceConfig:
    """Configuration for performance settings"""
    max_context_entries: int = 50
    max_conversation_history: int = 100
    cache_size_mb: int = 256
    query_timeout_seconds: int = 30
    batch_size: int = 100
    enable_caching: bool = True
    
    # Enhanced performance settings
    connection_pool_size: int = 10
    max_concurrent_operations: int = 50
    cache_ttl_seconds: int = 3600
    enable_query_optimization: bool = True
    enable_background_cleanup: bool = True
    cleanup_worker_threads: int = 2
    memory_usage_check_interval: int = 300  # seconds
    
    # Intelligent chat orchestrator priority settings
    prioritize_intelligent_chat: bool = True
    intelligent_chat_cache_size: int = 100
    intelligent_chat_priority_weight: float = 0.9
    context_retrieval_max_results: int = 5


@dataclass
class SecurityConfig:
    """Configuration for security and privacy settings"""
    encrypt_sensitive_data: bool = True
    enable_data_anonymization: bool = True
    require_user_consent: bool = True
    audit_data_access: bool = True
    max_failed_attempts: int = 3


@dataclass
class QualityConfig:
    """Configuration for response quality and scoring"""
    min_relevance_score: float = 0.3
    context_similarity_threshold: float = 0.7
    tool_success_threshold: float = 0.8
    response_quality_weights: Dict[str, float] = field(default_factory=lambda: {
        'relevance': 0.4,
        'completeness': 0.3,
        'accuracy': 0.3
    })


@dataclass
class MemoryConfig:
    """Main configuration class for the memory layer"""
    retention: RetentionPolicy = field(default_factory=RetentionPolicy)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    
    # Database configuration
    enable_database_storage: bool = True
    enable_cache_storage: bool = True
    
    # Feature flags
    enable_context_retrieval: bool = True
    enable_tool_analytics: bool = True
    enable_conversation_summaries: bool = True
    enable_health_monitoring: bool = True
    
    # Logging configuration
    log_level: str = "INFO"
    log_memory_operations: bool = True
    log_performance_metrics: bool = True

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MemoryConfig':
        """Create MemoryConfig from dictionary"""
        config = cls()
        
        # Update retention policy
        if 'retention' in config_dict:
            retention_dict = config_dict['retention'].copy()
            
            # Handle storage limits
            if 'storage_limits' in retention_dict:
                storage_limits_dict = retention_dict.pop('storage_limits')
                retention_dict['storage_limits'] = StorageLimits(**storage_limits_dict)
            
            # Handle cleanup policy
            if 'cleanup_policy' in retention_dict:
                cleanup_dict = retention_dict.pop('cleanup_policy')
                # Convert strategy string back to enum
                if 'strategy' in cleanup_dict:
                    cleanup_dict['strategy'] = CleanupStrategy(cleanup_dict['strategy'])
                retention_dict['cleanup_policy'] = CleanupPolicy(**cleanup_dict)
            
            config.retention = RetentionPolicy(**retention_dict)
        
        # Update performance config
        if 'performance' in config_dict:
            performance_dict = config_dict['performance']
            config.performance = PerformanceConfig(**performance_dict)
        
        # Update security config
        if 'security' in config_dict:
            security_dict = config_dict['security']
            config.security = SecurityConfig(**security_dict)
        
        # Update quality config
        if 'quality' in config_dict:
            quality_dict = config_dict['quality']
            config.quality = QualityConfig(**quality_dict)
        
        # Update other fields
        for key, value in config_dict.items():
            if key not in ['retention', 'performance', 'security', 'quality']:
                if hasattr(config, key):
                    setattr(config, key, value)
        
        return config

    @classmethod
    def from_file(cls, config_path: str) -> 'MemoryConfig':
        """Load configuration from JSON file"""
        if not os.path.exists(config_path):
            return cls()  # Return default config if file doesn't exist
        
        try:
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
            return cls.from_dict(config_dict)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            return cls()  # Return default config on error

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'retention': {
                'conversation_retention_days': self.retention.conversation_retention_days,
                'context_cache_retention_hours': self.retention.context_cache_retention_hours,
                'tool_metrics_retention_days': self.retention.tool_metrics_retention_days,
                'summary_retention_days': self.retention.summary_retention_days,
                'cleanup_interval_hours': self.retention.cleanup_interval_hours,
                'auto_cleanup_enabled': self.retention.auto_cleanup_enabled,
                'emergency_cleanup_threshold': self.retention.emergency_cleanup_threshold,
                'storage_limits': {
                    'max_conversations_per_user': self.retention.storage_limits.max_conversations_per_user,
                    'max_context_cache_entries': self.retention.storage_limits.max_context_cache_entries,
                    'max_tool_metrics_entries': self.retention.storage_limits.max_tool_metrics_entries,
                    'max_total_storage_mb': self.retention.storage_limits.max_total_storage_mb,
                    'max_conversation_length': self.retention.storage_limits.max_conversation_length,
                    'max_context_size_kb': self.retention.storage_limits.max_context_size_kb
                },
                'cleanup_policy': {
                    'strategy': self.retention.cleanup_policy.strategy.value,
                    'trigger_threshold': self.retention.cleanup_policy.trigger_threshold,
                    'target_threshold': self.retention.cleanup_policy.target_threshold,
                    'batch_size': self.retention.cleanup_policy.batch_size,
                    'max_cleanup_time_seconds': self.retention.cleanup_policy.max_cleanup_time_seconds,
                    'preserve_recent_days': self.retention.cleanup_policy.preserve_recent_days,
                    'preserve_high_quality': self.retention.cleanup_policy.preserve_high_quality
                }
            },
            'performance': {
                'max_context_entries': self.performance.max_context_entries,
                'max_conversation_history': self.performance.max_conversation_history,
                'cache_size_mb': self.performance.cache_size_mb,
                'query_timeout_seconds': self.performance.query_timeout_seconds,
                'batch_size': self.performance.batch_size,
                'enable_caching': self.performance.enable_caching,
                'connection_pool_size': self.performance.connection_pool_size,
                'max_concurrent_operations': self.performance.max_concurrent_operations,
                'cache_ttl_seconds': self.performance.cache_ttl_seconds,
                'enable_query_optimization': self.performance.enable_query_optimization,
                'enable_background_cleanup': self.performance.enable_background_cleanup,
                'cleanup_worker_threads': self.performance.cleanup_worker_threads,
                'memory_usage_check_interval': self.performance.memory_usage_check_interval,
                'prioritize_intelligent_chat': self.performance.prioritize_intelligent_chat,
                'intelligent_chat_cache_size': self.performance.intelligent_chat_cache_size,
                'intelligent_chat_priority_weight': self.performance.intelligent_chat_priority_weight,
                'context_retrieval_max_results': self.performance.context_retrieval_max_results
            },
            'security': {
                'encrypt_sensitive_data': self.security.encrypt_sensitive_data,
                'enable_data_anonymization': self.security.enable_data_anonymization,
                'require_user_consent': self.security.require_user_consent,
                'audit_data_access': self.security.audit_data_access,
                'max_failed_attempts': self.security.max_failed_attempts
            },
            'quality': {
                'min_relevance_score': self.quality.min_relevance_score,
                'context_similarity_threshold': self.quality.context_similarity_threshold,
                'tool_success_threshold': self.quality.tool_success_threshold,
                'response_quality_weights': self.quality.response_quality_weights
            },
            'enable_database_storage': self.enable_database_storage,
            'enable_cache_storage': self.enable_cache_storage,
            'enable_context_retrieval': self.enable_context_retrieval,
            'enable_tool_analytics': self.enable_tool_analytics,
            'enable_conversation_summaries': self.enable_conversation_summaries,
            'enable_health_monitoring': self.enable_health_monitoring,
            'log_level': self.log_level,
            'log_memory_operations': self.log_memory_operations,
            'log_performance_metrics': self.log_performance_metrics
        }

    def save_to_file(self, config_path: str) -> bool:
        """Save configuration to JSON file"""
        try:
            # Create directory if it doesn't exist
            Path(config_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error: Failed to save config to {config_path}: {e}")
            return False

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate retention policy
        if self.retention.conversation_retention_days <= 0:
            errors.append("conversation_retention_days must be positive")
        if self.retention.context_cache_retention_hours <= 0:
            errors.append("context_cache_retention_hours must be positive")
        if self.retention.tool_metrics_retention_days <= 0:
            errors.append("tool_metrics_retention_days must be positive")
        if self.retention.cleanup_interval_hours <= 0:
            errors.append("cleanup_interval_hours must be positive")
        
        # Validate storage limits
        if self.retention.storage_limits.max_conversations_per_user <= 0:
            errors.append("max_conversations_per_user must be positive")
        if self.retention.storage_limits.max_total_storage_mb <= 0:
            errors.append("max_total_storage_mb must be positive")
        if self.retention.storage_limits.max_conversation_length <= 0:
            errors.append("max_conversation_length must be positive")
        
        # Validate cleanup policy
        if not (0.0 <= self.retention.cleanup_policy.trigger_threshold <= 1.0):
            errors.append("cleanup trigger_threshold must be between 0.0 and 1.0")
        if not (0.0 <= self.retention.cleanup_policy.target_threshold <= 1.0):
            errors.append("cleanup target_threshold must be between 0.0 and 1.0")
        if self.retention.cleanup_policy.trigger_threshold <= self.retention.cleanup_policy.target_threshold:
            errors.append("cleanup trigger_threshold must be greater than target_threshold")
        if self.retention.cleanup_policy.batch_size <= 0:
            errors.append("cleanup batch_size must be positive")
        
        # Validate performance config
        if self.performance.max_context_entries <= 0:
            errors.append("max_context_entries must be positive")
        if self.performance.max_conversation_history <= 0:
            errors.append("max_conversation_history must be positive")
        if self.performance.cache_size_mb <= 0:
            errors.append("cache_size_mb must be positive")
        if self.performance.query_timeout_seconds <= 0:
            errors.append("query_timeout_seconds must be positive")
        if self.performance.connection_pool_size <= 0:
            errors.append("connection_pool_size must be positive")
        if self.performance.max_concurrent_operations <= 0:
            errors.append("max_concurrent_operations must be positive")
        
        # Validate security config
        if self.security.max_failed_attempts <= 0:
            errors.append("max_failed_attempts must be positive")
        
        # Validate quality config
        if not (0.0 <= self.quality.min_relevance_score <= 1.0):
            errors.append("min_relevance_score must be between 0.0 and 1.0")
        if not (0.0 <= self.quality.context_similarity_threshold <= 1.0):
            errors.append("context_similarity_threshold must be between 0.0 and 1.0")
        if not (0.0 <= self.quality.tool_success_threshold <= 1.0):
            errors.append("tool_success_threshold must be between 0.0 and 1.0")
        
        # Validate quality weights sum to 1.0
        weights_sum = sum(self.quality.response_quality_weights.values())
        if abs(weights_sum - 1.0) > 0.01:
            errors.append("response_quality_weights must sum to 1.0")
        
        # Validate required quality weight keys
        required_weights = {'relevance', 'completeness', 'accuracy'}
        if not required_weights.issubset(self.quality.response_quality_weights.keys()):
            errors.append("response_quality_weights must include 'relevance', 'completeness', and 'accuracy'")
        
        return errors

    def is_valid(self) -> bool:
        """Check if configuration is valid"""
        return len(self.validate()) == 0
    
    def get_cleanup_strategy(self) -> CleanupStrategy:
        """Get the configured cleanup strategy"""
        return self.retention.cleanup_policy.strategy
    
    def should_trigger_cleanup(self, current_usage: float) -> bool:
        """Check if cleanup should be triggered based on current usage"""
        return current_usage >= self.retention.cleanup_policy.trigger_threshold
    
    def should_trigger_emergency_cleanup(self, current_usage: float) -> bool:
        """Check if emergency cleanup should be triggered"""
        return current_usage >= self.retention.emergency_cleanup_threshold
    
    def get_cleanup_target_usage(self) -> float:
        """Get the target usage level after cleanup"""
        return self.retention.cleanup_policy.target_threshold
    
    def get_retention_cutoff_date(self, data_type: str) -> datetime:
        """Get the cutoff date for data retention based on type"""
        now = datetime.now()
        
        if data_type == "conversations":
            return now - timedelta(days=self.retention.conversation_retention_days)
        elif data_type == "context_cache":
            return now - timedelta(hours=self.retention.context_cache_retention_hours)
        elif data_type == "tool_metrics":
            return now - timedelta(days=self.retention.tool_metrics_retention_days)
        elif data_type == "summaries":
            return now - timedelta(days=self.retention.summary_retention_days)
        else:
            raise ValueError(f"Unknown data type: {data_type}")
    
    def get_preserve_cutoff_date(self) -> datetime:
        """Get the cutoff date for data that should always be preserved"""
        return datetime.now() - timedelta(days=self.retention.cleanup_policy.preserve_recent_days)
    
    def apply_environment_overrides(self, env_prefix: str = "MEMORY_") -> None:
        """Apply configuration overrides from environment variables"""
        # Retention overrides
        if os.getenv(f"{env_prefix}CONVERSATION_RETENTION_DAYS"):
            self.retention.conversation_retention_days = int(os.getenv(f"{env_prefix}CONVERSATION_RETENTION_DAYS"))
        if os.getenv(f"{env_prefix}CONTEXT_CACHE_RETENTION_HOURS"):
            self.retention.context_cache_retention_hours = int(os.getenv(f"{env_prefix}CONTEXT_CACHE_RETENTION_HOURS"))
        
        # Performance overrides
        if os.getenv(f"{env_prefix}MAX_CONTEXT_ENTRIES"):
            self.performance.max_context_entries = int(os.getenv(f"{env_prefix}MAX_CONTEXT_ENTRIES"))
        if os.getenv(f"{env_prefix}CACHE_SIZE_MB"):
            self.performance.cache_size_mb = int(os.getenv(f"{env_prefix}CACHE_SIZE_MB"))
        
        # Security overrides
        if os.getenv(f"{env_prefix}ENCRYPT_SENSITIVE_DATA"):
            self.security.encrypt_sensitive_data = os.getenv(f"{env_prefix}ENCRYPT_SENSITIVE_DATA").lower() == "true"
        
        # Feature flag overrides
        if os.getenv(f"{env_prefix}ENABLE_DATABASE_STORAGE"):
            self.enable_database_storage = os.getenv(f"{env_prefix}ENABLE_DATABASE_STORAGE").lower() == "true"
        if os.getenv(f"{env_prefix}ENABLE_CACHE_STORAGE"):
            self.enable_cache_storage = os.getenv(f"{env_prefix}ENABLE_CACHE_STORAGE").lower() == "true"


# Default configuration paths
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "memory_config.json")
USER_CONFIG_PATH = os.path.expanduser("~/.ai_agent/memory_config.json")


def load_config(config_path: Optional[str] = None) -> MemoryConfig:
    """Load memory configuration from file or use defaults"""
    if config_path:
        return MemoryConfig.from_file(config_path)
    
    # Try user config first, then default config, then defaults
    for path in [USER_CONFIG_PATH, DEFAULT_CONFIG_PATH]:
        if os.path.exists(path):
            return MemoryConfig.from_file(path)
    
    return MemoryConfig()  # Return default configuration


def save_default_config(config_path: Optional[str] = None) -> bool:
    """Save default configuration to file"""
    config = MemoryConfig()
    path = config_path or DEFAULT_CONFIG_PATH
    return config.save_to_file(path)


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors"""
    pass


class PolicyManager:
    """Manages memory policies and cleanup strategies"""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def validate_configuration(self) -> bool:
        """Validate configuration and log any errors"""
        errors = self.config.validate()
        if errors:
            for error in errors:
                self.logger.error(f"Configuration validation error: {error}")
            return False
        return True
    
    def get_cleanup_candidates(self, data_type: str, current_count: int) -> Dict[str, Any]:
        """Get cleanup parameters for a specific data type"""
        storage_limits = self.config.retention.storage_limits
        cleanup_policy = self.config.retention.cleanup_policy
        
        # Determine max count based on data type
        if data_type == "conversations":
            max_count = storage_limits.max_conversations_per_user
        elif data_type == "context_cache":
            max_count = storage_limits.max_context_cache_entries
        elif data_type == "tool_metrics":
            max_count = storage_limits.max_tool_metrics_entries
        else:
            raise ValueError(f"Unknown data type: {data_type}")
        
        # Calculate cleanup parameters
        trigger_count = int(max_count * cleanup_policy.trigger_threshold)
        target_count = int(max_count * cleanup_policy.target_threshold)
        
        should_cleanup = current_count >= trigger_count
        items_to_remove = max(0, current_count - target_count) if should_cleanup else 0
        
        return {
            "should_cleanup": should_cleanup,
            "items_to_remove": items_to_remove,
            "batch_size": cleanup_policy.batch_size,
            "strategy": cleanup_policy.strategy,
            "preserve_cutoff": self.config.get_preserve_cutoff_date(),
            "retention_cutoff": self.config.get_retention_cutoff_date(data_type),
            "preserve_high_quality": cleanup_policy.preserve_high_quality
        }
    
    def create_cleanup_filter(self, data_type: str, strategy: CleanupStrategy) -> Dict[str, Any]:
        """Create filter parameters for cleanup based on strategy"""
        base_filter = {
            "preserve_after": self.config.get_preserve_cutoff_date(),
            "delete_before": self.config.get_retention_cutoff_date(data_type)
        }
        
        if strategy == CleanupStrategy.OLDEST_FIRST:
            base_filter["order_by"] = "created_at ASC"
        elif strategy == CleanupStrategy.LEAST_ACCESSED:
            base_filter["order_by"] = "last_accessed ASC"
        elif strategy == CleanupStrategy.LOWEST_QUALITY:
            base_filter["order_by"] = "response_quality_score ASC"
            base_filter["exclude_high_quality"] = self.config.retention.cleanup_policy.preserve_high_quality
        elif strategy == CleanupStrategy.SIZE_BASED:
            base_filter["order_by"] = "LENGTH(user_message) + LENGTH(bot_response) DESC"
        
        return base_filter
    
    def estimate_cleanup_impact(self, data_type: str, items_to_remove: int) -> Dict[str, Any]:
        """Estimate the impact of cleanup operation"""
        # This would typically query the database to get actual statistics
        # For now, return estimated values
        estimated_size_mb = items_to_remove * 0.01  # Rough estimate
        estimated_time_seconds = items_to_remove / 100  # Rough estimate
        
        return {
            "items_to_remove": items_to_remove,
            "estimated_size_mb": estimated_size_mb,
            "estimated_time_seconds": estimated_time_seconds,
            "data_type": data_type,
            "strategy": self.config.get_cleanup_strategy().value
        }


class ConfigurationManager:
    """Manages memory configuration loading, validation, and updates"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config: Optional[MemoryConfig] = None
        self.policy_manager: Optional[PolicyManager] = None
        self.logger = logging.getLogger(__name__)
    
    def load_configuration(self, validate: bool = True) -> MemoryConfig:
        """Load and validate configuration"""
        try:
            self.config = load_config(self.config_path)
            
            # Apply environment overrides
            self.config.apply_environment_overrides()
            
            # Validate configuration
            if validate:
                if not self.config.is_valid():
                    errors = self.config.validate()
                    self.logger.warning(f"Configuration validation failed: {errors}")
                    self.logger.warning("Using default configuration")
                    self.config = MemoryConfig()
            
            self.policy_manager = PolicyManager(self.config)
            self.logger.info("Memory configuration loaded successfully")
            
            return self.config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.logger.info("Using default configuration")
            self.config = MemoryConfig()
            self.policy_manager = PolicyManager(self.config)
            return self.config
    
    def reload_configuration(self) -> bool:
        """Reload configuration from file"""
        try:
            old_config = self.config
            self.load_configuration()
            self.logger.info("Configuration reloaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")
            return False
    
    def update_configuration(self, updates: Dict[str, Any], save: bool = True) -> bool:
        """Update configuration with new values"""
        try:
            if not self.config:
                self.load_configuration()
            
            # Create updated config
            config_dict = self.config.to_dict()
            config_dict.update(updates)
            
            new_config = MemoryConfig.from_dict(config_dict)
            
            # Validate new configuration
            if not new_config.is_valid():
                errors = new_config.validate()
                raise ConfigurationError(f"Invalid configuration updates: {errors}")
            
            self.config = new_config
            self.policy_manager = PolicyManager(self.config)
            
            # Save to file if requested
            if save and self.config_path:
                self.config.save_to_file(self.config_path)
            
            self.logger.info("Configuration updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
            return False
    
    def get_policy_manager(self) -> PolicyManager:
        """Get the policy manager instance"""
        if not self.policy_manager:
            if not self.config:
                self.load_configuration()
            self.policy_manager = PolicyManager(self.config)
        return self.policy_manager
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        if not self.config:
            self.load_configuration()
        
        return {
            "retention_days": self.config.retention.conversation_retention_days,
            "cache_size_mb": self.config.performance.cache_size_mb,
            "max_context_entries": self.config.performance.max_context_entries,
            "cleanup_enabled": self.config.retention.auto_cleanup_enabled,
            "cleanup_strategy": self.config.get_cleanup_strategy().value,
            "security_enabled": self.config.security.encrypt_sensitive_data,
            "database_enabled": self.config.enable_database_storage,
            "cache_enabled": self.config.enable_cache_storage,
            "is_valid": self.config.is_valid()
        }