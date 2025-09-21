---
applyTo: "src/revit-plugin/**/*.cs,src/mcp-server/**/*.py,src/ai-models/**/*.cs,**/*.ts,**/*.tsx,**/*.js,**/*.jsx"
description: Error Handling Standards — consistent exception handling, logging, and recovery patterns across all systems.
---
As Error Handling Developer:
- Implement consistent exception handling patterns across all technology stacks
- Create proper error hierarchies with specific exception types
- Establish retry logic and circuit breaker patterns for external services
- Design user-friendly error messages and recovery strategies
- Ensure all errors are properly logged with correlation IDs for debugging

## Exception Hierarchy Design

### C# Exception Classes
```csharp
// Base exception for all RevitAutoPlan errors
public abstract class RevitAutoPlanException : Exception
{
    public string CorrelationId { get; }
    public string ErrorCode { get; }
    public Dictionary<string, object> Context { get; }
    public DateTime Timestamp { get; }
    
    protected RevitAutoPlanException(
        string message,
        string errorCode,
        string correlationId,
        Exception innerException = null,
        Dictionary<string, object> context = null)
        : base(message, innerException)
    {
        ErrorCode = errorCode;
        CorrelationId = correlationId;
        Context = context ?? new Dictionary<string, object>();
        Timestamp = DateTime.UtcNow;
    }
    
    public override string ToString()
    {
        var sb = new StringBuilder();
        sb.AppendLine($"Error Code: {ErrorCode}");
        sb.AppendLine($"Correlation ID: {CorrelationId}");
        sb.AppendLine($"Timestamp: {Timestamp:yyyy-MM-dd HH:mm:ss} UTC");
        sb.AppendLine($"Message: {Message}");
        
        if (Context.Any())
        {
            sb.AppendLine("Context:");
            foreach (var kvp in Context)
            {
                sb.AppendLine($"  {kvp.Key}: {kvp.Value}");
            }
        }
        
        if (InnerException != null)
        {
            sb.AppendLine($"Inner Exception: {InnerException.Message}");
        }
        
        return sb.ToString();
    }
}

// AI Service related exceptions
public class AIServiceException : RevitAutoPlanException
{
    public AIModel Model { get; }
    public double? ConfidenceScore { get; }
    
    public AIServiceException(
        string message, 
        string errorCode,
        string correlationId,
        AIModel model = AIModel.Unknown,
        double? confidenceScore = null,
        Exception innerException = null)
        : base(message, errorCode, correlationId, innerException)
    {
        Model = model;
        ConfidenceScore = confidenceScore;
        Context["aiModel"] = model.ToString();
        if (confidenceScore.HasValue)
            Context["confidenceScore"] = confidenceScore.Value;
    }
}

public class AIModelUnavailableException : AIServiceException
{
    public AIModelUnavailableException(
        AIModel model,
        string correlationId,
        Exception innerException = null)
        : base(
            $"AI model {model} is currently unavailable",
            "AI_001",
            correlationId,
            model,
            null,
            innerException)
    {
    }
}

public class AIValidationFailedException : AIServiceException
{
    public List<ValidationError> ValidationErrors { get; }
    
    public AIValidationFailedException(
        List<ValidationError> validationErrors,
        string correlationId,
        double? confidenceScore = null)
        : base(
            $"AI output validation failed with {validationErrors.Count} errors",
            "AI_002",
            correlationId,
            AIModel.Unknown,
            confidenceScore)
    {
        ValidationErrors = validationErrors;
        Context["validationErrorCount"] = validationErrors.Count;
        Context["validationErrors"] = validationErrors.Select(e => e.Message).ToArray();
    }
}

// Revit API related exceptions
public class RevitAPIException : RevitAutoPlanException
{
    public string RevitVersion { get; }
    public string DocumentName { get; }
    
    public RevitAPIException(
        string message,
        string errorCode,
        string correlationId,
        string revitVersion = null,
        string documentName = null,
        Exception innerException = null)
        : base(message, errorCode, correlationId, innerException)
    {
        RevitVersion = revitVersion;
        DocumentName = documentName;
        if (!string.IsNullOrEmpty(revitVersion))
            Context["revitVersion"] = revitVersion;
        if (!string.IsNullOrEmpty(documentName))
            Context["documentName"] = documentName;
    }
}

public class RevitTransactionFailedException : RevitAPIException
{
    public string TransactionName { get; }
    
    public RevitTransactionFailedException(
        string transactionName,
        string correlationId,
        Exception innerException = null)
        : base(
            $"Revit transaction '{transactionName}' failed",
            "RVT_001",
            correlationId,
            null,
            null,
            innerException)
    {
        TransactionName = transactionName;
        Context["transactionName"] = transactionName;
    }
}

// Validation related exceptions
public class ValidationException : RevitAutoPlanException
{
    public ValidationResult ValidationResult { get; }
    
    public ValidationException(
        string message,
        ValidationResult validationResult,
        string correlationId)
        : base(message, "VAL_001", correlationId)
    {
        ValidationResult = validationResult;
        Context["validationStatus"] = validationResult.Status.ToString();
        Context["errorCount"] = validationResult.Errors.Count;
    }
}

// Network and communication exceptions
public class NetworkException : RevitAutoPlanException
{
    public string ServiceEndpoint { get; }
    public int? HttpStatusCode { get; }
    
    public NetworkException(
        string message,
        string correlationId,
        string serviceEndpoint = null,
        int? httpStatusCode = null,
        Exception innerException = null)
        : base(message, "NET_001", correlationId, innerException)
    {
        ServiceEndpoint = serviceEndpoint;
        HttpStatusCode = httpStatusCode;
        if (!string.IsNullOrEmpty(serviceEndpoint))
            Context["serviceEndpoint"] = serviceEndpoint;
        if (httpStatusCode.HasValue)
            Context["httpStatusCode"] = httpStatusCode.Value;
    }
}
```

