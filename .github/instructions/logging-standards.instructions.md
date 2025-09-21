---
applyTo: "src/revit-plugin/**/*.cs,src/mcp-server/**/*.py,src/ai-models/**/*.cs,**/*.ts,**/*.tsx,**/*.js,**/*.jsx"
description: Logging Standards — structured logging patterns, correlation tracking, and audit trails across all systems.
---
As Logging Standards Developer:
- Implement structured logging with consistent fields across all technologies
- Establish correlation ID tracking throughout the entire system
- Create comprehensive audit trails for AI decisions and user actions
- Design log aggregation and monitoring strategies
- Ensure sensitive data is never logged while maintaining debugging capability

## Structured Logging Patterns

### C# Logging with Serilog
```csharp
// Startup.cs - Serilog Configuration
public void ConfigureServices(IServiceCollection services)
{
    // Configure Serilog
    Log.Logger = new LoggerConfiguration()
        .MinimumLevel.Information()
        .MinimumLevel.Override("Microsoft", LogEventLevel.Warning)
        .MinimumLevel.Override("System", LogEventLevel.Warning)
        .Enrich.FromLogContext()
        .Enrich.WithMachineName()
        .Enrich.WithThreadId()
        .Enrich.WithProperty("Application", "RevitAutoPlan")
        .WriteTo.Console(outputTemplate: 
            "[{Timestamp:HH:mm:ss} {Level:u3}] {CorrelationId} {SourceContext} {Message:lj}{NewLine}{Exception}")
        .WriteTo.File(
            path: "logs/revit-autoplan-.txt",
            rollingInterval: RollingInterval.Day,
            retainedFileCountLimit: 30,
            fileSizeLimitBytes: 100_000_000,
            outputTemplate: 
                "{Timestamp:yyyy-MM-dd HH:mm:ss.fff zzz} [{Level:u3}] {CorrelationId} {SourceContext} {Message:lj} {Properties:j}{NewLine}{Exception}")
        .WriteTo.Seq("http://localhost:5341") // For centralized logging
        .CreateLogger();
    
    services.AddLogging(builder => builder.AddSerilog());
    
    // Add correlation ID middleware
    services.AddScoped<CorrelationIdMiddleware>();
}

// CorrelationIdMiddleware.cs
public class CorrelationIdMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<CorrelationIdMiddleware> _logger;
    
    public CorrelationIdMiddleware(RequestDelegate next, ILogger<CorrelationIdMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }
    
    public async Task InvokeAsync(HttpContext context)
    {
        var correlationId = GetOrCreateCorrelationId(context);
        
        // Add to HTTP response headers
        context.Response.Headers.Add("X-Correlation-ID", correlationId);
        
        // Add to Serilog context
        using (LogContext.PushProperty("CorrelationId", correlationId))
        {
            await _next(context);
        }
    }
    
    private string GetOrCreateCorrelationId(HttpContext context)
    {
        const string correlationIdHeader = "X-Correlation-ID";
        
        if (context.Request.Headers.TryGetValue(correlationIdHeader, out var correlationId))
        {
            return correlationId;
        }
        
        return $"HTTP_{DateTime.UtcNow:yyyyMMddHHmmss}_{Guid.NewGuid():N}";
    }
}
```

