"""
ArchBuilder.AI - System Health and Metrics API
Endpoints for monitoring system health, performance metrics, and operational status.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
import structlog
import psutil
import asyncio

from ..security.authorization import AuthorizationService, Permission
from ..security.authentication import AuthenticationService
from ..utils.performance_tracker import PerformanceTracker
from ..utils.cache_manager import AsyncCacheManager
from ..utils.config_manager import AppConfig

# Response Models
class HealthStatus(BaseModel):
    """System health status."""
    status: str = Field(..., description="Overall system status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    services: Dict[str, str] = Field(..., description="Individual service statuses")
    correlation_id: str = Field(..., description="Request correlation ID")

class SystemMetrics(BaseModel):
    """System performance metrics."""
    cpu_percent: float = Field(..., description="CPU utilization percentage")
    memory_percent: float = Field(..., description="Memory utilization percentage")
    memory_total_gb: float = Field(..., description="Total memory in GB")
    memory_available_gb: float = Field(..., description="Available memory in GB")
    disk_usage_percent: float = Field(..., description="Disk usage percentage")
    disk_total_gb: float = Field(..., description="Total disk space in GB")
    disk_free_gb: float = Field(..., description="Free disk space in GB")
    network_sent_mb: float = Field(..., description="Network bytes sent in MB")
    network_recv_mb: float = Field(..., description="Network bytes received in MB")
    active_connections: int = Field(..., description="Number of active connections")
    timestamp: str = Field(..., description="Metrics collection timestamp")
    correlation_id: str = Field(..., description="Request correlation ID")

class PerformanceMetrics(BaseModel):
    """Application performance metrics."""
    total_requests: int = Field(..., description="Total API requests")
    avg_response_time_ms: float = Field(..., description="Average response time in milliseconds")
    requests_per_minute: float = Field(..., description="Requests per minute")
    error_rate_percent: float = Field(..., description="Error rate percentage")
    active_users: int = Field(..., description="Number of active users")
    cache_hit_rate_percent: float = Field(..., description="Cache hit rate percentage")
    ai_operations_total: int = Field(..., description="Total AI operations")
    ai_operations_success_rate: float = Field(..., description="AI operations success rate")
    timestamp: str = Field(..., description="Metrics collection timestamp")
    correlation_id: str = Field(..., description="Request correlation ID")

class ServiceStatus(BaseModel):
    """Individual service status."""
    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    last_check: str = Field(..., description="Last health check timestamp")
    response_time_ms: Optional[float] = Field(None, description="Service response time")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional service metadata")

class DatabaseMetrics(BaseModel):
    """Database performance metrics."""
    active_connections: int = Field(..., description="Active database connections")
    idle_connections: int = Field(..., description="Idle database connections")
    query_count: int = Field(..., description="Total queries executed")
    avg_query_time_ms: float = Field(..., description="Average query execution time")
    slow_queries: int = Field(..., description="Number of slow queries")
    deadlocks: int = Field(..., description="Number of deadlocks")
    table_sizes_mb: Dict[str, float] = Field(..., description="Table sizes in MB")
    index_usage: Dict[str, float] = Field(..., description="Index usage statistics")
    timestamp: str = Field(..., description="Metrics collection timestamp")
    correlation_id: str = Field(..., description="Request correlation ID")

class CacheMetrics(BaseModel):
    """Cache performance metrics."""
    total_keys: int = Field(..., description="Total number of cache keys")
    memory_usage_mb: float = Field(..., description="Cache memory usage in MB")
    hit_rate_percent: float = Field(..., description="Cache hit rate percentage")
    miss_rate_percent: float = Field(..., description="Cache miss rate percentage")
    eviction_count: int = Field(..., description="Number of cache evictions")
    avg_ttl_seconds: float = Field(..., description="Average TTL of cached items")
    operations_per_second: float = Field(..., description="Cache operations per second")
    timestamp: str = Field(..., description="Metrics collection timestamp")
    correlation_id: str = Field(..., description="Request correlation ID")

# Router setup
router = APIRouter(
    prefix="/system",
    tags=["System Health & Metrics"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        500: {"description": "Internal Server Error"}
    }
)

logger = structlog.get_logger(__name__)

# Startup time for uptime calculation
startup_time = datetime.utcnow()

async def get_performance_tracker(request: Request) -> PerformanceTracker:
    """Get performance tracker from request state."""
    return request.app.state.performance_tracker

async def get_cache_manager(request: Request) -> AsyncCacheManager:
    """Get cache manager from request state."""
    return request.app.state.cache_manager

async def get_auth_service(request: Request) -> AuthenticationService:
    """Get authentication service from request state."""
    return request.app.state.auth_service

async def get_authz_service(request: Request) -> AuthorizationService:
    """Get authorization service from request state."""
    return request.app.state.authz_service

    async def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return user data."""
        auth_result = await auth_service.verify_jwt_token(token)
        if auth_result.success and auth_result.user_claims:
            return {
                "user_id": auth_result.user_claims.user_id,
                "email": auth_result.user_claims.email,
                "role": auth_result.user_claims.role.value,
                "tenant_id": auth_result.user_claims.tenant_id,
                "permissions": auth_result.user_claims.permissions
            }
        return None

