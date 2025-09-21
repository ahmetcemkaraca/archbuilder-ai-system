"""
Subscription and billing API endpoints for ArchBuilder.AI
Implements subscription management, usage tracking, and payment processing
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import stripe

from ..core.auth.authentication import get_current_user
from ..core.billing.billing_service import billing_service
from ..core.database import get_db
from ..core.config import get_settings
from ..models.subscriptions import (
    SubscriptionResponse,
    SubscriptionUpgradeRequest,
    UpgradeResponse,
    UsageResponse,
    BillingHistoryResponse,
    SubscriptionTier
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
settings = get_settings()


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SubscriptionResponse:
    """
    Get current user subscription details and usage information
    """
    
    try:
        subscription = await billing_service.get_subscription_details(current_user.id, db)
        usage = await billing_service.get_remaining_usage(current_user.id, db)
        
        return SubscriptionResponse(
            subscription=subscription,
            usage=usage,
            limits=subscription.limits
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve subscription: {str(e)}"
        )


@router.post("/upgrade", response_model=UpgradeResponse)
async def upgrade_subscription(
    upgrade_request: SubscriptionUpgradeRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UpgradeResponse:
    """
    Upgrade user subscription with payment processing
    
    Supports upgrading to:
    - STARTER: $29.99/month
    - PROFESSIONAL: $99.99/month  
    - ENTERPRISE: $299.99/month
    """
    
    try:
        # Validate subscription tier
        valid_tiers = [SubscriptionTier.STARTER, SubscriptionTier.PROFESSIONAL, SubscriptionTier.ENTERPRISE]
        if upgrade_request.new_tier not in valid_tiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subscription tier"
            )
        
        # Process upgrade with billing service
        result = await billing_service.upgrade_subscription(
            user_id=current_user.id,
            new_tier=upgrade_request.new_tier,
            payment_method_id=upgrade_request.payment_method_id,
            db=db
        )
        
        return UpgradeResponse(
            success=result["success"],
            new_tier=result["new_tier"],
            next_billing_date=result["next_billing_date"],
            stripe_subscription_id=result.get("stripe_subscription_id"),
            amount_charged=upgrade_request.amount_expected
        )
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Subscription upgrade failed: {str(e)}"
        )


@router.post("/cancel")
async def cancel_subscription(
    immediate: bool = False,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Cancel user subscription
    
    Parameters:
    - immediate: If True, cancel immediately. If False, cancel at period end.
    """
    
    try:
        result = await billing_service.cancel_subscription(
            user_id=current_user.id,
            db=db,
            immediate=immediate
        )
        
        return {
            "message": "Subscription canceled successfully",
            "canceled_immediately": result["canceled_immediately"],
            "end_date": result.get("end_date"),
            "access_until": result.get("end_date") if not immediate else datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )


@router.get("/usage", response_model=UsageResponse)
async def get_usage_details(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UsageResponse:
    """
    Get detailed usage information for current billing period
    """
    
    try:
        subscription = await billing_service.get_subscription_details(current_user.id, db)
        remaining_usage = await billing_service.get_remaining_usage(current_user.id, db)
        
        # Calculate used amounts
        limits = subscription.limits
        used_usage = {
            "ai_layouts": limits.ai_layouts_per_month - remaining_usage.get("ai_layouts", 0),
            "ai_rooms": limits.ai_rooms_per_month - remaining_usage.get("ai_rooms", 0),
            "revit_projects": limits.revit_projects_per_month - remaining_usage.get("revit_projects", 0),
            "document_uploads": limits.document_uploads_per_month - remaining_usage.get("document_uploads", 0)
        }
        
        return UsageResponse(
            billing_period_start=subscription.current_period_start,
            billing_period_end=subscription.current_period_end,
            subscription_tier=subscription.tier,
            limits={
                "ai_layouts_per_month": limits.ai_layouts_per_month,
                "ai_rooms_per_month": limits.ai_rooms_per_month,
                "revit_projects_per_month": limits.revit_projects_per_month,
                "document_uploads_per_month": limits.document_uploads_per_month,
                "cloud_storage_gb": limits.cloud_storage_gb,
                "api_calls_per_hour": limits.api_calls_per_hour
            },
            used=used_usage,
            remaining=remaining_usage
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve usage details: {str(e)}"
        )


@router.get("/billing-history", response_model=List[BillingHistoryResponse])
async def get_billing_history(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 12
) -> List[BillingHistoryResponse]:
    """
    Get billing history for the user
    """
    
    try:
        # TODO: Implement billing history retrieval
        # This is a placeholder implementation
        
        billing_history = [
            BillingHistoryResponse(
                invoice_id="inv_example123",
                amount=29.99,
                currency="USD",
                status="paid",
                billing_date=datetime.utcnow(),
                period_start=datetime.utcnow(),
                period_end=datetime.utcnow(),
                subscription_tier=SubscriptionTier.STARTER,
                download_url="https://example.com/invoice.pdf"
            )
        ]
        
        return billing_history
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve billing history: {str(e)}"
        )


