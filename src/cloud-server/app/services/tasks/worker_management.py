"""
ArchBuilder.AI Worker Management System

Comprehensive worker lifecycle management for background task processing
with health monitoring, auto-scaling, and performance optimization.
"""

import asyncio
import psutil
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import structlog
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from .task_queue_service import TaskQueueService, QueueConfig, TaskStatus, QueueBackend
from .ai_tasks import AI_TASK_REGISTRY

logger = structlog.get_logger(__name__)


class WorkerStatus(Enum):
    """Worker status enumeration."""
    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class WorkerType(Enum):
    """Worker type enumeration."""
    GENERAL = "general"
    AI_PROCESSING = "ai_processing"
    FILE_PROCESSING = "file_processing"
    NOTIFICATION = "notification"
    BATCH = "batch"


@dataclass
class WorkerMetrics:
    """Worker performance metrics."""
    worker_id: str
    tasks_processed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    uptime_seconds: int = 0
    last_task_completed: Optional[datetime] = None
    error_rate: float = 0.0
    throughput_per_hour: float = 0.0


@dataclass
class WorkerConfiguration:
    """Worker configuration settings."""
    worker_id: str
    worker_type: WorkerType
    max_concurrent_tasks: int = 1
    task_timeout: int = 3600
    heartbeat_interval: int = 30
    max_memory_mb: int = 1024
    max_cpu_percent: float = 80.0
    auto_restart: bool = True
    queue_names: List[str] = field(default_factory=lambda: ["default"])
    task_types: List[str] = field(default_factory=list)


