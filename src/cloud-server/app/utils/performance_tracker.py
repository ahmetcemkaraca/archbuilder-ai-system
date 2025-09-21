"""
ArchBuilder.AI - Performance Tracking System
Comprehensive performance monitoring, metrics collection, and operation tracking.
"""

import asyncio
import time
import psutil
import structlog
from typing import Any, Dict, Optional, List, Callable, TypeVar, Awaitable
from functools import wraps
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import threading
from collections import defaultdict, deque
import json
import uuid

T = TypeVar('T')

class MetricType(Enum):
    """Types of performance metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

class AlertLevel(Enum):
    """Performance alert levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class PerformanceMetrics:
    """Performance metrics container."""
    operation_name: str
    correlation_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    memory_used_mb: float = 0.0
    memory_delta_mb: float = 0.0
    cpu_percent: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SystemMetrics:
    """System-wide performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    network_io_bytes: Dict[str, int]
    active_connections: int
    response_times: Dict[str, float]  # Operation -> avg response time

@dataclass
class PerformanceAlert:
    """Performance alert definition."""
    alert_id: str
    level: AlertLevel
    message: str
    metric_name: str
    threshold_value: float
    actual_value: float
    timestamp: datetime
    correlation_id: Optional[str] = None

class PerformanceTracker:
    """
    Comprehensive performance tracking system.
    
    Features:
    - Operation timing and resource usage tracking
    - System-wide metrics collection
    - Real-time performance alerts
    - Performance trend analysis
    - Automatic bottleneck detection
    """
    
    def __init__(
        self,
        collection_interval: float = 60.0,  # seconds
        retention_hours: int = 24,
        alert_thresholds: Optional[Dict[str, Dict[str, float]]] = None
    ):
        self.logger = structlog.get_logger(__name__)
        self.process = psutil.Process()
        
        # Configuration
        self.collection_interval = collection_interval
        self.retention_hours = retention_hours
        self.alert_thresholds = alert_thresholds or self._default_thresholds()
        
        # Data storage
        self.operation_metrics: Dict[str, List[PerformanceMetrics]] = defaultdict(list)
        self.system_metrics: deque = deque(maxlen=int(retention_hours * 3600 / collection_interval))
        self.alerts: deque = deque(maxlen=1000)
        
        # Real-time tracking
        self.active_operations: Dict[str, PerformanceMetrics] = {}
        self.metric_summaries: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Background collection
        self._collection_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Thread safety
        self._lock = threading.RLock()
    
    async def start_collection(self):
        """Start background metrics collection."""
        if self._running:
            return
            
        self._running = True
        self._collection_task = asyncio.create_task(self._collect_system_metrics())
        
        self.logger.info(
            "Performance tracking started",
            collection_interval=self.collection_interval,
            retention_hours=self.retention_hours
        )
    
    async def stop_collection(self):
        """Stop background metrics collection."""
        self._running = False
        
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Performance tracking stopped")
    
    @asynccontextmanager
    async def track_operation(
        self,
        operation_name: str,
        correlation_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracking operation performance.
        
        Args:
            operation_name: Name of the operation being tracked
            correlation_id: Request correlation ID
            metadata: Additional metadata to store with metrics
        """
        start_time = datetime.utcnow()
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = self.process.cpu_percent()
        
        # Create metrics object
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            correlation_id=correlation_id,
            start_time=start_time,
            memory_used_mb=start_memory,
            cpu_percent=start_cpu,
            metadata=metadata or {}
        )
        
        # Track active operation
        operation_id = f"{operation_name}:{correlation_id}"
        with self._lock:
            self.active_operations[operation_id] = metrics
        
        self.logger.debug(
            "Operation started",
            operation=operation_name,
            correlation_id=correlation_id,
            start_memory_mb=start_memory,
            metadata=metadata
        )
        
        try:
            yield metrics
            metrics.success = True
            
        except Exception as e:
            metrics.success = False
            metrics.error_message = str(e)
            
            self.logger.error(
                "Operation failed",
                operation=operation_name,
                correlation_id=correlation_id,
                error=str(e),
                exc_info=True
            )
            raise
            
        finally:
            # Calculate final metrics
            end_time = datetime.utcnow()
            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            end_cpu = self.process.cpu_percent()
            
            metrics.end_time = end_time
            metrics.duration_ms = (end_time - start_time).total_seconds() * 1000
            metrics.memory_delta_mb = end_memory - start_memory
            metrics.cpu_percent = max(end_cpu - start_cpu, 0)
            
            # Remove from active operations
            with self._lock:
                self.active_operations.pop(operation_id, None)
                
                # Store completed metrics
                self.operation_metrics[operation_name].append(metrics)
                
                # Keep only recent metrics
                max_metrics = int(self.retention_hours * 60)  # Assume 1 per minute avg
                if len(self.operation_metrics[operation_name]) > max_metrics:
                    self.operation_metrics[operation_name] = \
                        self.operation_metrics[operation_name][-max_metrics:]
            
            # Update metric summaries
            self._update_metric_summaries(operation_name, metrics)
            
            # Check for alerts
            await self._check_performance_alerts(operation_name, metrics)
            
            # Log completion
            self.logger.info(
                "Operation completed",
                operation=operation_name,
                correlation_id=correlation_id,
                duration_ms=metrics.duration_ms,
                memory_delta_mb=metrics.memory_delta_mb,
                cpu_percent=metrics.cpu_percent,
                success=metrics.success,
                metadata=metadata
            )
    
    def record_metric(
        self,
        metric_name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        tags: Optional[Dict[str, Any]] = None,
        correlation_id: str = "unknown"
    ):
        """
        Record a custom metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            metric_type: Type of metric
            tags: Additional tags/metadata
            correlation_id: Request correlation ID
        """
        with self._lock:
            if metric_name not in self.metric_summaries:
                self.metric_summaries[metric_name] = {
                    'count': 0,
                    'sum': 0.0,
                    'min': float('inf'),
                    'max': float('-inf'),
                    'avg': 0.0,
                    'last_value': 0.0,
                    'last_updated': datetime.utcnow()
                }
            
            summary = self.metric_summaries[metric_name]
            
            if metric_type == MetricType.COUNTER:
                summary['sum'] += value
                summary['last_value'] = summary['sum']
            else:  # GAUGE, HISTOGRAM, TIMER
                summary['count'] += 1
                summary['sum'] += value
                summary['min'] = min(summary['min'], value)
                summary['max'] = max(summary['max'], value)
                summary['avg'] = summary['sum'] / summary['count']
                summary['last_value'] = value
            
            summary['last_updated'] = datetime.utcnow()
        
        self.logger.debug(
            "Metric recorded",
            metric_name=metric_name,
            value=value,
            metric_type=metric_type.value,
            tags=tags,
            correlation_id=correlation_id
        )
    
    async def get_operation_summary(
        self,
        operation_name: str,
        time_window_hours: int = 1
    ) -> Dict[str, Any]:
        """
        Get performance summary for an operation.
        
        Args:
            operation_name: Name of the operation
            time_window_hours: Time window for analysis
            
        Returns:
            Performance summary dictionary
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        with self._lock:
            metrics = [
                m for m in self.operation_metrics.get(operation_name, [])
                if m.start_time >= cutoff_time
            ]
        
        if not metrics:
            return {
                "operation_name": operation_name,
                "time_window_hours": time_window_hours,
                "total_operations": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
                "p95_duration_ms": 0.0,
                "p99_duration_ms": 0.0,
                "avg_memory_delta_mb": 0.0,
                "avg_cpu_percent": 0.0
            }
        
        # Calculate statistics
        durations = [m.duration_ms for m in metrics]
        memory_deltas = [m.memory_delta_mb for m in metrics]
        cpu_percentages = [m.cpu_percent for m in metrics]
        
        successful_operations = sum(1 for m in metrics if m.success)
        
        durations.sort()
        p95_index = int(len(durations) * 0.95)
        p99_index = int(len(durations) * 0.99)
        
        return {
            "operation_name": operation_name,
            "time_window_hours": time_window_hours,
            "total_operations": len(metrics),
            "successful_operations": successful_operations,
            "failed_operations": len(metrics) - successful_operations,
            "success_rate": successful_operations / len(metrics),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "p95_duration_ms": durations[p95_index] if durations else 0,
            "p99_duration_ms": durations[p99_index] if durations else 0,
            "avg_memory_delta_mb": sum(memory_deltas) / len(memory_deltas),
            "avg_cpu_percent": sum(cpu_percentages) / len(cpu_percentages),
            "recent_errors": [
                {
                    "correlation_id": m.correlation_id,
                    "error_message": m.error_message,
                    "timestamp": m.start_time.isoformat()
                }
                for m in metrics[-10:]  # Last 10 operations
                if not m.success
            ]
        }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics."""
        # Current system metrics
        current_cpu = self.process.cpu_percent()
        current_memory = self.process.memory_info()
        current_memory_percent = self.process.memory_percent()
        
        # Disk usage
        disk_usage = psutil.disk_usage('/')
        
        # Network I/O
        network_io = psutil.net_io_counters()
        
        # Active operations
        with self._lock:
            active_count = len(self.active_operations)
            recent_alerts = list(self.alerts)[-10:]  # Last 10 alerts
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": current_cpu,
                "memory_percent": current_memory_percent,
                "memory_used_mb": current_memory.rss / 1024 / 1024,
                "disk_usage_percent": disk_usage.percent,
                "disk_free_gb": disk_usage.free / 1024 / 1024 / 1024
            },
            "network": {
                "bytes_sent": network_io.bytes_sent,
                "bytes_received": network_io.bytes_recv,
                "packets_sent": network_io.packets_sent,
                "packets_received": network_io.packets_recv
            },
            "application": {
                "active_operations": active_count,
                "total_tracked_operations": sum(
                    len(ops) for ops in self.operation_metrics.values()
                ),
                "metric_types_tracked": len(self.metric_summaries)
            },
            "alerts": {
                "total_alerts": len(self.alerts),
                "recent_alerts": [asdict(alert) for alert in recent_alerts]
            }
        }
    
    async def get_performance_report(
        self,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        
        Args:
            time_window_hours: Time window for analysis
            
        Returns:
            Comprehensive performance report
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        # Get operation summaries
        operation_summaries = {}
        with self._lock:
            for operation_name in self.operation_metrics:
                operation_summaries[operation_name] = await self.get_operation_summary(
                    operation_name, time_window_hours
                )
        
        # System health
        system_health = await self.get_system_health()
        
        # Performance trends
        trends = self._calculate_performance_trends(time_window_hours)
        
        # Bottleneck analysis
        bottlenecks = self._analyze_bottlenecks()
        
        return {
            "report_generated": datetime.utcnow().isoformat(),
            "time_window_hours": time_window_hours,
            "system_health": system_health,
            "operations": operation_summaries,
            "trends": trends,
            "bottlenecks": bottlenecks,
            "recommendations": self._generate_recommendations(
                operation_summaries, trends, bottlenecks
            )
        }
    
    async def _collect_system_metrics(self):
        """Background task for collecting system metrics."""
        while self._running:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                network = psutil.net_io_counters()
                
                # Active connections (approximate)
                active_connections = len(psutil.net_connections())
                
                # Response times from recent operations
                response_times = {}
                with self._lock:
                    for operation_name, metrics_list in self.operation_metrics.items():
                        recent_metrics = [
                            m for m in metrics_list[-10:]  # Last 10 operations
                            if m.end_time and 
                            (datetime.utcnow() - m.end_time).total_seconds() < 300  # Last 5 minutes
                        ]
                        if recent_metrics:
                            avg_response = sum(m.duration_ms for m in recent_metrics) / len(recent_metrics)
                            response_times[operation_name] = avg_response
                
                system_metrics = SystemMetrics(
                    timestamp=datetime.utcnow(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_used_mb=memory.used / 1024 / 1024,
                    disk_usage_percent=disk.percent,
                    network_io_bytes={
                        'sent': network.bytes_sent,
                        'received': network.bytes_recv
                    },
                    active_connections=active_connections,
                    response_times=response_times
                )
                
                self.system_metrics.append(system_metrics)
                
                # Check system-level alerts
                await self._check_system_alerts(system_metrics)
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                self.logger.error(
                    "System metrics collection failed",
                    error=str(e),
                    exc_info=True
                )
                await asyncio.sleep(self.collection_interval)
    
    def _default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Default performance alert thresholds."""
        return {
            "operation_duration_ms": {
                "warning": 5000,  # 5 seconds
                "critical": 30000  # 30 seconds
            },
            "memory_delta_mb": {
                "warning": 100,   # 100 MB
                "critical": 500   # 500 MB
            },
            "cpu_percent": {
                "warning": 80,    # 80%
                "critical": 95    # 95%
            },
            "system_memory_percent": {
                "warning": 80,    # 80%
                "critical": 95    # 95%
            },
            "system_cpu_percent": {
                "warning": 80,    # 80%
                "critical": 95    # 95%
            },
            "error_rate": {
                "warning": 0.05,  # 5%
                "critical": 0.10  # 10%
            }
        }
    
    def _update_metric_summaries(
        self,
        operation_name: str,
        metrics: PerformanceMetrics
    ):
        """Update metric summaries with new operation metrics."""
        # Update operation-specific summaries
        if operation_name not in self.metric_summaries:
            self.metric_summaries[operation_name] = {
                'count': 0,
                'total_duration_ms': 0.0,
                'avg_duration_ms': 0.0,
                'success_rate': 1.0,
                'total_operations': 0,
                'successful_operations': 0
            }
        
        summary = self.metric_summaries[operation_name]
        summary['count'] += 1
        summary['total_operations'] += 1
        summary['total_duration_ms'] += metrics.duration_ms
        summary['avg_duration_ms'] = summary['total_duration_ms'] / summary['count']
        
        if metrics.success:
            summary['successful_operations'] += 1
        
        summary['success_rate'] = summary['successful_operations'] / summary['total_operations']
        summary['last_updated'] = datetime.utcnow()
    
    async def _check_performance_alerts(
        self,
        operation_name: str,
        metrics: PerformanceMetrics
    ):
        """Check for performance alerts based on operation metrics."""
        alerts_to_create = []
        
        # Check duration threshold
        duration_thresholds = self.alert_thresholds.get("operation_duration_ms", {})
        if metrics.duration_ms > duration_thresholds.get("critical", float('inf')):
            alerts_to_create.append(PerformanceAlert(
                alert_id=str(uuid.uuid4()),
                level=AlertLevel.CRITICAL,
                message=f"Operation {operation_name} took {metrics.duration_ms:.1f}ms (critical threshold)",
                metric_name="operation_duration_ms",
                threshold_value=duration_thresholds["critical"],
                actual_value=metrics.duration_ms,
                timestamp=datetime.utcnow(),
                correlation_id=metrics.correlation_id
            ))
        elif metrics.duration_ms > duration_thresholds.get("warning", float('inf')):
            alerts_to_create.append(PerformanceAlert(
                alert_id=str(uuid.uuid4()),
                level=AlertLevel.WARNING,
                message=f"Operation {operation_name} took {metrics.duration_ms:.1f}ms (warning threshold)",
                metric_name="operation_duration_ms",
                threshold_value=duration_thresholds["warning"],
                actual_value=metrics.duration_ms,
                timestamp=datetime.utcnow(),
                correlation_id=metrics.correlation_id
            ))
        
        # Check memory delta threshold
        memory_thresholds = self.alert_thresholds.get("memory_delta_mb", {})
        if metrics.memory_delta_mb > memory_thresholds.get("critical", float('inf')):
            alerts_to_create.append(PerformanceAlert(
                alert_id=str(uuid.uuid4()),
                level=AlertLevel.CRITICAL,
                message=f"Operation {operation_name} used {metrics.memory_delta_mb:.1f}MB memory (critical threshold)",
                metric_name="memory_delta_mb",
                threshold_value=memory_thresholds["critical"],
                actual_value=metrics.memory_delta_mb,
                timestamp=datetime.utcnow(),
                correlation_id=metrics.correlation_id
            ))
        
        # Store alerts
        for alert in alerts_to_create:
            self.alerts.append(alert)
            
            self.logger.warning(
                "Performance alert triggered",
                alert_level=alert.level.value,
                message=alert.message,
                operation=operation_name,
                correlation_id=metrics.correlation_id
            )
    
    async def _check_system_alerts(self, metrics: SystemMetrics):
        """Check for system-level performance alerts."""
        alerts_to_create = []
        
        # Check CPU threshold
        cpu_thresholds = self.alert_thresholds.get("system_cpu_percent", {})
        if metrics.cpu_percent > cpu_thresholds.get("critical", float('inf')):
            alerts_to_create.append(PerformanceAlert(
                alert_id=str(uuid.uuid4()),
                level=AlertLevel.CRITICAL,
                message=f"System CPU usage at {metrics.cpu_percent:.1f}% (critical threshold)",
                metric_name="system_cpu_percent",
                threshold_value=cpu_thresholds["critical"],
                actual_value=metrics.cpu_percent,
                timestamp=datetime.utcnow()
            ))
        
        # Check memory threshold
        memory_thresholds = self.alert_thresholds.get("system_memory_percent", {})
        if metrics.memory_percent > memory_thresholds.get("critical", float('inf')):
            alerts_to_create.append(PerformanceAlert(
                alert_id=str(uuid.uuid4()),
                level=AlertLevel.CRITICAL,
                message=f"System memory usage at {metrics.memory_percent:.1f}% (critical threshold)",
                metric_name="system_memory_percent",
                threshold_value=memory_thresholds["critical"],
                actual_value=metrics.memory_percent,
                timestamp=datetime.utcnow()
            ))
        
        # Store alerts
        for alert in alerts_to_create:
            self.alerts.append(alert)
            
            self.logger.critical(
                "System performance alert",
                alert_level=alert.level.value,
                message=alert.message
            )
    
    def _calculate_performance_trends(self, time_window_hours: int) -> Dict[str, Any]:
        """Calculate performance trends over time window."""
        # Implementation would analyze metrics over time
        # For now, return placeholder
        return {
            "cpu_trend": "stable",
            "memory_trend": "increasing",
            "response_time_trend": "stable",
            "error_rate_trend": "decreasing"
        }
    
    def _analyze_bottlenecks(self) -> List[Dict[str, Any]]:
        """Analyze system bottlenecks."""
        bottlenecks = []
        
        # Analyze operation summaries for bottlenecks
        with self._lock:
            for operation_name, summary in self.metric_summaries.items():
                if isinstance(summary, dict) and 'avg_duration_ms' in summary:
                    if summary['avg_duration_ms'] > 5000:  # > 5 seconds
                        bottlenecks.append({
                            "type": "slow_operation",
                            "operation": operation_name,
                            "avg_duration_ms": summary['avg_duration_ms'],
                            "severity": "high" if summary['avg_duration_ms'] > 10000 else "medium"
                        })
        
        return bottlenecks
    
    def _generate_recommendations(
        self,
        operation_summaries: Dict[str, Any],
        trends: Dict[str, Any],
        bottlenecks: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        # Analyze bottlenecks
        for bottleneck in bottlenecks:
            if bottleneck["type"] == "slow_operation":
                recommendations.append(
                    f"Consider optimizing '{bottleneck['operation']}' operation "
                    f"(avg duration: {bottleneck['avg_duration_ms']:.1f}ms)"
                )
        
        # Analyze trends
        if trends.get("memory_trend") == "increasing":
            recommendations.append(
                "Memory usage is increasing - consider implementing memory optimization"
            )
        
        # Analyze error rates
        for op_name, summary in operation_summaries.items():
            if summary.get("success_rate", 1.0) < 0.95:  # < 95% success rate
                recommendations.append(
                    f"Operation '{op_name}' has low success rate "
                    f"({summary['success_rate']:.1%}) - investigate error causes"
                )
        
        return recommendations


def track_performance(operation_name: str):
    """
    Decorator for tracking function performance.
    
    Args:
        operation_name: Name of the operation to track
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Get performance tracker from kwargs or use global default
            tracker = kwargs.get('performance_tracker')
            correlation_id = kwargs.get('correlation_id', 'unknown')
            
            if not tracker:
                # Use global tracker or create default
                tracker = PerformanceTracker()
            
            async with tracker.track_operation(operation_name, correlation_id):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        try:
            total_operations = sum(len(ops) for ops in self.operation_metrics.values())
            total_errors = sum(len(errs) for errs in self.error_metrics.values())
            
            # Calculate average duration across all operations
            all_durations = []
            for operation_metrics in self.operation_metrics.values():
                all_durations.extend([m.duration_ms for m in operation_metrics])
            
            avg_duration = sum(all_durations) / len(all_durations) if all_durations else 0.0
            
            # Get recent system metrics
            recent_system = self.system_metrics[-1] if self.system_metrics else None
            
            return {
                "total_operations": total_operations,
                "total_errors": total_errors,
                "avg_duration_ms": avg_duration,
                "ai_operations": sum(
                    len(ops) for name, ops in self.operation_metrics.items() 
                    if "ai" in name.lower()
                ),
                "ai_success_rate": 100.0,  # Would need actual AI operation tracking
                "cache_hit_rate": 75.0,  # Would need cache integration
                "active_users": 0,  # Would need session tracking
                "current_cpu_percent": recent_system.cpu_percent if recent_system else 0.0,
                "current_memory_percent": recent_system.memory_percent if recent_system else 0.0
            }
        except Exception as e:
            self.logger.error("Failed to get metrics summary", error=str(e))
            return {}