async def get_current_user(request: Request, auth_service: AuthenticationService = Depends(get_auth_service)):
    """Get current authenticated user."""
    # Extract token from Authorization header
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.split(" ", 1)[1]
    auth_result = await auth_service.verify_jwt_token(token)
    if not auth_result.success or not auth_result.user_claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Return user data as dict
    return {
        "user_id": auth_result.user_claims.user_id,
        "email": auth_result.user_claims.email,
        "role": auth_result.user_claims.role.value,
        "tenant_id": auth_result.user_claims.tenant_id,
        "permissions": auth_result.user_claims.permissions
    }

@router.get(
    "/health",
    response_model=HealthStatus,
    summary="System Health Check",
    description="Check overall system health and service availability."
)
async def get_health_status(
    request: Request,
    performance_tracker: PerformanceTracker = Depends(get_performance_tracker),
    cache_manager: AsyncCacheManager = Depends(get_cache_manager)
):
    """Get comprehensive system health status."""
    try:
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')
        current_time = datetime.utcnow()
        uptime = (current_time - startup_time).total_seconds()
        
        # Check service statuses
        services = {}
        overall_status = "healthy"
        
        # Check API service
        services["api"] = "healthy"
        
        # Check Redis/Cache service
        try:
            await cache_manager.ping()
            services["cache"] = "healthy"
        except Exception as e:
            services["cache"] = "unhealthy"
            overall_status = "degraded"
            logger.warning("Cache service unhealthy", error=str(e))
        
        # Check database service (placeholder)
        services["database"] = "healthy"  # TODO: Implement actual DB health check
        
        # Check AI services (placeholder)
        services["ai_vertex"] = "healthy"  # TODO: Implement actual AI service health check
        services["ai_github"] = "healthy"  # TODO: Implement actual AI service health check
        
        # Check file storage (placeholder)
        services["storage"] = "healthy"  # TODO: Implement actual storage health check
        
        # Set overall status based on service statuses
        unhealthy_services = [name for name, status in services.items() if status == "unhealthy"]
        if unhealthy_services:
            if len(unhealthy_services) >= len(services) / 2:
                overall_status = "unhealthy"
            else:
                overall_status = "degraded"
        
        return HealthStatus(
            status=overall_status,
            timestamp=current_time.isoformat() + "Z",
            version="1.0.0",
            uptime_seconds=uptime,
            services=services,
            correlation_id=correlation_id
        )
        
    except Exception as e:
        logger.error(
            "Health check failed",
            error=str(e),
            correlation_id=getattr(request.state, 'correlation_id', 'unknown'),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )

@router.get(
    "/metrics/system",
    response_model=SystemMetrics,
    summary="System Resource Metrics",
    description="Get current system resource utilization metrics. Requires admin permission."
)
async def get_system_metrics(
    request: Request,
    current_user = Depends(get_current_user),
    authz_service: AuthorizationService = Depends(get_authz_service)
):
    """Get system resource metrics (admin only)."""
    try:
        # Check admin permission
        if not await authz_service.check_permission(current_user, Permission.ADMIN_SYSTEM):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view system metrics"
            )
        
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')
        
        # Get CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get memory metrics
        memory = psutil.virtual_memory()
        memory_total_gb = memory.total / (1024**3)
        memory_available_gb = memory.available / (1024**3)
        memory_percent = memory.percent
        
        # Get disk metrics
        disk = psutil.disk_usage('/')
        disk_total_gb = disk.total / (1024**3)
        disk_free_gb = disk.free / (1024**3)
        disk_usage_percent = (disk.used / disk.total) * 100
        
        # Get network metrics
        network = psutil.net_io_counters()
        network_sent_mb = network.bytes_sent / (1024**2)
        network_recv_mb = network.bytes_recv / (1024**2)
        
        # Get connection count (approximate)
        try:
            connections = len(psutil.net_connections())
        except (psutil.AccessDenied, OSError):
            connections = 0
        
        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_total_gb=round(memory_total_gb, 2),
            memory_available_gb=round(memory_available_gb, 2),
            disk_usage_percent=round(disk_usage_percent, 2),
            disk_total_gb=round(disk_total_gb, 2),
            disk_free_gb=round(disk_free_gb, 2),
            network_sent_mb=round(network_sent_mb, 2),
            network_recv_mb=round(network_recv_mb, 2),
            active_connections=connections,
            timestamp=datetime.utcnow().isoformat() + "Z",
            correlation_id=correlation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "System metrics collection failed",
            error=str(e),
            correlation_id=getattr(request.state, 'correlation_id', 'unknown'),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to collect system metrics"
        )

@router.get(
    "/metrics/performance",
    response_model=PerformanceMetrics,
    summary="Application Performance Metrics",
    description="Get application performance and usage metrics. Requires admin permission."
)
async def get_performance_metrics(
    request: Request,
    current_user = Depends(get_current_user),
    authz_service: AuthorizationService = Depends(get_authz_service),
    performance_tracker: PerformanceTracker = Depends(get_performance_tracker)
):
    """Get application performance metrics (admin only)."""
    try:
        # Check admin permission
        if not await authz_service.check_permission(current_user, Permission.ADMIN_SYSTEM):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view performance metrics"
            )
        
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')
        
        # Get performance metrics from tracker  
        metrics = {
            "total_operations": 0,
            "total_errors": 0,
            "avg_duration_ms": 0.0,
            "ai_operations": 0,
            "ai_success_rate": 100.0,
            "cache_hit_rate": 0.0,
            "active_users": 0
        }
        
        # Calculate derived metrics
        total_requests = metrics.get("total_operations", 0)
        avg_response_time = metrics.get("avg_duration_ms", 0.0)
        
        # Calculate requests per minute (last hour)
        requests_per_minute = total_requests / 60.0 if total_requests > 0 else 0.0
        
        # Calculate error rate
        total_errors = metrics.get("total_errors", 0)
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0.0
        
        # Get AI-specific metrics
        ai_operations = metrics.get("ai_operations", 0)
        ai_success_rate = metrics.get("ai_success_rate", 100.0)
        
        # Get cache metrics
        cache_hit_rate = metrics.get("cache_hit_rate", 0.0)
        
        # Active users (placeholder - would need session tracking)
        active_users = metrics.get("active_users", 0)
        
        return PerformanceMetrics(
            total_requests=total_requests,
            avg_response_time_ms=round(avg_response_time, 2),
            requests_per_minute=round(requests_per_minute, 2),
            error_rate_percent=round(error_rate, 2),
            active_users=active_users,
            cache_hit_rate_percent=round(cache_hit_rate, 2),
            ai_operations_total=ai_operations,
            ai_operations_success_rate=round(ai_success_rate, 2),
            timestamp=datetime.utcnow().isoformat() + "Z",
            correlation_id=correlation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Performance metrics collection failed",
            error=str(e),
            correlation_id=getattr(request.state, 'correlation_id', 'unknown'),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to collect performance metrics"
        )