### Python Exception Classes
```python
"""Exception hierarchy for RevitAutoPlan application."""

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
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "inner_exception": str(self.inner_exception) if self.inner_exception else None
        }
    
    def __str__(self) -> str:
        parts = [
            f"Error Code: {self.error_code}",
            f"Correlation ID: {self.correlation_id}",
            f"Timestamp: {self.timestamp.isoformat()}",
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
```

## Error Handling Patterns

### Try-Catch with Retry Logic (C#)
```csharp
public class ResilientAIService
{
    private readonly ILogger<ResilientAIService> _logger;
    private readonly HttpClient _httpClient;
    private readonly CircuitBreakerPolicy _circuitBreaker;
    
    public async Task<AIResponse> CallAIServiceAsync(
        string prompt,
        string correlationId,
        CancellationToken cancellationToken = default)
    {
        var retryPolicy = Policy
            .Handle<HttpRequestException>()
            .Or<TaskCanceledException>()
            .Or<AIModelUnavailableException>()
            .WaitAndRetryAsync(
                retryCount: 3,
                sleepDurationProvider: retryAttempt => TimeSpan.FromSeconds(Math.Pow(2, retryAttempt)),
                onRetry: (outcome, timespan, retryCount, context) =>
                {
                    _logger.LogWarning("AI service call failed, retrying {RetryCount}/3 in {Delay}ms",
                        retryCount, timespan.TotalMilliseconds, correlationId);
                });
        
        try
        {
            return await retryPolicy.ExecuteAsync(async () =>
            {
                using var scope = _logger.BeginScope("AIServiceCall {CorrelationId}", correlationId);
                
                try
                {
                    _logger.LogInformation("Calling AI service", correlationId);
                    
                    var response = await _circuitBreaker.ExecuteAsync(async () =>
                    {
                        var httpResponse = await _httpClient.PostAsync(
                            "/ai/generate",
                            new StringContent(prompt, Encoding.UTF8, "application/json"),
                            cancellationToken);
                        
                        if (httpResponse.StatusCode == HttpStatusCode.ServiceUnavailable)
                        {
                            throw new AIModelUnavailableException("gpt-4", correlationId);
                        }
                        
                        httpResponse.EnsureSuccessStatusCode();
                        
                        var content = await httpResponse.Content.ReadAsStringAsync(cancellationToken);
                        return JsonSerializer.Deserialize<AIResponse>(content);
                    });
                    
                    _logger.LogInformation("AI service call completed successfully", correlationId);
                    return response;
                }
                catch (HttpRequestException ex)
                {
                    _logger.LogError(ex, "HTTP error during AI service call", correlationId);
                    throw new NetworkException(
                        "Failed to communicate with AI service",
                        correlationId,
                        _httpClient.BaseAddress?.ToString(),
                        null,
                        ex);
                }
                catch (TaskCanceledException ex) when (ex.InnerException is TimeoutException)
                {
                    _logger.LogError(ex, "AI service call timed out", correlationId);
                    throw new NetworkException(
                        "AI service call timed out",
                        correlationId,
                        _httpClient.BaseAddress?.ToString(),
                        408,
                        ex);
                }
                catch (JsonException ex)
                {
                    _logger.LogError(ex, "Failed to parse AI service response", correlationId);
                    throw new AIServiceException(
                        "Invalid response format from AI service",
                        "AI_003",
                        correlationId,
                        AIModel.GPT4,
                        null,
                        ex);
                }
            });
        }
        catch (Exception ex) when (!(ex is RevitAutoPlanException))
        {
            _logger.LogError(ex, "Unexpected error during AI service call", correlationId);
            throw new AIServiceException(
                "Unexpected error occurred during AI processing",
                "AI_999",
                correlationId,
                AIModel.GPT4,
                null,
                ex);
        }
    }
}
```

