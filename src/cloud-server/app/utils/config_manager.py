"""
ArchBuilder.AI - Configuration Management System
Environment-based configuration with secret management, feature flags, and deployment settings.
"""

import os
import json
from typing import Any, Dict, Optional, List, Union, Type, get_type_hints
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import structlog
from pydantic import BaseModel, Field, validator
import yaml

class Environment(Enum):
    """Application environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

class LogLevel(Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str
    pool_size: int = 20
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    ssl_mode: str = "prefer"

@dataclass
class RedisConfig:
    """Redis configuration."""
    url: str = "redis://localhost:6379"
    password: Optional[str] = None
    db: int = 0
    max_connections: int = 20
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True

@dataclass
class AIModelConfig:
    """AI model configuration."""
    provider: str  # "vertex_ai", "github_models", "openai"
    model_name: str
    api_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.7
    timeout_seconds: int = 30
    retry_attempts: int = 3
    confidence_threshold: float = 0.7

@dataclass
class SecurityConfig:
    """Security configuration."""
    secret_key: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    password_hash_rounds: int = 12
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    cors_origins: List[str] = field(default_factory=list)
    https_only: bool = True
    secure_cookies: bool = True

@dataclass
class CacheConfig:
    """Cache configuration."""
    memory_cache_size: int = 1000
    memory_cache_ttl: int = 300  # 5 minutes
    redis_default_ttl: int = 3600  # 1 hour
    enable_compression: bool = True
    compression_threshold: int = 1024  # bytes
    max_key_length: int = 250

@dataclass
class PerformanceConfig:
    """Performance monitoring configuration."""
    collection_interval: float = 60.0  # seconds
    retention_hours: int = 24
    enable_profiling: bool = False
    enable_metrics_export: bool = True
    metrics_endpoint: str = "/metrics"
    alert_thresholds: Dict[str, Dict[str, float]] = field(default_factory=dict)

@dataclass
class FileProcessingConfig:
    """File processing configuration."""
    max_file_size_mb: int = 100
    allowed_extensions: List[str] = field(default_factory=lambda: ['.dwg', '.dxf', '.ifc', '.pdf'])
    upload_path: str = "/tmp/uploads"
    virus_scan_enabled: bool = True
    processing_timeout_minutes: int = 30
    cleanup_temp_files: bool = True

@dataclass
class FeatureFlags:
    """Feature flags configuration."""
    enable_ai_caching: bool = True
    enable_performance_tracking: bool = True
    enable_virus_scanning: bool = True
    enable_ocr_processing: bool = True
    enable_3d_visualization: bool = False
    enable_collaboration: bool = False
    enable_mobile_app: bool = False
    max_concurrent_ai_requests: int = 10
    enable_advanced_analytics: bool = False

class AppConfig:
    """
    Main application configuration class.
    
    Loads configuration from multiple sources in order of priority:
    1. Environment variables
    2. Configuration files (YAML/JSON)
    3. Default values
    """
    
    def __init__(
        self,
        config_file: Optional[str] = None,
        environment: Optional[Environment] = None
    ):
        self.logger = structlog.get_logger(__name__)
        
        # Determine environment
        self.environment = environment or Environment(
            os.getenv("APP_ENVIRONMENT", "development")
        )
        
        # Load configuration
        self.config_data = self._load_configuration(config_file)
        
        # Initialize configuration sections
        self.database = self._create_database_config()
        self.redis = self._create_redis_config()
        self.ai_models = self._create_ai_models_config()
        self.security = self._create_security_config()
        self.cache = self._create_cache_config()
        self.performance = self._create_performance_config()
        self.file_processing = self._create_file_processing_config()
        self.feature_flags = self._create_feature_flags()
        
        # Application settings
        self.app_name = self._get_config("app.name", "ArchBuilder.AI")
        self.app_version = self._get_config("app.version", "1.0.0")
        self.debug = self._get_config("app.debug", self.environment == Environment.DEVELOPMENT)
        self.log_level = LogLevel(self._get_config("app.log_level", "INFO"))
        self.host = self._get_config("app.host", "localhost")
        self.port = int(self._get_config("app.port", 8000))
        self.workers = int(self._get_config("app.workers", 1))
        
        # Regional settings
        self.default_locale = self._get_config("app.default_locale", "en-US")
        self.supported_locales = self._get_config(
            "app.supported_locales", 
            ["en-US", "tr-TR", "de-DE", "fr-FR", "es-ES"]
        )
        
        self.logger.info(
            "Configuration loaded",
            environment=self.environment.value,
            app_name=self.app_name,
            debug=self.debug,
            supported_locales=self.supported_locales
        )
    
    def _load_configuration(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file and environment variables."""
        config = {}
        
        # Load from configuration file
        if config_file:
            config_path = Path(config_file)
        else:
            # Look for default config files
            config_dir = Path("configs")
            possible_files = [
                config_dir / f"{self.environment.value}.yaml",
                config_dir / f"{self.environment.value}.yml",
                config_dir / f"{self.environment.value}.json",
                config_dir / "default.yaml",
                config_dir / "default.yml",
                config_dir / "default.json"
            ]
            
            config_path = None
            for path in possible_files:
                if path.exists():
                    config_path = path
                    break
        
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    if config_path.suffix.lower() in ['.yaml', '.yml']:
                        config = yaml.safe_load(f) or {}
                    else:
                        config = json.load(f)
                
                self.logger.info(
                    "Configuration file loaded",
                    config_file=str(config_path),
                    keys_loaded=list(config.keys())
                )
                
            except Exception as e:
                self.logger.warning(
                    "Failed to load configuration file",
                    config_file=str(config_path),
                    error=str(e)
                )
                config = {}
        
        return config
    
    def _get_config(
        self,
        key: str,
        default: Any = None,
        required: bool = False
    ) -> Any:
        """
        Get configuration value with environment variable override.
        
        Args:
            key: Configuration key (dot notation supported)
            default: Default value if not found
            required: Raise error if required and not found
            
        Returns:
            Configuration value
        """
        # Convert dot notation to environment variable
        env_key = key.upper().replace(".", "_")
        
        # Check environment variable first
        env_value = os.getenv(env_key)
        if env_value is not None:
            # Try to convert to appropriate type
            return self._convert_env_value(env_value)
        
        # Check configuration file
        keys = key.split(".")
        value = self.config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            if required:
                raise ValueError(f"Required configuration key '{key}' not found")
            return default
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Boolean values
        if value.lower() in ['true', 'yes', '1', 'on']:
            return True
        elif value.lower() in ['false', 'no', '0', 'off']:
            return False
        
        # Numeric values
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # List values (comma-separated)
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        # String value
        return value
    
    def _create_database_config(self) -> DatabaseConfig:
        """Create database configuration."""
        return DatabaseConfig(
            url=self._get_config("database.url", required=True),
            pool_size=int(self._get_config("database.pool_size", 20)),
            max_overflow=int(self._get_config("database.max_overflow", 10)),
            pool_timeout=int(self._get_config("database.pool_timeout", 30)),
            pool_recycle=int(self._get_config("database.pool_recycle", 3600)),
            echo=self._get_config("database.echo", False),
            ssl_mode=self._get_config("database.ssl_mode", "prefer")
        )
    
    def _create_redis_config(self) -> RedisConfig:
        """Create Redis configuration."""
        return RedisConfig(
            url=self._get_config("redis.url", "redis://localhost:6379"),
            password=self._get_config("redis.password"),
            db=int(self._get_config("redis.db", 0)),
            max_connections=int(self._get_config("redis.max_connections", 20)),
            socket_timeout=int(self._get_config("redis.socket_timeout", 5)),
            socket_connect_timeout=int(self._get_config("redis.socket_connect_timeout", 5)),
            retry_on_timeout=self._get_config("redis.retry_on_timeout", True)
        )
    
    def _create_ai_models_config(self) -> Dict[str, AIModelConfig]:
        """Create AI models configuration."""
        models = {}
        
        # Primary AI model
        models["primary"] = AIModelConfig(
            provider=self._get_config("ai.primary.provider", "vertex_ai"),
            model_name=self._get_config("ai.primary.model_name", "gemini-1.5-flash"),
            api_key=self._get_config("ai.primary.api_key"),
            endpoint_url=self._get_config("ai.primary.endpoint_url"),
            max_tokens=int(self._get_config("ai.primary.max_tokens", 4000)),
            temperature=float(self._get_config("ai.primary.temperature", 0.7)),
            timeout_seconds=int(self._get_config("ai.primary.timeout_seconds", 30)),
            retry_attempts=int(self._get_config("ai.primary.retry_attempts", 3)),
            confidence_threshold=float(self._get_config("ai.primary.confidence_threshold", 0.7))
        )
        
        # Fallback AI model
        models["fallback"] = AIModelConfig(
            provider=self._get_config("ai.fallback.provider", "github_models"),
            model_name=self._get_config("ai.fallback.model_name", "gpt-4"),
            api_key=self._get_config("ai.fallback.api_key"),
            endpoint_url=self._get_config("ai.fallback.endpoint_url"),
            max_tokens=int(self._get_config("ai.fallback.max_tokens", 4000)),
            temperature=float(self._get_config("ai.fallback.temperature", 0.7)),
            timeout_seconds=int(self._get_config("ai.fallback.timeout_seconds", 30)),
            retry_attempts=int(self._get_config("ai.fallback.retry_attempts", 3)),
            confidence_threshold=float(self._get_config("ai.fallback.confidence_threshold", 0.7))
        )
        
        return models
    
    def _create_security_config(self) -> SecurityConfig:
        """Create security configuration."""
        return SecurityConfig(
            secret_key=self._get_config("security.secret_key", required=True),
            jwt_secret=self._get_config("security.jwt_secret", required=True),
            jwt_algorithm=self._get_config("security.jwt_algorithm", "HS256"),
            jwt_expiration_hours=int(self._get_config("security.jwt_expiration_hours", 24)),
            password_hash_rounds=int(self._get_config("security.password_hash_rounds", 12)),
            max_login_attempts=int(self._get_config("security.max_login_attempts", 5)),
            lockout_duration_minutes=int(self._get_config("security.lockout_duration_minutes", 15)),
            cors_origins=self._get_config("security.cors_origins", []),
            https_only=self._get_config("security.https_only", True),
            secure_cookies=self._get_config("security.secure_cookies", True)
        )
    
    def _create_cache_config(self) -> CacheConfig:
        """Create cache configuration."""
        return CacheConfig(
            memory_cache_size=int(self._get_config("cache.memory_cache_size", 1000)),
            memory_cache_ttl=int(self._get_config("cache.memory_cache_ttl", 300)),
            redis_default_ttl=int(self._get_config("cache.redis_default_ttl", 3600)),
            enable_compression=self._get_config("cache.enable_compression", True),
            compression_threshold=int(self._get_config("cache.compression_threshold", 1024)),
            max_key_length=int(self._get_config("cache.max_key_length", 250))
        )
    
    def _create_performance_config(self) -> PerformanceConfig:
        """Create performance configuration."""
        default_thresholds = {
            "operation_duration_ms": {"warning": 5000, "critical": 30000},
            "memory_delta_mb": {"warning": 100, "critical": 500},
            "cpu_percent": {"warning": 80, "critical": 95},
            "system_memory_percent": {"warning": 80, "critical": 95},
            "system_cpu_percent": {"warning": 80, "critical": 95},
            "error_rate": {"warning": 0.05, "critical": 0.10}
        }
        
        return PerformanceConfig(
            collection_interval=float(self._get_config("performance.collection_interval", 60.0)),
            retention_hours=int(self._get_config("performance.retention_hours", 24)),
            enable_profiling=self._get_config("performance.enable_profiling", False),
            enable_metrics_export=self._get_config("performance.enable_metrics_export", True),
            metrics_endpoint=self._get_config("performance.metrics_endpoint", "/metrics"),
            alert_thresholds=self._get_config("performance.alert_thresholds", default_thresholds)
        )
    
    def _create_file_processing_config(self) -> FileProcessingConfig:
        """Create file processing configuration."""
        return FileProcessingConfig(
            max_file_size_mb=int(self._get_config("file_processing.max_file_size_mb", 100)),
            allowed_extensions=self._get_config(
                "file_processing.allowed_extensions", 
                ['.dwg', '.dxf', '.ifc', '.pdf']
            ),
            upload_path=self._get_config("file_processing.upload_path", "/tmp/uploads"),
            virus_scan_enabled=self._get_config("file_processing.virus_scan_enabled", True),
            processing_timeout_minutes=int(self._get_config("file_processing.processing_timeout_minutes", 30)),
            cleanup_temp_files=self._get_config("file_processing.cleanup_temp_files", True)
        )
    
    def _create_feature_flags(self) -> FeatureFlags:
        """Create feature flags configuration."""
        return FeatureFlags(
            enable_ai_caching=self._get_config("features.enable_ai_caching", True),
            enable_performance_tracking=self._get_config("features.enable_performance_tracking", True),
            enable_virus_scanning=self._get_config("features.enable_virus_scanning", True),
            enable_ocr_processing=self._get_config("features.enable_ocr_processing", True),
            enable_3d_visualization=self._get_config("features.enable_3d_visualization", False),
            enable_collaboration=self._get_config("features.enable_collaboration", False),
            enable_mobile_app=self._get_config("features.enable_mobile_app", False),
            max_concurrent_ai_requests=int(self._get_config("features.max_concurrent_ai_requests", 10)),
            enable_advanced_analytics=self._get_config("features.enable_advanced_analytics", False)
        )
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get secret value from secure storage or environment.
        
        Args:
            key: Secret key
            default: Default value if not found
            
        Returns:
            Secret value
        """
        # In production, this would integrate with secure secret stores
        # like AWS Secrets Manager, Azure Key Vault, or HashiCorp Vault
        
        # For now, use environment variables
        env_key = f"SECRET_{key.upper()}"
        return os.getenv(env_key, default)
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding secrets)."""
        return {
            "environment": self.environment.value,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "debug": self.debug,
            "log_level": self.log_level.value,
            "host": self.host,
            "port": self.port,
            "workers": self.workers,
            "default_locale": self.default_locale,
            "supported_locales": self.supported_locales,
            "database": {
                "pool_size": self.database.pool_size,
                "max_overflow": self.database.max_overflow,
                "pool_timeout": self.database.pool_timeout,
                "echo": self.database.echo
            },
            "redis": {
                "db": self.redis.db,
                "max_connections": self.redis.max_connections,
                "socket_timeout": self.redis.socket_timeout
            },
            "cache": {
                "memory_cache_size": self.cache.memory_cache_size,
                "memory_cache_ttl": self.cache.memory_cache_ttl,
                "redis_default_ttl": self.cache.redis_default_ttl,
                "enable_compression": self.cache.enable_compression
            },
            "performance": {
                "collection_interval": self.performance.collection_interval,
                "retention_hours": self.performance.retention_hours,
                "enable_profiling": self.performance.enable_profiling,
                "enable_metrics_export": self.performance.enable_metrics_export
            },
            "file_processing": {
                "max_file_size_mb": self.file_processing.max_file_size_mb,
                "allowed_extensions": self.file_processing.allowed_extensions,
                "virus_scan_enabled": self.file_processing.virus_scan_enabled,
                "processing_timeout_minutes": self.file_processing.processing_timeout_minutes
            },
            "feature_flags": {
                "enable_ai_caching": self.feature_flags.enable_ai_caching,
                "enable_performance_tracking": self.feature_flags.enable_performance_tracking,
                "enable_virus_scanning": self.feature_flags.enable_virus_scanning,
                "enable_ocr_processing": self.feature_flags.enable_ocr_processing,
                "enable_3d_visualization": self.feature_flags.enable_3d_visualization,
                "enable_collaboration": self.feature_flags.enable_collaboration,
                "enable_mobile_app": self.feature_flags.enable_mobile_app,
                "max_concurrent_ai_requests": self.feature_flags.max_concurrent_ai_requests,
                "enable_advanced_analytics": self.feature_flags.enable_advanced_analytics
            }
        }


# Global configuration instance
_config: Optional[AppConfig] = None

def get_config() -> AppConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config

def init_config(
    config_file: Optional[str] = None,
    environment: Optional[Environment] = None
) -> AppConfig:
    """Initialize global configuration."""
    global _config
    _config = AppConfig(config_file, environment)
    return _config