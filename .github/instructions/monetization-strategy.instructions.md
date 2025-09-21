---
applyTo: "src/cloud-server/**/*.py,src/revit-plugin/**/*.cs,**/*.md"
description: Monetization Strategy — SaaS business model, subscription management, usage tracking, billing integration.
---
As Monetization Strategy Developer:
- Design and implement subscription-based SaaS model with multiple pricing tiers
- Integrate usage tracking and billing systems for AI operations
- Implement Stripe integration for subscription management and payments
- Create analytics dashboard for revenue and usage monitoring
- Ensure transparent pricing and usage limits for different subscription tiers
- Design freemium model to attract new users and convert to paid plans

## Subscription Tiers and Pricing Model

### Tier Definitions
```python
class SubscriptionTier(Enum):
    FREE = "free"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"

SUBSCRIPTION_LIMITS = {
    SubscriptionTier.FREE: {
        "ai_layouts_per_month": 5,
        "building_scans_per_month": 2,
        "max_project_size_sqm": 200,
        "api_calls_per_hour": 10,
        "support_level": "community",
        "features": ["basic_layout", "simple_validation"]
    },
    SubscriptionTier.PROFESSIONAL: {
        "ai_layouts_per_month": 100,
        "building_scans_per_month": 20,
        "max_project_size_sqm": 2000,
        "api_calls_per_hour": 100,
        "support_level": "email",
        "features": ["advanced_layout", "code_compliance", "3d_visualization", "export_formats"]
    },
    SubscriptionTier.ENTERPRISE: {
        "ai_layouts_per_month": -1,  # Unlimited
        "building_scans_per_month": -1,  # Unlimited
        "max_project_size_sqm": -1,  # Unlimited
        "api_calls_per_hour": 1000,
        "support_level": "priority",
        "features": ["all_features", "custom_models", "white_label", "sso", "dedicated_support"]
    }
}
```

### Pricing Structure
```python
SUBSCRIPTION_PRICING = {
    SubscriptionTier.FREE: {
        "monthly_price_usd": 0,
        "yearly_price_usd": 0,
        "setup_fee_usd": 0
    },
    SubscriptionTier.PROFESSIONAL: {
        "monthly_price_usd": 49,
        "yearly_price_usd": 490,  # 2 months free
        "setup_fee_usd": 0
    },
    SubscriptionTier.ENTERPRISE: {
        "monthly_price_usd": 199,
        "yearly_price_usd": 1990,  # 2 months free
        "setup_fee_usd": 500
    },
    SubscriptionTier.CUSTOM: {
        "monthly_price_usd": "negotiated",
        "yearly_price_usd": "negotiated",
        "setup_fee_usd": "negotiated"
    }
}
```

## Usage Tracking Implementation