### Async Error Handling (Python)
```python
import asyncio
import aiohttp
from typing import Optional
import structlog
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential,
    retry_if_exception_type
)

logger = structlog.get_logger(__name__)


class ResilientAIService:
    """AI service with resilient error handling and retry logic."""
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((
            aiohttp.ClientError,
            asyncio.TimeoutError,
            AIModelUnavailableException
        ))
    )
    async def call_ai_service(
        self,
        prompt: str,
        correlation_id: str,
        model: str = "gpt-4"
    ) -> Dict[str, Any]:
        """Call AI service with comprehensive error handling."""
        
        logger.info(
            "Calling AI service",
            correlation_id=correlation_id,
            model=model
        )
        
        try:
            async with self._session.post(
                f"{self.base_url}/ai/generate",
                json={
                    "prompt": prompt,
                    "model": model,
                    "correlation_id": correlation_id
                }
            ) as response:
                
                # Handle different HTTP status codes
                if response.status == 503:
                    raise AIModelUnavailableException(model, correlation_id)
                elif response.status == 429:
                    raise NetworkException(
                        "Rate limit exceeded",
                        correlation_id,
                        self.base_url,
                        response.status
                    )
                elif response.status >= 500:
                    raise NetworkException(
                        f"Server error: {response.status}",
                        correlation_id,
                        self.base_url,
                        response.status
                    )
                elif response.status >= 400:
                    error_text = await response.text()
                    raise AIServiceException(
                        f"Client error: {error_text}",
                        "AI_004",
                        correlation_id,
                        model
                    )
                
                response.raise_for_status()
                
                try:
                    result = await response.json()
                    
                    # Validate response structure
                    if not isinstance(result, dict) or "layout" not in result:
                        raise AIServiceException(
                            "Invalid response structure from AI service",
                            "AI_003",
                            correlation_id,
                            model
                        )
                    
                    logger.info(
                        "AI service call completed successfully",
                        correlation_id=correlation_id,
                        confidence=result.get("confidence", 0)
                    )
                    
                    return result
                    
                except aiohttp.ContentTypeError as e:
                    raise AIServiceException(
                        "Invalid JSON response from AI service",
                        "AI_003",
                        correlation_id,
                        model,
                        inner_exception=e
                    )
                
        except asyncio.TimeoutError as e:
            logger.error(
                "AI service call timed out",
                correlation_id=correlation_id,
                timeout=self.timeout.total
            )
            raise NetworkException(
                "AI service call timed out",
                correlation_id,
                self.base_url,
                408,
                inner_exception=e
            )
            
        except aiohttp.ClientError as e:
            logger.error(
                "Network error during AI service call",
                correlation_id=correlation_id,
                error=str(e)
            )
            raise NetworkException(
                "Failed to communicate with AI service",
                correlation_id,
                self.base_url,
                inner_exception=e
            )
            
        except Exception as e:
            if isinstance(e, RevitAutoPlanException):
                raise
            
            logger.error(
                "Unexpected error during AI service call",
                correlation_id=correlation_id,
                error=str(e),
                exc_info=True
            )
            raise AIServiceException(
                "Unexpected error occurred during AI processing",
                "AI_999",
                correlation_id,
                model,
                inner_exception=e
            )
```

### Global Error Handlers

