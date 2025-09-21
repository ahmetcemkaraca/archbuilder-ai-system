"""
ArchBuilder.AI Subscription Management Service

Handles subscription lifecycle, plan management, and billing operations.
Integrates with Stripe for payment processing and subscription management.
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import structlog
import stripe
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

logger = structlog.get_logger(__name__)


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    PAUSED = "paused"


class SubscriptionTier(str, Enum):
    """Subscription tier enumeration."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class PricingPlan:
    """Pricing plan configuration."""
    tier: SubscriptionTier
    name: str
    monthly_price: float
    yearly_price: float
    stripe_price_id_monthly: str
    stripe_price_id_yearly: str
    features: List[str]
    limits: Dict[str, int]
    trial_days: int = 14


@dataclass 
class UsageMetrics:
    """User usage metrics."""
    ai_requests: int = 0
    documents_processed: int = 0
    projects_created: int = 0
    storage_used_mb: float = 0.0
    api_calls: int = 0
    render_hours: float = 0.0
    collaboration_seats: int = 0


@dataclass
class BillingInfo:
    """Billing information."""
    user_id: str
    subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    current_tier: SubscriptionTier = SubscriptionTier.FREE
    status: SubscriptionStatus = SubscriptionStatus.INACTIVE
    billing_cycle: str = "monthly"  # monthly or yearly
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    usage_metrics: UsageMetrics = field(default_factory=UsageMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SubscriptionService:
    """Subscription management service with Stripe integration."""
    
    def __init__(self, stripe_secret_key: str, webhook_secret: str):
        """Initialize subscription service."""
        stripe.api_key = stripe_secret_key
        self.webhook_secret = webhook_secret
        self.logger = logger.bind(service="subscription")
        
        # Define pricing plans
        self.pricing_plans = {
            SubscriptionTier.FREE: PricingPlan(
                tier=SubscriptionTier.FREE,
                name="Free",
                monthly_price=0.0,
                yearly_price=0.0,
                stripe_price_id_monthly="",
                stripe_price_id_yearly="",
                features=[
                    "1 project per month",
                    "Basic AI assistance",
                    "Standard templates",
                    "Community support"
                ],
                limits={
                    "projects_per_month": 1,
                    "ai_requests_per_month": 10,
                    "documents_per_month": 5,
                    "storage_mb": 100,
                    "collaboration_seats": 1
                },
                trial_days=0
            ),
            SubscriptionTier.STARTER: PricingPlan(
                tier=SubscriptionTier.STARTER,
                name="Starter",
                monthly_price=29.99,
                yearly_price=299.99,
                stripe_price_id_monthly="price_starter_monthly",
                stripe_price_id_yearly="price_starter_yearly",
                features=[
                    "10 projects per month",
                    "Advanced AI assistance",
                    "Premium templates",
                    "Email support",
                    "Basic analytics"
                ],
                limits={
                    "projects_per_month": 10,
                    "ai_requests_per_month": 500,
                    "documents_per_month": 50,
                    "storage_mb": 1000,
                    "collaboration_seats": 3
                },
                trial_days=14
            ),
            SubscriptionTier.PROFESSIONAL: PricingPlan(
                tier=SubscriptionTier.PROFESSIONAL,
                name="Professional",
                monthly_price=99.99,
                yearly_price=999.99,
                stripe_price_id_monthly="price_pro_monthly",
                stripe_price_id_yearly="price_pro_yearly",
                features=[
                    "Unlimited projects",
                    "Expert AI assistance",
                    "Custom templates",
                    "Priority support",
                    "Advanced analytics",
                    "Team collaboration",
                    "API access"
                ],
                limits={
                    "projects_per_month": -1,  # Unlimited
                    "ai_requests_per_month": 5000,
                    "documents_per_month": 500,
                    "storage_mb": 10000,
                    "collaboration_seats": 10
                },
                trial_days=14
            ),
            SubscriptionTier.ENTERPRISE: PricingPlan(
                tier=SubscriptionTier.ENTERPRISE,
                name="Enterprise",
                monthly_price=499.99,
                yearly_price=4999.99,
                stripe_price_id_monthly="price_enterprise_monthly",
                stripe_price_id_yearly="price_enterprise_yearly",
                features=[
                    "Unlimited everything",
                    "Dedicated AI models",
                    "Custom integrations",
                    "24/7 phone support",
                    "Custom analytics",
                    "Advanced team management",
                    "SLA guarantees",
                    "On-premise deployment"
                ],
                limits={
                    "projects_per_month": -1,
                    "ai_requests_per_month": -1,
                    "documents_per_month": -1,
                    "storage_mb": -1,
                    "collaboration_seats": -1
                },
                trial_days=30
            )
        }
        
        self.logger.info("Subscription service initialized", plans_count=len(self.pricing_plans))

    async def create_customer(self, user_id: str, email: str, name: str, metadata: Optional[Dict[str, str]] = None) -> str:
        """Create a new Stripe customer."""
        try:
            customer_metadata = {"user_id": user_id}
            if metadata:
                customer_metadata.update(metadata)
                
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=customer_metadata
            )
            
            self.logger.info("Stripe customer created", 
                           user_id=user_id, 
                           customer_id=customer.id)
            
            return customer.id
            
        except stripe.error.StripeError as e:
            self.logger.error("Failed to create Stripe customer", 
                            user_id=user_id, 
                            error=str(e))
            raise Exception(f"Failed to create customer: {str(e)}")

    async def start_subscription(self, user_id: str, customer_id: str, tier: SubscriptionTier, 
                               billing_cycle: str = "monthly") -> Dict[str, Any]:
        """Start a new subscription."""
        try:
            plan = self.pricing_plans[tier]
            
            # Get appropriate price ID
            price_id = (plan.stripe_price_id_monthly 
                       if billing_cycle == "monthly" 
                       else plan.stripe_price_id_yearly)
            
            if not price_id:
                raise ValueError(f"No price ID configured for {tier} {billing_cycle}")
            
            # Create subscription with trial if applicable
            subscription_params = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "metadata": {
                    "user_id": user_id,
                    "tier": tier.value,
                    "billing_cycle": billing_cycle
                },
                "expand": ["latest_invoice.payment_intent"]
            }
            
            # Add trial period if applicable
            if plan.trial_days > 0:
                trial_end = datetime.utcnow() + timedelta(days=plan.trial_days)
                subscription_params["trial_end"] = int(trial_end.timestamp())
            
            subscription = stripe.Subscription.create(**subscription_params)
            
            self.logger.info("Subscription created", 
                           user_id=user_id,
                           subscription_id=subscription.id,
                           tier=tier.value,
                           billing_cycle=billing_cycle)
            
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice else None,
                "trial_end": subscription.trial_end
            }
            
        except stripe.error.StripeError as e:
            self.logger.error("Failed to create subscription", 
                            user_id=user_id, 
                            tier=tier.value,
                            error=str(e))
            raise Exception(f"Failed to create subscription: {str(e)}")

    async def change_subscription(self, subscription_id: str, new_tier: SubscriptionTier, 
                                billing_cycle: str = "monthly") -> Dict[str, Any]:
        """Change subscription tier."""
        try:
            new_plan = self.pricing_plans[new_tier]
            price_id = (new_plan.stripe_price_id_monthly 
                       if billing_cycle == "monthly" 
                       else new_plan.stripe_price_id_yearly)
            
            # Get current subscription
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Update subscription
            updated_subscription = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    "id": subscription["items"]["data"][0]["id"],
                    "price": price_id
                }],
                metadata={
                    **subscription.metadata,
                    "tier": new_tier.value,
                    "billing_cycle": billing_cycle
                },
                proration_behavior="create_prorations"
            )
            
            self.logger.info("Subscription updated", 
                           subscription_id=subscription_id,
                           new_tier=new_tier.value,
                           billing_cycle=billing_cycle)
            
            return {
                "subscription_id": updated_subscription.id,
                "status": updated_subscription.status,
                "tier": new_tier.value,
                "billing_cycle": billing_cycle
            }
            
        except stripe.error.StripeError as e:
            self.logger.error("Failed to update subscription", 
                            subscription_id=subscription_id,
                            new_tier=new_tier.value,
                            error=str(e))
            raise Exception(f"Failed to update subscription: {str(e)}")

    async def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        """Cancel subscription."""
        try:
            if at_period_end:
                # Cancel at the end of the current billing period
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                # Cancel immediately
                subscription = stripe.Subscription.cancel(subscription_id)
            
            self.logger.info("Subscription canceled", 
                           subscription_id=subscription_id,
                           immediate=not at_period_end)
            
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "canceled_at": subscription.canceled_at,
                "cancel_at_period_end": subscription.cancel_at_period_end
            }
            
        except stripe.error.StripeError as e:
            self.logger.error("Failed to cancel subscription", 
                            subscription_id=subscription_id,
                            error=str(e))
            raise Exception(f"Failed to cancel subscription: {str(e)}")

    async def get_billing_info(self, user_id: str, db: AsyncSession) -> Optional[BillingInfo]:
        """Get user billing information."""
        try:
            # This would typically query your database
            # For now, return a mock response
            return BillingInfo(
                user_id=user_id,
                current_tier=SubscriptionTier.FREE,
                status=SubscriptionStatus.ACTIVE
            )
            
        except Exception as e:
            self.logger.error("Failed to get billing info", 
                            user_id=user_id,
                            error=str(e))
            return None

    async def track_usage(self, user_id: str, usage_type: str, amount: int = 1) -> bool:
        """Track user usage metrics."""
        try:
            # This would typically update usage in your database
            self.logger.info("Usage tracked", 
                           user_id=user_id,
                           usage_type=usage_type,
                           amount=amount)
            return True
            
        except Exception as e:
            self.logger.error("Failed to track usage", 
                            user_id=user_id,
                            usage_type=usage_type,
                            error=str(e))
            return False

    async def check_usage_limits(self, user_id: str, usage_type: str) -> Dict[str, Any]:
        """Check if user has exceeded usage limits."""
        try:
            # Get user's current tier and usage
            billing_info = await self.get_billing_info(user_id, None)
            if not billing_info:
                return {"allowed": False, "reason": "No billing info found"}
            
            plan = self.pricing_plans[billing_info.current_tier]
            
            # Check specific usage type
            if usage_type in plan.limits:
                limit = plan.limits[usage_type]
                if limit == -1:  # Unlimited
                    return {"allowed": True, "limit": "unlimited"}
                
                # Get current usage (mock for now)
                current_usage = getattr(billing_info.usage_metrics, usage_type.replace("_per_month", ""), 0)
                
                if current_usage >= limit:
                    return {
                        "allowed": False,
                        "reason": f"Monthly limit of {limit} {usage_type} exceeded",
                        "current": current_usage,
                        "limit": limit
                    }
                
                return {
                    "allowed": True,
                    "current": current_usage,
                    "limit": limit,
                    "remaining": limit - current_usage
                }
            
            return {"allowed": True, "reason": "No limit defined"}
            
        except Exception as e:
            self.logger.error("Failed to check usage limits", 
                            user_id=user_id,
                            usage_type=usage_type,
                            error=str(e))
            return {"allowed": False, "reason": "Error checking limits"}

    def get_pricing_plans(self) -> Dict[SubscriptionTier, PricingPlan]:
        """Get all pricing plans."""
        return self.pricing_plans

    async def process_webhook(self, payload: str, sig_header: str) -> Dict[str, Any]:
        """Process Stripe webhook."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            
            self.logger.info("Stripe webhook received", 
                           event_type=event["type"],
                           event_id=event["id"])
            
            # Handle different event types
            if event["type"] == "customer.subscription.created":
                await self._handle_subscription_created(event["data"]["object"])
            elif event["type"] == "customer.subscription.updated":
                await self._handle_subscription_updated(event["data"]["object"])
            elif event["type"] == "customer.subscription.deleted":
                await self._handle_subscription_deleted(event["data"]["object"])
            elif event["type"] == "invoice.payment_succeeded":
                await self._handle_payment_succeeded(event["data"]["object"])
            elif event["type"] == "invoice.payment_failed":
                await self._handle_payment_failed(event["data"]["object"])
            
            return {"status": "success", "event_type": event["type"]}
            
        except ValueError as e:
            self.logger.error("Invalid webhook payload", error=str(e))
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            self.logger.error("Invalid webhook signature", error=str(e))
            raise Exception("Invalid signature")
        except Exception as e:
            self.logger.error("Webhook processing failed", error=str(e))
            raise Exception(f"Webhook processing failed: {str(e)}")

    async def _handle_subscription_created(self, subscription: Dict[str, Any]):
        """Handle subscription created webhook."""
        user_id = subscription["metadata"].get("user_id")
        if user_id:
            self.logger.info("Subscription created webhook processed", 
                           user_id=user_id,
                           subscription_id=subscription["id"])

    async def _handle_subscription_updated(self, subscription: Dict[str, Any]):
        """Handle subscription updated webhook."""
        user_id = subscription["metadata"].get("user_id")
        if user_id:
            self.logger.info("Subscription updated webhook processed", 
                           user_id=user_id,
                           subscription_id=subscription["id"])

    async def _handle_subscription_deleted(self, subscription: Dict[str, Any]):
        """Handle subscription deleted webhook."""
        user_id = subscription["metadata"].get("user_id")
        if user_id:
            self.logger.info("Subscription deleted webhook processed", 
                           user_id=user_id,
                           subscription_id=subscription["id"])

    async def _handle_payment_succeeded(self, invoice: Dict[str, Any]):
        """Handle payment succeeded webhook."""
        customer_id = invoice["customer"]
        self.logger.info("Payment succeeded webhook processed", 
                       customer_id=customer_id,
                       invoice_id=invoice["id"])

    async def _handle_payment_failed(self, invoice: Dict[str, Any]):
        """Handle payment failed webhook.""" 
        customer_id = invoice["customer"]
        self.logger.info("Payment failed webhook processed", 
                       customer_id=customer_id,
                       invoice_id=invoice["id"])