"""
ArchBuilder.AI Task Monitoring Dashboard

Real-time monitoring dashboard for task queue performance, worker status,
AI processing jobs, and system health metrics with comprehensive analytics.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import json
import structlog

from ...services.tasks.task_queue_service import TaskQueueService, TaskStatus
from ...services.tasks.worker_management import WorkerManager, WorkerStatus
from ...services.tasks.ai_tasks import AITaskType

logger = structlog.get_logger(__name__)

# Initialize router and templates
router = APIRouter(prefix="/dashboard", tags=["monitoring"])
templates = Jinja2Templates(directory="templates/dashboard")


class MonitoringService:
    """Service for generating monitoring and analytics data."""
    
    def __init__(self, task_queue: TaskQueueService, worker_manager: WorkerManager):
        self.task_queue = task_queue
        self.worker_manager = worker_manager
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time system metrics."""
        try:
            # Get queue statistics
            queue_stats = await self.task_queue.get_queue_stats()
            
            # Get worker status
            worker_status = self.worker_manager.get_worker_status()
            
            # Calculate real-time metrics
            current_time = datetime.utcnow()
            
            metrics = {
                "timestamp": current_time.isoformat(),
                "system_overview": {
                    "total_workers": worker_status["total_workers"],
                    "active_tasks": queue_stats.get("active_tasks", 0),
                    "completed_tasks": queue_stats.get("completed_tasks", 0),
                    "failed_tasks": queue_stats.get("failed_tasks", 0),
                    "pending_tasks": queue_stats.get("pending_tasks", 0),
                    "system_health": self._calculate_system_health(queue_stats, worker_status)
                },
                "queue_performance": {
                    "throughput_per_hour": queue_stats.get("performance", {}).get("throughput_per_hour", 0),
                    "average_processing_time": queue_stats.get("performance", {}).get("avg_processing_time", 0),
                    "success_rate": self._calculate_success_rate(queue_stats),
                    "queue_depth": queue_stats.get("pending_tasks", 0),
                    "backend_type": queue_stats.get("backend", "memory")
                },
                "worker_metrics": {
                    "total_workers": worker_status["total_workers"],
                    "active_workers": worker_status["worker_breakdown"].get("running", 0) + 
                                    worker_status["worker_breakdown"].get("busy", 0),
                    "idle_workers": worker_status["worker_breakdown"].get("idle", 0),
                    "error_workers": worker_status["worker_breakdown"].get("error", 0),
                    "average_cpu": self._calculate_average_metric(worker_status["workers"], "cpu_percent"),
                    "average_memory": self._calculate_average_metric(worker_status["workers"], "memory_mb"),
                    "total_throughput": worker_status["aggregate_metrics"]["average_throughput"]
                },
                "ai_processing": await self._get_ai_metrics(),
                "alerts": await self._get_current_alerts(queue_stats, worker_status)
            }
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get real-time metrics", error=str(e))
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def get_historical_data(self, hours: int = 24) -> Dict[str, Any]:
        """Get historical performance data."""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # In a production system, this would query a time-series database
            # For now, we'll simulate historical data
            
            historical_data = {
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "hours": hours
                },
                "task_completion_timeline": self._generate_timeline_data(start_time, end_time),
                "worker_utilization": self._generate_worker_utilization_data(start_time, end_time),
                "ai_task_breakdown": await self._get_ai_task_breakdown(),
                "performance_trends": {
                    "throughput_trend": self._generate_throughput_trend(start_time, end_time),
                    "error_rate_trend": self._generate_error_rate_trend(start_time, end_time),
                    "response_time_trend": self._generate_response_time_trend(start_time, end_time)
                },
                "resource_usage": {
                    "cpu_usage": self._generate_cpu_usage_data(start_time, end_time),
                    "memory_usage": self._generate_memory_usage_data(start_time, end_time),
                    "queue_depth": self._generate_queue_depth_data(start_time, end_time)
                }
            }
            
            return historical_data
            
        except Exception as e:
            logger.error("Failed to get historical data", error=str(e))
            return {"error": str(e)}
    
    async def get_task_analytics(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed task analytics."""
        try:
            # Get all tasks for analysis
            all_tasks = (list(self.task_queue.active_tasks.values()) + 
                        list(self.task_queue.completed_tasks.values()) + 
                        list(self.task_queue.failed_tasks.values()))
            
            # Filter by project if specified
            if project_id:
                all_tasks = [t for t in all_tasks if t.metadata.get("project_id") == project_id]
            
            analytics = {
                "total_tasks": len(all_tasks),
                "status_breakdown": self._analyze_task_status(all_tasks),
                "task_type_breakdown": self._analyze_task_types(all_tasks),
                "execution_time_stats": self._analyze_execution_times(all_tasks),
                "error_analysis": self._analyze_task_errors(all_tasks),
                "user_activity": self._analyze_user_activity(all_tasks),
                "project_breakdown": self._analyze_project_breakdown(all_tasks),
                "ai_task_performance": await self._analyze_ai_task_performance(all_tasks),
                "trends": {
                    "completion_rate": self._calculate_completion_rate(all_tasks),
                    "average_retry_count": self._calculate_average_retries(all_tasks),
                    "peak_processing_hours": self._analyze_peak_hours(all_tasks)
                }
            }
            
            return analytics
            
        except Exception as e:
            logger.error("Failed to get task analytics", error=str(e))
            return {"error": str(e)}
    
    def _calculate_system_health(self, queue_stats: Dict, worker_status: Dict) -> str:
        """Calculate overall system health score."""
        try:
            health_score = 100
            
            # Check queue performance
            success_rate = self._calculate_success_rate(queue_stats)
            if success_rate < 0.9:
                health_score -= 20
            elif success_rate < 0.95:
                health_score -= 10
            
            # Check worker status
            total_workers = worker_status["total_workers"]
            error_workers = worker_status["worker_breakdown"].get("error", 0)
            
            if total_workers > 0:
                error_rate = error_workers / total_workers
                if error_rate > 0.2:
                    health_score -= 30
                elif error_rate > 0.1:
                    health_score -= 15
            
            # Check pending tasks
            pending_tasks = queue_stats.get("pending_tasks", 0)
            active_workers = worker_status["worker_breakdown"].get("running", 0) + \
                            worker_status["worker_breakdown"].get("busy", 0)
            
            if pending_tasks > active_workers * 5:
                health_score -= 25
            elif pending_tasks > active_workers * 2:
                health_score -= 10
            
            if health_score >= 90:
                return "excellent"
            elif health_score >= 75:
                return "good"
            elif health_score >= 60:
                return "fair"
            elif health_score >= 40:
                return "poor"
            else:
                return "critical"
                
        except Exception:
            return "unknown"
    
    def _calculate_success_rate(self, queue_stats: Dict) -> float:
        """Calculate task success rate."""
        completed = queue_stats.get("completed_tasks", 0)
        failed = queue_stats.get("failed_tasks", 0)
        total = completed + failed
        
        if total == 0:
            return 1.0
        
        return completed / total
    
    def _calculate_average_metric(self, workers: List[Dict], metric_key: str) -> float:
        """Calculate average metric across workers."""
        if not workers:
            return 0.0
        
        values = [w["metrics"][metric_key] for w in workers if metric_key in w["metrics"]]
        return sum(values) / len(values) if values else 0.0
    
    async def _get_ai_metrics(self) -> Dict[str, Any]:
        """Get AI-specific processing metrics."""
        try:
            # Get all AI tasks
            all_tasks = (list(self.task_queue.active_tasks.values()) + 
                        list(self.task_queue.completed_tasks.values()) + 
                        list(self.task_queue.failed_tasks.values()))
            
            ai_tasks = [t for t in all_tasks if t.metadata.get("ai_task")]
            
            metrics = {
                "total_ai_tasks": len(ai_tasks),
                "active_ai_tasks": len([t for t in ai_tasks if t.status == TaskStatus.RUNNING]),
                "completed_ai_tasks": len([t for t in ai_tasks if t.status == TaskStatus.COMPLETED]),
                "failed_ai_tasks": len([t for t in ai_tasks if t.status == TaskStatus.FAILED]),
                "ai_task_types": {},
                "average_ai_execution_time": 0.0,
                "ai_success_rate": 0.0
            }
            
            # Analyze by AI task type
            for task_type in AITaskType:
                type_tasks = [t for t in ai_tasks if t.metadata.get("task_type") == task_type.value]
                if type_tasks:
                    metrics["ai_task_types"][task_type.value] = {
                        "total": len(type_tasks),
                        "completed": len([t for t in type_tasks if t.status == TaskStatus.COMPLETED]),
                        "failed": len([t for t in type_tasks if t.status == TaskStatus.FAILED]),
                        "average_time": sum(t.execution_time or 0 for t in type_tasks) / len(type_tasks)
                    }
            
            # Calculate averages
            if ai_tasks:
                completed_ai = [t for t in ai_tasks if t.status == TaskStatus.COMPLETED]
                if completed_ai:
                    total_time = sum(t.execution_time or 0 for t in completed_ai)
                    metrics["average_ai_execution_time"] = total_time / len(completed_ai)
                
                success_count = len([t for t in ai_tasks if t.status == TaskStatus.COMPLETED])
                metrics["ai_success_rate"] = success_count / len(ai_tasks)
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get AI metrics", error=str(e))
            return {"error": str(e)}
    
    async def _get_current_alerts(self, queue_stats: Dict, worker_status: Dict) -> List[Dict]:
        """Get current system alerts."""
        alerts = []
        current_time = datetime.utcnow()
        
        try:
            # High queue depth alert
            pending_tasks = queue_stats.get("pending_tasks", 0)
            if pending_tasks > 100:
                alerts.append({
                    "severity": "high",
                    "type": "queue_depth",
                    "message": f"High queue depth: {pending_tasks} pending tasks",
                    "timestamp": current_time.isoformat(),
                    "action": "Consider scaling up workers"
                })
            
            # Worker error alert
            error_workers = worker_status["worker_breakdown"].get("error", 0)
            if error_workers > 0:
                alerts.append({
                    "severity": "medium",
                    "type": "worker_error",
                    "message": f"{error_workers} workers in error state",
                    "timestamp": current_time.isoformat(),
                    "action": "Check worker logs and restart if needed"
                })
            
            # Low success rate alert
            success_rate = self._calculate_success_rate(queue_stats)
            if success_rate < 0.8:
                alerts.append({
                    "severity": "high",
                    "type": "low_success_rate",
                    "message": f"Low task success rate: {success_rate:.1%}",
                    "timestamp": current_time.isoformat(),
                    "action": "Investigate task failures and system health"
                })
            
            # High resource usage alert
            avg_cpu = self._calculate_average_metric(worker_status["workers"], "cpu_percent")
            avg_memory = self._calculate_average_metric(worker_status["workers"], "memory_mb")
            
            if avg_cpu > 80:
                alerts.append({
                    "severity": "medium",
                    "type": "high_cpu",
                    "message": f"High average CPU usage: {avg_cpu:.1f}%",
                    "timestamp": current_time.isoformat(),
                    "action": "Monitor CPU usage and consider optimization"
                })
            
            if avg_memory > 1000:  # 1GB
                alerts.append({
                    "severity": "medium",
                    "type": "high_memory",
                    "message": f"High average memory usage: {avg_memory:.1f} MB",
                    "timestamp": current_time.isoformat(),
                    "action": "Monitor memory usage and check for leaks"
                })
            
            return alerts
            
        except Exception as e:
            logger.error("Failed to get current alerts", error=str(e))
            return [{"severity": "low", "type": "monitoring_error", 
                    "message": f"Alert system error: {str(e)}", 
                    "timestamp": current_time.isoformat()}]
    
    # Placeholder methods for historical data generation
    # In production, these would query actual time-series data
    
    def _generate_timeline_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Generate task completion timeline data."""
        # This would query actual historical data
        return []
    
    def _generate_worker_utilization_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Generate worker utilization historical data."""
        return []
    
    async def _get_ai_task_breakdown(self) -> Dict[str, int]:
        """Get breakdown of AI tasks by type."""
        # Get current AI tasks for analysis
        return {task_type.value: 0 for task_type in AITaskType}
    
    def _generate_throughput_trend(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Generate throughput trend data."""
        return []
    
    def _generate_error_rate_trend(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Generate error rate trend data."""
        return []
    
    def _generate_response_time_trend(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Generate response time trend data."""
        return []
    
    def _generate_cpu_usage_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Generate CPU usage historical data."""
        return []
    
    def _generate_memory_usage_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Generate memory usage historical data."""
        return []
    
    def _generate_queue_depth_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Generate queue depth historical data."""
        return []
    
    def _analyze_task_status(self, tasks: List) -> Dict[str, int]:
        """Analyze task status distribution."""
        status_counts = {}
        for task in tasks:
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts
    
    def _analyze_task_types(self, tasks: List) -> Dict[str, int]:
        """Analyze task type distribution."""
        type_counts = {}
        for task in tasks:
            task_type = task.metadata.get("task_type", task.task_name)
            type_counts[task_type] = type_counts.get(task_type, 0) + 1
        return type_counts
    
    def _analyze_execution_times(self, tasks: List) -> Dict[str, float]:
        """Analyze task execution time statistics."""
        execution_times = [t.execution_time for t in tasks if t.execution_time]
        
        if not execution_times:
            return {"average": 0, "min": 0, "max": 0, "median": 0}
        
        execution_times.sort()
        return {
            "average": sum(execution_times) / len(execution_times),
            "min": min(execution_times),
            "max": max(execution_times),
            "median": execution_times[len(execution_times) // 2],
            "count": len(execution_times)
        }
    
    def _analyze_task_errors(self, tasks: List) -> Dict[str, Any]:
        """Analyze task error patterns."""
        failed_tasks = [t for t in tasks if t.status == TaskStatus.FAILED]
        error_patterns = {}
        
        for task in failed_tasks:
            error = task.error or "Unknown error"
            error_type = error.split(":")[0] if ":" in error else error
            error_patterns[error_type] = error_patterns.get(error_type, 0) + 1
        
        return {
            "total_errors": len(failed_tasks),
            "error_patterns": error_patterns,
            "error_rate": len(failed_tasks) / len(tasks) if tasks else 0
        }
    
    def _analyze_user_activity(self, tasks: List) -> Dict[str, int]:
        """Analyze user activity patterns."""
        user_counts = {}
        for task in tasks:
            user_id = task.metadata.get("user_id", "unknown")
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        return user_counts
    
    def _analyze_project_breakdown(self, tasks: List) -> Dict[str, int]:
        """Analyze task distribution by project."""
        project_counts = {}
        for task in tasks:
            project_id = task.metadata.get("project_id", "unknown")
            project_counts[project_id] = project_counts.get(project_id, 0) + 1
        return project_counts
    
    async def _analyze_ai_task_performance(self, tasks: List) -> Dict[str, Any]:
        """Analyze AI task performance metrics."""
        ai_tasks = [t for t in tasks if t.metadata.get("ai_task")]
        
        if not ai_tasks:
            return {"total_ai_tasks": 0}
        
        performance = {
            "total_ai_tasks": len(ai_tasks),
            "by_type": {},
            "average_confidence": 0.0,
            "success_rate": 0.0
        }
        
        # Analyze by AI task type
        for task_type in AITaskType:
            type_tasks = [t for t in ai_tasks if t.metadata.get("task_type") == task_type.value]
            if type_tasks:
                completed = [t for t in type_tasks if t.status == TaskStatus.COMPLETED]
                performance["by_type"][task_type.value] = {
                    "total": len(type_tasks),
                    "completed": len(completed),
                    "success_rate": len(completed) / len(type_tasks),
                    "average_time": sum(t.execution_time or 0 for t in completed) / len(completed) if completed else 0
                }
        
        return performance
    
    def _calculate_completion_rate(self, tasks: List) -> float:
        """Calculate task completion rate."""
        if not tasks:
            return 0.0
        
        completed = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        return completed / len(tasks)
    
    def _calculate_average_retries(self, tasks: List) -> float:
        """Calculate average retry count."""
        if not tasks:
            return 0.0
        
        total_retries = sum(t.retry_count for t in tasks)
        return total_retries / len(tasks)
    
    def _analyze_peak_hours(self, tasks: List) -> Dict[int, int]:
        """Analyze peak processing hours."""
        hour_counts = {}
        
        for task in tasks:
            if task.started_at:
                hour = task.started_at.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        return hour_counts


# Dependency injection
async def get_monitoring_service() -> MonitoringService:
    """Get monitoring service instance."""
    # In production, these would be injected
    from ...services.tasks.task_queue_service import TaskQueueService, QueueConfig, QueueBackend
    from ...services.tasks.worker_management import WorkerManager
    
    config = QueueConfig(backend=QueueBackend.MEMORY)
    task_queue = TaskQueueService(config)
    worker_manager = WorkerManager(task_queue)
    
    return MonitoringService(task_queue, worker_manager)


# API endpoints for dashboard data
@router.get("/api/metrics")
async def get_real_time_metrics(
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get real-time system metrics for dashboard."""
    return await monitoring.get_real_time_metrics()


@router.get("/api/historical")
async def get_historical_data(
    hours: int = Query(24, ge=1, le=168, description="Hours of historical data"),
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get historical performance data."""
    return await monitoring.get_historical_data(hours)


@router.get("/api/analytics")
async def get_task_analytics(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get detailed task analytics."""
    return await monitoring.get_task_analytics(project_id)


# HTML dashboard endpoints
@router.get("/", response_class=HTMLResponse)
async def dashboard_home(
    request: Request,
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Main dashboard page."""
    try:
        metrics = await monitoring.get_real_time_metrics()
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "metrics": metrics,
            "page_title": "ArchBuilder.AI Task Queue Dashboard"
        })
    except Exception as e:
        logger.error("Dashboard error", error=str(e))
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })


@router.get("/workers", response_class=HTMLResponse)
async def workers_dashboard(
    request: Request,
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Worker monitoring dashboard."""
    try:
        worker_status = monitoring.worker_manager.get_worker_status()
        return templates.TemplateResponse("workers.html", {
            "request": request,
            "worker_status": worker_status,
            "page_title": "Worker Status - ArchBuilder.AI"
        })
    except Exception as e:
        logger.error("Worker dashboard error", error=str(e))
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(
    request: Request,
    project_id: Optional[str] = Query(None),
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Analytics dashboard."""
    try:
        analytics = await monitoring.get_task_analytics(project_id)
        return templates.TemplateResponse("analytics.html", {
            "request": request,
            "analytics": analytics,
            "project_id": project_id,
            "page_title": "Analytics - ArchBuilder.AI"
        })
    except Exception as e:
        logger.error("Analytics dashboard error", error=str(e))
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })