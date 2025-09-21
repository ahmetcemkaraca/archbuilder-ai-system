import structlog
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
import uuid

# Context variable for correlation ID
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

def configure_logging(log_level: str = "INFO", service_name: str = "archbuilder-ai", component_name: str = "cloud-server"):
    """Configure structured logging with Structlog."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Configure Structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            add_correlation_id,
            add_timestamp,
            add_service_info(service_name=service_name, component_name=component_name),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to all log entries."""
    correlation_id = correlation_id_context.get()
    if correlation_id:
        event_dict['correlation_id'] = correlation_id
    return event_dict

def add_timestamp(logger, method_name, event_dict):
    """Add ISO timestamp to all log entries."""
    event_dict['timestamp'] = datetime.utcnow().isoformat() + "Z"
    return event_dict

def add_service_info(service_name: str, component_name: str):
    def _add_service_info(logger, method_name, event_dict):
        """Add service information to all log entries."""
        event_dict['service'] = service_name
        event_dict['component'] = component_name
        return event_dict
    return _add_service_info

def set_correlation_id(correlation_id: str):
    """Set correlation ID in context."""
    correlation_id_context.set(correlation_id)

def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id_context.get()

def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4()).replace("-", "")[:8]
    return f"PY_{timestamp}_{unique_id}"

