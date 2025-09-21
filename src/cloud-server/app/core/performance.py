"""
Performance monitoring and optimization module for ArchBuilder.AI Cloud Server.

This module implements comprehensive performance tracking, monitoring, and optimization
features                    if metrics.duration and metrics.duration > target:
                        logger.warning("Performance target exceeded",
                                     operation=metrics.operation_name,
                                     duration=metrics.duration,
                                     target=target)rding to the performance-optimization.instructions.md guidelines.

Targets:
- Simple queries: <2s
- AI operations: <30s  
- Document OCR: <2min
- Memory usage: <500MB
"""

import time
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from functools import wraps
import psutil
import logging
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
import json
import hashlib
from collections import defaultdict

logger = structlog.get_logger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
    status: str = "started"
    error: Optional[str] = None
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)

    def complete(self, success: bool = True, error: Optional[str] = None):
        """Mark operation as complete and calculate duration"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = "completed" if success else "failed"
        self.error = error
        
        # Capture system metrics
        process = psutil.Process()
        self.memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        self.cpu_usage = process.cpu_percent()

class PerformanceTracker:
    """
    Comprehensive performance tracking and monitoring system.
    
    Features:
    - Operation timing and resource usage tracking
    - Memory and CPU monitoring
    - Performance targets validation
    - Metrics collection and reporting
    - Real-time performance alerts
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.redis_client = redis_client
        self.performance_targets = {
            "simple_query": 2.0,        # 2 seconds
            "ai_operation": 30.0,       # 30 seconds
            "document_ocr": 120.0,      # 2 minutes
            "file_upload": 60.0,        # 1 minute
            "layout_generation": 30.0,  # 30 seconds
            "validation": 5.0,          # 5 seconds
        }
        self.max_memory_mb = 500  # 500MB memory limit
        
        # Thread-local storage for nested operations
        self.local_data = threading.local()
        
        logger.info("PerformanceTracker initialized", 
                   targets=self.performance_targets,
                   max_memory_mb=self.max_memory_mb)
    
    @asynccontextmanager
    async def track_operation(
        self, 
        operation_name: str, 
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **additional_data
    ):
        """
        Async context manager for tracking operation performance.
        
        Usage:
            async with performance_tracker.track_operation("ai_layout_generation", correlation_id="123"):
                result = await ai_service.generate_layout(...)
        """
        
        operation_id = f"{operation_name}_{correlation_id}_{int(time.time() * 1000)}"
        
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            correlation_id=correlation_id,
            user_id=user_id,
            additional_data=additional_data
        )
        
        self.metrics[operation_id] = metrics
        
        try:
            logger.info("Operation started", 
                       operation=operation_name,
                       correlation_id=correlation_id,
                       user_id=user_id)
            
            yield metrics
            
            # Mark as successful completion
            metrics.complete(success=True)
            
            # Check performance targets
            await self._check_performance_targets(metrics)
            
            logger.info("Operation completed successfully",
                       operation=operation_name,
                       duration=metrics.duration,
                       memory_mb=metrics.memory_usage,
                       cpu_percent=metrics.cpu_usage,
                       correlation_id=correlation_id)
                       
        except Exception as e:
            # Mark as failed
            metrics.complete(success=False, error=str(e))
            
            logger.error("Operation failed",
                        operation=operation_name,
                        duration=metrics.duration,
                        error=str(e),
                        correlation_id=correlation_id)
            raise
            
        finally:
            # Store metrics for reporting
            await self._store_metrics(metrics)
    
    def performance_monitor(
        self, 
        operation_name: str,
        target_seconds: Optional[float] = None
    ):
        """
        Decorator for synchronous function performance monitoring.
        
        Usage:
            @performance_tracker.performance_monitor("database_query")
            def get_user_data(user_id: str):
                return db.query(User).filter(User.id == user_id).first()
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                operation_id = f"{operation_name}_{int(time.time() * 1000)}"
                
                metrics = PerformanceMetrics(
                    operation_name=operation_name,
                    start_time=time.time()
                )
                
                try:
                    result = func(*args, **kwargs)
                    metrics.complete(success=True)
                    
                    # Check performance target
                    target = target_seconds or self.performance_targets.get(operation_name, float('inf'))
                    if metrics.duration > target:
                        logger.warning("Performance target exceeded",
                                     operation=operation_name,
                                     duration=metrics.duration,
                                     target=target)
                    
                    return result
                    
                except Exception as e:
                    metrics.complete(success=False, error=str(e))
                    raise
                finally:
                    self.metrics[operation_id] = metrics
                    
            return wrapper
        return decorator
    
    def async_performance_monitor(
        self, 
        operation_name: str,
        target_seconds: Optional[float] = None
    ):
        """
        Decorator for asynchronous function performance monitoring.
        
        Usage:
            @performance_tracker.async_performance_monitor("ai_processing")
            async def process_ai_request(request):
                return await ai_service.process(request)
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                async with self.track_operation(operation_name) as metrics:
                    result = await func(*args, **kwargs)
                    
                    # Check performance target
                    target = target_seconds or self.performance_targets.get(operation_name, float('inf'))
                    if metrics.duration and metrics.duration > target:
                        logger.warning("Performance target exceeded",
                                     operation=operation_name,
                                     duration=metrics.duration,
                                     target=target)
                    
                    return result
                    
            return wrapper
        return decorator
    
    async def _check_performance_targets(self, metrics: PerformanceMetrics):
        """Check if operation meets performance targets"""
        target = self.performance_targets.get(metrics.operation_name)
        
        if target and metrics.duration and metrics.duration > target:
            # Performance target exceeded
            await self._send_performance_alert(metrics, target)
            
        # Check memory usage
        if metrics.memory_usage and metrics.memory_usage > self.max_memory_mb:
            await self._send_memory_alert(metrics)
    
    async def _send_performance_alert(self, metrics: PerformanceMetrics, target: float):
        """Send performance alert for exceeded targets"""
        alert_data = {
            "type": "performance_target_exceeded",
            "operation": metrics.operation_name,
            "duration": metrics.duration,
            "target": target,
            "excess_time": (metrics.duration or 0) - target,
            "correlation_id": metrics.correlation_id,
            "user_id": metrics.user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.warning("Performance target exceeded",
                      operation=metrics.operation_name,
                      duration=metrics.duration,
                      target=target,
                      correlation_id=metrics.correlation_id)
        
        # Store alert in Redis for monitoring dashboard
        if self.redis_client:
            await self.redis_client.lpush(
                "performance_alerts",
                json.dumps(alert_data)
            )
            await self.redis_client.expire("performance_alerts", 86400)  # 24 hours
    
    async def _send_memory_alert(self, metrics: PerformanceMetrics):
        """Send memory usage alert"""
        alert_data = {
            "type": "memory_usage_exceeded",
            "operation": metrics.operation_name,
            "memory_usage_mb": metrics.memory_usage,
            "limit_mb": self.max_memory_mb,
            "correlation_id": metrics.correlation_id,
            "user_id": metrics.user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.warning("Memory limit exceeded",
                      operation=metrics.operation_name,
                      memory_usage_mb=metrics.memory_usage,
                      limit_mb=self.max_memory_mb,
                      correlation_id=metrics.correlation_id)
        
        if self.redis_client:
            await self.redis_client.lpush(
                "memory_alerts",
                json.dumps(alert_data)
            )
            await self.redis_client.expire("memory_alerts", 86400)  # 24 hours
    
    async def _store_metrics(self, metrics: PerformanceMetrics):
        """Store metrics in Redis for reporting and analytics"""
        if not self.redis_client:
            return
            
        metrics_data = {
            "operation_name": metrics.operation_name,
            "start_time": metrics.start_time,
            "end_time": metrics.end_time,
            "duration": metrics.duration,
            "memory_usage": metrics.memory_usage,
            "cpu_usage": metrics.cpu_usage,
            "status": metrics.status,
            "error": metrics.error,
            "correlation_id": metrics.correlation_id,
            "user_id": metrics.user_id,
            "additional_data": metrics.additional_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store in time-series format for analytics
        key = f"metrics:{metrics.operation_name}:{datetime.utcnow().strftime('%Y%m%d')}"
        await self.redis_client.lpush(key, json.dumps(metrics_data))
        await self.redis_client.expire(key, 604800)  # 7 days
        
        # Store in user-specific metrics
        if metrics.user_id:
            user_key = f"user_metrics:{metrics.user_id}:{datetime.utcnow().strftime('%Y%m%d')}"
            await self.redis_client.lpush(user_key, json.dumps(metrics_data))
            await self.redis_client.expire(user_key, 604800)  # 7 days
    
    async def get_performance_report(
        self, 
        operation_name: Optional[str] = None,
        user_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Generate performance report for specified time period"""
        
        if not self.redis_client:
            return {"error": "Redis not available for reporting"}
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        report = {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours
            },
            "operations": {},
            "alerts": [],
            "summary": {}
        }
        
        # Collect metrics for each day in the period
        current_date = start_time.date()
        while current_date <= end_time.date():
            date_str = current_date.strftime('%Y%m%d')
            
            if operation_name:
                keys = [f"metrics:{operation_name}:{date_str}"]
            else:
                # Get all operation types
                pattern = f"metrics:*:{date_str}"
                keys = await self.redis_client.keys(pattern)
            
            for key in keys:
                metrics_list = await self.redis_client.lrange(key, 0, -1)
                for metrics_json in metrics_list:
                    try:
                        metrics_data = json.loads(metrics_json)
                        op_name = metrics_data["operation_name"]
                        
                        # Filter by user if specified
                        if user_id and metrics_data.get("user_id") != user_id:
                            continue
                        
                        # Filter by time period
                        metrics_time = datetime.fromisoformat(metrics_data["timestamp"])
                        if not (start_time <= metrics_time <= end_time):
                            continue
                        
                        if op_name not in report["operations"]:
                            report["operations"][op_name] = {
                                "count": 0,
                                "total_duration": 0.0,
                                "avg_duration": 0.0,
                                "min_duration": float('inf'),
                                "max_duration": 0.0,
                                "success_count": 0,
                                "error_count": 0,
                                "avg_memory_usage": 0.0,
                                "avg_cpu_usage": 0.0,
                                "target_violations": 0
                            }
                        
                        op_stats = report["operations"][op_name]
                        op_stats["count"] += 1
                        
                        if metrics_data["duration"]:
                            duration = metrics_data["duration"]
                            op_stats["total_duration"] += duration
                            op_stats["min_duration"] = min(op_stats["min_duration"], duration)
                            op_stats["max_duration"] = max(op_stats["max_duration"], duration)
                            
                            # Check target violations
                            target = self.performance_targets.get(op_name)
                            if target and duration > target:
                                op_stats["target_violations"] += 1
                        
                        if metrics_data["status"] == "completed":
                            op_stats["success_count"] += 1
                        else:
                            op_stats["error_count"] += 1
                        
                        if metrics_data["memory_usage"]:
                            op_stats["avg_memory_usage"] += metrics_data["memory_usage"]
                        
                        if metrics_data["cpu_usage"]:
                            op_stats["avg_cpu_usage"] += metrics_data["cpu_usage"]
                            
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning("Failed to parse metrics data", error=str(e))
            
            current_date += timedelta(days=1)
        
        # Calculate averages
        for op_name, stats in report["operations"].items():
            if stats["count"] > 0:
                stats["avg_duration"] = stats["total_duration"] / stats["count"]
                stats["avg_memory_usage"] = stats["avg_memory_usage"] / stats["count"]
                stats["avg_cpu_usage"] = stats["avg_cpu_usage"] / stats["count"]
                stats["success_rate"] = stats["success_count"] / stats["count"]
                
                if stats["min_duration"] == float('inf'):
                    stats["min_duration"] = 0.0
        
        # Get recent alerts
        alerts = await self.redis_client.lrange("performance_alerts", 0, 99)  # Last 100 alerts
        memory_alerts = await self.redis_client.lrange("memory_alerts", 0, 99)
        
        for alert_json in alerts + memory_alerts:
            try:
                alert_data = json.loads(alert_json)
                alert_time = datetime.fromisoformat(alert_data["timestamp"])
                if start_time <= alert_time <= end_time:
                    report["alerts"].append(alert_data)
            except (json.JSONDecodeError, KeyError):
                continue
        
        # Generate summary
        total_operations = sum(stats["count"] for stats in report["operations"].values())
        total_errors = sum(stats["error_count"] for stats in report["operations"].values())
        
        report["summary"] = {
            "total_operations": total_operations,
            "total_errors": total_errors,
            "error_rate": total_errors / total_operations if total_operations > 0 else 0,
            "alert_count": len(report["alerts"]),
            "operations_with_violations": len([
                op for op, stats in report["operations"].items() 
                if stats["target_violations"] > 0
            ])
        }
        
        return report
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics"""
        process = psutil.Process()
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get process metrics
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent()
        
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / 1024 / 1024,
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / 1024 / 1024 / 1024
            },
            "process": {
                "memory_mb": process_memory.rss / 1024 / 1024,
                "cpu_percent": process_cpu,
                "threads": process.num_threads(),
                "open_files": len(process.open_files())
            },
            "health_status": "healthy"
        }
        
        # Determine health status
        if (cpu_percent > 80 or 
            memory.percent > 90 or 
            disk.percent > 90 or
            process_memory.rss / 1024 / 1024 > self.max_memory_mb):
            health_data["health_status"] = "warning"
        
        if (cpu_percent > 95 or 
            memory.percent > 95 or 
            disk.percent > 95):
            health_data["health_status"] = "critical"
        
        return health_data

# Global performance tracker instance
performance_tracker = PerformanceTracker()

# Performance monitoring decorators for easy use
def monitor_performance(operation_name: str, target_seconds: Optional[float] = None):
    """Decorator for synchronous function performance monitoring"""
    return performance_tracker.performance_monitor(operation_name, target_seconds)

def async_monitor_performance(operation_name: str, target_seconds: Optional[float] = None):
    """Decorator for asynchronous function performance monitoring"""
    return performance_tracker.async_performance_monitor(operation_name, target_seconds)

# Convenience function for tracking operations
def track_operation(operation_name: str, correlation_id: Optional[str] = None, user_id: Optional[str] = None, **additional_data):
    """Convenience function for tracking operations"""
    return performance_tracker.track_operation(operation_name, correlation_id, user_id, **additional_data)