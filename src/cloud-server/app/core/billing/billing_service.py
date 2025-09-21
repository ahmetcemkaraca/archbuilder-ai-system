"""
Billing and subscription management for ArchBuilder.AI
Implements usage tracking, subscription tiers, and payment processing
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass

import stripe
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ...models.subscriptions import (
    SubscriptionTier, SubscriptionStatus, UsageType,
    SubscriptionDetails, UsageRecord, BillingCycle
)
from ...core.config import get_settings
from ...core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


@dataclass
class UsageLimits:
    """Usage limits for different subscription tiers"""
    ai_layouts_per_month: int
    ai_rooms_per_month: int
    revit_projects_per_month: int
    document_uploads_per_month: int
    cloud_storage_gb: int
    api_calls_per_hour: int
    concurrent_sessions: int


class SubscriptionTierLimits:
    """Predefined limits for each subscription tier"""
    
    LIMITS = {
        SubscriptionTier.FREE: UsageLimits(
            ai_layouts_per_month=3,
            ai_rooms_per_month=10,
            revit_projects_per_month=1,
            document_uploads_per_month=5,
            cloud_storage_gb=1,
            api_calls_per_hour=100,
            concurrent_sessions=1
        ),
        SubscriptionTier.STARTER: UsageLimits(
            ai_layouts_per_month=25,
            ai_rooms_per_month=100,
            revit_projects_per_month=10,
            document_uploads_per_month=50,
            cloud_storage_gb=10,
            api_calls_per_hour=1000,
            concurrent_sessions=2
        ),
        SubscriptionTier.PROFESSIONAL: UsageLimits(
            ai_layouts_per_month=100,
            ai_rooms_per_month=500,
            revit_projects_per_month=50,
            document_uploads_per_month=200,
            cloud_storage_gb=50,
            api_calls_per_hour=5000,
            concurrent_sessions=5
        ),
        SubscriptionTier.ENTERPRISE: UsageLimits(
            ai_layouts_per_month=1000,
            ai_rooms_per_month=5000,
            revit_projects_per_month=500,
            document_uploads_per_month=2000,
            cloud_storage_gb=500,
            api_calls_per_hour=50000,
            concurrent_sessions=20
        )
    }


class BillingService:
    """Core billing and subscription management service"""
    
    def __init__(self):
        self.stripe_client = stripe
    
    async def get_subscription_details(
        self, 
        user_id: str,
        db: Session
    ) -> SubscriptionDetails:
        """Get current subscription details for user"""
        
        # TODO: Implement database query for subscription
        # This is a placeholder implementation
        subscription = SubscriptionDetails(
            user_id=user_id,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.utcnow().replace(day=1),
            current_period_end=datetime.utcnow().replace(month=datetime.utcnow().month + 1, day=1),
            billing_cycle=BillingCycle.MONTHLY,
            stripe_subscription_id=None,
            limits=SubscriptionTierLimits.LIMITS[SubscriptionTier.FREE]
        )
        
        logger.debug(f"Retrieved subscription for user {user_id}: {subscription.tier}")
        return subscription
    
    async def check_usage_limit(
        self,
        user_id: str,
        usage_type: str,
        db: Session
    ) -> bool:
        """Check if user is within usage limits"""
        
        subscription = await self.get_subscription_details(user_id, db)
        current_usage = await self.get_current_usage(user_id, usage_type, db)
        
        # Map usage type to limit
        limit_mapping = {
            "ai_layout_generation": subscription.limits.ai_layouts_per_month,
            "ai_room_generation": subscription.limits.ai_rooms_per_month,
            "revit_project_creation": subscription.limits.revit_projects_per_month,
            "document_upload": subscription.limits.document_uploads_per_month,
            "api_call": subscription.limits.api_calls_per_hour
        }
        
        limit = limit_mapping.get(usage_type, 0)
        is_within_limit = current_usage < limit
        
        if not is_within_limit:
            logger.warning(f"Usage limit exceeded for user {user_id}, type {usage_type}: {current_usage}/{limit}")
        
        return is_within_limit
    
    async def track_usage(
        self,
        user_id: str,
        usage_type: str,
        cost_units: int,
        db: Session,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageRecord:
        """Track usage for billing and analytics"""
        
        usage_record = UsageRecord(
            user_id=user_id,
            usage_type=UsageType(usage_type),
            cost_units=cost_units,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # TODO: Save to database
        # db.add(usage_record)
        # db.commit()
        
        logger.info(f"Tracked usage for user {user_id}: {usage_type} = {cost_units} units")
        return usage_record
    
    async def get_current_usage(
        self,
        user_id: str,
        usage_type: str,
        db: Session,
        period_start: Optional[datetime] = None
    ) -> int:
        """Get current usage count for user in billing period"""
        
        if period_start is None:
            # Default to current month
            period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # TODO: Implement database query for usage count
        # This is a placeholder implementation
        usage_count = 0
        
        logger.debug(f"Current usage for user {user_id}, type {usage_type}: {usage_count}")
        return usage_count
    
    async def get_remaining_usage(
        self,
        user_id: str,
        db: Session
    ) -> Dict[str, int]:
        """Get remaining usage for all tracked metrics"""
        
        subscription = await self.get_subscription_details(user_id, db)
        limits = subscription.limits
        
        # Get current usage for all types
        ai_layouts_used = await self.get_current_usage(user_id, "ai_layout_generation", db)
        ai_rooms_used = await self.get_current_usage(user_id, "ai_room_generation", db)
        revit_projects_used = await self.get_current_usage(user_id, "revit_project_creation", db)
        document_uploads_used = await self.get_current_usage(user_id, "document_upload", db)
        
        remaining = {
            "ai_layouts": max(0, limits.ai_layouts_per_month - ai_layouts_used),
            "ai_rooms": max(0, limits.ai_rooms_per_month - ai_rooms_used),
            "revit_projects": max(0, limits.revit_projects_per_month - revit_projects_used),
            "document_uploads": max(0, limits.document_uploads_per_month - document_uploads_used),
        }
        
        logger.debug(f"Remaining usage for user {user_id}: {remaining}")
        return remaining
    
    async def upgrade_subscription(
        self,
        user_id: str,
        new_tier: SubscriptionTier,
        payment_method_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Upgrade user subscription with Stripe integration"""
        
        try:
            current_subscription = await self.get_subscription_details(user_id, db)
            
            # Calculate pricing
            tier_pricing = {
                SubscriptionTier.STARTER: {"monthly": 29.99, "yearly": 299.99},
                SubscriptionTier.PROFESSIONAL: {"monthly": 99.99, "yearly": 999.99},
                SubscriptionTier.ENTERPRISE: {"monthly": 299.99, "yearly": 2999.99}
            }
            
            if new_tier not in tier_pricing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid subscription tier"
                )
            
            # Create Stripe subscription
            price_amount = int(tier_pricing[new_tier]["monthly"] * 100)  # Convert to cents
            
            # Create or update Stripe customer
            customer = await self._get_or_create_stripe_customer(user_id, db)
            
            # Attach payment method
            self.stripe_client.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id
            )
            
            # Create subscription
            stripe_subscription = self.stripe_client.Subscription.create(
                customer=customer.id,
                items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'ArchBuilder.AI {new_tier.name}',
                        },
                        'unit_amount': price_amount,
                        'recurring': {
                            'interval': 'month',
                        },
                    },
                }],
                default_payment_method=payment_method_id,
                metadata={
                    'user_id': user_id,
                    'tier': new_tier.value
                }
            )
            
            # Update subscription in database
            # TODO: Implement database update
            
            logger.info(f"Upgraded subscription for user {user_id} to {new_tier}")
            
            return {
                "success": True,
                "new_tier": new_tier,
                "stripe_subscription_id": stripe_subscription.id,
                "next_billing_date": datetime.fromtimestamp(stripe_subscription.current_period_end)
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error during subscription upgrade: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment processing failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error during subscription upgrade: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upgrade subscription"
            )
    
    async def cancel_subscription(
        self,
        user_id: str,
        db: Session,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """Cancel user subscription"""
        
        try:
            subscription = await self.get_subscription_details(user_id, db)
            
            if subscription.stripe_subscription_id:
                # Cancel Stripe subscription
                canceled_subscription = self.stripe_client.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=not immediate
                )
                
                # Update database
                # TODO: Implement database update
                
                logger.info(f"Canceled subscription for user {user_id}, immediate: {immediate}")
                
                return {
                    "success": True,
                    "canceled_immediately": immediate,
                    "end_date": datetime.fromtimestamp(canceled_subscription.current_period_end)
                }
            else:
                # Handle free tier cancellation
                return {
                    "success": True,
                    "message": "Free tier subscription - no action needed"
                }
                
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error during subscription cancellation: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to cancel subscription: {str(e)}"
            )
    
    async def _get_or_create_stripe_customer(
        self,
        user_id: str,
        db: Session
    ) -> stripe.Customer:
        """Get existing Stripe customer or create new one"""
        
        # TODO: Get user details from database
        # user = await get_user_by_id(db, user_id)
        
        # For now, create a new customer
        customer = self.stripe_client.Customer.create(
            metadata={'user_id': user_id}
        )
        
        # TODO: Save customer ID to database
        
        return customer
    
    async def handle_stripe_webhook(
        self,
        event: Dict[str, Any],
        db: Session
    ) -> None:
        """Handle Stripe webhook events"""
        
        event_type = event['type']
        
        if event_type == 'customer.subscription.updated':
            await self._handle_subscription_updated(event['data']['object'], db)
        elif event_type == 'customer.subscription.deleted':
            await self._handle_subscription_deleted(event['data']['object'], db)
        elif event_type == 'invoice.payment_succeeded':
            await self._handle_payment_succeeded(event['data']['object'], db)
        elif event_type == 'invoice.payment_failed':
            await self._handle_payment_failed(event['data']['object'], db)
        
        logger.info(f"Processed Stripe webhook event: {event_type}")
    
    async def _handle_subscription_updated(
        self,
        subscription_data: Dict[str, Any],
        db: Session
    ) -> None:
        """Handle subscription update webhook"""
        user_id = subscription_data['metadata'].get('user_id')
        if user_id:
            # TODO: Update subscription in database
            logger.info(f"Updated subscription for user {user_id}")
    
    async def _handle_subscription_deleted(
        self,
        subscription_data: Dict[str, Any],
        db: Session
    ) -> None:
        """Handle subscription deletion webhook"""
        user_id = subscription_data['metadata'].get('user_id')
        if user_id:
            # TODO: Downgrade user to free tier
            logger.info(f"Downgraded user {user_id} to free tier")
    
    async def _handle_payment_succeeded(
        self,
        invoice_data: Dict[str, Any],
        db: Session
    ) -> None:
        """Handle successful payment webhook"""
        customer_id = invoice_data['customer']
        # TODO: Update payment status and extend subscription
        logger.info(f"Payment succeeded for customer {customer_id}")
    
    async def _handle_payment_failed(
        self,
        invoice_data: Dict[str, Any],
        db: Session
    ) -> None:
        """Handle failed payment webhook"""
        customer_id = invoice_data['customer']
        # TODO: Handle payment failure, send notifications
        logger.warning(f"Payment failed for customer {customer_id}")


# Global billing service instance
billing_service = BillingService()


def track_usage(operation_type: str, cost_units: int = 1):
    """Decorator to track usage for billing"""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user from dependencies
            current_user = None
            for arg in args:
                if hasattr(arg, 'id'):  # Assume this is the user object
                    current_user = arg
                    break
            
            if not current_user:
                # Look in kwargs
                current_user = kwargs.get('current_user')
            
            if current_user:
                db = kwargs.get('db')
                if db:
                    await billing_service.track_usage(
                        current_user.id,
                        operation_type,
                        cost_units,
                        db
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator