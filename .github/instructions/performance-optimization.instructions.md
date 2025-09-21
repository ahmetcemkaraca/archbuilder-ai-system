---
applyTo: "src/revit-plugin/**/*.cs,src/mcp-server/**/*.py,**/*.ts,**/*.tsx,**/*.js,**/*.jsx"
description: Performance Optimization Standards — monitoring, profiling, caching strategies, and resource management across the system.
---
As Performance Optimization Developer:
- Implement comprehensive performance monitoring across all system components
- Design intelligent caching strategies for AI responses and Revit data
- Optimize database queries and API calls for minimal latency
- Establish realistic performance budgets and monitoring alerts
- Create efficient resource management patterns for memory and CPU usage
- **NO C# AI PROCESSING**: Performance optimization focused on C# plugin and Python MCP server separation

## Performance Targets (Revised)
- **Simple Queries**: <2s (Revit element queries, project metadata)
- **AI Operations**: <30s (layout generation, document processing) 
- **Document OCR**: <2min (per document, with progress indicators)
- **Memory Usage**: <500MB for typical residential projects
- **Concurrent Users**: Support 10+ architects simultaneously

## Realistic Resource Management

### C# Performance Monitoring with MiniProfiler and Metrics
```csharp
// Startup.cs - Performance monitoring setup
public void ConfigureServices(IServiceCollection services)
{
    // Add MiniProfiler for detailed performance profiling
    services.AddMiniProfiler(options =>
    {
        options.RouteBasePath = "/profiler";
        options.EnableServerTimingHeader = true;
        options.IgnorePath("/health");
        options.IgnorePath("/metrics");
    }).AddEntityFramework();
    
    // Add Application Insights for production monitoring
    services.AddApplicationInsightsTelemetry();
    
    // Add custom metrics collection
    services.AddSingleton<IMetricsCollector, MetricsCollector>();
    services.AddSingleton<IPerformanceTracker, PerformanceTracker>();
    
    // Add memory caching
    services.AddMemoryCache(options =>
    {
        options.SizeLimit = 100_000; // Limit cache size
        options.CompactionPercentage = 0.25; // Compact when 25% full
    });
    
    // Add distributed caching (Redis)
    services.AddStackExchangeRedisCache(options =>
    {
        options.Configuration = "localhost:6379";
        options.InstanceName = "RevitAutoPlan";
    });
    
    // Add HTTP client with policies
    services.AddHttpClient<AIModelClient>(client =>
    {
        client.Timeout = TimeSpan.FromSeconds(30);
        client.DefaultRequestHeaders.Add("User-Agent", "RevitAutoPlan/1.0");
    })
    .AddPolicyHandler(GetRetryPolicy())
    .AddPolicyHandler(GetCircuitBreakerPolicy())
    .AddPolicyHandler(GetTimeoutPolicy());
}

public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
{
    // Add performance monitoring middleware
    app.UseMiddleware<PerformanceMonitoringMiddleware>();
    
    if (env.IsDevelopment())
    {
        app.UseMiniProfiler();
    }
    
    // Add response compression
    app.UseResponseCompression();
    
    // Add response caching
    app.UseResponseCaching();
}
```

### Performance Tracking Service
```csharp
public interface IPerformanceTracker
{
    IDisposable TrackOperation(string operationName, string correlationId, Dictionary<string, object> tags = null);
    void RecordMetric(string metricName, double value, Dictionary<string, object> tags = null);
    Task<PerformanceReport> GenerateReportAsync(DateTime startTime, DateTime endTime);
}

public class PerformanceTracker : IPerformanceTracker
{
    private readonly ILogger<PerformanceTracker> _logger;
    private readonly IMetricsCollector _metricsCollector;
    private readonly IMemoryCache _cache;
    
    public PerformanceTracker(
        ILogger<PerformanceTracker> logger,
        IMetricsCollector metricsCollector,
        IMemoryCache cache)
    {
        _logger = logger;
        _metricsCollector = metricsCollector;
        _cache = cache;
    }
    
    public IDisposable TrackOperation(
        string operationName, 
        string correlationId, 
        Dictionary<string, object> tags = null)
    {
        return new OperationTracker(operationName, correlationId, tags, _logger, _metricsCollector);
    }
    
    public void RecordMetric(string metricName, double value, Dictionary<string, object> tags = null)
    {
        _metricsCollector.RecordValue(metricName, value, tags);
        
        _logger.LogDebug("Performance metric recorded",
            metric_name: metricName,
            value: value,
            tags: tags);
    }
    
    public async Task<PerformanceReport> GenerateReportAsync(DateTime startTime, DateTime endTime)
    {
        var cacheKey = $"perf_report_{startTime:yyyyMMddHH}_{endTime:yyyyMMddHH}";
        
        if (_cache.TryGetValue(cacheKey, out PerformanceReport cachedReport))
        {
            return cachedReport;
        }
        
        var report = await _metricsCollector.GenerateReportAsync(startTime, endTime);
        
        _cache.Set(cacheKey, report, TimeSpan.FromMinutes(15));
        
        return report;
    }
}

public class OperationTracker : IDisposable
{
    private readonly string _operationName;
    private readonly string _correlationId;
    private readonly Dictionary<string, object> _tags;
    private readonly ILogger _logger;
    private readonly IMetricsCollector _metricsCollector;
    private readonly Stopwatch _stopwatch;
    private readonly long _startMemory;
    private bool _disposed = false;
    
    public OperationTracker(
        string operationName,
        string correlationId,
        Dictionary<string, object> tags,
        ILogger logger,
        IMetricsCollector metricsCollector)
    {
        _operationName = operationName;
        _correlationId = correlationId;
        _tags = tags ?? new Dictionary<string, object>();
        _logger = logger;
        _metricsCollector = metricsCollector;
        _stopwatch = Stopwatch.StartNew();
        _startMemory = GC.GetTotalMemory(false);
        
        _logger.LogDebug("Operation started",
            operation_name: _operationName,
            correlation_id: _correlationId,
            start_memory_bytes: _startMemory);
    }
    
    public void Dispose()
    {
        if (_disposed) return;
        
        _stopwatch.Stop();
        var endMemory = GC.GetTotalMemory(false);
        var memoryDelta = endMemory - _startMemory;
        
        var allTags = new Dictionary<string, object>(_tags)
        {
            ["operation"] = _operationName,
            ["correlation_id"] = _correlationId
        };
        
        // Record performance metrics
        _metricsCollector.RecordValue("operation_duration_ms", _stopwatch.ElapsedMilliseconds, allTags);
        _metricsCollector.RecordValue("operation_memory_delta_bytes", memoryDelta, allTags);
        
        _logger.LogInformation("Operation completed",
            operation_name: _operationName,
            correlation_id: _correlationId,
            elapsed_ms: _stopwatch.ElapsedMilliseconds,
            memory_delta_bytes: memoryDelta,
            tags: _tags);
        
        _disposed = true;
    }
}
```

