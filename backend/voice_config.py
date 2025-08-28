"""
Voice Feature Configuration for Different Deployment Environments
Provides environment-specific settings, feature toggles, and rate limiting
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import redis
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class DeploymentEnvironment(Enum):
    """Deployment environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class VoiceFeatureType(Enum):
    """Voice feature types for toggles"""
    VOICE_INPUT = "voice_input"
    VOICE_OUTPUT = "voice_output"
    VOICE_SETTINGS = "voice_settings"
    VOICE_ANALYTICS = "voice_analytics"
    ERROR_HANDLING = "error_handling"
    PERFORMANCE_TRACKING = "performance_tracking"
    A_B_TESTING = "ab_testing"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_limit: int = 10
    enabled: bool = True


@dataclass
class PerformanceConfig:
    """Performance monitoring configuration"""
    max_recording_duration: int = 30000  # milliseconds
    max_tts_text_length: int = 5000  # characters
    max_concurrent_sessions: int = 100
    memory_limit_mb: int = 50
    cache_ttl_seconds: int = 3600
    enable_compression: bool = True


@dataclass
class FeatureToggleConfig:
    """Feature toggle configuration"""
    enabled: bool = True
    rollout_percentage: float = 100.0  # 0-100
    user_groups: List[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    ab_test_variant: Optional[str] = None


@dataclass
class VoiceEnvironmentConfig:
    """Complete voice configuration for an environment"""
    environment: DeploymentEnvironment
    rate_limits: RateLimitConfig
    performance: PerformanceConfig
    feature_toggles: Dict[VoiceFeatureType, FeatureToggleConfig]
    debug_mode: bool = False
    analytics_enabled: bool = True
    error_reporting_enabled: bool = True
    fallback_mode_threshold: int = 3  # consecutive errors before fallback


class VoiceConfigManager:
    """Manages voice configuration across different environments"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.current_environment = self._detect_environment()
        self.config_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Load configuration
        self.config = self._load_environment_config()
        
        logger.info(f"VoiceConfigManager initialized for {self.current_environment.value} environment")

    def _detect_environment(self) -> DeploymentEnvironment:
        """Detect current deployment environment"""
        env_name = os.getenv('DEPLOYMENT_ENV', 'development').lower()
        
        try:
            return DeploymentEnvironment(env_name)
        except ValueError:
            logger.warning(f"Unknown environment '{env_name}', defaulting to development")
            return DeploymentEnvironment.DEVELOPMENT

    def _load_environment_config(self) -> VoiceEnvironmentConfig:
        """Load configuration for current environment"""
        config_file = f"voice_config_{self.current_environment.value}.json"
        config_path = os.path.join(os.path.dirname(__file__), 'config', config_file)
        
        # Try to load from file first
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                return self._parse_config_data(config_data)
            except Exception as e:
                logger.error(f"Failed to load config from {config_path}: {e}")
        
        # Fallback to default configuration
        return self._get_default_config()

    def _parse_config_data(self, config_data: Dict[str, Any]) -> VoiceEnvironmentConfig:
        """Parse configuration data from JSON"""
        try:
            # Parse rate limits
            rate_limits = RateLimitConfig(**config_data.get('rate_limits', {}))
            
            # Parse performance config
            performance = PerformanceConfig(**config_data.get('performance', {}))
            
            # Parse feature toggles
            feature_toggles = {}
            toggles_data = config_data.get('feature_toggles', {})
            
            for feature_name, toggle_data in toggles_data.items():
                try:
                    feature_type = VoiceFeatureType(feature_name)
                    
                    # Parse dates if present
                    if 'start_date' in toggle_data and toggle_data['start_date']:
                        toggle_data['start_date'] = datetime.fromisoformat(toggle_data['start_date'])
                    if 'end_date' in toggle_data and toggle_data['end_date']:
                        toggle_data['end_date'] = datetime.fromisoformat(toggle_data['end_date'])
                    
                    feature_toggles[feature_type] = FeatureToggleConfig(**toggle_data)
                except ValueError:
                    logger.warning(f"Unknown feature type: {feature_name}")
            
            return VoiceEnvironmentConfig(
                environment=self.current_environment,
                rate_limits=rate_limits,
                performance=performance,
                feature_toggles=feature_toggles,
                debug_mode=config_data.get('debug_mode', False),
                analytics_enabled=config_data.get('analytics_enabled', True),
                error_reporting_enabled=config_data.get('error_reporting_enabled', True),
                fallback_mode_threshold=config_data.get('fallback_mode_threshold', 3)
            )
            
        except Exception as e:
            logger.error(f"Failed to parse config data: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> VoiceEnvironmentConfig:
        """Get default configuration based on environment"""
        if self.current_environment == DeploymentEnvironment.PRODUCTION:
            return self._get_production_config()
        elif self.current_environment == DeploymentEnvironment.STAGING:
            return self._get_staging_config()
        elif self.current_environment == DeploymentEnvironment.TESTING:
            return self._get_testing_config()
        else:
            return self._get_development_config()

    def _get_production_config(self) -> VoiceEnvironmentConfig:
        """Production environment configuration"""
        return VoiceEnvironmentConfig(
            environment=DeploymentEnvironment.PRODUCTION,
            rate_limits=RateLimitConfig(
                requests_per_minute=30,
                requests_per_hour=500,
                requests_per_day=5000,
                burst_limit=5,
                enabled=True
            ),
            performance=PerformanceConfig(
                max_recording_duration=20000,
                max_tts_text_length=3000,
                max_concurrent_sessions=50,
                memory_limit_mb=30,
                cache_ttl_seconds=7200,
                enable_compression=True
            ),
            feature_toggles={
                VoiceFeatureType.VOICE_INPUT: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.VOICE_OUTPUT: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.VOICE_SETTINGS: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.VOICE_ANALYTICS: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.ERROR_HANDLING: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.PERFORMANCE_TRACKING: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.A_B_TESTING: FeatureToggleConfig(enabled=False, rollout_percentage=0.0)
            },
            debug_mode=False,
            analytics_enabled=True,
            error_reporting_enabled=True,
            fallback_mode_threshold=2
        )

    def _get_staging_config(self) -> VoiceEnvironmentConfig:
        """Staging environment configuration"""
        return VoiceEnvironmentConfig(
            environment=DeploymentEnvironment.STAGING,
            rate_limits=RateLimitConfig(
                requests_per_minute=60,
                requests_per_hour=1000,
                requests_per_day=10000,
                burst_limit=10,
                enabled=True
            ),
            performance=PerformanceConfig(
                max_recording_duration=30000,
                max_tts_text_length=5000,
                max_concurrent_sessions=100,
                memory_limit_mb=50,
                cache_ttl_seconds=3600,
                enable_compression=True
            ),
            feature_toggles={
                VoiceFeatureType.VOICE_INPUT: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.VOICE_OUTPUT: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.VOICE_SETTINGS: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.VOICE_ANALYTICS: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.ERROR_HANDLING: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.PERFORMANCE_TRACKING: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.A_B_TESTING: FeatureToggleConfig(enabled=True, rollout_percentage=50.0)
            },
            debug_mode=True,
            analytics_enabled=True,
            error_reporting_enabled=True,
            fallback_mode_threshold=3
        )

    def _get_development_config(self) -> VoiceEnvironmentConfig:
        """Development environment configuration"""
        return VoiceEnvironmentConfig(
            environment=DeploymentEnvironment.DEVELOPMENT,
            rate_limits=RateLimitConfig(
                requests_per_minute=120,
                requests_per_hour=2000,
                requests_per_day=20000,
                burst_limit=20,
                enabled=False  # Disabled for development
            ),
            performance=PerformanceConfig(
                max_recording_duration=60000,
                max_tts_text_length=10000,
                max_concurrent_sessions=200,
                memory_limit_mb=100,
                cache_ttl_seconds=1800,
                enable_compression=False
            ),
            feature_toggles={
                VoiceFeatureType.VOICE_INPUT: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.VOICE_OUTPUT: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.VOICE_SETTINGS: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.VOICE_ANALYTICS: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.ERROR_HANDLING: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.PERFORMANCE_TRACKING: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.A_B_TESTING: FeatureToggleConfig(enabled=True, rollout_percentage=100.0)
            },
            debug_mode=True,
            analytics_enabled=True,
            error_reporting_enabled=True,
            fallback_mode_threshold=5
        )

    def _get_testing_config(self) -> VoiceEnvironmentConfig:
        """Testing environment configuration"""
        return VoiceEnvironmentConfig(
            environment=DeploymentEnvironment.TESTING,
            rate_limits=RateLimitConfig(
                requests_per_minute=1000,
                requests_per_hour=10000,
                requests_per_day=100000,
                burst_limit=100,
                enabled=False  # Disabled for testing
            ),
            performance=PerformanceConfig(
                max_recording_duration=10000,
                max_tts_text_length=1000,
                max_concurrent_sessions=10,
                memory_limit_mb=20,
                cache_ttl_seconds=60,
                enable_compression=False
            ),
            feature_toggles={
                VoiceFeatureType.VOICE_INPUT: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.VOICE_OUTPUT: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.VOICE_SETTINGS: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.VOICE_ANALYTICS: FeatureToggleConfig(enabled=False, rollout_percentage=0.0),
                VoiceFeatureType.ERROR_HANDLING: FeatureToggleConfig(enabled=True, rollout_percentage=100.0),
                VoiceFeatureType.PERFORMANCE_TRACKING: FeatureToggleConfig(enabled=False, rollout_percentage=0.0),
                VoiceFeatureType.A_B_TESTING: FeatureToggleConfig(enabled=False, rollout_percentage=0.0)
            },
            debug_mode=True,
            analytics_enabled=False,
            error_reporting_enabled=False,
            fallback_mode_threshold=1
        )

    def is_feature_enabled(self, feature: VoiceFeatureType, user_id: str = None) -> bool:
        """Check if a feature is enabled for a user"""
        if feature not in self.config.feature_toggles:
            return False
        
        toggle = self.config.feature_toggles[feature]
        
        # Check if feature is globally disabled
        if not toggle.enabled:
            return False
        
        # Check date range
        now = datetime.utcnow()
        if toggle.start_date and now < toggle.start_date:
            return False
        if toggle.end_date and now > toggle.end_date:
            return False
        
        # Check rollout percentage
        if toggle.rollout_percentage < 100.0:
            if user_id:
                # Use consistent hash for user-based rollout
                import hashlib
                user_hash = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
                user_percentage = (user_hash % 100) + 1
                return user_percentage <= toggle.rollout_percentage
            else:
                # Random rollout for anonymous users
                import random
                return random.random() * 100 <= toggle.rollout_percentage
        
        return True

    def get_rate_limit_config(self) -> RateLimitConfig:
        """Get rate limiting configuration"""
        return self.config.rate_limits

    def get_performance_config(self) -> PerformanceConfig:
        """Get performance configuration"""
        return self.config.performance

    def get_feature_toggles(self, user_id: str = None) -> Dict[str, bool]:
        """Get all feature toggles for a user"""
        toggles = {}
        for feature_type in VoiceFeatureType:
            toggles[feature_type.value] = self.is_feature_enabled(feature_type, user_id)
        return toggles

    def update_feature_toggle(self, feature: VoiceFeatureType, config: FeatureToggleConfig) -> bool:
        """Update a feature toggle configuration"""
        try:
            self.config.feature_toggles[feature] = config
            
            # Update in Redis if available
            if self.redis_client:
                cache_key = f"voice_config:{self.current_environment.value}:toggles"
                toggles_data = {
                    feature_type.value: asdict(toggle_config)
                    for feature_type, toggle_config in self.config.feature_toggles.items()
                }
                self.redis_client.hset(cache_key, feature.value, json.dumps(asdict(config)))
                self.redis_client.expire(cache_key, self.cache_ttl)
            
            logger.info(f"Updated feature toggle {feature.value}: {config}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update feature toggle {feature.value}: {e}")
            return False

    def get_config_for_client(self, user_id: str = None) -> Dict[str, Any]:
        """Get configuration data for client-side use"""
        return {
            'environment': self.current_environment.value,
            'featureToggles': self.get_feature_toggles(user_id),
            'performance': {
                'maxRecordingDuration': self.config.performance.max_recording_duration,
                'maxTtsTextLength': self.config.performance.max_tts_text_length,
                'enableCompression': self.config.performance.enable_compression
            },
            'debugMode': self.config.debug_mode,
            'analyticsEnabled': self.config.analytics_enabled,
            'fallbackThreshold': self.config.fallback_mode_threshold
        }

    def validate_request_limits(self, user_id: str, request_type: str = 'general') -> bool:
        """Validate if request is within rate limits"""
        if not self.config.rate_limits.enabled:
            return True
        
        if not self.redis_client:
            # No Redis, allow all requests (fallback)
            return True
        
        try:
            now = datetime.utcnow()
            
            # Check different time windows
            windows = [
                ('minute', 60, self.config.rate_limits.requests_per_minute),
                ('hour', 3600, self.config.rate_limits.requests_per_hour),
                ('day', 86400, self.config.rate_limits.requests_per_day)
            ]
            
            for window_name, window_seconds, limit in windows:
                key = f"voice_rate_limit:{user_id}:{request_type}:{window_name}:{now.strftime('%Y%m%d%H%M' if window_name == 'minute' else '%Y%m%d%H' if window_name == 'hour' else '%Y%m%d')}"
                
                current_count = self.redis_client.get(key)
                current_count = int(current_count) if current_count else 0
                
                if current_count >= limit:
                    logger.warning(f"Rate limit exceeded for user {user_id}: {current_count}/{limit} per {window_name}")
                    return False
                
                # Increment counter
                pipe = self.redis_client.pipeline()
                pipe.incr(key)
                pipe.expire(key, window_seconds)
                pipe.execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check failed for user {user_id}: {e}")
            # Allow request on error (fail open)
            return True

    def get_ab_test_variant(self, user_id: str, test_name: str) -> Optional[str]:
        """Get A/B test variant for a user"""
        if not self.is_feature_enabled(VoiceFeatureType.A_B_TESTING, user_id):
            return None
        
        try:
            # Use consistent hash for user-based variant assignment
            import hashlib
            test_hash = hashlib.md5(f"{user_id}:{test_name}".encode()).hexdigest()
            variant_num = int(test_hash[:8], 16) % 2
            return 'A' if variant_num == 0 else 'B'
            
        except Exception as e:
            logger.error(f"Failed to get A/B test variant for {user_id}: {e}")
            return None

    def log_config_access(self, user_id: str, config_type: str):
        """Log configuration access for monitoring"""
        try:
            if self.redis_client and self.config.analytics_enabled:
                log_key = f"voice_config_access:{datetime.utcnow().strftime('%Y%m%d')}"
                log_data = {
                    'user_id': user_id,
                    'config_type': config_type,
                    'environment': self.current_environment.value,
                    'timestamp': datetime.utcnow().isoformat()
                }
                self.redis_client.lpush(log_key, json.dumps(log_data))
                self.redis_client.expire(log_key, 86400 * 7)  # Keep for 7 days
                
        except Exception as e:
            logger.error(f"Failed to log config access: {e}")

    def get_resource_usage_limits(self) -> Dict[str, Any]:
        """Get resource usage limits for monitoring"""
        return {
            'max_concurrent_sessions': self.config.performance.max_concurrent_sessions,
            'memory_limit_mb': self.config.performance.memory_limit_mb,
            'max_recording_duration': self.config.performance.max_recording_duration,
            'max_tts_text_length': self.config.performance.max_tts_text_length
        }


# Global config manager instance
_config_manager = None

def get_voice_config_manager(redis_client: Optional[redis.Redis] = None) -> VoiceConfigManager:
    """Get global voice configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = VoiceConfigManager(redis_client)
    return _config_manager