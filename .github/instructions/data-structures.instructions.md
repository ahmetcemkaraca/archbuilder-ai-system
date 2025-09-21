---
applyTo: "src/revit-plugin/**/*.cs,src/cloud-server/**/*.py,src/desktop-app/**/*.cs,src/shared/**/*.cs,**/*.ts,**/*.tsx,**/*.js,**/*.jsx,**/*.json,configs/**/*.json"
description: Data Structures — ArchBuilder.AI standardized data contracts, JSON schemas, and type definitions for multi-format CAD processing across all systems.
---
As Data Structure Developer:
- Define consistent data contracts between C# plugin, MCP server, and AI APIs
- Establish standard JSON schemas for all system communications
- Create type-safe data structures with validation
- Ensure backward compatibility and versioning support
- Support multi-regional data structures with localization
- Handle global building codes and cultural adaptations

## Global Multi-Regional Data Contracts

### Regional Building Information Schema
```typescript
// Multi-regional building information
interface GlobalBuildingInfo {
  id: string;
  region: "north_america" | "europe" | "asia_pacific" | "middle_east" | "africa" | "south_america";
  country: string;
  locale: string; // e.g., "en-US", "de-DE", "ja-JP", "ar-SA", "tr-TR"
  buildingType: BuildingType;
  measurementSystem: "metric" | "imperial" | "mixed";
  
  // Localized area measurements
  totalArea: {
    value: number;
    unit: "m2" | "sqft" | "sqm";
    convertedValue?: number;
  };
  
  // Regional compliance requirements
  applicableCodes: string[]; // e.g., ["IBC", "IRC"] or ["Eurocode", "DIN"] or ["İmar Yönetmeliği"]
  zoneName: string;
  occupancyClass: string;
  
  // Cultural and regional preferences
  culturalContext: {
    familyStructure: "nuclear" | "extended" | "multi_generational";
    privacyRequirements: "high" | "medium" | "low";
    entertainmentStyle: "formal" | "casual" | "mixed";
    outdoorConnection: "high" | "medium" | "low";
    religiousConsiderations?: string[];
  };
  
  // Climate and environmental factors
  climateZone: "tropical" | "arid" | "temperate" | "continental" | "polar";
  environmentalFactors: {
    seismicZone?: number;
    floodZone?: boolean;
    windLoadRequirements?: boolean;
    energyEfficiencyStandard: string;
  };
}

// Regional compliance validation structure
interface RegionalComplianceCheck {
  region: string;
  country: string;
  applicableCodes: string[];
  
  validationResults: {
    codeCompliance: {
      [codeType: string]: {
        compliant: boolean;
        violations: string[];
        warnings: string[];
      };
    };
    
    accessibilityCompliance: {
      standard: string; // "ADA", "European Accessibility Act", etc.
      compliant: boolean;
      issues: string[];
    };
    
    energyEfficiency: {
      standard: string;
      rating: string;
      meetsRequirements: boolean;
    };
    
    culturalAppropriateness: {
      privacyCompliant: boolean;
      culturalAdaptations: string[];
      recommendations: string[];
    };
  };
  
  confidence: number;
  reviewRequired: boolean;
  regionalExpertContact?: string;
}

// Localized room types with cultural adaptations  
interface GlobalRoomType {
  standardType: RoomTypeStandard;
  localizedNames: Record<string, string>; // Multi-language names
  culturalVariants?: {
    [region: string]: {
      alternativeNames: string[];
      culturalRequirements: string[];
      typicalDimensions: AreaMeasurement;
      designConsiderations: string[];
    };
  };
  regionalMinimumSizes: {
    [region: string]: {
      value: number;
      unit: string;
    };
  };
}

// Global AI prompt context
interface GlobalAIPromptContext {
  region: string;
  country: string;
  locale: string;
  
  buildingCodes: string[];
  culturalContext: CulturalPreferences;
  measurementSystem: MeasurementSystem;
  
  localizedPromptTemplates: {
    [language: string]: {
      systemPrompt: string;
      userPromptTemplate: string;
      outputSchema: string;
    };
  };
  
  regionalConstraints: {
    minRoomSizes: Record<string, AreaMeasurement>;
    maxOccupancyRatios: Record<string, number>;
    setbackRequirements: Record<string, number>;
    heightRestrictions: Record<string, number>;
  };
}
```

## Core Data Contracts

