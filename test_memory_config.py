"""
Unit tests for memory configuration management.
Tests configuration loading, validation, policy management, and cleanup strategies.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from memory_config import (
    MemoryConfig, RetentionPolicy, PerformanceConfig, SecurityConfig, QualityConfig,
    StorageLimits, CleanupPolicy, CleanupStrategy, PolicyManager, ConfigurationManager,
    ConfigurationError, load_config, save_default_config
)


class TestMemoryConfig:
    """Test MemoryConfig class functionality"""
    
    def test_default_config_creation(self):
        """Test creating default configuration"""
        config = MemoryConfig()
        
        assert config.retention.conversation_retention_days == 90
        assert config.performance.max_context_entries == 50
        assert config.security.encrypt_sensitive_data is True
        assert config.quality.min_relevance_score == 0.3
        assert config.enable_database_storage is True
    
    def test_config_validation_success(self):
        """Test successful configuration validation"""
        config = MemoryConfig()
        
        errors = config.validate()
        assert len(errors) == 0
        assert config.is_valid() is True
    
    def test_config_validation_failures(self):
        """Test configuration validation with invalid values"""
        config = MemoryConfig()
        
        # Set invalid values
        config.retention.conversation_retention_days = -1
        config.performance.max_context_entries = 0
        config.quality.min_relevance_score = 1.5
        config.retention.cleanup_policy.trigger_threshold = 0.5
        config.retention.cleanup_policy.target_threshold = 0.8  # Should be less than trigger
        
        errors = config.validate()
        assert len(errors) > 0
        assert config.is_valid() is False
        
        # Check specific error messages
        error_messages = " ".join(errors)
        assert "conversation_retention_days must be positive" in error_messages
        assert "max_context_entries must be positive" in error_messages
        assert "min_relevance_score must be between 0.0 and 1.0" in error_messages
        assert "trigger_threshold must be greater than target_threshold" in error_messages
    
    def test_quality_weights_validation(self):
        """Test validation of quality weights"""
        config = MemoryConfig()
        
        # Test weights that don't sum to 1.0
        config.quality.response_quality_weights = {
            'relevance': 0.5,
            'completeness': 0.3,
            'accuracy': 0.1  # Sum = 0.9
        }
        
        errors = config.validate()
        assert any("response_quality_weights must sum to 1.0" in error for error in errors)
        
        # Test missing required weights
        config.quality.response_quality_weights = {
            'relevance': 0.5,
            'other': 0.5
        }
        
        errors = config.validate()
        assert any("must include 'relevance', 'completeness', and 'accuracy'" in error for error in errors)
    
    def test_cleanup_strategy_methods(self):
        """Test cleanup strategy helper methods"""
        config = MemoryConfig()
        
        assert config.get_cleanup_strategy() == CleanupStrategy.OLDEST_FIRST
        assert config.should_trigger_cleanup(0.9) is True
        assert config.should_trigger_cleanup(0.7) is False
        assert config.should_trigger_emergency_cleanup(0.96) is True
        assert config.get_cleanup_target_usage() == 0.6
    
    def test_retention_cutoff_dates(self):
        """Test retention cutoff date calculations"""
        config = MemoryConfig()
        now = datetime.now()
        
        # Test conversation cutoff
        cutoff = config.get_retention_cutoff_date("conversations")
        expected = now - timedelta(days=90)
        assert abs((cutoff - expected).total_seconds()) < 60  # Within 1 minute
        
        # Test context cache cutoff
        cutoff = config.get_retention_cutoff_date("context_cache")
        expected = now - timedelta(hours=24)
        assert abs((cutoff - expected).total_seconds()) < 60
        
        # Test invalid data type
        with pytest.raises(ValueError):
            config.get_retention_cutoff_date("invalid_type")
    
    def test_environment_overrides(self):
        """Test environment variable overrides"""
        config = MemoryConfig()
        original_retention = config.retention.conversation_retention_days
        
        with patch.dict(os.environ, {'MEMORY_CONVERSATION_RETENTION_DAYS': '120'}):
            config.apply_environment_overrides()
            assert config.retention.conversation_retention_days == 120
        
        # Test boolean override
        with patch.dict(os.environ, {'MEMORY_ENCRYPT_SENSITIVE_DATA': 'false'}):
            config.apply_environment_overrides()
            assert config.security.encrypt_sensitive_data is False
    
    def test_config_serialization(self):
        """Test configuration to/from dictionary conversion"""
        config = MemoryConfig()
        config.retention.conversation_retention_days = 120
        config.performance.cache_size_mb = 512
        
        # Test to_dict
        config_dict = config.to_dict()
        assert config_dict['retention']['conversation_retention_days'] == 120
        assert config_dict['performance']['cache_size_mb'] == 512
        assert 'storage_limits' in config_dict['retention']
        assert 'cleanup_policy' in config_dict['retention']
        
        # Test from_dict
        new_config = MemoryConfig.from_dict(config_dict)
        assert new_config.retention.conversation_retention_days == 120
        assert new_config.performance.cache_size_mb == 512
        assert isinstance(new_config.retention.cleanup_policy.strategy, CleanupStrategy)
    
    def test_config_file_operations(self):
        """Test saving and loading configuration files"""
        config = MemoryConfig()
        config.retention.conversation_retention_days = 150
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Test saving
            assert config.save_to_file(temp_path) is True
            
            # Test loading
            loaded_config = MemoryConfig.from_file(temp_path)
            assert loaded_config.retention.conversation_retention_days == 150
            
            # Test loading non-existent file
            non_existent_config = MemoryConfig.from_file("non_existent.json")
            assert non_existent_config.retention.conversation_retention_days == 90  # Default
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestPolicyManager:
    """Test PolicyManager class functionality"""
    
    def test_policy_manager_creation(self):
        """Test creating policy manager"""
        config = MemoryConfig()
        manager = PolicyManager(config)
        
        assert manager.config == config
        assert manager.logger is not None
    
    def test_configuration_validation(self):
        """Test configuration validation through policy manager"""
        config = MemoryConfig()
        manager = PolicyManager(config)
        
        # Valid configuration
        assert manager.validate_configuration() is True
        
        # Invalid configuration
        config.retention.conversation_retention_days = -1
        assert manager.validate_configuration() is False
    
    def test_cleanup_candidates_calculation(self):
        """Test cleanup candidates calculation"""
        config = MemoryConfig()
        config.retention.storage_limits.max_conversations_per_user = 1000
        config.retention.cleanup_policy.trigger_threshold = 0.8
        config.retention.cleanup_policy.target_threshold = 0.6
        
        manager = PolicyManager(config)
        
        # Test when cleanup is needed
        candidates = manager.get_cleanup_candidates("conversations", 900)
        assert candidates["should_cleanup"] is True
        assert candidates["items_to_remove"] == 300  # 900 - (1000 * 0.6)
        assert candidates["strategy"] == CleanupStrategy.OLDEST_FIRST
        
        # Test when cleanup is not needed
        candidates = manager.get_cleanup_candidates("conversations", 500)
        assert candidates["should_cleanup"] is False
        assert candidates["items_to_remove"] == 0
    
    def test_cleanup_filter_creation(self):
        """Test cleanup filter creation for different strategies"""
        config = MemoryConfig()
        manager = PolicyManager(config)
        
        # Test oldest first strategy
        filter_params = manager.create_cleanup_filter("conversations", CleanupStrategy.OLDEST_FIRST)
        assert filter_params["order_by"] == "created_at ASC"
        assert "preserve_after" in filter_params
        assert "delete_before" in filter_params
        
        # Test least accessed strategy
        filter_params = manager.create_cleanup_filter("conversations", CleanupStrategy.LEAST_ACCESSED)
        assert filter_params["order_by"] == "last_accessed ASC"
        
        # Test lowest quality strategy
        filter_params = manager.create_cleanup_filter("conversations", CleanupStrategy.LOWEST_QUALITY)
        assert filter_params["order_by"] == "response_quality_score ASC"
        assert "exclude_high_quality" in filter_params
        
        # Test size based strategy
        filter_params = manager.create_cleanup_filter("conversations", CleanupStrategy.SIZE_BASED)
        assert "LENGTH" in filter_params["order_by"]
    
    def test_cleanup_impact_estimation(self):
        """Test cleanup impact estimation"""
        config = MemoryConfig()
        manager = PolicyManager(config)
        
        impact = manager.estimate_cleanup_impact("conversations", 100)
        
        assert impact["items_to_remove"] == 100
        assert impact["estimated_size_mb"] > 0
        assert impact["estimated_time_seconds"] > 0
        assert impact["data_type"] == "conversations"
        assert impact["strategy"] == CleanupStrategy.OLDEST_FIRST.value


class TestConfigurationManager:
    """Test ConfigurationManager class functionality"""
    
    def test_configuration_manager_creation(self):
        """Test creating configuration manager"""
        manager = ConfigurationManager()
        
        assert manager.config is None
        assert manager.policy_manager is None
        assert manager.logger is not None
    
    def test_load_configuration_success(self):
        """Test successful configuration loading"""
        manager = ConfigurationManager()
        
        config = manager.load_configuration()
        
        assert config is not None
        assert manager.config == config
        assert manager.policy_manager is not None
        assert config.is_valid()
    
    def test_load_configuration_with_file(self):
        """Test loading configuration from file"""
        # Create temporary config file
        config_data = {
            "retention": {
                "conversation_retention_days": 200
            },
            "performance": {
                "cache_size_mb": 1024
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            manager = ConfigurationManager(temp_path)
            config = manager.load_configuration()
            
            assert config.retention.conversation_retention_days == 200
            assert config.performance.cache_size_mb == 1024
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_configuration_update(self):
        """Test configuration updates"""
        manager = ConfigurationManager()
        manager.load_configuration()
        
        updates = {
            "retention": {
                "conversation_retention_days": 180
            }
        }
        
        success = manager.update_configuration(updates, save=False)
        assert success is True
        assert manager.config.retention.conversation_retention_days == 180
    
    def test_configuration_update_validation_failure(self):
        """Test configuration update with validation failure"""
        manager = ConfigurationManager()
        manager.load_configuration()
        
        # Invalid update
        updates = {
            "retention": {
                "conversation_retention_days": -1
            }
        }
        
        success = manager.update_configuration(updates, save=False)
        assert success is False
    
    def test_configuration_reload(self):
        """Test configuration reload"""
        manager = ConfigurationManager()
        manager.load_configuration()
        
        # Mock successful reload
        with patch.object(manager, 'load_configuration') as mock_load:
            mock_load.return_value = MemoryConfig()
            success = manager.reload_configuration()
            assert success is True
            mock_load.assert_called_once()
    
    def test_get_policy_manager(self):
        """Test getting policy manager"""
        manager = ConfigurationManager()
        
        # Should load configuration if not already loaded
        policy_manager = manager.get_policy_manager()
        assert policy_manager is not None
        assert manager.config is not None
    
    def test_configuration_summary(self):
        """Test getting configuration summary"""
        manager = ConfigurationManager()
        
        summary = manager.get_configuration_summary()
        
        assert "retention_days" in summary
        assert "cache_size_mb" in summary
        assert "max_context_entries" in summary
        assert "cleanup_enabled" in summary
        assert "cleanup_strategy" in summary
        assert "security_enabled" in summary
        assert "database_enabled" in summary
        assert "cache_enabled" in summary
        assert "is_valid" in summary


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_load_config_function(self):
        """Test load_config utility function"""
        config = load_config()
        assert isinstance(config, MemoryConfig)
        assert config.is_valid()
    
    def test_save_default_config_function(self):
        """Test save_default_config utility function"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            success = save_default_config(temp_path)
            assert success is True
            assert os.path.exists(temp_path)
            
            # Verify the saved config can be loaded
            config = MemoryConfig.from_file(temp_path)
            assert config.is_valid()
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestCleanupPolicyAndStorageLimits:
    """Test CleanupPolicy and StorageLimits classes"""
    
    def test_cleanup_policy_defaults(self):
        """Test CleanupPolicy default values"""
        policy = CleanupPolicy()
        
        assert policy.strategy == CleanupStrategy.OLDEST_FIRST
        assert policy.trigger_threshold == 0.8
        assert policy.target_threshold == 0.6
        assert policy.batch_size == 100
        assert policy.preserve_recent_days == 7
        assert policy.preserve_high_quality is True
    
    def test_storage_limits_defaults(self):
        """Test StorageLimits default values"""
        limits = StorageLimits()
        
        assert limits.max_conversations_per_user == 10000
        assert limits.max_context_cache_entries == 50000
        assert limits.max_tool_metrics_entries == 100000
        assert limits.max_total_storage_mb == 1024
        assert limits.max_conversation_length == 50000
        assert limits.max_context_size_kb == 100
    
    def test_cleanup_strategy_enum(self):
        """Test CleanupStrategy enum values"""
        assert CleanupStrategy.OLDEST_FIRST.value == "oldest_first"
        assert CleanupStrategy.LEAST_ACCESSED.value == "least_accessed"
        assert CleanupStrategy.LOWEST_QUALITY.value == "lowest_quality"
        assert CleanupStrategy.SIZE_BASED.value == "size_based"


if __name__ == "__main__":
    pytest.main([__file__])