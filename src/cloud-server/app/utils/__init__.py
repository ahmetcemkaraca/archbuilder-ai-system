"""
ArchBuilder.AI - Utility Classes Package
Advanced utility classes for cache management, performance tracking, configuration, and validation.
"""

from .cache_manager import AsyncCacheManager, CacheConfiguration, CacheMetrics, AICacheManager, cache_result
from .performance_tracker import (
    PerformanceTracker, 
    PerformanceMetrics, 
    SystemMetrics, 
    PerformanceAlert,
    MetricType,
    AlertLevel,
    track_performance
)
from .config_manager import (
    AppConfig,
    Environment,
    LogLevel,
    DatabaseConfig,
    RedisConfig,
    AIModelConfig,
    SecurityConfig,
    CacheConfig,
    PerformanceConfig,
    FileProcessingConfig,
    FeatureFlags,
    get_config,
    init_config
)
from .validation_service import (
    ComprehensiveValidator,
    InputValidator,
    GeometryValidator,
    SecurityValidator,
    ValidationResult,
    ValidationError,
    ValidationSeverity,
    ValidationCategory
)

__all__ = [
    # Cache Management
    "AsyncCacheManager",
    "CacheConfiguration", 
    "CacheMetrics",
    "AICacheManager",
    "cache_result",
    
    # Performance Tracking
    "PerformanceTracker",
    "PerformanceMetrics",
    "SystemMetrics", 
    "PerformanceAlert",
    "MetricType",
    "AlertLevel",
    "track_performance",
    
    # Configuration Management
    "AppConfig",
    "Environment",
    "LogLevel",
    "DatabaseConfig",
    "RedisConfig", 
    "AIModelConfig",
    "SecurityConfig",
    "CacheConfig",
    "PerformanceConfig",
    "FileProcessingConfig",
    "FeatureFlags",
    "get_config",
    "init_config",
    
    # Validation Services
    "ComprehensiveValidator",
    "InputValidator",
    "GeometryValidator", 
    "SecurityValidator",
    "ValidationResult",
    "ValidationError",
    "ValidationSeverity",
    "ValidationCategory"
]