### AI Command Flow
```typescript
// Base Command Structure
interface AICommandRequest {
  correlationId: string;
  timestamp: string; // ISO 8601
  userPrompt: string;
  attachments?: Attachment[];
  context?: CommandContext;
  options?: AIOptions;
}

interface AICommandResponse {
  correlationId: string;
  timestamp: string;
  status: 'success' | 'error' | 'requires_review';
  data?: any;
  errors?: ValidationError[];
  confidence?: number; // 0.0 - 1.0
  requiresHumanReview: boolean;
}

interface CommandContext {
  currentModel?: RevitModelInfo;
  selectedElements?: string[]; // Element IDs
  activeView?: string;
  userPreferences?: UserPreferences;
}

interface AIOptions {
  model: 'gpt-4' | 'claude-3-5-sonnet' | 'gemini-pro';
  temperature?: number;
  maxTokens?: number;
  confidenceThreshold?: number;
}
```

### Revit Domain Objects
```csharp
// C# Domain Models
public class RoomProgram
{
    public string CorrelationId { get; set; }
    public List<RoomRequirement> Rooms { get; set; } = new();
    public double TotalAreaM2 { get; set; }
    public string BuildingType { get; set; } // "residential", "office", "retail"
    public SpatialConstraints Constraints { get; set; }
    public StylePreferences Style { get; set; }
}

public class RoomRequirement
{
    public string Name { get; set; }
    public double AreaM2 { get; set; }
    public double? PreferredWidth { get; set; }
    public double? PreferredHeight { get; set; }
    public List<string> AdjacentToRooms { get; set; } = new();
    public List<string> RequiredFeatures { get; set; } = new(); // "window", "door", "sink"
    public AccessibilityRequirements Accessibility { get; set; }
}

public class LayoutResult
{
    public string CorrelationId { get; set; }
    public DateTime CreatedAt { get; set; }
    public List<WallDefinition> Walls { get; set; } = new();
    public List<DoorDefinition> Doors { get; set; } = new();
    public List<WindowDefinition> Windows { get; set; } = new();
    public List<RoomDefinition> Rooms { get; set; } = new();
    public List<FloorDefinition> Floors { get; set; } = new();
    public List<RoofDefinition> Roofs { get; set; } = new();
    public AIMetadata AIData { get; set; }
    public ValidationResult Validation { get; set; }
}

public class WallDefinition
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public Point3D StartPoint { get; set; }
    public Point3D EndPoint { get; set; }
    public double HeightMm { get; set; }
    public string WallTypeName { get; set; }
    public string LevelName { get; set; }
    public WallJoinBehavior JoinBehavior { get; set; }
    public List<WallParameter> Parameters { get; set; } = new();
}

public class DoorDefinition
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string HostWallId { get; set; }
    public double PositionRatio { get; set; } // 0.0 - 1.0 along wall
    public string FamilyName { get; set; }
    public string TypeName { get; set; }
    public double WidthMm { get; set; }
    public double HeightMm { get; set; }
    public DoorSwingDirection SwingDirection { get; set; }
    public List<ElementParameter> Parameters { get; set; } = new();
}

public class Point3D
{
    public double X { get; set; }
    public double Y { get; set; }
    public double Z { get; set; }
    
    // Convenience constructors
    public Point3D() { }
    public Point3D(double x, double y, double z = 0) 
    { 
        X = x; Y = y; Z = z; 
    }
}
```

### Python Data Models (Pydantic)
```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum
import uuid

class AICommandRequest(BaseModel):
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_prompt: str = Field(..., min_length=1, max_length=5000)
    attachments: Optional[List['Attachment']] = None
    context: Optional['CommandContext'] = None
    options: Optional['AIOptions'] = None

class AICommandResponse(BaseModel):
    correlation_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: Literal['success', 'error', 'requires_review']
    data: Optional[Any] = None
    errors: Optional[List['ValidationError']] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    requires_human_review: bool = False

class RoomProgram(BaseModel):
    correlation_id: str
    rooms: List['RoomRequirement']
    total_area_m2: float = Field(..., gt=0)
    building_type: Literal['residential', 'office', 'retail', 'industrial']
    constraints: Optional['SpatialConstraints'] = None
    style: Optional['StylePreferences'] = None

class WallDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_point: 'Point3D'
    end_point: 'Point3D'
    height_mm: float = Field(..., gt=0)
    wall_type_name: str
    level_name: str
    join_behavior: Optional['WallJoinBehavior'] = None
    parameters: List['WallParameter'] = Field(default_factory=list)
    
    @validator('height_mm')
    def validate_height(cls, v):
        if v < 1000 or v > 5000:  # 1m to 5m reasonable range
            raise ValueError('Wall height must be between 1000mm and 5000mm')
        return v

class Point3D(BaseModel):
    x: float
    y: float  
    z: float = 0.0
    
    def distance_to(self, other: 'Point3D') -> float:
        return ((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)**0.5
```

