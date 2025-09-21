"""
Performance monitoring middleware for ArchBuilder.AI Cloud Server.

This middleware provides real-time performance monitoring for FastAPI applications
including request/response timing, resource usage tracking, and performance alerting.

According to performance-optimization.instructions.md guidelines.
"""

import time
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import structlog
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import psutil
import json
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

from app.core.logging import set_correlation_id, generate_correlation_id
from app.core.exceptions import RevitAutoPlanException, ValidationException, AIModelUnavailableException, NetworkException
from app.core.config import get_settings

# Try to import performance and cache modules
try:
    from .performance import PerformanceTracker, performance_tracker
    PERFORMANCE_AVAILABLE = True
except ImportError:
    PERFORMANCE_AVAILABLE = False

try:
    from .cache import get_cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

logger = structlog.get_logger(__name__)

class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive performance monitoring middleware.
    
    Features:
    - Request/response timing
    - Resource usage monitoring
    - Performance target validation
    - Real-time alerting
    - Performance metrics collection
    """
    
    def __init__(
        self,
        app: ASGIApp,
        enable_detailed_monitoring: bool = True,
        slow_request_threshold: float = 5.0,
        memory_alert_threshold: int = 500  # MB
    ):
        super().__init__(app)
        self.tracker = tracker if PERFORMANCE_AVAILABLE else None
        self.enable_detailed_monitoring = enable_detailed_monitoring
        self.slow_request_threshold = slow_request_threshold
        self.memory_alert_threshold = memory_alert_threshold
        
        # Performance counters
        self.request_count = 0
        self.total_request_time = 0.0
        self.slow_request_count = 0
        self.error_count = 0
        
        # Recent requests for monitoring
        self.recent_requests: List[Dict[str, Any]] = []
        self.max_recent_requests = 100
        
        logger.info("PerformanceMiddleware initialized",
                   enable_detailed_monitoring=enable_detailed_monitoring,
                   slow_request_threshold=slow_request_threshold,
                   memory_alert_threshold=memory_alert_threshold)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance monitoring"""
        
        # Generate correlation ID if not present - moved to CorrelationIdMiddleware
        correlation_id = getattr(request.state, 'correlation_id', "unknown") # CorrelationIdMiddleware tarafından ayarlanmış olacak
        
        # Start timing
        start_time = time.time()
        start_memory = None
        start_cpu = None
        
        if self.enable_detailed_monitoring:
            process = psutil.Process()
            start_memory = process.memory_info().rss / 1024 / 1024  # MB
            start_cpu = process.cpu_percent()
        
        # Extract request info
        method = request.method
        url = str(request.url)
        path = request.url.path
        user_agent = request.headers.get("user-agent", "")
        client_ip = request.client.host if request.client else "unknown"
   
        response = None
        error = None
        
        try:
            # Process request
            if self.tracker and PERFORMANCE_AVAILABLE:
                async with self.tracker.track_operation(
                    f"http_{method.lower()}_{path.replace('/', '_')}",
                    correlation_id=correlation_id
                ):
                    response = await call_next(request)
            else:
                response = await call_next(request)
            
            # Add correlation ID to response headers - moved to CorrelationIdMiddleware
            
        except Exception as e:
            error = str(e)
            self.error_count += 1
            logger.error("Request processing error",
                        method=method,
                        path=path,
                        error=error,
                        correlation_id=correlation_id)
            raise
        
        finally:
            # Calculate timing and resource usage
            duration = time.time() - start_time
            self.request_count += 1
            self.total_request_time += duration
            
            end_memory = None
            end_cpu = None
            memory_delta = None
            cpu_usage = None
            
            if self.enable_detailed_monitoring:
                process = psutil.Process()
                end_memory = process.memory_info().rss / 1024 / 1024  # MB
                end_cpu = process.cpu_percent()
                
                if start_memory:
                    memory_delta = end_memory - start_memory
                
                cpu_usage = end_cpu
            
            # Check for slow requests
            is_slow = duration > self.slow_request_threshold
            if is_slow:
                self.slow_request_count += 1
            
            # Check for memory alerts
            memory_alert = end_memory and end_memory > self.memory_alert_threshold
            
            # Log request
            log_data = {
                "method": method,
                "path": path,
                "duration": duration,
                "status_code": response.status_code if response else None,
                "correlation_id": correlation_id,
                "client_ip": client_ip,
                "user_agent": user_agent[:100],  # Truncate long user agents
                "is_slow": is_slow,
                "memory_alert": memory_alert
            }
            
            if self.enable_detailed_monitoring:
                log_data.update({
                    "memory_mb": end_memory,
                    "memory_delta_mb": memory_delta,
                    "cpu_percent": cpu_usage
                })
            
            if error:
                log_data["error"] = error
                logger.error("Request completed with error", **log_data)
            elif is_slow:
                logger.warning("Slow request detected", **log_data)
            elif memory_alert:
                logger.warning("High memory usage detected", **log_data)
            else:
                logger.info("Request completed", **log_data)
            
            # Store recent request info
            request_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "method": method,
                "path": path,
                "duration": duration,
                "status_code": response.status_code if response else None,
                "correlation_id": correlation_id,
                "is_slow": is_slow,
                "memory_alert": memory_alert,
                "error": error
            }
            
            if self.enable_detailed_monitoring:
                request_info.update({
                    "memory_mb": end_memory,
                    "memory_delta_mb": memory_delta,
                    "cpu_percent": cpu_usage
                })
            
            self.recent_requests.append(request_info)
            if len(self.recent_requests) > self.max_recent_requests:
                self.recent_requests.pop(0)
            
            # Send alerts if needed
            if is_slow or memory_alert:
                await self._send_performance_alert(request_info)
        
        return response
    
    async def _send_performance_alert(self, request_info: Dict[str, Any]):
        """Send performance alert for problematic requests"""
        
        alert_type = []
        if request_info.get("is_slow"):
            alert_type.append("slow_request")
        if request_info.get("memory_alert"):
            alert_type.append("high_memory")
        
        alert_data = {
            "type": "performance_alert",
            "alert_types": alert_type,
            "request": request_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Try to store alert in cache/Redis if available
        if CACHE_AVAILABLE:
            try:
                cache = get_cache()
                await cache.set(
                    f"alert:{request_info['correlation_id']}",
                    alert_data,
                    ttl_seconds=3600  # Keep alerts for 1 hour
                )
            except Exception as e:
                logger.warning("Failed to store performance alert", error=str(e))
        
        logger.warning("Performance alert generated",
                      alert_types=alert_type,
                      correlation_id=request_info.get("correlation_id"))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get middleware performance statistics"""
        avg_request_time = (
            self.total_request_time / self.request_count 
            if self.request_count > 0 else 0
        )
        slow_request_rate = (
            self.slow_request_count / self.request_count 
            if self.request_count > 0 else 0
        )
        error_rate = (
            self.error_count / self.request_count 
            if self.request_count > 0 else 0
        )
        
        return {
            "request_count": self.request_count,
            "total_request_time": self.total_request_time,
            "avg_request_time": avg_request_time,
            "slow_request_count": self.slow_request_count,
            "slow_request_rate": slow_request_rate,
            "error_count": self.error_count,
            "error_rate": error_rate,
            "recent_requests": self.recent_requests[-10:],  # Last 10 requests
            "timestamp": datetime.utcnow().isoformat()
        }

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation IDs in FastAPI."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or create correlation ID
        correlation_id = self._get_or_create_correlation_id(request)
        
        # Set in context
        set_correlation_id(correlation_id)
        
        # Add to request state
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
    
    def _get_or_create_correlation_id(self, request: Request) -> str:
        """Get correlation ID from headers or create new one."""
        correlation_id = request.headers.get("X-Correlation-ID")
        
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        return correlation_id

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting based on client IP."""

    def __init__(self, app: ASGIApp, limiter: Limiter):
        super().__init__(app)
        self.limiter = limiter
        logger.info("RateLimitingMiddleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            # Use the app's limiter instance directly
            response = await call_next(request)
            return response
        except RateLimitExceeded as exc:
            logger.warning(
                "Rate limit exceeded",
                client_ip=get_remote_address(request),
                endpoint=request.url.path,
                rate_limit=str(exc.detail),
                correlation_id=getattr(request.state, 'correlation_id', "unknown")
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Çok fazla istek. Lütfen daha sonra tekrar deneyin.",
                    "retry_after": int(exc.retry_after)
                },
                headers={'Retry-After': str(int(exc.retry_after))}
            )

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add essential security headers to responses."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        logger.info("SecurityHeadersMiddleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        return response

class ResourceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    System resource monitoring middleware.
    
    Features:
    - CPU usage monitoring
    - Memory usage tracking
    - Disk space monitoring
    - Network connection tracking
    - Resource alerts
    """
    
    def __init__(
        self,
        app: ASGIApp,
        cpu_alert_threshold: float = 80.0,
        memory_alert_threshold: float = 80.0,
        disk_alert_threshold: float = 90.0
    ):
        super().__init__(app)
        self.cpu_alert_threshold = cpu_alert_threshold
        self.memory_alert_threshold = memory_alert_threshold
        self.disk_alert_threshold = disk_alert_threshold
        
        # Resource history
        self.resource_history: List[Dict[str, Any]] = []
        self.max_history = 100
        
        logger.info("ResourceMonitoringMiddleware initialized",
                   cpu_threshold=cpu_alert_threshold,
                   memory_threshold=memory_alert_threshold,
                   disk_threshold=disk_alert_threshold)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor system resources during request processing"""
        
        correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
        
        # Get system metrics before request
        start_metrics = self._get_system_metrics()
        
        # Process request
        response = await call_next(request)
        
        # Get system metrics after request
        end_metrics = self._get_system_metrics()
        
        # Check for resource alerts
        alerts = self._check_resource_alerts(end_metrics)
        
        if alerts:
            await self._send_resource_alerts(alerts, correlation_id)
        
        # Store resource info
        resource_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            "metrics": end_metrics,
            "alerts": alerts
        }
        
        self.resource_history.append(resource_info)
        if len(self.resource_history) > self.max_history:
            self.resource_history.pop(0)
        
        return response
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get current system resource metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count
                },
                "memory": {
                    "total_gb": memory.total / 1024 / 1024 / 1024,
                    "available_gb": memory.available / 1024 / 1024 / 1024,
                    "percent": memory.percent,
                    "used_gb": memory.used / 1024 / 1024 / 1024
                },
                "disk": {
                    "total_gb": disk.total / 1024 / 1024 / 1024,
                    "free_gb": disk.free / 1024 / 1024 / 1024,
                    "percent": disk.percent,
                    "used_gb": disk.used / 1024 / 1024 / 1024
                },
                "process": {
                    "memory_mb": process_memory.rss / 1024 / 1024,
                    "cpu_percent": process.cpu_percent(),
                    "threads": process.num_threads(),
                    "connections": len(process.connections()),
                    "open_files": len(process.open_files())
                }
            }
            
        except Exception as e:
            logger.warning("Failed to get system metrics", error=str(e))
            return {}
    
    def _check_resource_alerts(self, metrics: Dict[str, Any]) -> List[str]:
        """Check if any resource thresholds are exceeded"""
        alerts = []
        
        try:
            # CPU alert
            cpu_percent = metrics.get("cpu", {}).get("percent", 0)
            if cpu_percent > self.cpu_alert_threshold:
                alerts.append(f"high_cpu:{cpu_percent:.1f}%")
            
            # Memory alert
            memory_percent = metrics.get("memory", {}).get("percent", 0)
            if memory_percent > self.memory_alert_threshold:
                alerts.append(f"high_memory:{memory_percent:.1f}%")
            
            # Disk alert
            disk_percent = metrics.get("disk", {}).get("percent", 0)
            if disk_percent > self.disk_alert_threshold:
                alerts.append(f"high_disk:{disk_percent:.1f}%")
            
            # Process memory alert (500MB threshold)
            process_memory = metrics.get("process", {}).get("memory_mb", 0)
            if process_memory > 500:
                alerts.append(f"high_process_memory:{process_memory:.1f}MB")
                
        except Exception as e:
            logger.warning("Failed to check resource alerts", error=str(e))
        
        return alerts
    
    async def _send_resource_alerts(self, alerts: List[str], correlation_id: str):
        """Send resource usage alerts"""
        
        alert_data = {
            "type": "resource_alert",
            "alerts": alerts,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Try to store alert in cache if available
        if CACHE_AVAILABLE:
            try:
                cache = get_cache()
                await cache.set(
                    f"resource_alert:{correlation_id}",
                    alert_data,
                    ttl_seconds=3600
                )
            except Exception:
                pass
        
        logger.warning("Resource alerts generated",
                      alerts=alerts,
                      correlation_id=correlation_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get resource monitoring statistics"""
        current_metrics = self._get_system_metrics()
        
        return {
            "current_metrics": current_metrics,
            "recent_history": self.resource_history[-10:],
            "alert_thresholds": {
                "cpu_percent": self.cpu_alert_threshold,
                "memory_percent": self.memory_alert_threshold,
                "disk_percent": self.disk_alert_threshold
            },
            "timestamp": datetime.utcnow().isoformat()
        }

def add_middleware(app: FastAPI):
    """Add all custom middlewares to FastAPI app."""
    app.add_middleware(CorrelationIdMiddleware)

    # Güvenlik başlıkları middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Rate limiting middleware
    settings = get_settings()
    limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL_FOR_LIMITER)
    app.state.limiter = limiter # Limiter instance'ını uygulamaya bağla
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) # Hata işleyiciyi ekle
    app.add_middleware(RateLimitingMiddleware, limiter=limiter)

    # Performance monitoring middleware
    app.add_middleware(
        PerformanceMiddleware,
        tracker=performance_tracker if PERFORMANCE_AVAILABLE else None,
        enable_detailed_monitoring=True,
        slow_request_threshold=5.0,
        memory_alert_threshold=500
    )

    # Resource monitoring middleware
    app.add_middleware(
        ResourceMonitoringMiddleware,
        cpu_alert_threshold=80.0,
        memory_alert_threshold=80.0,  # Memory percentage threshold
        disk_alert_threshold=90.0
    )

    logger.info("All custom middlewares added to FastAPI app")

# Performance monitoring endpoints
async def get_performance_stats() -> Dict[str, Any]:
    """Get comprehensive performance statistics"""
    stats = {
        "timestamp": datetime.utcnow().isoformat(),
        "middleware_stats": {},
        "tracker_stats": {},
        "cache_stats": {},
        "system_health": {}
    }
    
    # Get tracker stats if available
    if PERFORMANCE_AVAILABLE and performance_tracker:
        try:
            stats["tracker_stats"] = await performance_tracker.get_performance_report()
            stats["system_health"] = await performance_tracker.get_system_health()
        except Exception as e:
            logger.warning("Failed to get tracker stats", error=str(e))
    
    # Get cache stats if available
    if CACHE_AVAILABLE:
        try:
            cache = get_cache()
            stats["cache_stats"] = await cache.get_stats()
        except Exception as e:
            logger.warning("Failed to get cache stats", error=str(e))
    
    return stats