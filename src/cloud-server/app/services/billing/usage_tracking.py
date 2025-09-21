"""
ArchBuilder.AI Usage Tracking Service

Tracks user activity, API usage, resource consumption, and billing metrics.
Provides analytics and insights for subscription management and optimization.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func

logger = structlog.get_logger(__name__)


class UsageCategory(str, Enum):
    """Usage category enumeration."""
    AI_REQUESTS = "ai_requests"
    DOCUMENTS_PROCESSED = "documents_processed"
    PROJECTS_CREATED = "projects_created"
    STORAGE_USED = "storage_used"
    API_CALLS = "api_calls"
    RENDER_HOURS = "render_hours"
    COLLABORATION_SEATS = "collaboration_seats"
    EXPORTS_GENERATED = "exports_generated"
    REVIT_SYNCS = "revit_syncs"
    FILE_UPLOADS = "file_uploads"


class BillingPeriod(str, Enum):
    """Billing period enumeration."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class UsageRecord:
    """Individual usage record."""
    user_id: str
    category: UsageCategory
    amount: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    project_id: Optional[str] = None


@dataclass
class UsageSummary:
    """Usage summary for a time period."""
    user_id: str
    period: BillingPeriod
    period_start: datetime
    period_end: datetime
    usage_by_category: Dict[UsageCategory, float]
    total_cost: float = 0.0
    overage_charges: float = 0.0


@dataclass
class UsageLimits:
    """Usage limits for a subscription tier."""
    tier: str
    monthly_limits: Dict[UsageCategory, float]
    overage_rates: Dict[UsageCategory, float]  # Per unit overage cost
    soft_limits: Dict[UsageCategory, float]   # Warning thresholds


