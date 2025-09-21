#!/usr/bin/env python3
"""
ArchBuilder.AI Cloud Server
Main FastAPI application entry point
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

import structlog
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.ai import router as ai_router
from app.api.documents import router as documents_router
from app.api.projects import router as projects_router
from app.api.system import router as system_router
from app.api.regional import router as regional_router
from app.api.billing import router as billing_router
from app.api.notifications import router as notifications_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import configure_logging, set_correlation_id, get_correlation_id
from app.core.middleware import add_middleware
from app.core.exceptions import RevitAutoPlanException, ValidationException, AIModelUnavailableException, NetworkException

# Task queue imports
try:
    from app.api.tasks import router as tasks_router
    from app.services.tasks.task_queue_service import TaskQueueService, QueueConfig, QueueBackend
    from app.services.tasks.worker_management import WorkerManager
    from app.services.tasks.monitoring_dashboard import router as dashboard_router
    from app.services.tasks.ai_tasks import AI_TASK_REGISTRY
    TASK_QUEUE_AVAILABLE = True
except ImportError as e:
    structlog.get_logger(__name__).warning("Task queue modules not available", error=str(e))
    TASK_QUEUE_AVAILABLE = False

# Performance optimization imports
try:
    from app.core.middleware import add_performance_middleware, get_performance_stats
    from app.core.performance import performance_tracker, initialize_performance_tracker
    from app.core.cache import initialize_cache
    from app.core.database_optimized import initialize_database, DatabaseConfig
    PERFORMANCE_AVAILABLE = True
except ImportError as e:
    structlog.get_logger(__name__).warning("Performance modules not available", error=str(e))
    PERFORMANCE_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    settings = get_settings()
    configure_logging(log_level=settings.LOG_LEVEL, service_name=settings.APP_NAME, component_name="cloud-server")
    logger = structlog.get_logger(__name__)
    logger.info("Starting ArchBuilder.AI Cloud Server")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize task queue system
    if TASK_QUEUE_AVAILABLE:
        try:
            # Initialize task queue service
            queue_config = QueueConfig(
                backend=QueueBackend.MEMORY,  # Use memory for development
                worker_concurrency=4,
                enable_monitoring=True
            )
            
            task_queue = TaskQueueService(queue_config)
            
            # Register AI tasks
            for task_name, task_function in AI_TASK_REGISTRY.items():
                task_queue.register_task(task_name, task_function)
            
            logger.info("Task queue service initialized", 
                       registered_tasks=len(AI_TASK_REGISTRY))
            
            # Initialize worker manager
            worker_manager = WorkerManager(task_queue)
            await worker_manager.start()
            
            logger.info("Worker manager initialized")
            
            # Store instances in app state
            app.state.task_queue = task_queue
            app.state.worker_manager = worker_manager
            
        except Exception as e:
            logger.warning("Failed to initialize task queue system", error=str(e))
    
    # Initialize performance monitoring if available
    if PERFORMANCE_AVAILABLE:
        try:
            logger.info("Performance tracker initialized")
            
            # Initialize cache (Redis will be None if not configured)
            redis_client = None
            logger.info("Cache system initialized")
            
        except Exception as e:
            logger.warning("Failed to initialize performance monitoring", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down ArchBuilder.AI Cloud Server")
    
    # Cleanup task queue system
    if TASK_QUEUE_AVAILABLE and hasattr(app.state, 'worker_manager'):
        try:
            await app.state.worker_manager.stop(graceful=True, timeout=30)
            logger.info("Task queue system shutdown completed")
        except Exception as e:
            logger.warning("Error during task queue cleanup", error=str(e))
    
    # Cleanup performance monitoring
    if PERFORMANCE_AVAILABLE:
        try:
            logger.info("Performance monitoring shutdown completed")
        except Exception as e:
            logger.warning("Error during performance cleanup", error=str(e))


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()
    
    app = FastAPI(
        title="ArchBuilder.AI Cloud Server",
        description="AI-Powered Architectural Design Automation Platform",
        version="1.0.0",
        docs_url="/docs",  # Always enable for development
        redoc_url="/redoc",  # Always enable for development
        lifespan=lifespan,
    )
    
    # Custom middlewares
    add_middleware(app) # Tüm özel middleware'leri ekle

    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.BACKEND_CORS_ORIGINS if settings.ENVIRONMENT == "production" else ["*"] # Configure properly in production
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS if settings.ENVIRONMENT == "production" else ["*"], # Configure properly in production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )
    
    # Add performance monitoring middleware - moved to add_middleware function
    
    # Include routers
    app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])
    app.include_router(ai_router, prefix="/api/ai", tags=["ai-processing"])
    app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
    app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
    app.include_router(system_router, prefix="/api/system", tags=["system"])
    app.include_router(regional_router, prefix="/api", tags=["regional-localization"])
    app.include_router(billing_router, prefix="/api", tags=["billing-subscription"])
    app.include_router(notifications_router, prefix="/api", tags=["notifications-email"])
    
    # Include task queue routers if available
    if TASK_QUEUE_AVAILABLE:
        try:
            app.include_router(tasks_router, prefix="/api", tags=["task-queue"])
            app.include_router(dashboard_router, prefix="/api", tags=["monitoring"])
            logger = structlog.get_logger(__name__)
            logger.info("Task queue API endpoints enabled")
        except Exception as e:
            logger = structlog.get_logger(__name__)
            logger.warning("Failed to include task queue routers", error=str(e))
    
    # Add performance monitoring endpoints
    if PERFORMANCE_AVAILABLE:
        @app.get("/api/system/performance", tags=["system"])
        async def get_system_performance():
            """Get comprehensive performance statistics"""
            try:
                return await get_performance_stats()
            except Exception as e:
                logger = structlog.get_logger(__name__)
                logger.error("Failed to get performance stats", error=str(e))
                return {"error": "Failed to retrieve performance statistics"}
        
        @app.get("/api/system/performance/health", tags=["system"])
        async def get_performance_health():
            """Get system health status"""
            try:
                return await performance_tracker.get_system_health()
            except Exception as e:
                logger = structlog.get_logger(__name__)
                logger.error("Failed to get system health", error=str(e))
                return {"error": "Failed to retrieve system health"}
        
    @app.exception_handler(RevitAutoPlanException)
    async def revit_autoplan_exception_handler(request: Request, exc: RevitAutoPlanException) -> JSONResponse:
        logger = structlog.get_logger(__name__).bind(correlation_id=get_correlation_id())
        logger.error(
            "RevitAutoPlan exception occurred",
            error_code=exc.error_code,
            correlation_id=exc.correlation_id,
            message=exc.message,
            context=exc.context,
            exc_info=True
        )

        # Determine HTTP status code based on exception type
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR  # Default server error
        if isinstance(exc, ValidationException):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, AIModelUnavailableException):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif isinstance(exc, NetworkException):
            status_code = exc.http_status_code or status.HTTP_502_BAD_GATEWAY

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "correlation_id": exc.correlation_id,
                    "timestamp": exc.timestamp.isoformat() + "Z",
                    "context": exc.context
                }
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger = structlog.get_logger(__name__).bind(correlation_id=get_correlation_id())
        logger.error(
            "Unhandled exception",
            exc_info=exc,
            path=request.url.path,
            method=request.method
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "SYS_001",
                    "message": "An unexpected error occurred",
                    "correlation_id": get_correlation_id(),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            }
        )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "service": "archbuilder-cloud-server"}
    
    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # Default host
        port=8000,       # Default port
        reload=True,     # Enable reload for development
        log_config=None,  # Use our custom logging setup
    )