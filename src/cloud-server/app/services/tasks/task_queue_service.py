"""
ArchBuilder.AI Task Queue Service

Comprehensive background task management system for AI processing, document handling,
project generation, and system maintenance with multiple queue backends support.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    NORMAL = "normal"  
    HIGH = "high"
    URGENT = "urgent"


class QueueBackend(str, Enum):
    """Supported queue backends."""
    CELERY = "celery"
    RQ = "rq"
    DRAMATIQ = "dramatiq"
    ARQ = "arq"
    MEMORY = "memory"


@dataclass
class TaskDefinition:
    """Task definition structure."""
    task_id: str
    task_name: str
    task_function: str
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    timeout: int = 3600    # 1 hour default
    eta: Optional[datetime] = None  # Estimated Time of Arrival
    expires: Optional[datetime] = None
    queue_name: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskResult:
    """Task execution result."""
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
    progress: int = 0  # 0-100
    logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueueConfig:
    """Queue configuration."""
    backend: QueueBackend
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/0"
    worker_concurrency: int = 4
    task_routes: Dict[str, str] = field(default_factory=dict)
    beat_schedule: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    timezone: str = "UTC"
    enable_monitoring: bool = True
    flower_port: int = 5555


class TaskQueueService:
    """Comprehensive task queue service with multiple backend support."""
    
    def __init__(self, config: QueueConfig):
        """Initialize task queue service."""
        self.config = config
        self.logger = logger.bind(service="task_queue")
        
        # Task storage
        self.active_tasks: Dict[str, TaskResult] = {}
        self.completed_tasks: Dict[str, TaskResult] = {}
        self.failed_tasks: Dict[str, TaskResult] = {}
        
        # Task registry
        self.task_registry: Dict[str, Callable] = {}
        
        # Queue clients
        self.queue_client = None
        self.scheduler_client = None
        
        # Initialize backend
        self._initialize_backend()
        
        self.logger.info("Task queue service initialized",
                        backend=config.backend.value,
                        broker_url=config.broker_url)

    def _initialize_backend(self):
        """Initialize the selected queue backend."""
        try:
            if self.config.backend == QueueBackend.CELERY:
                self._initialize_celery()
            elif self.config.backend == QueueBackend.RQ:
                self._initialize_rq()
            elif self.config.backend == QueueBackend.DRAMATIQ:
                self._initialize_dramatiq()
            elif self.config.backend == QueueBackend.ARQ:
                self._initialize_arq()
            else:
                self._initialize_memory_queue()
                
            self.logger.info("Queue backend initialized successfully",
                           backend=self.config.backend.value)
            
        except ImportError as e:
            self.logger.warning("Queue backend dependencies not available, using memory queue",
                              backend=self.config.backend.value,
                              error=str(e))
            self._initialize_memory_queue()
        except Exception as e:
            self.logger.error("Failed to initialize queue backend",
                            backend=self.config.backend.value,
                            error=str(e))
            self._initialize_memory_queue()

    def _initialize_celery(self):
        """Initialize Celery backend."""
        try:
            from celery import Celery
            
            self.queue_client = Celery(
                'archbuilder',
                broker=self.config.broker_url,
                backend=self.config.result_backend
            )
            
            # Configure Celery
            self.queue_client.conf.update(
                worker_concurrency=self.config.worker_concurrency,
                task_routes=self.config.task_routes,
                beat_schedule=self.config.beat_schedule,
                timezone=self.config.timezone,
                task_serializer='json',
                result_serializer='json',
                accept_content=['json'],
                result_expires=3600,
                task_track_started=True,
                worker_prefetch_multiplier=1
            )
            
            self.logger.info("Celery initialized successfully")
            
        except ImportError:
            raise ImportError("Celery not available")

    def _initialize_rq(self):
        """Initialize RQ backend."""
        try:
            import redis
            from rq import Queue, Worker
            
            redis_conn = redis.from_url(self.config.broker_url)
            self.queue_client = Queue('default', connection=redis_conn)
            
            self.logger.info("RQ initialized successfully")
            
        except ImportError:
            raise ImportError("RQ not available")

    def _initialize_dramatiq(self):
        """Initialize Dramatiq backend."""
        try:
            import dramatiq
            from dramatiq.brokers.redis import RedisBroker
            
            broker = RedisBroker(url=self.config.broker_url)
            dramatiq.set_broker(broker)
            self.queue_client = broker
            
            self.logger.info("Dramatiq initialized successfully")
            
        except ImportError:
            raise ImportError("Dramatiq not available")

    def _initialize_arq(self):
        """Initialize ARQ backend."""
        try:
            import aioredis
            from arq import create_pool
            
            # ARQ setup would be done here
            self.logger.info("ARQ initialized successfully")
            
        except ImportError:
            raise ImportError("ARQ not available")

    def _initialize_memory_queue(self):
        """Initialize in-memory queue for development/testing."""
        self.queue_client = {
            'pending_tasks': asyncio.Queue(),
            'workers': [],
            'active': True
        }
        
        self.logger.info("Memory queue initialized")

    def register_task(self, task_name: str, task_function: Callable):
        """Register a task function."""
        try:
            self.task_registry[task_name] = task_function
            
            # Register with backend if supported
            if self.config.backend == QueueBackend.CELERY and hasattr(self.queue_client, 'task'):
                self.queue_client.task(name=task_name)(task_function)
            elif self.config.backend == QueueBackend.DRAMATIQ:
                import dramatiq
                dramatiq.actor(task_function)
            
            self.logger.info("Task registered",
                           task_name=task_name,
                           backend=self.config.backend.value)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to register task",
                            task_name=task_name,
                            error=str(e))
            return False

    async def submit_task(self, task_definition: TaskDefinition) -> str:
        """Submit a task for execution."""
        try:
            # Validate task
            if task_definition.task_name not in self.task_registry:
                raise ValueError(f"Task '{task_definition.task_name}' not registered")
            
            # Create task result
            task_result = TaskResult(
                task_id=task_definition.task_id,
                task_name=task_definition.task_name,
                status=TaskStatus.PENDING,
                metadata=task_definition.metadata
            )
            
            self.active_tasks[task_definition.task_id] = task_result
            
            # Submit to backend
            if self.config.backend == QueueBackend.CELERY:
                await self._submit_celery_task(task_definition)
            elif self.config.backend == QueueBackend.RQ:
                await self._submit_rq_task(task_definition)
            elif self.config.backend == QueueBackend.DRAMATIQ:
                await self._submit_dramatiq_task(task_definition)
            elif self.config.backend == QueueBackend.ARQ:
                await self._submit_arq_task(task_definition)
            else:
                await self._submit_memory_task(task_definition)
            
            self.logger.info("Task submitted",
                           task_id=task_definition.task_id,
                           task_name=task_definition.task_name,
                           priority=task_definition.priority.value)
            
            return task_definition.task_id
            
        except Exception as e:
            self.logger.error("Failed to submit task",
                            task_id=task_definition.task_id,
                            error=str(e))
            raise Exception(f"Task submission failed: {str(e)}")

    async def _submit_celery_task(self, task_def: TaskDefinition):
        """Submit task to Celery."""
        try:
            task_function = self.task_registry[task_def.task_name]
            
            # Submit task
            celery_result = task_function.apply_async(
                args=task_def.args,
                kwargs=task_def.kwargs,
                task_id=task_def.task_id,
                eta=task_def.eta,
                expires=task_def.expires,
                retry=False,  # We handle retries manually
                queue=task_def.queue_name
            )
            
            # Update task result
            if task_def.task_id in self.active_tasks:
                self.active_tasks[task_def.task_id].status = TaskStatus.PENDING
            
        except Exception as e:
            self.logger.error("Failed to submit Celery task",
                            task_id=task_def.task_id,
                            error=str(e))
            raise

    async def _submit_rq_task(self, task_def: TaskDefinition):
        """Submit task to RQ."""
        try:
            task_function = self.task_registry[task_def.task_name]
            
            job = self.queue_client.enqueue_at(
                task_def.eta or datetime.utcnow(),
                task_function,
                *task_def.args,
                **task_def.kwargs,
                job_id=task_def.task_id,
                job_timeout=task_def.timeout
            )
            
        except Exception as e:
            self.logger.error("Failed to submit RQ task",
                            task_id=task_def.task_id,
                            error=str(e))
            raise

    async def _submit_dramatiq_task(self, task_def: TaskDefinition):
        """Submit task to Dramatiq."""
        try:
            task_function = self.task_registry[task_def.task_name]
            
            # Send task
            task_function.send(*task_def.args, **task_def.kwargs)
            
        except Exception as e:
            self.logger.error("Failed to submit Dramatiq task",
                            task_id=task_def.task_id,
                            error=str(e))
            raise

    async def _submit_arq_task(self, task_def: TaskDefinition):
        """Submit task to ARQ."""
        try:
            # ARQ task submission would be implemented here
            pass
            
        except Exception as e:
            self.logger.error("Failed to submit ARQ task",
                            task_id=task_def.task_id,
                            error=str(e))
            raise

    async def _submit_memory_task(self, task_def: TaskDefinition):
        """Submit task to memory queue."""
        try:
            await self.queue_client['pending_tasks'].put(task_def)
            
            # Start worker if not running
            if not self.queue_client['workers']:
                worker_task = asyncio.create_task(self._memory_worker())
                self.queue_client['workers'].append(worker_task)
            
        except Exception as e:
            self.logger.error("Failed to submit memory task",
                            task_id=task_def.task_id,
                            error=str(e))
            raise

    async def _memory_worker(self):
        """Memory queue worker."""
        try:
            while self.queue_client['active']:
                try:
                    # Get task with timeout
                    task_def = await asyncio.wait_for(
                        self.queue_client['pending_tasks'].get(),
                        timeout=1.0
                    )
                    
                    # Execute task
                    await self._execute_memory_task(task_def)
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    self.logger.error("Memory worker error", error=str(e))
                    await asyncio.sleep(1)
                    
        except Exception as e:
            self.logger.error("Memory worker failed", error=str(e))

    async def _execute_memory_task(self, task_def: TaskDefinition):
        """Execute task in memory worker."""
        try:
            # Update task status
            if task_def.task_id in self.active_tasks:
                task_result = self.active_tasks[task_def.task_id]
                task_result.status = TaskStatus.RUNNING
                task_result.started_at = datetime.utcnow()
                task_result.worker_id = f"memory_worker_{asyncio.current_task().get_name()}"
            
            # Get task function
            task_function = self.task_registry[task_def.task_name]
            
            # Execute task
            if asyncio.iscoroutinefunction(task_function):
                result = await task_function(*task_def.args, **task_def.kwargs)
            else:
                result = task_function(*task_def.args, **task_def.kwargs)
            
            # Update task result
            if task_def.task_id in self.active_tasks:
                task_result = self.active_tasks[task_def.task_id]
                task_result.status = TaskStatus.COMPLETED
                task_result.result = result
                task_result.completed_at = datetime.utcnow()
                
                if task_result.started_at:
                    task_result.execution_time = (task_result.completed_at - task_result.started_at).total_seconds()
                
                # Move to completed tasks
                self.completed_tasks[task_def.task_id] = task_result
                del self.active_tasks[task_def.task_id]
            
            self.logger.info("Memory task completed",
                           task_id=task_def.task_id,
                           execution_time=task_result.execution_time)
            
        except Exception as e:
            # Update task result with error
            if task_def.task_id in self.active_tasks:
                task_result = self.active_tasks[task_def.task_id]
                task_result.status = TaskStatus.FAILED
                task_result.error = str(e)
                task_result.completed_at = datetime.utcnow()
                
                if task_result.started_at:
                    task_result.execution_time = (task_result.completed_at - task_result.started_at).total_seconds()
                
                # Move to failed tasks
                self.failed_tasks[task_def.task_id] = task_result
                del self.active_tasks[task_def.task_id]
            
            self.logger.error("Memory task failed",
                            task_id=task_def.task_id,
                            error=str(e))

    async def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """Get task status and result."""
        try:
            # Check active tasks
            if task_id in self.active_tasks:
                return self.active_tasks[task_id]
            
            # Check completed tasks
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id]
            
            # Check failed tasks
            if task_id in self.failed_tasks:
                return self.failed_tasks[task_id]
            
            # Query backend if available
            if self.config.backend == QueueBackend.CELERY:
                return await self._get_celery_task_status(task_id)
            elif self.config.backend == QueueBackend.RQ:
                return await self._get_rq_task_status(task_id)
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to get task status",
                            task_id=task_id,
                            error=str(e))
            return None

    async def _get_celery_task_status(self, task_id: str) -> Optional[TaskResult]:
        """Get task status from Celery."""
        try:
            from celery.result import AsyncResult
            
            result = AsyncResult(task_id, app=self.queue_client)
            
            # Convert Celery state to our status
            status_mapping = {
                'PENDING': TaskStatus.PENDING,
                'STARTED': TaskStatus.RUNNING,
                'SUCCESS': TaskStatus.COMPLETED,
                'FAILURE': TaskStatus.FAILED,
                'REVOKED': TaskStatus.CANCELLED,
                'RETRY': TaskStatus.RETRYING
            }
            
            task_result = TaskResult(
                task_id=task_id,
                task_name="unknown",
                status=status_mapping.get(result.state, TaskStatus.PENDING),
                result=result.result if result.successful() else None,
                error=str(result.info) if result.failed() else None
            )
            
            return task_result
            
        except Exception as e:
            self.logger.error("Failed to get Celery task status",
                            task_id=task_id,
                            error=str(e))
            return None

    async def _get_rq_task_status(self, task_id: str) -> Optional[TaskResult]:
        """Get task status from RQ."""
        try:
            from rq import get_current_job
            import redis
            
            redis_conn = redis.from_url(self.config.broker_url)
            
            # This would be implemented with proper RQ job status checking
            return None
            
        except Exception as e:
            self.logger.error("Failed to get RQ task status",
                            task_id=task_id,
                            error=str(e))
            return None

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        try:
            # Cancel in backend
            if self.config.backend == QueueBackend.CELERY:
                self.queue_client.control.revoke(task_id, terminate=True)
            elif self.config.backend == QueueBackend.RQ:
                # RQ cancellation would be implemented here
                pass
            
            # Update local status
            if task_id in self.active_tasks:
                task_result = self.active_tasks[task_id]
                task_result.status = TaskStatus.CANCELLED
                task_result.completed_at = datetime.utcnow()
                
                self.completed_tasks[task_id] = task_result
                del self.active_tasks[task_id]
            
            self.logger.info("Task cancelled", task_id=task_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to cancel task",
                            task_id=task_id,
                            error=str(e))
            return False

    async def retry_task(self, task_id: str) -> bool:
        """Retry a failed task."""
        try:
            # Find task in failed tasks
            if task_id not in self.failed_tasks:
                self.logger.warning("Task not found in failed tasks", task_id=task_id)
                return False
            
            failed_task = self.failed_tasks[task_id]
            
            # Create new task definition for retry
            new_task_id = f"{task_id}_retry_{failed_task.retry_count + 1}"
            
            retry_task_def = TaskDefinition(
                task_id=new_task_id,
                task_name=failed_task.task_name,
                task_function=failed_task.task_name,
                metadata={
                    **failed_task.metadata,
                    "original_task_id": task_id,
                    "retry_count": failed_task.retry_count + 1
                }
            )
            
            # Submit retry
            await self.submit_task(retry_task_def)
            
            self.logger.info("Task retry submitted",
                           original_task_id=task_id,
                           retry_task_id=new_task_id,
                           retry_count=failed_task.retry_count + 1)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to retry task",
                            task_id=task_id,
                            error=str(e))
            return False

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        try:
            stats = {
                "backend": self.config.backend.value,
                "active_tasks": len(self.active_tasks),
                "completed_tasks": len(self.completed_tasks),
                "failed_tasks": len(self.failed_tasks),
                "registered_tasks": len(self.task_registry),
                "worker_concurrency": self.config.worker_concurrency,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Add backend-specific stats
            if self.config.backend == QueueBackend.CELERY:
                stats.update(await self._get_celery_stats())
            elif self.config.backend == QueueBackend.MEMORY:
                stats.update(await self._get_memory_stats())
            
            # Task breakdown by status
            task_breakdown = {
                "pending": len([t for t in self.active_tasks.values() if t.status == TaskStatus.PENDING]),
                "running": len([t for t in self.active_tasks.values() if t.status == TaskStatus.RUNNING]),
                "completed": len(self.completed_tasks),
                "failed": len(self.failed_tasks)
            }
            
            stats["task_breakdown"] = task_breakdown
            
            # Performance metrics
            if self.completed_tasks:
                execution_times = [
                    t.execution_time for t in self.completed_tasks.values() 
                    if t.execution_time is not None
                ]
                
                if execution_times:
                    stats["performance"] = {
                        "avg_execution_time": sum(execution_times) / len(execution_times),
                        "min_execution_time": min(execution_times),
                        "max_execution_time": max(execution_times),
                        "total_execution_time": sum(execution_times)
                    }
            
            return stats
            
        except Exception as e:
            self.logger.error("Failed to get queue stats", error=str(e))
            return {"error": str(e)}

    async def _get_celery_stats(self) -> Dict[str, Any]:
        """Get Celery-specific statistics."""
        try:
            inspect = self.queue_client.control.inspect()
            
            return {
                "celery_workers": len(inspect.active() or {}),
                "celery_queues": list(inspect.active_queues() or {}).keys() if inspect.active_queues() else [],
                "celery_scheduled": len(inspect.scheduled() or {})
            }
            
        except Exception as e:
            self.logger.warning("Failed to get Celery stats", error=str(e))
            return {}

    async def _get_memory_stats(self) -> Dict[str, Any]:
        """Get memory queue statistics."""
        try:
            return {
                "memory_pending": self.queue_client['pending_tasks'].qsize(),
                "memory_workers": len(self.queue_client['workers']),
                "memory_active": self.queue_client['active']
            }
            
        except Exception as e:
            self.logger.warning("Failed to get memory stats", error=str(e))
            return {}

    async def cleanup_old_tasks(self, days: int = 7) -> int:
        """Clean up old completed and failed tasks."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Clean completed tasks
            initial_completed = len(self.completed_tasks)
            self.completed_tasks = {
                task_id: task for task_id, task in self.completed_tasks.items()
                if task.completed_at and task.completed_at > cutoff_date
            }
            
            # Clean failed tasks
            initial_failed = len(self.failed_tasks)
            self.failed_tasks = {
                task_id: task for task_id, task in self.failed_tasks.items()
                if task.completed_at and task.completed_at > cutoff_date
            }
            
            cleaned_count = (initial_completed - len(self.completed_tasks)) + (initial_failed - len(self.failed_tasks))
            
            if cleaned_count > 0:
                self.logger.info("Cleaned up old tasks",
                               cleaned_count=cleaned_count,
                               cutoff_days=days)
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error("Failed to cleanup old tasks",
                            days=days,
                            error=str(e))
            return 0

    async def shutdown(self):
        """Shutdown the task queue service."""
        try:
            # Stop memory workers
            if self.config.backend == QueueBackend.MEMORY and self.queue_client:
                self.queue_client['active'] = False
                
                # Cancel worker tasks
                for worker_task in self.queue_client['workers']:
                    if not worker_task.done():
                        worker_task.cancel()
                        try:
                            await worker_task
                        except asyncio.CancelledError:
                            pass
            
            self.logger.info("Task queue service shutdown completed")
            
        except Exception as e:
            self.logger.error("Error during task queue shutdown", error=str(e))