#### FastAPI Error Handler
```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import structlog

app = FastAPI()
logger = structlog.get_logger(__name__)


@app.exception_handler(RevitAutoPlanException)
async def revit_autoplan_exception_handler(
    request: Request, 
    exc: RevitAutoPlanException
) -> JSONResponse:
    """Handle all RevitAutoPlan custom exceptions."""
    
    logger.error(
        "RevitAutoPlan exception occurred",
        error_code=exc.error_code,
        correlation_id=exc.correlation_id,
        message=exc.message,
        context=exc.context,
        exc_info=True
    )
    
    # Determine HTTP status code based on exception type
    status_code = 500  # Default server error
    if isinstance(exc, ValidationException):
        status_code = 400
    elif isinstance(exc, AIModelUnavailableException):
        status_code = 503
    elif isinstance(exc, NetworkException):
        status_code = exc.http_status_code or 502
    
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "correlation_id": exc.correlation_id,
                "timestamp": exc.timestamp.isoformat(),
                "context": exc.context
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other unhandled exceptions."""
    
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    logger.error(
        "Unhandled exception occurred",
        correlation_id=correlation_id,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "SYS_001",
                "message": "An unexpected error occurred",
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
```

#### C# Global Exception Handler
```csharp
public class GlobalExceptionMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<GlobalExceptionMiddleware> _logger;
    
    public GlobalExceptionMiddleware(RequestDelegate next, ILogger<GlobalExceptionMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }
    
    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (Exception ex)
        {
            await HandleExceptionAsync(context, ex);
        }
    }
    
    private async Task HandleExceptionAsync(HttpContext context, Exception exception)
    {
        var correlationId = context.TraceIdentifier;
        
        if (exception is RevitAutoPlanException customEx)
        {
            _logger.LogError(customEx, "RevitAutoPlan exception occurred {CorrelationId}", correlationId);
            
            var statusCode = customEx switch
            {
                ValidationException => 400,
                AIModelUnavailableException => 503,
                NetworkException netEx => netEx.HttpStatusCode ?? 502,
                _ => 500
            };
            
            var response = new
            {
                success = false,
                data = (object)null,
                error = new
                {
                    code = customEx.ErrorCode,
                    message = customEx.Message,
                    correlationId = customEx.CorrelationId,
                    timestamp = customEx.Timestamp,
                    context = customEx.Context
                }
            };
            
            context.Response.StatusCode = statusCode;
            context.Response.ContentType = "application/json";
            
            var json = JsonSerializer.Serialize(response, JsonOptions.Default);
            await context.Response.WriteAsync(json);
        }
        else
        {
            _logger.LogError(exception, "Unhandled exception occurred {CorrelationId}", correlationId);
            
            var response = new
            {
                success = false,
                data = (object)null,
                error = new
                {
                    code = "SYS_001",
                    message = "An unexpected error occurred",
                    correlationId,
                    timestamp = DateTime.UtcNow
                }
            };
            
            context.Response.StatusCode = 500;
            context.Response.ContentType = "application/json";
            
            var json = JsonSerializer.Serialize(response, JsonOptions.Default);
            await context.Response.WriteAsync(json);
        }
    }
}
```

## Circuit Breaker Pattern
```csharp
public class CircuitBreakerService
{
    private readonly IAsyncPolicy _circuitBreaker;
    private readonly ILogger<CircuitBreakerService> _logger;
    
    public CircuitBreakerService(ILogger<CircuitBreakerService> logger)
    {
        _logger = logger;
        
        _circuitBreaker = Policy
            .Handle<HttpRequestException>()
            .Or<TimeoutException>()
            .Or<AIModelUnavailableException>()
            .CircuitBreakerAsync(
                handledEventsAllowedBeforeBreaking: 3,
                durationOfBreak: TimeSpan.FromMinutes(1),
                onBreak: (exception, duration) =>
                {
                    _logger.LogWarning("Circuit breaker opened for {Duration}ms due to {Exception}",
                        duration.TotalMilliseconds, exception.GetType().Name);
                },
                onReset: () =>
                {
                    _logger.LogInformation("Circuit breaker reset - service is healthy again");
                },
                onHalfOpen: () =>
                {
                    _logger.LogInformation("Circuit breaker half-open - testing service health");
                });
    }
    
    public async Task<T> ExecuteAsync<T>(Func<Task<T>> operation)
    {
        return await _circuitBreaker.ExecuteAsync(operation);
    }
}
```

Always use specific exception types, include correlation IDs in all errors, implement retry with exponential backoff, and provide meaningful error messages to users.