### Service-Level Logging Patterns
```csharp
public class AILayoutService : IAILayoutService
{
    private readonly ILogger<AILayoutService> _logger;
    private readonly IAIModelClient _aiModelClient;
    
    public AILayoutService(ILogger<AILayoutService> logger, IAIModelClient aiModelClient)
    {
        _logger = logger;
        _aiModelClient = aiModelClient;
    }
    
    public async Task<LayoutResult> GenerateLayoutAsync(
        LayoutGenerationRequest request,
        string correlationId,
        CancellationToken cancellationToken = default)
    {
        // Create scoped logger with correlation ID and operation context
        using var scope = _logger.BeginScope(new Dictionary<string, object>
        {
            ["CorrelationId"] = correlationId,
            ["Operation"] = "GenerateLayout",
            ["UserPromptLength"] = request.UserPrompt?.Length ?? 0,
            ["BuildingType"] = request.BuildingType,
            ["TotalAreaM2"] = request.TotalAreaM2
        });
        
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        
        try
        {
            _logger.LogInformation("Starting AI layout generation", correlationId);
            
            // Log sanitized user input (never log sensitive data)
            _logger.LogInformation("Layout generation request received",
                building_type: request.BuildingType,
                total_area_m2: request.TotalAreaM2,
                room_count: request.RoomRequirements?.Count ?? 0,
                has_style_preferences: request.StylePreferences != null,
                correlation_id: correlationId);
            
            // Validate input
            var validationResult = await ValidateInputAsync(request, correlationId);
            if (!validationResult.IsValid)
            {
                _logger.LogWarning("Input validation failed",
                    validation_error_count: validationResult.Errors.Count,
                    validation_errors: validationResult.Errors.Select(e => e.Code).ToArray(),
                    correlation_id: correlationId);
                
                throw new ValidationException("Invalid input", validationResult, correlationId);
            }
            
            _logger.LogDebug("Input validation passed", correlationId);
            
            // Call AI service
            _logger.LogInformation("Calling AI model for layout generation",
                ai_model: "gpt-4",
                correlation_id: correlationId);
            
            var aiResponse = await _aiModelClient.GenerateLayoutAsync(request, correlationId, cancellationToken);
            
            _logger.LogInformation("AI model response received",
                confidence_score: aiResponse.Confidence,
                wall_count: aiResponse.Walls?.Count ?? 0,
                door_count: aiResponse.Doors?.Count ?? 0,
                window_count: aiResponse.Windows?.Count ?? 0,
                room_count: aiResponse.Rooms?.Count ?? 0,
                requires_human_review: aiResponse.RequiresHumanReview,
                correlation_id: correlationId);
            
            // Validate AI output
            var outputValidation = await ValidateAIOutputAsync(aiResponse, correlationId);
            
            _logger.LogInformation("AI output validation completed",
                validation_status: outputValidation.Status,
                validation_confidence: outputValidation.ConfidenceScore,
                error_count: outputValidation.Errors.Count,
                warning_count: outputValidation.Warnings.Count,
                correlation_id: correlationId);
            
            var result = new LayoutResult
            {
                CorrelationId = correlationId,
                Layout = aiResponse,
                Validation = outputValidation,
                CreatedAt = DateTime.UtcNow,
                RequiresHumanReview = aiResponse.RequiresHumanReview || outputValidation.RequiresHumanReview
            };
            
            stopwatch.Stop();
            
            _logger.LogInformation("AI layout generation completed successfully",
                elapsed_ms: stopwatch.ElapsedMilliseconds,
                final_confidence: aiResponse.Confidence,
                requires_human_review: result.RequiresHumanReview,
                correlation_id: correlationId);
            
            // Audit log for AI decision
            await LogAIDecisionAsync(request, result, correlationId);
            
            return result;
        }
        catch (ValidationException ex)
        {
            stopwatch.Stop();
            _logger.LogWarning(ex, "AI layout generation failed due to validation error",
                elapsed_ms: stopwatch.ElapsedMilliseconds,
                error_code: ex.ErrorCode,
                correlation_id: correlationId);
            throw;
        }
        catch (AIServiceException ex)
        {
            stopwatch.Stop();
            _logger.LogError(ex, "AI layout generation failed due to AI service error",
                elapsed_ms: stopwatch.ElapsedMilliseconds,
                ai_model: ex.Model,
                confidence_score: ex.ConfidenceScore,
                error_code: ex.ErrorCode,
                correlation_id: correlationId);
            throw;
        }
        catch (Exception ex)
        {
            stopwatch.Stop();
            _logger.LogError(ex, "AI layout generation failed due to unexpected error",
                elapsed_ms: stopwatch.ElapsedMilliseconds,
                correlation_id: correlationId);
            throw;
        }
    }
    
    private async Task LogAIDecisionAsync(
        LayoutGenerationRequest request,
        LayoutResult result,
        string correlationId)
    {
        // Audit log for AI decisions (separate from application logs)
        _logger.LogInformation("AI_DECISION_AUDIT",
            correlation_id: correlationId,
            decision_type: "layout_generation",
            input_hash: ComputeHash(request.UserPrompt), // Hash for privacy
            ai_model: "gpt-4",
            confidence_score: result.Layout.Confidence,
            validation_status: result.Validation.Status,
            requires_human_review: result.RequiresHumanReview,
            element_counts: new
            {
                walls = result.Layout.Walls?.Count ?? 0,
                doors = result.Layout.Doors?.Count ?? 0,
                windows = result.Layout.Windows?.Count ?? 0,
                rooms = result.Layout.Rooms?.Count ?? 0
            },
            decision_timestamp: DateTime.UtcNow);
    }
}
```

### Python Logging with Structlog
```python
"""Structured logging configuration for RevitAutoPlan Python services."""

import structlog
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
import uuid

# Context variable for correlation ID
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

def configure_logging(log_level: str = "INFO", service_name: str = "revit-autoplan"):
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
            add_service_info,
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


def add_service_info(logger, method_name, event_dict):
    """Add service information to all log entries."""
    event_dict['service'] = 'revit-autoplan'
    event_dict['component'] = 'mcp-server'
    return event_dict


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


# Service-level logging example
class AILayoutService:
    """AI Layout Service with comprehensive logging."""
    
    def __init__(self, ai_model_client, validation_service):
        self.logger = structlog.get_logger(__name__)
        self.ai_model_client = ai_model_client
        self.validation_service = validation_service
    
    async def generate_layout(
        self,
        request: Dict[str, Any],
        correlation_id: str
    ) -> Dict[str, Any]:
        """Generate layout with comprehensive logging."""
        
        # Set correlation ID in context
        set_correlation_id(correlation_id)
        
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(
                "Starting AI layout generation",
                operation="generate_layout",
                building_type=request.get("building_type"),
                total_area_m2=request.get("total_area_m2"),
                room_count=len(request.get("room_requirements", [])),
                has_style_preferences=bool(request.get("style_preferences")),
                user_prompt_length=len(request.get("user_prompt", ""))
            )
            
            # Validate input
            validation_result = await self._validate_input(request)
            if not validation_result["is_valid"]:
                self.logger.warning(
                    "Input validation failed",
                    validation_error_count=len(validation_result["errors"]),
                    validation_errors=[error["code"] for error in validation_result["errors"]]
                )
                raise ValidationException(
                    "Invalid input parameters",
                    validation_result,
                    correlation_id
                )
            
            self.logger.debug("Input validation passed")
            
            # Call AI service
            self.logger.info(
                "Calling AI model for layout generation",
                ai_model="gpt-4"
            )
            
            ai_response = await self.ai_model_client.generate_layout(request)
            
            self.logger.info(
                "AI model response received",
                confidence_score=ai_response.get("confidence"),
                wall_count=len(ai_response.get("walls", [])),
                door_count=len(ai_response.get("doors", [])),
                window_count=len(ai_response.get("windows", [])),
                room_count=len(ai_response.get("rooms", [])),
                requires_human_review=ai_response.get("requires_human_review", False)
            )
            
            # Validate AI output
            output_validation = await self.validation_service.validate_layout(ai_response)
            
            self.logger.info(
                "AI output validation completed",
                validation_status=output_validation["status"],
                validation_confidence=output_validation.get("confidence_score"),
                error_count=len(output_validation.get("errors", [])),
                warning_count=len(output_validation.get("warnings", []))
            )
            
            result = {
                "correlation_id": correlation_id,
                "layout": ai_response,
                "validation": output_validation,
                "created_at": datetime.utcnow().isoformat(),
                "requires_human_review": (
                    ai_response.get("requires_human_review", False) or
                    output_validation.get("requires_human_review", False)
                )
            }
            
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            self.logger.info(
                "AI layout generation completed successfully",
                elapsed_ms=elapsed_ms,
                final_confidence=ai_response.get("confidence"),
                requires_human_review=result["requires_human_review"]
            )
            
            # Audit log for AI decision
            await self._log_ai_decision(request, result)
            
            return result
            
        except ValidationException as e:
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.logger.warning(
                "AI layout generation failed due to validation error",
                elapsed_ms=elapsed_ms,
                error_code=e.error_code,
                exc_info=True
            )
            raise
            
        except AIServiceException as e:
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.logger.error(
                "AI layout generation failed due to AI service error",
                elapsed_ms=elapsed_ms,
                ai_model=e.ai_model,
                confidence_score=e.confidence_score,
                error_code=e.error_code,
                exc_info=True
            )
            raise
            
        except Exception as e:
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.logger.error(
                "AI layout generation failed due to unexpected error",
                elapsed_ms=elapsed_ms,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _validate_input(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input with detailed logging."""
        errors = []
        
        if not request.get("user_prompt", "").strip():
            errors.append({
                "code": "INPUT_001",
                "message": "User prompt cannot be empty",
                "field": "user_prompt"
            })
        
        if not request.get("total_area_m2") or request["total_area_m2"] <= 0:
            errors.append({
                "code": "INPUT_002", 
                "message": "Total area must be greater than 0",
                "field": "total_area_m2"
            })
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _log_ai_decision(self, request: Dict[str, Any], result: Dict[str, Any]):
        """Create audit log for AI decision."""
        import hashlib
        
        # Hash user prompt for privacy
        prompt_hash = hashlib.sha256(
            request.get("user_prompt", "").encode()
        ).hexdigest()[:16]
        
        self.logger.info(
            "AI_DECISION_AUDIT",
            decision_type="layout_generation",
            input_hash=prompt_hash,
            ai_model="gpt-4",
            confidence_score=result["layout"].get("confidence"),
            validation_status=result["validation"]["status"],
            requires_human_review=result["requires_human_review"],
            element_counts={
                "walls": len(result["layout"].get("walls", [])),
                "doors": len(result["layout"].get("doors", [])),
                "windows": len(result["layout"].get("windows", [])),
                "rooms": len(result["layout"].get("rooms", []))
            },
            decision_timestamp=datetime.utcnow().isoformat()
        )
```