### AI Response Caching Strategy
```csharp
public class AIResponseCache : IAIResponseCache
{
    private readonly IDistributedCache _distributedCache;
    private readonly IMemoryCache _memoryCache;
    private readonly ILogger<AIResponseCache> _logger;
    private readonly ICacheKeyGenerator _keyGenerator;
    
    public AIResponseCache(
        IDistributedCache distributedCache,
        IMemoryCache memoryCache,
        ILogger<AIResponseCache> logger,
        ICacheKeyGenerator keyGenerator)
    {
        _distributedCache = distributedCache;
        _memoryCache = memoryCache;
        _logger = logger;
        _keyGenerator = keyGenerator;
    }
    
    public async Task<T> GetOrCreateAsync<T>(
        string operation,
        object request,
        Func<Task<T>> factory,
        TimeSpan? localCacheExpiry = null,
        TimeSpan? distributedCacheExpiry = null,
        string correlationId = null) where T : class
    {
        var cacheKey = _keyGenerator.GenerateKey(operation, request);
        var localExpiry = localCacheExpiry ?? TimeSpan.FromMinutes(5);
        var distributedExpiry = distributedCacheExpiry ?? TimeSpan.FromHours(1);
        
        using var tracker = TrackCacheOperation(operation, cacheKey, correlationId);
        
        // Check L1 cache (memory)
        if (_memoryCache.TryGetValue(cacheKey, out T cachedValue))
        {
            tracker.SetCacheHit("memory");
            _logger.LogDebug("Cache hit in memory cache",
                cache_key: cacheKey,
                operation: operation,
                correlation_id: correlationId);
            return cachedValue;
        }
        
        // Check L2 cache (distributed)
        var distributedCachedBytes = await _distributedCache.GetAsync(cacheKey);
        if (distributedCachedBytes != null)
        {
            try
            {
                var distributedCachedValue = JsonSerializer.Deserialize<T>(distributedCachedBytes);
                
                // Store in memory cache for faster access
                _memoryCache.Set(cacheKey, distributedCachedValue, localExpiry);
                
                tracker.SetCacheHit("distributed");
                _logger.LogDebug("Cache hit in distributed cache",
                    cache_key: cacheKey,
                    operation: operation,
                    correlation_id: correlationId);
                
                return distributedCachedValue;
            }
            catch (JsonException ex)
            {
                _logger.LogWarning(ex, "Failed to deserialize cached value",
                    cache_key: cacheKey,
                    operation: operation,
                    correlation_id: correlationId);
            }
        }
        
        // Cache miss - execute factory
        tracker.SetCacheMiss();
        _logger.LogDebug("Cache miss - executing factory",
            cache_key: cacheKey,
            operation: operation,
            correlation_id: correlationId);
        
        var value = await factory();
        
        if (value != null)
        {
            // Store in both caches
            var serializedValue = JsonSerializer.SerializeToUtf8Bytes(value);
            
            await _distributedCache.SetAsync(cacheKey, serializedValue, 
                new DistributedCacheEntryOptions
                {
                    AbsoluteExpirationRelativeToNow = distributedExpiry
                });
            
            _memoryCache.Set(cacheKey, value, localExpiry);
            
            _logger.LogDebug("Value cached successfully",
                cache_key: cacheKey,
                operation: operation,
                serialized_size_bytes: serializedValue.Length,
                correlation_id: correlationId);
        }
        
        return value;
    }
    
    private ICacheOperationTracker TrackCacheOperation(
        string operation, 
        string cacheKey, 
        string correlationId)
    {
        return new CacheOperationTracker(operation, cacheKey, correlationId, _logger);
    }
}

public interface ICacheKeyGenerator
{
    string GenerateKey(string operation, object request);
}

public class CacheKeyGenerator : ICacheKeyGenerator
{
    public string GenerateKey(string operation, object request)
    {
        var requestHash = ComputeStableHash(request);
        return $"{operation}:{requestHash}";
    }
    
    private string ComputeStableHash(object obj)
    {
        // Create stable hash for caching (order-independent)
        var json = JsonSerializer.Serialize(obj, new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
        });
        
        using var sha256 = SHA256.Create();
        var hashBytes = sha256.ComputeHash(Encoding.UTF8.GetBytes(json));
        return Convert.ToBase64String(hashBytes)[..16]; // First 16 chars for shorter keys
    }
}
```

### Database Query Optimization
```csharp
public class OptimizedProjectRepository : IProjectRepository
{
    private readonly AutoPlanContext _context;
    private readonly IMemoryCache _cache;
    private readonly ILogger<OptimizedProjectRepository> _logger;
    
    public OptimizedProjectRepository(
        AutoPlanContext context,
        IMemoryCache cache,
        ILogger<OptimizedProjectRepository> logger)
    {
        _context = context;
        _cache = cache;
        _logger = logger;
    }
    
    public async Task<Project> GetProjectWithLayoutsAsync(
        int projectId, 
        string correlationId,
        CancellationToken cancellationToken = default)
    {
        var cacheKey = $"project_with_layouts_{projectId}";
        
        if (_cache.TryGetValue(cacheKey, out Project cachedProject))
        {
            _logger.LogDebug("Project loaded from cache",
                project_id: projectId,
                correlation_id: correlationId);
            return cachedProject;
        }
        
        using var activity = Activity.StartActivity("GetProjectWithLayouts");
        activity?.SetTag("project.id", projectId.ToString());
        
        var stopwatch = Stopwatch.StartNew();
        
        try
        {
            // Optimized query with includes and split queries
            var project = await _context.Projects
                .AsSplitQuery() // Avoid cartesian explosion
                .Include(p => p.Layouts.OrderByDescending(l => l.CreatedAt).Take(10))
                    .ThenInclude(l => l.Rooms)
                .Include(p => p.Layouts)
                    .ThenInclude(l => l.Walls)
                .Include(p => p.BuildingInfo)
                .Where(p => p.Id == projectId)
                .AsNoTracking() // Read-only for better performance
                .FirstOrDefaultAsync(cancellationToken);
            
            stopwatch.Stop();
            
            if (project != null)
            {
                // Cache for 10 minutes
                _cache.Set(cacheKey, project, TimeSpan.FromMinutes(10));
                
                _logger.LogInformation("Project loaded from database",
                    project_id: projectId,
                    layout_count: project.Layouts?.Count ?? 0,
                    room_count: project.Layouts?.SelectMany(l => l.Rooms).Count() ?? 0,
                    elapsed_ms: stopwatch.ElapsedMilliseconds,
                    correlation_id: correlationId);
            }
            else
            {
                _logger.LogWarning("Project not found",
                    project_id: projectId,
                    elapsed_ms: stopwatch.ElapsedMilliseconds,
                    correlation_id: correlationId);
            }
            
            return project;
        }
        catch (Exception ex)
        {
            stopwatch.Stop();
            _logger.LogError(ex, "Failed to load project",
                project_id: projectId,
                elapsed_ms: stopwatch.ElapsedMilliseconds,
                correlation_id: correlationId);
            throw;
        }
    }
    
    public async Task<PagedResult<ProjectSummary>> GetProjectSummariesAsync(
        ProjectSearchCriteria criteria,
        string correlationId,
        CancellationToken cancellationToken = default)
    {
        using var activity = Activity.StartActivity("GetProjectSummaries");
        
        var stopwatch = Stopwatch.StartNew();
        
        try
        {
            var query = _context.Projects.AsNoTracking();
            
            // Apply filters
            if (!string.IsNullOrEmpty(criteria.SearchTerm))
            {
                query = query.Where(p => 
                    EF.Functions.Like(p.Name, $"%{criteria.SearchTerm}%") ||
                    EF.Functions.Like(p.Description, $"%{criteria.SearchTerm}%"));
            }
            
            if (criteria.BuildingType.HasValue)
            {
                query = query.Where(p => p.BuildingType == criteria.BuildingType);
            }
            
            if (criteria.CreatedAfter.HasValue)
            {
                query = query.Where(p => p.CreatedAt >= criteria.CreatedAfter);
            }
            
            // Count total (use separate query for better performance)
            var totalCount = await query.CountAsync(cancellationToken);
            
            // Apply paging and projection
            var projects = await query
                .OrderByDescending(p => p.CreatedAt)
                .Skip(criteria.Skip)
                .Take(criteria.Take)
                .Select(p => new ProjectSummary
                {
                    Id = p.Id,
                    Name = p.Name,
                    BuildingType = p.BuildingType,
                    TotalAreaM2 = p.BuildingInfo.TotalAreaM2,
                    CreatedAt = p.CreatedAt,
                    LastModifiedAt = p.LastModifiedAt,
                    LayoutCount = p.Layouts.Count(),
                    Status = p.Status
                })
                .ToListAsync(cancellationToken);
            
            stopwatch.Stop();
            
            _logger.LogInformation("Project summaries loaded",
                result_count: projects.Count,
                total_count: totalCount,
                has_filters: !string.IsNullOrEmpty(criteria.SearchTerm) || criteria.BuildingType.HasValue,
                elapsed_ms: stopwatch.ElapsedMilliseconds,
                correlation_id: correlationId);
            
            return new PagedResult<ProjectSummary>
            {
                Items = projects,
                TotalCount = totalCount,
                Page = criteria.Page,
                PageSize = criteria.PageSize
            };
        }
        catch (Exception ex)
        {
            stopwatch.Stop();
            _logger.LogError(ex, "Failed to load project summaries",
                elapsed_ms: stopwatch.ElapsedMilliseconds,
                correlation_id: correlationId);
            throw;
        }
    }
}
```

## Python Performance Optimization