## JSON Schema Definitions
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "definitions": {
    "AICommandRequest": {
      "type": "object",
      "required": ["correlationId", "userPrompt"],
      "properties": {
        "correlationId": {
          "type": "string",
          "pattern": "^[A-Z]{2,3}_\\d{14}_[a-f0-9]{32}$"
        },
        "timestamp": {
          "type": "string",
          "format": "date-time"
        },
        "userPrompt": {
          "type": "string",
          "minLength": 1,
          "maxLength": 5000
        },
        "attachments": {
          "type": "array",
          "items": { "$ref": "#/definitions/Attachment" }
        },
        "context": { "$ref": "#/definitions/CommandContext" },
        "options": { "$ref": "#/definitions/AIOptions" }
      }
    },
    "LayoutResult": {
      "type": "object",
      "required": ["correlationId", "walls"],
      "properties": {
        "correlationId": { "type": "string" },
        "createdAt": { "type": "string", "format": "date-time" },
        "walls": {
          "type": "array",
          "items": { "$ref": "#/definitions/WallDefinition" },
          "minItems": 1
        },
        "doors": {
          "type": "array",
          "items": { "$ref": "#/definitions/DoorDefinition" }
        },
        "windows": {
          "type": "array", 
          "items": { "$ref": "#/definitions/WindowDefinition" }
        },
        "rooms": {
          "type": "array",
          "items": { "$ref": "#/definitions/RoomDefinition" }
        },
        "aiData": { "$ref": "#/definitions/AIMetadata" },
        "validation": { "$ref": "#/definitions/ValidationResult" }
      }
    },
    "WallDefinition": {
      "type": "object",
      "required": ["startPoint", "endPoint", "heightMm", "wallTypeName", "levelName"],
      "properties": {
        "id": { "type": "string" },
        "startPoint": { "$ref": "#/definitions/Point3D" },
        "endPoint": { "$ref": "#/definitions/Point3D" },
        "heightMm": { 
          "type": "number", 
          "minimum": 1000, 
          "maximum": 5000 
        },
        "wallTypeName": { "type": "string" },
        "levelName": { "type": "string" },
        "parameters": {
          "type": "array",
          "items": { "$ref": "#/definitions/WallParameter" }
        }
      }
    },
    "Point3D": {
      "type": "object",
      "required": ["x", "y"],
      "properties": {
        "x": { "type": "number" },
        "y": { "type": "number" },
        "z": { "type": "number", "default": 0 }
      }
    }
  }
}
```

## MCP Protocol Messages
```typescript
// MCP Standard Message Types
interface MCPRequest {
  jsonrpc: "2.0";
  id: string | number;
  method: string;
  params?: any;
}

interface MCPResponse {
  jsonrpc: "2.0";
  id: string | number;
  result?: any;
  error?: MCPError;
}

interface MCPNotification {
  jsonrpc: "2.0";
  method: string;
  params?: any;
}

// Custom MCP Extensions for Revit AutoPlan
interface RevitMCPCommand extends MCPRequest {
  method: "revit/execute_command";
  params: {
    correlationId: string;
    commandType: RevitCommandType;
    data: any;
  };
}

interface AIMCPRequest extends MCPRequest {
  method: "ai/process_prompt";
  params: {
    correlationId: string;
    prompt: string;
    model: AIModel;
    context?: any;
  };
}

type RevitCommandType = 
  | "create_layout"
  | "create_walls" 
  | "create_doors"
  | "create_windows"
  | "validate_geometry"
  | "generate_documentation";

type AIModel = "gpt-4" | "claude-3-5-sonnet" | "gemini-pro";
```

## WebSocket Message Standards
```typescript
// WebSocket Message Envelope
interface WebSocketMessage<T = any> {
  type: string;
  correlationId: string;
  timestamp: string;
  payload: T;
  version?: string; // for versioning
}

