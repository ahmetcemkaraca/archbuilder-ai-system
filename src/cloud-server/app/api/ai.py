"""
AI processing API endpoints for ArchBuilder.AI
Implements AI command processing with usage tracking and validation
"""

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Header, BackgroundTasks
from sqlalchemy.orm import Session

from ..core.auth.authentication import get_current_user, require_subscription_tier
from ..core.billing.billing_service import billing_service, track_usage
from ..core.database import get_db
from ..models.ai import (
    AICommandRequest,
    AICommandResponse,
    AILayoutRequest,
    AILayoutResponse,
    AIRoomRequest,
    AIRoomResponse,
    AIValidationRequest,
    AIValidationResponse,
    AIProgressUpdate
)
from ..models.subscriptions import SubscriptionTier
from ..services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["ai-processing"])


@router.post("/commands", response_model=AICommandResponse, status_code=status.HTTP_201_CREATED)
@track_usage("ai_command_processing", cost_units=5)
async def process_ai_command(
    request: AICommandRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Header(..., alias="X-Correlation-ID")
) -> AICommandResponse:
    """
    Process general AI command from natural language input
    
    Supports:
    - Layout generation from text descriptions
    - Room creation and modification
    - Building analysis and optimization
    - Regulatory compliance checking
    """
    
    # Check usage limits
    if not await billing_service.check_usage_limit(current_user.id, "ai_command_processing", db):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="AI command usage limit exceeded. Please upgrade your subscription."
        )
    
    try:
        # Process AI command asynchronously
        result = await ai_service.process_command(
            request=request,
            user_id=current_user.id,
            correlation_id=correlation_id
        )
        
        # Schedule background validation if needed
        if result.requires_validation:
            background_tasks.add_task(
                ai_service.validate_ai_output,
                result.output,
                correlation_id
            )
        
        return AICommandResponse(
            correlation_id=correlation_id,
            command_type=result.command_type,
            status="completed",
            confidence=result.confidence,
            output=result.output,
            requires_review=result.requires_human_review,
            validation_errors=result.validation_errors,
            usage_remaining=await billing_service.get_remaining_usage(current_user.id, db)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI command processing failed: {str(e)}"
        )


@router.post("/layouts", response_model=AILayoutResponse)
@track_usage("ai_layout_generation", cost_units=10)
async def generate_layout(
    request: AILayoutRequest,
    current_user = Depends(require_subscription_tier(SubscriptionTier.STARTER)),
    db: Session = Depends(get_db),
    correlation_id: str = Header(..., alias="X-Correlation-ID")
) -> AILayoutResponse:
    """
    Generate architectural layout from detailed requirements
    
    Requires STARTER subscription or higher
    Advanced layout generation with:
    - Multi-room coordination
    - Building code compliance
    - Optimization algorithms
    """
    
    # Check usage limits
    if not await billing_service.check_usage_limit(current_user.id, "ai_layout_generation", db):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Layout generation usage limit exceeded. Please upgrade your subscription."
        )
    
    try:
        # Generate layout using AI service
        layout_result = await ai_service.generate_layout(
            request=request,
            user_id=current_user.id,
            correlation_id=correlation_id
        )
        
        return AILayoutResponse(
            correlation_id=correlation_id,
            layout_id=layout_result.layout_id,
            confidence=layout_result.confidence,
            room_count=layout_result.room_count,
            total_area=layout_result.total_area,
            rooms=layout_result.rooms,
            walls=layout_result.walls,
            doors=layout_result.doors,
            windows=layout_result.windows,
            compliance_status=layout_result.compliance_status,
            optimization_score=layout_result.optimization_score,
            requires_review=layout_result.requires_human_review,
            next_steps=layout_result.next_steps
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Layout generation failed: {str(e)}"
        )


