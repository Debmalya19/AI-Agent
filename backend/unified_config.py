"""
Unified Configuration System

This module provides a centralized configuration system that manages settings for both
the AI Agent backend and admin dashboard components.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import secrets

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Deployment environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Create database config from environment variables"""
        return cls(
            url=os.getenv("DATABASE_URL", "postgresql://localhost/ai_agent"),
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
            echo=os.getenv("DB_ECHO", "false").lower() == "true"
        )


@dataclass
class AuthConfig:
    """Authentication configuration settings"""
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    session_timeout_hours: int = 24
    password_min_length: int = 8
    require_email_verification: bool = False
    
    @classmethod
    def from_env(cls) -> 'AuthConfig':
        """Create auth config from environment variables"""
        secret_key = os.getenv("JWT_SECRET_KEY")
        if not secret_key:
            secret_key = secrets.token_urlsafe(32)
            logger.warning("JWT_SECRET_KEY not set, generated random key (not suitable for production)")
        
        return cls(
            jwt_secret_key=secret_key,
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_expiration_hours=int(os.getenv("JWT_EXPIRATION_HOURS", "24")),
            session_timeout_hours=int(os.getenv("SESSION_TIMEOUT_HOURS", "24")),
            password_min_length=int(os.getenv("PASSWORD_MIN_LENGTH", "8")),
            require_email_verification=os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").lower() == "true"
        )