// Specific Message Types
interface AICommandMessage extends WebSocketMessage<AICommandRequest> {
  type: 'ai_command';
}

interface LayoutGeneratedMessage extends WebSocketMessage<LayoutResult> {
  type: 'layout_generated';
}

interface ValidationRequiredMessage extends WebSocketMessage<ValidationRequest> {
  type: 'validation_required';
}

interface HumanReviewMessage extends WebSocketMessage<HumanReviewRequest> {
  type: 'human_review_required';
}

interface ProgressUpdateMessage extends WebSocketMessage<ProgressUpdate> {
  type: 'progress_update';
}

interface ErrorMessage extends WebSocketMessage<ErrorDetails> {
  type: 'error';
}
```

## Validation and Error Structures
```csharp
public class ValidationResult
{
    public string CorrelationId { get; set; }
    public ValidationStatus Status { get; set; }
    public List<ValidationError> Errors { get; set; } = new();
    public List<ValidationWarning> Warnings { get; set; } = new();
    public double ConfidenceScore { get; set; }
    public bool RequiresHumanReview { get; set; }
    public DateTime ValidatedAt { get; set; }
}

public class ValidationError
{
    public string Code { get; set; } // e.g., "GEOM_001"
    public string Message { get; set; }
    public string Property { get; set; } // Which property failed
    public object? AttemptedValue { get; set; }
    public ValidationSeverity Severity { get; set; }
    public List<string> SuggestedFixes { get; set; } = new();
}

public enum ValidationStatus
{
    Valid,
    InvalidButCorrectable,
    RequiresManualReview,
    Rejected
}

public enum ValidationSeverity
{
    Info,
    Warning,
    Error,
    Critical
}
```

## Database Schema Models
```python
# SQLAlchemy Models
from sqlalchemy import Column, String, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class AICommand(Base):
    __tablename__ = 'ai_commands'
    
    correlation_id = Column(String(50), primary_key=True)
    user_prompt = Column(Text, nullable=False)
    ai_model = Column(String(50), nullable=False)
    ai_response = Column(JSON)
    confidence_score = Column(Float)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime)
    
    # Relationships
    validation_result = relationship("ValidationResult", back_populates="ai_command")
    human_review = relationship("HumanReview", back_populates="ai_command")

class LayoutResult(Base):
    __tablename__ = 'layout_results'
    
    correlation_id = Column(String(50), primary_key=True)
    layout_data = Column(JSON, nullable=False)  # Serialized LayoutResult
    ai_confidence = Column(Float)
    validation_status = Column(String(20))
    requires_human_review = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False)
    
class ValidationResult(Base):
    __tablename__ = 'validation_results'
    
    correlation_id = Column(String(50), ForeignKey('ai_commands.correlation_id'), primary_key=True)
    status = Column(String(20), nullable=False)
    errors = Column(JSON)  # List of ValidationError objects
    warnings = Column(JSON)  # List of ValidationWarning objects
    confidence_score = Column(Float)
    validated_at = Column(DateTime, nullable=False)
    
    # Relationships
    ai_command = relationship("AICommand", back_populates="validation_result")
```

## Configuration and Constants
```csharp
public static class DataConstants
{
    // Size constraints (in millimeters)
    public const double MIN_WALL_LENGTH_MM = 100;
    public const double MAX_WALL_LENGTH_MM = 50000;
    public const double MIN_WALL_HEIGHT_MM = 1000;
    public const double MAX_WALL_HEIGHT_MM = 5000;
    
    public const double MIN_DOOR_WIDTH_MM = 600;
    public const double MAX_DOOR_WIDTH_MM = 2000;
    public const double MIN_DOOR_HEIGHT_MM = 1800;
    public const double MAX_DOOR_HEIGHT_MM = 2500;
    
    public const double MIN_ROOM_AREA_M2 = 5.0;
    public const double MAX_ROOM_AREA_M2 = 1000.0;
    
    // AI model constraints
    public const double MIN_CONFIDENCE_THRESHOLD = 0.7;
    public const double HIGH_CONFIDENCE_THRESHOLD = 0.9;
    
    // Default values
    public const string DEFAULT_WALL_TYPE = "Generic - 200mm";
    public const string DEFAULT_DOOR_TYPE = "Single-Flush";
    public const string DEFAULT_WINDOW_TYPE = "Fixed";
}
```

Always validate data at system boundaries, use correlation IDs for traceability, and maintain backward compatibility through versioning.
