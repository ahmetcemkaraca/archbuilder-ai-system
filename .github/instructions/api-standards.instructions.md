---
applyTo: "src/revit-plugin/**/*.cs,src/cloud-server/**/*.py,src/desktop-app/**/*.cs,**/*.ts,**/*.tsx,**/*.js,**/*.jsx"
description: API Standards — ArchBuilder.AI consistent REST API implementations across all services with global localization support and multi-format CAD processing.
---
As API Standards Developer:
- Define consistent HTTP REST API patterns across all services with global localization
- Establish WebSocket communication standards for real-time features  
- Ensure proper error handling, authentication, and rate limiting
- Maintain API versioning and backward compatibility
- Support multi-regional endpoints and localized responses
- Handle international measurement systems and cultural preferences
- **NO CUSTOM MCP PROTOCOL**: Use standard HTTP REST APIs only

## REST API Standards

### Base URL Structure with Cloud SaaS Support
```
Production:  https://api.revit-autoplan.com/v1
Regional:    https://{region}.api.revit-autoplan.com/v1  # e.g., eu.api, asia.api
Development: https://dev-api.revit-autoplan.com/v1
Staging:     https://staging-api.revit-autoplan.com/v1

# Multi-tenant endpoints with user isolation
/v1/users/{user_id}/projects           # User-specific projects
/v1/users/{user_id}/ai/commands        # User AI command history
/v1/users/{user_id}/billing/usage      # Usage and billing info
/v1/admin/users                        # Admin user management
/v1/admin/analytics                    # System analytics

# Regional endpoints for localized services
/v1/regional/{region}/building-codes     # Regional building codes
/v1/regional/{region}/ai/prompts        # Localized AI prompts  
/v1/regional/{region}/compliance        # Regional compliance validation
/v1/localization/{locale}/translations  # UI translations

# Subscription and billing endpoints
/v1/auth/login                         # User authentication
/v1/auth/refresh                       # Token refresh
/v1/subscriptions                      # Subscription management
/v1/billing/usage                      # Usage tracking
/v1/billing/invoices                   # Invoice management
```

### Standard HTTP Endpoints with Authentication
```python
# FastAPI Route Patterns with OAuth2 + API Key Authentication
from fastapi import APIRouter, HTTPException, Depends, status, Header
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from typing import List, Optional
import httpx

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="X-API-Key")

router = APIRouter(prefix="/v1", tags=["ai-commands"])

# Authentication dependency
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    api_key: str = Depends(api_key_header)
) -> User:
    """Authenticate user with JWT token and API key"""
    user = await auth_service.authenticate_user(token, api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return user

# Usage tracking decorator
def track_usage(operation_type: str, cost_units: int = 1):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user')
            await billing_service.track_usage(user.id, operation_type, cost_units)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Resource-based URLs with authentication and billing
@router.post("/ai/commands", status_code=status.HTTP_201_CREATED)
@track_usage("ai_layout_generation", cost_units=10)
async def create_ai_command(
    request: AICommandRequest,
    current_user: User = Depends(get_current_user),
    correlation_id: str = Header(..., alias="X-Correlation-ID")
) -> AICommandResponse:
    """Process new AI command from user prompt with usage tracking"""
    
    # Check subscription limits
    if not await billing_service.check_usage_limit(current_user.id, "ai_layout_generation"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Usage limit exceeded. Please upgrade your subscription."
        )
    
    # Process AI command
    result = await ai_service.process_command(request, current_user.id, correlation_id)
    
    return AICommandResponse(
        correlation_id=correlation_id,
        result=result,
        usage_remaining=await billing_service.get_remaining_usage(current_user.id)
    )

@router.get("/ai/commands/{correlation_id}")
async def get_ai_command(
    correlation_id: str,
    current_user: User = Depends(get_current_user)
) -> AICommandResponse:
    """Get AI command result by correlation ID with user isolation"""
    
    # Ensure user can only access their own commands
    command = await ai_service.get_user_command(correlation_id, current_user.id)
    if not command:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found or access denied"
        )
    
    return command

@router.post("/auth/login")
async def login(credentials: LoginRequest) -> TokenResponse:
    """User authentication with subscription validation"""
    
    user = await auth_service.authenticate_credentials(
        credentials.username, 
        credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check subscription status
    subscription = await billing_service.get_active_subscription(user.id)
    if not subscription or subscription.status != "active":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required"
        )
    
    # Generate tokens
    access_token = auth_service.create_access_token(user.id)
    api_key = auth_service.create_api_key(user.id)
    
    return TokenResponse(
        access_token=access_token,
        api_key=api_key,
        token_type="bearer",
        subscription_tier=subscription.tier,
        usage_limits=subscription.limits
    )

@router.get("/subscriptions/current")
async def get_current_subscription(
    current_user: User = Depends(get_current_user)
) -> SubscriptionResponse:
    """Get current user subscription and usage info"""
    
    subscription = await billing_service.get_subscription_details(current_user.id)
    usage = await billing_service.get_current_usage(current_user.id)
    
    return SubscriptionResponse(
        subscription=subscription,
        usage=usage,
        limits=subscription.limits
    )

@router.post("/billing/upgrade")
async def upgrade_subscription(
    upgrade_request: SubscriptionUpgradeRequest,
    current_user: User = Depends(get_current_user)
) -> UpgradeResponse:
    """Upgrade user subscription with Stripe integration"""
    
    result = await billing_service.upgrade_subscription(
        current_user.id,
        upgrade_request.new_tier,
        upgrade_request.payment_method_id
    )
    
    return UpgradeResponse(
        success=result.success,
        new_tier=result.new_tier,
        next_billing_date=result.next_billing_date
    )

@router.get("/health")
async def health_check() -> HealthResponse:
    """Service health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow()
    )
```

