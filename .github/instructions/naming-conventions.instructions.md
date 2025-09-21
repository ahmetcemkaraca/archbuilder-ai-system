---
applyTo: "src/revit-plugin/**/*.cs,src/cloud-server/**/*.py,src/desktop-app/**/*.cs,src/shared/**/*.cs,**/*.ts,**/*.tsx,**/*.js,**/*.jsx,**/*.json,configs/**/*.json"
description: Naming Conventions — ArchBuilder.AI consistent variable, function, class naming across all technologies.
---
As Naming Standards Developer:
- Apply consistent naming conventions across C#, Python, TypeScript, and JSON
- Use technology-specific casing but maintain semantic consistency
- Establish clear patterns for ArchBuilder.AI domain objects
- Ensure AI-generated code follows established naming patterns

## Technology-Specific Conventions

### C# (.NET/Revit Plugin)
```csharp
// Classes: PascalCase
public class LayoutGenerationService
public class AICommandProcessor
public class RevitElementCreator

// Interfaces: IPascalCase
public interface IAILayoutService
public interface IRevitAPIWrapper
public interface IValidationService

// Methods: PascalCase
public async Task<LayoutResult> GenerateLayoutAsync(RoomProgram program)
public void CreateWallsFromAIOutput(List<WallDefinition> walls)
public ValidationResult ValidateGeometry(GeometryData geometry)

// Properties: PascalCase
public string CorrelationId { get; set; }
public DateTime CreatedAt { get; set; }
public AIConfidenceLevel Confidence { get; set; }

// Fields: camelCase with underscore prefix for private
private readonly ILogger _logger;
private readonly string _apiKey;
private static readonly string _defaultWallType;

// Parameters/Variables: camelCase
string userCommand = request.Command;
var aiResponse = await aiService.ProcessAsync(userCommand);
List<WallDefinition> wallDefinitions = aiResponse.Walls;

// Constants: SCREAMING_SNAKE_CASE
public const string DEFAULT_WALL_TYPE_NAME = "Generic - 200mm";
public const int MAX_RETRY_ATTEMPTS = 3;
public const double MIN_ROOM_AREA_M2 = 5.0;

// Enums: PascalCase
public enum AIProcessingStatus
{
    Pending,
    Processing,
    Completed,
    Failed,
    RequiresHumanReview
}
```

### Python (MCP Server/Backend)
```python
# Classes: PascalCase
class AILayoutService:
class RevitCommandGenerator:
class ValidationPipeline:

# Functions/Methods: snake_case
async def generate_layout_from_prompt(user_prompt: str) -> LayoutResult:
def validate_ai_output(ai_response: dict) -> ValidationResult:
def create_revit_commands(layout_data: dict) -> List[RevitCommand]:

# Variables: snake_case
user_command = request.command
ai_response = await ai_service.process_prompt(user_command)
wall_definitions = ai_response.walls
correlation_id = str(uuid.uuid4())

# Constants: SCREAMING_SNAKE_CASE
DEFAULT_WALL_TYPE = "Generic - 200mm"
MAX_RETRY_ATTEMPTS = 3
MIN_ROOM_AREA_M2 = 5.0
API_TIMEOUT_SECONDS = 30

# Private methods: _snake_case
def _validate_schema(self, data: dict) -> bool:
async def _call_openai_api(self, prompt: str) -> dict:
def _log_ai_interaction(self, correlation_id: str, prompt: str) -> None:

# Type hints: PascalCase for custom types
from typing import Dict, List, Optional, Union
RoomProgram = Dict[str, Any]
AIResponse = Dict[str, Any]
ValidationErrors = List[str]
```

### TypeScript/JavaScript (Frontend/Utilities)
```typescript
// Interfaces: IPascalCase
interface IAICommand {
    correlationId: string;
    userPrompt: string;
    aiResponse?: AIResponse;
}

interface ILayoutData {
    walls: WallDefinition[];
    doors: DoorDefinition[];
    rooms: RoomDefinition[];
}

// Classes: PascalCase
class AICommandProcessor {
    private readonly apiClient: HttpClient;
    
    public async processCommand(command: string): Promise<AIResponse> {
        // implementation
    }
}

// Functions: camelCase
async function generateLayoutFromPrompt(userPrompt: string): Promise<LayoutResult> {
    // implementation
}

function validateAIOutput(aiResponse: AIResponse): ValidationResult {
    // implementation
}

// Variables: camelCase
const userCommand = request.command;
const aiResponse = await aiService.processPrompt(userCommand);
const wallDefinitions = aiResponse.walls;
const correlationId = generateUniqueId();

// Constants: SCREAMING_SNAKE_CASE
const DEFAULT_WALL_TYPE = "Generic - 200mm";
const MAX_RETRY_ATTEMPTS = 3;
const MIN_ROOM_AREA_M2 = 5.0;
```

