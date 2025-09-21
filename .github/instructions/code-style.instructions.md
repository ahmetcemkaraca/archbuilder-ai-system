---
applyTo: "src/revit-plugin/**/*.cs,src/mcp-server/**/*.py,src/ai-models/**/*.cs,**/*.ts,**/*.tsx,**/*.js,**/*.jsx"
description: Code Style Standards — consistent formatting, structure, and best practices across all technologies.
---
As Code Style Developer:
- Apply consistent formatting rules across C#, Python, TypeScript, and JavaScript
- Follow technology-specific best practices while maintaining cross-language consistency
- Implement proper code organization, commenting, and documentation standards
- Ensure code readability and maintainability for AI-generated code
- Establish patterns for async/await, error handling, and dependency injection

## C# Code Style Standards

### File Organization and Naming
```csharp
// File: LayoutGenerationService.cs
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Configuration;
using RevitAutoPlan.Core.Models;
using RevitAutoPlan.Core.Interfaces;

namespace RevitAutoPlan.Services
{
    /// <summary>
    /// Service responsible for generating architectural layouts using AI models.
    /// Handles prompt processing, AI model communication, and result validation.
    /// </summary>
    public class LayoutGenerationService : ILayoutGenerationService
    {
        #region Private Fields
        
        private readonly ILogger<LayoutGenerationService> _logger;
        private readonly IAIModelClient _aiModelClient;
        private readonly IValidationService _validationService;
        private readonly IConfiguration _configuration;
        
        #endregion
        
        #region Constructor
        
        public LayoutGenerationService(
            ILogger<LayoutGenerationService> logger,
            IAIModelClient aiModelClient,
            IValidationService validationService,
            IConfiguration configuration)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _aiModelClient = aiModelClient ?? throw new ArgumentNullException(nameof(aiModelClient));
            _validationService = validationService ?? throw new ArgumentNullException(nameof(validationService));
            _configuration = configuration ?? throw new ArgumentNullException(nameof(configuration));
        }
        
        #endregion
        
        #region Public Methods
        
        /// <summary>
        /// Generates an architectural layout from user prompt and requirements.
        /// </summary>
        /// <param name="request">Layout generation request containing user prompt and context</param>
        /// <param name="correlationId">Unique identifier for tracking this operation</param>
        /// <param name="cancellationToken">Cancellation token for async operation</param>
        /// <returns>Generated layout result with validation status</returns>
        public async Task<LayoutResult> GenerateLayoutAsync(
            LayoutGenerationRequest request,
            string correlationId,
            CancellationToken cancellationToken = default)
        {
            using var scope = _logger.BeginScope("GenerateLayout {CorrelationId}", correlationId);
            
            try
            {
                _logger.LogInformation("Starting layout generation", correlationId);
                
                // Validate input request
                var inputValidation = await ValidateInputAsync(request, correlationId);
                if (!inputValidation.IsValid)
                {
                    throw new ValidationException("Invalid input parameters", inputValidation.Errors);
                }
                
                // Generate layout using AI
                var aiResponse = await CallAIServiceAsync(request, correlationId, cancellationToken);
                
                // Validate AI output
                var outputValidation = await _validationService.ValidateLayoutAsync(aiResponse, correlationId);
                
                var result = new LayoutResult
                {
                    CorrelationId = correlationId,
                    Layout = aiResponse,
                    Validation = outputValidation,
                    CreatedAt = DateTime.UtcNow,
                    RequiresHumanReview = outputValidation.RequiresHumanReview
                };
                
                _logger.LogInformation("Layout generation completed successfully", correlationId);
                return result;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Layout generation failed", correlationId);
                throw;
            }
        }
        
        #endregion
        
        #region Private Methods
        
        private async Task<ValidationResult> ValidateInputAsync(
            LayoutGenerationRequest request, 
            string correlationId)
        {
            // Input validation logic
            var errors = new List<ValidationError>();
            
            if (string.IsNullOrWhiteSpace(request.UserPrompt))
            {
                errors.Add(new ValidationError
                {
                    Code = "INPUT_001",
                    Message = "User prompt cannot be empty",
                    Property = nameof(request.UserPrompt)
                });
            }
            
            if (request.TotalAreaM2 <= 0)
            {
                errors.Add(new ValidationError
                {
                    Code = "INPUT_002", 
                    Message = "Total area must be greater than 0",
                    Property = nameof(request.TotalAreaM2)
                });
            }
            
            return new ValidationResult
            {
                IsValid = errors.Count == 0,
                Errors = errors,
                CorrelationId = correlationId
            };
        }
        
        private async Task<LayoutData> CallAIServiceAsync(
            LayoutGenerationRequest request,
            string correlationId,
            CancellationToken cancellationToken)
        {
            const int maxRetries = 3;
            
            for (int attempt = 1; attempt <= maxRetries; attempt++)
            {
                try
                {
                    _logger.LogInformation("AI service call attempt {Attempt}", attempt, correlationId);
                    
                    var response = await _aiModelClient.GenerateLayoutAsync(
                        request, 
                        correlationId, 
                        cancellationToken);
                    
                    return response;
                }
                catch (Exception ex) when (attempt < maxRetries)
                {
                    _logger.LogWarning(ex, "AI service call failed, retrying {Attempt}/{MaxRetries}", 
                        attempt, maxRetries, correlationId);
                    
                    await Task.Delay(TimeSpan.FromSeconds(Math.Pow(2, attempt)), cancellationToken);
                }
            }
            
            throw new AIServiceException("AI service failed after all retry attempts");
        }
        
        #endregion
    }
}
```