### FastAPI Middleware for Correlation ID
```python
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation IDs in FastAPI."""
    
    async def dispatch(self, request: Request, call_next):
        # Get or create correlation ID
        correlation_id = self._get_or_create_correlation_id(request)
        
        # Set in context
        set_correlation_id(correlation_id)
        
        # Add to request state
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
    
    def _get_or_create_correlation_id(self, request: Request) -> str:
        """Get correlation ID from headers or create new one."""
        correlation_id = request.headers.get("X-Correlation-ID")
        
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        return correlation_id


# Add middleware to FastAPI app
app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)
```

## Performance and Security Logging

### Performance Metrics Logging
```csharp
public class PerformanceLoggingService
{
    private readonly ILogger<PerformanceLoggingService> _logger;
    
    public async Task<T> LogExecutionTimeAsync<T>(
        string operationName,
        string correlationId,
        Func<Task<T>> operation,
        Dictionary<string, object> additionalContext = null)
    {
        var stopwatch = Stopwatch.StartNew();
        var context = additionalContext ?? new Dictionary<string, object>();
        
        try
        {
            _logger.LogDebug("Starting operation {OperationName}", operationName, correlationId);
            
            var result = await operation();
            
            stopwatch.Stop();
            
            _logger.LogInformation("Operation completed successfully",
                operation_name: operationName,
                elapsed_ms: stopwatch.ElapsedMilliseconds,
                correlation_id: correlationId,
                additional_context: context);
            
            return result;
        }
        catch (Exception ex)
        {
            stopwatch.Stop();
            
            _logger.LogError(ex, "Operation failed",
                operation_name: operationName,
                elapsed_ms: stopwatch.ElapsedMilliseconds,
                correlation_id: correlationId,
                additional_context: context);
            
            throw;
        }
    }
}
```

### Security Event Logging
```python
class SecurityEventLogger:
    """Logger for security-related events."""
    
    def __init__(self):
        self.security_logger = structlog.get_logger("security")
    
    def log_authentication_attempt(
        self,
        success: bool,
        api_key_hash: str,
        client_ip: str,
        user_agent: str,
        correlation_id: str
    ):
        """Log authentication attempts."""
        self.security_logger.info(
            "AUTHENTICATION_ATTEMPT",
            success=success,
            api_key_hash=api_key_hash,
            client_ip=client_ip,
            user_agent=user_agent,
            correlation_id=correlation_id,
            event_type="authentication"
        )
    
    def log_rate_limit_exceeded(
        self,
        client_ip: str,
        endpoint: str,
        limit: str,
        correlation_id: str
    ):
        """Log rate limit violations."""
        self.security_logger.warning(
            "RATE_LIMIT_EXCEEDED",
            client_ip=client_ip,
            endpoint=endpoint,
            rate_limit=limit,
            correlation_id=correlation_id,
            event_type="rate_limit_violation"
        )
    
    def log_suspicious_activity(
        self,
        activity_type: str,
        client_ip: str,
        details: Dict[str, Any],
        correlation_id: str
    ):
        """Log suspicious activities."""
        self.security_logger.warning(
            "SUSPICIOUS_ACTIVITY",
            activity_type=activity_type,
            client_ip=client_ip,
            details=details,
            correlation_id=correlation_id,
            event_type="suspicious_activity"
        )
```

## Data Privacy and Redaction
```csharp
public static class LogSanitizer
{
    private static readonly HashSet<string> SensitiveFields = new()
    {
        "password", "api_key", "token", "secret", "authorization",
        "credit_card", "ssn", "personal_id", "phone", "email"
    };
    
    public static object SanitizeLogData(object data)
    {
        if (data == null) return null;
        
        if (data is string str)
        {
            return SanitizeString(str);
        }
        
        if (data is IDictionary<string, object> dict)
        {
            var sanitized = new Dictionary<string, object>();
            foreach (var kvp in dict)
            {
                if (SensitiveFields.Any(field => 
                    kvp.Key.Contains(field, StringComparison.OrdinalIgnoreCase)))
                {
                    sanitized[kvp.Key] = "[REDACTED]";
                }
                else
                {
                    sanitized[kvp.Key] = SanitizeLogData(kvp.Value);
                }
            }
            return sanitized;
        }
        
        return data;
    }
    
    private static string SanitizeString(string input)
    {
        if (string.IsNullOrEmpty(input)) return input;
        
        // Redact potential API keys (32+ character alphanumeric strings)
        var apiKeyPattern = @"\b[A-Za-z0-9]{32,}\b";
        input = Regex.Replace(input, apiKeyPattern, "[API_KEY_REDACTED]");
        
        // Redact email addresses
        var emailPattern = @"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b";
        input = Regex.Replace(input, emailPattern, "[EMAIL_REDACTED]");
        
        return input;
    }
}
```

Always include correlation IDs, sanitize sensitive data, use structured logging, implement performance tracking, and maintain audit trails for all AI decisions.
