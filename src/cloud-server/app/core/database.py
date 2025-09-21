"""
ArchBuilder.AI - Database Configuration and Connection Management
Handles PostgreSQL database connections, connection pooling, and migration management
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any
from urllib.parse import quote_plus

import structlog
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine, AsyncEngine
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import asyncpg
from sqlalchemy.ext.declarative import declarative_base

from .config import get_settings
from .logging import get_correlation_id # Yeni import
from .exceptions import RevitAutoPlanException, NetworkException # Yeni import

logger = structlog.get_logger(__name__)

# Create base class for models
Base = declarative_base()
metadata = MetaData()

class DatabaseConfig:
    """Database configuration management."""
    
    def __init__(self, settings):
        self.settings = settings
        self.database_url = self._build_database_url()
        self.async_database_url = self._build_async_database_url()
        
    def _build_database_url(self) -> str:
        """Build synchronous database URL."""
        return self.settings.DATABASE_URL.replace("+asyncpg", "") # remove asyncpg for sync engine
    
    def _build_async_database_url(self) -> str:
        """Build asynchronous database URL."""
        return self.settings.DATABASE_URL if "+asyncpg" in self.settings.DATABASE_URL else self.settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    @property
    def connection_params(self) -> Dict[str, Any]:
        """Get connection parameters for asyncpg."""
        # URL'den bilgileri çıkar
        from urllib.parse import urlparse
        parsed_url = urlparse(self.settings.DATABASE_URL)
        
        return {
            "host": parsed_url.hostname or "localhost",
            "port": parsed_url.port or 5432,
            "user": parsed_url.username or "postgres",
            "password": parsed_url.password or "password",
            "database": parsed_url.path.lstrip('/') or "archbuilder_ai"
        }

class DatabaseManager:
    """Manages database connections, sessions, and operations."""
    
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.db_config = DatabaseConfig(self.settings)
        self.engine: Optional[AsyncEngine] = None
        self.sync_engine = None
        self.async_session_factory: Optional[async_sessionmaker] = None
        self.sync_session_factory: Optional[sessionmaker] = None
        
    async def initialize(self) -> None:
        """Initialize database connections and create tables."""
        try:
            # Create async engine with connection pooling
            self.engine = create_async_engine(
                self.db_config.async_database_url,
                echo=self.settings.DATABASE_ECHO,
                poolclass=QueuePool,
                pool_size=self.settings.DATABASE_POOL_SIZE, # Yeni ayar
                max_overflow=self.settings.DATABASE_MAX_OVERFLOW, # Yeni ayar
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True,  # Verify connections before use
                connect_args={
                    "server_settings": {
                        "application_name": "archbuilder-ai",
                        "timezone": "UTC"
                    }
                }
            )
            
            # Create sync engine for migrations
            self.sync_engine = create_engine(
                self.db_config.database_url,
                echo=self.settings.DATABASE_ECHO,
                poolclass=QueuePool,
                pool_size=self.settings.DATABASE_POOL_SIZE // 2, # Yeni ayar
                max_overflow=self.settings.DATABASE_MAX_OVERFLOW // 2, # Yeni ayar
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True
            )
            
            # Create session factories
            self.async_session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            self.sync_session_factory = sessionmaker(
                bind=self.sync_engine,
                autoflush=True,
                autocommit=False
            )
            
            logger.info(
                "Database manager initialized",
                host=self.db_config.connection_params["host"],
                port=self.db_config.connection_params["port"],
                database=self.db_config.connection_params["database"]
            )
            
        except Exception as e:
            logger.error("Failed to initialize database manager", error=str(e), exc_info=True, correlation_id=get_correlation_id())
            raise RevitAutoPlanException("Veritabanı yöneticisi başlatılamadı.", error_code="DB_001", correlation_id=get_correlation_id(), inner_exception=e)
    
    async def create_database_if_not_exists(self) -> None:
        """Create database if it doesn't exist."""
        try:
            # Connect to postgres database to create target database
            admin_params = self.db_config.connection_params.copy()
            target_database_name = admin_params.pop("database")
            admin_params["database"] = "postgres" # Connect to default postgres DB to create new one
            
            conn = await asyncpg.connect(**admin_params)
            
            try:
                # Check if database exists
                exists = await conn.fetchval(
                    "SELECT 1 FROM pg_database WHERE datname = $1",
                    target_database_name
                )
                
                if not exists:
                    # Create database
                    await conn.execute(
                        f'CREATE DATABASE "{target_database_name}" OWNER "{admin_params["user"]}'
                    )
                    logger.info("Database created", database=target_database_name, correlation_id=get_correlation_id())
                else:
                    logger.info("Database already exists", database=target_database_name, correlation_id=get_correlation_id())
                    
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error("Failed to create database", error=str(e), exc_info=True, correlation_id=get_correlation_id())
            raise RevitAutoPlanException("Veritabanı oluşturulamadı.", error_code="DB_002", correlation_id=get_correlation_id(), inner_exception=e)
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        try:
            if not self.engine:
                raise RevitAutoPlanException("Veritabanı motoru başlatılmadı.", error_code="DB_003", correlation_id=get_correlation_id())
            
            from app.models.database import Base # Modelleri import et

            async with self.engine.begin() as conn:
                # Create UUID extension if not exists
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                
                # Create all tables
                await conn.run_sync(Base.metadata.create_all)
                
            logger.info("Database tables created successfully", correlation_id=get_correlation_id())
            
        except Exception as e:
            logger.error("Failed to create tables", error=str(e), exc_info=True, correlation_id=get_correlation_id())
            raise RevitAutoPlanException("Veritabanı tabloları oluşturulamadı.", error_code="DB_004", correlation_id=get_correlation_id(), inner_exception=e)
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session with automatic cleanup."""
        if not self.async_session_factory:
            raise RevitAutoPlanException("Async oturum fabrikası başlatılmadı.", error_code="DB_005", correlation_id=get_correlation_id())
        
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database session transaction failed", error=str(e), exc_info=True, correlation_id=get_correlation_id())
            raise RevitAutoPlanException("Veritabanı oturum işlemi başarısız oldu.", error_code="DB_006", correlation_id=get_correlation_id(), inner_exception=e)
        finally:
            await session.close()
    
    async def check_connection(self) -> bool:
        """Check database connection health."""
        try:
            if not self.engine:
                logger.warning("Database engine not initialized for connection check.", correlation_id=get_correlation_id())
                return False
            
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()  # Don't await this
            
            logger.info("Database connection check successful.", correlation_id=get_correlation_id())
            return True
            
        except Exception as e:
            logger.error("Database connection check failed", error=str(e), correlation_id=get_correlation_id(), exc_info=True)
            return False
    
    async def cleanup(self) -> None:
        """Close all database connections and cleanup resources."""
        try:
            if self.engine:
                await self.engine.dispose()
                logger.info("Async database engine disposed", correlation_id=get_correlation_id())
            
            if self.sync_engine:
                self.sync_engine.dispose()
                logger.info("Sync database engine disposed", correlation_id=get_correlation_id())
                
        except Exception as e:
            logger.error("Failed to cleanup database connections", error=str(e), correlation_id=get_correlation_id(), exc_info=True)
            raise RevitAutoPlanException("Veritabanı bağlantıları temizlenirken hata oluştu.", error_code="DB_007", correlation_id=get_correlation_id(), inner_exception=e)

# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

async def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    
    if _db_manager is None:
        settings = get_settings()
        _db_manager = DatabaseManager(settings)
        await _db_manager.initialize()
    
    return _db_manager

async def init_db() -> None:
    """Initialize database - create database and tables if needed."""
    try:
        settings = get_settings()
        db_manager = DatabaseManager(settings)
        
        # Create database if it doesn't exist
        await db_manager.create_database_if_not_exists()
        
        # Initialize connection manager
        await db_manager.initialize()
        
        # Create tables
        await db_manager.create_tables()
        
        # Set global instance
        global _db_manager
        _db_manager = db_manager
        
        logger.info("Database initialization completed successfully", correlation_id=get_correlation_id())
        
    except Exception as e:
        logger.error("Database initialization failed", error=str(e), exc_info=True, correlation_id=get_correlation_id())
        raise RevitAutoPlanException("Veritabanı başlatma başarısız oldu.", error_code="DB_008", correlation_id=get_correlation_id(), inner_exception=e)

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    db_manager = await get_database_manager()
    async with db_manager.get_session() as session:
        yield session

# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    async with get_db_session() as session:
        yield session