### Method and Property Conventions
```csharp
// Properties: PascalCase with proper access modifiers
public string CorrelationId { get; set; }
public DateTime CreatedAt { get; init; } // Use init for immutable after construction
public bool RequiresHumanReview { get; private set; } // Private setter when appropriate

// Methods: PascalCase with clear naming
public async Task<ValidationResult> ValidateLayoutAsync(LayoutData layout, string correlationId)
public bool IsGeometricallyValid(List<WallDefinition> walls)
public void ApplyUserCorrections(List<Correction> corrections)

// Events: PascalCase with Event suffix
public event EventHandler<LayoutGeneratedEventArgs> LayoutGenerated;
public event EventHandler<ValidationCompletedEventArgs> ValidationCompleted;

// Constants: SCREAMING_SNAKE_CASE
public const double DEFAULT_WALL_HEIGHT_MM = 2700.0;
public const int MAX_RETRY_ATTEMPTS = 3;
public const string DEFAULT_WALL_TYPE_NAME = "Generic - 200mm";

// Async methods: Always suffix with Async
public async Task<LayoutResult> GenerateLayoutAsync()
public async Task<bool> ValidateAsync()
public async Task SaveToFileAsync(string filePath)
```

## Python Code Style Standards

### File Organization and Type Hints
```python
"""
Layout Generation Service

This module provides services for generating architectural layouts using AI models.
Handles prompt processing, AI model communication, and result validation.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

import structlog
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException, status

from revit_autoplan.core.models import (
    LayoutGenerationRequest,
    LayoutResult, 
    ValidationResult,
    AIModelResponse
)
from revit_autoplan.core.interfaces import (
    IAIModelClient,
    IValidationService,
    IPromptEngine
)
from revit_autoplan.core.exceptions import (
    ValidationException,
    AIServiceException,
    MCPException
)

logger = structlog.get_logger(__name__)


class LayoutGenerationService:
    """Service responsible for generating architectural layouts using AI models."""
    
    def __init__(
        self,
        ai_model_client: IAIModelClient,
        validation_service: IValidationService,
        prompt_engine: IPromptEngine,
        config: Dict[str, Any]
    ) -> None:
        """Initialize the layout generation service.
        
        Args:
            ai_model_client: Client for communicating with AI models
            validation_service: Service for validating AI outputs
            prompt_engine: Engine for generating optimized prompts
            config: Configuration dictionary
            
        Raises:
            ValueError: If required dependencies are None
        """
        if not ai_model_client:
            raise ValueError("ai_model_client cannot be None")
        if not validation_service:
            raise ValueError("validation_service cannot be None")
        if not prompt_engine:
            raise ValueError("prompt_engine cannot be None")
            
        self._ai_model_client = ai_model_client
        self._validation_service = validation_service
        self._prompt_engine = prompt_engine
        self._config = config
        self._max_retries = config.get("max_retries", 3)
        
    async def generate_layout(
        self,
        request: LayoutGenerationRequest,
        correlation_id: str,
    ) -> LayoutResult:
        """Generate an architectural layout from user prompt and requirements.
        
        Args:
            request: Layout generation request containing user prompt and context
            correlation_id: Unique identifier for tracking this operation
            
        Returns:
            Generated layout result with validation status
            
        Raises:
            ValidationException: If input validation fails
            AIServiceException: If AI service fails after retries
            MCPException: If MCP communication fails
        """
        logger.info(
            "Starting layout generation",
            correlation_id=correlation_id,
            user_prompt=request.user_prompt[:100] + "..." if len(request.user_prompt) > 100 else request.user_prompt
        )
        
        try:
            # Validate input request
            input_validation = await self._validate_input(request, correlation_id)
            if not input_validation.is_valid:
                raise ValidationException(
                    "Invalid input parameters",
                    validation_result=input_validation
                )
            
            # Generate optimized prompt
            optimized_prompt = await self._prompt_engine.create_layout_prompt(
                request, correlation_id
            )
            
            # Call AI service with retry logic
            ai_response = await self._call_ai_service_with_retry(
                optimized_prompt, correlation_id
            )
            
            # Validate AI output
            output_validation = await self._validation_service.validate_layout(
                ai_response, correlation_id
            )
            
            # Create result object
            result = LayoutResult(
                correlation_id=correlation_id,
                layout=ai_response,
                validation=output_validation,
                created_at=datetime.utcnow(),
                requires_human_review=output_validation.requires_human_review
            )
            
            logger.info(
                "Layout generation completed successfully",
                correlation_id=correlation_id,
                confidence_score=ai_response.confidence,
                requires_review=result.requires_human_review
            )
            
            return result
            
        except Exception as exc:
            logger.error(
                "Layout generation failed",
                correlation_id=correlation_id,
                error=str(exc),
                exc_info=True
            )
            raise
    
    async def _validate_input(
        self, 
        request: LayoutGenerationRequest,
        correlation_id: str
    ) -> ValidationResult:
        """Validate input request parameters."""
        errors = []
        
        if not request.user_prompt or not request.user_prompt.strip():
            errors.append({
                "code": "INPUT_001",
                "message": "User prompt cannot be empty",
                "field": "user_prompt"
            })
            
        if request.total_area_m2 <= 0:
            errors.append({
                "code": "INPUT_002",
                "message": "Total area must be greater than 0",
                "field": "total_area_m2"
            })
            
        if not request.building_type:
            errors.append({
                "code": "INPUT_003",
                "message": "Building type must be specified",
                "field": "building_type"
            })
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            correlation_id=correlation_id
        )
    
    async def _call_ai_service_with_retry(
        self,
        prompt: str,
        correlation_id: str
    ) -> AIModelResponse:
        """Call AI service with exponential backoff retry logic."""
        last_exception = None
        
        for attempt in range(1, self._max_retries + 1):
            try:
                logger.info(
                    "AI service call attempt",
                    attempt=attempt,
                    correlation_id=correlation_id
                )
                
                response = await self._ai_model_client.generate_layout(
                    prompt=prompt,
                    correlation_id=correlation_id
                )
                
                return response
                
            except Exception as exc:
                last_exception = exc
                
                if attempt < self._max_retries:
                    delay = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        "AI service call failed, retrying",
                        attempt=attempt,
                        max_retries=self._max_retries,
                        delay_seconds=delay,
                        error=str(exc),
                        correlation_id=correlation_id
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "AI service call failed after all retries",
                        attempts=self._max_retries,
                        error=str(exc),
                        correlation_id=correlation_id
                    )
        
        raise AIServiceException(
            f"AI service failed after {self._max_retries} attempts"
        ) from last_exception


# Function definitions: snake_case
async def process_user_command(command: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Process user command and return structured response."""
    pass

def calculate_room_dimensions(area_m2: float, aspect_ratio: float = 1.0) -> tuple[float, float]:
    """Calculate room width and height from area and aspect ratio."""
    width = (area_m2 * aspect_ratio) ** 0.5
    height = area_m2 / width
    return width, height

def validate_geometry(walls: List[Dict[str, Any]]) -> bool:
    """Validate geometric constraints of wall definitions."""
    pass

# Constants: SCREAMING_SNAKE_CASE
DEFAULT_WALL_HEIGHT_MM = 2700.0
MAX_RETRY_ATTEMPTS = 3
MIN_ROOM_AREA_M2 = 5.0
API_TIMEOUT_SECONDS = 30

# Private methods: _snake_case prefix
def _normalize_coordinates(point: Dict[str, float]) -> Dict[str, float]:
    """Normalize coordinate values to valid ranges."""
    pass
```