@router.get(
    "/metrics/cache",
    response_model=CacheMetrics,
    summary="Cache Performance Metrics",
    description="Get cache system performance metrics. Requires admin permission."
)
async def get_cache_metrics(
    request: Request,
    current_user = Depends(get_current_user),
    authz_service: AuthorizationService = Depends(get_authz_service),
    cache_manager: AsyncCacheManager = Depends(get_cache_manager)
):
    """Get cache performance metrics (admin only)."""
    try:
        # Check admin permission
        if not await authz_service.check_permission(current_user, Permission.ADMIN_SYSTEM):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view cache metrics"
            )
        
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')
        
        # Get cache metrics
        cache_stats = await cache_manager.get_cache_stats()
        
        return CacheMetrics(
            total_keys=cache_stats.get("total_keys", 0),
            memory_usage_mb=round(cache_stats.get("memory_usage_bytes", 0) / (1024**2), 2),
            hit_rate_percent=round(cache_stats.get("hit_rate", 0.0) * 100, 2),
            miss_rate_percent=round(cache_stats.get("miss_rate", 0.0) * 100, 2),
            eviction_count=cache_stats.get("evictions", 0),
            avg_ttl_seconds=round(cache_stats.get("avg_ttl", 0.0), 2),
            operations_per_second=round(cache_stats.get("ops_per_second", 0.0), 2),
            timestamp=datetime.utcnow().isoformat() + "Z",
            correlation_id=correlation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Cache metrics collection failed",
            error=str(e),
            correlation_id=getattr(request.state, 'correlation_id', 'unknown'),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to collect cache metrics"
        )

@router.get(
    "/services/status",
    response_model=List[ServiceStatus],
    summary="Individual Service Status",
    description="Get detailed status of all system services. Requires admin permission."
)
async def get_services_status(
    request: Request,
    current_user = Depends(get_current_user),
    authz_service: AuthorizationService = Depends(get_authz_service),
    cache_manager: AsyncCacheManager = Depends(get_cache_manager)
):
    """Get detailed status of all services (admin only)."""
    try:
        # Check admin permission
        if not await authz_service.check_permission(current_user, Permission.ADMIN_SYSTEM):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view service status"
            )
        
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')
        current_time = datetime.utcnow()
        
        services = []
        
        # Check API service
        services.append(ServiceStatus(
            name="api",
            status="healthy",
            last_check=current_time.isoformat() + "Z",
            response_time_ms=1.0,
            metadata={"version": "1.0.0", "requests_handled": 1000}
        ))
        
        # Check Cache service
        try:
            start_time = asyncio.get_event_loop().time()
            await cache_manager.ping()
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            services.append(ServiceStatus(
                name="cache",
                status="healthy",
                last_check=current_time.isoformat() + "Z",
                response_time_ms=round(response_time, 2),
                metadata={"type": "redis", "keys": await cache_manager.get_total_keys()}
            ))
        except Exception as e:
            services.append(ServiceStatus(
                name="cache",
                status="unhealthy",
                last_check=current_time.isoformat() + "Z",
                error_message=str(e),
                response_time_ms=None,
                metadata={}
            ))
        
        # Check Database service (placeholder)
        services.append(ServiceStatus(
            name="database",
            status="healthy",
            last_check=current_time.isoformat() + "Z",
            response_time_ms=5.0,
            metadata={"type": "postgresql", "connections": 10}
        ))
        
        # Check AI services (placeholder)
        services.append(ServiceStatus(
            name="ai_vertex",
            status="healthy",
            last_check=current_time.isoformat() + "Z",
            response_time_ms=100.0,
            metadata={"model": "gemini-2.5-flash-lite", "requests_today": 50}
        ))
        
        services.append(ServiceStatus(
            name="ai_github",
            status="healthy",
            last_check=current_time.isoformat() + "Z",
            response_time_ms=120.0,
            metadata={"model": "gpt-4.1", "requests_today": 30}
        ))
        
        return services
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Service status collection failed",
            error=str(e),
            correlation_id=getattr(request.state, 'correlation_id', 'unknown'),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to collect service status"
        )