### Usage Metrics Collection
```python
from typing import Dict, Any
import asyncio
from datetime import datetime, timedelta

class UsageTracker:
    """Track all billable operations with real-time monitoring"""
    
    def __init__(self, redis_client, database):
        self.redis = redis_client
        self.db = database
    
    async def track_operation(
        self,
        user_id: str,
        operation_type: str,
        cost_units: int = 1,
        metadata: Dict[str, Any] = None
    ):
        """Track a billable operation in real-time"""
        
        timestamp = datetime.utcnow()
        operation_key = f"usage:{user_id}:{operation_type}:{timestamp.strftime('%Y-%m')}"
        
        # Increment monthly usage in Redis for fast access
        await self.redis.hincrby(operation_key, "count", cost_units)
        await self.redis.expire(operation_key, 86400 * 31)  # 31 days expiry
        
        # Store detailed usage record in database
        usage_record = UsageRecord(
            user_id=user_id,
            operation_type=operation_type,
            cost_units=cost_units,
            timestamp=timestamp,
            metadata=metadata or {}
        )
        await self.db.save(usage_record)
        
        # Check if user is approaching limits
        await self._check_usage_limits(user_id, operation_type)
    
    async def get_monthly_usage(self, user_id: str, operation_type: str = None) -> Dict[str, int]:
        """Get current month usage for a user"""
        
        current_month = datetime.utcnow().strftime('%Y-%m')
        
        if operation_type:
            key = f"usage:{user_id}:{operation_type}:{current_month}"
            usage = await self.redis.hget(key, "count")
            return {operation_type: int(usage or 0)}
        else:
            # Get all operation types for user
            pattern = f"usage:{user_id}:*:{current_month}"
            keys = await self.redis.keys(pattern)
            
            usage_dict = {}
            for key in keys:
                op_type = key.split(':')[2]  # Extract operation type
                count = await self.redis.hget(key, "count")
                usage_dict[op_type] = int(count or 0)
            
            return usage_dict
    
    async def check_usage_limit(self, user_id: str, operation_type: str) -> bool:
        """Check if user can perform operation within their subscription limits"""
        
        # Get user's subscription tier
        subscription = await self.db.get_user_subscription(user_id)
        if not subscription or subscription.status != "active":
            return False
        
        tier_limits = SUBSCRIPTION_LIMITS.get(subscription.tier, {})
        operation_limit = tier_limits.get(f"{operation_type}_per_month", 0)
        
        # Unlimited for enterprise
        if operation_limit == -1:
            return True
        
        # Check current usage
        current_usage = await self.get_monthly_usage(user_id, operation_type)
        used_count = current_usage.get(operation_type, 0)
        
        return used_count < operation_limit
    
    async def _check_usage_limits(self, user_id: str, operation_type: str):
        """Check if user is approaching limits and send notifications"""
        
        subscription = await self.db.get_user_subscription(user_id)
        tier_limits = SUBSCRIPTION_LIMITS.get(subscription.tier, {})
        operation_limit = tier_limits.get(f"{operation_type}_per_month", 0)
        
        if operation_limit == -1:  # Unlimited
            return
        
        current_usage = await self.get_monthly_usage(user_id, operation_type)
        used_count = current_usage.get(operation_type, 0)
        
        # Notification thresholds
        if used_count >= operation_limit * 0.8:  # 80% usage
            await self._send_usage_warning(user_id, operation_type, used_count, operation_limit)
        
        if used_count >= operation_limit:  # 100% usage
            await self._send_limit_reached(user_id, operation_type)

class BillingService:
    """Handle subscription management and billing integration"""
    
    def __init__(self, stripe_client, database, usage_tracker):
        self.stripe = stripe_client
        self.db = database
        self.usage_tracker = usage_tracker
    
    async def create_subscription(
        self,
        user_id: str,
        tier: SubscriptionTier,
        payment_method_id: str,
        billing_cycle: str = "monthly"
    ) -> SubscriptionResult:
        """Create new subscription with Stripe integration"""
        
        try:
            user = await self.db.get_user(user_id)
            pricing = SUBSCRIPTION_PRICING[tier]
            
            # Create Stripe customer if not exists
            if not user.stripe_customer_id:
                stripe_customer = await self.stripe.Customer.create(
                    email=user.email,
                    name=user.full_name,
                    payment_method=payment_method_id,
                    invoice_settings={"default_payment_method": payment_method_id}
                )
                user.stripe_customer_id = stripe_customer.id
                await self.db.save(user)
            
            # Create subscription in Stripe
            price_key = f"{billing_cycle}_price_usd"
            price_amount = pricing[price_key]
            
            if price_amount == 0:  # Free tier
                subscription_record = UserSubscription(
                    user_id=user_id,
                    tier=tier,
                    status="active",
                    billing_cycle=billing_cycle,
                    next_billing_date=None,
                    stripe_subscription_id=None
                )
            else:
                stripe_subscription = await self.stripe.Subscription.create(
                    customer=user.stripe_customer_id,
                    items=[{"price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"RevitAutoPlan {tier.value.title()}"},
                        "unit_amount": price_amount * 100,  # Stripe uses cents
                        "recurring": {"interval": "month" if billing_cycle == "monthly" else "year"}
                    }}],
                    payment_settings={"payment_method_types": ["card"]},
                    expand=["latest_invoice.payment_intent"]
                )
                
                subscription_record = UserSubscription(
                    user_id=user_id,
                    tier=tier,
                    status="active",
                    billing_cycle=billing_cycle,
                    next_billing_date=stripe_subscription.current_period_end,
                    stripe_subscription_id=stripe_subscription.id
                )
            
            await self.db.save(subscription_record)
            
            return SubscriptionResult(
                success=True,
                subscription=subscription_record,
                message="Subscription created successfully"
            )
            
        except Exception as e:
            return SubscriptionResult(
                success=False,
                subscription=None,
                message=f"Failed to create subscription: {str(e)}"
            )
    
    async def upgrade_subscription(
        self,
        user_id: str,
        new_tier: SubscriptionTier,
        payment_method_id: str = None
    ) -> UpgradeResult:
        """Upgrade user subscription to higher tier"""
        
        current_subscription = await self.db.get_user_subscription(user_id)
        if not current_subscription:
            return UpgradeResult(success=False, message="No active subscription found")
        
        # Update Stripe subscription if paid tier
        pricing = SUBSCRIPTION_PRICING[new_tier]
        if pricing["monthly_price_usd"] > 0 and current_subscription.stripe_subscription_id:
            await self.stripe.Subscription.modify(
                current_subscription.stripe_subscription_id,
                items=[{"price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"RevitAutoPlan {new_tier.value.title()}"},
                    "unit_amount": pricing["monthly_price_usd"] * 100,
                    "recurring": {"interval": "month"}
                }}],
                proration_behavior="always_invoice"
            )
        
        # Update local subscription record
        current_subscription.tier = new_tier
        current_subscription.updated_at = datetime.utcnow()
        await self.db.save(current_subscription)
        
        return UpgradeResult(
            success=True,
            new_tier=new_tier,
            message="Subscription upgraded successfully"
        )
    
    async def handle_webhook(self, event_type: str, event_data: dict):
        """Handle Stripe webhook events"""
        
        if event_type == "customer.subscription.deleted":
            # Handle subscription cancellation
            subscription_id = event_data["object"]["id"]
            await self._deactivate_subscription(subscription_id)
        
        elif event_type == "invoice.payment_failed":
            # Handle failed payments
            customer_id = event_data["object"]["customer"]
            await self._handle_payment_failure(customer_id)
        
        elif event_type == "invoice.payment_succeeded":
            # Handle successful payments
            subscription_id = event_data["object"]["subscription"]
            await self._update_subscription_status(subscription_id, "active")

# Usage tracking decorator for API endpoints
def track_billable_operation(operation_type: str, cost_units: int = 1):
    """Decorator to automatically track billable operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if current_user:
                # Check limits before operation
                can_proceed = await usage_tracker.check_usage_limit(
                    current_user.id, operation_type
                )
                if not can_proceed:
                    raise HTTPException(
                        status_code=402,
                        detail="Usage limit exceeded. Please upgrade your subscription."
                    )
                
                # Execute operation
                result = await func(*args, **kwargs)
                
                # Track usage after successful operation
                await usage_tracker.track_operation(
                    current_user.id,
                    operation_type,
                    cost_units,
                    metadata={"endpoint": func.__name__}
                )
                
                return result
            else:
                return await func(*args, **kwargs)
        return wrapper
    return decorator
```

