from datetime import datetime
from typing import Any, Dict, List, Optional
import json

class RevitAutoPlanException(Exception):
    """Base exception for all RevitAutoPlan errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        correlation_id: str,
        context: Optional[Dict[str, Any]] = None,
        inner_exception: Optional[Exception] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.correlation_id = correlation_id
        self.context = context or {}
        self.inner_exception = inner_exception
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat() + "Z",
            "context": self.context,
            "inner_exception": str(self.inner_exception) if self.inner_exception else None
        }
    
    def __str__(self) -> str:
        parts = [
            f"Error Code: {self.error_code}",
            f"Correlation ID: {self.correlation_id}",
            f"Timestamp: {self.timestamp.isoformat()}Z",
            f"Message: {self.message}"
        ]
        
        if self.context:
            parts.append("Context:")
            for key, value in self.context.items():
                parts.append(f"  {key}: {value}")
        
        if self.inner_exception:
            parts.append(f"Inner Exception: {self.inner_exception}")
        
        return "\n".join(parts)


class AIServiceException(RevitAutoPlanException):
    """Exception for AI service related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        correlation_id: str,
        ai_model: str = "unknown",
        confidence_score: Optional[float] = None,
        inner_exception: Optional[Exception] = None
    ) -> None:
        context = {"ai_model": ai_model}
        if confidence_score is not None:
            context["confidence_score"] = confidence_score
            
        super().__init__(message, error_code, correlation_id, context, inner_exception)
        self.ai_model = ai_model
        self.confidence_score = confidence_score


class AIModelUnavailableException(AIServiceException):
    """Exception when AI model is unavailable."""
    
    def __init__(
        self,
        ai_model: str,
        correlation_id: str,
        inner_exception: Optional[Exception] = None
    ) -> None:
        super().__init__(
            f"AI model {ai_model} is currently unavailable",
            "AI_001",
            correlation_id,
            ai_model,
            inner_exception=inner_exception
        )


class AIValidationFailedException(AIServiceException):
    """Exception when AI output validation fails."""
    
    def __init__(
        self,
        validation_errors: List[Dict[str, Any]],
        correlation_id: str,
        confidence_score: Optional[float] = None
    ) -> None:
        message = f"AI output validation failed with {len(validation_errors)} errors"
        context = {
            "validation_error_count": len(validation_errors),
            "validation_errors": [error.get("message", str(error)) for error in validation_errors]
        }
        
        super().__init__(message, "AI_002", correlation_id, "unknown", confidence_score)
        self.context.update(context)
        self.validation_errors = validation_errors


class ValidationException(RevitAutoPlanException):
    """Exception for validation errors."""
    
    def __init__(
        self,
        message: str,
        validation_result: Dict[str, Any],
        correlation_id: str
    ) -> None:
        context = {
            "validation_status": validation_result.get("status"),
            "error_count": len(validation_result.get("errors", []))
        }
        
        super().__init__(message, "VAL_001", correlation_id, context)
        self.validation_result = validation_result


class NetworkException(RevitAutoPlanException):
    """Exception for network and communication errors."""
    
    def __init__(
        self,
        message: str,
        correlation_id: str,
        service_endpoint: Optional[str] = None,
        http_status_code: Optional[int] = None,
        inner_exception: Optional[Exception] = None
    ) -> None:
        context = {}
        if service_endpoint:
            context["service_endpoint"] = service_endpoint
        if http_status_code:
            context["http_status_code"] = http_status_code
            
        super().__init__(message, "NET_001", correlation_id, context, inner_exception)
        self.service_endpoint = service_endpoint
        self.http_status_code = http_status_code


class MCPException(RevitAutoPlanException):
    """Exception for MCP protocol errors."""
    
    def __init__(
        self,
        message: str,
        correlation_id: str,
        mcp_method: Optional[str] = None,
        mcp_error_code: Optional[str] = None,
        inner_exception: Optional[Exception] = None
    ) -> None:
        context = {}
        if mcp_method:
            context["mcp_method"] = mcp_method
        if mcp_error_code:
            context["mcp_error_code"] = mcp_error_code
            
        super().__init__(message, "MCP_001", correlation_id, context, inner_exception)
        self.mcp_method = mcp_method
        self.mcp_error_code = mcp_error_code

