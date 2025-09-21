"""
Structured logging configuration for ArchBuilder.AI
Implements correlation tracking and audit trails
"""

import logging
import logging.config
import sys
from typing import Optional, Dict, Any
from datetime import datetime
import json

from .config import get_settings

settings = get_settings()


class CorrelationFilter(logging.Filter):
    """Filter to add correlation ID to log records"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__()
        self.correlation_id = correlation_id
    
    def filter(self, record):
        record.correlation_id = getattr(record, 'correlation_id', self.correlation_id or 'N/A')
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', 'N/A'),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info', 'correlation_id']:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class ArchBuilderLogger:
    """Custom logger with correlation tracking"""
    
    def __init__(self, name: str, correlation_id: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.correlation_id = correlation_id
        
        # Add correlation filter
        if correlation_id:
            correlation_filter = CorrelationFilter(correlation_id)
            self.logger.addFilter(correlation_filter)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with extra fields"""
        extra = {'correlation_id': self.correlation_id}
        extra.update(kwargs)
        self.logger.log(level, message, extra=extra)


def setup_logging():
    """Configure application logging"""
    
    log_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': settings.LOG_FORMAT
            },
            'json': {
                '()': JSONFormatter
            }
        },
        'filters': {
            'correlation': {
                '()': CorrelationFilter
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'stream': sys.stdout,
                'formatter': 'json' if settings.ENVIRONMENT == 'production' else 'standard',
                'filters': ['correlation']
            }
        },
        'root': {
            'level': settings.LOG_LEVEL,
            'handlers': ['console']
        },
        'loggers': {
            'archbuilder': {
                'level': settings.LOG_LEVEL,
                'handlers': ['console'],
                'propagate': False
            },
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            },
            'fastapi': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            }
        }
    }
    
    logging.config.dictConfig(log_config)


def get_logger(name: str, correlation_id: Optional[str] = None) -> ArchBuilderLogger:
    """Get logger instance with optional correlation ID"""
    return ArchBuilderLogger(name, correlation_id)


def add_correlation_id(correlation_id: str):
    """Add correlation ID to all subsequent log entries in current context"""
    # This would be implemented with contextvars in a real application
    pass


class AuditLogger:
    """Specialized logger for audit trails"""
    
    def __init__(self):
        self.logger = logging.getLogger('archbuilder.audit')
    
    def log_user_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log user action for audit trail"""
        
        audit_entry = {
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'timestamp': datetime.utcnow().isoformat(),
            'correlation_id': correlation_id or 'N/A',
            'metadata': metadata or {}
        }
        
        self.logger.info('User action', extra=audit_entry)
    
    def log_system_event(
        self,
        event_type: str,
        description: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log system event for audit trail"""
        
        system_entry = {
            'event_type': event_type,
            'description': description,
            'timestamp': datetime.utcnow().isoformat(),
            'correlation_id': correlation_id or 'N/A',
            'metadata': metadata or {}
        }
        
        self.logger.info('System event', extra=system_entry)
    
    def log_api_call(
        self,
        method: str,
        endpoint: str,
        user_id: Optional[str],
        status_code: int,
        response_time_ms: float,
        correlation_id: Optional[str] = None
    ):
        """Log API call for performance and usage tracking"""
        
        api_entry = {
            'method': method,
            'endpoint': endpoint,
            'user_id': user_id,
            'status_code': status_code,
            'response_time_ms': response_time_ms,
            'timestamp': datetime.utcnow().isoformat(),
            'correlation_id': correlation_id or 'N/A'
        }
        
        self.logger.info('API call', extra=api_entry)


# Global audit logger instance
audit_logger = AuditLogger()


def log_file_operation(
    operation: str,
    file_path: str,
    file_type: Optional[str] = None,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Log file operations for audit and debugging"""
    
    file_entry = {
        'operation': operation,
        'file_path': file_path,
        'file_type': file_type,
        'timestamp': datetime.utcnow().isoformat(),
        'correlation_id': correlation_id or 'N/A',
        'metadata': metadata or {}
    }
    
    logger = logging.getLogger('archbuilder.files')
    logger.info('File operation', extra=file_entry)


def log_validation_result(
    validation_type: str,
    passed: bool,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
):
    """Log validation results for monitoring and debugging"""
    
    validation_entry = {
        'validation_type': validation_type,
        'passed': passed,
        'details': details or {},
        'timestamp': datetime.utcnow().isoformat(),
        'correlation_id': correlation_id or 'N/A'
    }
    
    logger = logging.getLogger('archbuilder.validation')
    logger.info('Validation result', extra=validation_entry)


def log_ai_operation(
    operation: str,
    model_used: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    confidence: Optional[float] = None,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Log AI model operations for monitoring and cost tracking"""
    
    ai_entry = {
        'operation': operation,
        'model_used': model_used,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'confidence': confidence,
        'timestamp': datetime.utcnow().isoformat(),
        'correlation_id': correlation_id or 'N/A',
        'metadata': metadata or {}
    }
    
    logger = logging.getLogger('archbuilder.ai')
    logger.info('AI operation', extra=ai_entry)


def log_security_event(
    event_type: str,
    severity: str,
    description: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    correlation_id: Optional[str] = None
):
    """Log security events for monitoring and alerting"""
    
    security_entry = {
        'event_type': event_type,
        'severity': severity,
        'description': description,
        'user_id': user_id,
        'ip_address': ip_address,
        'timestamp': datetime.utcnow().isoformat(),
        'correlation_id': correlation_id or 'N/A'
    }
    
    logger = logging.getLogger('archbuilder.security')
    logger.warning('Security event', extra=security_entry)


# Initialize logging on module import
setup_logging()