class WorkerInstance:
    """Individual worker instance with lifecycle management."""
    
    def __init__(self, config: WorkerConfiguration, task_queue: TaskQueueService):
        self.config = config
        self.task_queue = task_queue
        self.worker_id = config.worker_id
        self.status = WorkerStatus.STOPPED
        self.metrics = WorkerMetrics(worker_id=config.worker_id)
        self.started_at = None
        self.current_tasks = {}
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent_tasks)
        self.shutdown_event = threading.Event()
        self.heartbeat_thread = None
        self.monitoring_thread = None
        self._running = False
    
    async def start(self):
        """Start the worker instance."""
        try:
            logger.info("Starting worker", worker_id=self.worker_id)
            self.status = WorkerStatus.STARTING
            self.started_at = datetime.utcnow()
            self._running = True
            
            # Start heartbeat monitoring
            self.heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop, daemon=True
            )
            self.heartbeat_thread.start()
            
            # Start performance monitoring
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop, daemon=True
            )
            self.monitoring_thread.start()
            
            self.status = WorkerStatus.RUNNING
            logger.info("Worker started successfully", worker_id=self.worker_id)
            
            # Start task processing loop
            await self._task_processing_loop()
            
        except Exception as e:
            self.status = WorkerStatus.ERROR
            logger.error("Failed to start worker", 
                        worker_id=self.worker_id, error=str(e))
            raise
    
    async def stop(self, graceful: bool = True, timeout: int = 30):
        """Stop the worker instance."""
        try:
            logger.info("Stopping worker", 
                       worker_id=self.worker_id, graceful=graceful)
            
            self.status = WorkerStatus.STOPPING
            self._running = False
            
            if graceful:
                # Wait for current tasks to complete
                end_time = datetime.utcnow() + timedelta(seconds=timeout)
                while self.current_tasks and datetime.utcnow() < end_time:
                    await asyncio.sleep(1)
                
                # Cancel remaining tasks if timeout exceeded
                if self.current_tasks:
                    logger.warning("Force cancelling remaining tasks",
                                 worker_id=self.worker_id,
                                 remaining_tasks=len(self.current_tasks))
                    for task_future in self.current_tasks.values():
                        task_future.cancel()
            
            # Shutdown thread pool
            self.executor.shutdown(wait=True, timeout=timeout)
            
            # Signal shutdown to monitoring threads
            self.shutdown_event.set()
            
            self.status = WorkerStatus.STOPPED
            logger.info("Worker stopped successfully", worker_id=self.worker_id)
            
        except Exception as e:
            self.status = WorkerStatus.ERROR
            logger.error("Failed to stop worker", 
                        worker_id=self.worker_id, error=str(e))
            raise
    
    async def _task_processing_loop(self):
        """Main task processing loop."""
        while self._running:
            try:
                # Check if worker can accept more tasks
                if len(self.current_tasks) >= self.config.max_concurrent_tasks:
                    await asyncio.sleep(1)
                    continue
                
                # Check resource constraints
                if not self._check_resource_constraints():
                    self.status = WorkerStatus.IDLE
                    await asyncio.sleep(5)
                    continue
                
                # Get next task from queue
                task_definition = await self.task_queue.get_next_task(
                    queue_names=self.config.queue_names,
                    task_types=self.config.task_types
                )
                
                if task_definition:
                    # Process task asynchronously
                    future = self.executor.submit(
                        self._process_task_sync, task_definition
                    )
                    self.current_tasks[task_definition.task_id] = future
                    self.status = WorkerStatus.BUSY
                    
                    # Clean up completed tasks
                    await self._cleanup_completed_tasks()
                else:
                    # No tasks available
                    self.status = WorkerStatus.IDLE
                    await asyncio.sleep(2)
                
            except Exception as e:
                logger.error("Error in task processing loop",
                           worker_id=self.worker_id, error=str(e))
                await asyncio.sleep(5)
    
    def _process_task_sync(self, task_definition):
        """Process a single task synchronously."""
        task_id = task_definition.task_id
        start_time = time.time()
        
        try:
            logger.info("Processing task",
                       worker_id=self.worker_id,
                       task_id=task_id,
                       task_name=task_definition.task_name)
            
            # Get task function
            task_function = AI_TASK_REGISTRY.get(task_definition.task_function)
            if not task_function:
                raise ValueError(f"Unknown task function: {task_definition.task_function}")
            
            # Execute task with timeout
            if asyncio.iscoroutinefunction(task_function):
                # Handle async task
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        asyncio.wait_for(
                            task_function(*task_definition.args, **task_definition.kwargs),
                            timeout=self.config.task_timeout
                        )
                    )
                finally:
                    loop.close()
            else:
                # Handle sync task
                result = task_function(*task_definition.args, **task_definition.kwargs)
            
            execution_time = time.time() - start_time
            
            # Update metrics
            self.metrics.tasks_processed += 1
            self.metrics.total_execution_time += execution_time
            self.metrics.average_execution_time = (
                self.metrics.total_execution_time / self.metrics.tasks_processed
            )
            self.metrics.last_task_completed = datetime.utcnow()
            
            # Report success
            await self.task_queue.mark_task_completed(task_id, result)
            
            logger.info("Task completed successfully",
                       worker_id=self.worker_id,
                       task_id=task_id,
                       execution_time=execution_time)
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            error_msg = f"Task timed out after {execution_time:.2f} seconds"
            
            self.metrics.tasks_failed += 1
            await self.task_queue.mark_task_failed(task_id, error_msg)
            
            logger.error("Task timed out",
                        worker_id=self.worker_id,
                        task_id=task_id,
                        execution_time=execution_time)
            raise
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            self.metrics.tasks_failed += 1
            await self.task_queue.mark_task_failed(task_id, error_msg)
            
            logger.error("Task failed",
                        worker_id=self.worker_id,
                        task_id=task_id,
                        error=error_msg,
                        execution_time=execution_time)
            raise
        
        finally:
            # Remove from current tasks
            self.current_tasks.pop(task_id, None)
    
    async def _cleanup_completed_tasks(self):
        """Clean up completed task futures."""
        completed_tasks = []
        for task_id, future in self.current_tasks.items():
            if future.done():
                completed_tasks.append(task_id)
        
        for task_id in completed_tasks:
            self.current_tasks.pop(task_id, None)
    
    def _check_resource_constraints(self) -> bool:
        """Check if worker is within resource constraints."""
        try:
            # Check memory usage
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.config.max_memory_mb:
                logger.warning("Memory limit exceeded",
                             worker_id=self.worker_id,
                             memory_mb=memory_mb,
                             limit_mb=self.config.max_memory_mb)
                return False
            
            # Check CPU usage
            cpu_percent = process.cpu_percent()
            if cpu_percent > self.config.max_cpu_percent:
                logger.warning("CPU limit exceeded",
                             worker_id=self.worker_id,
                             cpu_percent=cpu_percent,
                             limit_percent=self.config.max_cpu_percent)
                return False
            
            # Update metrics
            self.metrics.memory_usage_mb = memory_mb
            self.metrics.cpu_usage_percent = cpu_percent
            
            return True
            
        except Exception as e:
            logger.error("Failed to check resource constraints",
                        worker_id=self.worker_id, error=str(e))
            return True  # Allow processing on error
    
    def _heartbeat_loop(self):
        """Worker heartbeat monitoring loop."""
        while self._running and not self.shutdown_event.is_set():
            try:
                # Calculate uptime
                if self.started_at:
                    uptime = datetime.utcnow() - self.started_at
                    self.metrics.uptime_seconds = int(uptime.total_seconds())
                
                # Calculate error rate
                total_tasks = self.metrics.tasks_processed + self.metrics.tasks_failed
                if total_tasks > 0:
                    self.metrics.error_rate = self.metrics.tasks_failed / total_tasks
                
                # Calculate throughput
                if self.metrics.uptime_seconds > 0:
                    self.metrics.throughput_per_hour = (
                        self.metrics.tasks_processed * 3600 / self.metrics.uptime_seconds
                    )
                
                logger.debug("Worker heartbeat",
                           worker_id=self.worker_id,
                           status=self.status.value,
                           active_tasks=len(self.current_tasks),
                           metrics=self.metrics)
                
                time.sleep(self.config.heartbeat_interval)
                
            except Exception as e:
                logger.error("Error in heartbeat loop",
                           worker_id=self.worker_id, error=str(e))
                time.sleep(self.config.heartbeat_interval)
    
    def _monitoring_loop(self):
        """Worker performance monitoring loop."""
        while self._running and not self.shutdown_event.is_set():
            try:
                # Monitor resource usage
                self._check_resource_constraints()
                
                # Check for worker health issues
                if self.metrics.error_rate > 0.5:  # 50% error rate
                    logger.warning("High error rate detected",
                                 worker_id=self.worker_id,
                                 error_rate=self.metrics.error_rate)
                
                if self.metrics.memory_usage_mb > self.config.max_memory_mb * 0.8:
                    logger.warning("High memory usage",
                                 worker_id=self.worker_id,
                                 memory_mb=self.metrics.memory_usage_mb)
                
                time.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error("Error in monitoring loop",
                           worker_id=self.worker_id, error=str(e))
                time.sleep(60)