### C# HTTP Client Patterns
```csharp
public class RevitAutoPlanApiClient
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<RevitAutoPlanApiClient> _logger;
    private readonly string _apiKey;
    
    public RevitAutoPlanApiClient(
        HttpClient httpClient, 
        IConfiguration config,
        ILogger<RevitAutoPlanApiClient> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
        _apiKey = config["RevitAutoPlan:ApiKey"];
        
        // Set default headers
        _httpClient.DefaultRequestHeaders.Add("X-API-Key", _apiKey);
        _httpClient.DefaultRequestHeaders.Add("User-Agent", "RevitAutoPlan-Plugin/1.0");
        _httpClient.Timeout = TimeSpan.FromSeconds(30);
    }
    
    public async Task<AICommandResponse> ProcessCommandAsync(
        AICommandRequest request, 
        string correlationId,
        CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogInformation("Sending AI command", correlationId);
            
            var json = JsonSerializer.Serialize(request, JsonOptions.Default);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            
            // Add correlation ID header
            content.Headers.Add("X-Correlation-ID", correlationId);
            
            var response = await _httpClient.PostAsync("/v1/ai/commands", content, cancellationToken);
            
            if (response.IsSuccessStatusCode)
            {
                var responseJson = await response.Content.ReadAsStringAsync(cancellationToken);
                var result = JsonSerializer.Deserialize<AICommandResponse>(responseJson, JsonOptions.Default);
                
                _logger.LogInformation("AI command completed successfully", correlationId);
                return result;
            }
            else
            {
                var errorContent = await response.Content.ReadAsStringAsync(cancellationToken);
                _logger.LogError("AI command failed: {StatusCode} - {Error}", 
                    response.StatusCode, errorContent, correlationId);
                    
                throw new ApiException(response.StatusCode, errorContent);
            }
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "Network error during AI command", correlationId);
            throw new NetworkException("Failed to communicate with AI service", ex);
        }
        catch (TaskCanceledException ex)
        {
            _logger.LogError(ex, "AI command timed out", correlationId);
            throw new TimeoutException("AI command timed out", ex);
        }
    }
}
```

### Standard HTTP Response Format
```json
{
  "success": true,
  "data": {
    "correlationId": "AI_20250910143022_a1b2c3d4e5f6",
    "result": { /* actual response data */ }
  },
  "meta": {
    "timestamp": "2025-09-10T14:30:22.123Z",
    "version": "v1",
    "requestId": "req_12345"
  },
  "errors": null
}
```

```json
{
  "success": false,
  "data": null,
  "meta": {
    "timestamp": "2025-09-10T14:30:22.123Z", 
    "version": "v1",
    "requestId": "req_12345"
  },
  "errors": [
    {
      "code": "AI_001",
      "message": "AI model is temporarily unavailable",
      "field": null,
      "details": "OpenAI API returned 503 status"
    }
  ]
}
```

## WebSocket Standards

### Connection Management
```typescript
class RevitAutoPlanWebSocket {
    private ws: WebSocket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000;
    
    constructor(
        private apiKey: string,
        private correlationId: string,
        private onMessage: (message: WebSocketMessage) => void,
        private onError: (error: Error) => void
    ) {}
    
    public connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            const wsUrl = `ws://localhost:8000/v1/ws?api_key=${this.apiKey}&correlation_id=${this.correlationId}`;
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected', this.correlationId);
                this.reconnectAttempts = 0;
                
                // Send connection confirmation
                this.send({
                    type: 'connection_confirmed',
                    correlationId: this.correlationId,
                    timestamp: new Date().toISOString(),
                    payload: { clientType: 'revit-plugin' }
                });
                
                resolve();
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const message: WebSocketMessage = JSON.parse(event.data);
                    this.onMessage(message);
                } catch (error) {
                    this.onError(new Error(`Invalid WebSocket message: ${event.data}`));
                }
            };
            
            this.ws.onclose = (event) => {
                console.log('WebSocket closed', event.code, event.reason);
                this.attemptReconnect();
            };
            
            this.ws.onerror = (event) => {
                console.error('WebSocket error', event);
                this.onError(new Error('WebSocket connection error'));
                reject(new Error('WebSocket connection failed'));
            };
        });
    }
    
    public send<T>(message: WebSocketMessage<T>): void {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            throw new Error('WebSocket is not connected');
        }
    }
    
    private attemptReconnect(): void {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            
            setTimeout(() => {
                console.log(`Reconnecting WebSocket (attempt ${this.reconnectAttempts})`);
                this.connect().catch(error => {
                    console.error('Reconnection failed', error);
                });
            }, delay);
        }
    }
}
```

### WebSocket Message Types
```python
# FastAPI WebSocket Handler
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import asyncio

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, correlation_id: str):
        await websocket.accept()
        self.active_connections[correlation_id] = websocket
        
        # Send welcome message
        await self.send_message(correlation_id, {
            "type": "connection_established",
            "correlationId": correlation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {"message": "Connected to RevitAutoPlan WebSocket"}
        })
    
    async def disconnect(self, correlation_id: str):
        if correlation_id in self.active_connections:
            del self.active_connections[correlation_id]
    
    async def send_message(self, correlation_id: str, message: dict):
        if correlation_id in self.active_connections:
            websocket = self.active_connections[correlation_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending WebSocket message: {e}")
                await self.disconnect(correlation_id)
    
    async def broadcast_progress(self, correlation_id: str, stage: str, progress: float):
        await self.send_message(correlation_id, {
            "type": "progress_update",
            "correlationId": correlation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "stage": stage,
                "progress": progress,
                "message": f"Processing: {stage}"
            }
        })

# WebSocket endpoint
@app.websocket("/v1/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    api_key: str = Query(...),
    correlation_id: str = Query(...)
):
    # Validate API key
    if not validate_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
    
    await websocket_manager.connect(websocket, correlation_id)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Route message based on type
            await handle_websocket_message(correlation_id, message)
            
    except WebSocketDisconnect:
        await websocket_manager.disconnect(correlation_id)
```

## MCP Protocol Implementation

### MCP Server Setup
```python
# MCP Server for AI Model Communication
from mcp import Server, RequestId
from typing import Any, Dict, List, Optional
import json

class RevitAutoPlanMCPServer:
    def __init__(self):
        self.server = Server("revit-autoplan")
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.server.tool("generate_layout")
        async def generate_layout(
            user_prompt: str,
            room_program: Optional[Dict[str, Any]] = None,
            style_preferences: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """Generate architectural layout from user prompt"""
            
            try:
                # Process the prompt through AI pipeline
                layout_result = await self.ai_service.generate_layout(
                    prompt=user_prompt,
                    room_program=room_program,
                    style_preferences=style_preferences
                )
                
                return {
                    "success": True,
                    "layout": layout_result,
                    "confidence": layout_result.confidence,
                    "requires_review": layout_result.requires_human_review
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "error_code": "LAYOUT_GENERATION_FAILED"
                }
        
        @self.server.tool("validate_geometry")
        async def validate_geometry(
            layout_data: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Validate geometric constraints of layout"""
            
            validation_result = await self.validation_service.validate_layout(layout_data)
            
            return {
                "is_valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "confidence": validation_result.confidence
            }
        
        @self.server.resource("templates://building_types")
        async def list_building_types() -> List[Dict[str, str]]:
            """List available building type templates"""
            return [
                {"id": "residential", "name": "Residential Building"},
                {"id": "office", "name": "Office Building"},
                {"id": "retail", "name": "Retail Space"},
                {"id": "industrial", "name": "Industrial Building"}
            ]
        
        @self.server.prompt("architectural_layout")
        async def architectural_layout_prompt(
            building_type: str,
            total_area: float,
            room_requirements: List[Dict[str, Any]]
        ) -> str:
            """Generate optimized prompt for architectural layout generation"""
            
            prompt_template = f"""
            You are an expert architect creating a {building_type} layout.
            
            REQUIREMENTS:
            - Total area: {total_area} m²
            - Room requirements: {json.dumps(room_requirements, indent=2)}
            
            TASK: Generate a JSON response with exact coordinates for:
            1. Wall lines (start/end points in millimeters)
            2. Door positions (wall location + offset)
            3. Window positions (wall location + offset)
            
            CONSTRAINTS:
            - All coordinates in millimeters
            - Minimum room size: 5m²
            - Standard door width: 800-1000mm
            - Standard window width: 1000-2000mm
            
            OUTPUT FORMAT: Return ONLY valid JSON matching the LayoutResult schema.
            """
            
            return prompt_template
```

### MCP Client Implementation
```csharp
public class MCPClient
{
    private readonly HttpClient _httpClient;
    private readonly string _mcpServerUrl;
    private readonly ILogger<MCPClient> _logger;
    
    public MCPClient(HttpClient httpClient, IConfiguration config, ILogger<MCPClient> logger)
    {
        _httpClient = httpClient;
        _mcpServerUrl = config["MCP:ServerUrl"];
        _logger = logger;
    }
    
    public async Task<T> CallToolAsync<T>(
        string toolName, 
        object parameters, 
        string correlationId,
        CancellationToken cancellationToken = default)
    {
        var request = new MCPRequest
        {
            JsonRpc = "2.0",
            Id = correlationId,
            Method = "tools/call",
            Params = new
            {
                name = toolName,
                arguments = parameters
            }
        };
        
        try
        {
            var json = JsonSerializer.Serialize(request);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            
            _logger.LogInformation("Calling MCP tool: {ToolName}", toolName, correlationId);
            
            var response = await _httpClient.PostAsync($"{_mcpServerUrl}/mcp", content, cancellationToken);
            response.EnsureSuccessStatusCode();
            
            var responseJson = await response.Content.ReadAsStringAsync(cancellationToken);
            var mcpResponse = JsonSerializer.Deserialize<MCPResponse>(responseJson);
            
            if (mcpResponse.Error != null)
            {
                throw new MCPException(mcpResponse.Error.Code, mcpResponse.Error.Message);
            }
            
            return JsonSerializer.Deserialize<T>(mcpResponse.Result.ToString());
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "MCP tool call failed: {ToolName}", toolName, correlationId);
            throw;
        }
    }
    
    public async Task<List<MCPResource>> ListResourcesAsync(string correlationId)
    {
        var request = new MCPRequest
        {
            JsonRpc = "2.0",
            Id = correlationId,
            Method = "resources/list"
        };
        
        return await CallAsync<List<MCPResource>>(request, correlationId);
    }
}
```

## Rate Limiting and Security
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply rate limits to endpoints
@app.post("/v1/ai/commands")
@limiter.limit("10/minute")  # 10 AI commands per minute per IP
async def create_ai_command(
    request: Request,
    command: AICommandRequest,
    api_key: str = Depends(validate_api_key)
):
    pass

@app.get("/v1/layouts/{correlation_id}")
@limiter.limit("60/minute")  # 60 layout requests per minute per IP  
async def get_layout(
    request: Request,
    correlation_id: str,
    api_key: str = Depends(validate_api_key)
):
    pass

# API Key validation
async def validate_api_key(api_key: str = Header(..., alias="X-API-Key")):
    if not api_key or not is_valid_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    return api_key

def is_valid_api_key(api_key: str) -> bool:
    # Implement API key validation logic
    # Check against database or configuration
    return api_key in valid_api_keys
```

## Error Handling Standards
```python
# Custom exception classes
class RevitAutoPlanException(Exception):
    def __init__(self, message: str, error_code: str, details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

class AIServiceException(RevitAutoPlanException):
    pass

class ValidationException(RevitAutoPlanException):
    pass

class MCPException(RevitAutoPlanException):
    pass

# Global exception handler
@app.exception_handler(RevitAutoPlanException)
async def revit_autoplan_exception_handler(request: Request, exc: RevitAutoPlanException):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "data": None,
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "version": "v1",
                "requestId": str(uuid.uuid4())
            },
            "errors": [{
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }]
        }
    )
```

Always include correlation IDs, implement proper rate limiting, validate all inputs, and provide consistent error responses across all APIs.