### Async Performance Monitoring
```python
"""Performance monitoring and optimization for Python services."""

import asyncio
import time
import psutil
import structlog
from typing import Any, Dict, Optional, Callable, TypeVar, Awaitable
from functools import wraps
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
import cachetools
import redis.asyncio as redis
import json
import hashlib

T = TypeVar('T')

@dataclass
class PerformanceMetrics:
    """Performance metrics container."""
    operation_name: str
    correlation_id: str
    duration_ms: float
    memory_used_mb: float
    cpu_percent: float
    cache_hit: bool = False
    cache_source: Optional[str] = None
    error: Optional[str] = None

class PerformanceTracker:
    """Async performance tracking service."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.logger = structlog.get_logger(__name__)
        self.redis_client = redis_client
        self.process = psutil.Process()
        
        # Local memory cache (LRU with TTL)
        self.memory_cache = cachetools.TTLCache(maxsize=1000, ttl=300)  # 5 minutes
        
    @asynccontextmanager
    async def track_operation(
        self,
        operation_name: str,
        correlation_id: str,
        additional_tags: Optional[Dict[str, Any]] = None
    ):
        """Context manager for tracking operation performance."""
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = self.process.cpu_percent()
        
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            correlation_id=correlation_id,
            duration_ms=0,
            memory_used_mb=start_memory,
            cpu_percent=start_cpu
        )
        
        self.logger.debug(
            "Operation started",
            operation=operation_name,
            correlation_id=correlation_id,
            start_memory_mb=start_memory,
            additional_tags=additional_tags or {}
        )
        
        try:
            yield metrics
            
        except Exception as e:
            metrics.error = str(e)
            self.logger.error(
                "Operation failed",
                operation=operation_name,
                correlation_id=correlation_id,
                error=str(e),
                exc_info=True
            )
            raise
            
        finally:
            end_time = time.time()
            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            end_cpu = self.process.cpu_percent()
            
            metrics.duration_ms = (end_time - start_time) * 1000
            metrics.memory_used_mb = end_memory - start_memory
            metrics.cpu_percent = max(end_cpu - start_cpu, 0)
            
            # Log performance metrics
            self.logger.info(
                "Operation completed",
                **asdict(metrics),
                additional_tags=additional_tags or {}
            )
            
            # Store metrics for analysis
            await self._store_metrics(metrics, additional_tags)
    
    async def _store_metrics(
        self,
        metrics: PerformanceMetrics,
        additional_tags: Optional[Dict[str, Any]] = None
    ):
        """Store metrics for later analysis."""
        if not self.redis_client:
            return
        
        try:
            metrics_data = {
                **asdict(metrics),
                "timestamp": time.time(),
                "additional_tags": additional_tags or {}
            }
            
            # Store in Redis time series (keep for 24 hours)
            key = f"metrics:{metrics.operation_name}:{int(time.time())}"
            await self.redis_client.setex(
                key,
                86400,  # 24 hours
                json.dumps(metrics_data)
            )
            
        except Exception as e:
            self.logger.warning(
                "Failed to store metrics",
                error=str(e),
                correlation_id=metrics.correlation_id
            )

def track_performance(operation_name: str):
    """Decorator for tracking function performance."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Try to get correlation_id from kwargs
            correlation_id = kwargs.get('correlation_id', 'unknown')
            
            tracker = PerformanceTracker()
            
            async with tracker.track_operation(operation_name, correlation_id):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator

class AsyncCache:
    """High-performance async caching with multiple levels."""
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        memory_cache_size: int = 1000,
        memory_cache_ttl: int = 300
    ):
        self.redis_client = redis_client
        self.memory_cache = cachetools.TTLCache(
            maxsize=memory_cache_size,
            ttl=memory_cache_ttl
        )
        self.logger = structlog.get_logger(__name__)
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        memory_ttl: int = 300,
        redis_ttl: int = 3600,
        correlation_id: str = "unknown"
    ) -> T:
        """Get value from cache or compute using factory."""
        
        # Check memory cache first (L1)
        if key in self.memory_cache:
            self.logger.debug(
                "Cache hit - memory",
                cache_key=key,
                correlation_id=correlation_id
            )
            return self.memory_cache[key]
        
        # Check Redis cache (L2)
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    value = json.loads(cached_data)
                    
                    # Store in memory cache for faster access
                    self.memory_cache[key] = value
                    
                    self.logger.debug(
                        "Cache hit - redis",
                        cache_key=key,
                        correlation_id=correlation_id
                    )
                    return value
                    
            except Exception as e:
                self.logger.warning(
                    "Redis cache read failed",
                    cache_key=key,
                    error=str(e),
                    correlation_id=correlation_id
                )
        
        # Cache miss - compute value
        self.logger.debug(
            "Cache miss - computing value",
            cache_key=key,
            correlation_id=correlation_id
        )
        
        start_time = time.time()
        value = await factory()
        compute_time = (time.time() - start_time) * 1000
        
        self.logger.info(
            "Value computed and cached",
            cache_key=key,
            compute_time_ms=compute_time,
            correlation_id=correlation_id
        )
        
        # Store in both caches
        self.memory_cache[key] = value
        
        if self.redis_client and value is not None:
            try:
                await self.redis_client.setex(
                    key,
                    redis_ttl,
                    json.dumps(value, default=str)  # Handle datetime, etc.
                )
            except Exception as e:
                self.logger.warning(
                    "Redis cache write failed",
                    cache_key=key,
                    error=str(e),
                    correlation_id=correlation_id
                )
        
        return value
    
    def generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate stable cache key from arguments."""
        # Create stable hash from arguments
        key_data = {
            "args": args,
            "kwargs": {k: v for k, v in kwargs.items() if k != 'correlation_id'}
        }
        
        key_json = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_json.encode()).hexdigest()[:16]
        
        return f"{prefix}:{key_hash}"

# Example usage in AI service
class OptimizedAILayoutService:
    """AI Layout Service with performance optimizations."""
    
    def __init__(self, ai_client, cache: AsyncCache, tracker: PerformanceTracker):
        self.ai_client = ai_client
        self.cache = cache
        self.tracker = tracker
        self.logger = structlog.get_logger(__name__)
    
    @track_performance("generate_layout")
    async def generate_layout(
        self,
        request: Dict[str, Any],
        correlation_id: str
    ) -> Dict[str, Any]:
        """Generate layout with caching and performance tracking."""
        
        # Generate cache key from request
        cache_key = self.cache.generate_cache_key(
            "ai_layout",
            request.get("building_type"),
            request.get("total_area_m2"),
            request.get("room_requirements"),
            # Hash user prompt for cache key
            hashlib.md5(request.get("user_prompt", "").encode()).hexdigest()[:8]
        )
        
        async def compute_layout():
            """Factory function for cache miss."""
            async with self.tracker.track_operation(
                "ai_model_call",
                correlation_id,
                {"cache_key": cache_key}
            ) as metrics:
                
                result = await self.ai_client.generate_layout(request)
                
                # Add performance metadata
                result["performance"] = {
                    "generation_time_ms": metrics.duration_ms,
                    "cache_key": cache_key,
                    "cached": False
                }
                
                return result
        
        # Get from cache or compute
        result = await self.cache.get_or_set(
            cache_key,
            compute_layout,
            memory_ttl=600,  # 10 minutes in memory
            redis_ttl=3600,  # 1 hour in Redis
            correlation_id=correlation_id
        )
        
        # Mark as cached if it came from cache
        if "performance" in result and not result["performance"]["cached"]:
            result["performance"]["cached"] = True
            
        return result
```