## TypeScript/JavaScript Code Style Standards

### Interface and Class Definitions
```typescript
/**
 * Service for generating architectural layouts using AI models.
 * Handles prompt processing, AI model communication, and result validation.
 */
export class LayoutGenerationService {
    private readonly logger: ILogger;
    private readonly aiModelClient: IAIModelClient;
    private readonly validationService: IValidationService;
    private readonly config: ServiceConfig;
    
    constructor(
        logger: ILogger,
        aiModelClient: IAIModelClient,
        validationService: IValidationService,
        config: ServiceConfig
    ) {
        this.logger = logger;
        this.aiModelClient = aiModelClient;
        this.validationService = validationService;
        this.config = config;
    }
    
    /**
     * Generate an architectural layout from user prompt and requirements.
     * @param request Layout generation request containing user prompt and context
     * @param correlationId Unique identifier for tracking this operation
     * @returns Promise resolving to generated layout result with validation status
     */
    public async generateLayout(
        request: LayoutGenerationRequest,
        correlationId: string
    ): Promise<LayoutResult> {
        this.logger.info('Starting layout generation', { correlationId });
        
        try {
            // Validate input request
            const inputValidation = await this.validateInput(request, correlationId);
            if (!inputValidation.isValid) {
                throw new ValidationException('Invalid input parameters', inputValidation.errors);
            }
            
            // Generate layout using AI
            const aiResponse = await this.callAIServiceWithRetry(request, correlationId);
            
            // Validate AI output
            const outputValidation = await this.validationService.validateLayout(
                aiResponse, 
                correlationId
            );
            
            const result: LayoutResult = {
                correlationId,
                layout: aiResponse,
                validation: outputValidation,
                createdAt: new Date(),
                requiresHumanReview: outputValidation.requiresHumanReview
            };
            
            this.logger.info('Layout generation completed successfully', { 
                correlationId,
                confidence: aiResponse.confidence 
            });
            
            return result;
            
        } catch (error) {
            this.logger.error('Layout generation failed', { 
                correlationId, 
                error: error.message 
            });
            throw error;
        }
    }
    
    private async validateInput(
        request: LayoutGenerationRequest,
        correlationId: string
    ): Promise<ValidationResult> {
        const errors: ValidationError[] = [];
        
        if (!request.userPrompt?.trim()) {
            errors.push({
                code: 'INPUT_001',
                message: 'User prompt cannot be empty',
                field: 'userPrompt'
            });
        }
        
        if (request.totalAreaM2 <= 0) {
            errors.push({
                code: 'INPUT_002',
                message: 'Total area must be greater than 0',
                field: 'totalAreaM2'
            });
        }
        
        return {
            isValid: errors.length === 0,
            errors,
            correlationId
        };
    }
    
    private async callAIServiceWithRetry(
        request: LayoutGenerationRequest,
        correlationId: string
    ): Promise<AIModelResponse> {
        const maxRetries = this.config.maxRetries;
        let lastError: Error;
        
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                this.logger.info('AI service call attempt', { attempt, correlationId });
                
                const response = await this.aiModelClient.generateLayout(
                    request,
                    correlationId
                );
                
                return response;
                
            } catch (error) {
                lastError = error as Error;
                
                if (attempt < maxRetries) {
                    const delay = Math.pow(2, attempt) * 1000; // Exponential backoff
                    this.logger.warn('AI service call failed, retrying', {
                        attempt,
                        maxRetries,
                        delayMs: delay,
                        error: error.message,
                        correlationId
                    });
                    
                    await this.delay(delay);
                }
            }
        }
        
        throw new AIServiceException(
            `AI service failed after ${maxRetries} attempts`,
            lastError
        );
    }
    
    private delay(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Interface definitions: IPascalCase
interface ILayoutGenerationService {
    generateLayout(request: LayoutGenerationRequest, correlationId: string): Promise<LayoutResult>;
}

interface LayoutGenerationRequest {
    correlationId: string;
    userPrompt: string;
    totalAreaM2: number;
    buildingType: BuildingType;
    context?: CommandContext;
}

interface LayoutResult {
    correlationId: string;
    layout: LayoutData;
    validation: ValidationResult;
    createdAt: Date;
    requiresHumanReview: boolean;
}

// Type definitions
type BuildingType = 'residential' | 'office' | 'retail' | 'industrial';
type ValidationStatus = 'valid' | 'invalid' | 'requires_review';

// Enums: PascalCase
enum AIModelType {
    GPT4 = 'gpt-4',
    Claude35Sonnet = 'claude-3-5-sonnet',
    GeminiPro = 'gemini-pro'
}

// Constants: SCREAMING_SNAKE_CASE
const DEFAULT_WALL_HEIGHT_MM = 2700;
const MAX_RETRY_ATTEMPTS = 3;
const MIN_ROOM_AREA_M2 = 5.0;
const API_TIMEOUT_MS = 30000;

// Functions: camelCase
export function calculateRoomDimensions(areaM2: number, aspectRatio: number = 1.0): [number, number] {
    const width = Math.sqrt(areaM2 * aspectRatio);
    const height = areaM2 / width;
    return [width, height];
}

export async function processUserCommand(
    command: string, 
    context: CommandContext
): Promise<CommandResult> {
    // Implementation
}

export function validateGeometry(walls: WallDefinition[]): boolean {
    // Implementation
}
```

## General Code Organization Principles

### File Structure Standards
```
src/
├── core/                       # Shared core functionality
│   ├── interfaces/            # Interface definitions
│   ├── models/               # Data models and DTOs
│   ├── exceptions/           # Custom exception classes
│   └── constants/            # Application constants
├── services/                  # Business logic services
│   ├── ai/                   # AI-related services
│   ├── validation/           # Validation services
│   └── revit/               # Revit API services
├── infrastructure/           # Infrastructure concerns
│   ├── data/                # Data access layer
│   ├── external/            # External service clients
│   └── logging/             # Logging configuration
└── presentation/             # UI and API controllers
    ├── api/                 # REST API controllers
    ├── websockets/          # WebSocket handlers
    └── ui/                  # User interface components
```

### Comment and Documentation Standards
```csharp
/// <summary>
/// Generates an architectural layout using AI models with comprehensive validation.
/// This method handles the complete workflow from prompt processing to result validation.
/// </summary>
/// <param name="request">The layout generation request containing user requirements</param>
/// <param name="correlationId">Unique identifier for tracking this operation across services</param>
/// <param name="cancellationToken">Token to cancel the operation if needed</param>
/// <returns>
/// A <see cref="LayoutResult"/> containing the generated layout, validation results,
/// and metadata about the AI processing.
/// </returns>
/// <exception cref="ValidationException">
/// Thrown when input validation fails or AI output is invalid
/// </exception>
/// <exception cref="AIServiceException">
/// Thrown when the AI service fails after all retry attempts
/// </exception>
/// <example>
/// <code>
/// var request = new LayoutGenerationRequest
/// {
///     UserPrompt = "Create a 2-bedroom apartment",
///     TotalAreaM2 = 80,
///     BuildingType = "residential"
/// };
/// 
/// var result = await service.GenerateLayoutAsync(request, correlationId);
/// if (result.RequiresHumanReview)
/// {
///     // Handle human review workflow
/// }
/// </code>
/// </example>
public async Task<LayoutResult> GenerateLayoutAsync(
    LayoutGenerationRequest request,
    string correlationId,
    CancellationToken cancellationToken = default)
{
    // Method implementation
}
```

Always prioritize readability, maintain consistent formatting, include comprehensive error handling, and document complex logic with clear comments.
