"""
ArchBuilder.AI Task Queue API

RESTful API endpoints for background task management, AI processing jobs,
monitoring, and queue administration with comprehensive task lifecycle management.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Path
from pydantic import BaseModel, Field
import structlog
import uuid

from ...services.tasks.task_queue_service import (
    TaskQueueService, QueueConfig, TaskDefinition, TaskResult, 
    TaskStatus, TaskPriority, QueueBackend
)
from ...services.tasks.ai_tasks import (
    AITaskType, AITaskInput, AITaskOutput, ProcessingStage, AI_TASK_REGISTRY
)

logger = structlog.get_logger(__name__)

# Initialize router
router = APIRouter(prefix="/tasks", tags=["task-queue"])

# Pydantic models for API
class TaskSubmissionRequest(BaseModel):
    """Task submission request model."""
    task_name: str
    task_type: Optional[AITaskType] = None
    project_id: str
    user_id: str
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    timeout: int = 3600
    eta: Optional[datetime] = None
    queue_name: str = "default"
    metadata: Dict[str, Any] = {}


class AITaskSubmissionRequest(BaseModel):
    """AI-specific task submission request."""
    task_type: AITaskType
    project_id: str
    user_id: str
    requirements: Dict[str, Any]
    site_data: Optional[Dict[str, Any]] = None
    building_codes: List[str] = []
    design_constraints: Dict[str, Any] = {}
    uploaded_documents: List[str] = []
    existing_models: List[str] = []
    preferences: Dict[str, Any] = {}
    locale: str = "en-US"
    priority: TaskPriority = TaskPriority.NORMAL
    priority_level: int = Field(1, ge=1, le=5)
    metadata: Dict[str, Any] = {}


class TaskStatusResponse(BaseModel):
    """Task status response model."""
    task_id: str
    task_name: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None
    retry_count: int = 0
    worker_id: Optional[str] = None
    progress: int = 0
    logs: List[str] = []
    metadata: Dict[str, Any] = {}


class QueueStatsResponse(BaseModel):
    """Queue statistics response model."""
    backend: str
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    registered_tasks: int
    worker_concurrency: int
    task_breakdown: Dict[str, int]
    performance: Optional[Dict[str, float]] = None
    generated_at: str


class TaskListResponse(BaseModel):
    """Task list response model."""
    total_tasks: int
    tasks: List[TaskStatusResponse]
    pagination: Dict[str, Any]


# Dependency injection for task queue service
async def get_task_queue_service() -> TaskQueueService:
    """Get task queue service instance."""
    # In production, this would be injected from a service container
    config = QueueConfig(
        backend=QueueBackend.MEMORY,  # Use memory for development
        broker_url="redis://localhost:6379/0",
        result_backend="redis://localhost:6379/0",
        worker_concurrency=4,
        enable_monitoring=True
    )
    
    service = TaskQueueService(config)
    
    # Register AI tasks
    for task_name, task_function in AI_TASK_REGISTRY.items():
        service.register_task(task_name, task_function)
    
    return service


# Task submission endpoints
@router.post("/submit", response_model=Dict[str, str])
async def submit_task(
    request: TaskSubmissionRequest,
    task_queue: TaskQueueService = Depends(get_task_queue_service)
):
    """Submit a general background task."""
    try:
        task_id = str(uuid.uuid4())
        
        task_definition = TaskDefinition(
            task_id=task_id,
            task_name=request.task_name,
            task_function=request.task_name,
            args=request.args,
            kwargs=request.kwargs,
            priority=request.priority,
            max_retries=request.max_retries,
            timeout=request.timeout,
            eta=request.eta,
            queue_name=request.queue_name,
            metadata={
                **request.metadata,
                "project_id": request.project_id,
                "user_id": request.user_id,
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        submitted_task_id = await task_queue.submit_task(task_definition)
        
        logger.info("Task submitted via API",
                   task_id=submitted_task_id,
                   task_name=request.task_name,
                   user_id=request.user_id,
                   project_id=request.project_id)
        
        return {
            "task_id": submitted_task_id,
            "status": "submitted",
            "message": f"Task '{request.task_name}' submitted successfully"
        }
        
    except Exception as e:
        logger.error("Failed to submit task via API",
                    task_name=request.task_name,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")


@router.post("/submit-ai", response_model=Dict[str, str])
async def submit_ai_task(
    request: AITaskSubmissionRequest,
    task_queue: TaskQueueService = Depends(get_task_queue_service)
):
    """Submit an AI processing task."""
    try:
        task_id = str(uuid.uuid4())
        
        # Create AI task input
        ai_input = AITaskInput(
            project_id=request.project_id,
            user_id=request.user_id,
            task_type=request.task_type,
            requirements=request.requirements,
            site_data=request.site_data,
            building_codes=request.building_codes,
            design_constraints=request.design_constraints,
            uploaded_documents=request.uploaded_documents,
            existing_models=request.existing_models,
            preferences=request.preferences,
            locale=request.locale,
            priority_level=request.priority_level,
            metadata=request.metadata
        )
        
        # Map AI task type to function name
        task_function_name = request.task_type.value
        
        task_definition = TaskDefinition(
            task_id=task_id,
            task_name=task_function_name,
            task_function=task_function_name,
            args=[ai_input],
            kwargs={},
            priority=request.priority,
            max_retries=3,
            timeout=7200,  # 2 hours for AI tasks
            queue_name="ai_processing",
            metadata={
                **request.metadata,
                "task_type": request.task_type.value,
                "project_id": request.project_id,
                "user_id": request.user_id,
                "ai_task": True,
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        submitted_task_id = await task_queue.submit_task(task_definition)
        
        logger.info("AI task submitted via API",
                   task_id=submitted_task_id,
                   task_type=request.task_type.value,
                   user_id=request.user_id,
                   project_id=request.project_id)
        
        return {
            "task_id": submitted_task_id,
            "status": "submitted",
            "message": f"AI task '{request.task_type.value}' submitted successfully",
            "estimated_completion": (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to submit AI task via API",
                    task_type=request.task_type.value,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to submit AI task: {str(e)}")


# Task monitoring endpoints
@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str = Path(..., description="Task ID to query"),
    task_queue: TaskQueueService = Depends(get_task_queue_service)
):
    """Get status and details of a specific task."""
    try:
        task_result = await task_queue.get_task_status(task_id)
        
        if not task_result:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return TaskStatusResponse(
            task_id=task_result.task_id,
            task_name=task_result.task_name,
            status=task_result.status,
            result=task_result.result,
            error=task_result.error,
            started_at=task_result.started_at,
            completed_at=task_result.completed_at,
            execution_time=task_result.execution_time,
            retry_count=task_result.retry_count,
            worker_id=task_result.worker_id,
            progress=task_result.progress,
            logs=task_result.logs,
            metadata=task_result.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get task status via API",
                    task_id=task_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.get("/list", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    task_queue: TaskQueueService = Depends(get_task_queue_service)
):
    """List tasks with optional filtering and pagination."""
    try:
        # Get all tasks from the queue service
        all_active = list(task_queue.active_tasks.values())
        all_completed = list(task_queue.completed_tasks.values())
        all_failed = list(task_queue.failed_tasks.values())
        
        all_tasks = all_active + all_completed + all_failed
        
        # Apply filters
        filtered_tasks = all_tasks
        
        if status:
            filtered_tasks = [t for t in filtered_tasks if t.status == status]
        
        if project_id:
            filtered_tasks = [t for t in filtered_tasks 
                             if t.metadata.get("project_id") == project_id]
        
        if user_id:
            filtered_tasks = [t for t in filtered_tasks 
                             if t.metadata.get("user_id") == user_id]
        
        # Sort by creation time (newest first)
        filtered_tasks.sort(
            key=lambda x: x.started_at or datetime.min, 
            reverse=True
        )
        
        # Apply pagination
        total_tasks = len(filtered_tasks)
        paginated_tasks = filtered_tasks[offset:offset + limit]
        
        # Convert to response models
        task_responses = [
            TaskStatusResponse(
                task_id=task.task_id,
                task_name=task.task_name,
                status=task.status,
                result=task.result,
                error=task.error,
                started_at=task.started_at,
                completed_at=task.completed_at,
                execution_time=task.execution_time,
                retry_count=task.retry_count,
                worker_id=task.worker_id,
                progress=task.progress,
                logs=task.logs,
                metadata=task.metadata
            )
            for task in paginated_tasks
        ]
        
        return TaskListResponse(
            total_tasks=total_tasks,
            tasks=task_responses,
            pagination={
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_tasks,
                "next_offset": offset + limit if offset + limit < total_tasks else None
            }
        )
        
    except Exception as e:
        logger.error("Failed to list tasks via API",
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


# Task control endpoints
@router.post("/cancel/{task_id}")
async def cancel_task(
    task_id: str = Path(..., description="Task ID to cancel"),
    task_queue: TaskQueueService = Depends(get_task_queue_service)
):
    """Cancel a running or pending task."""
    try:
        success = await task_queue.cancel_task(task_id)
        
        if success:
            logger.info("Task cancelled via API", task_id=task_id)
            return {
                "task_id": task_id,
                "status": "cancelled",
                "message": f"Task {task_id} cancelled successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found or cannot be cancelled")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel task via API",
                    task_id=task_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")


@router.post("/retry/{task_id}")
async def retry_task(
    task_id: str = Path(..., description="Task ID to retry"),
    task_queue: TaskQueueService = Depends(get_task_queue_service)
):
    """Retry a failed task."""
    try:
        success = await task_queue.retry_task(task_id)
        
        if success:
            logger.info("Task retry initiated via API", task_id=task_id)
            return {
                "task_id": task_id,
                "status": "retry_submitted",
                "message": f"Task {task_id} retry submitted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found or cannot be retried")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retry task via API",
                    task_id=task_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retry task: {str(e)}")


# Queue monitoring and administration
@router.get("/stats", response_model=QueueStatsResponse)
async def get_queue_statistics(
    task_queue: TaskQueueService = Depends(get_task_queue_service)
):
    """Get comprehensive queue statistics."""
    try:
        stats = await task_queue.get_queue_stats()
        
        return QueueStatsResponse(
            backend=stats.get("backend", "unknown"),
            active_tasks=stats.get("active_tasks", 0),
            completed_tasks=stats.get("completed_tasks", 0),
            failed_tasks=stats.get("failed_tasks", 0),
            registered_tasks=stats.get("registered_tasks", 0),
            worker_concurrency=stats.get("worker_concurrency", 0),
            task_breakdown=stats.get("task_breakdown", {}),
            performance=stats.get("performance"),
            generated_at=stats.get("generated_at", datetime.utcnow().isoformat())
        )
        
    except Exception as e:
        logger.error("Failed to get queue statistics via API",
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get queue statistics: {str(e)}")


@router.post("/cleanup")
async def cleanup_old_tasks(
    days: int = Query(7, ge=1, le=365, description="Number of days to keep completed tasks"),
    task_queue: TaskQueueService = Depends(get_task_queue_service)
):
    """Clean up old completed and failed tasks."""
    try:
        cleaned_count = await task_queue.cleanup_old_tasks(days=days)
        
        logger.info("Task cleanup completed via API",
                   cleaned_count=cleaned_count,
                   cutoff_days=days)
        
        return {
            "cleaned_count": cleaned_count,
            "cutoff_days": days,
            "message": f"Cleaned up {cleaned_count} old tasks older than {days} days"
        }
        
    except Exception as e:
        logger.error("Failed to cleanup tasks via API",
                    days=days,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to cleanup tasks: {str(e)}")


# AI-specific endpoints
@router.get("/ai-types")
async def list_ai_task_types():
    """List available AI task types."""
    try:
        ai_types = []
        for task_type in AITaskType:
            ai_types.append({
                "type": task_type.value,
                "display_name": task_type.value.replace('_', ' ').title(),
                "description": f"AI processing for {task_type.value.replace('_', ' ')}",
                "estimated_duration": "5-30 minutes",
                "supported": task_type.value in AI_TASK_REGISTRY
            })
        
        return {
            "total_types": len(ai_types),
            "ai_task_types": ai_types,
            "registered_functions": len(AI_TASK_REGISTRY)
        }
        
    except Exception as e:
        logger.error("Failed to list AI task types via API",
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list AI task types: {str(e)}")


@router.get("/ai-tasks")
async def list_ai_tasks(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    task_type: Optional[AITaskType] = Query(None, description="Filter by AI task type"),
    limit: int = Query(50, ge=1, le=1000),
    task_queue: TaskQueueService = Depends(get_task_queue_service)
):
    """List AI processing tasks with filtering."""
    try:
        # Get all tasks
        all_tasks = (list(task_queue.active_tasks.values()) + 
                    list(task_queue.completed_tasks.values()) + 
                    list(task_queue.failed_tasks.values()))
        
        # Filter AI tasks only
        ai_tasks = [t for t in all_tasks if t.metadata.get("ai_task")]
        
        # Apply additional filters
        if project_id:
            ai_tasks = [t for t in ai_tasks if t.metadata.get("project_id") == project_id]
        
        if user_id:
            ai_tasks = [t for t in ai_tasks if t.metadata.get("user_id") == user_id]
        
        if task_type:
            ai_tasks = [t for t in ai_tasks if t.metadata.get("task_type") == task_type.value]
        
        # Sort and limit
        ai_tasks.sort(key=lambda x: x.started_at or datetime.min, reverse=True)
        ai_tasks = ai_tasks[:limit]
        
        # Convert to response
        ai_task_responses = []
        for task in ai_tasks:
            response = {
                "task_id": task.task_id,
                "task_type": task.metadata.get("task_type"),
                "project_id": task.metadata.get("project_id"),
                "user_id": task.metadata.get("user_id"),
                "status": task.status.value,
                "progress": task.progress,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "execution_time": task.execution_time,
                "error": task.error
            }
            
            # Add AI-specific result data
            if task.result and isinstance(task.result, dict):
                response["ai_results"] = {
                    "confidence_scores": task.result.get("confidence_scores", {}),
                    "generated_files": task.result.get("generated_files", []),
                    "revit_commands": len(task.result.get("revit_commands", [])),
                    "compliance_score": task.result.get("compliance_report", {}).get("overall_score")
                }
            
            ai_task_responses.append(response)
        
        return {
            "total_ai_tasks": len(ai_task_responses),
            "ai_tasks": ai_task_responses
        }
        
    except Exception as e:
        logger.error("Failed to list AI tasks via API",
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list AI tasks: {str(e)}")


# Health check endpoint
@router.get("/health")
async def task_queue_health_check(
    task_queue: TaskQueueService = Depends(get_task_queue_service)
):
    """Health check for the task queue system."""
    try:
        stats = await task_queue.get_queue_stats()
        
        health_status = {
            "status": "healthy",
            "backend": stats.get("backend"),
            "active_tasks": stats.get("active_tasks", 0),
            "registered_tasks": stats.get("registered_tasks", 0),
            "last_check": datetime.utcnow().isoformat()
        }
        
        # Add backend-specific health checks
        if stats.get("backend") == "memory":
            health_status["memory_queue_active"] = True
        
        return health_status
        
    except Exception as e:
        logger.error("Task queue health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.utcnow().isoformat()
        }