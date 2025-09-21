"""
Configuration management for ArchBuilder.AI
Centralized settings with environment variable support
"""

import os
from functools import lru_cache
from typing import Optional, List
from pydantic import BaseModel, validator


class Settings(BaseModel):
    """Application settings with environment variable support"""
    
    # Application settings
    APP_NAME: str = "ArchBuilder.AI"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    API_KEY_EXPIRE_DAYS: int = 365
    
    # Database settings
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/archbuilder_ai"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL_FOR_LIMITER: str = "redis://localhost:6379/1" # Rate limiter için yeni Redis URL

    # AI Services settings
    AI_MODEL_GEMINI: str = "gemini-2.5-flash-latest" # Gemini model adı
    AI_MODEL_GPT4: str = "gpt-4-turbo" # GPT-4 model adı
    OPENAI_API_KEY: Optional[str] = None
    VERTEX_AI_PROJECT_ID: Optional[str] = None
    VERTEX_AI_LOCATION: str = "us-central1"
    GITHUB_TOKEN: Optional[str] = None
    
    # Stripe settings
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # File upload settings
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    UPLOAD_DIR: str = "uploads"
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Rate limiting settings
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600  # 1 hour
    
    # Regional settings
    DEFAULT_REGION: str = "us"
    DEFAULT_LOCALE: str = "en"
    SUPPORTED_LOCALES: List[str] = ["en", "tr", "es", "fr", "de"]
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if v == "your-secret-key-here":
            raise ValueError("Please set a proper SECRET_KEY in production")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Environment-specific configurations
class DevelopmentSettings(Settings):
    """Development environment settings"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DATABASE_ECHO: bool = True


class ProductionSettings(Settings):
    """Production environment settings"""
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    DATABASE_ECHO: bool = False
    
    @validator("SECRET_KEY")
    def validate_production_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        return v


class TestingSettings(Settings):
    """Testing environment settings"""
    DATABASE_URL: str = "sqlite:///./test.db"
    REDIS_HOST: str = "localhost"
    SECRET_KEY: str = "test-secret-key-for-testing-only"


def get_environment_settings() -> Settings:
    """Get settings based on environment"""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionSettings()
    elif environment == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()