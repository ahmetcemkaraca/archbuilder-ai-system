"""
Multi-level caching system for ArchBuilder.AI Cloud Server.

This module implements comprehensive caching strategies including:
- Memory cache (local)
- Redis cache (distributed)
- Cache key generation
- Cache invalidation
- Performance optimization

According to performance-optimization.instructions.md guidelines.
"""

import asyncio
import hashlib
import json
import pickle
import time
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass
import structlog
from enum import Enum

# Try to import redis, fallback if not available
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

logger = structlog.get_logger(__name__)

T = TypeVar('T')

class CacheLevel(Enum):
    """Cache levels for multi-tier caching"""
    MEMORY = "memory"
    REDIS = "redis"
    BOTH = "both"

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = 0
    size_bytes: int = 0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.last_accessed == 0:
            self.last_accessed = self.created_at
        if self.size_bytes == 0:
            self.size_bytes = len(pickle.dumps(self.value))
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def access(self):
        """Mark entry as accessed"""
        self.access_count += 1
        self.last_accessed = time.time()

class MemoryCache:
    """
    High-performance in-memory cache with LRU eviction and TTL support.
    
    Features:
    - LRU (Least Recently Used) eviction policy
    - TTL (Time To Live) support
    - Size-based eviction
    - Tag-based invalidation
    - Performance monitoring
    """
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []  # For LRU tracking
        self.total_size_bytes = 0
        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
        
        logger.info("MemoryCache initialized",
                   max_size=max_size,
                   max_memory_mb=max_memory_mb)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache"""
        if key not in self.cache:
            self.miss_count += 1
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if entry.is_expired():
            self._remove_entry(key)
            self.miss_count += 1
            return None
        
        # Update access statistics
        entry.access()
        self._update_access_order(key)
        self.hit_count += 1
        
        return entry.value
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None
    ):
        """Set value in memory cache with optional TTL and tags"""
        
        # Remove existing entry if present
        if key in self.cache:
            self._remove_entry(key)
        
        # Calculate expiration
        expires_at = None
        if ttl_seconds is not None:
            expires_at = time.time() + ttl_seconds
        
        # Create cache entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            expires_at=expires_at,
            tags=tags or []
        )
        
        # Check if we need to evict entries
        self._evict_if_needed(entry.size_bytes)
        
        # Add to cache
        self.cache[key] = entry
        self.access_order.append(key)
        self.total_size_bytes += entry.size_bytes
        
        logger.debug("Cache entry set",
                    key=key,
                    size_bytes=entry.size_bytes,
                    ttl_seconds=ttl_seconds,
                    tags=tags)
    
    def delete(self, key: str) -> bool:
        """Delete specific key from cache"""
        if key in self.cache:
            self._remove_entry(key)
            return True
        return False
    
    def delete_by_tags(self, tags: List[str]) -> int:
        """Delete all entries matching any of the specified tags"""
        deleted_count = 0
        keys_to_delete = []
        
        for key, entry in self.cache.items():
            if any(tag in entry.tags for tag in tags):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            self._remove_entry(key)
            deleted_count += 1
        
        logger.info("Cache entries deleted by tags",
                   tags=tags,
                   deleted_count=deleted_count)
        
        return deleted_count
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.access_order.clear()
        self.total_size_bytes = 0
        self.eviction_count = 0
        
        logger.info("Memory cache cleared")
    
    def _remove_entry(self, key: str):
        """Remove entry from cache"""
        if key in self.cache:
            entry = self.cache[key]
            del self.cache[key]
            
            if key in self.access_order:
                self.access_order.remove(key)
            
            self.total_size_bytes -= entry.size_bytes
    
    def _update_access_order(self, key: str):
        """Update LRU access order"""
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
    
    def _evict_if_needed(self, new_entry_size: int):
        """Evict entries if needed to make space"""
        # Check size limits
        while (len(self.cache) >= self.max_size or 
               self.total_size_bytes + new_entry_size > self.max_memory_bytes):
            
            if not self.access_order:
                break
                
            # Remove least recently used entry
            lru_key = self.access_order[0]
            self._remove_entry(lru_key)
            self.eviction_count += 1
        
        # Also remove expired entries
        self._cleanup_expired()
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if entry.expires_at and current_time > entry.expires_at:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_entry(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
        
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "total_entries": len(self.cache),
            "total_size_bytes": self.total_size_bytes,
            "total_size_mb": self.total_size_bytes / 1024 / 1024,
            "eviction_count": self.eviction_count,
            "max_size": self.max_size,
            "max_memory_mb": self.max_memory_bytes / 1024 / 1024
        }

class RedisCache:
    """
    Redis-based distributed cache with advanced features.
    
    Features:
    - Distributed caching across multiple instances
    - Automatic serialization/deserialization
    - Tag-based cache invalidation
    - TTL support
    - Performance monitoring
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.hit_count = 0
        self.miss_count = 0
        self.error_count = 0
        self.serialization_method = "json"  # or "pickle"
        
        if not REDIS_AVAILABLE or not redis_client:
            logger.warning("Redis not available, RedisCache will be disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("RedisCache initialized")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self.enabled:
            return None
            
        try:
            # Get value from Redis
            cached_data = await self.redis_client.get(f"cache:{key}")
            
            if cached_data is None:
                self.miss_count += 1
                return None
            
            # Deserialize value
            if self.serialization_method == "json":
                value = json.loads(cached_data)
            else:
                value = pickle.loads(cached_data)
            
            self.hit_count += 1
            return value
            
        except Exception as e:
            self.error_count += 1
            logger.error("Redis cache get error", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None
    ):
        """Set value in Redis cache with optional TTL and tags"""
        if not self.enabled:
            return
            
        try:
            # Serialize value
            if self.serialization_method == "json":
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = pickle.dumps(value)
            
            # Set in Redis
            cache_key = f"cache:{key}"
            if ttl_seconds:
                await self.redis_client.setex(cache_key, ttl_seconds, serialized_value)
            else:
                await self.redis_client.set(cache_key, serialized_value)
            
            # Store tags for invalidation
            if tags:
                for tag in tags:
                    tag_key = f"tag:{tag}"
                    await self.redis_client.sadd(tag_key, key)
                    if ttl_seconds:
                        await self.redis_client.expire(tag_key, ttl_seconds)
            
            logger.debug("Redis cache entry set",
                        key=key,
                        ttl_seconds=ttl_seconds,
                        tags=tags)
                        
        except Exception as e:
            self.error_count += 1
            logger.error("Redis cache set error", key=key, error=str(e))
    
    async def delete(self, key: str) -> bool:
        """Delete specific key from Redis cache"""
        if not self.enabled:
            return False
            
        try:
            result = await self.redis_client.delete(f"cache:{key}")
            return result > 0
            
        except Exception as e:
            self.error_count += 1
            logger.error("Redis cache delete error", key=key, error=str(e))
            return False
    
    async def delete_by_tags(self, tags: List[str]) -> int:
        """Delete all cached entries matching any of the specified tags"""
        if not self.enabled:
            return 0
            
        try:
            deleted_count = 0
            
            for tag in tags:
                tag_key = f"tag:{tag}"
                
                # Get all keys with this tag
                keys = await self.redis_client.smembers(tag_key)
                
                if keys:
                    # Delete cached entries
                    cache_keys = [f"cache:{key.decode() if isinstance(key, bytes) else key}" for key in keys]
                    await self.redis_client.delete(*cache_keys)
                    deleted_count += len(cache_keys)
                    
                    # Delete tag set
                    await self.redis_client.delete(tag_key)
            
            logger.info("Redis cache entries deleted by tags",
                       tags=tags,
                       deleted_count=deleted_count)
            
            return deleted_count
            
        except Exception as e:
            self.error_count += 1
            logger.error("Redis cache delete by tags error", tags=tags, error=str(e))
            return 0
    
    async def clear(self):
        """Clear all cache entries"""
        if not self.enabled:
            return
            
        try:
            # Delete all cache keys
            cache_keys = await self.redis_client.keys("cache:*")
            if cache_keys:
                await self.redis_client.delete(*cache_keys)
            
            # Delete all tag keys
            tag_keys = await self.redis_client.keys("tag:*")
            if tag_keys:
                await self.redis_client.delete(*tag_keys)
            
            logger.info("Redis cache cleared")
            
        except Exception as e:
            self.error_count += 1
            logger.error("Redis cache clear error", error=str(e))
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
        
        stats = {
            "enabled": self.enabled,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "error_count": self.error_count,
            "hit_rate": hit_rate
        }
        
        if self.enabled:
            try:
                # Get Redis info
                info = await self.redis_client.info("memory")
                stats.update({
                    "redis_memory_used": info.get("used_memory", 0),
                    "redis_memory_human": info.get("used_memory_human", "0B"),
                    "redis_keys_total": await self.redis_client.dbsize()
                })
            except Exception as e:
                logger.warning("Failed to get Redis stats", error=str(e))
        
        return stats

class AsyncCache:
    """
    Multi-level cache with memory and Redis layers.
    
    This is the main cache interface that coordinates between memory and Redis caches
    for optimal performance.
    
    Features:
    - Automatic fallback between cache levels
    - Smart cache level selection
    - Performance optimization
    - Unified cache interface
    """
    
    def __init__(
        self, 
        redis_client: Optional[redis.Redis] = None,
        memory_cache_size: int = 1000,
        memory_cache_mb: int = 100
    ):
        self.memory_cache = MemoryCache(memory_cache_size, memory_cache_mb)
        self.redis_cache = RedisCache(redis_client)
        
        logger.info("AsyncCache initialized",
                   memory_cache_enabled=True,
                   redis_cache_enabled=self.redis_cache.enabled)
    
    async def get(self, key: str, cache_level: CacheLevel = CacheLevel.BOTH) -> Optional[Any]:
        """
        Get value from cache with multi-level fallback.
        
        Strategy:
        1. Check memory cache first (fastest)
        2. If not found, check Redis cache
        3. If found in Redis, store in memory for next access
        """
        
        # Check memory cache first
        if cache_level in (CacheLevel.MEMORY, CacheLevel.BOTH):
            value = self.memory_cache.get(key)
            if value is not None:
                return value
        
        # Check Redis cache
        if cache_level in (CacheLevel.REDIS, CacheLevel.BOTH):
            value = await self.redis_cache.get(key)
            if value is not None:
                # Store in memory cache for faster next access
                if cache_level == CacheLevel.BOTH:
                    self.memory_cache.set(key, value, ttl_seconds=300)  # 5 minutes in memory
                return value
        
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None,
        cache_level: CacheLevel = CacheLevel.BOTH,
        tags: Optional[List[str]] = None
    ):
        """Set value in specified cache level(s)"""
        
        if cache_level in (CacheLevel.MEMORY, CacheLevel.BOTH):
            # For memory cache, use shorter TTL to prevent memory bloat
            memory_ttl = min(ttl_seconds or 3600, 3600)  # Max 1 hour in memory
            self.memory_cache.set(key, value, memory_ttl, tags)
        
        if cache_level in (CacheLevel.REDIS, CacheLevel.BOTH):
            await self.redis_cache.set(key, value, ttl_seconds, tags)
    
    async def delete(self, key: str, cache_level: CacheLevel = CacheLevel.BOTH) -> bool:
        """Delete key from specified cache level(s)"""
        memory_deleted = False
        redis_deleted = False
        
        if cache_level in (CacheLevel.MEMORY, CacheLevel.BOTH):
            memory_deleted = self.memory_cache.delete(key)
        
        if cache_level in (CacheLevel.REDIS, CacheLevel.BOTH):
            redis_deleted = await self.redis_cache.delete(key)
        
        return memory_deleted or redis_deleted
    
    async def delete_by_tags(self, tags: List[str], cache_level: CacheLevel = CacheLevel.BOTH) -> int:
        """Delete all entries matching tags from specified cache level(s)"""
        total_deleted = 0
        
        if cache_level in (CacheLevel.MEMORY, CacheLevel.BOTH):
            total_deleted += self.memory_cache.delete_by_tags(tags)
        
        if cache_level in (CacheLevel.REDIS, CacheLevel.BOTH):
            total_deleted += await self.redis_cache.delete_by_tags(tags)
        
        return total_deleted
    
    async def clear(self, cache_level: CacheLevel = CacheLevel.BOTH):
        """Clear specified cache level(s)"""
        if cache_level in (CacheLevel.MEMORY, CacheLevel.BOTH):
            self.memory_cache.clear()
        
        if cache_level in (CacheLevel.REDIS, CacheLevel.BOTH):
            await self.redis_cache.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        memory_stats = self.memory_cache.get_stats()
        redis_stats = await self.redis_cache.get_stats()
        
        return {
            "memory_cache": memory_stats,
            "redis_cache": redis_stats,
            "timestamp": datetime.utcnow().isoformat()
        }

