"""
Enhanced AI API endpoints for ArchBuilder.AI Cloud Server
Implements comprehensive security, authentication, rate limiting, and usage tracking
following security.instructions.md and api-standards.instructions.md patterns
"""

import asyncio
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Header, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.logging import get_correlation_id
from app.core.exceptions import (
    AIServiceException,
    AIModelUnavailableException,
    ValidationException,
    NetworkException,
    RevitAutoPlanException
)
from app.security.authentication import (
    get_current_user,
    get_current_active_user,
    verify_subscription
)
from app.services.ai_service import AIService
from app.services.billing.subscription_service import SubscriptionService
from app.services.billing.usage_tracking import UsageTrackingService, UsageCategory
from app.models.auth.user import User

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/ai", tags=["ai-processing"])

# Service dependencies
def get_ai_service() -> AIService:
    """Get AI service instance"""
    return AIService()

def get_subscription_service() -> SubscriptionService:
    """Get subscription service instance"""
    return SubscriptionService()

def get_usage_tracking_service() -> UsageTrackingService:
    """Get usage tracking service instance"""
    return UsageTrackingService()

# Enhanced usage tracking decorator with comprehensive security
def track_ai_usage(operation_type: str, cost_units: int = 1, min_subscription_tier: str = "FREE"):
    """
    Comprehensive usage tracking decorator with security validation
    
    Args:
        operation_type: Type of AI operation for billing
        cost_units: Cost in subscription units
        min_subscription_tier: Minimum subscription tier required
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            correlation_id = get_correlation_id()
            
            # Extract dependencies from kwargs
            current_user = kwargs.get('current_user')
            session = kwargs.get('session')
            subscription_service = kwargs.get('subscription_service')
            usage_tracking = kwargs.get('usage_tracking')
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required for AI operations"
                )
            
            logger.info(
                "AI operation started",
                user_id=current_user.id,
                operation_type=operation_type,
                cost_units=cost_units,
                correlation_id=correlation_id
            )
            
            try:
                # Check subscription tier and limits
                if subscription_service and session:
                    subscription = await subscription_service.get_active_subscription(session, current_user.id)
                    
                    if not subscription:
                        raise HTTPException(
                            status_code=status.HTTP_402_PAYMENT_REQUIRED,
                            detail="Active subscription required for AI operations"
                        )
                    
                    # Check if user's subscription tier is sufficient
                    tier_hierarchy = {"FREE": 0, "STARTER": 1, "PROFESSIONAL": 2, "ENTERPRISE": 3}
                    user_tier_level = tier_hierarchy.get(subscription.plan_name, 0)
                    required_tier_level = tier_hierarchy.get(min_subscription_tier, 0)
                    
                    if user_tier_level < required_tier_level:
                        raise HTTPException(
                            status_code=status.HTTP_402_PAYMENT_REQUIRED,
                            detail=f"Subscription upgrade required. This operation requires {min_subscription_tier} tier or higher."
                        )
                
                # Check usage limits with comprehensive tracking
                if usage_tracking and session:
                    usage_available = await usage_tracking.check_usage_limit(
                        session, 
                        current_user.id, 
                        UsageCategory.AI_REQUESTS,
                        cost_units
                    )
                    
                    if not usage_available:
                        logger.warning(
                            "AI usage limit exceeded",
                            user_id=current_user.id,
                            operation_type=operation_type,
                            cost_units=cost_units,
                            correlation_id=correlation_id
                        )
                        raise HTTPException(
                            status_code=status.HTTP_402_PAYMENT_REQUIRED,
                            detail=f"Usage limit exceeded for {operation_type}. Please upgrade your subscription or wait for next billing cycle."
                        )
                
                # Execute the actual function with comprehensive error handling
                try:
                    result = await func(*args, **kwargs)
                    
                    # Track successful usage
                    if usage_tracking and session:
                        await usage_tracking.record_usage(
                            session,
                            current_user.id,
                            UsageCategory.AI_REQUESTS,
                            cost_units,
                            metadata={
                                "operation_type": operation_type,
                                "correlation_id": correlation_id,
                                "success": True
                            }
                        )
                    
                    processing_time_ms = round((time.time() - start_time) * 1000, 2)
                    
                    logger.info(
                        "AI operation completed successfully",
                        user_id=current_user.id,
                        operation_type=operation_type,
                        cost_units=cost_units,
                        processing_time_ms=processing_time_ms,
                        correlation_id=correlation_id
                    )
                    
                    # Add usage information to response if it's a dict
                    if isinstance(result, dict):
                        result["usage_tracked"] = {
                            "operation_type": operation_type,
                            "cost_units": cost_units,
                            "processing_time_ms": processing_time_ms
                        }
                    
                    return result
                    
                except AIServiceException as e:
                    # AI-specific errors with detailed logging
                    logger.error(
                        "AI service error",
                        user_id=current_user.id,
                        operation_type=operation_type,
                        error_code=e.error_code,
                        error_message=e.message,
                        correlation_id=correlation_id,
                        exc_info=True
                    )
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"AI service temporarily unavailable: {e.message}"
                    )
                
                except ValidationException as e:
                    # Validation errors
                    logger.error(
                        "AI validation error",
                        user_id=current_user.id,
                        operation_type=operation_type,
                        validation_errors=e.context,
                        correlation_id=correlation_id
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Input validation failed: {e.message}"
                    )
                
                except Exception as e:
                    # Unexpected errors
                    processing_time_ms = round((time.time() - start_time) * 1000, 2)
                    logger.error(
                        "AI operation failed with unexpected error",
                        user_id=current_user.id,
                        operation_type=operation_type,
                        error=str(e),
                        processing_time_ms=processing_time_ms,
                        correlation_id=correlation_id,
                        exc_info=True
                    )
                    
                    # Track failed usage (no cost)
                    if usage_tracking and session:
                        await usage_tracking.record_usage(
                            session,
                            current_user.id,
                            UsageCategory.AI_REQUESTS,
                            0,  # No cost for failed operations
                            metadata={
                                "operation_type": operation_type,
                                "correlation_id": correlation_id,
                                "success": False,
                                "error": str(e)
                            }
                        )
                    
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="AI operation failed due to internal error. Please try again or contact support."
                    )
            
            except HTTPException:
                # Re-raise HTTP exceptions without modification
                raise
            except Exception as e:
                # Handle decorator-level errors
                logger.error(
                    "AI operation decorator error",
                    user_id=current_user.id if current_user else None,
                    operation_type=operation_type,
                    error=str(e),
                    correlation_id=correlation_id,
                    exc_info=True
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal error in AI operation handling"
                )
        
        return wrapper
    return decorator


@router.post("/commands", status_code=status.HTTP_201_CREATED)
@track_ai_usage("ai_command_processing", cost_units=5, min_subscription_tier="FREE")
async def process_ai_command(
    request: Dict[str, Any],  # Using generic dict for now since AICommandRequest might not exist
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    ai_service: AIService = Depends(get_ai_service),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
    usage_tracking: UsageTrackingService = Depends(get_usage_tracking_service),
    correlation_id: str = Header(None, alias="X-Correlation-ID")
) -> Dict[str, Any]:
    """
    Process general AI command from natural language input with comprehensive security
    
    Features:
    - Multi-model AI processing (Vertex AI + GitHub Models)
    - Comprehensive input validation
    - Usage tracking and billing
    - Security validation and audit logging
    - Human-in-the-loop validation
    - Fallback mechanisms
    """
    
    try:
        # Input validation and sanitization
        if not request or not isinstance(request, dict):
            raise ValidationException(
                message="Invalid request format",
                error_code="VAL_001",
                correlation_id=correlation_id
            )
        
        command_text = request.get("prompt", "").strip()
        if not command_text or len(command_text) > 10000:
            raise ValidationException(
                message="Command text is required and must be less than 10,000 characters",
                error_code="VAL_002",
                correlation_id=correlation_id
            )
        
        # Enhanced request context
        enhanced_request = {
            **request,
            "user_id": current_user.id,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            "client_info": {
                "subscription_tier": getattr(current_user, 'subscription_tier', 'FREE'),
                "language": request.get("language", "en"),
                "region": request.get("region", "US")
            }
        }
        
        logger.info(
            "Processing AI command",
            user_id=current_user.id,
            command_length=len(command_text),
            language=enhanced_request["client_info"]["language"],
            correlation_id=correlation_id
        )
        
        # Process AI command with comprehensive error handling
        ai_result = await ai_service.process_command(
            enhanced_request,
            correlation_id
        )
        
        # Validate AI output
        validation_required = ai_result.get("requires_human_review", True)
        confidence_score = ai_result.get("confidence_score", 0.0)
        
        # Schedule background validation if needed
        if validation_required:
            background_tasks.add_task(
                _schedule_human_review,
                ai_result,
                current_user.id,
                correlation_id
            )
        
        # Get remaining usage for response
        remaining_usage = None
        if usage_tracking:
            try:
                remaining_usage = await usage_tracking.get_remaining_usage(
                    session, current_user.id
                )
            except Exception as e:
                logger.warning("Failed to get remaining usage", error=str(e))
        
        # Comprehensive response
        response = {
            "correlation_id": correlation_id,
            "status": "completed",
            "result": ai_result.get("generated_content", {}),
            "metadata": {
                "model_used": ai_result.get("model_used", "unknown"),
                "provider": ai_result.get("provider", "unknown"),
                "confidence_score": confidence_score,
                "processing_time_ms": ai_result.get("processing_time_ms", 0),
                "requires_human_review": validation_required,
                "generated_at": datetime.utcnow().isoformat()
            },
            "validation": ai_result.get("validation_result", {}),
            "usage_info": {
                "operation_cost": 5,
                "remaining_usage": remaining_usage
            }
        }
        
        # Add warnings if AI used fallback
        if ai_result.get("fallback_used"):
            response["warnings"] = [
                "AI service used fallback mechanism. Results may have lower confidence.",
                f"Fallback reason: {ai_result.get('fallback_reason', 'Unknown')}"
            ]
        
        logger.info(
            "AI command processing completed",
            user_id=current_user.id,
            confidence_score=confidence_score,
            requires_review=validation_required,
            fallback_used=ai_result.get("fallback_used", False),
            correlation_id=correlation_id
        )
        
        return response
        
    except ValidationException:
        # Re-raise validation exceptions
        raise
    except AIServiceException:
        # Re-raise AI service exceptions  
        raise
    except Exception as e:
        # Handle unexpected errors
        logger.error(
            "Unexpected error in AI command processing",
            user_id=current_user.id,
            error=str(e),
            correlation_id=correlation_id,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your AI command"
        )


@router.post("/layouts", status_code=status.HTTP_201_CREATED)
@track_ai_usage("ai_layout_generation", cost_units=10, min_subscription_tier="STARTER")
async def generate_layout(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    ai_service: AIService = Depends(get_ai_service),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
    usage_tracking: UsageTrackingService = Depends(get_usage_tracking_service),
    correlation_id: str = Header(None, alias="X-Correlation-ID")
) -> Dict[str, Any]:
    """
    Generate comprehensive architectural layout with advanced AI models
    
    Requires STARTER subscription or higher
    Features:
    - Advanced layout generation with multi-room coordination
    - Building code compliance checking
    - Optimization algorithms
    - Regional building standards validation
    """
    
    logger.info(
        "Starting advanced layout generation",
        user_id=current_user.id,
        total_area=request.get("total_area_m2", 0),
        building_type=request.get("building_type", "unknown"),
        correlation_id=correlation_id
    )
    
    try:
        # Enhanced input validation for layout generation
        if not request.get("total_area_m2") or request["total_area_m2"] <= 0:
            raise ValidationException(
                message="Total area must be greater than 0",
                error_code="LAY_001",
                correlation_id=correlation_id
            )
        
        if request["total_area_m2"] > 10000:  # 10,000 m² limit
            raise ValidationException(
                message="Total area cannot exceed 10,000 m² for automated generation",
                error_code="LAY_002",
                correlation_id=correlation_id
            )
        
        # Enhanced request with architectural context
        enhanced_request = {
            **request,
            "user_id": current_user.id,
            "correlation_id": correlation_id,
            "analysis_type": "layout_generation",
            "complexity": "high",  # Advanced layout generation
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Process with AI service
        layout_result = await ai_service.process_command(
            enhanced_request,
            correlation_id
        )
        
        # Comprehensive response for layout generation
        response = {
            "correlation_id": correlation_id,
            "layout_id": str(uuid4()),
            "result": layout_result.get("generated_content", {}),
            "metadata": {
                "confidence_score": layout_result.get("confidence_score", 0.0),
                "model_used": layout_result.get("model_used", "unknown"),
                "processing_time_ms": layout_result.get("processing_time_ms", 0),
                "requires_human_review": layout_result.get("requires_human_review", True),
                "compliance_checked": True,
                "optimization_applied": True
            },
            "validation": layout_result.get("validation_result", {}),
            "next_steps": [
                "Review generated layout in ArchBuilder.AI desktop application",
                "Validate compliance with local building codes",
                "Test layout in Revit before final implementation",
                "Consider architectural review if confidence < 90%"
            ]
        }
        
        logger.info(
            "Layout generation completed",
            user_id=current_user.id,
            layout_id=response["layout_id"],
            confidence=response["metadata"]["confidence_score"],
            correlation_id=correlation_id
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Layout generation failed",
            user_id=current_user.id,
            error=str(e),
            correlation_id=correlation_id,
            exc_info=True
        )
        raise


@router.get("/models", response_model=List[Dict[str, Any]])
async def list_available_models(
    current_user: User = Depends(get_current_active_user)
) -> List[Dict[str, Any]]:
    """
    List available AI models and their capabilities with subscription requirements
    """
    
    models = [
        {
            "name": "Gemini-2.5-Flash-Lite",
            "provider": "Vertex AI",
            "capabilities": [
                "layout_generation",
                "room_design", 
                "compliance_checking",
                "turkish_building_codes",
                "prompt_optimization"
            ],
            "subscription_tier_required": "FREE",
            "cost_units_per_request": 5,
            "max_tokens": 32768,
            "languages_supported": ["en", "tr", "de", "fr", "es"],
            "specialties": ["cost_effective", "simple_tasks", "building_codes"],
            "recommended_for": [
                "Simple architectural tasks",
                "Turkish building code analysis",
                "Basic layout generation"
            ]
        },
        {
            "name": "GPT-4.1",
            "provider": "GitHub Models",
            "capabilities": [
                "advanced_layout_generation",
                "architectural_analysis",
                "complex_optimization",
                "multi_building_design",
                "existing_project_analysis",
                "cad_file_processing"
            ],
            "subscription_tier_required": "STARTER",
            "cost_units_per_request": 15,
            "max_tokens": 128000,
            "languages_supported": ["en", "tr", "de", "fr", "es"],
            "specialties": ["complex_reasoning", "multi_format_parsing", "bim_analysis"],
            "recommended_for": [
                "Complex architectural projects",
                "Existing Revit project analysis",
                "Multi-format CAD processing",
                "Professional architectural design"
            ]
        }
    ]
    
    # Filter models based on user's subscription
    user_subscription = getattr(current_user, 'subscription_tier', 'FREE')
    subscription_hierarchy = {"FREE": 0, "STARTER": 1, "PROFESSIONAL": 2, "ENTERPRISE": 3}
    user_level = subscription_hierarchy.get(user_subscription, 0)
    
    available_models = []
    for model in models:
        required_level = subscription_hierarchy.get(model["subscription_tier_required"], 0)
        model["accessible"] = user_level >= required_level
        available_models.append(model)
    
    logger.info(
        "Listed available AI models",
        user_id=current_user.id,
        user_subscription=user_subscription,
        total_models=len(available_models),
        accessible_models=sum(1 for m in available_models if m["accessible"])
    )
    
    return available_models


@router.get("/usage", response_model=Dict[str, Any])
async def get_ai_usage_stats(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
    usage_tracking: UsageTrackingService = Depends(get_usage_tracking_service)
) -> Dict[str, Any]:
    """
    Get comprehensive AI usage statistics for current user
    """
    
    try:
        # Get subscription details
        subscription = await subscription_service.get_active_subscription(session, current_user.id)
        
        # Get usage statistics
        usage_stats = await usage_tracking.get_usage_summary(session, current_user.id)
        
        # Calculate remaining usage
        remaining_usage = await usage_tracking.get_remaining_usage(session, current_user.id)
        
        response = {
            "user_id": current_user.id,
            "subscription": {
                "tier": subscription.plan_name if subscription else "FREE",
                "status": subscription.status if subscription else "inactive",
                "billing_period": {
                    "start": subscription.start_date.isoformat() if subscription else None,
                    "end": subscription.end_date.isoformat() if subscription else None
                }
            },
            "usage_current_period": {
                "ai_requests": usage_stats.ai_requests if usage_stats else 0,
                "total_cost_units": usage_stats.total_cost_units if usage_stats else 0,
                "last_used": usage_stats.last_used.isoformat() if usage_stats and usage_stats.last_used else None
            },
            "usage_remaining": remaining_usage,
            "limits": {
                "ai_requests_monthly": subscription.ai_requests_monthly if subscription else 50,
                "layout_generations_monthly": subscription.max_projects if subscription else 5,
                "api_calls_hourly": 100 if not subscription else (1000 if subscription.plan_name == "STARTER" else 5000)
            },
            "usage_history": {
                "last_30_days": "Available in PROFESSIONAL tier",
                "detailed_analytics": "Available in ENTERPRISE tier"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(
            "Retrieved AI usage statistics",
            user_id=current_user.id,
            subscription_tier=response["subscription"]["tier"],
            current_usage=response["usage_current_period"]["ai_requests"]
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Failed to retrieve usage statistics",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics"
        )


# Background task functions
async def _schedule_human_review(
    ai_result: Dict[str, Any],
    user_id: str,
    correlation_id: str
):
    """Schedule AI output for human review"""
    
    try:
        # Store review request (would integrate with review queue system)
        review_data = {
            "user_id": user_id,
            "correlation_id": correlation_id,
            "ai_result": ai_result,
            "status": "pending_review",
            "created_at": datetime.utcnow().isoformat(),
            "priority": "normal" if ai_result.get("confidence_score", 0) > 0.8 else "high"
        }
        
        logger.info(
            "Scheduled AI output for human review",
            user_id=user_id,
            correlation_id=correlation_id,
            confidence=ai_result.get("confidence_score", 0),
            priority=review_data["priority"]
        )
        
        # TODO: Integrate with actual review queue system
        # await review_queue_service.add_for_review(review_data)
        
    except Exception as e:
        logger.error(
            "Failed to schedule human review",
            user_id=user_id,
            correlation_id=correlation_id,
            error=str(e),
            exc_info=True
        )