### Resource Management and Connection Pooling
```python
class OptimizedDatabaseService:
    """Database service with connection pooling and query optimization."""
    
    def __init__(self, database_url: str, pool_size: int = 20):
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,  # Recycle connections every hour
            echo=False  # Set to True for SQL debugging
        )
        self.async_session = async_sessionmaker(
            self.engine,
            expire_on_commit=False
        )
        self.logger = structlog.get_logger(__name__)
    
    @asynccontextmanager
    async def get_session(self, correlation_id: str = "unknown"):
        """Get database session with performance tracking."""
        async with self.async_session() as session:
            start_time = time.time()
            try:
                yield session
                await session.commit()
                
                duration = (time.time() - start_time) * 1000
                self.logger.debug(
                    "Database session completed",
                    duration_ms=duration,
                    correlation_id=correlation_id
                )
                
            except Exception as e:
                await session.rollback()
                duration = (time.time() - start_time) * 1000
                
                self.logger.error(
                    "Database session failed",
                    duration_ms=duration,
                    error=str(e),
                    correlation_id=correlation_id,
                    exc_info=True
                )
                raise
    
    async def get_project_with_layouts(
        self,
        project_id: int,
        correlation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get project with optimized query and caching."""
        
        cache = AsyncCache()
        cache_key = f"project_layouts:{project_id}"
        
        async def load_from_db():
            async with self.get_session(correlation_id) as session:
                # Use optimized query with selectinload
                result = await session.execute(
                    select(Project)
                    .options(
                        selectinload(Project.layouts)
                        .selectinload(Layout.rooms),
                        selectinload(Project.layouts)
                        .selectinload(Layout.walls),
                        selectinload(Project.building_info)
                    )
                    .where(Project.id == project_id)
                )
                
                project = result.scalar_one_or_none()
                
                if project:
                    return {
                        "id": project.id,
                        "name": project.name,
                        "building_type": project.building_type,
                        "layouts": [
                            {
                                "id": layout.id,
                                "name": layout.name,
                                "created_at": layout.created_at.isoformat(),
                                "room_count": len(layout.rooms),
                                "wall_count": len(layout.walls)
                            }
                            for layout in project.layouts[:10]  # Limit to recent 10
                        ],
                        "total_area_m2": project.building_info.total_area_m2
                    }
                
                return None
        
        return await cache.get_or_set(
            cache_key,
            load_from_db,
            memory_ttl=300,  # 5 minutes
            redis_ttl=1800,  # 30 minutes
            correlation_id=correlation_id
        )
```

Always implement multi-level caching, track performance metrics, optimize database queries, use connection pooling, and establish performance budgets for all operations.