@router.get("/plans", response_model=List[dict])
async def get_subscription_plans() -> List[dict]:
    """
    Get available subscription plans and pricing
    """
    
    plans = [
        {
            "tier": "FREE",
            "name": "Free",
            "price_monthly": 0,
            "price_yearly": 0,
            "features": {
                "ai_layouts_per_month": 3,
                "ai_rooms_per_month": 10,
                "revit_projects_per_month": 1,
                "document_uploads_per_month": 5,
                "cloud_storage_gb": 1,
                "api_calls_per_hour": 100,
                "concurrent_sessions": 1,
                "support": "Community"
            },
            "popular": False
        },
        {
            "tier": "STARTER",
            "name": "Starter",
            "price_monthly": 29.99,
            "price_yearly": 299.99,
            "features": {
                "ai_layouts_per_month": 25,
                "ai_rooms_per_month": 100,
                "revit_projects_per_month": 10,
                "document_uploads_per_month": 50,
                "cloud_storage_gb": 10,
                "api_calls_per_hour": 1000,
                "concurrent_sessions": 2,
                "support": "Email"
            },
            "popular": True
        },
        {
            "tier": "PROFESSIONAL",
            "name": "Professional",
            "price_monthly": 99.99,
            "price_yearly": 999.99,
            "features": {
                "ai_layouts_per_month": 100,
                "ai_rooms_per_month": 500,
                "revit_projects_per_month": 50,
                "document_uploads_per_month": 200,
                "cloud_storage_gb": 50,
                "api_calls_per_hour": 5000,
                "concurrent_sessions": 5,
                "support": "Priority Support"
            },
            "popular": False
        },
        {
            "tier": "ENTERPRISE",
            "name": "Enterprise",
            "price_monthly": 299.99,
            "price_yearly": 2999.99,
            "features": {
                "ai_layouts_per_month": 1000,
                "ai_rooms_per_month": 5000,
                "revit_projects_per_month": 500,
                "document_uploads_per_month": 2000,
                "cloud_storage_gb": 500,
                "api_calls_per_hour": 50000,
                "concurrent_sessions": 20,
                "support": "Dedicated Account Manager"
            },
            "popular": False
        }
    ]
    
    return plans


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhook events for subscription management
    """
    
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    try:
        await billing_service.handle_stripe_webhook(event, db)
        return {"status": "success"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.get("/payment-methods")
async def get_payment_methods(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get user's saved payment methods
    """
    
    try:
        # TODO: Implement payment method retrieval
        # This is a placeholder implementation
        
        return {
            "payment_methods": [],
            "default_payment_method": None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payment methods: {str(e)}"
        )


@router.post("/payment-methods")
async def add_payment_method(
    payment_method_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Add new payment method for user
    """
    
    try:
        # TODO: Implement payment method addition
        # This is a placeholder implementation
        
        return {
            "message": "Payment method added successfully",
            "payment_method_id": payment_method_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add payment method: {str(e)}"
        )