## Domain-Specific Naming Standards

### AI/ML Related Objects
```csharp
// C# Examples
public class AIPromptRequest
public class AIModelResponse  
public class AIConfidenceMetrics
public class AIValidationResult
public class AIFallbackService

// Python Examples
class ai_prompt_engine:
class ai_model_client:
class ai_confidence_calculator:
class ai_validation_pipeline:
class ai_fallback_handler:
```

### Revit Domain Objects
```csharp
// Geometry and Elements
public class WallDefinition
public class DoorDefinition  
public class WindowDefinition
public class RoomDefinition
public class FloorDefinition
public class RoofDefinition

// Layout and Planning
public class RoomProgram
public class LayoutResult
public class GeometryValidation
public class SpatialConstraints
public class BuildingCodeConstraints

// Commands and Operations
public class RevitCommand
public class LayoutCommand
public class ElementCreationCommand
public class ValidationCommand
public class DocumentationCommand
```

### MCP Protocol Objects
```python
# MCP Standard Naming
class mcp_request:
class mcp_response:
class mcp_notification:
class mcp_error:

# Custom MCP Extensions
class revit_mcp_command:
class ai_mcp_request:
class layout_mcp_response:
class validation_mcp_result:
```

### WebSocket Message Types
```typescript
// Message Types: PascalCase with suffix
interface AICommandMessage {
    type: 'ai_command';
    correlationId: string;
    payload: AICommandPayload;
}

interface LayoutGeneratedMessage {
    type: 'layout_generated';
    correlationId: string;
    payload: LayoutResult;
}

interface ValidationRequiredMessage {
    type: 'validation_required';
    correlationId: string;
    payload: ValidationRequest;
}

interface HumanReviewMessage {
    type: 'human_review';
    correlationId: string;
    payload: HumanReviewRequest;
}
```

## JSON Schema Naming
```json
{
  "aiCommand": {
    "correlationId": "string",
    "userPrompt": "string", 
    "aiModel": "string",
    "confidenceThreshold": "number"
  },
  "layoutResult": {
    "walls": ["WallDefinition"],
    "doors": ["DoorDefinition"],
    "rooms": ["RoomDefinition"],
    "aiConfidence": "number",
    "validationStatus": "string",
    "requiresHumanReview": "boolean"
  },
  "revitCommand": {
    "commandType": "string",
    "elementType": "string", 
    "parameters": "object",
    "correlationId": "string"
  }
}
```

## Database Table/Column Naming
```sql
-- Tables: snake_case
ai_commands
layout_results
validation_results
human_reviews
audit_logs

-- Columns: snake_case
correlation_id
user_prompt
ai_response
created_at
updated_at
confidence_score
requires_human_review
validation_status
```

## File and Directory Naming
```
src/
  revit-plugin/
    Commands/
    Services/
    Models/
    Validators/
  mcp-server/
    ai_services/
    validation/
    mcp_handlers/
    models/
  shared/
    data-contracts/
    enums/
    constants/
```

## Error Code Naming
```csharp
// Error Codes: SCREAMING_SNAKE_CASE with prefix
public const string AI_MODEL_UNAVAILABLE = "AI_001";
public const string AI_VALIDATION_FAILED = "AI_002"; 
public const string AI_CONFIDENCE_TOO_LOW = "AI_003";
public const string REVIT_API_ERROR = "RVT_001";
public const string REVIT_TRANSACTION_FAILED = "RVT_002";
public const string MCP_CONNECTION_ERROR = "MCP_001";
public const string MCP_PROTOCOL_ERROR = "MCP_002";
```

## Correlation ID Pattern
```csharp
// Always use consistent correlation ID format
// Pattern: {PREFIX}_{TIMESTAMP}_{RANDOM}
string correlationId = $"AI_{DateTime.UtcNow:yyyyMMddHHmmss}_{Guid.NewGuid():N}";

// Examples:
// AI_20250910143022_a1b2c3d4e5f6
// VAL_20250910143022_a1b2c3d4e5f6  
// RVT_20250910143022_a1b2c3d4e5f6
```

Always maintain consistency across all technology layers while respecting each platform's conventions.
