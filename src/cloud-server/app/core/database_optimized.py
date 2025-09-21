"""
Database performance optimization module for ArchBuilder.AI Cloud Server.

This module implements optimized database operations including:
- Connection pooling
- Query optimization
- Async session management
- Performance monitoring
- Database health checks

According to performance-optimization.instructions.md guidelines.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Type, AsyncGenerator
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from functools import wraps
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import text, select, update, delete, func, and_, or_
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
import psutil

logger = structlog.get_logger(__name__)

T = TypeVar('T', bound=DeclarativeBase)

class DatabaseConfig:
    """Database configuration for performance optimization"""
    
    def __init__(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 30,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False,
        query_timeout: int = 30
    ):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo
        self.query_timeout = query_timeout

class DatabaseMetrics:
    """Database performance metrics collector"""
    
    def __init__(self):
        self.query_count = 0
        self.total_query_time = 0.0
        self.slow_query_count = 0
        self.error_count = 0
        self.connection_pool_hits = 0
        self.connection_pool_misses = 0
        self.active_connections = 0
        self.slow_query_threshold = 2.0  # 2 seconds
        self.recent_queries: List[Dict[str, Any]] = []
        self.max_recent_queries = 100
    
    def record_query(
        self, 
        query: str, 
        duration: float, 
        success: bool = True,
        correlation_id: Optional[str] = None
    ):
        """Record query execution metrics"""
        self.query_count += 1
        self.total_query_time += duration
        
        if not success:
            self.error_count += 1
        
        if duration > self.slow_query_threshold:
            self.slow_query_count += 1
            logger.warning("Slow query detected",
                          query=query[:200],
                          duration=duration,
                          correlation_id=correlation_id)
        
        # Store recent query info
        query_info = {
            "query": query[:200],  # Truncate long queries
            "duration": duration,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id
        }
        
        self.recent_queries.append(query_info)
        if len(self.recent_queries) > self.max_recent_queries:
            self.recent_queries.pop(0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        avg_query_time = self.total_query_time / self.query_count if self.query_count > 0 else 0
        slow_query_rate = self.slow_query_count / self.query_count if self.query_count > 0 else 0
        error_rate = self.error_count / self.query_count if self.query_count > 0 else 0
        
        return {
            "query_count": self.query_count,
            "total_query_time": self.total_query_time,
            "avg_query_time": avg_query_time,
            "slow_query_count": self.slow_query_count,
            "slow_query_rate": slow_query_rate,
            "error_count": self.error_count,
            "error_rate": error_rate,
            "active_connections": self.active_connections,
            "connection_pool_hits": self.connection_pool_hits,
            "connection_pool_misses": self.connection_pool_misses,
            "recent_queries": self.recent_queries[-10:],  # Last 10 queries
            "timestamp": datetime.utcnow().isoformat()
        }

class OptimizedDatabaseService:
    """
    High-performance database service with optimization features.
    
    Features:
    - Connection pooling with async support
    - Query performance monitoring
    - Automatic query optimization
    - Batch operations
    - Health monitoring
    - Resource management
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.metrics = DatabaseMetrics()
        self.engine: Optional[AsyncEngine] = None
        self.async_session_maker: Optional[async_sessionmaker] = None
        self._initialized = False
        
        logger.info("OptimizedDatabaseService created", config=config.__dict__)
    
    async def initialize(self):
        """Initialize database engine and connection pool"""
        if self._initialized:
            return
        
        # Create async engine with optimized settings
        self.engine = create_async_engine(
            self.config.database_url,
            poolclass=QueuePool,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            echo=self.config.echo,
            # Async specific optimizations
            pool_pre_ping=True,  # Verify connections before use
            pool_reset_on_return='commit',  # Reset connections on return
        )
        
        # Create async session maker
        self.async_session_maker = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,  # Manual control over flushing
            autocommit=False
        )
        
        self._initialized = True
        
        logger.info("Database engine initialized",
                   pool_size=self.config.pool_size,
                   max_overflow=self.config.max_overflow)
    
    async def shutdown(self):
        """Gracefully shutdown database connections"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database engine disposed")
    
    @asynccontextmanager
    async def get_session(self, correlation_id: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
        """
        Get optimized database session with automatic resource management.
        
        Usage:
            async with db_service.get_session() as session:
                result = await session.execute(select(User))
        """
        if not self._initialized:
            await self.initialize()
        
        session = self.async_session_maker()
        self.metrics.active_connections += 1
        
        try:
            yield session
            await session.commit()
            
        except Exception as e:
            await session.rollback()
            logger.error("Database session error",
                        error=str(e),
                        correlation_id=correlation_id)
            raise
            
        finally:
            await session.close()
            self.metrics.active_connections -= 1
    
    async def execute_query(
        self,
        query: Union[str, Any],
        params: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> Any:
        """
        Execute optimized database query with performance monitoring.
        
        Args:
            query: SQL query string or SQLAlchemy query object
            params: Query parameters
            correlation_id: Request correlation ID for tracking
        
        Returns:
            Query result
        """
        start_time = time.time()
        query_str = str(query)
        
        try:
            async with self.get_session(correlation_id) as session:
                if isinstance(query, str):
                    # Raw SQL query
                    result = await session.execute(text(query), params or {})
                else:
                    # SQLAlchemy query object
                    result = await session.execute(query, params or {})
                
                # Fetch results based on query type
                if hasattr(result, 'fetchall'):
                    data = result.fetchall()
                elif hasattr(result, 'scalars'):
                    data = result.scalars().all()
                else:
                    data = result
                
                duration = time.time() - start_time
                self.metrics.record_query(query_str, duration, True, correlation_id)
                
                logger.debug("Query executed successfully",
                           query=query_str[:100],
                           duration=duration,
                           result_count=len(data) if hasattr(data, '__len__') else 1,
                           correlation_id=correlation_id)
                
                return data
                
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_query(query_str, duration, False, correlation_id)
            
            logger.error("Query execution failed",
                        query=query_str[:100],
                        duration=duration,
                        error=str(e),
                        correlation_id=correlation_id)
            raise
    
    async def execute_batch(
        self,
        operations: List[Dict[str, Any]],
        correlation_id: Optional[str] = None
    ) -> List[Any]:
        """
        Execute batch operations for improved performance.
        
        Args:
            operations: List of operations, each containing:
                       {'type': 'select|insert|update|delete', 'query': query, 'params': params}
            correlation_id: Request correlation ID
        
        Returns:
            List of results for each operation
        """
        start_time = time.time()
        results = []
        
        try:
            async with self.get_session(correlation_id) as session:
                for operation in operations:
                    op_type = operation.get('type')
                    query = operation.get('query')
                    params = operation.get('params', {})
                    
                    if isinstance(query, str):
                        result = await session.execute(text(query), params)
                    else:
                        result = await session.execute(query, params)
                    
                    # Process result based on operation type
                    if op_type == 'select':
                        if hasattr(result, 'scalars'):
                            data = result.scalars().all()
                        else:
                            data = result.fetchall()
                        results.append(data)
                    else:
                        # For insert/update/delete, return affected rows
                        results.append(result.rowcount)
                
                # Commit all operations at once
                await session.commit()
                
                duration = time.time() - start_time
                self.metrics.record_query(f"BATCH({len(operations)} ops)", duration, True, correlation_id)
                
                logger.info("Batch operations completed",
                           operation_count=len(operations),
                           duration=duration,
                           correlation_id=correlation_id)
                
                return results
                
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_query(f"BATCH({len(operations)} ops)", duration, False, correlation_id)
            
            logger.error("Batch operation failed",
                        operation_count=len(operations),
                        duration=duration,
                        error=str(e),
                        correlation_id=correlation_id)
            raise
    
    async def get_model_by_id(
        self,
        model_class: Type[T],
        model_id: Any,
        correlation_id: Optional[str] = None
    ) -> Optional[T]:
        """
        Optimized single model retrieval by ID.
        
        Args:
            model_class: SQLAlchemy model class
            model_id: Model ID
            correlation_id: Request correlation ID
        
        Returns:
            Model instance or None
        """
        query = select(model_class).where(model_class.id == model_id)
        
        start_time = time.time()
        try:
            async with self.get_session(correlation_id) as session:
                result = await session.execute(query)
                model = result.scalar_one_or_none()
                
                duration = time.time() - start_time
                self.metrics.record_query(f"GET {model_class.__name__} BY ID", duration, True, correlation_id)
                
                return model
                
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_query(f"GET {model_class.__name__} BY ID", duration, False, correlation_id)
            raise
    
    async def get_models_by_filter(
        self,
        model_class: Type[T],
        filters: Dict[str, Any],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> List[T]:
        """
        Optimized model retrieval with filters, pagination, and sorting.
        
        Args:
            model_class: SQLAlchemy model class
            filters: Dictionary of field:value filters
            limit: Maximum results to return
            offset: Number of results to skip
            order_by: Field name to order by
            correlation_id: Request correlation ID
        
        Returns:
            List of model instances
        """
        query = select(model_class)
        
        # Apply filters
        for field, value in filters.items():
            if hasattr(model_class, field):
                column = getattr(model_class, field)
                if isinstance(value, list):
                    query = query.where(column.in_(value))
                elif isinstance(value, str) and value.startswith('%') and value.endswith('%'):
                    # LIKE query
                    query = query.where(column.like(value))
                else:
                    query = query.where(column == value)
        
        # Apply ordering
        if order_by and hasattr(model_class, order_by):
            order_column = getattr(model_class, order_by)
            query = query.order_by(order_column)
        
        # Apply pagination
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        start_time = time.time()
        try:
            async with self.get_session(correlation_id) as session:
                result = await session.execute(query)
                models = result.scalars().all()
                
                duration = time.time() - start_time
                self.metrics.record_query(f"FILTER {model_class.__name__}", duration, True, correlation_id)
                
                logger.debug("Filtered query completed",
                           model=model_class.__name__,
                           filters=filters,
                           result_count=len(models),
                           duration=duration,
                           correlation_id=correlation_id)
                
                return models
                
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_query(f"FILTER {model_class.__name__}", duration, False, correlation_id)
            raise
    
    async def create_model(
        self,
        model_class: Type[T],
        data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> T:
        """
        Optimized model creation.
        
        Args:
            model_class: SQLAlchemy model class
            data: Model data dictionary
            correlation_id: Request correlation ID
        
        Returns:
            Created model instance
        """
        start_time = time.time()
        try:
            async with self.get_session(correlation_id) as session:
                model = model_class(**data)
                session.add(model)
                await session.flush()  # Get the ID without committing
                await session.refresh(model)  # Refresh to get all fields
                
                duration = time.time() - start_time
                self.metrics.record_query(f"CREATE {model_class.__name__}", duration, True, correlation_id)
                
                logger.debug("Model created",
                           model=model_class.__name__,
                           model_id=getattr(model, 'id', None),
                           duration=duration,
                           correlation_id=correlation_id)
                
                return model
                
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_query(f"CREATE {model_class.__name__}", duration, False, correlation_id)
            raise
    
    async def update_model(
        self,
        model_class: Type[T],
        model_id: Any,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Optional[T]:
        """
        Optimized model update.
        
        Args:
            model_class: SQLAlchemy model class
            model_id: Model ID
            data: Update data dictionary
            correlation_id: Request correlation ID
        
        Returns:
            Updated model instance or None
        """
        start_time = time.time()
        try:
            async with self.get_session(correlation_id) as session:
                # First get the model
                result = await session.execute(
                    select(model_class).where(model_class.id == model_id)
                )
                model = result.scalar_one_or_none()
                
                if not model:
                    return None
                
                # Update fields
                for field, value in data.items():
                    if hasattr(model, field):
                        setattr(model, field, value)
                
                await session.flush()
                await session.refresh(model)
                
                duration = time.time() - start_time
                self.metrics.record_query(f"UPDATE {model_class.__name__}", duration, True, correlation_id)
                
                logger.debug("Model updated",
                           model=model_class.__name__,
                           model_id=model_id,
                           duration=duration,
                           correlation_id=correlation_id)
                
                return model
                
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_query(f"UPDATE {model_class.__name__}", duration, False, correlation_id)
            raise
    
    async def delete_model(
        self,
        model_class: Type[T],
        model_id: Any,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Optimized model deletion.
        
        Args:
            model_class: SQLAlchemy model class
            model_id: Model ID
            correlation_id: Request correlation ID
        
        Returns:
            True if deleted, False if not found
        """
        start_time = time.time()
        try:
            async with self.get_session(correlation_id) as session:
                result = await session.execute(
                    delete(model_class).where(model_class.id == model_id)
                )
                
                deleted = result.rowcount > 0
                
                duration = time.time() - start_time
                self.metrics.record_query(f"DELETE {model_class.__name__}", duration, True, correlation_id)
                
                logger.debug("Model deletion completed",
                           model=model_class.__name__,
                           model_id=model_id,
                           deleted=deleted,
                           duration=duration,
                           correlation_id=correlation_id)
                
                return deleted
                
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_query(f"DELETE {model_class.__name__}", duration, False, correlation_id)
            raise
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get database health status and performance metrics.
        
        Returns:
            Comprehensive health status dictionary
        """
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": self.metrics.get_stats(),
            "connection_pool": {},
            "system_resources": {}
        }
        
        try:
            # Test database connectivity
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                result.fetchone()
            
            # Get connection pool stats
            if self.engine:
                pool = self.engine.pool
                health_data["connection_pool"] = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid()
                }
            
            # Get system resource usage
            process = psutil.Process()
            health_data["system_resources"] = {
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "cpu_percent": process.cpu_percent(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections())
            }
            
            # Determine overall health status
            metrics = self.metrics.get_stats()
            if (metrics["slow_query_rate"] > 0.1 or  # More than 10% slow queries
                metrics["error_rate"] > 0.05 or      # More than 5% errors
                health_data["system_resources"]["memory_mb"] > 500):  # More than 500MB memory
                health_data["status"] = "warning"
            
            if (metrics["error_rate"] > 0.2 or       # More than 20% errors
                health_data["system_resources"]["memory_mb"] > 1000):  # More than 1GB memory
                health_data["status"] = "critical"
                
        except Exception as e:
            health_data["status"] = "unhealthy"
            health_data["error"] = str(e)
            logger.error("Database health check failed", error=str(e))
        
        return health_data

# Database performance monitoring decorator
def monitor_db_performance(operation_name: str):
    """
    Decorator for monitoring database operation performance.
    
    Usage:
        @monitor_db_performance("get_user_projects")
        async def get_user_projects(user_id: str):
            return await db_service.get_models_by_filter(Project, {"user_id": user_id})
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.debug("Database operation completed",
                           operation=operation_name,
                           duration=duration)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error("Database operation failed",
                           operation=operation_name,
                           duration=duration,
                           error=str(e))
                raise
                
        return wrapper
    return decorator

# Global database service instance
db_service: Optional[OptimizedDatabaseService] = None

def initialize_database(config: DatabaseConfig):
    """Initialize global database service"""
    global db_service
    db_service = OptimizedDatabaseService(config)
    logger.info("Global database service initialized")

def get_database() -> OptimizedDatabaseService:
    """Get global database service instance"""
    if db_service is None:
        raise RuntimeError("Database not initialized. Call initialize_database() first.")
    return db_service