@dataclass
class AIAgentConfig:
    """AI Agent specific configuration"""
    google_api_key: Optional[str] = None
    model_name: str = "gemini-2.0-flash"
    temperature: float = 0.3
    max_tokens: Optional[int] = None
    memory_cleanup_interval_hours: int = 24
    memory_retention_days: int = 30
    
    @classmethod
    def from_env(cls) -> 'AIAgentConfig':
        """Create AI agent config from environment variables"""
        return cls(
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            model_name=os.getenv("AI_MODEL_NAME", "gemini-2.0-flash"),
            temperature=float(os.getenv("AI_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("AI_MAX_TOKENS")) if os.getenv("AI_MAX_TOKENS") else None,
            memory_cleanup_interval_hours=int(os.getenv("MEMORY_CLEANUP_INTERVAL_HOURS", "24")),
            memory_retention_days=int(os.getenv("MEMORY_RETENTION_DAYS", "30"))
        )


@dataclass
class AdminDashboardConfig:
    """Admin dashboard specific configuration"""
    enabled: bool = True
    frontend_path: str = "admin-dashboard/frontend"
    api_prefix: str = "/api/admin"
    require_admin_role: bool = True
    session_timeout_minutes: int = 60
    
    @classmethod
    def from_env(cls) -> 'AdminDashboardConfig':
        """Create admin dashboard config from environment variables"""
        return cls(
            enabled=os.getenv("ADMIN_DASHBOARD_ENABLED", "true").lower() == "true",
            frontend_path=os.getenv("ADMIN_FRONTEND_PATH", "admin-dashboard/frontend"),
            api_prefix=os.getenv("ADMIN_API_PREFIX", "/api/admin"),
            require_admin_role=os.getenv("ADMIN_REQUIRE_ROLE", "true").lower() == "true",
            session_timeout_minutes=int(os.getenv("ADMIN_SESSION_TIMEOUT_MINUTES", "60"))
        )


@dataclass
class DataSyncConfig:
    """Data synchronization configuration"""
    enabled: bool = True
    sync_interval_seconds: int = 30
    batch_size: int = 100
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    
    @classmethod
    def from_env(cls) -> 'DataSyncConfig':
        """Create data sync config from environment variables"""
        return cls(
            enabled=os.getenv("DATA_SYNC_ENABLED", "true").lower() == "true",
            sync_interval_seconds=int(os.getenv("DATA_SYNC_INTERVAL_SECONDS", "30")),
            batch_size=int(os.getenv("DATA_SYNC_BATCH_SIZE", "100")),
            retry_attempts=int(os.getenv("DATA_SYNC_RETRY_ATTEMPTS", "3")),
            retry_delay_seconds=int(os.getenv("DATA_SYNC_RETRY_DELAY_SECONDS", "5"))
        )


@dataclass
class VoiceConfig:
    """Voice assistant configuration"""
    enabled: bool = True
    max_recording_duration_ms: int = 30000
    max_tts_text_length: int = 5000
    rate_limit_per_minute: int = 60
    
    @classmethod
    def from_env(cls) -> 'VoiceConfig':
        """Create voice config from environment variables"""
        return cls(
            enabled=os.getenv("VOICE_ENABLED", "true").lower() == "true",
            max_recording_duration_ms=int(os.getenv("VOICE_MAX_RECORDING_MS", "30000")),
            max_tts_text_length=int(os.getenv("VOICE_MAX_TTS_LENGTH", "5000")),
            rate_limit_per_minute=int(os.getenv("VOICE_RATE_LIMIT_PER_MINUTE", "60"))
        )


@dataclass
class AnalyticsConfig:
    """Analytics configuration"""
    enabled: bool = True
    retention_days: int = 90
    batch_processing: bool = True
    real_time_updates: bool = True
    
    @classmethod
    def from_env(cls) -> 'AnalyticsConfig':
        """Create analytics config from environment variables"""
        return cls(
            enabled=os.getenv("ANALYTICS_ENABLED", "true").lower() == "true",
            retention_days=int(os.getenv("ANALYTICS_RETENTION_DAYS", "90")),
            batch_processing=os.getenv("ANALYTICS_BATCH_PROCESSING", "true").lower() == "true",
            real_time_updates=os.getenv("ANALYTICS_REAL_TIME_UPDATES", "true").lower() == "true"
        )


@dataclass
class ErrorHandlingConfig:
    """Error handling and monitoring configuration"""
    log_level: str = "INFO"
    log_file: Optional[str] = None
    error_reporting_enabled: bool = True
    retry_attempts: int = 3
    circuit_breaker_enabled: bool = True
    
    @classmethod
    def from_env(cls) -> 'ErrorHandlingConfig':
        """Create error handling config from environment variables"""
        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_file=os.getenv("LOG_FILE"),
            error_reporting_enabled=os.getenv("ERROR_REPORTING_ENABLED", "true").lower() == "true",
            retry_attempts=int(os.getenv("ERROR_RETRY_ATTEMPTS", "3")),
            circuit_breaker_enabled=os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"
        )


@dataclass
class ServerConfig:
    """Server configuration settings"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    workers: int = 1
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    
    @classmethod
    def from_env(cls) -> 'ServerConfig':
        """Create server config from environment variables"""
        cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
        return cls(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            reload=os.getenv("RELOAD", "false").lower() == "true",
            workers=int(os.getenv("WORKERS", "1")),
            cors_origins=cors_origins
        )


@dataclass
class UnifiedConfig:
    """Unified configuration for the entire application"""
    environment: Environment
    database: DatabaseConfig
    auth: AuthConfig
    ai_agent: AIAgentConfig
    admin_dashboard: AdminDashboardConfig
    data_sync: DataSyncConfig
    voice: VoiceConfig
    analytics: AnalyticsConfig
    error_handling: ErrorHandlingConfig
    server: ServerConfig
    
    @classmethod
    def from_env(cls) -> 'UnifiedConfig':
        """Create unified config from environment variables"""
        env_name = os.getenv("ENVIRONMENT", "development").lower()
        try:
            environment = Environment(env_name)
        except ValueError:
            logger.warning(f"Unknown environment '{env_name}', defaulting to development")
            environment = Environment.DEVELOPMENT
        
        return cls(
            environment=environment,
            database=DatabaseConfig.from_env(),
            auth=AuthConfig.from_env(),
            ai_agent=AIAgentConfig.from_env(),
            admin_dashboard=AdminDashboardConfig.from_env(),
            data_sync=DataSyncConfig.from_env(),
            voice=VoiceConfig.from_env(),
            analytics=AnalyticsConfig.from_env(),
            error_handling=ErrorHandlingConfig.from_env(),
            server=ServerConfig.from_env()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (excluding sensitive data)"""
        config_dict = {}
        for key, value in self.__dict__.items():
            if hasattr(value, '__dict__'):
                # Handle nested dataclass
                nested_dict = {}
                for nested_key, nested_value in value.__dict__.items():
                    # Exclude sensitive information
                    if 'secret' in nested_key.lower() or 'password' in nested_key.lower() or 'key' in nested_key.lower():
                        nested_dict[nested_key] = "***REDACTED***"
                    else:
                        nested_dict[nested_key] = nested_value
                config_dict[key] = nested_dict
            else:
                config_dict[key] = value
        return config_dict
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate database URL
        if not self.database.url:
            errors.append("Database URL is required")
        
        # Validate JWT secret in production
        if self.environment == Environment.PRODUCTION:
            if not self.auth.jwt_secret_key or len(self.auth.jwt_secret_key) < 32:
                errors.append("JWT secret key must be at least 32 characters in production")
        
        # Validate authentication configuration
        if self.auth.session_timeout_hours <= 0:
            errors.append("Session timeout must be greater than 0")
        
        if self.auth.password_min_length < 6:
            errors.append("Password minimum length must be at least 6 characters")
        
        # Validate AI agent configuration
        if not self.ai_agent.google_api_key:
            errors.append("Google API key is required for AI agent functionality")
        
        # Validate admin dashboard path
        if self.admin_dashboard.enabled:
            frontend_path = Path(self.admin_dashboard.frontend_path)
            if not frontend_path.exists():
                errors.append(f"Admin dashboard frontend path does not exist: {frontend_path}")
        
        return errors
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == Environment.DEVELOPMENT


class ConfigManager:
    """Manages unified configuration throughout the application lifecycle"""
    
    def __init__(self, config: Optional[UnifiedConfig] = None):
        self._config = config or UnifiedConfig.from_env()
        self._validated = False
        self._validation_errors: List[str] = []
    
    @property
    def config(self) -> UnifiedConfig:
        """Get the current configuration"""
        return self._config
    
    def validate_config(self) -> bool:
        """Validate the configuration and return True if valid"""
        self._validation_errors = self._config.validate()
        self._validated = True
        return len(self._validation_errors) == 0
    
    def get_validation_errors(self) -> List[str]:
        """Get configuration validation errors"""
        if not self._validated:
            self.validate_config()
        return self._validation_errors.copy()
    
    def setup_logging(self) -> None:
        """Setup logging based on configuration"""
        log_level = getattr(logging, self._config.error_handling.log_level, logging.INFO)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=self._config.error_handling.log_file
        )
        
        # Set specific logger levels
        if self._config.is_development():
            logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        else:
            logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    def get_database_url(self) -> str:
        """Get database URL for SQLAlchemy"""
        return self._config.database.url
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins for FastAPI"""
        return self._config.server.cors_origins
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        feature_map = {
            'admin_dashboard': self._config.admin_dashboard.enabled,
            'data_sync': self._config.data_sync.enabled,
            'voice': self._config.voice.enabled,
            'analytics': self._config.analytics.enabled,
            'error_reporting': self._config.error_handling.error_reporting_enabled
        }
        return feature_map.get(feature, False)
    
    def get_health_check_info(self) -> Dict[str, Any]:
        """Get configuration info for health checks"""
        return {
            'environment': self._config.environment.value,
            'features_enabled': {
                'admin_dashboard': self._config.admin_dashboard.enabled,
                'data_sync': self._config.data_sync.enabled,
                'voice': self._config.voice.enabled,
                'analytics': self._config.analytics.enabled,
                'ai_agent': bool(self._config.ai_agent.google_api_key)
            },
            'validation_status': {
                'validated': self._validated,
                'errors_count': len(self._validation_errors),
                'is_valid': len(self._validation_errors) == 0 if self._validated else None
            }
        }


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> UnifiedConfig:
    """Get the current unified configuration"""
    return get_config_manager().config


def validate_configuration() -> bool:
    """Validate the current configuration"""
    return get_config_manager().validate_config()


def get_validation_errors() -> List[str]:
    """Get configuration validation errors"""
    return get_config_manager().get_validation_errors()