@router.post("/rooms", response_model=AIRoomResponse)
@track_usage("ai_room_generation", cost_units=3)
async def generate_room(
    request: AIRoomRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Header(..., alias="X-Correlation-ID")
) -> AIRoomResponse:
    """
    Generate individual room layout and furniture placement
    
    Available for all subscription tiers with usage limits
    """
    
    # Check usage limits
    if not await billing_service.check_usage_limit(current_user.id, "ai_room_generation", db):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Room generation usage limit exceeded. Please upgrade your subscription."
        )
    
    try:
        # Generate room using AI service
        room_result = await ai_service.generate_room(
            request=request,
            user_id=current_user.id,
            correlation_id=correlation_id
        )
        
        return AIRoomResponse(
            correlation_id=correlation_id,
            room_id=room_result.room_id,
            room_type=room_result.room_type,
            dimensions=room_result.dimensions,
            furniture=room_result.furniture,
            lighting=room_result.lighting,
            materials=room_result.materials,
            confidence=room_result.confidence,
            compliance_notes=room_result.compliance_notes,
            cost_estimate=room_result.cost_estimate
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Room generation failed: {str(e)}"
        )


@router.post("/validate", response_model=AIValidationResponse)
async def validate_design(
    request: AIValidationRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Header(..., alias="X-Correlation-ID")
) -> AIValidationResponse:
    """
    Validate architectural design against building codes and best practices
    
    Free validation service for all users
    """
    
    try:
        # Validate design using AI service
        validation_result = await ai_service.validate_design(
            request=request,
            user_id=current_user.id,
            correlation_id=correlation_id
        )
        
        return AIValidationResponse(
            correlation_id=correlation_id,
            is_valid=validation_result.is_valid,
            confidence=validation_result.confidence,
            compliance_score=validation_result.compliance_score,
            errors=validation_result.errors,
            warnings=validation_result.warnings,
            suggestions=validation_result.suggestions,
            building_codes_checked=validation_result.building_codes_checked,
            validation_timestamp=validation_result.validation_timestamp
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Design validation failed: {str(e)}"
        )


@router.get("/commands/{correlation_id}", response_model=AICommandResponse)
async def get_ai_command_status(
    correlation_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> AICommandResponse:
    """
    Get AI command result by correlation ID
    
    Supports polling for long-running AI operations
    """
    
    try:
        # Get command status from AI service
        command = await ai_service.get_command_status(
            correlation_id=correlation_id,
            user_id=current_user.id
        )
        
        if not command:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI command not found or access denied"
            )
        
        return command
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve AI command: {str(e)}"
        )


@router.get("/commands", response_model=List[AICommandResponse])
async def list_ai_commands(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
) -> List[AICommandResponse]:
    """
    List user's AI command history with pagination
    """
    
    try:
        commands = await ai_service.list_user_commands(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        return commands
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve AI commands: {str(e)}"
        )


@router.delete("/commands/{correlation_id}")
async def delete_ai_command(
    correlation_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Delete AI command and associated data
    """
    
    try:
        success = await ai_service.delete_command(
            correlation_id=correlation_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI command not found or access denied"
            )
        
        return {
            "message": "AI command deleted successfully",
            "correlation_id": correlation_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete AI command: {str(e)}"
        )


@router.get("/models", response_model=List[dict])
async def list_available_models(
    current_user = Depends(get_current_user)
) -> List[dict]:
    """
    List available AI models and their capabilities
    """
    
    models = [
        {
            "name": "Gemini-2.5-Flash-Lite",
            "provider": "Vertex AI",
            "capabilities": [
                "layout_generation",
                "room_design",
                "compliance_checking",
                "optimization"
            ],
            "tier_required": "FREE",
            "cost_units": 5
        },
        {
            "name": "GPT-4.1",
            "provider": "GitHub Models",
            "capabilities": [
                "advanced_layout_generation",
                "architectural_analysis",
                "complex_optimization",
                "multi_building_design"
            ],
            "tier_required": "PROFESSIONAL",
            "cost_units": 15
        }
    ]
    
    return models


@router.get("/usage", response_model=dict)
async def get_ai_usage_stats(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get AI usage statistics for current user
    """
    
    try:
        remaining_usage = await billing_service.get_remaining_usage(current_user.id, db)
        subscription = await billing_service.get_subscription_details(current_user.id, db)
        
        return {
            "subscription_tier": subscription.tier,
            "billing_period": {
                "start": subscription.current_period_start,
                "end": subscription.current_period_end
            },
            "usage_remaining": remaining_usage,
            "limits": {
                "ai_layouts": subscription.limits.ai_layouts_per_month,
                "ai_rooms": subscription.limits.ai_rooms_per_month,
                "api_calls": subscription.limits.api_calls_per_hour
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve usage stats: {str(e)}"
        )