## Analytics and Reporting

### Revenue Analytics
```python
class RevenueAnalytics:
    """Analytics for revenue tracking and business intelligence"""
    
    async def get_monthly_revenue_report(self, year: int, month: int) -> RevenueReport:
        """Generate comprehensive monthly revenue report"""
        
        # Get all subscriptions for the month
        subscriptions = await self.db.get_subscriptions_by_month(year, month)
        
        revenue_by_tier = {}
        total_revenue = 0
        active_subscribers = 0
        
        for subscription in subscriptions:
            tier = subscription.tier
            if tier not in revenue_by_tier:
                revenue_by_tier[tier] = {"count": 0, "revenue": 0}
            
            pricing = SUBSCRIPTION_PRICING[tier]
            monthly_revenue = pricing["monthly_price_usd"]
            
            revenue_by_tier[tier]["count"] += 1
            revenue_by_tier[tier]["revenue"] += monthly_revenue
            total_revenue += monthly_revenue
            active_subscribers += 1
        
        # Calculate usage-based metrics
        usage_stats = await self.usage_tracker.get_period_usage_stats(year, month)
        
        return RevenueReport(
            period=f"{year}-{month:02d}",
            total_revenue=total_revenue,
            active_subscribers=active_subscribers,
            revenue_by_tier=revenue_by_tier,
            usage_stats=usage_stats,
            growth_rate=await self._calculate_growth_rate(year, month)
        )
    
    async def get_user_lifetime_value(self, user_id: str) -> UserLifetimeValue:
        """Calculate lifetime value for a specific user"""
        
        subscriptions = await self.db.get_user_subscription_history(user_id)
        usage_history = await self.usage_tracker.get_user_usage_history(user_id)
        
        total_paid = sum(sub.amount_paid for sub in subscriptions)
        months_subscribed = len(subscriptions)
        avg_usage = usage_history.get_average_monthly_usage()
        
        return UserLifetimeValue(
            user_id=user_id,
            total_revenue=total_paid,
            months_subscribed=months_subscribed,
            average_monthly_usage=avg_usage,
            predicted_lifetime_value=self._predict_ltv(total_paid, months_subscribed)
        )

# Feature gating based on subscription tier
class FeatureManager:
    """Manage feature access based on subscription tiers"""
    
    @staticmethod
    def check_feature_access(user_subscription: UserSubscription, feature: str) -> bool:
        """Check if user's subscription tier includes specific feature"""
        
        tier_features = SUBSCRIPTION_LIMITS.get(user_subscription.tier, {}).get("features", [])
        return feature in tier_features or "all_features" in tier_features
    
    @staticmethod
    def get_upgrade_suggestion(current_tier: SubscriptionTier, requested_feature: str) -> str:
        """Suggest subscription upgrade for accessing premium features"""
        
        for tier, limits in SUBSCRIPTION_LIMITS.items():
            if requested_feature in limits.get("features", []):
                pricing = SUBSCRIPTION_PRICING[tier]
                return f"Upgrade to {tier.value.title()} (${pricing['monthly_price_usd']}/month) to access {requested_feature}"
        
        return "Feature not available in any subscription tier"
```

Always implement transparent pricing, track all billable operations, provide clear usage limits, and ensure subscription management integrates seamlessly with the user experience.