class WorkerManager:
    """Manages multiple worker instances with auto-scaling and health monitoring."""
    
    def __init__(self, task_queue: TaskQueueService):
        self.task_queue = task_queue
        self.workers: Dict[str, WorkerInstance] = {}
        self.worker_configs: Dict[str, WorkerConfiguration] = {}
        self.auto_scaling_enabled = True
        self.max_workers = 10
        self.min_workers = 1
        self.scaling_thread = None
        self.shutdown_event = threading.Event()
        self._running = False
    
    async def start(self):
        """Start the worker manager."""
        logger.info("Starting worker manager")
        self._running = True
        
        # Start auto-scaling thread
        if self.auto_scaling_enabled:
            self.scaling_thread = threading.Thread(
                target=self._auto_scaling_loop, daemon=True
            )
            self.scaling_thread.start()
        
        # Start minimum number of workers
        await self._ensure_minimum_workers()
        
        logger.info("Worker manager started", 
                   active_workers=len(self.workers))
    
    async def stop(self, graceful: bool = True, timeout: int = 60):
        """Stop the worker manager and all workers."""
        logger.info("Stopping worker manager", graceful=graceful)
        
        self._running = False
        self.shutdown_event.set()
        
        # Stop all workers
        stop_tasks = []
        for worker in self.workers.values():
            stop_tasks.append(worker.stop(graceful=graceful, timeout=timeout))
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        self.workers.clear()
        logger.info("Worker manager stopped")
    
    async def add_worker(self, config: WorkerConfiguration) -> str:
        """Add a new worker with the given configuration."""
        worker_id = config.worker_id or str(uuid.uuid4())
        config.worker_id = worker_id
        
        if worker_id in self.workers:
            raise ValueError(f"Worker {worker_id} already exists")
        
        worker = WorkerInstance(config, self.task_queue)
        self.workers[worker_id] = worker
        self.worker_configs[worker_id] = config
        
        # Start the worker
        await worker.start()
        
        logger.info("Worker added", worker_id=worker_id)
        return worker_id
    
    async def remove_worker(self, worker_id: str, graceful: bool = True) -> bool:
        """Remove a worker."""
        if worker_id not in self.workers:
            return False
        
        worker = self.workers[worker_id]
        await worker.stop(graceful=graceful)
        
        del self.workers[worker_id]
        del self.worker_configs[worker_id]
        
        logger.info("Worker removed", worker_id=worker_id)
        return True
    
    async def scale_workers(self, target_count: int):
        """Scale workers to target count."""
        current_count = len(self.workers)
        
        if target_count > current_count:
            # Scale up
            for i in range(target_count - current_count):
                config = WorkerConfiguration(
                    worker_id=f"auto-worker-{uuid.uuid4().hex[:8]}",
                    worker_type=WorkerType.GENERAL,
                    max_concurrent_tasks=2,
                    queue_names=["default", "ai_processing"]
                )
                await self.add_worker(config)
        
        elif target_count < current_count:
            # Scale down
            workers_to_remove = list(self.workers.keys())[target_count:]
            for worker_id in workers_to_remove:
                await self.remove_worker(worker_id, graceful=True)
        
        logger.info("Workers scaled", 
                   from_count=current_count, 
                   to_count=target_count)
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get status of all workers."""
        status = {
            "total_workers": len(self.workers),
            "worker_breakdown": {},
            "aggregate_metrics": {
                "total_tasks_processed": 0,
                "total_tasks_failed": 0,
                "average_error_rate": 0.0,
                "total_uptime_hours": 0.0,
                "average_throughput": 0.0
            },
            "workers": []
        }
        
        total_error_rate = 0.0
        total_throughput = 0.0
        
        for worker in self.workers.values():
            worker_info = {
                "worker_id": worker.worker_id,
                "status": worker.status.value,
                "worker_type": worker.config.worker_type.value,
                "current_tasks": len(worker.current_tasks),
                "max_concurrent": worker.config.max_concurrent_tasks,
                "metrics": {
                    "tasks_processed": worker.metrics.tasks_processed,
                    "tasks_failed": worker.metrics.tasks_failed,
                    "error_rate": worker.metrics.error_rate,
                    "uptime_hours": worker.metrics.uptime_seconds / 3600,
                    "throughput": worker.metrics.throughput_per_hour,
                    "memory_mb": worker.metrics.memory_usage_mb,
                    "cpu_percent": worker.metrics.cpu_usage_percent
                }
            }
            
            status["workers"].append(worker_info)
            
            # Aggregate metrics
            status["aggregate_metrics"]["total_tasks_processed"] += worker.metrics.tasks_processed
            status["aggregate_metrics"]["total_tasks_failed"] += worker.metrics.tasks_failed
            status["aggregate_metrics"]["total_uptime_hours"] += worker.metrics.uptime_seconds / 3600
            
            total_error_rate += worker.metrics.error_rate
            total_throughput += worker.metrics.throughput_per_hour
            
            # Worker breakdown by status
            status_key = worker.status.value
            status["worker_breakdown"][status_key] = status["worker_breakdown"].get(status_key, 0) + 1
        
        # Calculate averages
        worker_count = len(self.workers)
        if worker_count > 0:
            status["aggregate_metrics"]["average_error_rate"] = total_error_rate / worker_count
            status["aggregate_metrics"]["average_throughput"] = total_throughput / worker_count
        
        return status
    
    async def _ensure_minimum_workers(self):
        """Ensure minimum number of workers are running."""
        current_count = len(self.workers)
        
        if current_count < self.min_workers:
            for i in range(self.min_workers - current_count):
                config = WorkerConfiguration(
                    worker_id=f"min-worker-{i}",
                    worker_type=WorkerType.GENERAL,
                    max_concurrent_tasks=2,
                    queue_names=["default", "ai_processing", "notification"]
                )
                await self.add_worker(config)
    
    def _auto_scaling_loop(self):
        """Auto-scaling monitoring loop."""
        while self._running and not self.shutdown_event.is_set():
            try:
                # Get queue statistics
                queue_stats = asyncio.run(self.task_queue.get_queue_stats())
                
                active_tasks = queue_stats.get("active_tasks", 0)
                pending_tasks = queue_stats.get("pending_tasks", 0)
                
                current_workers = len(self.workers)
                busy_workers = sum(1 for w in self.workers.values() 
                                 if w.status == WorkerStatus.BUSY)
                
                # Scale up if queue is growing
                if pending_tasks > current_workers * 2 and current_workers < self.max_workers:
                    target_workers = min(
                        self.max_workers,
                        current_workers + max(1, pending_tasks // 5)
                    )
                    logger.info("Auto-scaling up",
                               current=current_workers,
                               target=target_workers,
                               pending_tasks=pending_tasks)
                    
                    asyncio.run(self.scale_workers(target_workers))
                
                # Scale down if workers are idle
                elif (busy_workers < current_workers * 0.3 and 
                      current_workers > self.min_workers and 
                      pending_tasks == 0):
                    
                    target_workers = max(
                        self.min_workers,
                        current_workers - 1
                    )
                    logger.info("Auto-scaling down",
                               current=current_workers,
                               target=target_workers,
                               busy_workers=busy_workers)
                    
                    asyncio.run(self.scale_workers(target_workers))
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error("Error in auto-scaling loop", error=str(e))
                time.sleep(30)