class CacheKeyGenerator:
    """
    Smart cache key generation with consistent hashing.
    
    Features:
    - Deterministic key generation
    - Parameter normalization
    - Collision avoidance
    - Readable key format
    """
    
    @staticmethod
    def generate_key(
        prefix: str,
        *args,
        **kwargs
    ) -> str:
        """
        Generate a consistent cache key from parameters.
        
        Args:
            prefix: Key prefix (e.g., "user", "ai_layout", "document")
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Formatted cache key string
        """
        
        # Normalize arguments
        normalized_args = []
        for arg in args:
            if isinstance(arg, (dict, list)):
                normalized_args.append(json.dumps(arg, sort_keys=True))
            else:
                normalized_args.append(str(arg))
        
        normalized_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, (dict, list)):
                normalized_kwargs[key] = json.dumps(value, sort_keys=True)
            else:
                normalized_kwargs[key] = str(value)
        
        # Create hash input
        hash_input = "|".join(normalized_args)
        if normalized_kwargs:
            sorted_kwargs = sorted(normalized_kwargs.items())
            kwargs_str = "|".join(f"{k}={v}" for k, v in sorted_kwargs)
            hash_input = f"{hash_input}|{kwargs_str}"
        
        # Generate hash
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        
        # Format key
        return f"{prefix}:{hash_value}"
    
    @staticmethod
    def user_key(user_id: str, action: str, **params) -> str:
        """Generate user-specific cache key"""
        return CacheKeyGenerator.generate_key("user", user_id, action, **params)
    
    @staticmethod
    def ai_key(operation: str, **params) -> str:
        """Generate AI operation cache key"""
        return CacheKeyGenerator.generate_key("ai", operation, **params)
    
    @staticmethod
    def document_key(document_id: str, operation: str, **params) -> str:
        """Generate document processing cache key"""
        return CacheKeyGenerator.generate_key("doc", document_id, operation, **params)
    
    @staticmethod
    def layout_key(building_type: str, area: float, requirements: Dict, **params) -> str:
        """Generate layout generation cache key"""
        return CacheKeyGenerator.generate_key("layout", building_type, area, requirements, **params)

def cached(
    ttl_seconds: Optional[int] = 3600,
    cache_level: CacheLevel = CacheLevel.BOTH,
    tags: Optional[List[str]] = None,
    key_prefix: Optional[str] = None
):
    """
    Decorator for caching function results.
    
    Usage:
        @cached(ttl_seconds=300, tags=["user_data"])
        async def get_user_profile(user_id: str):
            return await database.get_user(user_id)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = CacheKeyGenerator.generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache.get(cache_key, cache_level)
            if cached_result is not None:
                logger.debug("Cache hit", function=func.__name__, key=cache_key)
                return cached_result
            
            # Execute function
            logger.debug("Cache miss, executing function", function=func.__name__, key=cache_key)
            result = await func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                await cache.set(cache_key, result, ttl_seconds, cache_level, tags)
                logger.debug("Result cached", function=func.__name__, key=cache_key)
            
            return result
        return wrapper
    return decorator

# Global cache instance
cache: Optional[AsyncCache] = None

def initialize_cache(redis_client: Optional[redis.Redis] = None):
    """Initialize global cache instance"""
    global cache
    cache = AsyncCache(redis_client)
    logger.info("Global cache initialized")

def get_cache() -> AsyncCache:
    """Get global cache instance"""
    if cache is None:
        raise RuntimeError("Cache not initialized. Call initialize_cache() first.")
    return cache