class UsageTrackingService:
    """Service for tracking and analyzing user usage."""
    
    def __init__(self):
        """Initialize usage tracking service."""
        self.logger = logger.bind(service="usage_tracking")
        
        # Define usage limits by tier
        self.tier_limits = {
            "free": UsageLimits(
                tier="free",
                monthly_limits={
                    UsageCategory.AI_REQUESTS: 10,
                    UsageCategory.DOCUMENTS_PROCESSED: 5,
                    UsageCategory.PROJECTS_CREATED: 1,
                    UsageCategory.STORAGE_USED: 100,  # MB
                    UsageCategory.API_CALLS: 100,
                    UsageCategory.RENDER_HOURS: 0.5,
                    UsageCategory.COLLABORATION_SEATS: 1,
                    UsageCategory.EXPORTS_GENERATED: 3,
                    UsageCategory.REVIT_SYNCS: 5,
                    UsageCategory.FILE_UPLOADS: 10
                },
                overage_rates={},  # No overages allowed on free tier
                soft_limits={}
            ),
            "starter": UsageLimits(
                tier="starter",
                monthly_limits={
                    UsageCategory.AI_REQUESTS: 500,
                    UsageCategory.DOCUMENTS_PROCESSED: 50,
                    UsageCategory.PROJECTS_CREATED: 10,
                    UsageCategory.STORAGE_USED: 1000,  # MB
                    UsageCategory.API_CALLS: 1000,
                    UsageCategory.RENDER_HOURS: 5,
                    UsageCategory.COLLABORATION_SEATS: 3,
                    UsageCategory.EXPORTS_GENERATED: 50,
                    UsageCategory.REVIT_SYNCS: 100,
                    UsageCategory.FILE_UPLOADS: 100
                },
                overage_rates={
                    UsageCategory.AI_REQUESTS: 0.10,
                    UsageCategory.DOCUMENTS_PROCESSED: 0.50,
                    UsageCategory.STORAGE_USED: 0.01,  # per MB
                    UsageCategory.RENDER_HOURS: 2.00
                },
                soft_limits={
                    UsageCategory.AI_REQUESTS: 400,    # 80% of limit
                    UsageCategory.DOCUMENTS_PROCESSED: 40,
                    UsageCategory.PROJECTS_CREATED: 8
                }
            ),
            "professional": UsageLimits(
                tier="professional",
                monthly_limits={
                    UsageCategory.AI_REQUESTS: 5000,
                    UsageCategory.DOCUMENTS_PROCESSED: 500,
                    UsageCategory.PROJECTS_CREATED: -1,  # Unlimited
                    UsageCategory.STORAGE_USED: 10000,  # MB
                    UsageCategory.API_CALLS: 10000,
                    UsageCategory.RENDER_HOURS: 50,
                    UsageCategory.COLLABORATION_SEATS: 10,
                    UsageCategory.EXPORTS_GENERATED: 500,
                    UsageCategory.REVIT_SYNCS: 1000,
                    UsageCategory.FILE_UPLOADS: 1000
                },
                overage_rates={
                    UsageCategory.AI_REQUESTS: 0.08,
                    UsageCategory.DOCUMENTS_PROCESSED: 0.40,
                    UsageCategory.STORAGE_USED: 0.005,
                    UsageCategory.RENDER_HOURS: 1.50
                },
                soft_limits={
                    UsageCategory.AI_REQUESTS: 4000,
                    UsageCategory.DOCUMENTS_PROCESSED: 400,
                    UsageCategory.STORAGE_USED: 8000
                }
            ),
            "enterprise": UsageLimits(
                tier="enterprise",
                monthly_limits={
                    UsageCategory.AI_REQUESTS: -1,  # Unlimited
                    UsageCategory.DOCUMENTS_PROCESSED: -1,
                    UsageCategory.PROJECTS_CREATED: -1,
                    UsageCategory.STORAGE_USED: -1,
                    UsageCategory.API_CALLS: -1,
                    UsageCategory.RENDER_HOURS: -1,
                    UsageCategory.COLLABORATION_SEATS: -1,
                    UsageCategory.EXPORTS_GENERATED: -1,
                    UsageCategory.REVIT_SYNCS: -1,
                    UsageCategory.FILE_UPLOADS: -1
                },
                overage_rates={},  # Enterprise has custom pricing
                soft_limits={}
            )
        }
        
        self.logger.info("Usage tracking service initialized", 
                        tiers_configured=len(self.tier_limits))

    async def record_usage(self, user_id: str, category: UsageCategory, 
                          amount: float = 1.0, metadata: Optional[Dict[str, Any]] = None,
                          session_id: Optional[str] = None, project_id: Optional[str] = None,
                          db: Optional[AsyncSession] = None) -> bool:
        """Record a usage event."""
        try:
            usage_record = UsageRecord(
                user_id=user_id,
                category=category,
                amount=amount,
                timestamp=datetime.utcnow(),
                metadata=metadata or {},
                session_id=session_id,
                project_id=project_id
            )
            
            # In production, save to database
            # For now, log the usage
            self.logger.info("Usage recorded", 
                           user_id=user_id,
                           category=category.value,
                           amount=amount,
                           session_id=session_id,
                           project_id=project_id)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to record usage", 
                            user_id=user_id,
                            category=category.value,
                            error=str(e))
            return False

    async def get_current_usage(self, user_id: str, period: BillingPeriod = BillingPeriod.MONTHLY,
                               db: Optional[AsyncSession] = None) -> Dict[UsageCategory, float]:
        """Get current usage for a billing period."""
        try:
            # Calculate period boundaries
            now = datetime.utcnow()
            if period == BillingPeriod.MONTHLY:
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == BillingPeriod.DAILY:
                period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == BillingPeriod.WEEKLY:
                days_since_monday = now.weekday()
                period_start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == BillingPeriod.YEARLY:
                period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # In production, query database for actual usage
            # For now, return mock data
            mock_usage = {
                UsageCategory.AI_REQUESTS: 45,
                UsageCategory.DOCUMENTS_PROCESSED: 12,
                UsageCategory.PROJECTS_CREATED: 3,
                UsageCategory.STORAGE_USED: 250.5,
                UsageCategory.API_CALLS: 156,
                UsageCategory.RENDER_HOURS: 2.5,
                UsageCategory.COLLABORATION_SEATS: 2,
                UsageCategory.EXPORTS_GENERATED: 8,
                UsageCategory.REVIT_SYNCS: 23,
                UsageCategory.FILE_UPLOADS: 31
            }
            
            self.logger.info("Current usage retrieved", 
                           user_id=user_id,
                           period=period.value,
                           period_start=period_start.isoformat())
            
            return mock_usage
            
        except Exception as e:
            self.logger.error("Failed to get current usage", 
                            user_id=user_id,
                            period=period.value,
                            error=str(e))
            return {}

    async def check_usage_limits(self, user_id: str, category: UsageCategory, 
                                tier: str, requested_amount: float = 1.0) -> Dict[str, Any]:
        """Check if usage would exceed limits."""
        try:
            if tier not in self.tier_limits:
                return {"allowed": False, "reason": f"Unknown tier: {tier}"}
            
            tier_limit = self.tier_limits[tier]
            category_limit = tier_limit.monthly_limits.get(category, 0)
            
            # Unlimited usage
            if category_limit == -1:
                return {"allowed": True, "limit": "unlimited"}
            
            # Get current usage
            current_usage = await self.get_current_usage(user_id)
            current_amount = current_usage.get(category, 0)
            
            # Check if adding requested amount would exceed limit
            new_total = current_amount + requested_amount
            
            if new_total > category_limit:
                # Check if overages are allowed
                if category in tier_limit.overage_rates:
                    overage_cost = (new_total - category_limit) * tier_limit.overage_rates[category]
                    return {
                        "allowed": True,
                        "overage": True,
                        "overage_amount": new_total - category_limit,
                        "overage_cost": overage_cost,
                        "current": current_amount,
                        "limit": category_limit,
                        "requested": requested_amount
                    }
                else:
                    return {
                        "allowed": False,
                        "reason": f"Monthly limit of {category_limit} {category.value} exceeded",
                        "current": current_amount,
                        "limit": category_limit,
                        "requested": requested_amount
                    }
            
            # Check soft limits for warnings
            soft_limit = tier_limit.soft_limits.get(category)
            warning = False
            if soft_limit and new_total > soft_limit:
                warning = True
            
            return {
                "allowed": True,
                "current": current_amount,
                "limit": category_limit,
                "remaining": category_limit - new_total,
                "requested": requested_amount,
                "warning": warning,
                "soft_limit": soft_limit
            }
            
        except Exception as e:
            self.logger.error("Failed to check usage limits", 
                            user_id=user_id,
                            category=category.value,
                            tier=tier,
                            error=str(e))
            return {"allowed": False, "reason": "Error checking limits"}

    async def get_usage_summary(self, user_id: str, tier: str, 
                               period: BillingPeriod = BillingPeriod.MONTHLY) -> UsageSummary:
        """Get usage summary with cost calculations."""
        try:
            # Get current usage
            usage_by_category = await self.get_current_usage(user_id, period)
            
            # Calculate costs and overages
            total_cost = 0.0
            overage_charges = 0.0
            
            if tier in self.tier_limits:
                tier_limit = self.tier_limits[tier]
                
                for category, amount in usage_by_category.items():
                    limit = tier_limit.monthly_limits.get(category, 0)
                    
                    # Calculate overages
                    if limit != -1 and amount > limit and category in tier_limit.overage_rates:
                        overage_amount = amount - limit
                        overage_cost = overage_amount * tier_limit.overage_rates[category]
                        overage_charges += overage_cost
            
            # Calculate period boundaries
            now = datetime.utcnow()
            if period == BillingPeriod.MONTHLY:
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            else:
                period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(days=1) - timedelta(seconds=1)
            
            summary = UsageSummary(
                user_id=user_id,
                period=period,
                period_start=period_start,
                period_end=period_end,
                usage_by_category=usage_by_category,
                total_cost=total_cost,
                overage_charges=overage_charges
            )
            
            self.logger.info("Usage summary generated", 
                           user_id=user_id,
                           period=period.value,
                           overage_charges=overage_charges)
            
            return summary
            
        except Exception as e:
            self.logger.error("Failed to generate usage summary", 
                            user_id=user_id,
                            tier=tier,
                            period=period.value,
                            error=str(e))
            raise Exception(f"Failed to generate usage summary: {str(e)}")

    async def get_usage_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage analytics and trends."""
        try:
            # In production, this would query historical data
            # For now, return mock analytics
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Mock trend data
            daily_usage = []
            for i in range(days):
                date = start_date + timedelta(days=i)
                daily_usage.append({
                    "date": date.date().isoformat(),
                    "ai_requests": max(0, 10 + i % 5 - 2),
                    "documents_processed": max(0, 2 + i % 3),
                    "projects_created": 1 if i % 7 == 0 else 0,
                    "storage_used": 100 + i * 2.5
                })
            
            # Mock category breakdown
            category_breakdown = {
                "ai_requests": {"percentage": 35, "trend": "increasing"},
                "documents_processed": {"percentage": 25, "trend": "stable"},
                "projects_created": {"percentage": 15, "trend": "stable"},
                "storage_used": {"percentage": 20, "trend": "increasing"},
                "other": {"percentage": 5, "trend": "stable"}
            }
            
            # Mock peak usage times
            peak_hours = {
                "9": 15, "10": 25, "11": 30, "14": 28, "15": 22, "16": 20
            }
            
            analytics = {
                "period": {
                    "start_date": start_date.date().isoformat(),
                    "end_date": end_date.date().isoformat(),
                    "days": days
                },
                "daily_usage": daily_usage,
                "category_breakdown": category_breakdown,
                "peak_hours": peak_hours,
                "total_sessions": 45,
                "average_session_duration": 25.5,  # minutes
                "most_used_features": [
                    "ai_layout_generation",
                    "document_processing",
                    "room_optimization"
                ]
            }
            
            self.logger.info("Usage analytics generated", 
                           user_id=user_id,
                           days=days,
                           total_sessions=analytics["total_sessions"])
            
            return analytics
            
        except Exception as e:
            self.logger.error("Failed to generate usage analytics", 
                            user_id=user_id,
                            days=days,
                            error=str(e))
            return {}

    def get_tier_limits(self, tier: str) -> Optional[UsageLimits]:
        """Get usage limits for a subscription tier."""
        return self.tier_limits.get(tier)

    async def reset_monthly_usage(self, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        """Reset monthly usage counters (typically called on billing cycle)."""
        try:
            # In production, this would reset counters in database
            self.logger.info("Monthly usage reset", user_id=user_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to reset monthly usage", 
                            user_id=user_id,
                            error=str(e))
            return False

    async def bulk_usage_report(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Generate bulk usage report for all users in a date range."""
        try:
            # In production, this would query database for all users
            # For now, return mock data
            
            mock_report = [
                {
                    "user_id": "user_123",
                    "tier": "professional",
                    "total_ai_requests": 1250,
                    "total_documents": 89,
                    "total_projects": 12,
                    "total_cost": 99.99,
                    "overage_charges": 15.50
                },
                {
                    "user_id": "user_456",
                    "tier": "starter",
                    "total_ai_requests": 345,
                    "total_documents": 23,
                    "total_projects": 5,
                    "total_cost": 29.99,
                    "overage_charges": 3.40
                }
            ]
            
            self.logger.info("Bulk usage report generated", 
                           start_date=start_date.isoformat(),
                           end_date=end_date.isoformat(),
                           users_count=len(mock_report))
            
            return mock_report
            
        except Exception as e:
            self.logger.error("Failed to generate bulk usage report", 
                            start_date=start_date.isoformat(),
                            end_date=end_date.isoformat(),
                            error=str(e))
            return []