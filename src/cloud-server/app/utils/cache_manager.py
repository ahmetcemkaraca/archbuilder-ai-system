"""
ArchBuilder.AI - Advanced Cache Management System
Multi-level caching with Redis and memory cache, performance tracking, and intelligent cache invalidation.
"""

import asyncio
import json
import hashlib
import time
from typing import Any, Dict, Optional, Callable, TypeVar, Awaitable, Union, List
from functools import wraps
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
import cachetools
import redis.asyncio as redis
import structlog
from pydantic import BaseModel
from datetime import datetime, timedelta

T = TypeVar('T')

@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    operation: str
    cache_key: str
    hit: bool
    cache_level: Optional[str] = None  # 'memory', 'redis', None for miss
    access_time_ms: float = 0.0
    value_size_bytes: int = 0
    correlation_id: str = "unknown"

class CacheConfiguration(BaseModel):
    """Cache configuration settings."""
    memory_cache_size: int = 1000
    memory_cache_ttl: int = 300  # 5 minutes
    redis_default_ttl: int = 3600  # 1 hour
    redis_url: str = "redis://localhost:6379"
    enable_compression: bool = True
    compression_threshold: int = 1024  # bytes
    max_key_length: int = 250

class AsyncCacheManager:
    """
    Advanced multi-level cache manager with performance tracking.
    
    Features:
    - Memory cache (L1) + Redis cache (L2)
    - Intelligent key generation
    - Performance metrics collection
    - Cache invalidation strategies
    - Compression for large values
    - Cache warming capabilities
    """
    
    def __init__(
        self,
        config: CacheConfiguration,
        redis_client: Optional[redis.Redis] = None
    ):
        self.config = config
        self.logger = structlog.get_logger(__name__)
        
        # Initialize memory cache (L1)
        self.memory_cache = cachetools.TTLCache(
            maxsize=config.memory_cache_size,
            ttl=config.memory_cache_ttl
        )
        
        # Initialize Redis client (L2)
        self.redis_client = redis_client or redis.from_url(
            config.redis_url,
            decode_responses=False,  # Handle binary data
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        
        # Performance tracking
        self.metrics: List[CacheMetrics] = []
        self.hit_rates: Dict[str, float] = {}
        
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        memory_ttl: Optional[int] = None,
        redis_ttl: Optional[int] = None,
        correlation_id: str = "unknown",
        force_refresh: bool = False
    ) -> T:
        """
        Get value from cache or compute using factory function.
        
        Args:
            key: Cache key
            factory: Async function to compute value if cache miss
            memory_ttl: TTL for memory cache (defaults to config)
            redis_ttl: TTL for Redis cache (defaults to config)
            correlation_id: Request correlation ID
            force_refresh: Force cache refresh
            
        Returns:
            Cached or computed value
        """
        start_time = time.time()
        
        # Use default TTLs if not specified
        memory_ttl = memory_ttl or self.config.memory_cache_ttl
        redis_ttl = redis_ttl or self.config.redis_default_ttl
        
        # Normalize cache key
        normalized_key = self._normalize_key(key)
        
        if not force_refresh:
            # Try L1 cache (memory)
            memory_result = await self._get_from_memory(normalized_key, correlation_id)
            if memory_result is not None:
                self._record_cache_hit(normalized_key, "memory", start_time, correlation_id)
                return memory_result
            
            # Try L2 cache (Redis)
            redis_result = await self._get_from_redis(normalized_key, correlation_id)
            if redis_result is not None:
                # Store in memory cache for faster future access
                self.memory_cache[normalized_key] = redis_result
                self._record_cache_hit(normalized_key, "redis", start_time, correlation_id)
                return redis_result
        
        # Cache miss - compute value
        self.logger.debug(
            "Cache miss - computing value",
            cache_key=normalized_key,
            force_refresh=force_refresh,
            correlation_id=correlation_id
        )
        
        try:
            value = await factory()
            
            # Store in both caches
            await self._store_in_caches(
                normalized_key, value, memory_ttl, redis_ttl, correlation_id
            )
            
            self._record_cache_miss(normalized_key, start_time, correlation_id)
            return value
            
        except Exception as e:
            self.logger.error(
                "Factory function failed",
                cache_key=normalized_key,
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise

    async def invalidate(
        self,
        pattern: str,
        correlation_id: str = "unknown"
    ) -> int:
        """
        Invalidate cache entries matching pattern.
        
        Args:
            pattern: Cache key pattern (supports wildcards)
            correlation_id: Request correlation ID
            
        Returns:
            Number of keys invalidated
        """
        count = 0
        
        # Invalidate from memory cache
        keys_to_remove = [
            key for key in self.memory_cache.keys()
            if self._matches_pattern(key, pattern)
        ]
        
        for key in keys_to_remove:
            del self.memory_cache[key]
            count += 1
        
        # Invalidate from Redis
        try:
            redis_keys = await self.redis_client.keys(pattern)
            if redis_keys:
                await self.redis_client.delete(*redis_keys)
                count += len(redis_keys)
                
        except Exception as e:
            self.logger.warning(
                "Redis invalidation failed",
                pattern=pattern,
                error=str(e),
                correlation_id=correlation_id
            )
        
        self.logger.info(
            "Cache invalidated",
            pattern=pattern,
            keys_invalidated=count,
            correlation_id=correlation_id
        )
        
        return count

    async def warm_cache(
        self,
        warm_data: Dict[str, Any],
        correlation_id: str = "unknown"
    ) -> int:
        """
        Warm cache with pre-computed data.
        
        Args:
            warm_data: Dictionary of key-value pairs to cache
            correlation_id: Request correlation ID
            
        Returns:
            Number of items cached
        """
        count = 0
        
        for key, value in warm_data.items():
            try:
                normalized_key = self._normalize_key(key)
                await self._store_in_caches(
                    normalized_key, value,
                    self.config.memory_cache_ttl,
                    self.config.redis_default_ttl,
                    correlation_id
                )
                count += 1
                
            except Exception as e:
                self.logger.warning(
                    "Cache warming failed for key",
                    cache_key=key,
                    error=str(e),
                    correlation_id=correlation_id
                )
        
        self.logger.info(
            "Cache warmed",
            items_cached=count,
            correlation_id=correlation_id
        )
        
        return count

    def generate_cache_key(
        self,
        prefix: str,
        *args,
        **kwargs
    ) -> str:
        """
        Generate stable cache key from arguments.
        
        Args:
            prefix: Key prefix
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Generated cache key
        """
        # Remove correlation_id from kwargs for consistent hashing
        clean_kwargs = {k: v for k, v in kwargs.items() if k != 'correlation_id'}
        
        # Create stable hash from arguments
        key_data = {
            "args": args,
            "kwargs": clean_kwargs
        }
        
        key_json = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()[:16]
        
        return f"{prefix}:{key_hash}"

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        memory_info = {
            "size": len(self.memory_cache),
            "maxsize": self.memory_cache.maxsize,
            "ttl": self.memory_cache.ttl,
            "hits": getattr(self.memory_cache, 'hits', 0),
            "misses": getattr(self.memory_cache, 'misses', 0)
        }
        
        redis_info = {}
        try:
            redis_info = await self.redis_client.info('memory')
        except Exception as e:
            self.logger.warning("Failed to get Redis info", error=str(e))
        
        recent_metrics = self.metrics[-100:]  # Last 100 operations
        total_operations = len(recent_metrics)
        hits = sum(1 for m in recent_metrics if m.hit)
        
        return {
            "memory_cache": memory_info,
            "redis_cache": redis_info,
            "recent_performance": {
                "total_operations": total_operations,
                "cache_hits": hits,
                "cache_misses": total_operations - hits,
                "hit_rate": hits / total_operations if total_operations > 0 else 0,
                "avg_access_time_ms": sum(m.access_time_ms for m in recent_metrics) / total_operations if total_operations > 0 else 0
            }
        }

    async def _get_from_memory(
        self,
        key: str,
        correlation_id: str
    ) -> Optional[Any]:
        """Get value from memory cache."""
        try:
            if key in self.memory_cache:
                value = self.memory_cache[key]
                self.logger.debug(
                    "Memory cache hit",
                    cache_key=key,
                    correlation_id=correlation_id
                )
                return value
        except Exception as e:
            self.logger.warning(
                "Memory cache access failed",
                cache_key=key,
                error=str(e),
                correlation_id=correlation_id
            )
        
        return None

    async def _get_from_redis(
        self,
        key: str,
        correlation_id: str
    ) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            cached_data = await self.redis_client.get(key)
            if cached_data:
                # Decompress if needed
                if self.config.enable_compression and cached_data.startswith(b'compressed:'):
                    import gzip
                    cached_data = gzip.decompress(cached_data[11:])  # Remove 'compressed:' prefix
                
                value = json.loads(cached_data)
                
                self.logger.debug(
                    "Redis cache hit",
                    cache_key=key,
                    value_size_bytes=len(cached_data),
                    correlation_id=correlation_id
                )
                
                return value
                
        except Exception as e:
            self.logger.warning(
                "Redis cache access failed",
                cache_key=key,
                error=str(e),
                correlation_id=correlation_id
            )
        
        return None

    async def _store_in_caches(
        self,
        key: str,
        value: Any,
        memory_ttl: int,
        redis_ttl: int,
        correlation_id: str
    ) -> None:
        """Store value in both memory and Redis caches."""
        if value is None:
            return
        
        # Store in memory cache
        try:
            self.memory_cache[key] = value
            
        except Exception as e:
            self.logger.warning(
                "Memory cache store failed",
                cache_key=key,
                error=str(e),
                correlation_id=correlation_id
            )
        
        # Store in Redis cache
        try:
            serialized_value = json.dumps(value, default=str).encode()
            
            # Compress if value is large
            if (self.config.enable_compression and 
                len(serialized_value) > self.config.compression_threshold):
                import gzip
                compressed_value = b'compressed:' + gzip.compress(serialized_value)
                serialized_value = compressed_value
            
            await self.redis_client.setex(key, redis_ttl, serialized_value)
            
            self.logger.debug(
                "Value cached successfully",
                cache_key=key,
                value_size_bytes=len(serialized_value),
                compressed=len(serialized_value) > self.config.compression_threshold,
                correlation_id=correlation_id
            )
            
        except Exception as e:
            self.logger.warning(
                "Redis cache store failed",
                cache_key=key,
                error=str(e),
                correlation_id=correlation_id
            )

    def _normalize_key(self, key: str) -> str:
        """Normalize cache key to ensure consistency."""
        # Remove invalid characters and limit length
        normalized = "".join(c for c in key if c.isalnum() or c in "._-:")
        
        if len(normalized) > self.config.max_key_length:
            # Hash long keys
            hash_suffix = hashlib.md5(key.encode()).hexdigest()[:8]
            normalized = normalized[:self.config.max_key_length-9] + "_" + hash_suffix
        
        return normalized

    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern (simple wildcard support)."""
        import re
        # Convert glob pattern to regex
        regex_pattern = pattern.replace("*", ".*").replace("?", ".")
        return bool(re.match(f"^{regex_pattern}$", key))

    def _record_cache_hit(
        self,
        key: str,
        cache_level: str,
        start_time: float,
        correlation_id: str
    ) -> None:
        """Record cache hit metrics."""
        access_time = (time.time() - start_time) * 1000  # ms
        
        metric = CacheMetrics(
            operation="get",
            cache_key=key,
            hit=True,
            cache_level=cache_level,
            access_time_ms=access_time,
            correlation_id=correlation_id
        )
        
        self.metrics.append(metric)
        
        # Keep only recent metrics
        if len(self.metrics) > 1000:
            self.metrics = self.metrics[-500:]

    def _record_cache_miss(
        self,
        key: str,
        start_time: float,
        correlation_id: str
    ) -> None:
        """Record cache miss metrics."""
        access_time = (time.time() - start_time) * 1000  # ms
        
        metric = CacheMetrics(
            operation="get",
            cache_key=key,
            hit=False,
            access_time_ms=access_time,
            correlation_id=correlation_id
        )
        
        self.metrics.append(metric)
        
        # Keep only recent metrics
        if len(self.metrics) > 1000:
            self.metrics = self.metrics[-500:]

    async def ping(self) -> bool:
        """Ping Redis to check connectivity."""
        try:
            if self.redis_client:
                await self.redis_client.ping()
                return True
            return False
        except Exception as e:
            self.logger.error("Redis ping failed", error=str(e))
            return False
    
    async def get_total_keys(self) -> int:
        """Get total number of keys in cache."""
        try:
            if self.redis_client:
                return await self.redis_client.dbsize()
            return len(self.memory_cache)
        except Exception as e:
            self.logger.error("Failed to get total keys", error=str(e))
            return 0

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        try:
            # Calculate hit/miss rates from metrics
            hits = sum(1 for m in self.metrics if m.hit)
            total_requests = len(self.metrics)
            hit_rate = hits / max(total_requests, 1)
            miss_rate = (total_requests - hits) / max(total_requests, 1)
            
            stats = {
                "total_keys": await self.get_total_keys(),
                "memory_usage_bytes": 0,
                "hit_rate": hit_rate,
                "miss_rate": miss_rate,
                "evictions": 0,  # Would need Redis INFO command for actual evictions
                "avg_ttl": 3600.0,  # Default 1 hour
                "ops_per_second": total_requests / max(1, 60)  # Approximate
            }
            
            if self.redis_client:
                try:
                    info = await self.redis_client.info("memory")
                    stats["memory_usage_bytes"] = info.get("used_memory", 0)
                except Exception:
                    pass
            
            return stats
        except Exception as e:
            self.logger.error("Failed to get cache stats", error=str(e))
            return {}


def cache_result(
    key_prefix: str,
    memory_ttl: int = 300,
    redis_ttl: int = 3600
):
    """
    Decorator for caching function results.
    
    Args:
        key_prefix: Prefix for cache key
        memory_ttl: Memory cache TTL in seconds
        redis_ttl: Redis cache TTL in seconds
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Get cache manager from app context or create default
            cache_manager = kwargs.get('cache_manager')
            if not cache_manager:
                # Use global cache manager or create default
                cache_manager = AsyncCacheManager(CacheConfiguration())
            
            # Generate cache key
            cache_key = cache_manager.generate_cache_key(key_prefix, *args, **kwargs)
            
            # Get correlation ID
            correlation_id = kwargs.get('correlation_id', 'unknown')
            
            async def factory():
                return await func(*args, **kwargs)
            
            return await cache_manager.get_or_set(
                cache_key,
                factory,
                memory_ttl=memory_ttl,
                redis_ttl=redis_ttl,
                correlation_id=correlation_id
            )
        
        return wrapper
    return decorator


# Example usage for AI responses
class AICacheManager:
    """Specialized cache manager for AI responses."""
    
    def __init__(self, cache_manager: AsyncCacheManager):
        self.cache_manager = cache_manager
        self.logger = structlog.get_logger(__name__)
    
    @cache_result("ai_layout", memory_ttl=600, redis_ttl=3600)
    async def cache_layout_generation(
        self,
        building_type: str,
        total_area_m2: float,
        room_requirements: Dict[str, Any],
        user_prompt: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """This would be called by the actual AI service."""
        # This is just the cache wrapper - actual AI call happens in service
        pass
    
    async def invalidate_ai_cache(
        self,
        building_type: Optional[str] = None,
        correlation_id: str = "unknown"
    ) -> int:
        """Invalidate AI-related cache entries."""
        if building_type:
            pattern = f"ai_layout:{building_type}:*"
        else:
            pattern = "ai_layout:*"
        
        return await self.cache_manager.invalidate(pattern, correlation_id)